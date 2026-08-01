from fastapi import APIRouter, Depends

from app.dependencies.rag import get_rag_service
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag_service import RAGService

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/answer", response_model=ChatResponse)
def answer(
    request: ChatRequest,
    service: RAGService = Depends(get_rag_service),
) -> ChatResponse:
    return service.answer(request)