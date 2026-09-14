"""PR-28 — reusable HTTP client with connection pooling and timeouts.

Without a pool every request pays for a fresh TCP + TLS handshake.
With ``httpx.Limits`` connections are kept alive and reused, which
matters for an agent that makes several external calls per run.
"""

from __future__ import annotations

from functools import lru_cache

import httpx

from app.core.config import settings


def create_http_client() -> httpx.Client:
    """Build a sync client with per-phase timeouts and a connection pool.

    Timeout phases:
      connect  — TCP + TLS handshake
      read     — waiting for the response body (the main search budget)
      write    — sending the request body
      pool     — waiting for a free connection in the pool
    """
    return httpx.Client(
        timeout=httpx.Timeout(
            connect=settings.HTTP_CONNECT_TIMEOUT_SECONDS,
            read=settings.WEB_SEARCH_TIMEOUT_SECONDS,
            write=settings.HTTP_WRITE_TIMEOUT_SECONDS,
            pool=settings.HTTP_POOL_TIMEOUT_SECONDS,
        ),
        limits=httpx.Limits(
            max_connections=settings.HTTP_MAX_CONNECTIONS,
            max_keepalive_connections=(
                settings.HTTP_MAX_KEEPALIVE_CONNECTIONS
            ),
        ),
        headers={
            "User-Agent": "enterprise-ai-assistant/0.1",
        },
        follow_redirects=True,
    )


def create_async_http_client() -> httpx.AsyncClient:
    """Async variant for use inside async contexts."""
    return httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=settings.HTTP_CONNECT_TIMEOUT_SECONDS,
            read=settings.WEB_SEARCH_TIMEOUT_SECONDS,
            write=settings.HTTP_WRITE_TIMEOUT_SECONDS,
            pool=settings.HTTP_POOL_TIMEOUT_SECONDS,
        ),
        limits=httpx.Limits(
            max_connections=settings.HTTP_MAX_CONNECTIONS,
            max_keepalive_connections=(
                settings.HTTP_MAX_KEEPALIVE_CONNECTIONS
            ),
        ),
        headers={
            "User-Agent": "enterprise-ai-assistant/0.1",
        },
        follow_redirects=True,
    )


@lru_cache(maxsize=1)
def get_http_client() -> httpx.Client:
    """Process-wide pooled client (lazy, cached)."""
    return create_http_client()


@lru_cache(maxsize=1)
def get_async_http_client() -> httpx.AsyncClient:
    return create_async_http_client()


async def close_http_clients() -> None:
    """Close the pooled clients and drop the cached references.

    Called from the app lifespan on shutdown so keep-alive sockets held
    by the pool are released and the process can exit. The cache is
    cleared because a closed client must never be handed out again.
    The sync client closes with ``close()``; the async client needs
    ``aclose()`` (an awaitable), so each is closed via its own method.
    """
    for getter in (get_http_client, get_async_http_client):
        client = getter()
        try:
            if isinstance(client, httpx.AsyncClient):
                await client.aclose()
            else:
                client.close()
        except Exception:  # noqa: BLE001 S110 — best-effort on shutdown
            pass
        getter.cache_clear()