"""PR-28 — one helper that combines circuit breaker + timeout + retry
+ failure metrics for a synchronous dependency call.

Used by the RAG / Research / Data specialist agents so every external
call follows the same policy:

    check circuit → run with timeout → retry transient failures
    → record metrics → raise

Permanent failures (401/403/bad payload) raise immediately — never
retried, never masked.
"""

from __future__ import annotations

import logging
import time

from collections.abc import Callable
from typing import TypeVar

from app.core.config import settings
from app.core.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
)
from app.core.retry import (
    backoff_delay,
    classify_failure,
    is_retryable_exception,
)
from app.core.timeout import run_with_timeout
from app.observability import metrics

logger = logging.getLogger(__name__)

T = TypeVar("T")


def execute_sync(
    operation: Callable[[], T],
    *,
    name: str,
    breaker: CircuitBreaker | None = None,
    timeout: float | None = None,
    max_attempts: int | None = None,
    base_delay: float | None = None,
) -> T:
    """Run ``operation()`` through the full reliability stack.

    Raises:
        CircuitOpenError: dependency circuit is open (fail fast).
        DependencyTimeoutError: operation exceeded its timeout budget.
        Exception: the final error after retries are exhausted.
    """
    attempts = (
        max_attempts
        if max_attempts is not None
        else settings.RETRY_MAX_ATTEMPTS
    )

    if breaker is not None:
        # Fail fast without touching the dependency when it is open.
        breaker.check()

    last_exception: BaseException | None = None
    retried = 0

    for attempt in range(attempts):

        started = time.perf_counter()

        try:

            if timeout is not None:
                result = run_with_timeout(
                    operation,
                    name=name,
                    timeout=timeout,
                )
            else:
                result = operation()

            if breaker is not None:
                breaker.record_success()

            if retried:
                _record_retry(name, "success")

            _record_duration(name, time.perf_counter() - started)
            return result

        except CircuitOpenError:
            # Circuit tripped mid-flight; propagate as a degraded
            # dependency, not a 500.
            raise

        except Exception as exc:
            last_exception = exc

            if breaker is not None:
                breaker.record_failure()

            _record_duration(name, time.perf_counter() - started)
            _record_failure(name, classify_failure(exc))

            # Only transient, retryable failures are retried.
            if not is_retryable_exception(exc):
                raise

            if attempt == attempts - 1:
                logger.warning(
                    "dependency exhausted name=%s attempts=%s error=%s",
                    name,
                    attempts,
                    exc,
                )
                break

            # Circuit went open mid-retry: stop hammering the service.
            if breaker is not None and breaker.is_open:
                logger.warning(
                    "dependency tripped circuit during retry "
                    "name=%s",
                    name,
                )
                break

            retried += 1
            _record_retry(name, "failure")

            delay = backoff_delay(attempt, base_delay)
            logger.info(
                "dependency backing off name=%s attempt=%s delay=%.2fs",
                name,
                attempt + 1,
                delay,
            )
            time.sleep(delay)

    raise last_exception  # type: ignore[misc]


def _record_duration(name: str, seconds: float) -> None:
    try:
        if metrics.dependency_duration_seconds is None:
            return
        metrics.dependency_duration_seconds.record(
            seconds,
            {
                "dependency": name,
            },
        )
    except Exception:
        pass


def _record_failure(name: str, reason: str) -> None:
    try:
        if metrics.dependency_failures is None:
            return
        metrics.dependency_failures.add(
            1,
            {
                "dependency": name,
                "reason": reason,
            },
        )
    except Exception:
        pass


def _record_retry(name: str, outcome: str) -> None:
    try:
        if metrics.retry_attempts is None:
            return
        metrics.retry_attempts.add(
            1,
            {
                "dependency": name,
                "outcome": outcome,
            },
        )
    except Exception:
        pass