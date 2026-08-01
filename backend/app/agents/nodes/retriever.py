from app.schemas.search import SemanticSearchRequest


class RetrieverNode:

    def __init__(self, retrieval_service):

        self.retrieval_service = retrieval_service

    def __call__(self, state):

        request = SemanticSearchRequest(

            query=state["question"],

            owner_id=state["owner_id"],

            document_id=state["document_id"],

            limit=state["limit"],

            score_threshold=None,
        )

        result = self.retrieval_service.search(request)

        state["retrieved_chunks"] = result.results

        return state