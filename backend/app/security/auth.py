from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.security.jwt import decode_access_token
from app.security.models import Role, UserContext
from app.security.rbac import permissions_for_role


bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials,
        Depends(bearer_scheme),
    ],
) -> UserContext:
    payload = decode_access_token(credentials.credentials)

    try:
        role = Role(payload["role"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user role",
        ) from exc

    return UserContext(
        user_id=payload["sub"],
        role=role,
        permissions=permissions_for_role(role),
    )
