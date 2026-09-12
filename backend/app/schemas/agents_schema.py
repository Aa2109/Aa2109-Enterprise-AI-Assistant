from enum import Enum

from pydantic import BaseModel, Field


class AgentName(str, Enum):
    RAG = "rag"
    RESEARCH = "research"
    DATA = "data"


class RoutingDecision(BaseModel):
    agents: list[AgentName] = Field(
        default_factory=list,
    )
    reasoning: str
    done: bool = False


class AgentResult(BaseModel):
    agent: AgentName
    success: bool
    content: str = ""
    metadata: dict = Field(
        default_factory=dict,
    )
    error: str | None = None