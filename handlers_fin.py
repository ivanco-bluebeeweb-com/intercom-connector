"""Fin AI Agent: start/continue a Fin conversation programmatically, plus
External Pages (custom knowledge-source content Fin can learn from) and
Content Import Sources. Built on intercom_client.py / schemas.py, same
shape as handlers_tags_segments.py -- async, full @chat.function metadata,
ActionResult.success()/.error().
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import intercom_client as ic
from app import chat
from handlers_connection import resolve_or_error
from schemas import (
    StartFinConversationParams, ReplyToFinParams, FinConversationTurn,
    ListExternalPagesParams, ExternalPage, ExternalPageList,
    CreateExternalPageParams, UpdateExternalPageParams,
    DeleteExternalPageParams, DeleteResult,
    ListContentImportSourcesParams, ContentImportSource, ContentImportSourceList,
)


def _fin_turn_from(raw: dict) -> FinConversationTurn:
    reply_parts = raw.get("reply") or {}
    if isinstance(reply_parts, dict):
        reply_text = reply_parts.get("body", "") or ""
    else:
        reply_text = str(reply_parts)
    sources = [s.get("url", "") for s in (raw.get("sources") or []) if isinstance(s, dict)]
    return FinConversationTurn(
        conversation_id=raw.get("id", "") or raw.get("conversation_id", ""),
        reply=reply_text, sources=sources, state=raw.get("state", ""),
    )


@chat.function(
    "start_fin_conversation",
    "Start a new Fin AI Agent conversation on behalf of one of your own end-users, and get Fin's first reply.",
    action_type="write",
    chain_callable=True,
    data_model=FinConversationTurn,
    event="intercom-connector.start_fin_conversation",
    effects=["intercom.fin_conversation.started"],
)
async def start_fin_conversation(ctx, params: StartFinConversationParams) -> ActionResult:
    """Start a Fin AI Agent conversation."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    body = {"user": {"id": params.user_id}, "message": {"body": params.message}}
    try:
        result = await ic.request(ctx, "POST", "/ai/fin/conversations", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_FIN_START_FAILED")
    return ActionResult.success(_fin_turn_from(result), summary="Fin conversation started.")


@chat.function(
    "reply_to_fin",
    "Send a follow-up message into an existing Fin AI Agent conversation and get Fin's next reply.",
    action_type="write",
    chain_callable=True,
    data_model=FinConversationTurn,
    event="intercom-connector.reply_to_fin",
    effects=["intercom.fin_conversation.replied"],
)
async def reply_to_fin(ctx, params: ReplyToFinParams) -> ActionResult:
    """Reply to Fin within an existing conversation."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    body = {"message": {"body": params.message}}
    try:
        result = await ic.request(ctx, "POST", f"/ai/fin/conversations/{params.conversation_id}/reply", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_FIN_REPLY_FAILED")
    return ActionResult.success(_fin_turn_from(result), summary="Fin replied.")


@chat.function(
    "list_external_pages",
    "List External Pages -- custom knowledge-source content registered for Fin AI Agent to learn from.",
    action_type="read",
    chain_callable=True,
    data_model=ExternalPageList,
)
async def list_external_pages(ctx, params: ListExternalPagesParams) -> ActionResult:
    """List External Pages."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", "/external_pages", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_LIST_EXTPAGES_FAILED")
    items = [
        ExternalPage(id=str(p.get("id", "")), title=p.get("title", ""), html=p.get("html", "") or "",
                     url=p.get("url", "") or "", external_id=p.get("external_id", "") or "",
                     created_at=p.get("created_at", 0), updated_at=p.get("updated_at", 0))
        for p in (body.get("data") or [])
    ]
    return ActionResult.success(ExternalPageList(items=items), summary=f"{len(items)} external pages.")


@chat.function(
    "create_external_page",
    "Register a new External Page as a Fin AI Agent knowledge source.",
    action_type="write",
    chain_callable=True,
    data_model=ExternalPage,
    event="intercom-connector.create_external_page",
    effects=["intercom.external_page.created"],
)
async def create_external_page(ctx, params: CreateExternalPageParams) -> ActionResult:
    """Create a new External Page."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    body = {"title": params.title, "html": params.html, "url": params.url, "external_id": params.external_id}
    try:
        result = await ic.request(ctx, "POST", "/external_pages", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_CREATE_EXTPAGE_FAILED")
    return ActionResult.success(
        ExternalPage(id=str(result.get("id", "")), title=result.get("title", ""), html=result.get("html", "") or "",
                     url=result.get("url", "") or "", external_id=result.get("external_id", "") or "",
                     created_at=result.get("created_at", 0), updated_at=result.get("updated_at", 0)),
        summary=f"Created external page '{params.title}'.",
    )


@chat.function(
    "update_external_page",
    "Update an existing External Page's content so Fin AI Agent learns the new version.",
    action_type="write",
    chain_callable=True,
    data_model=ExternalPage,
    event="intercom-connector.update_external_page",
    effects=["intercom.external_page.updated"],
)
async def update_external_page(ctx, params: UpdateExternalPageParams) -> ActionResult:
    """Update an External Page."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    body: dict = {}
    if params.title:
        body["title"] = params.title
    if params.html:
        body["html"] = params.html
    if params.url:
        body["url"] = params.url
    if not body:
        return ActionResult.error("Provide at least one field to update.", code="INTERCOM_NO_FIELDS")
    try:
        result = await ic.request(ctx, "PUT", f"/external_pages/{params.page_id}", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_UPDATE_EXTPAGE_FAILED")
    return ActionResult.success(
        ExternalPage(id=str(result.get("id", "")), title=result.get("title", ""), html=result.get("html", "") or "",
                     url=result.get("url", "") or "", external_id=result.get("external_id", "") or "",
                     created_at=result.get("created_at", 0), updated_at=result.get("updated_at", 0)),
        summary="External page updated.",
    )


@chat.function(
    "delete_external_page",
    "Permanently delete an External Page so Fin AI Agent stops using it as a source. Cannot be undone.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="intercom-connector.delete_external_page",
    effects=["intercom.external_page.deleted"],
)
async def delete_external_page(ctx, params: DeleteExternalPageParams) -> ActionResult:
    """Permanently delete an External Page."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await ic.request(ctx, "DELETE", f"/external_pages/{params.page_id}", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_DELETE_EXTPAGE_FAILED")
    return ActionResult.success(DeleteResult(id=params.page_id, deleted=True), summary="External page deleted.")


@chat.function(
    "list_content_import_sources",
    "List Content Import Sources -- external URLs/sites Fin AI Agent syncs and learns from automatically.",
    action_type="read",
    chain_callable=True,
    data_model=ContentImportSourceList,
)
async def list_content_import_sources(ctx, params: ListContentImportSourcesParams) -> ActionResult:
    """List Content Import Sources."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", "/content_import_sources", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_LIST_IMPORT_SOURCES_FAILED")
    items = [
        ContentImportSource(id=str(s.get("id", "")), status=s.get("status", ""), url=s.get("url", "") or "",
                             sync_behavior=s.get("sync_behavior", "") or "")
        for s in (body.get("data") or [])
    ]
    return ActionResult.success(ContentImportSourceList(items=items), summary=f"{len(items)} content import sources.")
