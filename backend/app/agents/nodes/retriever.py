from app.schemas.search import SemanticSearchRequest


class RetrieverNode:

    def __init__(self, retrieval_service):
       self.retrieval_service = retrieval_service

    def __call__(self, state):
        print("<<<<<< Retriever node started")

        retrieval_request = SemanticSearchRequest(
            query=state["question"],
            limit=state["limit"],
            owner_id=state["owner_id"],
            document_id=state["document_id"],
        )

        result = self.retrieval_service.search(retrieval_request)
        print("Retrieved:", len(result.results))
        state["retrieved_chunks"] = result.results
        print("Keys after retrieval:", state.keys())
        return state