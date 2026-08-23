"""Extension declaration, secrets, lifecycle hooks.

WHY BYOK (bring-your-own-key), SAME REASONING AS PagerDuty Connector /
Stripe Connector / Cin7 Core Connector.

Intercom is the user's OWN customer-messaging workspace -- Imperal cannot
and should not broker access to someone else's customers/conversations
centrally. The user pastes their own private-app Access Token once,
Vault-encrypted via `ctx.secrets`, and every call runs against their own
Intercom workspace.

WHY A PLAIN ACCESS TOKEN, NOT OAUTH2, FOR THE PRIMARY CONNECTION -- SAME
REASONING AS Stripe Connector / PagerDuty Connector.

Intercom's REST API authenticates private apps with a single Access
Token sent as `Authorization: Bearer <token>` (developers.intercom.com/
docs/build-an-integration/learn-more/authentication, confirmed during
Discovery 2026-08-23) -- issued immediately when the user creates a
private app in their own Developer Hub, no review needed. OAuth is only
required for PUBLIC Intercom Marketplace apps that reach OTHER people's
workspaces -- not our model. `connect_intercom` validates the pasted
token against `GET /me` (cheap, always-available call) and stores it.

WHY THE REGION IS STORED ALONGSIDE THE TOKEN, NOT ASSUMED.

Intercom workspaces are regionally hosted (US/EU/Australia) and the
REST API host itself changes per region: `api.intercom.io` (US),
`api.eu.intercom.io` (EU), `api.au.intercom.io` (AU) -- confirmed via
intercom.com/help/en/articles/6124430-regional-data-hosting, 2026-08-23.
Using the wrong host for a non-US workspace produces a connection
failure that looks like a bad token, not a region mismatch -- so
`connect_intercom` asks for (or auto-detects via trial request) the
region and stores it next to the token, same "store what actually
varies the request" precedent as PagerDuty Connector's from_email.

WHY ONE SECRET HOLDING A JSON ARRAY FOR CONNECTIONS, SAME PRECEDENT AS
MuleSoft Connector / PagerDuty Connector / Power Automate Connector.

A user may run more than one Intercom workspace (e.g. one per brand, if
this is used by an agency). `ctx.secrets` only supports a fixed,
manifest-declared set of NAMES -- there is no "one secret per
connection" primitive, so `intercom_connections` holds a JSON array of
`{id, label, access_token, region}` objects, and every tool's
`connection_id` parameter addresses one entry in that array -- see
handlers_connection.py's `_load_connections`/`_save_connections` helpers.
"""
from __future__ import annotations

from imperal_sdk import ChatExtension, Extension

ext = Extension(
    "intercom-connector",
    version="0.1.0",
    display_name="Intercom",
    description=(
        "Connect your own Intercom workspace to manage customer "
        "messaging from Imperal -- contacts, companies, conversations "
        "(reply/close/snooze/assign/tag/note), tickets and ticket "
        "types/states, Help Center articles and collections, News "
        "items, in-app/email messages, admins/teams/away status, data "
        "attributes and custom data events, segments, tags, "
        "subscription types, calls, visitors, Fin AI Agent "
        "conversations, Fin's knowledge base (AI Content external "
        "pages/content import sources), and reporting/data exports. "
        "Uses your own Access Token -- nothing is hosted or proxied by "
        "Imperal beyond the request itself."
    ),
    icon="icon.svg",
    capabilities=[
        "intercom:read",
        "intercom:write",
    ],
    actions_explicit=True,
    system=False,
)

chat = ChatExtension(
    ext,
    tool_name="intercom",
    description=(
        "Intercom Connector -- connect your own Intercom workspace via "
        "your Access Token, then manage contacts, companies, "
        "conversations, tickets, Help Center articles, News, messages, "
        "admins/teams, data attributes/events, segments, tags, calls, "
        "visitors, Fin AI Agent, AI content sources, and data exports."
    ),
)

ext.secret(
    "intercom_connections",
    (
        "Your connected Intercom workspaces -- stored as a JSON array, "
        "one entry per workspace, each with its own Access Token and "
        "data-hosting region. Managed through connect_intercom / "
        "disconnect_intercom -- you should not need to edit this "
        "directly."
    ),
    required=True,
    write_mode="both",
    max_bytes=65536,
    rotation_hint_days=180,
)(lambda: None)


@ext.health_check
async def health_check(ctx) -> dict:
    """Fast configuration health; no third-party call -- just confirms at
    least one workspace connection is stored, same shape as PagerDuty
    Connector's health_check."""
    import json as _json
    raw = await ctx.secrets.get("intercom_connections")
    try:
        count = len(_json.loads(raw)) if raw else 0
    except Exception:
        count = 0
    return {
        "healthy": True,
        "detail": (
            f"{count} Intercom workspace(s) connected." if count
            else "Not connected yet -- run connect_intercom."
        ),
    }
