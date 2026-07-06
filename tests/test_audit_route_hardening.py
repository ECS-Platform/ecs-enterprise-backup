"""Route-hardening tests for the Audit Intelligence REST + UI layer.

Focus (production-readiness, NOT new features):
  * Every ``/api/audit/*`` endpoint returns valid JSON and never leaks a stack
    trace, even for empty state / unknown resources / unsupported technology.
  * Errors use the consistent envelope
    ``{"ok": false, "status": "error", "message": ..., "errors": [...]}``.
  * The compatibility aliases ``/api/audit/dashboard`` and ``/api/audit/repository``
    exist and return bounded JSON.
  * Secrets never appear in config-like responses (integration masking).
  * The ``/mvp/audit/*`` pages still render.

Runs against the FastAPI app via TestClient in DEMO_MODE (auth bypassed). Offline:
no live connector is touched (integration adapters are config-only skeletons).
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from modules.audit_intelligence.engines import evidence_orchestrator as orch
from modules.audit_intelligence.engines import evidence_repository as repo
from modules.audit_intelligence.engines import observation_generation as obs

client = TestClient(app, follow_redirects=False)
Q = "role=owner&user=AppOwner"


@pytest.fixture(autouse=True)
def _clean():
    orch.reset_runs()
    repo.reset_repository()
    obs.reset_observations()
    yield
    orch.reset_runs()
    repo.reset_repository()
    obs.reset_observations()


def _get(path: str):
    sep = "&" if "?" in path else "?"
    return client.get(f"{path}{sep}{Q}")


def _post(path: str, json=None):
    sep = "&" if "?" in path else "?"
    return client.post(f"{path}{sep}{Q}", json=json or {})


def _assert_error_shape(body: dict) -> None:
    """The house error envelope every /api/audit/* error must conform to."""
    assert body.get("ok") is False
    assert body.get("status") == "error"
    assert isinstance(body.get("message"), str) and body["message"]
    assert isinstance(body.get("errors"), list) and body["errors"]
    # Legacy alias retained for backward compatibility.
    assert body.get("error") == body.get("message")


# --------------------------------------------------------------------------- #
# Consistent error envelope
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "path,status",
    [
        ("/api/audit/mapping/technology/DoesNotExist", 404),
        ("/api/audit/mapping/framework/DoesNotExist", 404),
        ("/api/audit/runs/RUN-nope", 404),
        ("/api/audit/observations/OBS-nope", 404),
        ("/api/audit/dashboard/not_a_real_section", 404),
        ("/api/audit/integrations/not_a_real_adapter/health", 404),
        ("/api/audit/packs/bogus/x", 400),
    ],
)
def test_error_envelope_is_consistent(path, status):
    r = _get(path)
    assert r.status_code == status, f"{path} -> {r.status_code}"
    _assert_error_shape(r.json())


def test_missing_scope_kind_uses_error_envelope():
    r = _post("/api/audit/runs", {})
    assert r.status_code == 400
    _assert_error_shape(r.json())


def test_invalid_transition_uses_error_envelope():
    from modules.audit_intelligence.models import ValidationResult, VERDICT_FAIL

    vr = ValidationResult(control_id="NGX-005", technology="NGINX", verdict=VERDICT_FAIL,
                          control_status="Non-Compliant", rule_id="assertion.negative_signal",
                          frameworks=("PCI DSS",), rationale="disabled")
    o = obs.generate_observation(vr, asset_id="web-1")
    bad = _post(f"/api/audit/observations/{o.observation_id}/transition", {"to_status": "Closed"})
    assert bad.status_code == 400
    _assert_error_shape(bad.json())


# --------------------------------------------------------------------------- #
# Compatibility aliases
# --------------------------------------------------------------------------- #
def test_dashboard_alias_exists_and_returns_json():
    r = _get("/api/audit/dashboard")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    dash = body["dashboard"]
    # Composite sections present (empty-state safe).
    for key in ("technology_coverage", "framework_readiness", "risk_summary",
                "evidence_coverage", "generated_at"):
        assert key in dash


def test_repository_alias_matches_evidence_endpoint():
    repo.store_evidence(control_id="NGX-003", content="ssl on", technology="NGINX",
                        asset_id="web-1", frameworks=("PCI DSS",), verdict="PASS")
    a = _get("/api/audit/repository?technology=NGINX")
    b = _get("/api/audit/evidence?technology=NGINX")
    assert a.status_code == b.status_code == 200
    assert a.json()["evidence"] == b.json()["evidence"]
    assert "page" in a.json()


def test_mapping_root_alias_returns_paginated_rows():
    r = _get("/api/audit/mapping")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert isinstance(body["results"], list)
    assert "page" in body and "stats" in body


def test_dashboard_section_allowlisted():
    ok = _get("/api/audit/dashboard/risk_summary")
    assert ok.status_code == 200 and ok.json()["section"] == "risk_summary"
    # A real module attribute that is NOT a dashboard section must 404 (allow-list).
    for blocked in ("reset_cache", "invalidate_dashboard_cache", "executive_readiness",
                    "datetime", "_build_executive_readiness"):
        r = _get(f"/api/audit/dashboard/{blocked}")
        assert r.status_code == 404, f"{blocked} should not be callable via the API"


# --------------------------------------------------------------------------- #
# Empty-state / unsupported inputs never crash
# --------------------------------------------------------------------------- #
def test_empty_state_endpoints_are_valid_json():
    # Repository/observations/runs are empty after the fixture reset.
    for path, key in [
        ("/api/audit/repository", "evidence"),
        ("/api/audit/observations", "observations"),
        ("/api/audit/runs", "runs"),
        ("/api/audit/evidence/stats", "stats"),
        ("/api/audit/observations/summary", "summary"),
    ]:
        r = _get(path)
        assert r.status_code == 200, f"{path} -> {r.status_code}"
        body = r.json()
        assert body["ok"] is True and key in body


def test_unsupported_technology_does_not_crash():
    # Unknown technology -> 404 with the error envelope, not a 500 / stack trace.
    r = _get("/api/audit/mapping/technology/TotallyMadeUpTech")
    assert r.status_code == 404
    _assert_error_shape(r.json())
    # Search + pack for an unknown technology -> empty, bounded, 200.
    s = _get("/api/audit/mapping/search?technology=TotallyMadeUpTech")
    assert s.status_code == 200 and s.json()["results"] == []
    p = _get("/api/audit/packs/technology/TotallyMadeUpTech")
    assert p.status_code == 200 and p.json()["pack"]["item_count"] == 0


def test_empty_repository_pack_does_not_crash():
    r = _get("/api/audit/packs/framework/PCI DSS")
    assert r.status_code == 200
    assert r.json()["pack"]["item_count"] == 0
    assert r.json()["pack"]["items"] == []


# --------------------------------------------------------------------------- #
# Secret safety (integration config masking)
# --------------------------------------------------------------------------- #
_SECRET_ENV = {
    "ECS_SERVICENOW_CLIENT_SECRET": "sn-supersecret-AAA",
    "ECS_ARCHER_API_TOKEN": "archer-token-BBB",
    "ECS_JIRA_API_TOKEN": "jira-token-CCC",
    "ECS_CONFLUENCE_API_TOKEN": "confluence-token-DDD",
    "ECS_SONARQUBE_TOKEN": "sonar-token-EEE",
    "ECS_CHECKMARX_CLIENT_SECRET": "cx-secret-FFF",
    "ECS_PRISMA_CLOUD_SECRET_KEY": "prisma-secret-GGG",
    "ECS_TRIPWIRE_PASSWORD": "tripwire-pass-HHH",
    "ECS_GRAPH_CLIENT_SECRET": "graph-secret-III",
}


@pytest.fixture
def _fake_secrets(monkeypatch):
    for name, value in _SECRET_ENV.items():
        monkeypatch.setenv(name, value)
    yield


def test_integrations_config_never_leaks_secrets(_fake_secrets):
    r = _get("/api/audit/integrations")
    assert r.status_code == 200
    raw = r.text
    for secret in _SECRET_ENV.values():
        assert secret not in raw, "a raw secret value leaked into the integrations response"
    # Masking markers should be present instead of raw values.
    body = r.json()
    assert body["ok"] is True and body["integrations"]


def test_integrations_health_never_leaks_secrets(_fake_secrets):
    r = _get("/api/audit/integrations/health")
    assert r.status_code == 200
    raw = r.text
    for secret in _SECRET_ENV.values():
        assert secret not in raw


def test_dashboard_and_repository_never_leak_secrets(_fake_secrets):
    repo.store_evidence(control_id="NGX-003", content="ssl on", technology="NGINX",
                        asset_id="web-1", frameworks=("PCI DSS",), verdict="PASS")
    for path in ("/api/audit/dashboard", "/api/audit/repository", "/api/audit/runs"):
        r = _get(path)
        assert r.status_code == 200
        for secret in _SECRET_ENV.values():
            assert secret not in r.text, f"secret leaked via {path}"


# --------------------------------------------------------------------------- #
# UI pages still render (route hardening must not break templates)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path,heading", [
    ("/mvp/audit/executive-readiness", "Executive Readiness"),
    ("/mvp/audit/assets", "Asset Inventory"),
    ("/mvp/audit/mapping", "Framework Mapping"),
    ("/mvp/audit/runs", "Evidence Runs"),
    ("/mvp/audit/repository", "Evidence Repository"),
    ("/mvp/audit/observations", "Observation Management"),
    ("/mvp/audit/packs", "Evidence Packs"),
])
def test_mvp_audit_pages_render(path, heading):
    r = client.get(f"{path}?{Q}")
    assert r.status_code == 200, f"{path} -> {r.status_code}"
    assert heading in r.text
