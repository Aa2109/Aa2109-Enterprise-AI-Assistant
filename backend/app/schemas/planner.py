from enum import Enum

from pydantic import BaseModel, Field


class PlannerAction(str, Enum):
    RAG = "RAG"
    DIRECT = "DIRECT"
    TOOL = "TOOL"
    CLARIFY = "CLARIFY"
    UNSUPPORTED = "UNSUPPORTED"
    FINAL = "FINAL"


class PlannerDecision(BaseModel):
    action: PlannerAction
    reason: str | None = None
    tool_name: str | None = None
    tool_arguments: dict | None = None