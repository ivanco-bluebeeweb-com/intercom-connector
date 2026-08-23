"""Connection management: connect/disconnect Intercom workspaces, list
connections. Same shape as PagerDuty Connector's / AppFolio Connector's
connection handlers -- async, one secret holding a JSON array,
ActionResult.success()/.error(), full @chat.function metadata.
"""
from __future__ import annotations

import json
import uuid

from imperal_sdk import ActionResult

import intercom_client as ic
from app import ext, chat
from schemas import (
    NoParams,
    ConnectIntercomParams, IntercomConnection, IntercomConnectionList,
    DisconnectIntercomParams, DeleteResult,
)

_CONN_SECRET = "intercom_connections"


async def _load_connections(ctx) -> list[dict]:
    raw = await ctx.secrets.get(_CONN_SECRET)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


async def _save_connections(ctx, items: list[dict]) -> None:
    await ctx.secrets.set(_CONN_SECRET, json.dumps(items))


async def resolve_connection(ctx, connection_id: str = "") -> dict | None:
    items = await _load_connections(ctx)
    if not items:
        return None
    if connection_id:
        for item in items:
            if item.get("id") == connection_id:
                return item
        return None
    return items[0]


async def resolve_or_error(ctx, connection_id: str = ""):
    """Shared guard: resolve a connection or return the standard
    'not connected' ActionResult.error. Returns (conn, error_or_None)."""
    conn = await resolve_connection(ctx, connection_id)
    if conn is None:
        return None, ActionResult.error(
            "No Intercom workspace is connected yet. Use connect_intercom first.",
            code="INTERCOM_ACCOUNT_MISSING",
        )
    return conn, None


@chat.function(
    "connect_intercom",
    "Connect your own Intercom workspace by saving its private-app Access "
    "Token, after checking it actually works against your chosen data "
    "region. Get a token from Intercom: Developer Hub > your app > "
    "Configure > Authentication.",
    action_type="write",
    chain_callable=True,
    data_model=IntercomConnection,
    event="intercom-connector.connect_intercom",
    effects=["intercom.provider.connected"],
)
async def connect_intercom(ctx, params: ConnectIntercomParams) -> ActionResult:
    """Connect your own Intercom workspace by saving its Access Token."""
    token = (params.access_token or "").strip()
    if not token:
        return ActionResult.error("Access Token is required.", code="INTERCOM_MISSING_FIELD")
    region = (params.region or "us").strip().lower()
    if region not in ("us", "eu", "au"):
        return ActionResult.error(
            "region must be one of: us, eu, au.", code="INTERCOM_INVALID_REGION",
        )

    try:
        me = await ic.validate_token(ctx, token, region)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), retryable=(e.status == 0), code="INTERCOM_CONNECT_FAILED")

    workspace_name = ""
    app_info = me.get("app") if isinstance(me, dict) else None
    if isinstance(app_info, dict):
        workspace_name = app_info.get("name") or app_info.get("id_code") or ""

    items = await _load_connections(ctx)
    entry = {
        "id": str(uuid.uuid4()),
        "label": params.label or workspace_name or f"Intercom ({region.upper()})",
        "access_token": token,
        "region": region,
        "workspace_name": workspace_name,
    }
    items.append(entry)
    await _save_connections(ctx, items)

    return ActionResult.success(
        IntercomConnection(
            id=entry["id"], title=entry["label"], connected=True,
            detail=f"Connected to Intercom region {region.upper()}.",
            region=region, workspace_name=workspace_name,
        ),
        summary=f"Connected Intercom workspace '{entry['label']}' ({region.upper()}).",
        refresh_panels=["ic_connect", "ic_settings"],
    )


@chat.function(
    "disconnect_intercom",
    "Disconnect an Intercom workspace: deletes the saved Access Token. "
    "Nothing in Intercom itself is changed.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="intercom-connector.disconnect_intercom",
    effects=["intercom.provider.disconnected"],
)
async def disconnect_intercom(ctx, params: DisconnectIntercomParams) -> ActionResult:
    """Disconnect an Intercom workspace: deletes the saved Access Token."""
    items = await _load_connections(ctx)
    if not items:
        return ActionResult.error("No Intercom workspace is connected.", code="INTERCOM_NOT_CONNECTED")

    target_id = params.connection_id or items[0]["id"]
    remaining = [i for i in items if i.get("id") != target_id]
    if len(remaining) == len(items):
        return ActionResult.error("Connection not found.", code="INTERCOM_CONNECTION_NOT_FOUND")

    await _save_connections(ctx, remaining)
    return ActionResult.success(
        DeleteResult(id=target_id, deleted=True),
        summary="Disconnected the Intercom workspace.",
        refresh_panels=["ic_connect", "ic_settings"],
    )


@chat.function(
    "list_connections",
    "List the connected Intercom workspaces.",
    action_type="read",
    chain_callable=True,
    data_model=IntercomConnectionList,
)
async def list_connections(ctx, params: NoParams) -> ActionResult:
    """List the connected Intercom workspaces."""
    items = await _load_connections(ctx)
    out = [
        IntercomConnection(
            id=i.get("id", ""), title=i.get("label", ""), connected=True,
            detail=f"Region: {i.get('region', 'us').upper()}",
            region=i.get("region", "us"), workspace_name=i.get("workspace_name", ""),
        )
        for i in items
    ]
    return ActionResult.success(
        IntercomConnectionList(items=out),
        summary=f"{len(out)} Intercom workspace(s) connected." if out else "No Intercom workspace connected yet.",
    )
