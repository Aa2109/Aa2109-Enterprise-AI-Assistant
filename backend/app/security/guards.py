from fastapi import HTTPException, status

from app.security.audit import audit_security_event
from app.security.models import Permission, UserContext


def has_permission(
    user: UserContext | None,
    required_permission: Permission,
) -> bool:
    """Non-raising check used by agent nodes.

    Returns False when the caller is missing the permission (or unknown),
    so graph nodes can keep running and produce a clean "not authorized"
    agent result instead of crashing.
    """
    if user is None:
        return False

    return required_permission in user.permissions


def require_tool_permission(
    user: UserContext,
    required_permission: Permission,
) -> None:
    if not has_permission(user, required_permission):
        audit_security_event(
            event="tool_authorization_denied",
            user_id=user.user_id,
            resource=required_permission.value,
            action="execute",
            allowed=False,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"User '{user.user_id}' is not authorized "
                f"to execute this tool"
            ),
        )
