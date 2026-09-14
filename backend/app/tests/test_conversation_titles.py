"""Conversation titling, renaming and history-window behaviour.

Covers the sidebar-facing pieces added for the frontend: threads name
themselves after the first query, users can rename them, and the
conversations API can read a whole thread rather than the short window
the agent graph feeds back to the LLM.
"""

from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.conversation_service import (
    DEFAULT_TITLE,
    TITLE_MAX_LENGTH,
    ConversationService,
    derive_title,
)


class FakeConversationRow:
    def __init__(self, title=DEFAULT_TITLE):
        self.id = uuid4()
        self.owner_id = uuid4()
        self.title = title


class FakeConversationRepo:
    def __init__(self, conversation=None):
        self.conversation = conversation
        self.updates = 0

    def get(self, conversation_id):
        return self.conversation

    def update(self, conversation):
        self.updates += 1
        return conversation


class FakeMessageRepo:
    def __init__(self):
        self.calls = []

    def history(self, conversation_id, limit=10):
        self.calls.append(limit)
        return []


def make_service(conversation=None):
    return ConversationService(
        conversation_repo=FakeConversationRepo(conversation),
        message_repo=FakeMessageRepo(),
    )


# ============================================================
# derive_title
# ============================================================


def test_derive_title_keeps_a_short_query_verbatim():
    assert derive_title("What is our leave policy?") == (
        "What is our leave policy?"
    )


def test_derive_title_collapses_whitespace():
    assert derive_title("  what is   in the docs? ") == (
        "what is in the docs?"
    )


def test_derive_title_truncates_on_a_word_boundary():
    query = (
        "Compare our leave policy with current industry "
        "practices and summarise the differences"
    )

    title = derive_title(query)

    assert title.endswith("…")
    assert len(title) <= TITLE_MAX_LENGTH + 1
    # Cut between words, so no partial word is left behind.
    assert query.startswith(title[:-1])
    assert not title[:-1].endswith(" ")


def test_derive_title_cuts_a_single_long_word():
    title = derive_title("A" * 120)

    assert title == "A" * TITLE_MAX_LENGTH + "…"


def test_derive_title_falls_back_for_blank_input():
    assert derive_title("   ") == DEFAULT_TITLE


# ============================================================
# ensure_title
# ============================================================


def test_ensure_title_names_an_untitled_conversation():
    conversation = FakeConversationRow()
    service = make_service(conversation)

    service.ensure_title(conversation.id, "What is our leave policy?")

    assert conversation.title == "What is our leave policy?"
    assert service.conversation_repo.updates == 1


def test_ensure_title_never_overwrites_an_existing_title():
    conversation = FakeConversationRow(title="Q3 planning")
    service = make_service(conversation)

    service.ensure_title(conversation.id, "a different question")

    assert conversation.title == "Q3 planning"
    assert service.conversation_repo.updates == 0


def test_ensure_title_ignores_a_missing_conversation():
    service = make_service(None)

    assert service.ensure_title(uuid4(), "anything") is None


# ============================================================
# rename
# ============================================================


def test_rename_trims_and_persists():
    conversation = FakeConversationRow()
    service = make_service(conversation)

    service.rename(conversation.id, "  Leave policy review  ")

    assert conversation.title == "Leave policy review"
    assert service.conversation_repo.updates == 1


def test_rename_rejects_a_blank_title():
    conversation = FakeConversationRow()
    service = make_service(conversation)

    with pytest.raises(HTTPException) as exc:
        service.rename(conversation.id, "   ")

    assert exc.value.status_code == 422
    assert conversation.title == DEFAULT_TITLE


def test_rename_404s_for_a_missing_conversation():
    service = make_service(None)

    with pytest.raises(HTTPException) as exc:
        service.rename(uuid4(), "New name")

    assert exc.value.status_code == 404


# ============================================================
# history window
# ============================================================


def test_history_defaults_to_the_agent_window():
    service = make_service()

    service.history(uuid4())

    assert service.message_repo.calls == [10]


def test_history_passes_through_an_unbounded_window():
    service = make_service()

    service.history(uuid4(), limit=None)

    assert service.message_repo.calls == [None]
