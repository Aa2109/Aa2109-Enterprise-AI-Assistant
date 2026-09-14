from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies.memory import get_memory_service
from app.security.models import Permission, UserContext
from app.security.permissions import require_permission
from app.services.memory_service import MemoryService


router = APIRouter(
    prefix="/memories",
    tags=["memories"],
)

@router.get("")
def list_memories(
    user: UserContext = Depends(
        require_permission(Permission.RAG_READ)
    ),
    service: MemoryService = Depends(
        get_memory_service
    ),
):
    user_id = UUID(user.user_id)

    memories = service.list_memories(
        user_id
    )

    return {
        "memories": [
            {
                "id": str(memory.id),
                "user_id": str(memory.user_id),
                "memory_type": memory.memory_type,
                "content": memory.content,
                "importance": memory.importance,
                "created_at": memory.created_at,
                "updated_at": memory.updated_at,
            }
            for memory in memories
        ]
    }

@router.delete("/{memory_id}")
def delete_memory(
    memory_id: UUID,
    user: UserContext = Depends(
        require_permission(Permission.RAG_READ)
    ),
    service: MemoryService = Depends(
        get_memory_service
    ),
):
    user_id = UUID(user.user_id)

    deleted = service.delete_memory(
        user_id=user_id,
        memory_id=memory_id,
    )

    if not deleted:

        raise HTTPException(
            status_code=404,
            detail="Memory not found",
        )

    return {
        "memory_id": str(memory_id),
        "status": "deleted",
    }

