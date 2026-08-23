"""Data Attributes (custom fields), Data Events, Data Export, Reporting Data
Export, Away Status Reasons. Built on intercom_client.py / schemas.py, same
shape as handlers_admin.py -- async, full @chat.function metadata,
ActionResult.success()/.error().
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import intercom_client as ic
from app import chat
from handlers_connection import resolve_or_error
from schemas import (
    ListDataAttributesParams, DataAttribute, DataAttributeList,
    CreateDataAttributeParams,
    CreateDataEventParams, ListDataEventsParams, DataEvent, DataEventList,
    CreateDataExportParams, DataExportJob, GetDataExportParams,
    CreateReportingExportParams,
    ListAwayStatusReasonsParams, AwayStatusReason, AwayStatusReasonList,
)


@chat.function(
    "list_data_attributes",
    "List custom/default data attributes defined for contacts, companies, or conversations.",
    action_type="read",
    chain_callable=True,
    data_model=DataAttributeList,
)
async def list_data_attributes(ctx, params: ListDataAttributesParams) -> ActionResult:
    """List data attributes for one model."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", "/data_attributes", conn["access_token"], conn["region"], params={"model": params.model})
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_LIST_ATTRS_FAILED")
    items = [
        DataAttribute(name=a.get("name", ""), full_name=a.get("full_name", ""), label=a.get("label", "") or "",
                      data_type=a.get("data_type", ""), model=a.get("model", ""), custom=bool(a.get("custom")))
        for a in (body.get("data") or [])
    ]
    return ActionResult.success(DataAttributeList(items=items), summary=f"{len(items)} attributes for '{params.model}'.")


@chat.function(
    "create_data_attribute",
    "Create a new custom data attribute (field) on contacts or companies.",
    action_type="write",
    chain_callable=True,
    data_model=DataAttribute,
    event="intercom-connector.create_data_attribute",
    effects=["intercom.data_attribute.created"],
)
async def create_data_attribute(ctx, params: CreateDataAttributeParams) -> ActionResult:
    """Create a new custom data attribute."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    body = {"name": params.name, "model": params.model, "data_type": params.data_type}
    if params.description:
        body["description"] = params.description
    try:
        result = await ic.request(ctx, "POST", "/data_attributes", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_CREATE_ATTR_FAILED")
    return ActionResult.success(
        DataAttribute(name=result.get("name", ""), full_name=result.get("full_name", ""), label=result.get("label", "") or "",
                      data_type=result.get("data_type", ""), model=result.get("model", ""), custom=bool(result.get("custom"))),
        summary=f"Created data attribute '{params.name}' on {params.model}.",
    )


@chat.function(
    "create_data_event",
    "Track a custom event for a contact (e.g. 'invited-friend', 'completed-onboarding') with optional metadata.",
    action_type="write",
    chain_callable=True,
    data_model=DataEvent,
    event="intercom-connector.create_data_event",
    effects=["intercom.data_event.created"],
)
async def create_data_event(ctx, params: CreateDataEventParams) -> ActionResult:
    """Track a custom data event."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    if not (params.contact_id or params.email):
        return ActionResult.error("Provide contact_id or email.", code="INTERCOM_MISSING_TARGET")
    import time
    body: dict = {"event_name": params.event_name, "created_at": int(time.time())}
    if params.contact_id:
        body["id"] = params.contact_id
    if params.email:
        body["email"] = params.email
    if params.metadata:
        body["metadata"] = params.metadata
    try:
        await ic.request(ctx, "POST", "/events", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_CREATE_EVENT_FAILED")
    return ActionResult.success(
        DataEvent(event_name=params.event_name, created_at=body["created_at"], contact_id=params.contact_id, email=params.email),
        summary=f"Tracked event '{params.event_name}'.",
    )


@chat.function(
    "create_data_export",
    "Enqueue a bulk Data Export job for a date range (contacts/conversations archive). Returns a job to poll with get_data_export.",
    action_type="write",
    chain_callable=True,
    data_model=DataExportJob,
    event="intercom-connector.create_data_export",
    effects=["intercom.data_export.created"],
)
async def create_data_export(ctx, params: CreateDataExportParams) -> ActionResult:
    """Enqueue a Data Export job."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    body = {"created_at_after": params.created_at_after, "created_at_before": params.created_at_before}
    try:
        result = await ic.request(ctx, "POST", "/export/content/data", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_CREATE_EXPORT_FAILED")
    return ActionResult.success(
        DataExportJob(job_identifier=result.get("job_identifier", ""), status=result.get("status", ""),
                      download_url=result.get("download_url", "") or "", download_expires_at=result.get("download_expires_at") or 0),
        summary="Data export job enqueued.",
    )


@chat.function(
    "get_data_export",
    "Check the status of a Data Export job and get its download URL once ready.",
    action_type="read",
    chain_callable=True,
    data_model=DataExportJob,
)
async def get_data_export(ctx, params: GetDataExportParams) -> ActionResult:
    """Check a Data Export job's status."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        result = await ic.request(ctx, "GET", f"/export/content/data/{params.job_identifier}", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_GET_EXPORT_FAILED")
    return ActionResult.success(
        DataExportJob(job_identifier=result.get("job_identifier", ""), status=result.get("status", ""),
                      download_url=result.get("download_url", "") or "", download_expires_at=result.get("download_expires_at") or 0),
        summary=f"Export job status: {result.get('status', 'unknown')}.",
    )


@chat.function(
    "create_reporting_export",
    "Enqueue a Reporting Data Export job for a specific dataset/attribute set and date range -- Intercom's newer analytics-grade export.",
    action_type="write",
    chain_callable=True,
    data_model=DataExportJob,
    event="intercom-connector.create_reporting_export",
    effects=["intercom.reporting_export.created"],
)
async def create_reporting_export(ctx, params: CreateReportingExportParams) -> ActionResult:
    """Enqueue a Reporting Data Export job."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    body = {
        "data_set_identifier": params.data_set_identifier,
        "attribute_ids": params.attribute_ids,
        "start_time": params.start_time,
        "end_time": params.end_time,
    }
    try:
        result = await ic.request(ctx, "POST", "/export/reporting_data/enqueue", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_CREATE_REPORTING_EXPORT_FAILED")
    return ActionResult.success(
        DataExportJob(job_identifier=result.get("job_identifier", ""), status=result.get("status", "")),
        summary="Reporting data export job enqueued.",
    )


@chat.function(
    "list_away_status_reasons",
    "List the away status reasons admins can select when setting themselves away.",
    action_type="read",
    chain_callable=True,
    data_model=AwayStatusReasonList,
)
async def list_away_status_reasons(ctx, params: ListAwayStatusReasonsParams) -> ActionResult:
    """List away status reasons."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", "/away_status_reasons", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_LIST_AWAY_REASONS_FAILED")
    items = [
        AwayStatusReason(id=str(r.get("id", "")), label=r.get("label", ""), emoji=r.get("emoji", "") or "")
        for r in (body.get("data") or body.get("list") or [])
    ]
    return ActionResult.success(AwayStatusReasonList(items=items), summary=f"{len(items)} away status reasons.")
