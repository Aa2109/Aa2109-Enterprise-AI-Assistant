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
from app.core.logger import configure_logging

configure_logging()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.include_router(api_router)