"""PR-28 — concurrency backpressure for agent execution.

A multi-agent system can fan out RAG + Research + Data at the same time.
That is good, but unbounded concurrency lets 1000 requests × 3 agents
overwhelm the LLM API, Qdrant, PostgreSQL and Redis at once.

FastAPI's synchronous endpoints run in a thread pool, so an
``asyncio.Semaphore`` cannot be shared safely across requests here. A
process-wide ``threading`` semaphore provides equivalent backpressure
for the sync graph path. (An async API would use ``asyncio.Semaphore``
the same way.)
"""

from __future__ import annotations

import threading
import time

from contextlib import contextmanager

from app.core.config import settings
from app.observability import metrics
from opentelemetry import trace


class AgentConcurrencyLimitExceeded(RuntimeError):
    """Raised when no concurrency slot is available within the wait."""


_SEMAPHORE = threading.BoundedSemaphore(
    settings.AGENT_CONCURRENCY
)

_WAIT_TIMEOUT_SECONDS = 30.0


@contextmanager
def agent_execution_slot():
    """Acquire one of ``AGENT_CONCURRENCY`` global agent slots.

    Provides a graceful backpressure window; once the wait elapses the
    request fails fast instead of queueing forever behind other runs.
    """
    acquired = _SEMAPHORE.acquire(
        timeout=_WAIT_TIMEOUT_SECONDS
    )

    if not acquired:
        try:
            if metrics.concurrency_limited is not None:
                metrics.concurrency_limited.add(1)
        except Exception:
            pass

        raise AgentConcurrencyLimitExceeded(
            "Agent execution concurrency limit reached"
        )

    submitted_at = time.perf_counter()

    try:
        yield

    finally:
        _SEMAPHORE.release()

        try:
            if metrics.concurrency_duration_seconds is not None:
                metrics.concurrency_duration_seconds.record(
                    time.perf_counter() - submitted_at
                )
        except Exception:
            pass


def current_concurrency() -> int:
    """Total in-flight agent executions (approximate, best-effort)."""
    return settings.AGENT_CONCURRENCY - _SEMAPHORE._value  # type: ignore[attr-defined]