import logging

from opentelemetry import trace

from app.core.circuit_breaker import CircuitBreaker, CircuitOpenError
from app.core.config import settings
from app.core.reliability import execute_sync
from app.core.timeout import DependencyTimeoutError
from app.observability import metrics
from app.agents.result import build_result
from app.security.audit import audit_security_event
from app.security.guards import has_permission
from app.security.models import Permission

logger = logging.getLogger(__name__)

tracer = trace.get_tracer(
    "enterprise-ai-assistant"
)

# Process-wide circuit for the read-only database dependency.
DATA_CIRCUIT = CircuitBreaker(name="database")

# Safe, non-sensitive error text.
ERROR_TIMEOUT = "The database query timed out."
ERROR_UNAVAILABLE = (
    "Structured data access is temporarily unavailable. "
    "Please try again later."
)
ERROR_CIRCUIT_OPEN = (
    "Structured data access is temporarily unavailable; "
    "too many recent failures. Please try again shortly."
)
ERROR_TOOL_LIMIT = "The maximum number of tool executions was reached."


class DataAgent:

    def __init__(
        self,
        sql_tool,
        breaker: CircuitBreaker | None = None,
    ):
        self.sql_tool = sql_tool
        self.breaker = breaker or DATA_CIRCUIT

    def __call__(self, state):

        with tracer.start_as_current_span(
            "agent.data"
        ) as span:

            span.set_attribute(
                "agent.name",
                "data",
            )

            state["current_agent"] = "data"

            try:

                # ==========================================
                # Permission boundary
                # ==========================================

                user = state.get("user_context")

                allowed = has_permission(
                    user,
                    Permission.DATA_READ,
                )

                span.set_attribute(
                    "agent.permission_allowed",
                    allowed,
                )

                if not allowed:

                    audit_security_event(
                        event="tool_authorization_denied",
                        user_id=(
                            user.user_id
                            if user is not None
                            else None
                        ),
                        resource="data",
                        action="execute",
                        allowed=False,
                    )

                    agent_result = build_result(
                        "data",
                        success=False,
                        metadata={
                            "permission_denied": True,
                        },
                        error=(
                            "You are not authorized to execute "
                            "the data operation."
                        ),
                    )

                    state["data_results"] = [
                        agent_result
                    ]

                    state.setdefault(
                        "agent_results",
                        {},
                    )["data"] = agent_result

                    logger.warning(
                        "Data agent permission denied"
                    )

                    return state

                # ==========================================
                # PR-28 tool-call limit
                # ==========================================

                reason, should_stop = self._tool_call_guard(
                    state
                )

                if should_stop:
                    return self._store_failure(
                        state,
                        error=ERROR_TOOL_LIMIT,
                        reason=reason,
                    )

                # ==========================================
                # PR-28 reliable dependency call
                #
                # The SQL tool is read-only (validator enforces SELECT)
                # so transient failures may be retried. The actual DB
                # statement is bounded by DATABASE_TIMEOUT via the
                # engine's statement_timeout; a statement-timeout raises
                # a retryable OperationalError.
                # ==========================================

                try:

                    result = execute_sync(
                        lambda: self.sql_tool.execute(
                            {
                                "question": state["question"],
                                "read_only": True,
                            }
                        ),
                        name="database",
                        breaker=self.breaker,
                        timeout=settings.DATABASE_TIMEOUT_SECONDS,
                    )

                except CircuitOpenError:
                    self._record_failure(span, "circuit_open")
                    return self._store_failure(
                        state,
                        error=ERROR_CIRCUIT_OPEN,
                        reason="circuit_open",
                    )

                except DependencyTimeoutError:
                    self._record_failure(span, "timeout")
                    return self._store_failure(
                        state,
                        error=ERROR_TIMEOUT,
                        reason="timeout",
                    )

                except Exception as exc:

                    span.record_exception(exc)
                    self._record_failure(span, "service_unavailable")

                    logger.exception(
                        "Data agent dependency failed"
                    )

                    return self._store_failure(
                        state,
                        error=ERROR_UNAVAILABLE,
                        reason="service_unavailable",
                    )

                state["tool_result"] = result
                state["tool_name"] = "sql"

                # PR-30 — standardized contract: a short human-readable
                # preview as content, "database" as the source. The full
                # structured rows stay in metadata for the responder's
                # deterministic SQL formatting to use.
                columns = result.get(
                    "columns",
                    [],
                )

                rows = result.get(
                    "rows",
                    [],
                )

                row_count = result.get(
                    "row_count",
                    len(rows),
                )

                agent_result = build_result(
                    "data",
                    success=True,
                    content=(
                        f"Returned {row_count} row(s); "
                        "columns: "
                        + ", ".join(
                            str(column)
                            for column in columns
                        )
                    ),
                    sources=["database"],
                    metadata=result,
                )

                state["data_results"] = [
                    agent_result
                ]

                state.setdefault(
                    "agent_results",
                    {},
                )["data"] = agent_result

                span.set_attribute(
                    "agent.result_success",
                    True,
                )

                logger.info(
                    "Data agent completed"
                )

                return state

            except Exception as exc:

                span.record_exception(exc)

                span.set_status(
                    trace.Status(
                        trace.StatusCode.ERROR,
                        str(exc),
                    )
                )

                return self._store_failure(
                    state,
                    error=ERROR_UNAVAILABLE,
                    reason="unexpected",
                )

            finally:
                state["current_agent"] = None

    # ==========================================================
    # Helpers
    # ==========================================================

    @staticmethod
    def _tool_call_guard(state):
        tool_calls = state.get(
            "tool_call_count",
            0,
        ) + 1

        state["tool_call_count"] = tool_calls

        if tool_calls > settings.MAX_TOOL_CALLS:
            return "tool_limit", True

        return None, False

    def _store_failure(
        self,
        state,
        *,
        error: str,
        reason: str,
    ) -> dict:

        agent_result = build_result(
            "data",
            success=False,
            metadata={
                "reason": reason,
            },
            error=error,
        )

        state["data_results"] = [
            agent_result
        ]

        state.setdefault(
            "agent_results",
            {},
        )["data"] = agent_result

        return state

    @staticmethod
    def _record_failure(span, reason: str) -> None:

        try:

            if metrics.agent_failures is not None:
                metrics.agent_failures.add(
                    1,
                    {
                        "agent": "data",
                        "reason": reason,
                    },
                )

            if reason == "timeout" and metrics.agent_timeouts is not None:
                metrics.agent_timeouts.add(
                    1,
                    {
                        "agent": "data",
                    },
                )

        except Exception:
            pass

        span.set_attribute(
            "agent.success",
            False,
        )
        span.set_attribute(
            "agent.failure_reason",
            reason,
        )