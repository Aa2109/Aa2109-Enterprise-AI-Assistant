from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ConversationCreateResponse(BaseModel):
    id: UUID
    title: str

    model_config = {
        "from_attributes": True
    }


class ConversationResponse(BaseModel):
    id: UUID
    owner_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }