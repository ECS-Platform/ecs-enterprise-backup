"""Readiness-probe (`/readyz`) tests.

`/readyz` returns 200 when the PostgreSQL evidence repository is reachable and 503
otherwise, with a `repository_ok` flag. These tests are offline: the 503 path is
the natural state (no live DB in CI), and the 200 path is exercised by injecting a
fake EvidenceRepository so no real database is required.

Complements the existing `/healthz` (liveness) assertions in
test_production_hardening.py — this file specifically covers readiness semantics.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


# --------------------------------------------------------------------------- #
# healthz vs readyz semantics
# --------------------------------------------------------------------------- #
def test_healthz_is_liveness_only():
    """Liveness must be 200 regardless of dependencies (no I/O)."""
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_readyz_reports_503_when_repository_unreachable():
    """With no live Postgres, readiness reports not-ready (503) but never raises."""
    r = client.get("/readyz")
    assert r.status_code in (200, 503)  # 503 in CI (no DB); 200 only if a DB is present
    body = r.json()
    assert "repository_ok" in body and "status" in body
    if r.status_code == 503:
        assert body["repository_ok"] is False
        assert body["status"] == "not-ready"


def test_readyz_reports_200_when_repository_ok(monkeypatch):
    """Inject a fake repository that answers SELECT 1 -> readiness is 200/ready."""
    import ecs_platform.repository as repo_mod

    class _Cur:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, *_a, **_k):
            return None

        def fetchone(self):
            return (1,)

    class _Conn:
        def cursor(self):
            return _Cur()

    class _FakeRepo:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def connect(self):
            return _Conn()

    monkeypatch.setattr(repo_mod, "EvidenceRepository", _FakeRepo)
    r = client.get("/readyz")
    assert r.status_code == 200
    body = r.json()
    assert body["repository_ok"] is True
    assert body["status"] == "ready"


def test_readyz_never_raises_on_repository_error(monkeypatch):
    """A repository that blows up must yield a clean 503, not a 500/stacktrace."""
    import ecs_platform.repository as repo_mod

    class _BoomRepo:
        def __enter__(self):
            raise RuntimeError("db down")

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(repo_mod, "EvidenceRepository", _BoomRepo)
    r = client.get("/readyz")
    assert r.status_code == 503
    assert r.json()["repository_ok"] is False
