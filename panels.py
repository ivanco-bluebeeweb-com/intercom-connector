"""Panel UI -- connections list/connect form in the left sidebar.

SIDEBAR CONTENT -- NO CARDS ANYWHERE, per ~/UI_INTERFACE_STANDARD.md's
"left sidebar, no decorated cards" rule (same convention as DocuSign
Connector's / PagerDuty Connector's panels.py).

Every section (connections, connect form) is a plain ui.Stack, content
stacked vertically and left-aligned, sections separated by ui.Divider() --
no Card border/background/shadow anywhere in this slot. Disconnect lives
only in the "App settings" screen (panels_settings.py). The one secondary
"App settings" button is always the LAST element at the bottom of the
sidebar.

PER ~/UI_INTERFACE_STANDARD.md (2026-08-21 addendum): every Input carries
its own visible label (never placeholder-only), the placeholder text is
always contextually specific to what's being entered (never a generic
"Enter value"), the form's own container is stretched to the full width
of the left sidebar, and the form's inner content is stretched to fill
that container. The "How do I get an Access Token?" walkthrough lives
ONLY in the help modal (intercom_connect_help below) -- it is not
duplicated as static sidebar text.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
import handlers_connection as h


def _settings_button() -> ui.UINode:
    """The one required secondary entry point into the settings screen --
    always the last element at the bottom of the sidebar."""
    return ui.Button(
        "App settings", variant="secondary", size="sm", full_width=True,
        icon="settings", on_click=ui.Call("__panel__intercom_settings"),
    )


def _connection_row(c: dict) -> ui.UINode:
    label = c.get("label") or c.get("workspace_name") or "Intercom workspace"
    region = (c.get("region") or "us").upper()
    detail = f"Region: {region}" + (f" · {c.get('workspace_name')}" if c.get("workspace_name") and c.get("label") else "")
    return ui.Stack(direction="v", gap=1, children=[
        ui.Text(label, variant="body"),
        ui.Text(detail, variant="caption"),
    ])


def _connections_section(connections: list[dict]) -> ui.UINode:
    if not connections:
        return ui.Text("No Intercom workspaces connected yet.", variant="caption")
    children: list[ui.UINode] = []
    for i, c in enumerate(connections):
        if i > 0:
            children.append(ui.Divider())
        children.append(_connection_row(c))
    return ui.Stack(direction="v", gap=2, children=children)


def _connect_section() -> ui.UINode:
    """Form container stretched to the FULL WIDTH of the left sidebar, its
    inner content stretched to fill it (align="stretch" on both the outer
    Stack and the Form's own children Stack). No intro heading/description
    text here -- the Access Token walkthrough lives ONLY in
    intercom_connect_help's modal (button below opens it); repeating it
    here would duplicate that instruction."""
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Button("How do I get an Access Token?", variant="ghost", size="sm",
                  icon="HelpCircle",
                  on_click=ui.Call("__panel__intercom_connect_help")),
        ui.Form(
            action="connect_intercom",
            submit_label="Verify and connect",
            children=[
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Access Token", variant="caption"),
                    ui.Password(param_name="access_token",
                                placeholder="Your private app's Access Token from Developer Hub"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Region", variant="caption"),
                    ui.Select(param_name="region",
                              options=[
                                  {"label": "US (default)", "value": "us"},
                                  {"label": "EU", "value": "eu"},
                                  {"label": "Australia", "value": "au"},
                              ],
                              value="us"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Label (optional)", variant="caption"),
                    ui.Input(param_name="label", placeholder="e.g. Support workspace or Sales workspace"),
                ]),
            ],
        ),
    ])


@ext.panel("intercom_connect", slot="left", title="Intercom", icon="💬",
           default_width=340, min_width=280, max_width=440)
async def intercom_connect_panel(ctx, **kwargs) -> object:
    connections = await h._load_connections(ctx)
    connected = bool(connections)

    header = ui.Header(text="Intercom", level=2,
                        subtitle="Customer messaging, support, and Fin AI Agent from Imperal")

    if not connected:
        return ui.Stack(direction="v", gap=4, align="stretch", children=[
            header,
            _connect_section(),
            ui.Divider(),
            _settings_button(),
        ])

    return ui.Stack(direction="v", gap=4, align="stretch", children=[
        header,
        ui.Text("Connected workspaces", variant="subtitle"),
        _connections_section(connections),
        ui.Divider(),
        _connect_section(),
        ui.Divider(),
        _settings_button(),
    ])


@ext.panel("intercom_connect_help", slot="center",
           title="How to connect Intercom", center_overlay=True)
async def intercom_connect_help(ctx, **kwargs) -> object:
    content = ui.Stack(direction="v", gap=3, children=[
        ui.Text("1. In Intercom, go to Settings > Integrations > Developer Hub, and create a new app (or use an existing one)."),
        ui.Text("2. Under that app's Authentication page, copy its Access Token -- that's what this form asks for."),
        ui.Text("3. Check your workspace's data hosting region (Settings > Workspace > General, or ask your Intercom admin) and select it here -- US, EU, or Australia. The wrong region makes every call fail with an auth-looking error."),
        ui.Text("4. Under Permissions on the same app, grant the scopes you plan to use (Contacts, Companies, Conversations, Tickets, Articles, Fin AI Agent, etc.)."),
        ui.Text("5. Connect here -- the token is checked immediately against your own workspace."),
        ui.Divider(),
        ui.Alert(
            title="REST API v2.16 scope",
            message=(
                "This manages contacts, companies, conversations, tickets, "
                "Help Center articles/collections, News items, admins/teams, "
                "data attributes/events/export, tags, segments, and Fin AI "
                "Agent conversations/external pages. Visitors, Calls, "
                "Switch, and Internal Articles are out of scope."
            ),
            type="warning",
        ),
        ui.Divider(),
        ui.Link(
            label="Open Intercom's official Authentication guide",
            href="https://developers.intercom.com/docs/build-an-integration/learn-more/authentication",
        ),
    ])
    return ui.Dialog(
        title="How to connect Intercom",
        content=content,
        confirm_label="",
        cancel_label="Close",
    )


@ext.panel("intercom_center", slot="center", title="Intercom", icon="💬", center_overlay=True)
async def intercom_center_panel(ctx, **kwargs) -> object:
    """Base center panel -- per UI_INTERFACE_STANDARD.md (2026-08-20).
    This app has no list/detail content of its own to show in the center
    by default (everything lives in the sidebar). MUST carry
    center_overlay=True: per docs.imperal.io/en/concepts/panels, a plain
    slot="center" panel is registered but the Panel app never fetches it
    at session-init without that flag. Text is the shared canonical
    wording -- must stay identical across every app in this situation."""
    return ui.Empty(
        message="Select an action -- use the Intercom panel on the left, or ask Webbee to do something with Intercom.",
    )
