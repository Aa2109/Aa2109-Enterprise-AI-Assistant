from uuid import UUID

from fastapi import APIRouter, Depends

from app.dependencies.conversation import get_conversation_service
from app.schemas.conversation import (
    ConversationCreateResponse,
    ConversationResponse,
)
from app.services.conversation_service import ConversationService

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)


@router.post(
    "",
    response_model=ConversationCreateResponse,
)
def create_conversation(
    service: ConversationService = Depends(
        get_conversation_service
    ),
):
    owner_id = UUID(
        "11111111-1111-1111-1111-111111111111"
    )

    return service.create(owner_id)


@router.get(
    "",
    response_model=list[ConversationResponse],
)
def list_conversations(
    service: ConversationService = Depends(
        get_conversation_service
    ),
):
    owner_id = UUID(
        "11111111-1111-1111-1111-111111111111"
    )

    return service.list(owner_id)


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
)
def get_conversation(
    conversation_id: UUID,
    service: ConversationService = Depends(
        get_conversation_service
    ),
):
    return service.get(conversation_id)


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: UUID,
    service: ConversationService = Depends(
        get_conversation_service
    ),
):
    service.delete(conversation_id)

    return {
        "message": "Conversation deleted successfully"
    }