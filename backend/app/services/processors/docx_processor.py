from pathlib import Path

from docx import Document

from app.services.processors.base import DocumentProcessor


class DocxProcessor(DocumentProcessor):

    def extract_text(self, file_path: Path) -> str:

        document = Document(file_path)

        paragraphs = []

        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if text:
                paragraphs.append(text)

        return "\n".join(paragraphs)