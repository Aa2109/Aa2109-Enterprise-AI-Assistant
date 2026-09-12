from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.security.auth import get_current_user
from app.security.models import Permission, UserContext
from app.security.rbac import (
    ROLE_PERMISSIONS,
    permissions_for_role,
)

# Re-exported for callers that import from ``app.security.permissions``.
__all__ = [
    "ROLE_PERMISSIONS",
    "permissions_for_role",
    "require_permission",
]


def require_permission(
    permission: Permission,
) -> Callable:
    async def checker(
        user: UserContext = Depends(get_current_user),
    ) -> UserContext:
        if permission not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission.value}",
            )
        return user

    return checker