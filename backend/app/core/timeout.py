"""PR-28 — enforce timeouts on synchronous blocking calls.

The graph nodes are synchronous, so ``asyncio.timeout`` cannot wrap
them directly. ``run_with_timeout`` executes the callable in a worker
thread and fails fast when the dependency exceeds its budget instead of
leaking a stuck request forever.
"""

from __future__ import annotations

import threading

from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings


class DependencyTimeoutError(TimeoutError):
    """Raised when a dependency exceeds its configured timeout."""

    def __init__(self, name: str, timeout: float) -> None:
        super().__init__(
            f"dependency '{name}' timed out after {timeout}s"
        )
        self.name = name
        self.timeout = timeout


# Small shared pool keeps thread churn low for time-bounded calls.
_POOL = ThreadPoolExecutor(
    max_workers=8,
    thread_name_prefix="dependency-timeout",
)

_POOL_LOCK = threading.Lock()


def run_with_timeout(
    operation,
    *,
    name: str,
    timeout: float | None = None,
) -> object:
    """Run ``operation()`` in a thread, aborting after ``timeout`` seconds.

    ``timeout=None`` falls back to the single global agent timeout.

    Raises:
        DependencyTimeoutError: the callable did not finish in time.
    """
    budget = (
        timeout
        if timeout is not None
        else settings.AGENT_TOTAL_TIMEOUT_SECONDS
    )

    future = _POOL.submit(operation)

    try:
        return future.result(timeout=budget)

    except TimeoutError:
        # The worker thread keeps running in the background but the
        # calling request is unblocked. The graph will treat the
        # dependency as degraded.
        future.cancel()
        raise DependencyTimeoutError(
            name=name,
            timeout=budget,
        ) from None