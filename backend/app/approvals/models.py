from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.core.enums.approval import ApprovalStatus


# class ApprovalStatus(str, Enum):
#     PENDING = "PENDING"
#     APPROVED = "APPROVED"
#     REJECTED = "REJECTED"
#     EXPIRED = "EXPIRED"


class ApprovalRequest(BaseModel):
    id: UUID = Field(default_factory=uuid4)

    conversation_id: UUID
    user_id: UUID

    tool_name: str
    arguments: dict[str, Any]

    reason: str

    status: ApprovalStatus = ApprovalStatus.PENDING

    created_at: datetime
    expires_at: datetime | None = None
    resolved_at: datetime | None = None