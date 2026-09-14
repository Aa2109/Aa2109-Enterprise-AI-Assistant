"""PR-28 — AI cost guard and token budget tracking.

Agentic loops can burn tokens very quickly (supervisor -> RAG ->
supervisor -> ...). This module enforces a per-request token budget so
one runaway user request cannot produce a runaway API bill.
"""

from __future__ import annotations

import logging

from dataclasses import dataclass

from app.core.config import settings
from app.observability import metrics

logger = logging.getLogger(__name__)


class BudgetExceededError(RuntimeError):
    """Raised when an operation would exceed the token budget."""


@dataclass
class UsageBudget:
    """A fixed token ceiling with monotonic consumption tracking."""

    max_tokens: int = settings.MAX_TOTAL_TOKENS
    used_tokens: int = 0

    def consume(self, tokens: int) -> None:
        if tokens < 0:
            raise ValueError("tokens must be non-negative")

        if self.used_tokens + tokens > self.max_tokens:
            raise BudgetExceededError(
                f"AI token budget exceeded "
                f"(used={self.used_tokens}, request={tokens}, "
                f"max={self.max_tokens})"
            )

        self.used_tokens += tokens

    @property
    def remaining(self) -> int:
        return self.max_tokens - self.used_tokens

    @property
    def exceeded(self) -> bool:
        return self.used_tokens >= self.max_tokens


def estimate_tokens(text: str | None) -> int:
    """Rough token estimate (~4 chars per token).

    Production systems use a real tokenizer; a deterministic estimate is
    enough for a hard budget guard and for cost observability.
    """
    if not text:
        return 0

    return max(1, len(text) // 4)


def _safe_record(count: int, labels: dict) -> None:
    try:
        if metrics.llm_total_tokens is None:
            return
        metrics.llm_total_tokens.add(count, labels)
    except Exception:
        pass


def charge_usage(state: dict, *, input_text: str, output_text: str) -> dict:
    """Add estimated token usage to graph state and mark over-budget.

    Mutates and returns ``state`` so callers can thread it through the
    graph without extra plumbing.
    """
    input_tokens = estimate_tokens(input_text)
    output_tokens = estimate_tokens(output_text)

    total_used = (
        state.get("total_tokens", 0)
        + input_tokens
        + output_tokens
    )

    state["input_tokens"] = (
        state.get("input_tokens", 0) + input_tokens
    )
    state["output_tokens"] = (
        state.get("output_tokens", 0) + output_tokens
    )
    state["total_tokens"] = total_used

    _safe_record(
        input_tokens,
        {"token": "input"},
    )
    _safe_record(
        output_tokens,
        {"token": "output"},
    )

    if total_used > settings.MAX_TOTAL_TOKENS:
        state["token_budget_exceeded"] = True

        try:
            if metrics.token_budget_exceeded is not None:
                metrics.token_budget_exceeded.add(1)
        except Exception:
            pass

        logger.warning(
            "Token budget exceeded total=%s max=%s",
            total_used,
            settings.MAX_TOTAL_TOKENS,
        )

    return state