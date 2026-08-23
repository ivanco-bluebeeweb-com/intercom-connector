"""Admin (teammate) and Team management: list/get admins, set away status,
list/get teams. Built on intercom_client.py / schemas.py, same shape as
handlers_content.py -- async, full @chat.function metadata,
ActionResult.success()/.error().
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import intercom_client as ic
from app import chat
from handlers_connection import resolve_or_error
from schemas import (
    ListAdminsParams, Admin, AdminList,
    GetAdminParams, SetAdminAwayParams,
    ListTeamsParams, GetTeamParams, Team, TeamList,
)


@chat.function(
    "list_admins",
    "List admins (teammates) on the connected Intercom workspace.",
    action_type="read",
    chain_callable=True,
    data_model=AdminList,
)
async def list_admins(ctx, params: ListAdminsParams) -> ActionResult:
    """List admins."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", "/admins", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_LIST_ADMINS_FAILED")
    items = [
        Admin(id=str(a.get("id", "")), name=a.get("name", ""), email=a.get("email", ""),
              away_mode_enabled=bool(a.get("away_mode_enabled")), team_ids=[str(t) for t in (a.get("team_ids") or [])])
        for a in (body.get("admins") or [])
    ]
    return ActionResult.success(AdminList(items=items), summary=f"{len(items)} admins.")


@chat.function(
    "get_admin",
    "Read one admin (teammate) in full by id.",
    action_type="read",
    chain_callable=True,
    data_model=Admin,
)
async def get_admin(ctx, params: GetAdminParams) -> ActionResult:
    """Read one admin by id."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", f"/admins/{params.admin_id}", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_GET_ADMIN_FAILED")
    return ActionResult.success(
        Admin(id=str(body.get("id", "")), name=body.get("name", ""), email=body.get("email", ""),
              away_mode_enabled=bool(body.get("away_mode_enabled")), team_ids=[str(t) for t in (body.get("team_ids") or [])]),
        summary=f"Admin '{body.get('name') or params.admin_id}'.",
    )


@chat.function(
    "set_admin_away",
    "Set an admin away or back, optionally reassigning their open conversations.",
    action_type="write",
    chain_callable=True,
    data_model=Admin,
    event="intercom-connector.set_admin_away",
    effects=["intercom.admin.away_status_changed"],
)
async def set_admin_away(ctx, params: SetAdminAwayParams) -> ActionResult:
    """Set an admin's away/back status."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    body: dict = {
        "away_mode_enabled": params.away_mode_enabled,
        "away_mode_reassign": params.reassign_conversations,
    }
    if params.away_status_reason_id:
        body["away_status_reason_id"] = params.away_status_reason_id
    try:
        result = await ic.request(ctx, "PUT", f"/admins/{params.admin_id}/away", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_SET_AWAY_FAILED")
    return ActionResult.success(
        Admin(id=str(result.get("id", "")), name=result.get("name", ""), email=result.get("email", ""),
              away_mode_enabled=bool(result.get("away_mode_enabled")), team_ids=[str(t) for t in (result.get("team_ids") or [])]),
        summary=f"Admin '{result.get('name') or params.admin_id}' is now {'away' if params.away_mode_enabled else 'back'}.",
    )


@chat.function(
    "list_teams",
    "List teams (groups of admins) on the connected Intercom workspace.",
    action_type="read",
    chain_callable=True,
    data_model=TeamList,
)
async def list_teams(ctx, params: ListTeamsParams) -> ActionResult:
    """List teams."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", "/teams", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_LIST_TEAMS_FAILED")
    items = [
        Team(id=str(t.get("id", "")), name=t.get("name", ""), admin_ids=[str(a) for a in (t.get("admin_ids") or [])])
        for t in (body.get("teams") or [])
    ]
    return ActionResult.success(TeamList(items=items), summary=f"{len(items)} teams.")


@chat.function(
    "get_team",
    "Read one team in full: its name and member admin ids.",
    action_type="read",
    chain_callable=True,
    data_model=Team,
)
async def get_team(ctx, params: GetTeamParams) -> ActionResult:
    """Read one team by id."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", f"/teams/{params.team_id}", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_GET_TEAM_FAILED")
    return ActionResult.success(
        Team(id=str(body.get("id", "")), name=body.get("name", ""), admin_ids=[str(a) for a in (body.get("admin_ids") or [])]),
        summary=f"Team '{body.get('name') or params.team_id}'.",
    )
