"""Pydantic params models + SDL entity contracts for Intercom Connector.

All params models are module-scope (V17 federal invariant, same rule as
PagerDuty Connector / MuleSoft Connector's schemas.py). Organized by domain
to match handlers_*.py split (connection, contacts, companies,
conversations, tickets, content/help-center, internal-content/news,
messages, admin/teams, data (attributes/events/export), tags/segments,
Fin AI, audit/value-add reports).
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from imperal_sdk import sdl


class NoParams(BaseModel):
    """Explicit empty params model -- V17 disallows untyped handlers."""
    pass


# ──────────────────────────────────────────────────────────────────────────
# Connection
# ──────────────────────────────────────────────────────────────────────────


class ConnectIntercomParams(BaseModel):
    access_token: str = Field(
        "",
        description="Your Intercom private app Access Token (Developer Hub > your app > Configure > Authentication).",
    )
    region: str = Field(
        "us",
        description="Data hosting region of your Intercom workspace: 'us', 'eu', or 'au'. Using the wrong region will make every call fail with an auth-looking error.",
    )
    label: str = Field("", description="Optional friendly name for this connection.")


class IntercomConnection(sdl.Entity):
    id: str = ""
    title: str = ""
    connected: bool = False
    detail: str = ""
    region: str = ""
    workspace_name: str = ""


class IntercomConnectionList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[IntercomConnection] = Field(default_factory=list)


class DisconnectIntercomParams(BaseModel):
    connection_id: str = Field("", description="Connection id to disconnect (from list_connections). Leave empty if only one is connected.")


class DeleteResult(sdl.Entity):
    title: str = ""
    id: str = ""
    deleted: bool = False


# ──────────────────────────────────────────────────────────────────────────
# Contacts
# ──────────────────────────────────────────────────────────────────────────


class ListContactsParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    starting_after: str = Field("", description="Pagination cursor from a previous list_contacts call.")
    per_page: int = Field(50, description="How many contacts per page (max 150).")


class GetContactParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    contact_id: str = Field(..., description="Intercom contact id.")


class CreateContactParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    role: str = Field("user", description="'user' (identified customer) or 'lead' (unidentified prospect).")
    email: str = Field("", description="Contact's email address.")
    phone: str = Field("", description="Contact's phone number, e.g. +15551234567.")
    external_id: str = Field("", description="Your own unique id for this contact in your system.")
    name: str = Field("", description="Contact's full name.")


class UpdateContactParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    contact_id: str = Field(..., description="Intercom contact id to update.")
    email: str = Field("", description="New email address (leave empty to keep unchanged).")
    phone: str = Field("", description="New phone number (leave empty to keep unchanged).")
    name: str = Field("", description="New full name (leave empty to keep unchanged).")
    unsubscribed_from_emails: bool | None = Field(None, description="Set the contact's email subscription state, or leave unset to keep unchanged.")


class DeleteContactParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    contact_id: str = Field(..., description="Intercom contact id to permanently delete.")


class ArchiveContactParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    contact_id: str = Field(..., description="Intercom contact id to archive (soft-delete, reversible).")
    unarchive: bool = Field(False, description="Set true to unarchive instead of archive.")


class MergeContactsParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    lead_id: str = Field(..., description="Contact id of the 'lead' (unidentified) record to merge from.")
    user_id: str = Field(..., description="Contact id of the 'user' (identified) record to merge into.")


class SearchContactsParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    field: str = Field("email", description="Contact field to filter on, e.g. 'email', 'name', 'role'.")
    operator: str = Field("=", description="Comparison operator: '=', '!=', '>', '<', '~', '!~', 'IN', 'NIN'.")
    value: str = Field(..., description="Value to compare the field against.")


class Contact(sdl.Entity):
    title: str = ""
    id: str = ""
    role: str = ""
    email: str = ""
    phone: str = ""
    name: str = ""
    external_id: str = ""
    created_at: int = 0
    updated_at: int = 0
    last_seen_at: int = 0
    signed_up_at: int = 0
    unsubscribed_from_emails: bool = False
    location: str = ""
    companies_count: int = 0
    tags: list[str] = Field(default_factory=list)


class ContactList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[Contact] = Field(default_factory=list)
    next_cursor: str = ""
    total_count: int = 0


class ListContactNotesParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    contact_id: str = Field(..., description="Intercom contact id whose notes to list.")


class CreateContactNoteParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    contact_id: str = Field(..., description="Intercom contact id to attach the note to.")
    body: str = Field(..., description="Note text (plain text or simple HTML).")
    admin_id: str = Field("", description="Admin id the note should be attributed to (leave empty to use the app's default admin).")


class NoteEntry(sdl.Entity):
    title: str = ""
    id: str = ""
    body: str = ""
    created_at: int = 0
    author_name: str = ""


class NoteList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[NoteEntry] = Field(default_factory=list)


class TagContactParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    contact_id: str = Field(..., description="Intercom contact id to tag.")
    tag_id: str = Field(..., description="Tag id to attach (from list_tags).")


class UntagContactParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    contact_id: str = Field(..., description="Intercom contact id to untag.")
    tag_id: str = Field(..., description="Tag id to remove (from list_tags).")


class AttachContactToCompanyParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    contact_id: str = Field(..., description="Intercom contact id.")
    company_id: str = Field(..., description="Intercom company id (from list_companies).")


class DetachContactFromCompanyParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    contact_id: str = Field(..., description="Intercom contact id.")
    company_id: str = Field(..., description="Intercom company id to detach.")


class ListContactCompaniesParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    contact_id: str = Field(..., description="Intercom contact id whose companies to list.")


# ──────────────────────────────────────────────────────────────────────────
# Companies
# ──────────────────────────────────────────────────────────────────────────


class ListCompaniesParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    page: int = Field(1, description="Page number to fetch.")
    per_page: int = Field(50, description="How many companies per page (max 150).")


class GetCompanyParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    company_id: str = Field(..., description="Intercom company id.")


class CreateOrUpdateCompanyParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    company_id: str = Field(..., description="Your own unique id for this company (Intercom upserts by this).")
    name: str = Field("", description="Company display name.")
    website: str = Field("", description="Company website URL.")
    industry: str = Field("", description="Company industry.")
    monthly_spend: float | None = Field(None, description="Monthly spend value for this company, if tracked.")
    size: int | None = Field(None, description="Number of employees, if tracked.")
    plan: str = Field("", description="Subscription plan name, if tracked.")


class DeleteCompanyParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    company_id: str = Field(..., description="Intercom company id to permanently delete.")


class Company(sdl.Entity):
    title: str = ""
    id: str = ""
    company_id: str = ""
    name: str = ""
    website: str = ""
    industry: str = ""
    monthly_spend: float = 0.0
    session_count: int = 0
    user_count: int = 0
    created_at: int = 0
    updated_at: int = 0
    plan: str = ""
    size: int = 0


class CompanyList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[Company] = Field(default_factory=list)
    total_count: int = 0


class ListCompanyContactsParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    company_id: str = Field(..., description="Intercom company id whose contacts to list.")


class ListCompanySegmentsParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    company_id: str = Field(..., description="Intercom company id whose segments to list.")


# ──────────────────────────────────────────────────────────────────────────
# Conversations
# ──────────────────────────────────────────────────────────────────────────


class ListConversationsParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    starting_after: str = Field("", description="Pagination cursor from a previous list_conversations call.")
    per_page: int = Field(20, description="How many conversations per page (max 150).")


class GetConversationParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    conversation_id: str = Field(..., description="Intercom conversation id.")


class SearchConversationsParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    field: str = Field("state", description="Conversation field to filter on, e.g. 'state', 'source.author.id', 'created_at'.")
    operator: str = Field("=", description="Comparison operator: '=', '!=', '>', '<', 'IN', 'NIN'.")
    value: str = Field(..., description="Value to compare the field against.")


class ReplyConversationParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    conversation_id: str = Field(..., description="Intercom conversation id to reply to.")
    admin_id: str = Field(..., description="Admin id sending this reply as (required for admin-authored replies).")
    body: str = Field(..., description="Reply message body (HTML allowed).")
    message_type: str = Field("comment", description="'comment' (visible reply) or 'note' (internal note).")


class ManageConversationParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    conversation_id: str = Field(..., description="Intercom conversation id to manage.")
    admin_id: str = Field(..., description="Admin id performing this action.")
    action: str = Field(..., description="'close', 'snooze', 'open', or 'assign'.")
    snoozed_until: int = Field(0, description="Unix timestamp to snooze until (only used when action='snooze').")
    assignee_id: str = Field("", description="Admin or team id to assign to (only used when action='assign').")


class AddConversationNoteParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    conversation_id: str = Field(..., description="Intercom conversation id to add an internal note to.")
    admin_id: str = Field(..., description="Admin id adding this note.")
    body: str = Field(..., description="Internal note body (HTML allowed), visible only to teammates.")


class AttachContactToConversationParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    conversation_id: str = Field(..., description="Intercom conversation id.")
    contact_id: str = Field(..., description="Intercom contact id to add as a participant.")


class DetachContactFromConversationParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    conversation_id: str = Field(..., description="Intercom conversation id.")
    contact_id: str = Field(..., description="Intercom contact id to remove.")
    admin_id: str = Field(..., description="Admin id performing this removal.")


class TagConversationParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    conversation_id: str = Field(..., description="Intercom conversation id to tag.")
    tag_id: str = Field(..., description="Tag id to attach (from list_tags).")
    admin_id: str = Field(..., description="Admin id performing this action.")


class UntagConversationParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    conversation_id: str = Field(..., description="Intercom conversation id to untag.")
    tag_id: str = Field(..., description="Tag id to remove.")


class ConversationPart(sdl.Entity):
    title: str = ""
    id: str = ""
    part_type: str = ""
    body: str = ""
    author_type: str = ""
    author_name: str = ""
    created_at: int = 0


class Conversation(sdl.Entity):
    id: str = ""
    title: str = ""
    state: str = ""
    open: bool = False
    read: bool = False
    priority: str = ""
    created_at: int = 0
    updated_at: int = 0
    waiting_since: int = 0
    snoozed_until: int = 0
    admin_assignee_id: str = ""
    team_assignee_id: str = ""
    source_body: str = ""
    source_author_type: str = ""
    tags: list[str] = Field(default_factory=list)
    parts: list[ConversationPart] = Field(default_factory=list)


class ConversationList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[Conversation] = Field(default_factory=list)
    next_cursor: str = ""
    total_count: int = 0


# ──────────────────────────────────────────────────────────────────────────
# Tickets
# ──────────────────────────────────────────────────────────────────────────


class ListTicketsParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    starting_after: str = Field("", description="Pagination cursor from a previous list_tickets call.")
    per_page: int = Field(20, description="How many tickets per page (max 60).")


class GetTicketParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    ticket_id: str = Field(..., description="Intercom ticket id.")


class CreateTicketParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    ticket_type_id: str = Field(..., description="Ticket type id this ticket belongs to (from list_ticket_types).")
    contact_id: str = Field(..., description="Intercom contact id this ticket is raised for.")
    title: str = Field("", description="Ticket title/subject (maps to the ticket type's default title attribute if left empty).")
    description: str = Field("", description="Ticket description body.")


class UpdateTicketParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    ticket_id: str = Field(..., description="Intercom ticket id to update.")
    state: str = Field("", description="New ticket state id/category, e.g. 'in_progress', 'resolved' (leave empty to keep unchanged).")
    title: str = Field("", description="New title (leave empty to keep unchanged).")


class ReplyTicketParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    ticket_id: str = Field(..., description="Intercom ticket id to reply to.")
    admin_id: str = Field(..., description="Admin id sending this reply as.")
    body: str = Field(..., description="Reply message body.")
    message_type: str = Field("comment", description="'comment' (visible reply) or 'note' (internal note).")


class Ticket(sdl.Entity):
    id: str = ""
    ticket_type_id: str = ""
    ticket_type_name: str = ""
    title: str = ""
    description: str = ""
    state: str = ""
    category: str = ""
    created_at: int = 0
    updated_at: int = 0
    contact_id: str = ""
    admin_assignee_id: str = ""


class TicketList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[Ticket] = Field(default_factory=list)
    next_cursor: str = ""
    total_count: int = 0


class ListTicketTypesParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")


class CreateTicketTypeParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    name: str = Field(..., description="Ticket type name, e.g. 'Bug Report', 'Feature Request'.")
    description: str = Field("", description="Ticket type description.")
    category: str = Field("Customer", description="'Customer', 'Back-office', or 'Tracker'.")
    icon: str = Field("🎫", description="Emoji icon for this ticket type.")


class TicketType(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    description: str = ""
    category: str = ""
    icon: str = ""
    archived: bool = False


class TicketTypeList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[TicketType] = Field(default_factory=list)


class ListTicketStatesParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")


class TicketState(sdl.Entity):
    title: str = ""
    id: str = ""
    category: str = ""
    label: str = ""
    is_default: bool = False


class TicketStateList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[TicketState] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────
# Articles / Help Center
# ──────────────────────────────────────────────────────────────────────────


class ListArticlesParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    page: int = Field(1, description="Page number to fetch.")
    per_page: int = Field(50, description="How many articles per page (max 250).")


class GetArticleParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    article_id: str = Field(..., description="Intercom article id.")


class CreateArticleParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    title: str = Field(..., description="Article title.")
    body: str = Field(..., description="Article body (HTML).")
    author_id: str = Field(..., description="Admin id to attribute this article to.")
    state: str = Field("draft", description="'draft' or 'published'.")
    parent_id: str = Field("", description="Collection or section id this article belongs under, if any.")


class UpdateArticleParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    article_id: str = Field(..., description="Intercom article id to update.")
    title: str = Field("", description="New title (leave empty to keep unchanged).")
    body: str = Field("", description="New body HTML (leave empty to keep unchanged).")
    state: str = Field("", description="New state: 'draft' or 'published' (leave empty to keep unchanged).")


class DeleteArticleParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    article_id: str = Field(..., description="Intercom article id to permanently delete.")


class Article(sdl.Entity):
    id: str = ""
    title: str = ""
    description: str = ""
    body: str = ""
    state: str = ""
    author_id: str = ""
    url: str = ""
    created_at: int = 0
    updated_at: int = 0


class ArticleList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[Article] = Field(default_factory=list)
    total_count: int = 0


class ListHelpCenterCollectionsParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")


class CreateHelpCenterCollectionParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    name: str = Field(..., description="Collection name shown to end-users in the Help Center.")
    description: str = Field("", description="Collection description.")
    parent_id: str = Field("", description="Parent collection id, if nesting this under another collection.")


class HelpCenterCollection(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    description: str = ""
    icon: str = ""
    url: str = ""
    order: int = 0


class HelpCenterCollectionList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[HelpCenterCollection] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────
# News
# ──────────────────────────────────────────────────────────────────────────


class ListNewsItemsParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")


class CreateNewsItemParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    title: str = Field(..., description="News item title.")
    body: str = Field(..., description="News item body (HTML).")
    sender_id: str = Field(..., description="Admin id this news item is sent from.")
    state: str = Field("draft", description="'draft' or 'live'.")


class UpdateNewsItemParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    news_item_id: str = Field(..., description="Intercom news item id to update.")
    title: str = Field("", description="New title (leave empty to keep unchanged).")
    body: str = Field("", description="New body HTML (leave empty to keep unchanged).")
    state: str = Field("", description="New state: 'draft' or 'live' (leave empty to keep unchanged).")


class DeleteNewsItemParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    news_item_id: str = Field(..., description="Intercom news item id to permanently delete.")


class NewsItem(sdl.Entity):
    id: str = ""
    title: str = ""
    body: str = ""
    state: str = ""
    sender_id: str = ""
    created_at: int = 0
    updated_at: int = 0


class NewsItemList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[NewsItem] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────
# Messages (outbound one-off)
# ──────────────────────────────────────────────────────────────────────────


class CreateMessageParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    message_type: str = Field("inapp", description="'inapp' (Messenger) or 'email'.")
    subject: str = Field("", description="Email subject (only used when message_type='email').")
    body: str = Field(..., description="Message body.")
    from_admin_id: str = Field(..., description="Admin id sending this message.")
    to_contact_id: str = Field(..., description="Intercom contact id to send this message to.")


class Message(sdl.Entity):
    title: str = ""
    id: str = ""
    message_type: str = ""
    subject: str = ""
    body: str = ""
    created_at: int = 0


# ──────────────────────────────────────────────────────────────────────────
# Admin / Teams
# ──────────────────────────────────────────────────────────────────────────


class ListAdminsParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")


class GetAdminParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    admin_id: str = Field(..., description="Intercom admin (teammate) id.")


class SetAdminAwayParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    admin_id: str = Field(..., description="Intercom admin id to set away/back status for.")
    away_mode_enabled: bool = Field(..., description="True to set the admin away, false to set them back.")
    away_status_reason_id: str = Field("", description="Away status reason id, if away_mode_enabled is true.")
    reassign_conversations: bool = Field(False, description="Reassign this admin's open conversations while away.")


class Admin(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    email: str = ""
    away_mode_enabled: bool = False
    team_ids: list[str] = Field(default_factory=list)


class AdminList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[Admin] = Field(default_factory=list)


class ListTeamsParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")


class GetTeamParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    team_id: str = Field(..., description="Intercom team id.")


class Team(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    admin_ids: list[str] = Field(default_factory=list)


class TeamList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[Team] = Field(default_factory=list)


class ListAwayStatusReasonsParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")


class AwayStatusReason(sdl.Entity):
    title: str = ""
    id: str = ""
    label: str = ""
    emoji: str = ""


class AwayStatusReasonList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[AwayStatusReason] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────
# Data Attributes / Events / Export
# ──────────────────────────────────────────────────────────────────────────


class ListDataAttributesParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    model: str = Field("contact", description="'contact', 'company', or 'conversation' -- which model's attributes to list.")


class CreateDataAttributeParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    model: str = Field("contact", description="'contact' or 'company' -- custom attributes cannot be created on conversations.")
    name: str = Field(..., description="Attribute key name (snake_case recommended).")
    data_type: str = Field("string", description="'string', 'integer', 'float', 'boolean', or 'date'.")
    description: str = Field("", description="Human-readable description shown in the Intercom UI.")


class DataAttribute(sdl.Entity):
    id: str = ""
    title: str = ""
    name: str = ""
    full_name: str = ""
    label: str = ""
    data_type: str = ""
    model: str = ""
    custom: bool = False


class DataAttributeList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[DataAttribute] = Field(default_factory=list)


class CreateDataEventParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    event_name: str = Field(..., description="Event name, e.g. 'invited-friend', 'completed-onboarding'.")
    contact_id: str = Field("", description="Intercom contact id this event happened for (use this OR email).")
    email: str = Field("", description="Contact email this event happened for (use this OR contact_id).")
    metadata: dict = Field(default_factory=dict, description="Extra key/value metadata to attach to this event.")


class ListDataEventsParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    contact_id: str = Field(..., description="Intercom contact id whose event history to list.")


class DataEvent(sdl.Entity):
    id: str = ""
    title: str = ""
    event_name: str = ""
    created_at: int = 0
    metadata: dict = Field(default_factory=dict)


class DataEventList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[DataEvent] = Field(default_factory=list)


class CreateDataExportParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    created_at_after: int = Field(..., description="Unix timestamp: export conversations created at or after this time.")
    created_at_before: int = Field(..., description="Unix timestamp: export conversations created before this time.")


class DataExportJob(sdl.Entity):
    id: str = ""
    title: str = ""
    job_identifier: str = ""
    status: str = ""
    download_url: str = ""
    download_expires_at: int = 0


class GetDataExportParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    job_identifier: str = Field(..., description="Export job identifier returned by create_data_export.")


class CreateReportingExportParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    dataset_id: str = Field(..., description="Reporting dataset id to export, e.g. 'conversation'.")
    attribute_names: list[str] = Field(..., description="Attribute names to include in the export, e.g. ['conversation_id', 'first_response_time_seconds'].")
    start_time: int = Field(..., description="Unix timestamp: export data from this time.")
    end_time: int = Field(..., description="Unix timestamp: export data until this time.")


# ──────────────────────────────────────────────────────────────────────────
# Tags / Segments
# ──────────────────────────────────────────────────────────────────────────


class ListTagsParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")


class CreateTagParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    name: str = Field(..., description="Tag name to create.")


class DeleteTagParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    tag_id: str = Field(..., description="Tag id to permanently delete.")


class Tag(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""


class TagList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[Tag] = Field(default_factory=list)


class ListSegmentsParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")


class GetSegmentParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    segment_id: str = Field(..., description="Intercom segment id.")


class Segment(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    created_at: int = 0
    updated_at: int = 0
    person_type: str = ""


class SegmentList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[Segment] = Field(default_factory=list)


class ListSubscriptionTypesParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")


class SubscriptionType(sdl.Entity):
    title: str = ""
    id: str = ""
    state: str = ""
    default_translation: str = ""
    content_types: list[str] = Field(default_factory=list)


class SubscriptionTypeList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[SubscriptionType] = Field(default_factory=list)


class AttachContactSubscriptionParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    contact_id: str = Field(..., description="Intercom contact id.")
    subscription_type_id: str = Field(..., description="Subscription type id to opt this contact into.")


class DetachContactSubscriptionParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    contact_id: str = Field(..., description="Intercom contact id.")
    subscription_type_id: str = Field(..., description="Subscription type id to opt this contact out of.")


# ──────────────────────────────────────────────────────────────────────────
# Fin AI Agent
# ──────────────────────────────────────────────────────────────────────────


class StartFinConversationParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    user_id: str = Field(..., description="Your own end-user id Fin should treat as the asker.")
    message: str = Field(..., description="The question/message to start the Fin conversation with.")


class ReplyToFinParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    conversation_id: str = Field(..., description="Fin conversation id returned by start_fin_conversation.")
    message: str = Field(..., description="Follow-up message/answer to send to Fin.")


class FinConversationTurn(sdl.Entity):
    id: str = ""
    title: str = ""
    conversation_id: str = ""
    reply: str = ""
    sources: list[str] = Field(default_factory=list)
    state: str = ""


class ListExternalPagesParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")


class CreateExternalPageParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    title: str = Field(..., description="External page title Fin will use as a knowledge source.")
    html: str = Field(..., description="External page content as HTML, for Fin to learn from.")
    url: str = Field(..., description="Canonical URL this content lives at (for citation).")
    external_id: str = Field(..., description="Your own unique id for this page (used to upsert on repeat calls).")


class UpdateExternalPageParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    external_page_id: str = Field(..., description="Intercom external page id to update.")
    title: str = Field("", description="New title (leave empty to keep unchanged).")
    html: str = Field("", description="New HTML content (leave empty to keep unchanged).")


class DeleteExternalPageParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    external_page_id: str = Field(..., description="Intercom external page id to permanently delete.")


class ExternalPage(sdl.Entity):
    id: str = ""
    title: str = ""
    url: str = ""
    external_id: str = ""
    created_at: int = 0
    updated_at: int = 0


class ExternalPageList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[ExternalPage] = Field(default_factory=list)


class ListContentImportSourcesParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")


class ContentImportSource(sdl.Entity):
    title: str = ""
    id: str = ""
    status: str = ""
    url: str = ""
    sync_behavior: str = ""


class ContentImportSourceList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[ContentImportSource] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────
# Messages (outbound one-off, in-app/email)
# ──────────────────────────────────────────────────────────────────────────


class CreateMessageParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    message_type: str = Field("inapp", description="'inapp' or 'email'.")
    subject: str = Field("", description="Email subject (required for message_type='email').")
    body: str = Field(..., description="Message body (HTML allowed).")
    from_admin_id: str = Field(..., description="Admin id this message is sent from.")
    to_contact_id: str = Field(..., description="Intercom contact id to send this message to.")


class MessageResult(sdl.Entity):
    title: str = ""
    id: str = ""
    message_type: str = ""
    subject: str = ""
    body: str = ""
    created_at: int = 0


# ──────────────────────────────────────────────────────────────────────────
# Audit / value-add reports
# ──────────────────────────────────────────────────────────────────────────


class AuditWorkspaceParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    sample_size: int = Field(50, description="How many recent conversations to sample for the health report.")


class AuditRow(sdl.Entity):
    id: str = ""
    conversation_id: str = ""
    title: str = ""
    state: str = ""
    priority: str = ""
    waiting_hours: float = 0.0
    admin_assignee_id: str = ""
    reason: str = ""


class AuditReport(sdl.Entity):
    id: str = ""
    title: str = ""
    sampled: int = 0
    open_count: int = 0
    unassigned_open_count: int = 0
    stale_open_count: int = 0
    priority_open_count: int = 0
    snoozed_count: int = 0
    closed_count: int = 0
    rows: list[AuditRow] = Field(default_factory=list)
    summary: str = ""


class StaleConversationsParams(BaseModel):
    connection_id: str = Field("", description="Connection id. Leave empty if only one is connected.")
    min_hours_open: float = Field(24.0, description="Flag conversations open and waiting on a reply for at least this many hours.")
    sample_size: int = Field(100, description="How many recent open conversations to scan.")


class StaleConversationsResult(sdl.Entity):
    id: str = ""
    title: str = ""
    scanned: int = 0
    stale_count: int = 0
    rows: list[AuditRow] = Field(default_factory=list)
    summary: str = ""
