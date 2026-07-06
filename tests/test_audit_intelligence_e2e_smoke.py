"""End-to-end smoke test for the Audit Intelligence pipeline (deterministic, mocked).

Exercises the full chain with NO live systems / Docker / network:
  ServiceNow (mock transport) -> asset discovery -> fingerprinting ->
  technology->control mapping -> evidence orchestration (mock executor) ->
  validation -> observation generation -> evidence repository -> evidence pack ->
  dashboard aggregation -> REST API responses.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from modules.audit_intelligence.engines import (
    asset_discovery,
    evidence_orchestrator as orch,
    evidence_packs,
    evidence_repository as repo,
    evidence_validation as validation,
    observation_generation as obs,
    technology_control_mapping as mapping,
    technology_fingerprint as fp,
)
from modules.audit_intelligence.services import dashboard_service

client = TestClient(app, follow_redirects=False)
Q = "role=owner&user=AppOwner"


@pytest.fixture(autouse=True)
def _clean():
    for m in (mapping, fp):
        m.reset_cache()
    orch.reset_runs()
    repo.reset_repository()
    obs.reset_observations()
    yield
    orch.reset_runs()
    repo.reset_repository()
    obs.reset_observations()


def _servicenow_transport(method, url, headers, params):
    return {"result": [
        {"sys_id": "SNOW-1", "name": "svc-nginx-lb", "sys_class_name": "cmdb_ci_server",
         "used_for": "UAT", "assigned_to": "InfraOps"},
        {"sys_id": "SNOW-2", "name": "db-postgres-01", "sys_class_name": "cmdb_ci_server",
         "used_for": "UAT", "assigned_to": "DBA"},
    ]}


def _executor(control_id, user):
    """Mock predefined-query executor producing pass/fail signals deterministically."""
    if control_id == "NGX-005":  # assertion control -> disabled -> FAIL
        return {"ok": True, "message": "ok", "rows_returned": 1, "duration_ms": 5,
                "output": "server_tokens off; disabled", "evidence_id": "E5", "evidence_filename": "e5.txt"}
    return {"ok": True, "message": "ok", "rows_returned": 1, "duration_ms": 5,
            "output": "TLSv1.2 enabled", "evidence_id": f"E-{control_id}", "evidence_filename": "e.txt"}


def test_full_pipeline_end_to_end(monkeypatch):
    monkeypatch.setenv("ECS_SERVICENOW_BASE_URL", "https://uat.example.service-now.com")

    # 1. Asset discovery from mocked ServiceNow
    assets = asset_discovery.discover_from_servicenow(transport=_servicenow_transport)
    assert len(assets) == 2

    # 2. Fingerprinting produced technologies
    techs = {a.technology for a in assets}
    assert "NGINX" in techs and "PostgreSQL" in techs

    # 3. Technology -> control mapping
    nginx_controls = mapping.controls_for_technology("NGINX")
    assert any(c.control_id == "NGX-005" for c in nginx_controls)

    # 4. Evidence orchestration (mock executor) over NGINX controls
    run = orch.create_run(scope_kind="technology", scope_value="NGINX",
                          control_ids=["NGX-003", "NGX-005"], asset_id="SNOW-1")
    for rec in run.records:
        rec.executable = True
    orch.execute_run(run.run_id, executor=_executor)
    assert run.status == "Completed"

    # 5. Validation
    controls_by_id = {c.control_id: c.to_dict() for c in mapping.all_controls()}
    results = validation.validate_records(run.records, controls_by_id)
    verdicts = {r.control_id: r.verdict for r in results}
    assert verdicts["NGX-003"] == "PASS"
    assert verdicts["NGX-005"] == "FAIL"
    summary = validation.compliance_summary(results)
    assert 0 <= summary["compliance_percent"] <= 100

    # 6. Observation generation from failures
    observations = obs.generate_from_results(results, asset_id="SNOW-1", controls_by_id=controls_by_id)
    assert len(observations) == 1  # only NGX-005 failed
    assert observations[0].control_id == "NGX-005"

    # 7. Evidence repository storage
    stored = repo.store_from_run(run, results_by_control={r.control_id: r for r in results})
    assert len(stored) == 2
    assert repo.stats()["evidence_keys"] == 2

    # 8. Evidence pack + verifiable manifest
    pack = evidence_packs.technology_pack("NGINX")
    assert pack["item_count"] == 2
    assert evidence_packs.verify_manifest(pack) is True

    # 9. Dashboard aggregation reflects the stored evidence
    dash = dashboard_service.executive_readiness()
    assert dash["evidence_coverage"]["evidence_keys"] == 2
    assert dash["open_observations"]["total"] == 1
    assert dash["validation_summary"]["total_evidence"] == 2

    # 10. REST API responses are consistent
    r = client.get(f"/api/audit/dashboard?{Q}")
    assert r.status_code == 200 and r.json()["ok"] is True
    r2 = client.get(f"/api/audit/evidence?technology=NGINX&{Q}")
    assert r2.status_code == 200 and len(r2.json()["evidence"]) == 2
    r3 = client.get(f"/api/audit/observations/summary?{Q}")
    assert r3.status_code == 200 and r3.json()["summary"]["total"] == 1


def test_pipeline_empty_state_is_safe():
    """With no discovery/evidence, every stage returns safe empty results."""
    assert asset_discovery.discover() == []
    dash = dashboard_service.executive_readiness()
    assert dash["evidence_coverage"]["evidence_keys"] == 0
    assert dash["open_observations"]["total"] == 0
    r = client.get(f"/api/audit/evidence?{Q}")
    assert r.status_code == 200 and r.json()["evidence"] == []
    r2 = client.get(f"/api/audit/dashboard?{Q}")
    assert r2.status_code == 200 and r2.json()["ok"] is True


def test_unsupported_technology_scope_is_safe():
    run = orch.create_run(scope_kind="technology", scope_value="NonExistentTech")
    assert run.records == []
    out = orch.execute_run(run.run_id, executor=_executor)
    assert out.status == "Completed"  # nothing to do, no crash
