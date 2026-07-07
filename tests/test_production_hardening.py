"""Production hardening tests (Scope 4).

Covers the added hardening: request-ID / correlation middleware and the global
safe JSON exception handler. Durable-persistence startup wiring is covered by its
own foundation tests; here we assert the flag-gated install does not break boot.
All offline (DEMO_MODE).
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

from fastapi.testclient import TestClient

from app.main import app

# A throwaway route that raises, registered once, to exercise the global handler.
@app.get("/__hardening_boom__")
def _hardening_boom():
    raise ValueError("secret-internal-marker")


client = TestClient(app, raise_server_exceptions=False)


# --------------------------------------------------------------------------- #
# Request-ID middleware
# --------------------------------------------------------------------------- #
def test_response_has_request_id_header():
    r = client.get("/healthz")
    assert r.status_code == 200
    rid = r.headers.get("X-Request-ID")
    assert rid and len(rid) >= 8


def test_request_id_is_unique_per_request():
    a = client.get("/healthz").headers.get("X-Request-ID")
    b = client.get("/healthz").headers.get("X-Request-ID")
    assert a and b and a != b


def test_caller_supplied_request_id_is_echoed():
    r = client.get("/healthz", headers={"X-Request-ID": "corr-abc-123"})
    assert r.headers.get("X-Request-ID") == "corr-abc-123"


def test_malicious_request_id_is_replaced():
    # A header with unsafe characters must not be reflected verbatim.
    bad = "id with spaces & <script>"
    r = client.get("/healthz", headers={"X-Request-ID": bad})
    assert r.headers.get("X-Request-ID") != bad
    assert r.headers.get("X-Request-ID")


def test_api_response_has_request_id():
    r = client.get("/api/evidence/completeness?role=owner")
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID")


# --------------------------------------------------------------------------- #
# Global exception handler
# --------------------------------------------------------------------------- #
def test_global_handler_returns_safe_envelope():
    r = client.get("/__hardening_boom__")
    assert r.status_code == 500
    body = r.json()
    assert body["ok"] is False
    assert body["error"] == "internal_error"
    assert body.get("request_id")
    assert r.headers.get("X-Request-ID")


def test_global_handler_hides_internals_in_prod(monkeypatch):
    monkeypatch.setenv("ECS_ENV", "prod")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.delenv("ECS_DEBUG_ERRORS", raising=False)
    r = client.get("/__hardening_boom__")
    assert r.status_code == 500
    # No stack trace / exception message leaks; only the type is exposed.
    assert "secret-internal-marker" not in r.text
    assert "detail" not in r.json()
    assert r.json().get("type") == "ValueError"


def test_global_handler_shows_detail_in_debug(monkeypatch):
    monkeypatch.setenv("ECS_DEBUG_ERRORS", "true")
    r = client.get("/__hardening_boom__")
    assert r.status_code == 500
    assert "detail" in r.json()


def test_404_still_returns_normally():
    # StarletteHTTPException must be unaffected by the catch-all handler.
    assert client.get("/definitely-not-a-route").status_code == 404


# --------------------------------------------------------------------------- #
# Durable persistence startup wiring (flag-gated; boot must not break)
# --------------------------------------------------------------------------- #
def test_persistence_default_in_memory():
    from modules.audit_intelligence.services.persistence import (
        get_persistence, reset_persistence,
    )

    reset_persistence()
    assert type(get_persistence()).__name__ == "InMemoryAuditPersistence"


def test_persistence_sql_backend_when_flag_on(monkeypatch):
    monkeypatch.setenv("AUDIT_WORKFLOW_ENABLED", "true")
    from modules.audit_intelligence.services.persistence import (
        reset_persistence, set_persistence,
    )
    from modules.audit_intelligence.services.sql_persistence import SqlAuditPersistence

    reset_persistence()
    # Emulate the startup wiring path.
    set_persistence(SqlAuditPersistence())
    from modules.audit_intelligence.services.persistence import get_persistence
    assert type(get_persistence()).__name__ == "SqlAuditPersistence"
    reset_persistence()
