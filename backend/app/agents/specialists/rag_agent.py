import logging

from opentelemetry import trace

from app.core.circuit_breaker import CircuitBreaker, CircuitOpenError
from app.core.config import settings
from app.core.reliability import execute_sync
from app.core.timeout import DependencyTimeoutError
from app.observability import metrics
from app.agents.result import build_result, truncate_text
from app.security.audit import audit_security_event
from app.security.guards import has_permission
from app.security.models import Permission

logger = logging.getLogger(__name__)

tracer = trace.get_tracer(
    "enterprise-ai-assistant"
)

# Process-wide circuit for Qdrant-backed retrieval: after repeated
# failures the breaker trips so we fail fast instead of hammering a
# down vector store on every request.
RAG_CIRCUIT = CircuitBreaker(name="qdrant")

# Safe, non-sensitive error text (never raw exceptions / hosts / URLs).
ERROR_TIMEOUT = "Internal document retrieval timed out."
ERROR_UNAVAILABLE = (
    "Internal document retrieval is temporarily unavailable. "
    "Please try again later."
)
ERROR_CIRCUIT_OPEN = (
    "Internal document retrieval is temporarily unavailable; "
    "too many recent failures. Please try again shortly."
)
ERROR_TOOL_LIMIT = "The maximum number of tool executions was reached."


class RAGAgent:

    def __init__(
        self,
        retriever,
        breaker: CircuitBreaker | None = None,
    ):
        self.retriever = retriever
        self.breaker = breaker or RAG_CIRCUIT

    def __call__(self, state):

        with tracer.start_as_current_span(
            "agent.rag"
        ) as span:

            span.set_attribute(
                "agent.name",
                "rag",
            )

            state["current_agent"] = "rag"

            try:

                # ==========================================
                # Permission boundary
                # ==========================================

                user = state.get("user_context")

                allowed = has_permission(
                    user,
                    Permission.RAG_READ,
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
                        resource="rag",
                        action="execute",
                        allowed=False,
                    )

                    result = build_result(
                        "rag",
                        success=False,
                        metadata={
                            "permission_denied": True,
                        },
                        error=(
                            "You are not authorized to access "
                            "internal documents."
                        ),
                    )

                    state["rag_results"] = [result]
                    state.setdefault(
                        "agent_results",
                        {},
                    )["rag"] = result

                    logger.warning(
                        "RAG agent permission denied"
                    )

                    return state

                # ==========================================
                # PR-28 tool-call limit
                # ==========================================

                reason, should_stop = self._tool_call_guard(
                    state
                )

                if should_stop:
                    result = self._store_failure(
                        state,
                        error=ERROR_TOOL_LIMIT,
                        reason=reason,
                    )
                    span.set_attribute(
                        "agent.failure_reason",
                        reason,
                    )
                    return result

                # ==========================================
                # PR-28 reliable dependency call
                #
                # Retriever = embedding + Qdrant. It is read-only so
                # transient failures may be retried; a timeout aborts
                # after RAG_TIMEOUT_SECONDS; the circuit breaker trips
                # after CIRCUIT_FAIL_MAX consecutive failures.
                # ==========================================

                try:

                    updated_state = execute_sync(
                        lambda: self.retriever(state),
                        name="qdrant",
                        breaker=self.breaker,
                        timeout=settings.RAG_TIMEOUT_SECONDS,
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
                        "RAG agent dependency failed"
                    )

                    return self._store_failure(
                        state,
                        error=ERROR_UNAVAILABLE,
                        reason="service_unavailable",
                    )

                chunks = updated_state.get(
                    "retrieved_chunks",
                    [],
                )

                # PR-30 — standardized contract: carry the actual
                # evidence (chunk content) plus human-readable sources
                # (document names) so the responder never has to read
                # internals of the retriever.
                content = truncate_text(
                    "\n\n".join(
                        getattr(
                            chunk,
                            "content",
                            str(chunk),
                        )
                        for chunk in chunks
                    ),
                    settings.MAX_CONTEXT_CHARS,
                )

                sources = list(
                    dict.fromkeys(
                        (
                            getattr(
                                chunk,
                                "document_name",
                                None,
                            )
                            or str(chunk.document_id)
                        )
                        for chunk in chunks
                    )
                )

                result = build_result(
                    "rag",
                    success=True,
                    content=content,
                    sources=sources,
                    metadata={
                        "result_count": len(
                            chunks
                        ),
                    },
                )

                state["rag_results"] = [
                    result
                ]

                state.setdefault(
                    "agent_results",
                    {},
                )["rag"] = result

                span.set_attribute(
                    "agent.result_count",
                    len(chunks),
                )

                logger.info(
                    "RAG agent completed result_count=%s",
                    len(chunks),
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
        """Increment the global tool-call counter and enforce the cap."""
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

        result = build_result(
            "rag",
            success=False,
            metadata={
                "reason": reason,
            },
            error=error,
        )

        state["rag_results"] = [result]
        state.setdefault(
            "agent_results",
            {},
        )["rag"] = result

        return state

    @staticmethod
    def _record_failure(span, reason: str) -> None:

        try:

            if metrics.agent_failures is not None:
                metrics.agent_failures.add(
                    1,
                    {
                        "agent": "rag",
                        "reason": reason,
                    },
                )

            if reason == "timeout" and metrics.agent_timeouts is not None:
                metrics.agent_timeouts.add(
                    1,
                    {
                        "agent": "rag",
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