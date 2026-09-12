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
    """Standardized contract every specialist returns.

    The supervisor and the final responder only rely on these six fields,
    so any specialist can be swapped (e.g. research -> deep research)
    without redesigning the orchestration.
    """

    agent: AgentName
    success: bool
    content: str = ""
    sources: list[str] = Field(
        default_factory=list,
    )
    metadata: dict = Field(
        default_factory=dict,
    )
    error: str | None = None