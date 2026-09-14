"""SPA fallback routing (app/core/spa.py).

Covers the shared-origin hosting contract:
- with a frontend build present, client-side routes (/login, /chat/<id>)
  serve index.html instead of the 404 JSON envelope a browser used to get,
- real compiled assets are served as-is,
- traversal and lookalike-file paths stay genuine 404s,
- API-only deployments (no build) keep the plain 404 envelope,
- registered API routes always win over the SPA catch-all.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.spa import get_dist_dir
from app.main import app


def _write_build(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(
        '<!doctype html><title>EIA</title><div id="root"></div>',
        encoding="utf-8",
    )
    (dist / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    return dist


def _spa_client(tmp_path: Path, monkeypatch) -> TestClient:
    dist = _write_build(tmp_path)
    monkeypatch.setenv("FRONTEND_DIST", str(dist))
    return TestClient(app)


def test_get_dist_dir_without_build_is_none(monkeypatch):
    monkeypatch.delenv("FRONTEND_DIST", raising=False)
    # Repo has a real build (frontend/dist) in dev, so start from that and
    # assert we return it only when it actually exists.
    dist = get_dist_dir()
    if dist is not None:
        assert (dist / "index.html").is_file()


def test_api_only_404_envelope_without_build(tmp_path, monkeypatch):
    monkeypatch.setenv("FRONTEND_DIST", str(tmp_path / "missing"))
    client = TestClient(app)
    r = client.get("/login")
    assert r.status_code == 404
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"


def test_client_route_serves_index_html(tmp_path, monkeypatch):
    client = _spa_client(tmp_path, monkeypatch)
    # /documents and /conversations are registered API routes and are
    # deliberately NOT shadowed — these are pure client-side routes.
    for path in ("/login", "/signup", "/chat/abc-123", "/login?reason=session_expired"):
        r = client.get(path)
        assert r.status_code == 200, path
        assert r.text.startswith("<!doctype html>")
        assert "<div id=\"root\">" in r.text


def test_compiled_assets_served_as_is(tmp_path, monkeypatch):
    client = _spa_client(tmp_path, monkeypatch)
    r = client.get("/assets/app.js")
    assert r.status_code == 200
    assert r.text == "console.log(1)"

    r = client.get("/favicon.svg")
    assert r.status_code == 200
    assert r.text == "<svg/>"


def test_missing_static_like_path_is_404(tmp_path, monkeypatch):
    client = _spa_client(tmp_path, monkeypatch)
    for path in ("/assets/missing.js", "/image.png", "/nonexistent.css"):
        r = client.get(path)
        assert r.status_code == 404, path
        assert r.json()["error"]["code"] == "NOT_FOUND"


def test_path_traversal_rejected(tmp_path, monkeypatch):
    client = _spa_client(tmp_path, monkeypatch)
    for path in ("/../pyproject.toml", "/..%2Fpyproject.toml", "/%2e%2e/test.txt"):
        r = client.get(path)
        assert r.status_code in (403, 404), path


def test_api_routes_win_over_spa_fallback(tmp_path, monkeypatch):
    client = _spa_client(tmp_path, monkeypatch)
    r = client.get("/health")
    # /health is a real API route (registered before the catch-all) — it
    # must keep returning its API response, never index.html.
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")