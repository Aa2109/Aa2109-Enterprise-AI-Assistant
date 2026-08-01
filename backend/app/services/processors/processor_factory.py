from pathlib import Path

from app.services.processors.pdf_processor import PDFProcessor
from app.services.processors.docx_processor import DocxProcessor


class ProcessorFactory:

    @staticmethod
    def get_processor(file_path: Path):

        extension = file_path.suffix.lower()

        if extension == ".pdf":
            return PDFProcessor()
        if extension == ".docx":
            return DocxProcessor()

        raise ValueError(
            f"Unsupported file type {extension}"
        )
