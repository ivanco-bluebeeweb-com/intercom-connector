"""Messages: send a one-off outbound in-app or email message from an admin
to a contact. Built on intercom_client.py / schemas.py, same shape as
handlers_fin.py -- async, full @chat.function metadata,
ActionResult.success()/.error().
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import intercom_client as ic
from app import chat
from handlers_connection import resolve_or_error
from schemas import CreateMessageParams, MessageResult


@chat.function(
    "create_message",
    "Send a one-off outbound message (in-app or email) from an admin to a contact.",
    action_type="write",
    chain_callable=True,
    data_model=MessageResult,
    event="intercom-connector.create_message",
    effects=["intercom.message.created"],
)
async def create_message(ctx, params: CreateMessageParams) -> ActionResult:
    """Send a one-off message to a contact."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    message_type = (params.message_type or "inapp").strip().lower()
    if message_type not in ("inapp", "email"):
        return ActionResult.error("message_type must be 'inapp' or 'email'.", code="INTERCOM_BAD_MESSAGE_TYPE")
    if message_type == "email" and not params.subject:
        return ActionResult.error("subject is required for message_type='email'.", code="INTERCOM_MISSING_SUBJECT")
    body = {
        "message_type": message_type,
        "body": params.body,
        "from": {"type": "admin", "id": params.from_admin_id},
        "to": {"type": "contact", "id": params.to_contact_id},
    }
    if message_type == "email":
        body["subject"] = params.subject
    try:
        result = await ic.request(ctx, "POST", "/messages", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_CREATE_MESSAGE_FAILED")
    return ActionResult.success(
        MessageResult(id=str(result.get("id", "")), message_type=result.get("message_type", ""),
                      subject=result.get("subject", "") or "", body=result.get("body", "") or "",
                      created_at=result.get("created_at", 0)),
        summary=f"Message sent to contact {params.to_contact_id}.",
    )
