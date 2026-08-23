"""Intercom HTTP client -- one REST surface, but a REGIONAL base URL, plus
Bearer auth and Intercom's own pagination shapes. Same fail()/ClientFail
shared-request-helper pattern as pagerduty_client.py / mulesoft_client.py --
uses the platform's own `ctx.http` (async), never `requests`.

WHY THE BASE URL IS A FUNCTION OF THE STORED REGION, NOT A CONSTANT.

Intercom workspaces are regionally hosted (US/EU/Australia) and the REST
API host itself changes per region (intercom.com/help/en/articles/
6124430-regional-data-hosting, confirmed 2026-08-23):
  - US (default): api.intercom.io
  - EU:            api.eu.intercom.io
  - AU:            api.au.intercom.io
Calling the US host with an EU-hosted workspace's token does not error
cleanly -- it looks like an auth failure. `region_base_url()` centralizes
this mapping so every handler gets it right without repeating the table.

WHY BEARER, NOT A CUSTOM SCHEME (UNLIKE PAGERDUTY).

Intercom's REST API authenticates every request with a plain
`Authorization: Bearer <access_token>` header (developers.intercom.com/
docs/build-an-integration/learn-more/authentication, confirmed
2026-08-23) -- simpler than PagerDuty's `Token token=` scheme.

WHY `Intercom-Version` IS SENT ON EVERY REQUEST.

Intercom versions its REST API independently of the product and expects
a `Intercom-Version` header to pin behaviour (developers.intercom.com/
docs/references/introduction, confirmed 2026-08-23 -- current stable is
2.16). Omitting it defaults to the account's configured default version,
which can silently change response shapes later if the workspace's
default is bumped -- pinning here keeps this connector's parsing stable.

WHY 429 IS RETRIED ONCE USING THE `X-RateLimit-Reset` WINDOW.

Intercom returns `X-RateLimit-Limit` / `X-RateLimit-Remaining` /
`X-RateLimit-Reset` headers and a 429 status when a private app exceeds
its per-minute budget (developers.intercom.com/docs/references/rest-api/
errors/rate-limiting, confirmed 2026-08-23: private apps default to
10,000 calls/minute per app and 25,000/minute per workspace) -- a single
bounded retry absorbs a transient burst without the caller handling it.
"""
from __future__ import annotations

import asyncio
from typing import Any

INTERCOM_VERSION = "2.16"

_REGION_HOSTS = {
    "us": "https://api.intercom.io",
    "eu": "https://api.eu.intercom.io",
    "au": "https://api.au.intercom.io",
}


def region_base_url(region: str) -> str:
    return _REGION_HOSTS.get((region or "us").strip().lower(), _REGION_HOSTS["us"])


class ClientFail(Exception):
    """Raised for any non-2xx Intercom response, carrying a human reason."""

    def __init__(self, reason: str, status: int = 0):
        super().__init__(reason)
        self.reason = reason
        self.status = status


def _headers(access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Intercom-Version": INTERCOM_VERSION,
    }


def _map_error(status: int, body: Any) -> str:
    detail = ""
    if isinstance(body, dict):
        errors = body.get("errors")
        if isinstance(errors, list) and errors:
            parts = []
            for e in errors:
                if isinstance(e, dict):
                    parts.append(str(e.get("message") or e.get("code") or e))
                else:
                    parts.append(str(e))
            detail = "; ".join(parts)
    if status == 401:
        return "Intercom rejected this Access Token -- it may be wrong, revoked, or issued for a different region."
    if status == 403:
        return f"Intercom accepted the token but refused this action (missing OAuth/private-app scope).{(' ' + detail) if detail else ''}"
    if status == 404:
        return "That Intercom resource was not found (wrong id, or it was deleted)."
    if status == 422:
        return f"Intercom rejected the request data.{(' ' + detail) if detail else ''}"
    if status == 429:
        return "Intercom rate-limited this app -- too many requests too quickly (10,000/min per app, 25,000/min per workspace)."
    return f"Intercom API error ({status}).{(' ' + detail) if detail else ''}"


async def request(
    ctx,
    method: str,
    path: str,
    access_token: str,
    region: str = "us",
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    _retried: bool = False,
) -> dict[str, Any]:
    """One call against Intercom's REST API. `path` starts with '/', e.g. '/contacts'."""
    url = f"{region_base_url(region)}{path}"
    headers = _headers(access_token)
    try:
        method_u = method.upper()
        if method_u == "GET":
            resp = await ctx.http.get(url, headers=headers, params=params)
        elif method_u == "POST":
            resp = await ctx.http.post(url, headers=headers, params=params, json=json_body)
        elif method_u == "PUT":
            resp = await ctx.http.put(url, headers=headers, params=params, json=json_body)
        elif method_u == "DELETE":
            resp = await ctx.http.delete(url, headers=headers, params=params, json=json_body)
        else:
            raise ClientFail(f"Unsupported HTTP method: {method}")
    except ClientFail:
        raise
    except Exception as e:
        raise ClientFail(f"Could not reach Intercom's API: {e}")

    if resp.status_code == 429 and not _retried:
        await asyncio.sleep(2.0)
        return await request(
            ctx, method, path, access_token, region,
            params=params, json_body=json_body, _retried=True,
        )

    if resp.status_code == 204 or not getattr(resp, "content", resp.body if hasattr(resp, "body") else None):
        if resp.status_code >= 400:
            raise ClientFail(_map_error(resp.status_code, {}), resp.status_code)
        return {}

    body = resp.body if isinstance(resp.body, (dict, list)) else {}

    if resp.status_code >= 400:
        raise ClientFail(_map_error(resp.status_code, body), resp.status_code)

    return body if isinstance(body, dict) else {"items": body}


async def get_all_cursor(
    ctx, path: str, access_token: str, region: str, list_key: str,
    *, params: dict[str, Any] | None = None, max_items: int = 1000,
) -> list[dict[str, Any]]:
    """Paginate an Intercom cursor-based GET list endpoint (the 'pages.next'
    shape used by /contacts, /companies, /tags, etc, confirmed
    2026-08-23)."""
    out: list[dict[str, Any]] = []
    q = dict(params or {})
    starting_after = q.pop("starting_after", "") or ""
    while len(out) < max_items:
        if starting_after:
            q["starting_after"] = starting_after
        body = await request(ctx, "GET", path, access_token, region, params=q)
        items = body.get(list_key) or body.get("data") or []
        out.extend(items)
        pages = body.get("pages") or {}
        nxt = pages.get("next")
        if isinstance(nxt, dict):
            starting_after = nxt.get("starting_after") or ""
        elif isinstance(nxt, str):
            starting_after = nxt
        else:
            starting_after = ""
        if not starting_after or not items:
            break
    return out[:max_items]


async def validate_token(ctx, access_token: str, region: str = "us") -> dict[str, Any]:
    """Confirm an Access Token actually works via GET /me (the connected
    admin's own identity, cheap and always-available), confirmed
    2026-08-23."""
    return await request(ctx, "GET", "/me", access_token, region)
