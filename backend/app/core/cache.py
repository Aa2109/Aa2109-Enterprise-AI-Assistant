"""PR-28 — response caching with permission-aware, versioned cache keys.

Cache keys are NEVER just ``hash(query)``. They also carry:

  * the caller's authorization scope — so a result cached for an admin
    can never be served to a lower-privileged caller (an "unauthorized
    user -> cache cannot leak data" guarantee), and
  * a knowledge version — so re-indexed documents naturally invalidate
    old entries (``v42 -> v43``) without anyone deleting entries.

Graceful degradation is first-class: the cache must never break a
request. When Redis is not installed, not configured, or unreachable we
transparently fall back to a bounded in-process TTL cache, and finally
to a no-op. ``REDIS_TIMEOUT_SECONDS`` bounds every Redis round-trip so a
hung Redis never stalls the response path.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from typing import Any

from app.core.config import settings
from app.observability import metrics
from app.security.models import UserContext

logger = logging.getLogger(__name__)

# Optional dependency — the module must import even when redis is not
# installed (isolated tooling, offline dev machines).
try:
    import redis as _redis  # type: ignore
except ImportError:  # pragma: no cover
    _redis = None  # type: ignore[assignment]

_IN_MEMORY_MAX_ENTRIES = 1024


# ==========================================================
# Cache keys
# ==========================================================

def build_cache_key(
    *,
    namespace: str,
    query: str,
    knowledge_version: int | None = None,
    scope: str,
) -> str:
    """Deterministic cache key = namespace + version + scope + query hash.

    ``query`` is normalized (collapsed whitespace, lowercased) so "What
    is  X?" and "what   is x?" hit the same entry.
    """
    normalized = " ".join(query.lower().split())
    digest = hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()[:16]

    version = (
        knowledge_version
        if knowledge_version is not None
        else settings.KNOWLEDGE_VERSION
    )

    return f"{namespace}:v{version}:{scope}:{digest}"


def permission_scope(user: UserContext | None) -> str:
    """Authorization-scope portion of the cache key.

    Derived from role + sorted permission values so two callers with
    different access levels never share a cache entry.
    """
    if user is None:
        return "anonymous"

    permissions = "|".join(
        sorted(p.value for p in user.permissions)
    )

    return f"{user.role.value}:{permissions}"


# ==========================================================
# Bounded in-memory fallback (Redis unavailable)
# ==========================================================

class _MemoryCache:
    """Tiny thread-safe TTL cache with FIFO eviction."""

    def __init__(self, max_entries: int = _IN_MEMORY_MAX_ENTRIES) -> None:
        self._max_entries = max_entries
        self._entries: OrderedDict[str, tuple[float, str]] = (
            OrderedDict()
        )
        self._lock = threading.Lock()

    def get(self, key: str) -> str | None:
        with self._lock:
            entry = self._entries.get(key)

            if entry is None:
                return None

            expires_at, payload = entry

            if time.monotonic() >= expires_at:
                del self._entries[key]
                return None

            self._entries.move_to_end(key)
            return payload

    def set(self, key: str, value: str, ttl_seconds: float) -> None:
        with self._lock:
            self._entries[key] = (
                time.monotonic() + ttl_seconds,
                value,
            )
            self._entries.move_to_end(key)

            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)


# ==========================================================
# Cache facade
# ==========================================================

class ResponseCache:
    """Redis-backed cache that degrades to memory, then no-op.

    Only established-read answer payloads (JSON strings) are cached.
    Everything here is best-effort: any failure is logged once, never
    raised to the caller.
    """

    def __init__(self, *, namespace: str = "enterprise_ai") -> None:
        self._namespace = namespace
        self._memory = _MemoryCache()
        self._client: Any = None
        self._redis_unavailable_reported = False
        self._lock = threading.Lock()

    # ------------------------------------------------------
    # Public API
    # ------------------------------------------------------

    def get(self, key: str) -> str | None:
        """Return the cached JSON payload, or None on miss/degraded."""

        payload = self._redis_get(key)

        if payload is None:
            payload = self._memory.get(key)

        if payload is None:
            _record("cache_misses")
            return None

        _record("cache_hits")
        return payload

    def set(
        self,
        key: str,
        value: str,
        *,
        ttl_seconds: int | None = None,
    ) -> None:
        ttl = (
            ttl_seconds
            if ttl_seconds is not None
            else settings.REDIS_CACHE_TTL_SECONDS
        )

        # Memory always gets the entry so a redis outage mid-request
        # does not drop a just-computed answer.
        self._memory.set(key, value, ttl)

        try:
            client = self._redis_client()

            if client is not None:
                client.set(
                    key,
                    value,
                    ex=ttl,
                )
        except Exception:  # noqa: BLE001 — cache must never break the hot path
            self._warn_degraded()

    # ------------------------------------------------------
    # Redis internals
    # ------------------------------------------------------

    def _redis_get(self, key: str) -> str | None:
        try:
            client = self._redis_client()

            if client is None:
                return None

            return client.get(key)
        except Exception:  # noqa: BLE001 — degraded to memory cache
            self._warn_degraded()
            return None

    def _redis_client(self):
        # Lazy init: checking availability is expensive, so only probe
        # when the URL is actually configured and the module imported.
        if _redis is None:
            return None

        if self._client is not None:
            return self._client

        if not settings.REDIS_URL:
            return None

        with self._lock:
            if self._client is not None:
                return self._client

            self._client = _redis.Redis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=settings.REDIS_TIMEOUT_SECONDS,
                socket_timeout=settings.REDIS_TIMEOUT_SECONDS,
                decode_responses=True,
            )

            return self._client

    def _warn_degraded(self) -> None:
        if self._redis_unavailable_reported:
            return
        self._redis_unavailable_reported = True
        logger.warning(
            "Redis response cache unavailable; "
            "degrading to in-process cache"
        )


def _record(kind: str) -> None:
    try:
        if kind == "cache_hits":
            if metrics.cache_hits is not None:
                metrics.cache_hits.add(1)
        else:
            if metrics.cache_misses is not None:
                metrics.cache_misses.add(1)
    except Exception:  # noqa: BLE001 S110 — metrics are best-effort
        pass


# ==========================================================
# Singletons / helpers
# ==========================================================

_cache: ResponseCache | None = None
_cache_lock = threading.Lock()


def get_response_cache() -> ResponseCache:
    global _cache

    if _cache is not None:
        return _cache

    with _cache_lock:
        if _cache is None:
            _cache = ResponseCache()

        return _cache


def cached_value_to_json(value: Any) -> str:
    return json.dumps(value, default=str)


def json_to_cached_value(payload: str) -> Any:
    return json.loads(payload)