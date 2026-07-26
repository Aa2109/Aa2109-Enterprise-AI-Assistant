from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "application_started",
        application="Enterprise AI Assistant",
    )

    yield

    logger.info("application_shutdown")