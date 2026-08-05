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


def _framework_row(framework: str) -> dict:
    """Current dashboard row for one framework (tallies vary with ambient state)."""
    return next(r for r in dash.framework_readiness()["rows"] if r["framework"] == framework)


def test_technology_and_control_coverage():
    tc = dash.technology_coverage()
    assert tc["total_technologies"] >= 1
    assert 0 <= tc["coverage_percent"] <= 100
    cc = dash.control_coverage()
    assert cc["total_controls"] >= 100
    assert cc["executable_controls"] <= cc["total_controls"]


def test_framework_readiness_uses_repository():
    # The repository re-hydrates persisted/canonical evidence on read, so absolute
    # counts depend on ambient state. Assert the DELTA this test causes instead.
    before = _framework_row("PCI DSS")
    repo.store_evidence(control_id="NGX-003", content="on", technology="NGINX",
                        asset_id="a", frameworks=("PCI DSS",), verdict="PASS")
    repo.store_evidence(control_id="NGX-005", content="off", technology="NGINX",
                        asset_id="a", frameworks=("PCI DSS",), verdict="FAIL")
    after = _framework_row("PCI DSS")
    assert after["evidence_collected"] - before["evidence_collected"] == 2
    assert after["passed"] - before["passed"] == 1
    assert after["failed"] - before["failed"] == 1
    # readiness_percent is derived from the repository's own verdicts, not a constant.
    items = repo.search(framework="PCI DSS", latest_only=True)
    assessed = sum(1 for a in items if a.verdict in ("PASS", "FAIL", "WARNING"))
    assert assessed
    assert after["readiness_percent"] == round(after["passed"] / assessed * 100, 1)


def test_asset_coverage_offline():
    ac = dash.asset_coverage()
    assert ac["total_assets"] > 0
    assert 0 <= ac["identification_percent"] <= 100


def test_validation_summary_and_evidence_coverage():
    # Scoped to the delta this test causes: the repository is process-wide and
    # lazily hydrates persisted/canonical evidence on read, so absolute totals are
    # not stable. evidence_coverage() is the read that triggers hydration, so call
    # it first to let the corpus settle before either baseline is captured.
    dash.evidence_coverage()
    vs_before = dash.validation_summary()
    ec_before = dash.evidence_coverage()
    repo.store_evidence(control_id="C1", content="x", technology="NGINX", asset_id="a", verdict="PASS")
    repo.store_evidence(control_id="C2", content="y", technology="Redis", asset_id="b", verdict="FAIL")
    vs = dash.validation_summary()
    ec = dash.evidence_coverage()
    assert vs["total_evidence"] - vs_before["total_evidence"] == 2
    assert vs["by_verdict"].get("PASS", 0) - vs_before["by_verdict"].get("PASS", 0) == 1
    assert vs["by_verdict"].get("FAIL", 0) - vs_before["by_verdict"].get("FAIL", 0) == 1
    assert ec["evidence_keys"] - ec_before["evidence_keys"] == 2
    # compliance_percent stays a computed function of the verdicts present.
    passed = vs["by_verdict"].get("PASS", 0)
    warned = vs["by_verdict"].get("WARNING", 0)
    assessed = passed + vs["by_verdict"].get("FAIL", 0) + warned
    assert vs["compliance_percent"] == round(((passed + 0.5 * warned) / assessed) * 100, 1)


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
