from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from langgraph.types import Command

from app.dependencies.agent import get_agent_graph
from app.dependencies.approval import (
        get_approval_repository,
    )
from app.repositories.approval_repository import ApprovalRepository
from app.core.enums.approval import ApprovalStatus
from app.security.models import Permission, UserContext
from app.security.permissions import require_permission


router = APIRouter(
        prefix="/approvals",
        tags=["approvals"],
)


@router.post("/{approval_id}/approve")
def approve(
    approval_id: UUID,
    user: UserContext = Depends(
        require_permission(Permission.ADMIN)
    ),
    repository: ApprovalRepository = Depends(
        get_approval_repository
        ),
    graph=Depends(get_agent_graph)
):

    approval = repository.get(
        approval_id
    )

    # --------------------------------------------------
    # Approval does not exist
    # --------------------------------------------------

    if approval is None:

        raise HTTPException(
            status_code=404,
            detail="Approval request not found",
        )

    # --------------------------------------------------
    # Already resolved
    # --------------------------------------------------

    if (
        approval.status
        != ApprovalStatus.PENDING.value
    ):

        return {
            "approval_id": str(approval_id),
            "status": approval.status,
            "message": "Approval request was already resolved"
        }

    # --------------------------------------------------
    # Check expiration
    # --------------------------------------------------

    now = datetime.now(timezone.utc)

    if (
        approval.expires_at
        and approval.expires_at <= now
    ):

        repository.expire(
            approval_id
        )

        return {
            "approval_id": str(approval_id),
            "status": ApprovalStatus.EXPIRED.value,
        }

    # --------------------------------------------------
    # Atomic approval
    #
    # Repository performs:
    #
    # PENDING -> APPROVED
    #
    # only if the record is still PENDING
    # --------------------------------------------------

    updated = repository.approve(
        approval_id
    )

    # --------------------------------------------------
    # Another request may have resolved it first
    # --------------------------------------------------

    if not updated:

        approval = repository.get(
            approval_id
        )

        return {
            "approval_id": str(approval_id),
            "status": (
                approval.status
                if approval
                else "UNKNOWN"
            ),
        }
        
    # Resume the interrupted LangGraph excution
    result = graph.invoke(
        Command(
            resume={
                "approval_id": str(approval_id),
                "status": ApprovalStatus.APPROVED.value
            }
        ),
        config={
            "configurable": {
                "thread_id": str(approval.run_id)
            }
        },
    )

    return {
        "approval_id": str(approval_id),
        "status": ApprovalStatus.APPROVED.value,
        "answer": result.get("answer")
    }


@router.post("/{approval_id}/reject")
def reject(
    approval_id: UUID,
    repository: ApprovalRepository = Depends(
        get_approval_repository
    ),
    graph=Depends(get_agent_graph),
):

    approval = repository.get(
        approval_id
    )

    # --------------------------------------------------
    # Approval does not exist
    # --------------------------------------------------

    if approval is None:

        raise HTTPException(
            status_code=404,
            detail="Approval request not found",
        )

    # --------------------------------------------------
    # Already resolved
    # --------------------------------------------------

    if (
        approval.status
        != ApprovalStatus.PENDING.value
    ):

        return {
            "approval_id": str(approval_id),
            "status": ApprovalStatus.REJECTED.value,
            "message": "Approval request was already resolved",

        }

    # --------------------------------------------------
    # Check expiration
    # --------------------------------------------------

    now = datetime.now(timezone.utc)

    if (
        approval.expires_at
        and approval.expires_at <= now
    ):

        repository.expire(
            approval_id
        )

        return {
            "approval_id": str(approval_id),
            "status": ApprovalStatus.EXPIRED.value,
        }

    # --------------------------------------------------
    # Atomic rejection
    # --------------------------------------------------

    updated = repository.reject(
        approval_id
    )

    # --------------------------------------------------
    # Another request may have resolved it first
    # --------------------------------------------------

    if not updated:

        approval = repository.get(
            approval_id
        )

        return {
            "approval_id": str(approval_id),
            "status": (
                approval.status
                if approval
                else "UNKNOWN"
            ),
        }

    #Resume paused LangGraph execution
    result = graph.invoke(
        Command(
            resume={
                "approval_id": str(approval_id),
                "status": (ApprovalStatus.REJECTED.value
                ),
            }
        ),
        config={
            "configurable": {
                "thread_id": str(
                    approval.run_id
                )
            }
        },
    )

    return {
        "approval_id": str(approval_id),
        "status": ApprovalStatus.REJECTED.value,
        "answer": result.get("answer"),
    }