"""Conversation-context helpers (PR memory fix).

A follow-up message like *"what should I study to master this field"* must
carry its earlier turns ("data science") into the router, the search/SQL
tools and the final synthesis. These tests pin the two helpers in
``app/agents/context.py`` that build those self-contained inputs.
"""

from app.agents.context import (
    build_contextualized_question,
    build_memory_and_history_context,
)

DATA_SCIENCE_Q = "What is data science, in two lines?"
DATA_SCIENCE_A = "Data science is an interdisciplinary field that combines statistics, computer science, and domain expertise."
FOLLOW_UP = "What should I study to master this field?"

REAL_HISTORY = [
    {"role": "user", "content": DATA_SCIENCE_Q},
    {"role": "assistant", "content": DATA_SCIENCE_A},
]


# ============================================================
# build_contextualized_question
# ============================================================


def test_no_history_returns_raw_question():
    state = {"question": FOLLOW_UP, "history": []}

    assert build_contextualized_question(state) == FOLLOW_UP


def test_no_question_returns_empty_string():
    state = {"question": "", "history": REAL_HISTORY}

    assert build_contextualized_question(state) == ""


def test_followup_prepends_recent_turns():
    state = {"question": FOLLOW_UP, "history": REAL_HISTORY}

    query = build_contextualized_question(state)

    assert query.endswith(f"\n\nCurrent question: {FOLLOW_UP}")
    assert "Data science is" in query
    # The antecedent is now inline for the search tool.
    assert DATA_SCIENCE_A in query


def test_trailing_turn_that_is_the_current_question_is_deduped():
    # StreamingChatService persists the current message before loading
    # history, so the last history turn equals the new question.
    state = {
        "question": FOLLOW_UP,
        "history": [*REAL_HISTORY, {"role": "user", "content": FOLLOW_UP}],
    }

    query = build_contextualized_question(state)

    # The current question must appear exactly once (in "Current question:").
    assert query.count(FOLLOW_UP) == 1


def test_only_last_six_turns_are_used():
    spam = [
        {"role": "user", "content": f"old question {i}"}
        for i in range(12)
    ]
    state = {"question": FOLLOW_UP, "history": [*spam, *REAL_HISTORY]}

    query = build_contextualized_question(state)

    assert "old question 0" not in query
    assert "old question 11" in query  # within the trailing window


# ============================================================
# build_memory_and_history_context
# ============================================================


def test_context_block_includes_memories_and_history():
    state = {
        "question": FOLLOW_UP,
        "history": REAL_HISTORY,
        "retrieved_memories": [
            {
                "memory_id": "1",
                "user_id": "u1",
                "content": "The user is studying data science.",
                "memory_type": "semantic",
                "importance": 0.5,
                "score": 0.6,
            }
        ],
    }

    block = build_memory_and_history_context(state)

    assert "Relevant user memory:" in block
    assert "The user is studying data science." in block
    assert "Conversation history:" in block
    assert DATA_SCIENCE_A in block


def test_context_block_empty_without_memories_or_history():
    state = {
        "question": FOLLOW_UP,
        "history": [],
        "retrieved_memories": [],
    }

    assert build_memory_and_history_context(state) == ""


def test_context_block_omits_empty_memory_entries():
    state = {
        "question": FOLLOW_UP,
        "history": REAL_HISTORY,
        "retrieved_memories": [
            {"content": "  "},
            {"content": None},
        ],
    }

    block = build_memory_and_history_context(state)

    assert "Relevant user memory:" not in block
    assert "Conversation history:" in block