"""PR-30 — final synthesis policy ("AI policy layer").

The final responder turns raw specialist ``AgentResult``-shaped dicts into
a user-facing answer. This module centralizes the *rules* that answer
must obey, so they are testable and independent of the LLM wiring:

- Only successful results count as evidence.
- Failed / unavailable / unauthorized agents are reported honestly and
  with safe, non-sensitive wording — never invented, never raw errors.
- A RAG run that found no evidence must not be turned into an answer
  (no fabrication) when nothing else succeeded.
- Citations are collected from successful agents and deduplicated.

The responder only needs the standard six fields of an ``AgentResult``:
``agent``, ``success``, ``content``, ``sources``, ``metadata``, ``error``.
"""

from __future__ import annotations

from typing import Any

from app.agents.result import result_to_model
from app.schemas.agents_schema import AgentResult

# Deterministic, non-sensitive answers (never a raw exception in here).

PERMISSION_DENIED_ANSWER = (
    "You are not authorized to access the requested data."
)

ALL_FAILED_ANSWER_PREFIX = (
    "I couldn't complete the request because the following "
    "specialists were unavailable: "
)

NO_INTERNAL_DOCUMENT_ANSWER = (
    "I couldn't find any relevant internal documentation for that "
    "question, so I won't invent an answer. Please rephrase the "
    "question or confirm the relevant document has been uploaded."
)


class SynthesisPolicy:
    """Evaluate a set of agent results against the synthesis rules."""

    def __init__(
        self,
        successful: dict[str, AgentResult],
        failed: dict[str, AgentResult],
    ):
        self.successful = successful
        self.failed = failed

    # ----------------------------------------------------------
    # Construction
    # ----------------------------------------------------------

    @classmethod
    def from_results(
        cls,
        agent_results: dict[str, Any],
    ) -> SynthesisPolicy:
        """Split raw agent_results dicts into typed successful/failed sets.

        Non-dict values are ignored defensively.
        """
        successful: dict[str, AgentResult] = {}
        failed: dict[str, AgentResult] = {}

        for name, raw in agent_results.items():
            if not isinstance(raw, dict):
                continue
            try:
                result = result_to_model(raw)
            except (KeyError, TypeError, ValueError):
                continue
            if result.success:
                successful[name] = result
            else:
                failed[name] = result

        return cls(
            successful=successful,
            failed=failed,
        )

    # ----------------------------------------------------------
    # Properties / rule checks
    # ----------------------------------------------------------

    @property
    def permission_denied(self) -> bool:
        return any(
            isinstance(result.metadata, dict)
            and result.metadata.get("permission_denied")
            for result in self.failed.values()
        )

    @property
    def has_successful(self) -> bool:
        return bool(self.successful)

    def result_has_evidence(self, result: AgentResult) -> bool:
        if isinstance(result.metadata, dict) and (
            result.metadata.get("result_count", 0) or 0
        ):
            return True
        return bool((result.content or "").strip())

    @property
    def rag_no_evidence(self) -> bool:
        """RAG ran successfully but produced no retrievable documents."""
        rag_result = self.successful.get("rag")
        if rag_result is None:
            return False
        return not self.result_has_evidence(rag_result)

    @property
    def any_evidence(self) -> bool:
        return any(
            self.result_has_evidence(result)
            for result in self.successful.values()
        )

    # ----------------------------------------------------------
    # User-facing helpers
    # ----------------------------------------------------------

    def collect_sources(self) -> list[str]:
        """Deduplicated, order-preserving citation list across agents."""
        sources: list[str] = []
        for result in self.successful.values():
            for source in result.sources:
                if source not in sources:
                    sources.append(source)
        return sources

    def failure_summary(self) -> str:
        """One safe line per failed agent, in insertion order."""
        return "\n".join(
            f"- {name}: {self.safe_failure_description(name, result)}"
            for name, result in self.failed.items()
        ) or "None"

    @staticmethod
    def safe_failure_description(
        agent_name: str,
        result: AgentResult,
    ) -> str:
        """Map an unavailable agent to safe, non-sensitive wording."""
        if isinstance(result.metadata, dict) and result.metadata.get(
            "permission_denied"
        ):
            return "access was denied"

        if agent_name == "research":
            return "external research was unavailable"
        if agent_name == "rag":
            return "internal document retrieval was unavailable"
        if agent_name == "data":
            return "structured data access was unavailable"

        return "the specialist was unavailable"