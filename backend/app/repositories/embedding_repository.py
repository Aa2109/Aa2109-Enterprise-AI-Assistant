# app/repositories/embedding_repository.py

from sqlalchemy.orm import Session

from app.db.models.embedding import Embedding
from app.db.models.document_chunk import DocumentChunk


class EmbeddingRepository:

    def __init__(self, db: Session):

        self.db = db

    def create_many(
        self,
        embeddings: list[Embedding],
    ):

        self.db.add_all(embeddings)
        # self.db.commit()
        self.db.flush()

        return embeddings

    def find_by_chunk(
        self,
        chunk_id,
    ):

        return (
            self.db.query(Embedding)
            .filter(
                Embedding.chunk_id == chunk_id
            )
            .first()
        )

    def delete_by_document(
        self,
        document_id,
    ):

        embeddings =(
            self.db.query(Embedding)
            .join(Embedding.chunk)
            .filter(
                DocumentChunk.document_id==document_id)
            .all()
        )
        for embedding in embeddings:
            self.db.delete(embedding)

        self.db.commit()
