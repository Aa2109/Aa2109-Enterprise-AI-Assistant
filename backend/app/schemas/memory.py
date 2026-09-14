from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums.memory import MemoryType


class ExtractedMemory(BaseModel):
    memory_type: MemoryType
    content: str = Field(min_length=1)
    importance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
    )
    evidence: str = Field(
        min_length=1,
    )


class MemoryExtractionResult(BaseModel):
    memories: list[ExtractedMemory] = Field(
        default_factory=list
    )


class MemoryResponse(BaseModel):
    id: UUID
    user_id: UUID
    memory_type: MemoryType
    content: str
    importance: float
    created_at: datetime
    updated_at: datetime