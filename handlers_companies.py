"""Companies: list/get/create-or-update(upsert)/delete, list contacts of a
company. Built on intercom_client.py / schemas.py, same shape as
handlers_contacts.py -- async, full @chat.function metadata,
ActionResult.success()/.error().
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import intercom_client as ic
from app import chat
from handlers_connection import resolve_or_error
from schemas import (
    ListCompaniesParams, Company, CompanyList,
    GetCompanyParams, CreateOrUpdateCompanyParams, DeleteCompanyParams,
    DeleteResult, ListCompanyContactsParams, Contact, ContactList,
)


def _company_from(raw: dict) -> Company:
    return Company(
        id=raw.get("id", ""), company_id=raw.get("company_id", ""),
        name=raw.get("name", ""), website=raw.get("website", ""),
        industry=raw.get("industry", ""),
        monthly_spend=raw.get("monthly_spend") or 0.0,
        size=raw.get("size") or 0, plan=(raw.get("plan") or {}).get("name", "") if isinstance(raw.get("plan"), dict) else "",
        created_at=raw.get("created_at", 0), updated_at=raw.get("updated_at", 0),
        user_count=raw.get("user_count") or 0,
        session_count=raw.get("session_count") or 0,
    )


@chat.function(
    "list_companies",
    "List companies in the connected Intercom workspace.",
    action_type="read",
    chain_callable=True,
    data_model=CompanyList,
)
async def list_companies(ctx, params: ListCompaniesParams) -> ActionResult:
    """List companies, page-paginated."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", "/companies", conn["access_token"], conn["region"], params={"page": params.page, "per_page": params.per_page})
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_LIST_COMPANIES_FAILED")
    items = [_company_from(c) for c in (body.get("data") or [])]
    return ActionResult.success(CompanyList(items=items), summary=f"{len(items)} companies.")


@chat.function(
    "get_company",
    "Read one company in full, including user/session counts and plan.",
    action_type="read",
    chain_callable=True,
    data_model=Company,
)
async def get_company(ctx, params: GetCompanyParams) -> ActionResult:
    """Read one company by id."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", f"/companies/{params.company_id}", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_GET_COMPANY_FAILED")
    return ActionResult.success(_company_from(body), summary=f"Company '{body.get('name') or params.company_id}'.")


@chat.function(
    "create_or_update_company",
    "Create a new company, or update an existing one if company_id already exists (Intercom upserts by company_id).",
    action_type="write",
    chain_callable=True,
    data_model=Company,
    event="intercom-connector.create_or_update_company",
    effects=["intercom.company.upserted"],
)
async def create_or_update_company(ctx, params: CreateOrUpdateCompanyParams) -> ActionResult:
    """Create or update (upsert) a company by company_id."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    body: dict = {"company_id": params.company_id}
    if params.name:
        body["name"] = params.name
    if params.website:
        body["website"] = params.website
    if params.industry:
        body["industry"] = params.industry
    if params.monthly_spend is not None:
        body["monthly_spend"] = params.monthly_spend
    if params.size is not None:
        body["size"] = params.size
    if params.plan:
        body["plan"] = params.plan
    try:
        result = await ic.request(ctx, "POST", "/companies", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_UPSERT_COMPANY_FAILED")
    return ActionResult.success(_company_from(result), summary=f"Company '{result.get('name') or params.company_id}' saved.")


@chat.function(
    "delete_company",
    "Permanently delete a company. Cannot be undone.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="intercom-connector.delete_company",
    effects=["intercom.company.deleted"],
)
async def delete_company(ctx, params: DeleteCompanyParams) -> ActionResult:
    """Permanently delete a company by id."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await ic.request(ctx, "DELETE", f"/companies/{params.company_id}", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_DELETE_COMPANY_FAILED")
    return ActionResult.success(DeleteResult(id=params.company_id, deleted=True), summary="Company deleted.")


@chat.function(
    "list_company_contacts",
    "List the contacts belonging to one company.",
    action_type="read",
    chain_callable=True,
    data_model=ContactList,
)
async def list_company_contacts(ctx, params: ListCompanyContactsParams) -> ActionResult:
    """List contacts attached to a company."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", f"/companies/{params.company_id}/contacts", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_LIST_COMPANY_CONTACTS_FAILED")
    from handlers_contacts import _contact_from
    items = [_contact_from(c) for c in (body.get("data") or [])]
    return ActionResult.success(ContactList(items=items), summary=f"{len(items)} contacts for this company.")
