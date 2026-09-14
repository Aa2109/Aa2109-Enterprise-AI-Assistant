from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
    BackgroundTasks,
)

from app.db.session import get_db
from app.dependencies.storage import get_document_service
from app.schemas.document import DocumentResponse
from app.security.models import Permission, UserContext
from app.security.permissions import require_permission

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

@router.get(
    "",
    response_model=list[DocumentResponse],
)
def list_documents(
    user: UserContext = Depends(
        require_permission(Permission.CHAT)
    ),
    service=Depends(get_document_service),
):
    """List all documents owned by the authenticated user."""
    owner_id = UUID(user.user_id)

    return service.list_documents(owner_id)


@router.post("/upload")
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: UserContext = Depends(
        require_permission(Permission.CHAT)
    ),
    service=Depends(get_document_service),
    db=Depends(get_db),
):
    owner_id = UUID(user.user_id)

    document = service.upload_document(
        owner_id=owner_id,
        file=file,
    )

    background_tasks.add_task(
        service.process_document,
        document,
        document.storage_path,
        db,
    )

    return document