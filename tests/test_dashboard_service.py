"""Tests for the executive dashboard aggregation (Milestone 6). Offline/deterministic."""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.audit_intelligence.engines import evidence_orchestrator as orch
from modules.audit_intelligence.engines import evidence_repository as repo
from modules.audit_intelligence.engines import observation_generation as obs
from modules.audit_intelligence.engines import technology_control_mapping as mapping
from modules.audit_intelligence.services import dashboard_service as dash


@pytest.fixture(autouse=True)
def _clean():
    mapping.reset_cache()
    repo.reset_repository()
    obs.reset_observations()
    orch.reset_runs()
    yield
    mapping.reset_cache()
    repo.reset_repository()
    obs.reset_observations()
    orch.reset_runs()


def test_technology_and_control_coverage():
    tc = dash.technology_coverage()
    assert tc["total_technologies"] >= 1
    assert 0 <= tc["coverage_percent"] <= 100
    cc = dash.control_coverage()
    assert cc["total_controls"] >= 100
    assert cc["executable_controls"] <= cc["total_controls"]


def test_framework_readiness_uses_repository():
    repo.store_evidence(control_id="NGX-003", content="on", technology="NGINX",
                        asset_id="a", frameworks=("PCI DSS",), verdict="PASS")
    repo.store_evidence(control_id="NGX-005", content="off", technology="NGINX",
                        asset_id="a", frameworks=("PCI DSS",), verdict="FAIL")
    fr = dash.framework_readiness()
    pci = next(r for r in fr["rows"] if r["framework"] == "PCI DSS")
    assert pci["evidence_collected"] == 2
    assert pci["passed"] == 1 and pci["failed"] == 1
    assert pci["readiness_percent"] == 50.0


def test_asset_coverage_offline():
    ac = dash.asset_coverage()
    assert ac["total_assets"] > 0
    assert 0 <= ac["identification_percent"] <= 100


def test_validation_summary_and_evidence_coverage():
    repo.store_evidence(control_id="C1", content="x", technology="NGINX", asset_id="a", verdict="PASS")
    repo.store_evidence(control_id="C2", content="y", technology="Redis", asset_id="b", verdict="FAIL")
    vs = dash.validation_summary()
    assert vs["total_evidence"] == 2
    assert vs["compliance_percent"] == 50.0
    ec = dash.evidence_coverage()
    assert ec["evidence_keys"] == 2


def test_collection_progress_reads_runs():
    run = orch.create_run(scope_kind="control", scope_value="NGX-001", control_ids=["NGX-001"])
    for r in run.records:
        r.executable = True
    orch.execute_run(run.run_id, executor=lambda cid, u: {"ok": True, "message": "m", "rows_returned": 1, "output": "x"})
    cp = dash.collection_progress()
    assert cp["runs"] == 1
    assert cp["controls_completed"] == 1
    assert cp["progress_percent"] == 100.0


def test_risk_summary_weights_severity():
    from modules.audit_intelligence.models import ValidationResult, VERDICT_FAIL

    vr = ValidationResult(control_id="C", technology="NGINX", verdict=VERDICT_FAIL,
                          control_status="Non-Compliant", rule_id="assertion.negative_signal",
                          frameworks=("PCI DSS",), rationale="x")
    obs.generate_observation(vr, asset_id="a")  # Critical
    rs = dash.risk_summary()
    assert rs["risk_score"] >= 5
    assert rs["risk_band"] in ("Low", "Medium", "High")


def test_evidence_freshness_bands():
    repo.store_evidence(control_id="C", content="x", technology="NGINX", asset_id="a", verdict="PASS")
    fr = dash.evidence_freshness()
    assert fr["total_evidence"] == 1
    assert fr["fresh"] == 1  # just collected
    assert fr["fresh_percent"] == 100.0


def test_executive_readiness_composite():
    payload = dash.executive_readiness()
    for key in ("technology_coverage", "control_coverage", "framework_readiness",
                "asset_coverage", "evidence_coverage", "collection_progress",
                "validation_summary", "open_observations", "risk_summary", "evidence_freshness"):
        assert key in payload
    assert payload["generated_at"]
