from fastapi import APIRouter
from app.core.logger import logger

router = APIRouter(
    prefix="/health",
    tags=["Health"]
)

@router.get("")
async def health():
    logger.info("health_check_requested")
    '''logger.info(
    "health_check",
    database="UP",
    redis="UP",
    qdrant="UP",
)'''
    return {
        "status": "healthy"
    }