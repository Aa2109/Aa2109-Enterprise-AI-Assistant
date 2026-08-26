from app.db.database import SessionLocal
from app.repositories.approval_repository import ApprovalRepository


def get_approval_repository():
    return ApprovalRepository(
        session_factory=SessionLocal
    )