"""PR-28 — retry helpers with exponential backoff, jitter, and
retryable-error classification.

Retry is for *transient* failures ("this request failed temporarily").
Permanent errors (401, 403, 404, invalid payloads) are never retried —
retrying them only multiplies the cost without ever succeeding.
"""

from __future__ import annotations

import logging
import random
import time

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from app.core.config import settings
from app.core.timeout import DependencyTimeoutError, run_with_timeout
from app.observability import metrics

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ==========================================================
# Retryable-error classification
# ==========================================================

# Timeouts and connection-level failures: the transport never
# established/completed a request, so nothing side-effectful happened.
RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    TimeoutError,
    ConnectionError,
    OSError,
)

try:
    # A read-only SELECT that hits a statement_timeout is safe to retry:
    # no rows were ever written. (Guard so the module also imports when
    # sqlalchemy is unavailable, e.g. in isolated tooling.)
    from sqlalchemy.exc import (  # noqa: PLC0415
        OperationalError as _SQLAlchemyOperationalError,
    )

    RETRYABLE_EXCEPTIONS = (
        RETRYABLE_EXCEPTIONS
        + (_SQLAlchemyOperationalError,)
    )
except ImportError:
    pass

# HTTP status codes safe to retry: outages/throttling, not client errors.
RETRYABLE_HTTP_STATUS: frozenset[int] = frozenset(
    {408, 425, 429, 500, 502, 503, 504}
)


def is_retryable_exception(exc: BaseException) -> bool:
    return isinstance(exc, RETRYABLE_EXCEPTIONS)


def is_retryable_http_status(status: int) -> bool:
    return status in RETRYABLE_HTTP_STATUS


def classify_failure(exc: BaseException) -> str:
    """Map an exception to a safe, non-sensitive reason label."""
    if isinstance(exc, DependencyTimeoutError):
        return "timeout"
    if isinstance(exc, TimeoutError):
        return "timeout"
    return "service_unavailable"


def backoff_delay(
    attempt: int,
    base_delay: float | None = None,
) -> float:
    """Exponential backoff with jitter.

    delay = base * 2**attempt + random_jitter

    Jitter de-synchronizes concurrent clients so a recovering service
    is not stampeded by a wall of simultaneous retries.
    """
    base = (
        base_delay
        if base_delay is not None
        else settings.RETRY_BASE_DELAY_SECONDS
    )
    jitter = random.uniform(0.0, 0.2)
    return min(
        base * (2 ** attempt) + jitter,
        settings.RETRY_MAX_DELAY_SECONDS,
    )


def _record_retry(dependency: str, outcome: str) -> None:
    try:
        if metrics.retry_attempts is None:
            return
        metrics.retry_attempts.add(
            1,
            {
                "dependency": dependency,
                "outcome": outcome,
            },
        )
    except Exception:  # metrics must never break the hot path
        pass


# ==========================================================
# Async retry
# ==========================================================

async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    max_attempts: int | None = None,
    base_delay: float | None = None,
    timeout: float | None = None,
    dependency: str = "operation",
    retryable: Callable[[BaseException], bool] | None = None,
) -> T:
    """Retry an async operation with exponential backoff + jitter.

    Only exceptions classified retryable are retried — everything else
    re-raises immediately.
    """
    attempts = (
        max_attempts
        if max_attempts is not None
        else settings.RETRY_MAX_ATTEMPTS
    )
    should_retry = (
        retryable
        if retryable is not None
        else is_retryable_exception
    )

    last_exception: BaseException | None = None

    for attempt in range(attempts):

        try:

            if timeout is not None:
                import asyncio

                result = await asyncio.wait_for(
                    operation(),
                    timeout=timeout,
                )
            else:
                result = await operation()

            if attempt > 0:
                _record_retry(dependency, "success")

            return result

        except Exception as exc:
            last_exception = exc

            _record_retry(dependency, "failure")

            if not should_retry(exc):
                raise

            if attempt == attempts - 1:
                logger.warning(
                    "retry_async exhausted dependency=%s "
                    "attempts=%s error=%s",
                    dependency,
                    attempts,
                    exc,
                )
                break

            delay = backoff_delay(attempt, base_delay)
            logger.info(
                "retry_async backing off dependency=%s "
                "attempt=%s delay=%.2fs",
                dependency,
                attempt + 1,
                delay,
            )
            await _asyncio_sleep(delay)

    raise last_exception  # type: ignore[misc]


async def _asyncio_sleep(delay: float) -> None:
    import asyncio

    await asyncio.sleep(delay)


# ==========================================================
# Sync retry (used by the LangGraph nodes)
# ==========================================================

def retry_sync(
    operation: Callable[[], T],
    *,
    max_attempts: int | None = None,
    base_delay: float | None = None,
    timeout: float | None = None,
    dependency: str = "operation",
    retryable: Callable[[BaseException], bool] | None = None,
) -> T:
    """Retry a synchronous blocking operation with backoff + jitter.

    When ``timeout`` is set the callable runs inside a worker thread so a
    hung dependency fails fast instead of blocking a worker forever.
    """
    attempts = (
        max_attempts
        if max_attempts is not None
        else settings.RETRY_MAX_ATTEMPTS
    )
    should_retry = (
        retryable
        if retryable is not None
        else is_retryable_exception
    )

    last_exception: BaseException | None = None

    for attempt in range(attempts):

        try:

            if timeout is not None:
                result = run_with_timeout(
                    operation,
                    name=dependency,
                    timeout=timeout,
                )
            else:
                result = operation()

            if attempt > 0:
                _record_retry(dependency, "success")

            return result

        except Exception as exc:
            last_exception = exc

            _record_retry(dependency, "failure")

            if not should_retry(exc):
                raise

            if attempt == attempts - 1:
                logger.warning(
                    "retry_sync exhausted dependency=%s "
                    "attempts=%s error=%s",
                    dependency,
                    attempts,
                    exc,
                )
                break

            delay = backoff_delay(attempt, base_delay)
            logger.info(
                "retry_sync backing off dependency=%s "
                "attempt=%s delay=%.2fs",
                dependency,
                attempt + 1,
                delay,
            )
            time.sleep(delay)

    raise last_exception  # type: ignore[misc]