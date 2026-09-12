"""LEGACY — retained for reference, not wired into the graph since PR-30.

This standalone retriever node was the pre-PR-26 RAG path. Retrieval now
runs inside the RAG specialist (``app/agents/specialists/rag_agent.py``),
which wraps the same ``RetrievalService`` in the reliability stack.
"""

from app.schemas.search import SemanticSearchRequest


class RetrieverNode:

    def __init__(self, retrieval_service):
       self.retrieval_service = retrieval_service

    def __call__(self, state):

        retrieval_request = SemanticSearchRequest(
            query=state["question"],
            limit=state["limit"],
            owner_id=state["owner_id"],
            document_id=state["document_id"],
        )

        result = self.retrieval_service.search(retrieval_request)
        state["retrieved_chunks"] = result.results
        return state