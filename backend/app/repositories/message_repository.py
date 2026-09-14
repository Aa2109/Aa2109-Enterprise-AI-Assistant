from app.db.models.message import Message

class MessageRepository:

    def __init__(self, db):
        self.db = db

    def create(self, message):
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def history(
        self,
        conversation_id,
        limit=10,
    ):
        query = (
            self.db.query(Message)
            .filter(
                Message.conversation_id == conversation_id
            )
            .order_by(Message.created_at.desc())
        )

        # ``limit=None`` means "the whole thread" — the conversations
        # API uses it to rebuild a conversation in the UI.
        if limit is not None:
            query = query.limit(limit)

        return query.all()[::-1]