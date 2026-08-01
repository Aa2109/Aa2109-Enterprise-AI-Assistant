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

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

@router.post("/upload")
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    service=Depends(get_document_service),
    db=Depends(get_db),
):
    owner_id = UUID("11111111-1111-1111-1111-111111111111")

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