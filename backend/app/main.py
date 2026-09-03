# from fastapi import FastAPI

# app = FastAPI(title="Enterprise AI Knowledge Assistant", version="0.1.0")


# @app.get("/")
# def root():
#     return {"message": "Enterprise AI Assistant API"}


# @app.get("/health")
# def health():
#     return {"status": "healthy"}

from fastapi import FastAPI
from app.api.v1.api import api_router
from app.core.config import settings
from app.core.lifespan import lifespan
# from app.core.logger import configure_logging
from app.middleware.request_id import RequestIDMiddleware
from app.core.exception_handlers import (
    app_exception_handler,
    unhandled_exception_handler,
)
from app.core.exceptions import AppException

from app.observability import (
    init_observability,
)

# configure_logging()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

init_observability(app=app,)

app.add_middleware(RequestIDMiddleware)
app.include_router(api_router)
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)