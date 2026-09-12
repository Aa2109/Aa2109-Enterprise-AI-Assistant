from fastapi import APIRouter, Depends


from app.dependencies.retrieval import (
    get_retrieval_service
)

from app.schemas.search import (
    SemanticSearchRequest,
    SemanticSearchResponse,
)

from app.security.models import Permission, UserContext
from app.security.permissions import require_permission

from app.services.retrieval_service import (
    RetrievalService
)



router = APIRouter(
    prefix="/search",
    tags=["Search"]
)



@router.post(
    "/semantic",
    response_model=SemanticSearchResponse
)
def semantic_search(

    request: SemanticSearchRequest,

    user: UserContext = Depends(
        require_permission(Permission.RAG_READ)
    ),

    service: RetrievalService = Depends(
        get_retrieval_service
    )

):

    return service.search(request)