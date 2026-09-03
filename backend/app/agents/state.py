from typing import List
from uuid import UUID
from typing_extensions import TypedDict
from app.schemas.search import SearchHit

class AgentState(TypedDict, total=False):

    question: str
    conversation_id: UUID
    owner_id: UUID | None
    document_id: UUID | None
    limit: int

    history: List[list]

    decision: str
    decision_reason: str
    
    retrieved_chunks: List[SearchHit]

    sources: list

    tool_name: str | None
    tool_arguments: dict | None
    tool_result: object | None
    tool_error: str | None

    web_results: list[dict] | None

    answer: str

    iteration: int
    tool_call_count: int
    retry_count: int

    # Complete tool execution history
    tool_executions: list

    approval_request_id: UUID | None
    approval_status: str | None
    approval_required: bool
    run_id: str | None

    retrieved_memories: list[dict]
    memory_candidates: list[dict]