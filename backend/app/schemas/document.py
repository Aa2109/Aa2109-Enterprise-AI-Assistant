from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.enums.document import DocumentStatus


class DocumentResponse(BaseModel):
    id: UUID
    original_filename: str
    status: DocumentStatus
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
