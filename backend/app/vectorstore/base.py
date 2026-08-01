from abc import ABC, abstractmethod
from uuid import UUID

class VectorStore(ABC):

    @abstractmethod
    def create_collection(self) -> None:
        ...

    @abstractmethod
    def upsert(
        self,
        vectors: list[dict],
    ) -> None:
      ...

    @abstractmethod
    def delete(
        self,
        ids: list[UUID],
    ) -> None:
        ...

    @abstractmethod
    def search(
        self,
        vector: list[float],
        limit: int = 5,
        owner_id: UUID | None = None,
        document_id: UUID | None = None,
        score_threshold: float | None = None,
    ) -> list[dict]:
        raise NotImplementedError