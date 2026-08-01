from app.db.models.embedding import Embedding
from app.core.config import settings

from app.embeddings.base import EmbeddingProvider
from app.vectorstore.base import VectorStore
from app.repositories.embedding_repository import EmbeddingRepository

class VectorService:

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        embedding_repository: EmbeddingRepository,
    ):

        self.embedding_provider = embedding_provider

        self.vector_store = vector_store

        self.embedding_repository = embedding_repository

    def index_document(
    self,
    document,
    chunks,
    ):
        print("INDEX DOCUMENT")
        
        if not chunks:
            return
        texts = [
            chunk.content
            for chunk in chunks
        ]

        #   vectors = self.embedding_provider.embed(texts)
        vectors = []

        batch_size = settings.EMBEDDING_BATCH_SIZE

        for i in range(0, len(texts), batch_size):

            batch = texts[i:i + batch_size]

            vectors.extend(
                self.embedding_provider.embed(batch)
            )

        payload = []

        metadata = []

        for chunk, vector in zip(chunks, vectors):

            payload.append({

                "chunk_id": chunk.id,

                "document_id": chunk.document_id,

                "owner_id": document.owner_id,

                "chunk_index": chunk.chunk_index,

                "content": chunk.content,

                "embedding": vector,
            })

            metadata.append(

                Embedding(

                    chunk_id=chunk.id,

                    provider=settings.EMBEDDING_PROVIDER,

                    model=settings.EMBEDDING_MODEL,

                    dimension=len(vector),

                    vector_id=str(chunk.id),
                )
            )

        self.vector_store.upsert(payload)

        self.embedding_repository.create_many(metadata)
