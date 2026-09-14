import logging
import time

from opentelemetry import trace

from app.observability import metrics


tracer = trace.get_tracer(
    "enterprise-ai-assistant"
)

logger = logging.getLogger(__name__)


class MemoryRetrieverNode:

    def __init__(
        self,
        memory_retriever,
    ):
        self.memory_retriever = memory_retriever

    def __call__(
        self,
        state,
    ):

        user_id = state.get("owner_id")
        question = state.get("question")

        if not user_id or not question:

            state["retrieved_memories"] = []

            return state

        start_time = time.perf_counter()

        metrics.memory_retrieval.add(
            1
        )

        try:

            with tracer.start_as_current_span(
                "memory.retrieve"
            ) as span:

                span.set_attribute(
                    "memory.top_k",
                    5,
                )

                memories = self.memory_retriever.retrieve(
                    user_id=user_id,
                    query=question,
                    top_k=5,
                )

                span.set_attribute(
                    "memory.result_count",
                    len(memories),
                )

                state["retrieved_memories"] = [
                    {
                        "memory_id": str(
                            memory["memory_id"]
                        ),
                        "user_id": str(
                            memory["user_id"]
                        ),
                        "content": memory["content"],
                        "memory_type": memory["memory_type"],
                        "importance": float(
                            memory["importance"]
                        ),
                        "score": float(
                            memory["score"]
                        ),
                    }
                    for memory in memories
                ]

        except Exception as exc:

            logger.exception(
                "Memory retrieval failed: %s",
                exc,
            )

            state["retrieved_memories"] = []

        finally:

            metrics.memory_retrieval_duration_seconds.record(
                time.perf_counter() - start_time
            )

        return state