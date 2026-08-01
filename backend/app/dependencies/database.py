
from collections.abc import Generator
from sqlalchemy.orm import Session

from app.db.session import get_db


def get_database() -> Generator[Session, None, None]:
    """
    Wrapper around the application's database dependency.
    Future enhancements (metrics, tracing, multi-tenancy)
    can be added here without changing callers.
    """
    yield from get_db()