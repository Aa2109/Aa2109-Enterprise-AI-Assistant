import logging

from opentelemetry import trace

from app.core.circuit_breaker import CircuitBreaker, CircuitOpenError
from app.core.config import settings
from app.core.reliability import execute_sync
from app.core.timeout import DependencyTimeoutError
from app.observability import metrics
from app.security.audit import audit_security_event
from app.security.guards import has_permission
from app.security.models import Permission

logger = logging.getLogger(__name__)

tracer = trace.get_tracer(
    "enterprise-ai-assistant"
)

# Process-wide circuit for the web search dependency.
RESEARCH_CIRCUIT = CircuitBreaker(name="web_search")

# Safe, non-sensitive error text — never raw exceptions/hosts/URLs.
ERROR_TIMEOUT = "The external research service timed out."
ERROR_UNAVAILABLE = (
    "The external research service is temporarily unavailable. "
    "Please try again later."
)
ERROR_CIRCUIT_OPEN = (
    "The external research service is temporarily unavailable; "
    "too many recent failures. Please try again shortly."
)
ERROR_TOOL_LIMIT = "The maximum number of tool executions was reached."


class ResearchAgent:

    def __init__(
        self,
        web_search_tool,
        breaker: CircuitBreaker | None = None,
    ):
        self.web_search_tool = web_search_tool
        self.breaker = breaker or RESEARCH_CIRCUIT

    def __call__(self, state):

        with tracer.start_as_current_span(
            "agent.research"
        ) as span:

            span.set_attribute(
                "agent.name",
                "research",
            )

            state["current_agent"] = "research"

            try:

                logger.info(
                    "Research agent started=%r",
                    state.get("question"),
                )

                # ==========================================
                # Permission boundary
                # ==========================================

                user = state.get("user_context")

                allowed = has_permission(
                    user,
                    Permission.RESEARCH,
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
                        resource="research",
                        action="execute",
                        allowed=False,
                    )

                    agent_result = {
                        "agent": "research",
                        "success": False,
                        "content": "",
                        "metadata": {
                            "permission_denied": True,
                        },
                        "error": (
                            "You are not authorized to run "
                            "external research."
                        ),
                    }

                    state["research_results"] = [
                        agent_result
                    ]

                    state.setdefault(
                        "agent_results",
                        {},
                    )["research"] = agent_result

                    logger.warning(
                        "Research agent permission denied"
                    )

                    return state

                if "[test-research-failure]" in state["question"]:
                    raise RuntimeError("Simulated research agent failure")

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
                # Web search is a read-only external GET. Transient
                # failures retry with backoff; a timeout aborts after
                # WEB_SEARCH_TIMEOUT_SECONDS; the circuit breaker trips
                # after repeated failures.
                # ==========================================

                try:

                    result = execute_sync(
                        lambda: self.web_search_tool.execute(
                            {
                                "query": state["question"],
                                "max_results": 5,
                            }
                        ),
                        name="web_search",
                        breaker=self.breaker,
                        timeout=settings.WEB_SEARCH_TIMEOUT_SECONDS,
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
                        "Research agent dependency failed"
                    )

                    return self._store_failure(
                        state,
                        error=ERROR_UNAVAILABLE,
                        reason="service_unavailable",
                    )

                web_results = result.get(
                    "results",
                    [],
                )

                state["web_results"] = web_results

                agent_result = {
                    "agent": "research",
                    "success": True,
                    "content": "",
                    "metadata": {
                        "result_count": len(
                            web_results
                        ),
                    },
                }

                state["research_results"] = [
                    agent_result
                ]

                state.setdefault(
                    "agent_results",
                    {},
                )["research"] = agent_result

                span.set_attribute(
                    "agent.result_count",
                    len(web_results),
                )

                logger.info(
                    "Research agent completed "
                    "result_count=%s",
                    len(web_results),
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

        agent_result = {
            "agent": "research",
            "success": False,
            "content": "",
            "metadata": {
                "reason": reason,
            },
            "error": error,
        }

        state["research_results"] = [
            agent_result
        ]

        state.setdefault(
            "agent_results",
            {},
        )["research"] = agent_result

        return state

    @staticmethod
    def _record_failure(span, reason: str) -> None:

        try:

            if metrics.agent_failures is not None:
                metrics.agent_failures.add(
                    1,
                    {
                        "agent": "research",
                        "reason": reason,
                    },
                )

            if reason == "timeout" and metrics.agent_timeouts is not None:
                metrics.agent_timeouts.add(
                    1,
                    {
                        "agent": "research",
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