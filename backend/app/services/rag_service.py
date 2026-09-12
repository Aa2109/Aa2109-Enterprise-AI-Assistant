from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    SourceChunk,
)
from app.core.cache import (
    build_cache_key,
    cached_value_to_json,
    get_response_cache,
    json_to_cached_value,
    permission_scope,
)
from app.core.concurrency import (
    AgentConcurrencyLimitExceeded,
    agent_execution_slot,
)
from app.core.enums.message import MessageRole
from fastapi import HTTPException, status as http_status
from app.security.models import UserContext
from app.security.prompt_guard import validate_user_prompt
from uuid import UUID, uuid4

import time

from app.observability import metrics

from opentelemetry import trace

tracer = trace.get_tracer(
    "enterprise-ai-assistant"
)

import logging

logger = logging.getLogger(__name__)


def _safe_counter_add(counter, value: int = 1, attributes=None) -> None:
    # Metrics must never break the request path (e.g. before OpenTelemetry
    # is configured, or during a Prometheus scrape outage).
    try:
        if counter is not None:
            if attributes:
                counter.add(value, attributes)
            else:
                counter.add(value)
    except Exception:
        pass


class RAGService:

    def __init__(
        self,
        graph,
        conversation_service,
    ):
        self.graph = graph
        self.conversation_service = conversation_service

    def _save_conversation_pair(
        self,
        *,
        conversation_id,
        query: str,
        answer: str,
    ) -> None:
        """Persist the user query and final assistant answer pair.

        Shared by the normal path (fresh answer) and the cached path,
        so the conversation history always mirrors what the user saw.
        """
        self.conversation_service.add_message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=query,
        )

        self.conversation_service.add_message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=answer,
        )

    def answer(
        self,
        request: ChatRequest,
        user: UserContext,
        request_id: str | None = None,
    ) -> ChatResponse:

        start_time = time.perf_counter()
        _safe_counter_add(metrics.agent_requests)
        with tracer.start_as_current_span(
        "rag.answer"
        ) as rag_span:

            rag_span.set_attribute(
                "request_id",
                request_id or "",
            )

            rag_span.set_attribute(
            "conversation.id",
            str(request.conversation_id),
            )

            if request.owner_id:
                rag_span.set_attribute(
                    "owner.id",
                    str(request.owner_id),
                )

            try:

                # ==================================================
                # Prompt guard — validate the user prompt before
                # any retrieval or LLM work.
                # ==================================================

                try:
                    validate_user_prompt(request.query)
                except ValueError as exc:
                    raise HTTPException(
                        status_code=http_status.HTTP_400_BAD_REQUEST,
                        detail=str(exc),
                    ) from exc

                # Validate Conversation
                conversation = self.conversation_service.get(
                    request.conversation_id
                )

                if conversation is None:
                    raise ValueError(
                        f"Conversation not found: "
                        f"{request.conversation_id}"
                    )

                # 1. Load Conversation history
                history = self.conversation_service.history(
                    request.conversation_id
                )

                logger.info(
                    "Conversation history loaded count=%s",
                    len(history),
                )

                # ==================================================
                # PR-28 response cache — stable RAG answers only.
                #
                # The key embeds the caller's authorization scope and
                # the knowledge version, so a cached admin answer can
                # never leak to a lower-privileged caller, and a
                # document re-index (knowledge_version bump) naturally
                # invalidates old entries.
                # ==================================================

                cache = get_response_cache()

                cache_key = build_cache_key(
                    namespace="rag",
                    query=request.query,
                    scope=permission_scope(user),
                )

                cached_payload = cache.get(cache_key)

                if cached_payload is not None:

                    cached = json_to_cached_value(cached_payload)

                    answer = cached.get("answer")

                    if answer:
                        logger.info(
                            "Response cache HIT key=%s",
                            cache_key,
                        )

                        self._save_conversation_pair(
                            conversation_id=request.conversation_id,
                            query=request.query,
                            answer=answer,
                        )

                        return ChatResponse(
                            answer=answer,
                            sources=[
                                SourceChunk(**source)
                                for source in cached.get(
                                    "sources",
                                    [],
                                )
                            ],
                            citations=cached.get(
                                "citations",
                                [],
                            ),
                            status="completed",
                            approval_id=None,
                        )

                # ==================================================
                # 2. Build graph state
                # ==================================================

                # PR-30 — correlate with the middleware request_id (or a
                # fresh id) so one user request shares one id across the
                # graph state, spans and logs.
                run_id = request_id or str(uuid4())
                serializable_history = [
                    {
                        "role": message.role.value,
                        "content": message.content,
                    }
                    for message in history
                ]
                
                state = {
                    "question": request.query,
                    "conversation_id": request.conversation_id,
                    "run_id": run_id, # new added...
                    # Authoritative owner: the authenticated token wins,
                    # never a caller-supplied owner_id.
                    "owner_id": UUID(user.user_id),
                    "document_id": request.document_id,
                    "limit": request.limit,
                    "history": serializable_history,
                    "user_context": user,

                    # Agent execution state(new added)
                    "iteration": 0,
                    "tool_call_count": 0,
                    "retry_count": 0,
                    "tool_executions": [],

                    "agent_step": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "token_budget_exceeded": False,

                    "tool_name": None,
                    "tool_arguments": None,
                    "tool_result": None,
                    "tool_error": None,

                    "retrieved_chunks": [],
                    "web_results": [],

                    "retrieved_memories": [],
                    "memory_candidates": [],

                    "approval_required": False,
                    "approval_request_id": None,
                    "approval_status": None,


                }

                # ==================================================
                # 3. LangGraph thread configuration
                # ==================================================

                config = {
                    "configurable": {
                        "thread_id": run_id
                    }
                }

                # ==================================================
                # 4. Invoke graph
                # ==================================================

                # result = self.graph.invoke(state, config=config,)
                with tracer.start_as_current_span(
                    "agent.run"
                ) as span:

                    span.set_attribute(
                        "agent.run_id", run_id,
                    )

                    span.set_attribute(
                        "request_id",
                        run_id,
                    )

                    try:

                        with agent_execution_slot():

                            result = self.graph.invoke(
                                state,
                                config=config,
                            )
                        span.set_attribute(
                            "agent.iteration_count",
                            result.get("iteration", 0),
                        )

                        span.set_attribute(
                            "agent.tool_call_count",
                            result.get("tool_call_count", 0),
                        )

                        # PR-30 — token usage on the run span so "why did
                        # this request cost X tokens" is self-service.
                        span.set_attribute(
                            "agent.total_tokens",
                            result.get("total_tokens", 0),
                        )

                        span.set_attribute(
                            "agent.input_tokens",
                            result.get("input_tokens", 0),
                        )

                        span.set_attribute(
                            "agent.output_tokens",
                            result.get("output_tokens", 0),
                        )

                        # if result.get("decision"):
                        #     span.set_attribute(
                        #         "agent.final_decision",
                        #         result.get("tool_call_count", 0),
                        #     )
                        decision = result.get("decision")
                        if decision:
                            span.set_attribute(
                                "agent.final_decision",
                                decision,
                            )

                    except Exception as exc:

                        span.record_exception(
                            exc
                        )

                        span.set_status(
                            trace.Status(
                                trace.StatusCode.ERROR,
                                str(exc),
                            )
                        )

                        raise

                # ==================================================
                # 5. HITL approval interrupt
                # ==================================================

                interrupts = result.get(
                    "__interrupt__",
                    []
                )

                if interrupts:

                    interrupt_value = None

                    first_interrupt = interrupts[0]

                    if hasattr(
                        first_interrupt,
                        "value",
                    ):
                        interrupt_value = first_interrupt.value
                        

                    elif isinstance(
                        first_interrupt,
                        dict,
                    ):
                        interrupt_value = first_interrupt

                    approval_id = None

                    if isinstance(
                        interrupt_value,
                        dict,
                    ):

                        approval_id = interrupt_value.get("approval_id")

                    # --------------------------------------------------
                    # Save USER message only.
                    #
                    # Do NOT save an assistant answer because the
                    # agent has not completed yet.
                    # --------------------------------------------------

                    self.conversation_service.add_message(
                        conversation_id=request.conversation_id,
                        role=MessageRole.USER,
                        content=request.query,
                    )

                    return ChatResponse(
                        answer=None,
                        sources=[],
                        status="approval_required",
                        approval_id=approval_id,
                    )

                # ==================================================
                # 6. Normal completed execution
                # ==================================================

                retrieved_chunks = result.get(
                    "retrieved_chunks",
                    [],
                )

                answer = result.get(
                    "answer"
                )

                # ==================================================
                # Safety check
                # ==================================================

                if answer is None:

                    raise RuntimeError(
                        "Agent execution completed without an answer "
                        "and without an approval interrupt."
                    )

                # ==================================================
                # 7 & 8. Save USER + ASSISTANT messages
                # ==================================================

                self._save_conversation_pair(
                    conversation_id=request.conversation_id,
                    query=request.query,
                    answer=answer,
                )

                # ==================================================
                # PR-28 — cache stable document-grounded answers only.
                #
                # ``retrieved_chunks`` is populated only on the RAG /
                # FINAL-with-context path, so research and data results
                # (dynamic, permission-sensitive) are never cached.
                # A failed retrieval leaves it empty, so degraded
                # responses are not cached either.
                # ==================================================

                if retrieved_chunks and answer:

                    cache.set(
                        cache_key,
                        cached_value_to_json(
                            {
                                "answer": answer,
                                "citations": result.get(
                                    "citations",
                                    [],
                                ),
                                "sources": [
                                    {
                                        "chunk_id": str(hit.chunk_id),
                                        "document_id": str(
                                            hit.document_id
                                        ),
                                        "chunk_index": hit.chunk_index,
                                        "content": hit.content,
                                        "score": hit.score,
                                    }
                                    for hit in retrieved_chunks
                                ],
                            }
                        ),
                    )

                    logger.info(
                        "Response cache MISS stored key=%s",
                        cache_key,
                    )

                # ==================================================
                # 9. Return normal response
                # ==================================================

                return ChatResponse(
                    answer=answer,
                    sources=[
                        SourceChunk(
                            chunk_id=hit.chunk_id,
                            document_id=hit.document_id,
                            chunk_index=hit.chunk_index,
                            content=hit.content,
                            score=hit.score,
                        )
                        for hit in retrieved_chunks
                    ],
                    citations=result.get(
                        "citations",
                        [],
                    ),
                    status="completed",
                    approval_id=None,
                )
            except AgentConcurrencyLimitExceeded as exc:
                _safe_counter_add(metrics.agent_failures)
                raise HTTPException(
                    status_code=(
                        http_status.HTTP_503_SERVICE_UNAVAILABLE
                    ),
                    detail=str(exc),
                ) from exc
            except Exception as exc:
                _safe_counter_add(metrics.agent_failures)
                rag_span.record_exception(exc)
                rag_span.set_status(
                    trace.Status(
                        trace.StatusCode.ERROR,
                        str(exc),
                    )
                )
                raise
            finally:
                try:
                    if metrics.agent_duration_seconds is not None:
                        metrics.agent_duration_seconds.record(
                            time.perf_counter() - start_time
                        )
                except Exception:
                    pass

