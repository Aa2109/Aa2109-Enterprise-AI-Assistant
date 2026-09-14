from sqlalchemy import Column, Integer, Text, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin


class DocumentContent(Base, TimestampMixin):

    __tablename__ = "document_contents"

    id = Column(
        Integer,
        primary_key=True
    )

    document_id = Column(
        ForeignKey("documents.id"),
        unique=True,
        nullable=False
    )

    raw_text = Column(
        Text,
        nullable=False
    )

    clean_text = Column(
        Text,
        nullable=False
    )

    page_count = Column(
        Integer,
        nullable=True
    )

    language = Column(
        String,
        nullable=True
    )


    document = relationship(
        "Document",
        back_populates="content"
    )
