from fastapi import HTTPException

from app.db.models.conversation import Conversation
from app.db.models.message import Message

DEFAULT_TITLE = "New Conversation"

#: Titles derived from a query are trimmed to this many characters so
#: the sidebar can render them on a single line.
TITLE_MAX_LENGTH = 60


def derive_title(query: str) -> str:
    """Build a sidebar title out of the first user query.

    Collapses whitespace and cuts on a word boundary, the way
    ChatGPT/Claude name a thread after its opening message.
    """
    cleaned = " ".join(query.split())

    if not cleaned:
        return DEFAULT_TITLE

    if len(cleaned) <= TITLE_MAX_LENGTH:
        return cleaned

    clipped = cleaned[:TITLE_MAX_LENGTH]
    last_space = clipped.rfind(" ")

    # Only honour the word boundary when it keeps a usable title;
    # a single very long word is simply cut.
    if last_space > TITLE_MAX_LENGTH // 2:
        clipped = clipped[:last_space]

    return f"{clipped.rstrip()}…"


class ConversationService:

    def __init__(
        self,
        conversation_repo,
        message_repo,
    ):
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo

    def create(self, owner_id):
        conversation = Conversation(
            owner_id=owner_id,
            title=DEFAULT_TITLE,
        )
        return self.conversation_repo.create(conversation)

    def list(self, owner_id):
        return self.conversation_repo.list_by_user(owner_id)

    def get(self, conversation_id):
        conversation = self.conversation_repo.get(conversation_id)

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )

        return conversation

    def rename(self, conversation_id, title):
        """Set a user-supplied title on a conversation."""
        conversation = self.get(conversation_id)

        cleaned = " ".join(title.split())

        if not cleaned:
            raise HTTPException(
                status_code=422,
                detail="Title must not be empty",
            )

        conversation.title = cleaned[:255]

        return self.conversation_repo.update(conversation)

    def ensure_title(self, conversation_id, query):
        """Name an untitled conversation after its first query.

        No-ops once the conversation carries any other title, so a
        rename by the user is never overwritten.
        """
        conversation = self.conversation_repo.get(conversation_id)

        if conversation is None:
            return None

        if conversation.title != DEFAULT_TITLE:
            return conversation

        conversation.title = derive_title(query)

        return self.conversation_repo.update(conversation)

    def delete(self, conversation_id):
        conversation = self.conversation_repo.get(conversation_id)

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )

        self.conversation_repo.delete(conversation)

    def add_message(
        self,
        conversation_id,
        role,
        content,
        metadata=None,
    ):
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            message_metadata=metadata or {},
        )
        return self.message_repo.create(message)

    def history(self, conversation_id, limit=10):
        """Recent messages, oldest first.

        The default window is what the agent graph feeds back to the
        LLM; the conversations API passes ``limit=None`` to rebuild a
        whole thread for the UI.
        """
        return self.message_repo.history(
            conversation_id,
            limit=limit,
        )