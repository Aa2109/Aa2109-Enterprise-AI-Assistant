from fastapi import APIRouter, Depends
from fastapi.responses import Response

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    generate_latest,
)

from app.security.models import Permission, UserContext
from app.security.permissions import require_permission

router = APIRouter()


@router.get(
    "/metrics",
    include_in_schema=False,
)
def metrics(
    user: UserContext = Depends(
        require_permission(Permission.ADMIN)
    ),
):
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )