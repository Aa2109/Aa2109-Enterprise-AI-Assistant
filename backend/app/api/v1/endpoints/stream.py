from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.dependencies.streaming import get_streaming_service
from app.schemas.chat import ChatRequest
from app.security.models import Permission, UserContext
from app.security.permissions import require_permission

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


@router.post("/stream")
def stream(
    request: ChatRequest,
    user: UserContext = Depends(
        require_permission(Permission.CHAT)
    ),
    service=Depends(get_streaming_service),
):

    return StreamingResponse(
        service.stream(request, user),
        media_type="text/event-stream",
    )