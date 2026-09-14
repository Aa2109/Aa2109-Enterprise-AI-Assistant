"""Conversation-context helpers (PR memory fix).

Both ``RAGService`` and ``StreamingChatService`` load prior turns into
``state["history"]`` and the graph's memory_retriever populates
``state["retrieved_memories"]``, but until now only the responder's DIRECT
branch made use of them. These deterministic (no LLM) helpers turn that
context into self-contained inputs so a follow-up like *"what should I
study to master this field"* keeps its antecedent (*"data science"*) when
it reaches the router, a search/SQL tool, or the final synthesis.
"""

from __future__ import annotations

# Bounded turn window — mirrors the responder's ``history[-6:]``.
MAX_CONTEXT_TURNS = 6


def _recent_turns(state: dict, max_turns: int = MAX_CONTEXT_TURNS) -> list[dict]:
    """Return the most recent message turns from graph state (may be empty)."""
    return (state.get("history") or [])[-max_turns:]


def _turns_text(turns: list[dict]) -> str:
    return "\n".join(
        f"{'User' if m.get('role') == 'user' else 'Assistant'}: {m.get('content', '')}"
        for m in turns
    )


def _memories_text(state: dict) -> str:
    return "\n".join(
        content
        for memory in (state.get("retrieved_memories") or [])
        if isinstance(memory, dict)
        and (content := (memory.get("content") or "").strip())
    )


def build_contextualized_question(state: dict) -> str:
    """Turn a bare follow-up into a self-contained query for tool calls.

    Prepends the most recent conversation turns so a search/SQL tool sees
    the antecedent. Returns the raw question unchanged when there is no
    history. A trailing user turn that equals the current question is
    dropped — ``StreamingChatService`` persists the current message before
    loading history, so without this the question would repeat itself.
    """
    question = (state.get("question") or "").strip()

    if not question:
        return ""

    turns = _recent_turns(state)

    if not turns:
        return question

    # Dedupe the just-persisted current turn when the streaming service
    # already included it in history.
    last_content = (
        (turns[-1].get("content") or "").strip()
        if isinstance(turns[-1], dict)
        else ""
    )
    if question and last_content == question:
        turns = turns[:-1]

    if not turns:
        return question

    return f"{_turns_text(turns)}\n\nCurrent question: {question}"


def build_memory_and_history_context(state: dict) -> str:
    """Labeled context block for LLM prompts: memory + recent history.

    Mirrors the phrasing already used by the responder's DIRECT branch.
    Returns an empty string when neither memories nor history exist.
    """
    blocks: list[str] = []

    memories = _memories_text(state)
    if memories:
        blocks.append(f"Relevant user memory:\n{memories}")

    turns = _recent_turns(state)
    if turns:
        blocks.append(f"Conversation history:\n{_turns_text(turns)}")

    return "\n\n".join(blocks)