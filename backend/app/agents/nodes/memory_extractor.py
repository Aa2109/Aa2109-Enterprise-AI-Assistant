import logging

from opentelemetry import trace
tracer = trace.get_tracer(
    "enterprise-ai-assistant"
)

import time
from app.observability import metrics

logger = logging.getLogger(__name__)

class MemoryExtractorNode:

    def __init__(
        self,
        extractor,
        memory_service,
    ):
        self.extractor = extractor
        self.memory_service = memory_service

    def __call__(self, state):


        user_id = state.get("owner_id")
        question = state.get("question")
        answer = state.get("answer")

        # --------------------------------------------------
        # Cannot store anything without a user
        # --------------------------------------------------

        if not user_id:

            state["memory_candidates"] = []

            return state

        # --------------------------------------------------
        # Need both sides of the interaction
        # --------------------------------------------------

        if not question or not answer:

            state["memory_candidates"] = []

            return state

        start_time = time.perf_counter()

        metrics.memory_extraction.add(1)

        try:

            with tracer.start_as_current_span(
                "memory.extract"
            ) as span:

                try:

                    extraction = self.extractor.extract(
                        user_message=question,
                        assistant_message=answer,
                    )

                    candidates = extraction.memories

                    span.set_attribute(
                        "memory.candidate_count",
                        len(candidates),
                    )

                except Exception as exc:

                    span.record_exception(exc)

                    span.set_status(
                        trace.Status(
                            trace.StatusCode.ERROR,
                            str(exc),
                        )
                    )

                    raise

            # ==================================================
            # Validate candidates
            # ==================================================

            validated_candidates = []

            for memory in candidates:

                evidence = memory.evidence.strip()

                if not evidence:
                    continue

                if evidence.lower() not in question.lower():
                    continue

                validated_candidates.append(memory)

            candidates = validated_candidates

            state["memory_candidates"] = [
                memory.model_dump(mode="json")
                for memory in candidates
            ]

            # ==================================================
            # Persist
            # ==================================================

            saved_memories = []

            for memory in candidates:
                saved = self.memory_service.save_memory(
                    user_id=user_id,
                    memory=memory,
                )

                if saved is not None:

                    saved_memories.append(
                        {
                            "id": str(saved.id),
                            "user_id": str(saved.user_id),
                            "memory_type": saved.memory_type,
                            "content": saved.content,
                            "importance": saved.importance,
                        }
                    )

            state["memories"] = saved_memories

        except Exception as exc:

            logger.exception(
                "[MEMORY] Memory extraction failed: %s",
                exc,
            )

            state["memory_candidates"] = []
            state["memories"] = []

        finally:

            metrics.memory_extraction_duration_seconds.record(
                time.perf_counter() - start_time
            )