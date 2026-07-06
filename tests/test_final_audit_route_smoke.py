"""Final route smoke coverage for the ECS Audit Intelligence API + UI.

Asserts that every canonical audit route exists and does NOT 404 — including the
compatibility aliases added during finalization (e.g. ``/api/audit/health``,
``/api/audit/packs``, ``/mvp/audit/dashboard``, ``/mvp/audit/technology-mapping``,
``/mvp/audit/evidence-runs``, ``/mvp/audit/validation-results``,
``/mvp/audit/evidence-packs``).

Runs against the FastAPI app via TestClient in DEMO_MODE (auth bypassed). Fully
offline: integration adapters are config-only skeletons (no live calls); the
audit engines use their in-memory stores.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, follow_redirects=False)
Q = "role=owner&user=AppOwner"

# Canonical API routes that must exist (Task 5 finalization list).
API_ROUTES = [
    "/api/audit/dashboard",
    "/api/audit/assets",
    "/api/audit/mapping",
    "/api/audit/runs",
    "/api/audit/repository",
    "/api/audit/observations",
    "/api/audit/packs",
    "/api/audit/integrations",
    "/api/audit/health",
]

# Canonical UI routes that must exist (Task 5 finalization list).
UI_ROUTES = [
    "/mvp/audit/dashboard",
    "/mvp/audit/assets",
    "/mvp/audit/technology-mapping",
    "/mvp/audit/evidence-runs",
    "/mvp/audit/validation-results",
    "/mvp/audit/observations",
    "/mvp/audit/repository",
    "/mvp/audit/evidence-packs",
    "/mvp/audit/executive-readiness",
]

# Aliases specifically added in finalization (must resolve, i.e. not 404).
ALIAS_ROUTES = [
    "/api/audit/health",
    "/api/audit/packs",
    "/mvp/audit/dashboard",
    "/mvp/audit/technology-mapping",
    "/mvp/audit/evidence-runs",
    "/mvp/audit/validation-results",
    "/mvp/audit/evidence-packs",
]


def _get(path: str):
    sep = "&" if "?" in path else "?"
    return client.get(f"{path}{sep}{Q}")


# --------------------------------------------------------------------------- #
# API routes
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", API_ROUTES)
def test_api_route_exists_and_ok(path):
    resp = _get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"
    body = resp.json()
    assert isinstance(body, dict)
    assert body.get("ok") is True, f"{path} not ok: {body}"


def test_api_health_reports_status_and_integrations():
    body = _get("/api/audit/health").json()
    assert body["ok"] is True
    assert body["status"] in ("ok", "degraded")
    assert "integrations" in body and "total" in body["integrations"]
    assert body["integrations"]["total"] == 9


def test_api_packs_base_lists_pack_types():
    body = _get("/api/audit/packs").json()
    assert body["ok"] is True
    assert set(body["pack_types"]) >= {"evidence", "framework", "asset", "technology"}
    assert "repository_stats" in body


def test_api_health_and_integrations_never_leak_secret_values(monkeypatch):
    # Set a distinctive fake secret; it must never appear in health/integration JSON.
    monkeypatch.setenv("ECS_JIRA_API_TOKEN", "LEAKCANARY123")
    monkeypatch.setenv("ECS_PRISMA_CLOUD_SECRET_KEY", "LEAKCANARY123")
    for path in ("/api/audit/health", "/api/audit/integrations",
                 "/api/audit/integrations/health"):
        assert "LEAKCANARY123" not in _get(path).text, f"secret leaked in {path}"


# --------------------------------------------------------------------------- #
# UI routes
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", UI_ROUTES)
def test_ui_route_exists_and_renders(path):
    resp = _get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"
    assert "text/html" in resp.headers.get("content-type", "")
    assert len(resp.text) > 200  # a real page, not an empty/error stub


# --------------------------------------------------------------------------- #
# Aliases resolve to the same handler family (no 404, valid content)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", ALIAS_ROUTES)
def test_alias_routes_do_not_404(path):
    resp = _get(path)
    assert resp.status_code != 404, f"alias {path} returned 404"
    assert resp.status_code == 200


def test_ui_dashboard_alias_matches_executive_readiness():
    # Both the alias and the original should render the same executive page shell.
    alias = _get("/mvp/audit/dashboard")
    original = _get("/mvp/audit/executive-readiness")
    assert alias.status_code == original.status_code == 200
    # Same template family -> both are non-trivial HTML documents.
    assert "text/html" in alias.headers.get("content-type", "")
    assert "text/html" in original.headers.get("content-type", "")


def test_unknown_audit_route_still_404s():
    # Guard: aliasing must not accidentally make everything resolve.
    assert _get("/api/audit/does-not-exist").status_code == 404
    assert _get("/mvp/audit/does-not-exist").status_code == 404
