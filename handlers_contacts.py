"""Contacts: list/get/create/update/delete, plus tags/notes/companies
attach-detach on a contact. Built on intercom_client.py / schemas.py, same
shape as PagerDuty Connector's handlers_*.py -- async, full @chat.function
metadata, ActionResult.success()/.error().
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import intercom_client as ic
from app import chat
from handlers_connection import resolve_or_error
from schemas import (
    ListContactsParams, Contact, ContactList,
    GetContactParams, CreateContactParams, UpdateContactParams,
    DeleteContactParams, DeleteResult,
    TagContactParams as AttachTagToContactParams,
    UntagContactParams as DetachTagFromContactParams,
    AttachContactToCompanyParams, DetachContactFromCompanyParams,
    ListContactCompaniesParams, CompanyList, Company,
)


def _contact_from(raw: dict) -> Contact:
    loc = raw.get("location") or {}
    return Contact(
        id=raw.get("id", ""), external_id=raw.get("external_id", ""),
        role=raw.get("role", ""), email=raw.get("email", ""),
        phone=raw.get("phone", ""), name=raw.get("name", ""),
        avatar=(raw.get("avatar") or {}).get("image_url", "") if isinstance(raw.get("avatar"), dict) else "",
        created_at=raw.get("created_at", 0), updated_at=raw.get("updated_at", 0),
        last_seen_at=raw.get("last_seen_at") or 0,
        signed_up_at=raw.get("signed_up_at") or 0,
        city=loc.get("city", ""), country=loc.get("country", ""),
        tags=[t.get("name", "") for t in (raw.get("tags") or {}).get("data", [])] if isinstance(raw.get("tags"), dict) else [],
    )


@chat.function(
    "list_contacts",
    "List contacts (people and leads) in the connected Intercom workspace, cursor-paginated.",
    action_type="read",
    chain_callable=True,
    data_model=ContactList,
)
async def list_contacts(ctx, params: ListContactsParams) -> ActionResult:
    """List contacts in the connected Intercom workspace."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    q = {"per_page": params.per_page}
    if params.starting_after:
        q["starting_after"] = params.starting_after
    try:
        body = await ic.request(ctx, "GET", "/contacts", conn["access_token"], conn["region"], params=q)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_LIST_CONTACTS_FAILED")
    items = [_contact_from(c) for c in body.get("data", [])]
    pages = body.get("pages") or {}
    nxt = pages.get("next")
    next_cursor = (nxt.get("starting_after") if isinstance(nxt, dict) else nxt) or ""
    return ActionResult.success(
        ContactList(items=items, next_cursor=next_cursor, total_count=body.get("total_count", len(items))),
        summary=f"{len(items)} contact(s) fetched.",
    )


@chat.function(
    "get_contact",
    "Read one contact in full, including emails/phones/tags/companies and activity timestamps.",
    action_type="read",
    chain_callable=True,
    data_model=Contact,
)
async def get_contact(ctx, params: GetContactParams) -> ActionResult:
    """Read one contact in full by id."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", f"/contacts/{params.contact_id}", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_GET_CONTACT_FAILED")
    return ActionResult.success(_contact_from(body), summary=f"Contact '{body.get('name') or body.get('email') or params.contact_id}'.")


@chat.function(
    "create_contact",
    "Create a new contact (user or lead) with email/phone/external_id/name.",
    action_type="write",
    chain_callable=True,
    data_model=Contact,
    event="intercom-connector.create_contact",
    effects=["intercom.contact.created"],
)
async def create_contact(ctx, params: CreateContactParams) -> ActionResult:
    """Create a new contact."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    if not (params.email or params.phone or params.external_id):
        return ActionResult.error("Provide at least one of: email, phone, external_id.", code="INTERCOM_MISSING_FIELD")
    body = {"role": params.role}
    if params.email:
        body["email"] = params.email
    if params.phone:
        body["phone"] = params.phone
    if params.external_id:
        body["external_id"] = params.external_id
    if params.name:
        body["name"] = params.name
    try:
        result = await ic.request(ctx, "POST", "/contacts", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_CREATE_CONTACT_FAILED")
    return ActionResult.success(_contact_from(result), summary=f"Created contact '{result.get('name') or result.get('email') or result.get('id')}'.")


@chat.function(
    "update_contact",
    "Update selected fields of an existing contact. Only given fields change.",
    action_type="write",
    chain_callable=True,
    data_model=Contact,
    event="intercom-connector.update_contact",
    effects=["intercom.contact.updated"],
)
async def update_contact(ctx, params: UpdateContactParams) -> ActionResult:
    """Update selected fields of an existing contact."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    body = {}
    if params.email:
        body["email"] = params.email
    if params.phone:
        body["phone"] = params.phone
    if params.name:
        body["name"] = params.name
    if not body:
        return ActionResult.error("Provide at least one field to update.", code="INTERCOM_NO_FIELDS")
    try:
        result = await ic.request(ctx, "PUT", f"/contacts/{params.contact_id}", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_UPDATE_CONTACT_FAILED")
    return ActionResult.success(_contact_from(result), summary=f"Updated contact '{params.contact_id}'.")


@chat.function(
    "delete_contact",
    "Permanently delete a contact. Cannot be undone through the API.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="intercom-connector.delete_contact",
    effects=["intercom.contact.deleted"],
)
async def delete_contact(ctx, params: DeleteContactParams) -> ActionResult:
    """Permanently delete a contact."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await ic.request(ctx, "DELETE", f"/contacts/{params.contact_id}", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_DELETE_CONTACT_FAILED")
    return ActionResult.success(DeleteResult(id=params.contact_id, deleted=True), summary="Contact deleted.")


@chat.function(
    "attach_tag_to_contact",
    "Attach an existing tag to a contact by tag id.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="intercom-connector.attach_tag_to_contact",
    effects=["intercom.contact.tagged"],
)
async def attach_tag_to_contact(ctx, params: AttachTagToContactParams) -> ActionResult:
    """Attach a tag to a contact."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await ic.request(ctx, "POST", f"/contacts/{params.contact_id}/tags", conn["access_token"], conn["region"], json_body={"id": params.tag_id})
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_TAG_CONTACT_FAILED")
    return ActionResult.success(DeleteResult(id=params.contact_id, deleted=False), summary="Tag attached to contact.")


@chat.function(
    "detach_tag_from_contact",
    "Remove a tag from a contact by tag id.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="intercom-connector.detach_tag_from_contact",
    effects=["intercom.contact.untagged"],
)
async def detach_tag_from_contact(ctx, params: DetachTagFromContactParams) -> ActionResult:
    """Remove a tag from a contact."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await ic.request(ctx, "DELETE", f"/contacts/{params.contact_id}/tags/{params.tag_id}", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_UNTAG_CONTACT_FAILED")
    return ActionResult.success(DeleteResult(id=params.contact_id, deleted=False), summary="Tag removed from contact.")


@chat.function(
    "attach_contact_to_company",
    "Attach a contact to a company by company id.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="intercom-connector.attach_contact_to_company",
    effects=["intercom.contact.company_attached"],
)
async def attach_contact_to_company(ctx, params: AttachContactToCompanyParams) -> ActionResult:
    """Attach a contact to a company."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await ic.request(ctx, "POST", f"/contacts/{params.contact_id}/companies", conn["access_token"], conn["region"], json_body={"id": params.company_id})
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_ATTACH_COMPANY_FAILED")
    return ActionResult.success(DeleteResult(id=params.contact_id, deleted=False), summary="Contact attached to company.")


@chat.function(
    "detach_contact_from_company",
    "Remove a contact from a company.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="intercom-connector.detach_contact_from_company",
    effects=["intercom.contact.company_detached"],
)
async def detach_contact_from_company(ctx, params: DetachContactFromCompanyParams) -> ActionResult:
    """Remove a contact from a company."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await ic.request(ctx, "DELETE", f"/contacts/{params.contact_id}/companies/{params.company_id}", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_DETACH_COMPANY_FAILED")
    return ActionResult.success(DeleteResult(id=params.contact_id, deleted=False), summary="Contact removed from company.")


@chat.function(
    "list_contact_companies",
    "List the companies a contact belongs to.",
    action_type="read",
    chain_callable=True,
    data_model=CompanyList,
)
async def list_contact_companies(ctx, params: ListContactCompaniesParams) -> ActionResult:
    """List companies attached to a contact."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", f"/contacts/{params.contact_id}/companies", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_LIST_CONTACT_COMPANIES_FAILED")
    items = [Company(id=c.get("id", ""), company_id=c.get("company_id", ""), name=c.get("name", "")) for c in (body.get("data") or [])]
    return ActionResult.success(CompanyList(items=items), summary=f"{len(items)} companies for this contact.")
