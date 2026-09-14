from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ToolExecution(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)

    result: Any = None
    error: str | None = None

    success: bool = False

    iteration: int
    retry_count: int = 0

    started_at: datetime | None = None
    completed_at: datetime | None = None