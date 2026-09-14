"""Global exception handlers (global exception handling).

Every handler is registered explicitly in :mod:`app.main` so that every
error path — app exceptions, FastAPI ``HTTPException``, request
validation, dependency timeouts, circuit breakers, token budgets and
unhandled errors — returns the same JSON envelope:

    {
        "success": False,
        "detail": "<user-safe message>",
        "error": {
            "code": "...",
            "message": "...",
            "details": <structured, non-sensitive detail or None>,
            "request_id": "...",
        },
        # only present when settings.DEBUG is True:
        "debug": { "type": "...", "reason": "..." },
    }

The exact exception type/message is always logged with the ``request_id``
so a developer can find the reason in the logs; server-side (5xx)
failures additionally log the full traceback. Client-side (4xx) errors
log a clean line — no traceback — since the caller's own request caused
them. The response body only exposes the exact reason when
``settings.DEBUG`` — otherwise the user gets a safe, curated message and
sensitive internals stay in the logs.
"""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.budget import BudgetExceededError
from app.core.circuit_breaker import CircuitOpenError
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logger import logger
from app.core.timeout import DependencyTimeoutError

# ------------------------------------------------------------
# Shared helpers — every handler funnels through these so the
# envelope and log line stay identical across exception classes.
# ------------------------------------------------------------


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _log_exception(
    request: Request,
    exc: BaseException,
    *,
    level: str,
    error_code: str,
    status_code: int,
    extra: dict[str, Any] | None = None,
) -> None:
    """Write one structured log line per handled exception.

    A full traceback is attached only for server-side (5xx) failures, so
    the exact reason is recoverable via ``request_id``. Client-side
    errors (4xx) are the caller's own fault — ``error_code``,
    ``status_code`` and ``error_message`` tell the whole story, and
    attaching ``exc_info`` would make every handled 401/404/422 dump a
    huge stack trace to the console.
    """
    event: dict[str, Any] = {
        "request_id": _request_id(request),
        "error_code": error_code,
        "status_code": status_code,
        "error_message": str(exc),
    }
    if extra:
        event.update(extra)

    # 5xx always keep their traceback (regardless of DEBUG) so a
    # developer can chase the real reason via request_id. The traceback
    # still never reaches the response body — whether the DEBUG `debug`
    # block appears is decided separately in _error_payload().
    if status_code >= 500:
        event["exc_info"] = (type(exc), exc, exc.__traceback__)

    getattr(logger, level)("exception_handled", **event)


def _error_payload(
    request: Request,
    *,
    message: str,
    code: str,
    status_code: int,
    details: Any = None,
    exc: BaseException | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "details": details,
        "request_id": _request_id(request),
    }

    payload: dict[str, Any] = {
        "success": False,
        "detail": message,
        "error": error,
    }

    if settings.DEBUG and exc is not None:
        # A short developer-facing reason only. Full tracebacks never go
        # into the HTTP body — they are written to the logs and chased by
        # ``request_id`` so clients are not flooded with large JSON.
        payload["debug"] = {
            "type": f"{type(exc).__module__}.{type(exc).__qualname__}",
            "reason": str(exc),
        }

    return payload


def _error_response(
    request: Request,
    *,
    message: str,
    code: str,
    status_code: int,
    details: Any = None,
    exc: BaseException | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=_error_payload(
            request,
            message=message,
            code=code,
            status_code=status_code,
            details=details,
            exc=exc,
        ),
    )


def _log_level_for_status(status_code: int) -> str:
    return "error" if status_code >= 500 else "warning"


# ------------------------------------------------------------
# App exceptions (our own taxonomy)
# ------------------------------------------------------------


async def app_exception_handler(
    request: Request,
    exc: AppException,
) -> JSONResponse:
    _log_exception(
        request,
        exc,
        level=_log_level_for_status(exc.status_code),
        error_code=exc.error_code,
        status_code=exc.status_code,
        extra={"details": exc.details} if exc.details is not None else None,
    )

    return _error_response(
        request,
        message=exc.message,
        code=exc.error_code,
        status_code=exc.status_code,
        details=exc.details,
        exc=exc,
    )


# ------------------------------------------------------------
# FastAPI / Starlette built-ins
# ------------------------------------------------------------

_STATUS_CODE_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "UNPROCESSABLE_ENTITY",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
    504: "GATEWAY_TIMEOUT",
}


def _code_for_status(status_code: int) -> str:
    return _STATUS_CODE_CODES.get(status_code, "HTTP_ERROR")


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Normalize every raw ``raise HTTPException(...)`` in the app."""
    detail = exc.detail

    if isinstance(detail, dict):
        message = str(
            detail.get("message")
            or detail.get("detail")
            or detail
        )
        details: Any = detail
    else:
        message = detail if isinstance(detail, str) else str(detail)
        details = None

    code = _code_for_status(exc.status_code)

    _log_exception(
        request,
        exc,
        level=_log_level_for_status(exc.status_code),
        error_code=code,
        status_code=exc.status_code,
        extra={"details": details} if details is not None else None,
    )

    return _error_response(
        request,
        message=message,
        code=code,
        status_code=exc.status_code,
        details=details,
        exc=exc,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """422 with a structured list of field errors for the developer.

    The raw pydantic error list can carry non-JSON-serializable context,
    so only ``loc`` / ``msg`` / ``type`` are forwarded.
    """
    errors = [
        {
            "loc": [str(part) for part in err.get("loc", [])],
            "msg": err.get("msg"),
            "type": err.get("type"),
        }
        for err in exc.errors()
    ]

    _log_exception(
        request,
        exc,
        level="warning",
        error_code="VALIDATION_ERROR",
        status_code=422,
        extra={"validation_errors": errors},
    )

    return _error_response(
        request,
        message="Request validation failed.",
        code="VALIDATION_ERROR",
        status_code=422,
        details=errors,
        exc=exc,
    )


# ------------------------------------------------------------
# PR-28 reliability exceptions
# ------------------------------------------------------------


async def dependency_timeout_handler(
    request: Request,
    exc: DependencyTimeoutError,
) -> JSONResponse:
    details = {"dependency": exc.name}
    _log_exception(
        request,
        exc,
        level="error",
        error_code="UPSTREAM_TIMEOUT",
        status_code=504,
        extra=details,
    )

    return _error_response(
        request,
        message="A required service timed out. Please try again.",
        code="UPSTREAM_TIMEOUT",
        status_code=504,
        details=details,
        exc=exc,
    )


async def circuit_open_handler(
    request: Request,
    exc: CircuitOpenError,
) -> JSONResponse:
    details = {"dependency": exc.name}
    _log_exception(
        request,
        exc,
        level="error",
        error_code="DEPENDENCY_UNAVAILABLE",
        status_code=503,
        extra=details,
    )

    return _error_response(
        request,
        message="A required service is temporarily unavailable.",
        code="DEPENDENCY_UNAVAILABLE",
        status_code=503,
        details=details,
        exc=exc,
    )


async def token_budget_handler(
    request: Request,
    exc: BudgetExceededError,
) -> JSONResponse:
    details = {"max_tokens": settings.MAX_TOTAL_TOKENS}
    _log_exception(
        request,
        exc,
        level="warning",
        error_code="TOKEN_BUDGET_EXCEEDED",
        status_code=429,
        extra=details,
    )

    return _error_response(
        request,
        message="The request exceeded the AI token budget.",
        code="TOKEN_BUDGET_EXCEEDED",
        status_code=429,
        details=details,
        exc=exc,
    )


async def upstream_dependency_handler(
    request: Request,
    exc: BaseException,
) -> JSONResponse:
    """Map calls-away failures (LLM, search, HTTP providers) to a clear
    503/504 instead of a bare 500.

    The request's ``request_id`` still lets a developer find the full
    traceback in the logs — this handler only dresses up the user-facing
    message and status code.
    """
    timed_out = isinstance(exc, (TimeoutError, httpx.TimeoutException))

    if timed_out:
        code = "UPSTREAM_TIMEOUT"
        status_code = 504
        message = "A required service timed out. Please try again."
    else:
        code = "DEPENDENCY_UNAVAILABLE"
        status_code = 503
        message = (
            "A required service is temporarily unavailable. "
            "Please try again in a moment."
        )

    details = {"dependency": type(exc).__name__}

    _log_exception(
        request,
        exc,
        level="error",
        error_code=code,
        status_code=status_code,
        extra=details,
    )

    return _error_response(
        request,
        message=message,
        code=code,
        status_code=status_code,
        details=details,
        exc=exc,
    )


# ------------------------------------------------------------
# Database exceptions (SQLAlchemy)
# ------------------------------------------------------------


async def integrity_error_handler(
    request: Request,
    exc: IntegrityError,
) -> JSONResponse:
    _log_exception(
        request,
        exc,
        level="warning",
        error_code="CONFLICT",
        status_code=409,
        extra={"orig": str(exc.orig)},
    )

    return _error_response(
        request,
        message=(
            "The resource already exists or conflicts with "
            "existing data."
        ),
        code="CONFLICT",
        status_code=409,
        exc=exc,
    )


async def db_unavailable_handler(
    request: Request,
    exc: OperationalError,
) -> JSONResponse:
    _log_exception(
        request,
        exc,
        level="error",
        error_code="DATABASE_UNAVAILABLE",
        status_code=503,
    )

    return _error_response(
        request,
        message="The database is currently unavailable.",
        code="DATABASE_UNAVAILABLE",
        status_code=503,
        exc=exc,
    )


# ------------------------------------------------------------
# Catch-all
# ------------------------------------------------------------


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Last-resort 500 for anything not matched above.

    The traceback is logged in full (with request_id) so the developer
    sees the exact reason; the user sees a generic, safe message.
    """
    _log_exception(
        request,
        exc,
        level="error",
        error_code="INTERNAL_ERROR",
        status_code=500,
    )

    return _error_response(
        request,
        message="Internal Server Error",
        code="INTERNAL_ERROR",
        status_code=500,
        exc=exc,
    )