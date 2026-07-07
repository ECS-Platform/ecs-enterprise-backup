"""Tests for scripts/run_production_smoke.py.

No live external integration is contacted. The heavy FastAPI app import is skipped
via ``--skip-app`` for the orchestration tests; the registry / masking /
persistence checks run against the real (offline) internals. HTTP probing is
tested with a monkeypatched fetch (no sockets).
"""

from __future__ import annotations

import os

os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

import scripts.run_production_smoke as smoke


# --------------------------------------------------------------------------- #
# Individual checks (real, offline internals)
# --------------------------------------------------------------------------- #
def test_integration_registry_check_passes():
    chk = smoke.Check()
    smoke.check_integration_registry(chk)
    r = chk.results[-1]
    assert r["check"] == "integration_adapter_registry" and r["ok"] is True
    assert "adapters registered" in r["detail"]


def test_config_masking_check_no_leak():
    chk = smoke.Check()
    smoke.check_config_masking(chk)
    r = chk.results[-1]
    assert r["check"] == "config_masking" and r["ok"] is True
    assert "no secret leak" in r["detail"].lower()


def test_config_masking_canary_not_leaked(monkeypatch, capsys):
    # Run the full check and ensure the injected canary is cleaned up + not leaked.
    chk = smoke.Check()
    smoke.check_config_masking(chk)
    # The canary env var must be removed after the check (was unset before).
    assert "SMOKECANARY_" not in (os.environ.get("ECS_JIRA_API_TOKEN") or "")


def test_persistence_provider_check_passes():
    chk = smoke.Check()
    smoke.check_persistence_provider(chk)
    r = chk.results[-1]
    assert r["check"] == "persistence_provider" and r["ok"] is True
    assert "backend=" in r["detail"]


def test_env_presence_advisory_when_not_required(monkeypatch):
    monkeypatch.delenv("ECS_ENV", raising=False)
    chk = smoke.Check()
    smoke.check_env_presence(chk, require=False)
    r = chk.results[-1]
    assert r["ok"] is True and "advisory" in r["detail"]


def test_env_presence_fails_when_required_and_missing(monkeypatch):
    monkeypatch.delenv("ECS_ENV", raising=False)
    chk = smoke.Check()
    smoke.check_env_presence(chk, require=True)
    assert chk.results[-1]["ok"] is False


def test_env_presence_passes_when_set(monkeypatch):
    monkeypatch.setenv("ECS_ENV", "uat")
    chk = smoke.Check()
    smoke.check_env_presence(chk, require=True)
    assert chk.results[-1]["ok"] is True


# --------------------------------------------------------------------------- #
# Audit route check (with a fake app; no real import)
# --------------------------------------------------------------------------- #
class _FakeRoute:
    def __init__(self, path):
        self.path = path


class _FakeApp:
    def __init__(self, paths):
        self.routes = [_FakeRoute(p) for p in paths]


def test_audit_routes_present():
    app = _FakeApp(["/api/audit/health", "/api/audit/dashboard",
                    "/api/audit/integrations", "/api/audit/runs"])
    chk = smoke.Check()
    smoke.check_audit_routes(chk, app)
    assert chk.results[-1]["ok"] is True


def test_audit_routes_missing_detected():
    app = _FakeApp(["/api/audit/runs"])  # missing required ones
    chk = smoke.Check()
    smoke.check_audit_routes(chk, app)
    r = chk.results[-1]
    assert r["ok"] is False and "missing" in r["detail"]


def test_audit_routes_no_app():
    chk = smoke.Check()
    smoke.check_audit_routes(chk, None)
    assert chk.results[-1]["ok"] is False


# --------------------------------------------------------------------------- #
# HTTP endpoint checks (monkeypatched — no real sockets)
# --------------------------------------------------------------------------- #
def test_http_endpoints_ok(monkeypatch):
    class _Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def getcode(self): return 200

    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: _Resp())
    chk = smoke.Check()
    smoke.check_http_endpoints(chk, "http://ecs.example")
    assert all(r["ok"] for r in chk.results)
    assert len(chk.results) == len(smoke.HTTP_ENDPOINTS)


def test_http_endpoints_failure(monkeypatch):
    def _boom(*a, **k):
        raise ConnectionError("refused")
    monkeypatch.setattr("urllib.request.urlopen", _boom)
    chk = smoke.Check()
    smoke.check_http_endpoints(chk, "http://ecs.example")
    assert all(not r["ok"] for r in chk.results)


# --------------------------------------------------------------------------- #
# Orchestration (skip the heavy app import)
# --------------------------------------------------------------------------- #
def test_run_skip_app_passes_offline_checks(monkeypatch):
    monkeypatch.setenv("ECS_ENV", "uat")
    report = smoke.run(skip_app=True, require_env=True)
    names = {r["check"] for r in report["checks"]}
    assert "integration_adapter_registry" in names
    assert "config_masking" in names
    assert "persistence_provider" in names
    assert "environment_variables" in names
    # app_imports is recorded as skipped=pass
    assert any(r["check"] == "app_imports" and r["ok"] for r in report["checks"])
    assert report["ok"] is True


def test_main_json_and_strict_exit_zero(monkeypatch, capsys):
    monkeypatch.setenv("ECS_ENV", "uat")
    rc = smoke.main(["--skip-app", "--json", "--strict"])
    out = capsys.readouterr().out
    import json
    data = json.loads(out)
    assert data["ok"] is True
    assert rc == 0


def test_main_strict_exit_one_on_failure(monkeypatch):
    # Force the registry check to fail so strict returns non-zero.
    monkeypatch.setenv("ECS_ENV", "uat") if hasattr(monkeypatch, "setenv") else None
    monkeypatch.setattr(smoke, "check_integration_registry",
                        lambda chk: chk.add("integration_adapter_registry", False, "forced"))
    rc = smoke.main(["--skip-app", "--strict"])
    assert rc == 1


def test_render_smoke(monkeypatch):
    monkeypatch.setenv("ECS_ENV", "uat")
    report = smoke.run(skip_app=True)
    text = smoke.render(report)
    assert "ECS Production Smoke" in text
    assert "Result:" in text


def test_output_never_leaks_canary(monkeypatch, capsys):
    monkeypatch.setenv("ECS_ENV", "uat")
    smoke.main(["--skip-app"])
    out = capsys.readouterr().out
    assert "SMOKECANARY_" not in out  # masking check must not echo its canary
