
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    def __init__(self, db: Session):
        super().__init__(Document, db)

    def find_by_owner(self, owner_id):
        statement = (
            select(Document)
            .where(Document.owner_id == owner_id)
        )

        return self.db.scalars(statement).all()
