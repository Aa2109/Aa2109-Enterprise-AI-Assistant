"""Re-run document processing to completion.

One-off helper to finish a document that was left stuck in
EXTRACTING (e.g. uploaded as .txt before TxtProcessor existed).
"""

from pathlib import Path

from app.db.database import SessionLocal
from app.db.models.document import Document
from app.repositories.document_repository import DocumentRepository
from app.repositories.embedding_repository import EmbeddingRepository
from app.services.storage.local_storage import LocalStorageService
from app.embeddings.factory import EmbeddingFactory
from app.vectorstore.factory import VectorStoreFactory
from app.services.vector_service import VectorService
from app.services.document_service import DocumentService


def main():
    db = SessionLocal()
    try:
        document = (
            db.query(Document)
            .order_by(Document.created_at.desc())
            .first()
        )
        print("before:", document.original_filename, "->", document.status)

        service = DocumentService(
            repository=DocumentRepository(db),
            storage_service=LocalStorageService(),
            vector_service=VectorService(
                embedding_provider=EmbeddingFactory.get_provider(),
                vector_store=VectorStoreFactory.get_store(),
                embedding_repository=EmbeddingRepository(db),
            ),
        )

        service.process_document(
            document,
            Path(document.storage_path),
            db,
        )
        print("after :", document.status)

    finally:
        db.close()


if __name__ == "__main__":
    main()