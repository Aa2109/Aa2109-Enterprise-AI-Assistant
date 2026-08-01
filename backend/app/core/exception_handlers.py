'''
@app.exception_handler(AppException)
async def app_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "request_id": request.state.request_id,
            },
        },
    )
'''
    

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException
from app.core.logger import logger


async def app_exception_handler(
    request: Request,
    exc: AppException,
) -> JSONResponse:
    logger.warning(
        "application_exception",
        request_id=getattr(request.state, "request_id", None),
        error=exc.message,
        status_code=exc.status_code,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.message,
        },
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception(
        "unhandled_exception",
        request_id=getattr(request.state, "request_id", None),
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
        },
    )
    