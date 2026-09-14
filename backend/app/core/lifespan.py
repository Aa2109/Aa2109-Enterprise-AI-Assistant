from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.logger import logger
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
    "application_started",
    app_name=settings.APP_NAME,
    environment=settings.ENVIRONMENT    ,
)

    yield

    logger.info("application_shutdown")

