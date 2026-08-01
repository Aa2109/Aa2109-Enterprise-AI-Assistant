
from app.repositories.document_repository import DocumentRepository

import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.enums.document import DocumentStatus
from app.db.models.document import Document

from app.services.processors.processor_factory import ProcessorFactory
from app.services.processors.text_cleaner import TextCleaner
from app.db.models.document_content import DocumentContent
from app.utils.token_counter import count_tokens

from app.chunking.factory import ChunkerFactory
from app.db.models.document_chunk import DocumentChunk


class DocumentService:
    def __init__(
        self,
        repository,
        storage_service,
        vector_service,
    ):
        self.repository = repository
        self.storage = storage_service
        self.vector_service = vector_service

    def health(self) -> bool:
            return self.repository.health()

    def upload_document(
        self,
        owner_id,
        file: UploadFile,
    ):
        extension = Path(file.filename).suffix

        storage_name = f"{uuid.uuid4()}{extension}"

        stored_path = self.storage.save(
            file,
            storage_name,
        )

        stored_size = stored_path.stat().st_size

        document = Document(
            owner_id=owner_id,
            original_filename=file.filename,
            storage_filename=storage_name,
            storage_path=str(stored_path),
            mime_type=file.content_type,
            file_size=stored_size,
            status=DocumentStatus.UPLOADED,
        )

        return self.repository.create(document)

    def process_document(self, document, file_path, db):

        # print("PROCESS DOCUMENT")

        # document.status = "EXTRACTING"
        document.status= DocumentStatus.EXTRACTING

        db.commit()
        processor = ProcessorFactory.get_processor(
            Path(file_path)
        )
        # print("=" * 50)
        # print("Processing document:", document.id)
        # print("=" * 50)
        
        raw_text = processor.extract_text(
            Path(file_path)
        )
        # print("Raw text length:", len(raw_text))
        clean_text = TextCleaner.clean(
            raw_text
        )

        content = DocumentContent(
            document_id=document.id,
            raw_text=raw_text,
            clean_text=clean_text,
        )

        db.add(content)
        db.flush()  # optional

        chunker = ChunkerFactory.get_chunker()
        chunks = chunker.split(
            clean_text
        )

        chunk_entities = []

        for index, chunk in enumerate(chunks):

            chunk_entities.append(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=index,
                    content=chunk,
                    token_count=count_tokens(chunk),
                )
            )

        db.add_all(chunk_entities)
        db.flush()

        self.vector_service.index_document(
            document=document,
            chunks=chunk_entities,
        )

        document.status= DocumentStatus.READY
        db.commit()
