"""Tags, Segments, and Subscription Types (contact opt-in/out). Built on
intercom_client.py / schemas.py, same shape as handlers_data.py -- async,
full @chat.function metadata, ActionResult.success()/.error().
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import intercom_client as ic
from app import chat
from handlers_connection import resolve_or_error
from schemas import (
    ListTagsParams, Tag, TagList, CreateTagParams, DeleteTagParams, DeleteResult,
    ListSegmentsParams, Segment, SegmentList, GetSegmentParams,
    ListSubscriptionTypesParams, SubscriptionType, SubscriptionTypeList,
    AttachContactSubscriptionParams, DetachContactSubscriptionParams,
)


@chat.function(
    "list_tags",
    "List tags defined on the connected Intercom workspace.",
    action_type="read",
    chain_callable=True,
    data_model=TagList,
)
async def list_tags(ctx, params: ListTagsParams) -> ActionResult:
    """List tags."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", "/tags", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_LIST_TAGS_FAILED")
    items = [Tag(id=str(t.get("id", "")), name=t.get("name", "")) for t in (body.get("data") or [])]
    return ActionResult.success(TagList(items=items), summary=f"{len(items)} tags.")


@chat.function(
    "create_tag",
    "Create a new tag on the connected Intercom workspace.",
    action_type="write",
    chain_callable=True,
    data_model=Tag,
    event="intercom-connector.create_tag",
    effects=["intercom.tag.created"],
)
async def create_tag(ctx, params: CreateTagParams) -> ActionResult:
    """Create a new tag."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        result = await ic.request(ctx, "POST", "/tags", conn["access_token"], conn["region"], json_body={"name": params.name})
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_CREATE_TAG_FAILED")
    return ActionResult.success(Tag(id=str(result.get("id", "")), name=result.get("name", "")), summary=f"Created tag '{params.name}'.")


@chat.function(
    "delete_tag",
    "Permanently delete a tag from the workspace. Removes it from every contact/conversation/company it was attached to.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="intercom-connector.delete_tag",
    effects=["intercom.tag.deleted"],
)
async def delete_tag(ctx, params: DeleteTagParams) -> ActionResult:
    """Permanently delete a tag by id."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await ic.request(ctx, "DELETE", f"/tags/{params.tag_id}", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_DELETE_TAG_FAILED")
    return ActionResult.success(DeleteResult(id=params.tag_id, deleted=True), summary="Tag deleted.")


@chat.function(
    "list_segments",
    "List segments (dynamic, condition-based contact groups computed by Intercom itself) on the connected workspace.",
    action_type="read",
    chain_callable=True,
    data_model=SegmentList,
)
async def list_segments(ctx, params: ListSegmentsParams) -> ActionResult:
    """List segments."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", "/segments", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_LIST_SEGMENTS_FAILED")
    items = [
        Segment(id=s.get("id", ""), name=s.get("name", ""), created_at=s.get("created_at", 0),
                updated_at=s.get("updated_at", 0), person_type=s.get("person_type", "") or "")
        for s in (body.get("data") or [])
    ]
    return ActionResult.success(SegmentList(items=items), summary=f"{len(items)} segments.")


@chat.function(
    "get_segment",
    "Read one segment's definition in full by id.",
    action_type="read",
    chain_callable=True,
    data_model=Segment,
)
async def get_segment(ctx, params: GetSegmentParams) -> ActionResult:
    """Read one segment by id."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", f"/segments/{params.segment_id}", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_GET_SEGMENT_FAILED")
    return ActionResult.success(
        Segment(id=body.get("id", ""), name=body.get("name", ""), created_at=body.get("created_at", 0),
                updated_at=body.get("updated_at", 0), person_type=body.get("person_type", "") or ""),
        summary=f"Segment '{body.get('name') or params.segment_id}'.",
    )


@chat.function(
    "list_subscription_types",
    "List subscription types (opt-in/opt-out communication categories, e.g. Newsletters, Product Updates) on the workspace.",
    action_type="read",
    chain_callable=True,
    data_model=SubscriptionTypeList,
)
async def list_subscription_types(ctx, params: ListSubscriptionTypesParams) -> ActionResult:
    """List subscription types."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", "/subscription_types", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_LIST_SUBS_FAILED")
    items = [
        SubscriptionType(id=str(s.get("id", "")), state=s.get("state", ""),
                          default_translation=(s.get("default_translation") or {}).get("name", "") if isinstance(s.get("default_translation"), dict) else "",
                          content_types=s.get("content_types") or [])
        for s in (body.get("data") or [])
    ]
    return ActionResult.success(SubscriptionTypeList(items=items), summary=f"{len(items)} subscription types.")


@chat.function(
    "attach_contact_subscription",
    "Opt a contact into a subscription type (e.g. subscribe them to a newsletter category).",
    action_type="write",
    chain_callable=True,
    data_model=SubscriptionType,
    event="intercom-connector.attach_contact_subscription",
    effects=["intercom.contact.subscribed"],
)
async def attach_contact_subscription(ctx, params: AttachContactSubscriptionParams) -> ActionResult:
    """Opt a contact into a subscription type."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        result = await ic.request(
            ctx, "POST", f"/contacts/{params.contact_id}/subscriptions", conn["access_token"], conn["region"],
            json_body={"id": params.subscription_type_id},
        )
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_ATTACH_SUB_FAILED")
    return ActionResult.success(
        SubscriptionType(id=str(result.get("id", "")), state=result.get("state", "")),
        summary="Contact subscribed.",
    )


@chat.function(
    "detach_contact_subscription",
    "Opt a contact out of a subscription type.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="intercom-connector.detach_contact_subscription",
    effects=["intercom.contact.unsubscribed"],
)
async def detach_contact_subscription(ctx, params: DetachContactSubscriptionParams) -> ActionResult:
    """Opt a contact out of a subscription type."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await ic.request(
            ctx, "DELETE", f"/contacts/{params.contact_id}/subscriptions/{params.subscription_type_id}",
            conn["access_token"], conn["region"],
        )
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_DETACH_SUB_FAILED")
    return ActionResult.success(DeleteResult(id=params.subscription_type_id, deleted=True), summary="Contact unsubscribed.")
