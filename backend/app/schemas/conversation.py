from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationCreateResponse(BaseModel):
    id: UUID
    title: str

    model_config = {
        "from_attributes": True
    }


class ConversationUpdateRequest(BaseModel):
    """Rename a conversation from the sidebar."""

    title: str = Field(
        min_length=1,
        max_length=255,
    )


class ConversationResponse(BaseModel):
    id: UUID
    owner_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class MessageResponse(BaseModel):
    """A persisted chat message inside a conversation.

    Mirrors ``app/db/models/message.py``; ``role`` is emitted as the
    string value of the ``MessageRole`` enum (USER / ASSISTANT / ...).
    """

    id: UUID
    role: str
    content: str
    message_metadata: dict = {}
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }