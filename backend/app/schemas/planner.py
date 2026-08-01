from enum import Enum

from pydantic import BaseModel


class PlannerAction(str, Enum):

    RAG = "RAG"

    DIRECT = "DIRECT"

    CLARIFY = "CLARIFY"


class PlannerDecision(BaseModel):

    action: PlannerAction

    reason: str