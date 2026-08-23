"""Value-add reports: aggregated workspace health audit, stale-open-
conversation finder. Built on intercom_client.py / schemas.py, same shape
as PagerDuty Connector's / AppFolio Connector's audit handlers -- async,
full @chat.function metadata, ActionResult.success()/.error().
"""
from __future__ import annotations

import time

from imperal_sdk import ActionResult

import intercom_client as ic
from app import chat
from handlers_connection import resolve_or_error
from schemas import (
    AuditWorkspaceParams, AuditReport, AuditRow,
    StaleConversationsParams, StaleConversationsResult,
)


def _row_from(raw: dict, now: float, reason: str = "") -> AuditRow:
    waiting_since = raw.get("waiting_since") or raw.get("created_at") or 0
    waiting_hours = round((now - waiting_since) / 3600.0, 1) if waiting_since else 0.0
    return AuditRow(
        conversation_id=raw.get("id", ""), title=raw.get("title", "") or "(no title)",
        state=raw.get("state", ""), priority=raw.get("priority", "") or "not_priority",
        waiting_hours=waiting_hours, admin_assignee_id=str(raw.get("admin_assignee_id") or ""),
        reason=reason,
    )


@chat.function(
    "audit_workspace_health",
    "Build one aggregated health report across recent conversations on the connected Intercom workspace: open/unassigned/stale/priority/snoozed counts, so you can spot support backlog at a glance.",
    action_type="read",
    chain_callable=True,
    data_model=AuditReport,
)
async def audit_workspace_health(ctx, params: AuditWorkspaceParams) -> ActionResult:
    """Build one aggregated health report across recent conversations."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    sample = max(1, min(params.sample_size, 150))
    try:
        body = await ic.request(
            ctx, "GET", "/conversations", conn["access_token"], conn["region"],
            params={"per_page": min(sample, 150)},
        )
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_AUDIT_FAILED")
    convs = (body.get("conversations") or [])[:sample]
    now = time.time()
    open_count = unassigned_open = stale_open = priority_open = snoozed_count = closed_count = 0
    rows: list[AuditRow] = []
    for c in convs:
        state = c.get("state", "")
        if state == "open":
            open_count += 1
            reasons = []
            if not c.get("admin_assignee_id"):
                unassigned_open += 1
                reasons.append("unassigned")
            waiting_since = c.get("waiting_since") or c.get("created_at") or 0
            if waiting_since and (now - waiting_since) / 3600.0 >= 24:
                stale_open += 1
                reasons.append("stale (24h+)")
            if c.get("priority") == "priority":
                priority_open += 1
                reasons.append("priority")
            if reasons:
                rows.append(_row_from(c, now, reason=", ".join(reasons)))
        elif state == "snoozed":
            snoozed_count += 1
        elif state == "closed":
            closed_count += 1
    summary = (
        f"{len(convs)} sampled: {open_count} open ({unassigned_open} unassigned, "
        f"{stale_open} stale 24h+, {priority_open} priority), {snoozed_count} snoozed, {closed_count} closed."
    )
    return ActionResult.success(
        AuditReport(
            sampled=len(convs), open_count=open_count, unassigned_open_count=unassigned_open,
            stale_open_count=stale_open, priority_open_count=priority_open,
            snoozed_count=snoozed_count, closed_count=closed_count, rows=rows, summary=summary,
        ),
        summary=summary,
    )


@chat.function(
    "find_stale_conversations",
    "Scan recent open conversations and flag every one waiting on a reply for at least a given number of hours -- catches support backlog before customers escalate.",
    action_type="read",
    chain_callable=True,
    data_model=StaleConversationsResult,
)
async def find_stale_conversations(ctx, params: StaleConversationsParams) -> ActionResult:
    """Flag open conversations waiting past a threshold."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    sample = max(1, min(params.sample_size, 150))
    threshold_hours = params.min_hours_open if params.min_hours_open > 0 else 24.0
    try:
        body = await ic.request(
            ctx, "POST", "/conversations/search", conn["access_token"], conn["region"],
            json_body={"query": {"field": "state", "operator": "=", "value": "open"}},
        )
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_STALE_SCAN_FAILED")
    convs = (body.get("conversations") or [])[:sample]
    now = time.time()
    rows: list[AuditRow] = []
    for c in convs:
        waiting_since = c.get("waiting_since") or c.get("created_at") or 0
        if not waiting_since:
            continue
        hours = (now - waiting_since) / 3600.0
        if hours >= threshold_hours:
            rows.append(_row_from(c, now, reason=f"waiting {round(hours, 1)}h (threshold {threshold_hours}h)"))
    summary = f"{len(rows)} of {len(convs)} scanned open conversations have waited {threshold_hours}h+ without a reply."
    return ActionResult.success(
        StaleConversationsResult(scanned=len(convs), stale_count=len(rows), rows=rows, summary=summary),
        summary=summary,
    )
