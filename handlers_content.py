"""Articles / Help Center collections + News items. Built on
intercom_client.py / schemas.py, same shape as handlers_tickets.py --
async, full @chat.function metadata, ActionResult.success()/.error().
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import intercom_client as ic
from app import chat
from handlers_connection import resolve_or_error
from schemas import (
    ListArticlesParams, Article, ArticleList,
    GetArticleParams, CreateArticleParams, UpdateArticleParams,
    DeleteArticleParams, DeleteResult,
    ListHelpCenterCollectionsParams, CreateHelpCenterCollectionParams,
    HelpCenterCollection, HelpCenterCollectionList,
    ListNewsItemsParams, CreateNewsItemParams, UpdateNewsItemParams,
    DeleteNewsItemParams, NewsItem, NewsItemList,
)


def _article_from(raw: dict) -> Article:
    return Article(
        id=raw.get("id", ""), title=raw.get("title", ""),
        description=raw.get("description", "") or "", body=raw.get("body", "") or "",
        state=raw.get("state", ""), author_id=str(raw.get("author_id") or ""),
        url=raw.get("url", "") or "", created_at=raw.get("created_at", 0), updated_at=raw.get("updated_at", 0),
    )


@chat.function(
    "list_articles",
    "List Help Center articles on the connected Intercom workspace.",
    action_type="read",
    chain_callable=True,
    data_model=ArticleList,
)
async def list_articles(ctx, params: ListArticlesParams) -> ActionResult:
    """List articles, page-paginated."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", "/articles", conn["access_token"], conn["region"], params={"page": params.page, "per_page": params.per_page})
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_LIST_ARTICLES_FAILED")
    items = [_article_from(a) for a in (body.get("data") or [])]
    return ActionResult.success(ArticleList(items=items, total_count=body.get("total_count", 0)), summary=f"{len(items)} articles.")


@chat.function(
    "get_article",
    "Read one Help Center article in full.",
    action_type="read",
    chain_callable=True,
    data_model=Article,
)
async def get_article(ctx, params: GetArticleParams) -> ActionResult:
    """Read one article by id."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", f"/articles/{params.article_id}", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_GET_ARTICLE_FAILED")
    return ActionResult.success(_article_from(body), summary=f"Article '{body.get('title')}'.")


@chat.function(
    "create_article",
    "Create a new Help Center article, as a draft or published immediately.",
    action_type="write",
    chain_callable=True,
    data_model=Article,
    event="intercom-connector.create_article",
    effects=["intercom.article.created"],
)
async def create_article(ctx, params: CreateArticleParams) -> ActionResult:
    """Create a new article."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    body = {"title": params.title, "body": params.body, "author_id": params.author_id, "state": params.state}
    if params.parent_id:
        body["parent_id"] = params.parent_id
        body["parent_type"] = "collection"
    try:
        result = await ic.request(ctx, "POST", "/articles", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_CREATE_ARTICLE_FAILED")
    return ActionResult.success(_article_from(result), summary=f"Created article '{params.title}'.")


@chat.function(
    "update_article",
    "Update selected fields of an existing article (title/body/state). Only given fields change.",
    action_type="write",
    chain_callable=True,
    data_model=Article,
    event="intercom-connector.update_article",
    effects=["intercom.article.updated"],
)
async def update_article(ctx, params: UpdateArticleParams) -> ActionResult:
    """Update an existing article."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    body: dict = {}
    if params.title:
        body["title"] = params.title
    if params.body:
        body["body"] = params.body
    if params.state:
        body["state"] = params.state
    if not body:
        return ActionResult.error("Provide at least one field to update.", code="INTERCOM_NO_FIELDS")
    try:
        result = await ic.request(ctx, "PUT", f"/articles/{params.article_id}", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_UPDATE_ARTICLE_FAILED")
    return ActionResult.success(_article_from(result), summary=f"Updated article '{params.article_id}'.")


@chat.function(
    "delete_article",
    "Permanently delete a Help Center article. Cannot be undone.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="intercom-connector.delete_article",
    effects=["intercom.article.deleted"],
)
async def delete_article(ctx, params: DeleteArticleParams) -> ActionResult:
    """Permanently delete an article by id."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await ic.request(ctx, "DELETE", f"/articles/{params.article_id}", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_DELETE_ARTICLE_FAILED")
    return ActionResult.success(DeleteResult(id=params.article_id, deleted=True), summary="Article deleted.")


@chat.function(
    "list_help_center_collections",
    "List Help Center collections (the top-level folders articles are organized into).",
    action_type="read",
    chain_callable=True,
    data_model=HelpCenterCollectionList,
)
async def list_help_center_collections(ctx, params: ListHelpCenterCollectionsParams) -> ActionResult:
    """List Help Center collections."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", "/help_center/collections", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_LIST_COLLECTIONS_FAILED")
    items = [
        HelpCenterCollection(id=c.get("id", ""), name=c.get("name", ""), description=c.get("description", "") or "",
                              icon=c.get("icon", "") or "", url=c.get("url", "") or "", order=c.get("order") or 0)
        for c in (body.get("data") or [])
    ]
    return ActionResult.success(HelpCenterCollectionList(items=items), summary=f"{len(items)} collections.")


@chat.function(
    "create_help_center_collection",
    "Create a new Help Center collection (a top-level folder or nested sub-collection of articles).",
    action_type="write",
    chain_callable=True,
    data_model=HelpCenterCollection,
    event="intercom-connector.create_help_center_collection",
    effects=["intercom.collection.created"],
)
async def create_help_center_collection(ctx, params: CreateHelpCenterCollectionParams) -> ActionResult:
    """Create a new Help Center collection."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    body: dict = {"name": params.name}
    if params.description:
        body["description"] = params.description
    if params.parent_id:
        body["parent_id"] = params.parent_id
    try:
        result = await ic.request(ctx, "POST", "/help_center/collections", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_CREATE_COLLECTION_FAILED")
    return ActionResult.success(
        HelpCenterCollection(id=result.get("id", ""), name=result.get("name", ""), description=result.get("description", "") or "",
                              icon=result.get("icon", "") or "", url=result.get("url", "") or "", order=result.get("order") or 0),
        summary=f"Created collection '{params.name}'.",
    )


@chat.function(
    "list_news_items",
    "List News items (in-product announcements) on the connected Intercom workspace.",
    action_type="read",
    chain_callable=True,
    data_model=NewsItemList,
)
async def list_news_items(ctx, params: ListNewsItemsParams) -> ActionResult:
    """List News items."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await ic.request(ctx, "GET", "/news/news_items", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_LIST_NEWS_FAILED")
    items = [
        NewsItem(id=n.get("id", ""), title=n.get("title", ""), body=n.get("body", "") or "",
                 state=n.get("state", ""), sender_id=str(n.get("sender_id") or ""),
                 created_at=n.get("created_at", 0), updated_at=n.get("updated_at", 0))
        for n in (body.get("data") or [])
    ]
    return ActionResult.success(NewsItemList(items=items), summary=f"{len(items)} news items.")


@chat.function(
    "create_news_item",
    "Create a new News item (draft or live) sent from a given admin.",
    action_type="write",
    chain_callable=True,
    data_model=NewsItem,
    event="intercom-connector.create_news_item",
    effects=["intercom.news_item.created"],
)
async def create_news_item(ctx, params: CreateNewsItemParams) -> ActionResult:
    """Create a new News item."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    body = {"title": params.title, "body": params.body, "sender_id": params.sender_id, "state": params.state}
    try:
        result = await ic.request(ctx, "POST", "/news/news_items", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_CREATE_NEWS_FAILED")
    return ActionResult.success(
        NewsItem(id=result.get("id", ""), title=result.get("title", ""), body=result.get("body", "") or "",
                 state=result.get("state", ""), sender_id=str(result.get("sender_id") or ""),
                 created_at=result.get("created_at", 0), updated_at=result.get("updated_at", 0)),
        summary=f"Created news item '{params.title}'.",
    )


@chat.function(
    "update_news_item",
    "Update selected fields of an existing News item. Only given fields change.",
    action_type="write",
    chain_callable=True,
    data_model=NewsItem,
    event="intercom-connector.update_news_item",
    effects=["intercom.news_item.updated"],
)
async def update_news_item(ctx, params: UpdateNewsItemParams) -> ActionResult:
    """Update an existing News item."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    body: dict = {}
    if params.title:
        body["title"] = params.title
    if params.body:
        body["body"] = params.body
    if params.state:
        body["state"] = params.state
    if not body:
        return ActionResult.error("Provide at least one field to update.", code="INTERCOM_NO_FIELDS")
    try:
        result = await ic.request(ctx, "PUT", f"/news/news_items/{params.news_item_id}", conn["access_token"], conn["region"], json_body=body)
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_UPDATE_NEWS_FAILED")
    return ActionResult.success(
        NewsItem(id=result.get("id", ""), title=result.get("title", ""), body=result.get("body", "") or "",
                 state=result.get("state", ""), sender_id=str(result.get("sender_id") or ""),
                 created_at=result.get("created_at", 0), updated_at=result.get("updated_at", 0)),
        summary="News item updated.",
    )


@chat.function(
    "delete_news_item",
    "Permanently delete a News item. Cannot be undone.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="intercom-connector.delete_news_item",
    effects=["intercom.news_item.deleted"],
)
async def delete_news_item(ctx, params: DeleteNewsItemParams) -> ActionResult:
    """Permanently delete a News item by id."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await ic.request(ctx, "DELETE", f"/news/news_items/{params.news_item_id}", conn["access_token"], conn["region"])
    except ic.ClientFail as e:
        return ActionResult.error(str(e.reason), code="INTERCOM_DELETE_NEWS_FAILED")
    return ActionResult.success(DeleteResult(id=params.news_item_id, deleted=True), summary="News item deleted.")
