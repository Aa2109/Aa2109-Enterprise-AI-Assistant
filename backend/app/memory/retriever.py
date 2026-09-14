from uuid import UUID

from app.embeddings.base import EmbeddingProvider
from app.memory.vectorstore import MemoryVectorStore


class MemoryRetriever:

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: MemoryVectorStore,
    ):
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

    def retrieve(
        self,
        user_id: UUID,
        query: str,
        top_k: int = 5,
    ):

        query_vector = (
            self.embedding_provider.embed(
                [query]
            )[0]
        )

        return self.vector_store.search(
            vector=query_vector,
            user_id=user_id,
            limit=top_k,
            score_threshold=0.5,
        )