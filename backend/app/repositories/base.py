from typing import Generic, Type, TypeVar, Union
from uuid import UUID

from sqlalchemy import text
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

    def get_by_id(self, id: Union[UUID, str]) -> ModelType | None:
        return self.db.get(self.model, id)

    def delete(self, obj: ModelType) -> None:
        self.db.delete(obj)
        self.db.commit()

    def health(self) -> bool:
        """Lightweight DB liveness probe: succeeds if a trivial query runs."""
        self.db.execute(text("SELECT 1"))
        return True
