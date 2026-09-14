from fastapi import APIRouter

router = APIRouter(tags=["Root"])

@router.get("/")
async def root():
    return {
        "message": "Welcome to Enterprise AI Assistant"
    }