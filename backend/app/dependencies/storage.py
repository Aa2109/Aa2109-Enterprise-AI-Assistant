from fastapi import Depends

from app.db.session import get_db

from app.repositories.document_repository import DocumentRepository
from app.repositories.embedding_repository import EmbeddingRepository

from app.embeddings.factory import EmbeddingFactory
from app.vectorstore.factory import VectorStoreFactory

from app.services.document_service import DocumentService
from app.services.vector_service import VectorService
from app.services.storage.local_storage import LocalStorageService


def get_storage():
    return LocalStorageService()


def get_document_repository(
    db=Depends(get_db),
):
    return DocumentRepository(db)


def get_embedding_repository(
    db=Depends(get_db),
):
    return EmbeddingRepository(db)


def get_vector_service(
    embedding_repo=Depends(get_embedding_repository),
):
    embedding_provider = EmbeddingFactory.get_provider()

    vector_store = VectorStoreFactory.get_store()

    return VectorService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        embedding_repository=embedding_repo,
    )


def get_document_service(
    repo=Depends(get_document_repository),
    storage=Depends(get_storage),
    vector_service=Depends(get_vector_service),
):
    return DocumentService(
        repository=repo,
        storage_service=storage,
        vector_service=vector_service,
    )