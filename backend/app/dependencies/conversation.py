from fastapi import Depends

from app.db.session import get_db
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.services.conversation_service import ConversationService


def get_conversation_repository(db=Depends(get_db)):
    return ConversationRepository(db)


def get_message_repository(db=Depends(get_db)):
    return MessageRepository(db)


def get_conversation_service(
    conversation_repo=Depends(get_conversation_repository),
    message_repo=Depends(get_message_repository),
):
    return ConversationService(
        conversation_repo,
        message_repo,
    )