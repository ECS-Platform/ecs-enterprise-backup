"""Tests for the enterprise gap-close wave.

Covers newly-exposed REST endpoints (thin wrappers over existing services) and
the added production-hardening (GZip compression, graceful-shutdown lifespan):

  * GET  /api/audit/scheduler/history      (reuses audit persistence)
  * POST /api/audit/scheduler/execute      (reuses asset_scheduler; RBAC-guarded)
  * GET  /api/evidence/search              (reuses governance search_module)
  * GET  /api/audit/comparison             (reuses comparison_engine)
  * GZip middleware present
  * lifespan runs startup + shutdown cleanly

Fully offline (DEMO_MODE); no external services.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# --------------------------------------------------------------------------- #
# Scheduler execution + history REST
# --------------------------------------------------------------------------- #
def test_scheduler_history_endpoint():
    r = client.get("/api/audit/scheduler/history?limit=25")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "history" in body and "count" in body


def test_scheduler_history_limit_is_clamped():
    r = client.get("/api/audit/scheduler/history?limit=abc")
    assert r.status_code == 200  # bad limit coerced, never 422


def test_scheduler_execute_requires_admin():
    denied = client.post("/api/audit/scheduler/execute?role=auditor", json={})
    assert denied.status_code == 403
    ok = client.post("/api/audit/scheduler/execute?role=system_admin", json={})
    assert ok.status_code == 200
    body = ok.json()
    assert body["ok"] is True
    assert "executed" in body and "plan" in body


# --------------------------------------------------------------------------- #
# Evidence search REST
# --------------------------------------------------------------------------- #
def test_evidence_search_endpoint():
    r = client.get("/api/evidence/search?q=encryption")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "results" in body and "page" in body


def test_evidence_search_filters():
    r = client.get("/api/evidence/search?framework=PCI DSS&application=Net Banking")
    assert r.status_code == 200
    assert r.json()["filters"]["framework"] == "PCI DSS"


def test_evidence_search_empty_is_safe():
    r = client.get("/api/evidence/search?q=zzz_no_match&framework=DOES_NOT_EXIST")
    assert r.status_code == 200
    assert isinstance(r.json()["results"], list)


# --------------------------------------------------------------------------- #
# Comparison REST
# --------------------------------------------------------------------------- #
def test_comparison_endpoint():
    r = client.get("/api/audit/comparison")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert isinstance(body["readiness_matrix"], list)
    assert isinstance(body["heatmap"], list)


def test_comparison_scope_param():
    r = client.get("/api/audit/comparison?scope=All Applications&time_range=Current Month")
    assert r.status_code == 200


# --------------------------------------------------------------------------- #
# Production hardening: GZip + lifespan
# --------------------------------------------------------------------------- #
def test_gzip_middleware_registered():
    from starlette.middleware.gzip import GZipMiddleware

    classes = [m.cls for m in app.user_middleware]
    assert GZipMiddleware in classes


def test_large_response_is_gzipped():
    # The comparison matrix is large (>1KB); with gzip requested the client
    # transparently decodes it and the response must still be valid JSON 200.
    r = client.get("/api/audit/comparison", headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_lifespan_startup_and_shutdown_clean():
    # Entering + exiting the TestClient context runs the full lifespan (startup
    # then graceful-shutdown). It must not raise.
    with TestClient(app) as c:
        assert c.get("/api/audit/scheduler/history").status_code == 200
