from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_database
from app.repositories.document_repository import DocumentRepository
from fastapi import Depends
from app.services.document_service import DocumentService



def get_document_repository(
    db: Session = Depends(get_database),
) -> DocumentRepository:
    return DocumentRepository(db)

def get_document_service(
    repository: DocumentRepository = Depends(get_document_repository),
) -> DocumentService:
    return DocumentService(repository)