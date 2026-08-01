from fastapi import APIRouter, Depends

from app.core.exceptions import DocumentNotFoundException
from app.dependencies.documents import get_document_service
from app.services.document_service import DocumentService

router = APIRouter()


@router.get("/test/document-not-found")
async def document_not_found():
    raise DocumentNotFoundException("doc-123")

@router.get("/di-test")
async def di_test(
    service: DocumentService = Depends(get_document_service),
):
    return {
        "dependency_injection": service.health()
    }