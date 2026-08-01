from fastapi import HTTPException

from app.db.models.conversation import Conversation
from app.db.models.message import Message


class ConversationService:

    def __init__(
        self,
        conversation_repo,
        message_repo,
    ):
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo

    def create(self, owner_id):
        conversation = Conversation(
            owner_id=owner_id,
            title="New Conversation",
        )
        return self.conversation_repo.create(conversation)

    def list(self, owner_id):
        return self.conversation_repo.list_by_user(owner_id)

    def get(self, conversation_id):
        conversation = self.conversation_repo.get(conversation_id)

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )

        return conversation

    def delete(self, conversation_id):
        conversation = self.conversation_repo.get(conversation_id)

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )

        self.conversation_repo.delete(conversation)

    def add_message(
        self,
        conversation_id,
        role,
        content,
        metadata=None,
    ):
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            message_metadata=metadata or {},
        )
        return self.message_repo.create(message)

    def history(self, conversation_id):
        return self.message_repo.history(conversation_id)