from sqlalchemy.orm import Session
from uuid import UUID
from app.db.models.document_chunk import DocumentChunk


class DocumentChunkRepository:

    def __init__(
        self,
        session: Session
    ):
        self.session = session


    def create_many(
        self,
        chunks: list[DocumentChunk]
    ):

        self.session.add_all(chunks)
        self.session.flush()


    def find_by_document(
        self,
        document_id: UUID,
    ):

        return (
            self.session.query(DocumentChunk)
            .filter(
                DocumentChunk.document_id == document_id
            )
            .all()
        )


    def delete_by_document(
        self,
        document_id
    ):

        (
            self.session.query(DocumentChunk)
            .filter(
                DocumentChunk.document_id == document_id
            )
            .delete()
        )
