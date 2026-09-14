from typing import Any
from uuid import UUID

from typing_extensions import TypedDict

from app.schemas.search import SearchHit
from app.security.models import UserContext


class AgentState(TypedDict, total=False):

    # ==================================================
    # Request context
    # ==================================================

    question: str
    conversation_id: UUID
    owner_id: UUID | None
    document_id: UUID | None
    limit: int

    user_context: UserContext | None

    history: list

    # ==================================================
    # Existing planner / execution state
    # ==================================================

    decision: str
    decision_reason: str

    iteration: int
    tool_call_count: int
    retry_count: int

    tool_name: str | None
    tool_arguments: dict | None
    tool_result: object | None
    tool_error: str | None

    tool_executions: list

    # ==================================================
    # Retrieval
    # ==================================================

    retrieved_chunks: list[SearchHit]
    sources: list

    web_results: list[dict] | None

    retrieved_memories: list[dict]
    memory_candidates: list[dict]

    # ==================================================
    # HITL
    # ==================================================

    approval_request_id: UUID | None
    approval_status: str | None
    approval_required: bool

    # ==================================================
    # Agent execution
    # ==================================================

    run_id: str | None

    # ==================================================
    # Supervisor
    # ==================================================

    selected_agents: list[str]
    pending_agents: list[str]
    current_agent: str | None
    supervisor_reason: str | None
    done: bool

    # ==================================================
    # Specialist results
    # ==================================================

    rag_results: list[dict[str, Any]]
    research_results: list[dict[str, Any]]
    data_results: list[dict[str, Any]]

    agent_results: dict[str, Any]

    agent_step: int
    supervisor_done: bool

    # ==================================================
    # PR-28 Token / cost control
    # ==================================================

    input_tokens: int
    output_tokens: int
    total_tokens: int
    token_budget_exceeded: bool

    # ==================================================
    # Final response
    # ==================================================

    answer: str | None

    # PR-30 — human-readable source/citation list collected from
    # successful specialist results during final synthesis.
    citations: list