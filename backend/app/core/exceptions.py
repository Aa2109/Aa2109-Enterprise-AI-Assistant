"""Application exception taxonomy (global exception handling).

Every application-level error is raised as an :class:`AppException`
subclass. Handlers in :mod:`app.core.exception_handlers` translate each
into one consistent JSON envelope:

    {
        "success": False,
        "detail": "<user-safe message>",
        "error": {
            "code": "NOT_FOUND",
            "message": "<user-safe message>",
            "details": <structured, non-sensitive detail or None>,
            "request_id": "550e8400-e29b-41d4-a716-446655440000",
        },
        # only present when settings.DEBUG is True:
        "debug": { "type": "...", "reason": "..." },
    }

The exact underlying reason is always written to the structured logs so
a developer can chase it via ``request_id``; the response body only ever
carries the safe, user-facing ``message`` (plus the ``debug`` block in
non-production environments).
"""

from __future__ import annotations

from typing import Any

from fastapi import status


class AppException(Exception):
    """Base class for all application exceptions.

    Attributes:
        message: user-safe text returned in the response.
        error_code: stable machine-readable code for this error.
        status_code: HTTP status the handler should respond with.
        details: optional structured detail (must be JSON-safe and
            non-sensitive).
        internal_message: exact developer-facing reason. Written to the
            logs — never returned to the user.
    """

    DEFAULT_MESSAGE = "An unexpected error occurred."
    ERROR_CODE = "INTERNAL_ERROR"
    DEFAULT_STATUS_CODE = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | list[Any] | None = None,
        internal_message: str | None = None,
        error_code: str | None = None,
        status_code: int | None = None,
    ) -> None:
        self.message = message if message is not None else self.DEFAULT_MESSAGE
        self.error_code = error_code or self.ERROR_CODE
        self.status_code = status_code or self.DEFAULT_STATUS_CODE
        self.details = details
        self.internal_message = internal_message
        super().__init__(self.message)

    def __str__(self) -> str:
        parts = [self.error_code, self.message]
        if self.internal_message:
            parts.append(f"({self.internal_message})")
        return " ".join(parts)


# ============================================================
# HTTP-semantic exceptions (4xx)
# ============================================================


class BadRequestException(AppException):
    """The client sent a malformed or nonsensical request."""

    DEFAULT_MESSAGE = "The request is invalid."
    ERROR_CODE = "BAD_REQUEST"
    DEFAULT_STATUS_CODE = status.HTTP_400_BAD_REQUEST


class AuthenticationException(AppException):
    """The client is not (or is no longer) authenticated."""

    DEFAULT_MESSAGE = "Authentication failed. Please sign in again."
    ERROR_CODE = "AUTHENTICATION_FAILED"
    DEFAULT_STATUS_CODE = status.HTTP_401_UNAUTHORIZED


class ForbiddenException(AppException):
    """The client is authenticated but lacks permission."""

    DEFAULT_MESSAGE = (
        "You do not have permission to perform this action."
    )
    ERROR_CODE = "FORBIDDEN"
    DEFAULT_STATUS_CODE = status.HTTP_403_FORBIDDEN


class NotFoundException(AppException):
    """The requested resource does not exist."""

    DEFAULT_MESSAGE = "The requested resource was not found."
    ERROR_CODE = "NOT_FOUND"
    DEFAULT_STATUS_CODE = status.HTTP_404_NOT_FOUND


class ConflictException(AppException):
    """The request conflicts with the current state of the resource."""

    DEFAULT_MESSAGE = (
        "The request conflicts with the current state of the resource."
    )
    ERROR_CODE = "CONFLICT"
    DEFAULT_STATUS_CODE = status.HTTP_409_CONFLICT


class UnprocessableEntityException(AppException):
    """The request body is well-formed but could not be processed."""

    DEFAULT_MESSAGE = "The request could not be processed."
    ERROR_CODE = "UNPROCESSABLE_ENTITY"
    DEFAULT_STATUS_CODE = status.HTTP_422_UNPROCESSABLE_CONTENT


class ValidationException(UnprocessableEntityException):
    """Domain-level validation failure (prompt guard, SQL validator, ...)."""

    DEFAULT_MESSAGE = "The request failed validation."
    ERROR_CODE = "VALIDATION_ERROR"


class RateLimitException(AppException):
    """The client has exceeded a rate or quota limit."""

    DEFAULT_MESSAGE = "Too many requests. Please try again later."
    ERROR_CODE = "RATE_LIMITED"
    DEFAULT_STATUS_CODE = status.HTTP_429_TOO_MANY_REQUESTS


# ============================================================
# Dependency / backend exceptions
# ============================================================


class DependencyException(AppException):
    """A required dependency (LLM, vector store, search, ...) is down."""

    DEFAULT_MESSAGE = "A required service is currently unavailable."
    ERROR_CODE = "DEPENDENCY_UNAVAILABLE"
    DEFAULT_STATUS_CODE = status.HTTP_503_SERVICE_UNAVAILABLE


class UpstreamTimeoutException(AppException):
    """A required dependency exceeded its timeout budget."""

    DEFAULT_MESSAGE = "A required service timed out. Please try again."
    ERROR_CODE = "UPSTREAM_TIMEOUT"
    DEFAULT_STATUS_CODE = status.HTTP_504_GATEWAY_TIMEOUT


class DatabaseException(AppException):
    """The database is unreachable or unhealthy."""

    DEFAULT_MESSAGE = "The database is currently unavailable."
    ERROR_CODE = "DATABASE_UNAVAILABLE"
    DEFAULT_STATUS_CODE = status.HTTP_503_SERVICE_UNAVAILABLE


class TokenBudgetExceededException(AppException):
    """The per-request AI token budget was exhausted."""

    DEFAULT_MESSAGE = "The request exceeded the AI token budget."
    ERROR_CODE = "TOKEN_BUDGET_EXCEEDED"
    DEFAULT_STATUS_CODE = status.HTTP_429_TOO_MANY_REQUESTS


# ============================================================
# Project-specific exceptions
# ============================================================


class DocumentNotFoundException(NotFoundException):
    """Raised when a requested document is not found in the database."""

    def __init__(self, document_id: int | str) -> None:
        super().__init__(
            message=f"Document {document_id} not found.",
            details={"document_id": document_id},
        )