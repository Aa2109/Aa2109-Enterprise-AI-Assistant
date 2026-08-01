from typing import List

from typing_extensions import TypedDict

from app.schemas.search import SearchResult


class AgentState(TypedDict):

    question: str

    conversation_id: str

    owner_id: str

    document_id: str | None

    limit: int

    history: list

    decision: str

    retrieved_chunks: List[SearchResult]

    answer: str

    sources: list