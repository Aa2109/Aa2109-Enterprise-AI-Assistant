from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)
    owner_id: UUID | None = None
    document_id: UUID | None = None
    limit: int = Field(default=5, ge=1, le=10)
    conversation_id: UUID
    # run_id: UUID | None = None


class SourceChunk(BaseModel):
    chunk_id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    score: float


class ChatResponse(BaseModel):
    answer: str | None = None
    sources: list[SourceChunk] = Field(default_factory=list)
    # PR-30 — human-readable citation list collected from successful
    # specialist results (document names for RAG, title — URL for
    # research, "database" for data). Distinct from ``sources``, which
    # carries the structured RAG chunk detail.
    citations: list[str] = Field(default_factory=list)
    status: str = "completed"
    approval_id: UUID | None = None