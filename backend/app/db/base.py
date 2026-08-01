from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.
    """
    pass


# Import models for Alembic discovery
# from app.db.models.user import User
# from app.db.models.document import Document
# from app.db.models.document_content import DocumentContent
# from app.db.models.document_chunk import DocumentChunk
