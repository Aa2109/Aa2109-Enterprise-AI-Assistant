import fitz
from pathlib import Path

from app.services.processors.base import DocumentProcessor


class PDFProcessor(DocumentProcessor):

    def extract_text(self, file_path: Path) -> str:

        document = fitz.open(file_path)

        pages = []

        for page in document:
            pages.append(page.get_text())

        document.close()

        return "\n".join(pages)
