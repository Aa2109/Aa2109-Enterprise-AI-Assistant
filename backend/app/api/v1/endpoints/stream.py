from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.dependencies.streaming import get_streaming_service
from app.schemas.chat import ChatRequest

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


@router.post("/stream")
def stream(
    request: ChatRequest,
    service=Depends(get_streaming_service),
):

    return StreamingResponse(
        service.stream(request),
        media_type="text/event-stream",
    )