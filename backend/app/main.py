# from fastapi import FastAPI

# app = FastAPI(title="Enterprise AI Knowledge Assistant", version="0.1.0")


# @app.get("/")
# def root():
#     return {"message": "Enterprise AI Assistant API"}


# @app.get("/health")
# def health():
#     return {"status": "healthy"}

import httpx
import openai
import requests
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.api import api_router
from app.core.budget import BudgetExceededError
from app.core.circuit_breaker import CircuitOpenError
from app.core.config import settings
from app.core.spa import spa_fallback
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
from app.core.exceptions import AppException
from app.core.lifespan import lifespan

# from app.core.logger import configure_logging
from app.core.timeout import DependencyTimeoutError
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.security import SecurityHeadersMiddleware
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

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(api_router)

# ------------------------------------------------------------
# SPA hosting (shared origin).
#
# Registered last so every real API route wins. Catches client-side
# routes that only exist in the React app (/login, /chat/<id>, /documents)
# and serves the compiled frontend when it is present — otherwise these
# paths previously surfaced a raw 404 JSON envelope in the browser.
# With no build on disk (e.g. the API-only Docker image) it stays a 404.
# ------------------------------------------------------------
app.add_api_route(
    "/{full_path:path}",
    spa_fallback,
    methods=["GET"],
    include_in_schema=False,
    name="spa",
)

# ------------------------------------------------------------
# Global exception handlers.
#
# Every error path returns the same envelope
#   {success, detail, error:{code, message, details, request_id}}
# (plus a `debug` block when DEBUG is on). Concrete handlers are
# registered per exception class so the exact reason is logged with the
# request_id while the user only ever sees a safe message.
# ------------------------------------------------------------
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
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
# Calls-away failures (LLM / search / HTTP providers) get a clear 503/504
# instead of a bare 500. The shared catch-all below still catches genuine
# internal bugs.
app.add_exception_handler(TimeoutError, upstream_dependency_handler)
app.add_exception_handler(ConnectionError, upstream_dependency_handler)
app.add_exception_handler(httpx.HTTPError, upstream_dependency_handler)
app.add_exception_handler(
    requests.RequestException,
    upstream_dependency_handler,
)
app.add_exception_handler(openai.APIError, upstream_dependency_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)