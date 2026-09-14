"""Global exception handler tests.

Every API error — app exceptions, raw HTTPExceptions, request
validation, dependency timeouts, circuit breakers, token budgets,
SQLAlchemy errors and catch-all 500s — must come back in the same
envelope with a safe user message, a stable error code, and the
request_id echoed, while the exact reason only surfaces in the response
when DEBUG is on.
"""

from __future__ import annotations

from uuid import uuid4

import httpx
import openai
import pytest
import requests
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.budget import BudgetExceededError
from app.core.circuit_breaker import CircuitOpenError
from app.core.config import settings
from app.core.exception_handlers import (
    app_exception_handler,
    circuit_open_handler,
    db_unavailable_handler,
    dependency_timeout_handler,
    http_exception_handler,
    integrity_error_handler,
    token_budget_handler,
    unhandled_exception_handler,
    upstream_dependency_handler,
    validation_exception_handler,
)
from app.core.exceptions import (
    AppException,
    DocumentNotFoundException,
    NotFoundException,
)
from app.core.timeout import DependencyTimeoutError
from app.middleware.request_id import RequestIDMiddleware

RID = str(uuid4())


class _Body(BaseModel):
    name: str


def _build_app() -> FastAPI:
    # Mirror the wiring in app/main.py so the tests exercise the same
    # registered handler set.
    app = FastAPI()

    @app.get("/not-found")
    def not_found() -> None:
        raise NotFoundException(
            "The widget was not found.",
            details={"widget_id": 7},
        )

    @app.get("/http-exc")
    def http_exc() -> None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    @app.post("/validation")
    def validation(body: _Body) -> dict:
        return {"name": body.name}

    @app.get("/timeout")
    def timeout() -> None:
        raise DependencyTimeoutError("search", 5.0)

    @app.get("/circuit")
    def circuit() -> None:
        raise CircuitOpenError("rag")

    @app.get("/budget")
    def budget() -> None:
        raise BudgetExceededError("AI token budget exceeded")

    @app.get("/integrity")
    def integrity() -> None:
        raise IntegrityError("INSERT ...", {}, Exception("pk constraint"))

    @app.get("/db-unavailable")
    def db_unavailable() -> None:
        raise OperationalError(
            "SELECT ...", {}, Exception("connection refused")
        )

    @app.get("/boom")
    def boom() -> None:
        raise ValueError("secret internal reason")

    @app.get("/upstream-timeout")
    def upstream_timeout() -> None:
        raise TimeoutError("timed out waiting for the LLM")

    @app.get("/upstream-connection")
    def upstream_connection() -> None:
        raise ConnectionError("connection refused by search provider")

    @app.get("/upstream-httpx")
    def upstream_httpx() -> None:
        raise httpx.ConnectError("could not connect to provider")

    @app.get("/upstream-requests")
    def upstream_requests() -> None:
        raise requests.ConnectionError("could not connect to provider")

    @app.get("/upstream-openai")
    def upstream_openai() -> None:
        raise openai.APIError(
            "provider returned an error",
            request=None,
            body=None,
        )

    @app.get("/document-not-found")
    def document_not_found() -> None:
        raise DocumentNotFoundException("doc-123")

    app.add_middleware(RequestIDMiddleware)
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,
    )
    app.add_exception_handler(
        DependencyTimeoutError,
        dependency_timeout_handler,
    )
    app.add_exception_handler(CircuitOpenError, circuit_open_handler)
    app.add_exception_handler(BudgetExceededError, token_budget_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(OperationalError, db_unavailable_handler)
    app.add_exception_handler(TimeoutError, upstream_dependency_handler)
    app.add_exception_handler(ConnectionError, upstream_dependency_handler)
    app.add_exception_handler(httpx.HTTPError, upstream_dependency_handler)
    app.add_exception_handler(
        requests.RequestException,
        upstream_dependency_handler,
    )
    app.add_exception_handler(openai.APIError, upstream_dependency_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    return app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(
        _build_app(),
        raise_server_exceptions=False,
    )


def _headers() -> dict[str, str]:
    return {"X-Request-ID": RID}


# ------------------------------------------------------------
# AppException → app_exception_handler
# ------------------------------------------------------------


def test_app_exception_envelope(client: TestClient):
    resp = client.get("/not-found", headers=_headers())

    assert resp.status_code == 404

    body = resp.json()
    assert body["success"] is False
    assert body["detail"] == "The widget was not found."
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["message"] == "The widget was not found."
    assert body["error"]["details"] == {"widget_id": 7}
    assert body["error"]["request_id"] == RID


def test_document_not_found_accepts_string_id(client: TestClient):
    resp = client.get("/document-not-found", headers=_headers())

    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["message"] == "Document doc-123 not found."
    assert body["error"]["details"] == {"document_id": "doc-123"}


# ------------------------------------------------------------
# HTTPException → http_exception_handler
# ------------------------------------------------------------


def test_http_exception_normalized(client: TestClient):
    resp = client.get("/http-exc", headers=_headers())

    assert resp.status_code == 404

    body = resp.json()
    assert body["success"] is False
    # detail is preserved verbatim for existing clients.
    assert body["detail"] == "Conversation not found"
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["request_id"] == RID


# ------------------------------------------------------------
# RequestValidationError → validation_exception_handler
# ------------------------------------------------------------


def test_validation_errors_are_structured(client: TestClient):
    resp = client.post("/validation", json={"name": 123}, headers=_headers())

    assert resp.status_code == 422

    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"

    errors = body["error"]["details"]
    assert isinstance(errors, list)
    assert errors
    assert errors[0]["loc"] == ["body", "name"]
    assert errors[0]["type"]
    assert errors[0]["msg"]


# ------------------------------------------------------------
# PR-28 reliability exceptions
# ------------------------------------------------------------


def test_dependency_timeout_is_504(client: TestClient):
    resp = client.get("/timeout", headers=_headers())

    assert resp.status_code == 504
    body = resp.json()
    assert body["error"]["code"] == "UPSTREAM_TIMEOUT"
    assert body["error"]["details"] == {"dependency": "search"}
    assert body["error"]["request_id"] == RID


def test_circuit_open_is_503(client: TestClient):
    resp = client.get("/circuit", headers=_headers())

    assert resp.status_code == 503
    body = resp.json()
    assert body["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
    assert body["error"]["details"] == {"dependency": "rag"}


def test_token_budget_is_429(client: TestClient):
    resp = client.get("/budget", headers=_headers())

    assert resp.status_code == 429
    body = resp.json()
    assert body["error"]["code"] == "TOKEN_BUDGET_EXCEEDED"
    assert body["error"]["details"] == {
        "max_tokens": settings.MAX_TOTAL_TOKENS
    }


# ------------------------------------------------------------
# Upstream / calls-away failures → 503 / 504
# ------------------------------------------------------------


def test_bare_timeout_is_504(client: TestClient):
    resp = client.get("/upstream-timeout", headers=_headers())

    assert resp.status_code == 504
    body = resp.json()
    assert body["error"]["code"] == "UPSTREAM_TIMEOUT"
    assert body["error"]["details"] == {"dependency": "TimeoutError"}
    assert body["error"]["request_id"] == RID
    assert "timed out waiting for the LLM" not in body["detail"]


def test_connection_error_is_503(client: TestClient):
    resp = client.get("/upstream-connection", headers=_headers())

    assert resp.status_code == 503
    body = resp.json()
    assert body["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
    assert body["error"]["details"] == {"dependency": "ConnectionError"}


def test_httpx_error_is_503(client: TestClient):
    resp = client.get("/upstream-httpx", headers=_headers())

    assert resp.status_code == 503
    body = resp.json()
    assert body["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
    assert body["error"]["details"] == {"dependency": "ConnectError"}


def test_requests_error_is_503(client: TestClient):
    resp = client.get("/upstream-requests", headers=_headers())

    assert resp.status_code == 503
    body = resp.json()
    assert body["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
    assert body["error"]["details"] == {"dependency": "ConnectionError"}


def test_openai_error_is_503(client: TestClient):
    resp = client.get("/upstream-openai", headers=_headers())

    assert resp.status_code == 503
    body = resp.json()
    assert body["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
    assert body["error"]["details"] == {"dependency": "APIError"}
    assert "provider returned an error" not in body["detail"]


# ------------------------------------------------------------
# Database errors
# ------------------------------------------------------------


def test_integrity_error_is_409(client: TestClient):
    resp = client.get("/integrity", headers=_headers())

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT"


def test_db_unavailable_is_503(client: TestClient):
    resp = client.get("/db-unavailable", headers=_headers())

    assert resp.status_code == 503
    body = resp.json()
    assert body["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert body["detail"] == "The database is currently unavailable."


# ------------------------------------------------------------
# Catch-all → unhandled_exception_handler
# ------------------------------------------------------------


def test_unhandled_500_hides_internals_from_user(client: TestClient):
    resp = client.get("/boom", headers=_headers())

    assert resp.status_code == 500
    body = resp.json()
    assert body["detail"] == "Internal Server Error"
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["request_id"] == RID
    # The internal reason must never leak to the user.
    assert "secret internal reason" not in body["detail"]
    assert "DEBUG" not in body


def test_unhandled_500_exposes_reason_when_debug_is_on(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "DEBUG", True)

    resp = client.get("/boom", headers=_headers())

    assert resp.status_code == 500
    body = resp.json()

    debug = body["debug"]
    assert "secret internal reason" in debug["reason"]
    assert "ValueError" in debug["type"]
    # Full tracebacks never go into the HTTP body — they are logged and
    # chased by request_id.
    assert "trace" not in debug


def test_unhandled_500_excludes_reason_when_debug_is_off(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "DEBUG", False)

    resp = client.get("/boom", headers=_headers())

    assert resp.status_code == 500
    assert "debug" not in resp.json()
    assert "secret internal reason" not in resp.text


# ------------------------------------------------------------
# Real app wiring (app/main.py → temp endpoint)
# ------------------------------------------------------------


def test_real_app_wraps_errors_in_the_envelope():
    """A live request through the real app must hit the global handlers."""
    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get(
            "/test/document-not-found",
            headers=_headers(),
        )

    assert resp.status_code == 404

    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["message"] == "Document doc-123 not found."
    assert body["error"]["details"] == {"document_id": "doc-123"}
    assert body["error"]["request_id"] == RID