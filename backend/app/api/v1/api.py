from fastapi import APIRouter

from app.api.v1.endpoints import (
    approvals,
    auth,
    chat,
    conversations,
    document,
    health,
    memories,
    metrics,
    root,
    search,
    stream,
    temp,
)

api_router = APIRouter()

api_router.include_router(root.router)
api_router.include_router(health.router)
api_router.include_router(temp.router)
api_router.include_router(document.router)
api_router.include_router(search.router)
api_router.include_router(chat.router)
api_router.include_router(conversations.router)
api_router.include_router(stream.router)
api_router.include_router(approvals.router)
api_router.include_router(memories.router)
api_router.include_router(metrics.router)
api_router.include_router(auth.router)
