from app.schemas.search import (
    SemanticSearchRequest,
    SemanticSearchResponse,
    SearchHit,
)

from app.vectorstore.base import VectorStore
from app.embeddings.base import EmbeddingProvider


class RetrievalService:

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
    ):

        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

    def search(
        self,
        request: SemanticSearchRequest,
    ):

        query_vector = (
            self.embedding_provider
            .embed(
                [request.query]
            )[0]
        )

        results = self.vector_store.search(

            vector=query_vector,

            limit=request.limit,

            owner_id=request.owner_id,

            document_id=request.document_id,

            score_threshold=request.score_threshold,
        )

        hits = [

            SearchHit(

                chunk_id=item["chunk_id"],

                document_id=item["document_id"],

                chunk_index=item["chunk_index"],

                content=item["content"],

                score=item["score"],

                document_name=item.get("document_name"),

            )

            for item in results
        ]

        return SemanticSearchResponse(

            query=request.query,

            results=hits,
        )