from pathlib import Path

from app.services.processors.pdf_processor import PDFProcessor
from app.services.processors.docx_processor import DocxProcessor
from app.services.processors.txt_processor import TxtProcessor


class ProcessorFactory:

    @staticmethod
    def get_processor(file_path: Path):

        extension = file_path.suffix.lower()

        if extension == ".pdf":
            return PDFProcessor()
        if extension == ".docx":
            return DocxProcessor()
        if extension in (".txt", ".md"):
            return TxtProcessor()

        raise ValueError(
            f"Unsupported file type {extension}"
        )
