"""Conversations: list/get/search/reply/manage(assign,close,snooze,open),
notes, parts. Built on intercom_client.py / schemas.py, same shape as
handlers_contacts.py -- async, full @chat.function metadata,
ActionResult.success()/.error().
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import intercom_client as ic
from app import chat
from handlers_connection import resolve_or_error
from schemas import (
    ListConversationsParams, Conversation, ConversationList, ConversationPart,
    GetConversationParams, SearchConversationsParams,
    ReplyConversationParams, ManageConversationParams,
    AddConversationNoteParams,
)


def _part_from(raw: dict) -> ConversationPart:
    author = raw.get("author") or {}
    return ConversationPart(
        id=raw.get("id", ""), part_type=raw.get("part_type", ""),
        body=raw.get("body", "") or "", author_type=author.get("type", ""),
        author_name=author.get("name", ""), created_at=raw.get("created_at", 0),
    )


def _conversation_from(raw: dict) -> Conversation:
    source = raw.get("source") or {}
    author = source.get("author") or {}
    parts = ((raw.get("conversation_parts") or {}).get("conversation_parts")) or []
    return Conversation(
        id=raw.get("id", ""), title=raw.get("title", "") or "",
        state=raw.get("state", ""), open=bool(raw.get("open")), read=bool(raw.get("read")),
        priority=raw.get("priority", "") or "",
        created_at=raw.get("created_at", 0), updated_at=raw.get("updated_at", 0),
        waiting_since=raw.get("waiting_since") or 0, snoozed_until=raw.get("snoozed_until") or 0,
        admin_assignee_id=str(raw.get("admin_assignee_id") or ""),
        team_assignee_id=str(raw.get("team_assignee_id") or ""),
        source_body=source.get("body", "") or "", source_author_type=author.get("type", ""),
        tags=[t.get("name", "") for t in (raw.get("tags") or {}).get("tags", [])] if isinstance(raw.get("tags"), dict) else [],
        parts=[_part_from(p) for p in parts],
    )


@chat.function(
    "list_conversations",
    "List conversations in the connected Intercom workspace, cursor-paginated.",
    action_type="read",
    chain_callable=True,
    data_model=ConversationList,
)
async def list_conversations(ctx, params: ListConversationsParams) -> ActionResult:
    """List conversations."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    q = {"per_page": params.per_page}
    if params.starting_after:
        q["starting_after"] = params.starting_after
    try:
        body = await ic.request(ctx, "GET", "/conversations", conn["access_token"], conn["region"], params=q)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_LIST_CONVERSATIONS_FAILED")
    items = [_conversation_from(c) for c in (body.get("conversations") or [])]
    pages = body.get("pages") or {}
    nxt = pages.get("next")
    next_cursor = (nxt.get("starting_after") if isinstance(nxt, dict) else nxt) or ""
    return ActionResult.success(
        ConversationList(items=items, next_cursor=next_cursor, total_count=body.get("total_count", 0)),
        summary=f"{len(items)} conversations.",
    )


@chat.function(
    "get_conversation",
    "Read one conversation in full: source message, state, assignee, tags, and every conversation part (replies/notes).",
    action_type="read",
    chain_callable=True,
    data_model=Conversation,
)
async def get_conversation(ctx, params: GetConversationParams) -> ActionResult:
    """Read one conversation by id."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", f"/conversations/{params.conversation_id}", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_GET_CONVERSATION_FAILED")
    return ActionResult.success(_conversation_from(body), summary=f"Conversation '{body.get('title') or params.conversation_id}'.")


@chat.function(
    "search_conversations",
    "Search conversations by a single field/operator/value filter (e.g. state = open, priority = priority).",
    action_type="read",
    chain_callable=True,
    data_model=ConversationList,
)
async def search_conversations(ctx, params: SearchConversationsParams) -> ActionResult:
    """Search conversations with one filter clause."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    query = {"field": params.field, "operator": params.operator, "value": params.value}
    try:
        body = await ic.request(ctx, "POST", "/conversations/search", conn["access_token"], conn["region"], json_body={"query": query})
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_SEARCH_CONVERSATIONS_FAILED")
    items = [_conversation_from(c) for c in (body.get("conversations") or [])]
    return ActionResult.success(ConversationList(items=items, total_count=body.get("total_count", 0)), summary=f"{len(items)} matching conversations.")


@chat.function(
    "reply_conversation",
    "Reply to a conversation as an admin, either a visible comment or an internal note.",
    action_type="write",
    chain_callable=True,
    data_model=Conversation,
    event="intercom-connector.reply_conversation",
    effects=["intercom.conversation.replied"],
)
async def reply_conversation(ctx, params: ReplyConversationParams) -> ActionResult:
    """Reply to a conversation as an admin."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    body = {
        "message_type": params.message_type, "type": "admin",
        "admin_id": params.admin_id, "body": params.body,
    }
    try:
        result = await ic.request(ctx, "POST", f"/conversations/{params.conversation_id}/reply", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_REPLY_CONVERSATION_FAILED")
    return ActionResult.success(_conversation_from(result), summary="Reply sent.")


@chat.function(
    "manage_conversation",
    "Manage a conversation's lifecycle: close, snooze, reopen, or assign to an admin/team.",
    action_type="write",
    chain_callable=True,
    data_model=Conversation,
    event="intercom-connector.manage_conversation",
    effects=["intercom.conversation.managed"],
)
async def manage_conversation(ctx, params: ManageConversationParams) -> ActionResult:
    """Close, snooze, reopen, or assign a conversation."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    action = (params.action or "").strip().lower()
    if action not in ("close", "snooze", "open", "assign"):
        return ActionResult.error("action must be one of: close, snooze, open, assign.", code="INTERCOM_BAD_ACTION")
    body: dict = {"message_type": action, "type": "admin", "admin_id": params.admin_id}
    if action == "snooze":
        if not params.snoozed_until:
            return ActionResult.error("snoozed_until (unix timestamp) is required for action='snooze'.", code="INTERCOM_MISSING_SNOOZE_TIME")
        body["snoozed_until"] = params.snoozed_until
    if action == "assign":
        if not params.assignee_id:
            return ActionResult.error("assignee_id is required for action='assign'.", code="INTERCOM_MISSING_ASSIGNEE")
        body["assignee_id"] = params.assignee_id
    try:
        result = await ic.request(ctx, "POST", f"/conversations/{params.conversation_id}/parts", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_MANAGE_CONVERSATION_FAILED")
    return ActionResult.success(_conversation_from(result), summary=f"Conversation {action}d." if action != "open" else "Conversation reopened.")


@chat.function(
    "add_conversation_note",
    "Add an internal note to a conversation, visible only to teammates.",
    action_type="write",
    chain_callable=True,
    data_model=Conversation,
    event="intercom-connector.add_conversation_note",
    effects=["intercom.conversation.note_added"],
)
async def add_conversation_note(ctx, params: AddConversationNoteParams) -> ActionResult:
    """Add an internal note to a conversation."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    body = {"message_type": "note", "type": "admin", "admin_id": params.admin_id, "body": params.body}
    try:
        result = await ic.request(ctx, "POST", f"/conversations/{params.conversation_id}/reply", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_ADD_NOTE_FAILED")
    return ActionResult.success(_conversation_from(result), summary="Note added.")
