"""SPA static hosting for the built frontend.

The API and the browser UI share an origin in single-host deployments
(and locally behind the backend). The React router uses client-side
routes like ``/login`` and ``/chat/<id>`` that exist only in the browser —
the backend has no route for them, so a full page load used to surface a
raw 404 JSON envelope instead of the app.

This module hands those paths to the built frontend when one is
available:

- request paths that resolve to a real compiled file (``/assets/...``,
  ``/favicon.svg``) are served as-is,
- any other GET is an SPA route and gets ``index.html`` so React Router
  takes over,
- paths that *look* like missing static files (a trailing extension) and
  any path outside the dist directory still get a genuine 404.

An API-only deployment (no frontend build on disk) is unchanged: every
handler falls back to the usual 404 envelope.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import Request
from fastapi.responses import FileResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException


def get_dist_dir() -> Path | None:
    """Resolve the compiled frontend directory, or ``None`` to stay API-only.

    An explicit ``FRONTEND_DIST`` is authoritative: when set it must point
    at a usable build, otherwise no SPA is served (no silent fallback to a
    stale repo build). Without it, the repo's ``frontend/dist`` is used
    when present. Returns ``None`` when no build exists so the app keeps
    its JSON envelope for unknown paths.
    """
    override = os.environ.get("FRONTEND_DIST")
    if override:
        candidate = Path(override)
        if candidate.is_dir() and (candidate / "index.html").is_file():
            return candidate
        return None

    for candidate in (
        Path(__file__).resolve().parents[3] / "frontend" / "dist",
        Path(__file__).resolve().parents[2] / "frontend" / "dist",
    ):
        if candidate.is_dir() and (candidate / "index.html").is_file():
            return candidate

    return None


def _guard_inside(dist: Path, target: Path) -> Path:
    """Reject any path that would escape the dist directory."""
    root = dist.resolve()
    resolved = target.resolve()
    inside = str(resolved) == str(root) or str(resolved).startswith(
        str(root) + os.sep
    )
    if not inside:
        raise StarletteHTTPException(
            status_code=403,
            detail="Requested resource is outside the static directory.",
        )
    return resolved


async def spa_fallback(request: Request, full_path: str) -> Response:
    """Serve the compiled SPA for browser routes that only exist client-side."""
    dist = get_dist_dir()
    if dist is None:
        # API-only deployment → keep the normal 404 envelope.
        raise StarletteHTTPException(status_code=404)

    target = _guard_inside(dist, dist / full_path)

    if target.is_file():
        return FileResponse(target)

    # A path with a trailing extension that isn't a real file is a
    # genuine miss (e.g. a missing asset) — 404, don't paper over it.
    if Path(full_path).suffix:
        raise StarletteHTTPException(status_code=404)

    index = dist / "index.html"
    if index.is_file():
        return FileResponse(index)

    raise StarletteHTTPException(status_code=404)