"""
End-to-end upload pipeline verification (Phase D).

Checks that a document makes it through the full chain:

    documents → document_contents → document_chunks → embeddings

The embeddings table is keyed by chunk_id (FK -> document_chunks.id),
NOT document_id, so we reach embeddings via a JOIN on document_chunks.

Run from the backend/ directory:
    python test_e2e_upload.py
"""

from sqlalchemy import func

from app.core.config import settings
from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.db.models.document_content import DocumentContent
from app.db.models.embedding import Embedding
from app.db.database import SessionLocal


def verify_latest_document(db):
    """Reach embeddings for the most recently uploaded document."""
    print("=" * 70)
    print("PHASE D - END-TO-END UPLOAD VERIFICATION")
    print("=" * 70)

    # 1. Latest document
    document = (
        db.query(Document)
        .order_by(Document.created_at.desc())
        .first()
    )

    if document is None:
        raise RuntimeError("No documents found in the database.")

    print(f"1. Document        : {document.original_filename}")
    print(f"   status          : {document.status}")
    print(f"   id              : {document.id}")

    if str(document.status) != "READY":
        print(f"   WARNING: document not READY (status={document.status})")

    # 2. Document content
    content = (
        db.query(DocumentContent)
        .filter(DocumentContent.document_id == document.id)
        .first()
    )

    if content is None:
        raise RuntimeError("DocumentContent missing for document.")
    print(f"2. Content         : {len(content.clean_text)} clean chars")

    # 3. Chunks
    chunk_count = (
        db.query(func.count(DocumentChunk.id))
        .filter(DocumentChunk.document_id == document.id)
        .scalar()
    )
    print(f"3. Chunks          : {chunk_count}")
    if chunk_count == 0:
        raise RuntimeError("Document has no chunks.")

    # 4. Embeddings — the fix: JOIN through document_chunks
    embeddings = (
        db.query(Embedding)
        .join(DocumentChunk, DocumentChunk.id == Embedding.chunk_id)
        .filter(DocumentChunk.document_id == document.id)
        .all()
    )

    print(f"4. Embeddings      : {len(embeddings)}")
    if not embeddings:
        raise RuntimeError(
            "No embeddings found. Chunks exist but vectors were not stored."
        )

    unique_chunks = {e.chunk_id for e in embeddings}
    print(f"   chunk_ids       : {len(unique_chunks)} unique / {chunk_count} chunks")

    if len(unique_chunks) < chunk_count:
        raise RuntimeError(
            "Some chunks are missing an embedding row."
        )

    for e in embeddings[:3]:
        print(
            f"   - chunk={str(e.chunk_id)[:8]} "
            f"provider={e.provider} model={e.model} "
            f"dim={e.dimension} vector_id={e.vector_id}"
        )

    print("=" * 70)
    print("PHASE D VERIFICATION: PASS")
    print("=" * 70)
    return document


def main():
    db = SessionLocal()

    try:
        verify_latest_document(db)

    except RuntimeError as exc:
        print(f"PHASE D VERIFICATION: FAIL -> {exc}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()