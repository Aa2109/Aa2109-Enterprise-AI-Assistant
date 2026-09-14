from fastapi import APIRouter, Depends, Request

from app.dependencies.rag import get_rag_service
from app.schemas.chat import ChatRequest, ChatResponse
from app.security.auth import get_current_user
from app.security.models import Permission, UserContext
from app.security.permissions import require_permission
from app.services.rag_service import RAGService

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/answer", response_model=ChatResponse)
def answer(
    request: Request,
    body: ChatRequest,
    user: UserContext = Depends(
        require_permission(Permission.CHAT)
    ),
    service: RAGService = Depends(get_rag_service),
) -> ChatResponse:
    # PR-30 — thread the request_id set by RequestIDMiddleware into the
    # graph so logs / traces / metrics for one user request share one id.
    request_id = getattr(
        request.state,
        "request_id",
        None,
    )

    return service.answer(
        body,
        user,
        request_id=request_id,
    )