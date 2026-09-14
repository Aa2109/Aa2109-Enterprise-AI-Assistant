from pathlib import Path

from app.services.processors.base import DocumentProcessor


class TxtProcessor(DocumentProcessor):

    def extract_text(self, file_path: Path) -> str:

        return file_path.read_text(
            encoding="utf-8",
            errors="replace",
        )