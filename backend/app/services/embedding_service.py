# app/services/embedding_service.py

from app.core.config import settings
from app.embeddings.factory import EmbeddingFactory
from app.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)


class EmbeddingService:

    def __init__(
        self,
        chunk_repository: DocumentChunkRepository,
    ):

        self.chunk_repository = chunk_repository

        self.provider = (
            EmbeddingFactory.get_provider()
        )

    def generate_embeddings(self, document_id,):
        chunks = (
            self.chunk_repository.find_by_document(
                document_id
            )
        )
        results = []
        batch_size = settings.EMBEDDING_BATCH_SIZE
        for i in range(
            0,
            len(chunks),
            batch_size,
        ):

            batch = chunks[i : i + batch_size]

            texts = [
                chunk.content
                for chunk in batch
            ]

            embeddings = self.provider.embed(texts)

            for chunk, vector in zip(
                batch,
                embeddings,
            ):
                
                results.append(
                    {
                        "chunk": chunk,
                        "embedding":vector,
                    }
                )

        return results
