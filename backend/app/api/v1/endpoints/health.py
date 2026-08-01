from fastapi import APIRouter
from app.core.logger import logger
from fastapi import Request

router = APIRouter(
    prefix="/health",
    tags=["Health"]
)

@router.get("")
async def health(request: Request):
    logger.info("health_check_requested")
    '''logger.info(
    "health_check",
    database="UP",
    redis="UP",
    qdrant="UP",
)'''
    request_id = request.state.request_id
    logger.info(
        "health_check_requested",
        request_id=request_id,
    )
    return {
        "status": "healthy",
        "ENVIRONMENT": "development",
        "request_id": request.state.request_id
    }