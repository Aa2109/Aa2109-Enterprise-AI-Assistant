"""PR-28 — lightweight circuit breaker (CLOSED / OPEN / HALF-OPEN).

Retries handle "this request failed temporarily"; the circuit breaker
handles "this dependency is consistently failing — stop hammering it".
After ``fail_max`` consecutive failures the breaker trips OPEN and all
calls fail fast without touching the dependency. After
``recovery_timeout`` it allows a single HALF-OPEN probe to test whether
the dependency has recovered.

Implemented in-process (no third-party dependency) so metrics, state
transitions and thread-safety are transparent and verifiable by hand.
"""

from __future__ import annotations

import logging
import threading
import time

from enum import Enum

from app.core.config import settings
from app.observability import metrics

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    """Raised when a dependency's circuit breaker is tripped."""

    def __init__(self, name: str) -> None:
        super().__init__(
            f"circuit '{name}' is open; dependency available to fail fast"
        )
        self.name = name


class CircuitBreaker:

    def __init__(
        self,
        name: str,
        fail_max: int | None = None,
        recovery_timeout: float | None = None,
    ) -> None:
        self.name = name
        self.fail_max = (
            fail_max
            if fail_max is not None
            else settings.CIRCUIT_FAIL_MAX
        )
        self.recovery_timeout = (
            recovery_timeout
            if recovery_timeout is not None
            else settings.CIRCUIT_RECOVERY_TIMEOUT_SECONDS
        )

        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at: float | None = None
        self._half_open_probe_available = False

        self._lock = threading.Lock()

    # ==========================================================
    # Public API
    # ==========================================================

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def is_open(self) -> bool:
        return self._state == CircuitState.OPEN

    def check(self) -> None:
        """Raise before issuing a real call if the circuit is open."""
        with self._lock:

            if (
                self._state == CircuitState.OPEN
                and self._opened_at is not None
                and (
                    time.monotonic() - self._opened_at
                    >= self.recovery_timeout
                )
            ):
                # Recovery window elapsed: allow exactly one probe.
                self._state = CircuitState.HALF_OPEN
                self._half_open_probe_available = True
                self._record_state_change(
                    from_state=CircuitState.OPEN,
                    to_state=CircuitState.HALF_OPEN,
                    reason="recovery_timeout_elapsed",
                )

            if self._state == CircuitState.OPEN:
                raise CircuitOpenError(self.name)

            if (
                self._state == CircuitState.HALF_OPEN
                and not self._half_open_probe_available
            ):
                # A probe is already in flight — concurrent callers wait.
                raise CircuitOpenError(self.name)

    def record_success(self) -> None:
        """A call succeeded; close the circuit."""
        with self._lock:

            if self._state in {
                CircuitState.OPEN,
                CircuitState.HALF_OPEN,
            }:
                self._record_state_change(
                    from_state=self._state,
                    to_state=CircuitState.CLOSED,
                    reason="success",
                )

            self._state = CircuitState.CLOSED
            self._failures = 0
            self._half_open_probe_available = False

    def record_failure(self) -> None:
        """A call failed; count it toward the trip threshold."""
        with self._lock:

            if self._state == CircuitState.CLOSED:
                self._failures += 1

                if self._failures >= self.fail_max:
                    self._open_locked()

            elif self._state == CircuitState.HALF_OPEN:
                # The recovery probe failed: trip open again.
                self._open_locked()

            # OPEN is already latched: ignore further failures.

    # ==========================================================
    # Decorator-style wrappers
    # ==========================================================

    def guard_sync(self, operation, *args, **kwargs):
        """Run ``operation(*args, **kwargs)`` behind the breaker."""

        self.check()

        try:
            result = operation(*args, **kwargs)
        except Exception:
            self.record_failure()
            raise

        self.record_success()
        return result

    # ==========================================================
    # Internals
    # ==========================================================

    def _open_locked(self) -> None:
        if self._state == CircuitState.OPEN:
            return

        self._record_state_change(
            from_state=self._state,
            to_state=CircuitState.OPEN,
            reason="failure_threshold",
        )

        self._state = CircuitState.OPEN
        self._opened_at = time.monotonic()
        self._half_open_probe_available = False

        try:
            if metrics.circuit_breaker_open is not None:
                metrics.circuit_breaker_open.add(
                    1,
                    {
                        "circuit": self.name,
                    },
                )
        except Exception:
            pass

        logger.warning(
            "Circuit breaker opened circuit=%s "
            "fail_max=%s",
            self.name,
            self.fail_max,
        )

    @staticmethod
    def _record_state_change(
        from_state: CircuitState,
        to_state: CircuitState,
        reason: str,
    ) -> None:
        try:
            if metrics.circuit_breaker_state is not None:
                metrics.circuit_breaker_state.add(
                    1,
                    {
                        "circuit_from": from_state.value,
                        "circuit_to": to_state.value,
                        "reason": reason,
                    },
                )
        except Exception:
            pass