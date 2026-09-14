from uuid import UUID

from pydantic import BaseModel, Field


class SemanticSearchRequest(BaseModel):

    query: str = Field(
        min_length=1,
        description="User search query"
    )

    limit: int = Field(
        default=5,
        ge=1,
        le=20
    )

    owner_id: UUID | None = None

    document_id: UUID | None = None

    score_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0
    )


class SearchHit(BaseModel):

    chunk_id: UUID

    document_id: UUID

    chunk_index: int

    content: str

    score: float

    # PR-30 — human-readable source name for citations. Populated at
    # ingestion time in the vector payload; None for documents indexed
    # before this field existed (callers fall back to document_id).
    document_name: str | None = None


class SemanticSearchResponse(BaseModel):

    query: str

    results: list[SearchHit]