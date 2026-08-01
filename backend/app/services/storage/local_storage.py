import shutil
from pathlib import Path

from fastapi import UploadFile

from app.services.storage.storage_interface import StorageService


class LocalStorageService(StorageService):
    def __init__(self):
        self.base_path = Path("uploads/documents")
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, file: UploadFile, filename: str) -> Path:
        destination = self.base_path / filename

        with destination.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return destination

    def delete(self, path: Path):
        if path.exists():
            path.unlink()

    def exists(self, path: Path):
        return path.exists()

    def read(self, path: Path):
        return path.read_bytes()
