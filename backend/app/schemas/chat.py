from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)
    owner_id: UUID | None = None
    document_id: UUID | None = None
    limit: int = Field(default=5, ge=1, le=10)
    conversation_id: UUID


class SourceChunk(BaseModel):
    chunk_id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]