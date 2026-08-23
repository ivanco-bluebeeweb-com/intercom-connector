"""Tickets: list/get/create/update/reply, ticket types (list/create), ticket
states (list). Built on intercom_client.py / schemas.py, same shape as
handlers_conversations.py -- async, full @chat.function metadata,
ActionResult.success()/.error().
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import intercom_client as ic
from app import chat
from handlers_connection import resolve_or_error
from schemas import (
    ListTicketsParams, Ticket, TicketList,
    GetTicketParams, CreateTicketParams, UpdateTicketParams, ReplyTicketParams,
    ListTicketTypesParams, CreateTicketTypeParams, TicketType, TicketTypeList,
    ListTicketStatesParams, TicketState, TicketStateList,
)


def _ticket_from(raw: dict) -> Ticket:
    ttype = raw.get("ticket_type") or {}
    tstate = raw.get("ticket_state") or {}
    contacts = ((raw.get("contacts") or {}).get("contacts")) or []
    attrs = raw.get("ticket_attributes") or {}
    return Ticket(
        id=raw.get("id", ""), ticket_type_id=str(ttype.get("id") or ""),
        ticket_type_name=ttype.get("name", ""),
        title=attrs.get("_default_title_", "") or raw.get("title", "") or "",
        description=attrs.get("_default_description_", "") or "",
        state=tstate.get("category", "") if isinstance(tstate, dict) else str(raw.get("ticket_state") or ""),
        category=ttype.get("category", ""),
        created_at=raw.get("created_at", 0), updated_at=raw.get("updated_at", 0),
        contact_id=contacts[0].get("id", "") if contacts else "",
        admin_assignee_id=str(raw.get("admin_assignee_id") or ""),
    )


@chat.function(
    "list_tickets",
    "List support tickets in the connected Intercom workspace, cursor-paginated.",
    action_type="read",
    chain_callable=True,
    data_model=TicketList,
)
async def list_tickets(ctx, params: ListTicketsParams) -> ActionResult:
    """List tickets."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    q = {"per_page": params.per_page}
    if params.starting_after:
        q["starting_after"] = params.starting_after
    try:
        body = await ic.request(ctx, "GET", "/tickets", conn["access_token"], conn["region"], params=q)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_LIST_TICKETS_FAILED")
    items = [_ticket_from(t) for t in (body.get("tickets") or body.get("data") or [])]
    pages = body.get("pages") or {}
    nxt = pages.get("next")
    next_cursor = (nxt.get("starting_after") if isinstance(nxt, dict) else nxt) or ""
    return ActionResult.success(TicketList(items=items, next_cursor=next_cursor, total_count=body.get("total_count", 0)), summary=f"{len(items)} tickets.")


@chat.function(
    "get_ticket",
    "Read one ticket in full: type, state, description, and linked contact.",
    action_type="read",
    chain_callable=True,
    data_model=Ticket,
)
async def get_ticket(ctx, params: GetTicketParams) -> ActionResult:
    """Read one ticket by id."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", f"/tickets/{params.ticket_id}", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_GET_TICKET_FAILED")
    return ActionResult.success(_ticket_from(body), summary=f"Ticket #{params.ticket_id}.")


@chat.function(
    "create_ticket",
    "Create a new ticket of a given ticket type, raised for a contact.",
    action_type="write",
    chain_callable=True,
    data_model=Ticket,
    event="intercom-connector.create_ticket",
    effects=["intercom.ticket.created"],
)
async def create_ticket(ctx, params: CreateTicketParams) -> ActionResult:
    """Create a new ticket."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    attrs: dict = {}
    if params.title:
        attrs["_default_title_"] = params.title
    if params.description:
        attrs["_default_description_"] = params.description
    body = {
        "ticket_type_id": params.ticket_type_id,
        "contacts": [{"id": params.contact_id}],
    }
    if attrs:
        body["ticket_attributes"] = attrs
    try:
        result = await ic.request(ctx, "POST", "/tickets", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_CREATE_TICKET_FAILED")
    return ActionResult.success(_ticket_from(result), summary=f"Created ticket #{result.get('id')}.")


@chat.function(
    "update_ticket",
    "Update selected fields of an existing ticket (state and/or title). Only given fields change.",
    action_type="write",
    chain_callable=True,
    data_model=Ticket,
    event="intercom-connector.update_ticket",
    effects=["intercom.ticket.updated"],
)
async def update_ticket(ctx, params: UpdateTicketParams) -> ActionResult:
    """Update an existing ticket's state and/or title."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    body: dict = {}
    if params.state:
        body["state"] = params.state
    if params.title:
        body["ticket_attributes"] = {"_default_title_": params.title}
    if not body:
        return ActionResult.error("Provide at least one field to update.", code="INTERCOM_NO_FIELDS")
    try:
        result = await ic.request(ctx, "PUT", f"/tickets/{params.ticket_id}", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_UPDATE_TICKET_FAILED")
    return ActionResult.success(_ticket_from(result), summary=f"Updated ticket #{params.ticket_id}.")


@chat.function(
    "reply_ticket",
    "Reply to a ticket as an admin, either a visible comment or an internal note.",
    action_type="write",
    chain_callable=True,
    data_model=Ticket,
    event="intercom-connector.reply_ticket",
    effects=["intercom.ticket.replied"],
)
async def reply_ticket(ctx, params: ReplyTicketParams) -> ActionResult:
    """Reply to a ticket."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    body = {"message_type": params.message_type, "type": "admin", "admin_id": params.admin_id, "body": params.body}
    try:
        result = await ic.request(ctx, "POST", f"/tickets/{params.ticket_id}/reply", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_REPLY_TICKET_FAILED")
    return ActionResult.success(_ticket_from(result), summary="Reply sent.")


@chat.function(
    "list_ticket_types",
    "List ticket types configured on the connected Intercom workspace (e.g. 'Bug Report', 'Feature Request').",
    action_type="read",
    chain_callable=True,
    data_model=TicketTypeList,
)
async def list_ticket_types(ctx, params: ListTicketTypesParams) -> ActionResult:
    """List ticket types."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", "/ticket_types", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_LIST_TICKET_TYPES_FAILED")
    items = [
        TicketType(id=t.get("id", ""), name=t.get("name", ""), description=t.get("description", "") or "",
                   category=t.get("category", ""), icon=t.get("icon", "") or "", archived=bool(t.get("archived")))
        for t in (body.get("data") or body.get("ticket_types") or [])
    ]
    return ActionResult.success(TicketTypeList(items=items), summary=f"{len(items)} ticket types.")


@chat.function(
    "create_ticket_type",
    "Create a new ticket type definition (a custom ticket 'shape' with its own attributes).",
    action_type="write",
    chain_callable=True,
    data_model=TicketType,
    event="intercom-connector.create_ticket_type",
    effects=["intercom.ticket_type.created"],
)
async def create_ticket_type(ctx, params: CreateTicketTypeParams) -> ActionResult:
    """Create a new ticket type."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    body = {"name": params.name, "description": params.description, "category": params.category, "icon": params.icon}
    try:
        result = await ic.request(ctx, "POST", "/ticket_types", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_CREATE_TICKET_TYPE_FAILED")
    return ActionResult.success(
        TicketType(id=result.get("id", ""), name=result.get("name", ""), description=result.get("description", "") or "",
                   category=result.get("category", ""), icon=result.get("icon", "") or "", archived=False),
        summary=f"Created ticket type '{params.name}'.",
    )


@chat.function(
    "list_ticket_states",
    "List the ticket states configured on the connected Intercom workspace (e.g. Submitted, In Progress, Resolved).",
    action_type="read",
    chain_callable=True,
    data_model=TicketStateList,
)
async def list_ticket_states(ctx, params: ListTicketStatesParams) -> ActionResult:
    """List ticket states."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", "/ticket_states", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_LIST_TICKET_STATES_FAILED")
    items = [
        TicketState(id=str(s.get("id", "")), category=s.get("category", ""), label=s.get("label", ""), is_default=bool(s.get("is_default")))
        for s in (body.get("ticket_states") or body.get("data") or [])
    ]
    return ActionResult.success(TicketStateList(items=items), summary=f"{len(items)} ticket states.")
