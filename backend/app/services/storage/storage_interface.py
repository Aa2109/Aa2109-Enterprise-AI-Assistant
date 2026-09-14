from abc import ABC, abstractmethod
from pathlib import Path


class StorageService(ABC):
    """
    Contract for all storage providers.
    """

    @abstractmethod
    def save(self, file, filename: str) -> Path:
        """Save file and return its path."""
        pass

    @abstractmethod
    def delete(self, path: Path) -> None:
        pass

    @abstractmethod
    def exists(self, path: Path) -> bool:
        pass

    @abstractmethod
    def read(self, path: Path) -> bytes:
        pass
