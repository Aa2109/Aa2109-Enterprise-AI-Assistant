from typing import Any

import asyncpg
import httpx
from fastapi import APIRouter, Response, status
from redis.asyncio import Redis

from backend.app.config import Settings, get_settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "alive"}


async def check_postgres(settings: Settings) -> None:
    database_url = settings.database_url.replace("+asyncpg", "")
    connection = await asyncpg.connect(database_url, timeout=2)
    await connection.close()


async def check_redis(settings: Settings) -> None:
    client = Redis.from_url(settings.redis_url, socket_connect_timeout=2)
    try:
        await client.ping()
    finally:
        await client.aclose()


async def check_http_service(url: str, path: str) -> None:
    async with httpx.AsyncClient(base_url=url, timeout=2) as client:
        response = await client.get(path)
        response.raise_for_status()


async def check_dependencies(settings: Settings) -> dict[str, str]:
    checks: dict[str, str] = {}
    checks_to_run: dict[str, Any] = {
        "postgres": check_postgres,
        "redis": check_redis,
        "qdrant": lambda current_settings: check_http_service(
            current_settings.qdrant_url, "/healthz"
        ),
        "minio": lambda current_settings: check_http_service(
            current_settings.minio_endpoint, "/minio/health/live"
        ),
    }
    for name, check in checks_to_run.items():
        try:
            await check(settings)
            checks[name] = "ok"
        except Exception:
            checks[name] = "unavailable"
    return checks


@router.get("/ready")
async def ready(response: Response, settings: Settings | None = None) -> dict[str, Any]:
    if settings is None:
        settings = get_settings()
    checks = await check_dependencies(settings)
    is_ready = all(value == "ok" for value in checks.values())
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready" if is_ready else "not_ready", "checks": checks}
