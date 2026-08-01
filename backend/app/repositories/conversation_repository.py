from app.db.models.conversation import Conversation


class ConversationRepository:

    def __init__(self, db):
        self.db = db

    def create(self, conversation):
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get(self, conversation_id):
        return self.db.get(Conversation, conversation_id)

    def list_by_user(self, owner_id):
        return (
            self.db.query(Conversation)
            .filter(Conversation.owner_id == owner_id)
            .order_by(Conversation.updated_at.desc())
            .all()
        )

    def delete(self, conversation):
        self.db.delete(conversation)
        self.db.commit()