from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_database
from app.dependencies.storage import get_storage, get_vector_service
from app.repositories.document_repository import DocumentRepository
from app.services.document_service import DocumentService
from app.services.storage.local_storage import LocalStorageService
from app.services.vector_service import VectorService



def get_document_repository(
    db: Session = Depends(get_database),
) -> DocumentRepository:
    return DocumentRepository(db)

def get_document_service(
    repository: DocumentRepository = Depends(get_document_repository),
    storage: LocalStorageService = Depends(get_storage),
    vector_service: VectorService = Depends(get_vector_service),
) -> DocumentService:
    return DocumentService(
        repository=repository,
        storage_service=storage,
        vector_service=vector_service,
    )