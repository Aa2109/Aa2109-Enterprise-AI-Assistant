from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies.conversation import get_conversation_service
from app.schemas.conversation import (
    ConversationCreateResponse,
    ConversationResponse,
    ConversationUpdateRequest,
    MessageResponse,
)
from app.security.models import Permission, Role, UserContext
from app.security.permissions import require_permission
from app.services.conversation_service import ConversationService

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)


def _assert_owned(
    conversation,
    user: UserContext,
) -> None:
    """Conversations are private to their owner; admins may view any.

    Mirrors the existing service-level checks: a missing conversation
    already 404s via ``service.get``, so this only guards cross-owner
    reads.
    """
    if (
        conversation.owner_id != UUID(user.user_id)
        and user.role != Role.ADMIN
    ):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this conversation",
        )


@router.post(
    "",
    response_model=ConversationCreateResponse,
)
def create_conversation(
    user: UserContext = Depends(
        require_permission(Permission.CHAT)
    ),
    service: ConversationService = Depends(
        get_conversation_service
    ),
):
    owner_id = UUID(user.user_id)

    return service.create(owner_id)


@router.get(
    "",
    response_model=list[ConversationResponse],
)
def list_conversations(
    user: UserContext = Depends(
        require_permission(Permission.CHAT)
    ),
    service: ConversationService = Depends(
        get_conversation_service
    ),
):
    owner_id = UUID(user.user_id)

    return service.list(owner_id)


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
)
def get_conversation(
    conversation_id: UUID,
    user: UserContext = Depends(
        require_permission(Permission.CHAT)
    ),
    service: ConversationService = Depends(
        get_conversation_service
    ),
):
    conversation = service.get(conversation_id)

    _assert_owned(conversation, user)

    return conversation


@router.get(
    "/{conversation_id}/messages",
    response_model=dict[str, object],
)
def get_conversation_messages(
    conversation_id: UUID,
    user: UserContext = Depends(
        require_permission(Permission.CHAT)
    ),
    service: ConversationService = Depends(
        get_conversation_service
    ),
):
    """Return the full persisted message history for one conversation.

    Both /chat/answer and /chat/stream persist the user/assistant pair
    server-side, so reopening a conversation can reconstruct the thread
    from here. Ownership is enforced exactly like ``get_conversation``.
    """
    conversation = service.get(conversation_id)

    _assert_owned(conversation, user)

    messages = [
        MessageResponse.model_validate(message)
        for message in service.history(
            conversation_id,
            limit=None,
        )
    ]

    return {
        "conversation_id": str(conversation_id),
        "messages": messages,
    }


@router.patch(
    "/{conversation_id}",
    response_model=ConversationResponse,
)
def rename_conversation(
    conversation_id: UUID,
    body: ConversationUpdateRequest,
    user: UserContext = Depends(
        require_permission(Permission.CHAT)
    ),
    service: ConversationService = Depends(
        get_conversation_service
    ),
):
    """Rename one conversation. Owner-only, admins may rename any."""
    conversation = service.get(conversation_id)

    _assert_owned(conversation, user)

    return service.rename(conversation_id, body.title)


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: UUID,
    user: UserContext = Depends(
        require_permission(Permission.CHAT)
    ),
    service: ConversationService = Depends(
        get_conversation_service
    ),
):
    """Delete one conversation. Owner-only, admins may delete any."""
    conversation = service.get(conversation_id)

    _assert_owned(conversation, user)

    service.delete(conversation_id)

    return {
        "message": "Conversation deleted successfully"
    }