"""RAG retriever node — vector retrieval for the RAG specialist.

This is the live retrieval path: ``dependencies/retriever.py`` wires it
into ``RAGAgent`` (which wraps it in the reliability stack). The query is
contextualized from recent conversation turns so a same-conversation
follow-up retrieves against its antecedent rather than the bare sentence.
"""

from app.schemas.search import SemanticSearchRequest


class RetrieverNode:

    def __init__(self, retrieval_service):
       self.retrieval_service = retrieval_service

    def __call__(self, state):

        from app.agents.context import build_contextualized_question

        retrieval_request = SemanticSearchRequest(
            query=build_contextualized_question(state),
            limit=state["limit"],
            owner_id=state["owner_id"],
            document_id=state["document_id"],
        )

        result = self.retrieval_service.search(retrieval_request)
        state["retrieved_chunks"] = result.results
        return state