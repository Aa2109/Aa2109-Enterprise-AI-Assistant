from typing import Generic, Type, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(
        self,
        model: Type[ModelType],
        db: Session,
    ) -> None:
        self.model = model
        self.db = db

    def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def get_by_id(self, id: UUID) -> ModelType | None:
        return self.db.get(self.model, id)

    def delete(self, obj: ModelType) -> None:
        self.db.delete(obj)
        self.db.commit()
