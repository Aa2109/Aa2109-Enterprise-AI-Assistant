from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session) -> None:
        super().__init__(User, db)

    def get_by_email(self, email: str) -> User | None:
        statement = (
            select(User)
            .where(User.email == email)
        )

        return self.db.scalar(statement)

    def count(self) -> int:
        from sqlalchemy import func

        statement = select(func.count()).select_from(User)
        return self.db.scalar(statement) or 0

    def exists_admin(self) -> bool:
        statement = (
            select(User)
            .where(User.role == "admin")
            .limit(1)
        )
        return self.db.scalar(statement) is not None
