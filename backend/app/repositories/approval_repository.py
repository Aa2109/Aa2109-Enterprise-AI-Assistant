from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, update
from app.core.enums.approval import ApprovalStatus
from app.db.models.approval_request import ApprovalRequestDB
from sqlalchemy import select

class ApprovalRepository:

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def create(self, approval: ApprovalRequestDB):

        with self.session_factory() as session:

            session.add(approval)
            session.commit()
            session.refresh(approval)

            return approval

    def get(
        self,
        approval_id: UUID,
    ):
        with self.session_factory() as session:
            return session.scalar(
                select(ApprovalRequestDB).where(
                    ApprovalRequestDB.id == approval_id
                )
            )

    def approve(
        self,
        approval_id: UUID,

    ):
        now = datetime.now(timezone.utc)
        with self.session_factory() as session:
            result = session.execute(
                update(ApprovalRequestDB)
                .where(
                    ApprovalRequestDB.id == approval_id,
                    ApprovalRequestDB.status
                    == ApprovalStatus.PENDING.value,
                    ApprovalRequestDB.expires_at > now,
                )
                .values(
                    status=ApprovalStatus.APPROVED.value,
                    resolved_at=now,
                )
            )
            session.commit()
            return result.rowcount == 1

    def reject(
        self,
        approval_id: UUID,
    ):
        now = datetime.now(timezone.utc)
        with self.session_factory() as session:
            result = session.execute(
                update(ApprovalRequestDB)
                .where(
                    ApprovalRequestDB.id == approval_id,
                    ApprovalRequestDB.status
                    == ApprovalStatus.PENDING.value,
                    ApprovalRequestDB.expires_at > now,
                )
                .values(
                    status=ApprovalStatus.REJECTED.value,
                    resolved_at=now,
                )
            )
            session.commit()
            return result.rowcount == 1

    def expire(
        self,
        approval_id: UUID,
    ):
        now = datetime.now(timezone.utc)
        with self.session_factory() as session:
            result = session.execute(
                update(ApprovalRequestDB)
                .where(
                    ApprovalRequestDB.id == approval_id,
                    ApprovalRequestDB.status
                    == ApprovalStatus.PENDING.value,
                    ApprovalRequestDB.expires_at <= now,
                )
                .values(
                    status=ApprovalStatus.EXPIRED.value,
                    resolved_at=now,
                )
            )
            session.commit()
            return result.rowcount == 1

    def get_pending_by_run_id(
        self,
        run_id: UUID,
    ):
        with self.session_factory() as session:
            return session.scalar(
                select(ApprovalRequestDB)
                .where(
                    ApprovalRequestDB.run_id == run_id,
                    ApprovalRequestDB.status
                    == ApprovalStatus.PENDING.value,
                )
                .order_by(
                    ApprovalRequestDB.created_at.desc()
                )
            )

    def get_by_run_id(
        self,
        run_id: UUID,
    ):
        with self.session_factory() as session:

            return session.scalar(
                select(
                    ApprovalRequestDB
                )
                .where(
                    ApprovalRequestDB.run_id
                    == run_id
                )
                .order_by(
                    ApprovalRequestDB.created_at.desc()
                )
            )