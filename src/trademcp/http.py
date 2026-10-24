"""Shared HTTP layer: browser-like headers, retries and actionable errors."""

from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx

from . import config

_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()

_RETRY_STATUS = {429, 500, 502, 503, 504}


class DataSourceError(RuntimeError):
    """An upstream free data source could not serve the request."""


async def get_client() -> httpx.AsyncClient:
    """One shared client so connections and cookies are reused."""
    global _client
    if _client is None:
        async with _client_lock:
            if _client is None:
                _client = httpx.AsyncClient(
                    headers={
                        "User-Agent": config.USER_AGENT,
                        "Accept-Language": "en-US,en;q=0.9",
                    },
                    follow_redirects=True,
                    timeout=config.TIMEOUT,
                    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
                )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def get_json(url: str, params: dict[str, Any] | None = None, *, source: str, attempts: int = 3) -> Any:
    """GET JSON with backoff on rate limits and transient network errors."""
    client = await get_client()
    last: Exception | None = None

    for attempt in range(attempts):
        try:
            resp = await client.get(url, params=params)
            if resp.status_code == 404:
                raise DataSourceError(f"{source}: not found (404). Check the symbol or ticker.")
            if resp.status_code in _RETRY_STATUS:
                raise httpx.HTTPStatusError("retryable", request=resp.request, response=resp)
            resp.raise_for_status()
            try:
                return resp.json()
            except ValueError as exc:
                raise DataSourceError(
                    f"{source}: response was not valid JSON (HTTP {resp.status_code}). "
                    "The upstream endpoint may be rate limiting - retry shortly."
                ) from exc
        except DataSourceError:
            raise
        except httpx.HTTPStatusError as exc:
            last = exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last = exc

        if attempt < attempts - 1:
            await asyncio.sleep(1.5 * (attempt + 1) + random.random())

    raise DataSourceError(
        f"{source}: request failed after {attempts} attempts ({type(last).__name__}). "
        "The free endpoint may be rate limiting - retry shortly."
    )


async def get_text(url: str, params: dict[str, Any] | None = None, *, source: str, attempts: int = 3) -> str:
    """GET a text/HTML body with the same retry policy as get_json."""
    client = await get_client()
    last: Exception | None = None

    for attempt in range(attempts):
        try:
            resp = await client.get(url, params=params)
            if resp.status_code == 404:
                raise DataSourceError(f"{source}: not found (404). Check the symbol.")
            if resp.status_code in _RETRY_STATUS:
                raise httpx.HTTPStatusError("retryable", request=resp.request, response=resp)
            resp.raise_for_status()
            return resp.text
        except DataSourceError:
            raise
        except httpx.HTTPStatusError as exc:
            last = exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last = exc

        if attempt < attempts - 1:
            await asyncio.sleep(1.5 * (attempt + 1) + random.random())

    raise DataSourceError(
        f"{source}: request failed after {attempts} attempts ({type(last).__name__}). "
        "The free endpoint may be rate limiting - retry shortly."
    )
