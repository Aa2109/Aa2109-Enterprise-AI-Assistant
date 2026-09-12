"""Standardized specialist result contract (PR-30).

Every specialist returns a plain dict that conforms to
``app.schemas.agents_schema.AgentResult``. Keeping the results as plain
dicts (rather than pydantic instances) means they serialize cleanly
through the LangGraph state checkpoint, while the schema still gives us
a single source of truth for the contract.

The supervisor and final responder depend only on:

    agent      # which specialist produced the result
    success    # True / False
    content    # evidence the specialist gathered
    sources    # human-readable citation list
    metadata   # structured, non-sensitive detail
    error      # safe, non-sensitive explanation on failure
"""

from __future__ import annotations

from typing import Any

from app.schemas.agents_schema import AgentName, AgentResult


def build_result(
    agent: AgentName | str,
    *,
    success: bool,
    content: str = "",
    sources: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Build a canonical AgentResult-shaped dict.

    Non-sensitive only: callers must pass safe, user-facing error text,
    never raw exceptions, hosts, URLs, or stack traces.
    """
    return {
        "agent": (
            agent.value
            if isinstance(agent, AgentName)
            else str(agent)
        ),
        "success": bool(success),
        "content": content or "",
        "sources": list(sources or []),
        "metadata": dict(metadata or {}),
        "error": error,
    }


def result_to_model(result: dict[str, Any]) -> AgentResult:
    """Coerce a specialist result dict back into the contract model."""
    return AgentResult(
        agent=result["agent"],
        success=result["success"],
        content=result.get("content", ""),
        sources=result.get("sources", []),
        metadata=result.get("metadata", {}),
        error=result.get("error"),
    )


def validate_result(result: dict[str, Any]) -> list[str]:
    """Validate a specialist result shape; returns a list of violations.

    Empty list means the result conforms to the AgentResult contract.
    Used by tests to keep the specialists honest without coupling them
    to pydantic.
    """
    violations: list[str] = []

    if "agent" not in result or result.get("agent") not in {
        name.value for name in AgentName
    }:
        violations.append(
            f"invalid agent name: {result.get('agent')!r}"
        )

    if "success" not in result:
        violations.append("missing success flag")

    if not isinstance(result.get("content", ""), str):
        violations.append("content must be a string")

    if not isinstance(result.get("sources", []), list):
        violations.append("sources must be a list of strings")

    if not isinstance(result.get("metadata", {}), dict):
        violations.append("metadata must be a dict")

    return violations


def truncate_text(
    text: str | None,
    max_chars: int,
) -> str:
    """Cap oversized evidence so it never blows the LLM context window."""
    if not text:
        return ""
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars]
    return text