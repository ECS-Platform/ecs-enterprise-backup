"""Phase-2 intelligence gaps: SC/LP, completeness, reuse, quality, summary, CEQ, leadership."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")
os.environ.setdefault("AUDIT_WORKFLOW_ENABLED", "true")

import pytest
from fastapi.testclient import TestClient

from ecs_platform.storage import LocalObjectStore, reset_object_store, set_object_store
from modules.audit_intelligence.engines import evidence_repository as ai_repo
from modules.audit_intelligence.engines import observation_generation as obs_gen
from modules.audit_intelligence.services import persistence as P
from modules.audit_intelligence.services.sql_persistence import SqlAuditPersistence
from modules.operations.engines import common_controls_collector as cc
from modules.operations.engines import evidence_repository as ops_repo
from modules.operations.engines import phase2_intelligence as intel
from modules.operations.engines import phase2_reusability as p2
from modules.shared.services.common_evidence_presets import execute_preset_query

from app.main import app

client = TestClient(app, follow_redirects=False)

CORE_APPS = ["net_banking", "mobile_banking", "payments"]


@pytest.fixture(autouse=True)
def _clean(tmp_path, monkeypatch):
    monkeypatch.setenv("ECS_EVIDENCE_SNAPSHOT_ENABLED", "true")
    monkeypatch.setenv("ECS_EVIDENCE_CUSTODY_MODE", "SNAPSHOT")
    monkeypatch.setenv("ECS_COMMON_CONTROLS_COLLECTION_ENABLED", "true")
    monkeypatch.setenv("ECS_MOCK_EVIDENCE_COLLECTION_ENABLED", "false")
    monkeypatch.setenv("ECS_PREDEFINED_QUERY_SCHEDULER_ENABLED", "false")
    set_object_store(LocalObjectStore(tmp_path / "objects"))
    P.reset_persistence()
    P.set_persistence(SqlAuditPersistence())
    ai_repo.reset_repository()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    obs_gen.reset_observations()
    yield
    reset_object_store()
    P.reset_persistence()
    ai_repo.reset_repository()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    obs_gen.reset_observations()


def test_three_apps_secure_configuration():
    sim = p2.simulate_application_control_reusability(
        user="tester",
        run_id="P2-SC",
        application_ids=CORE_APPS,
    )
    sc = [r for r in sim.receipts if r["control_slug"] == "secure-configuration"]
    apps = {r["application"] for r in sc}
    assert {"Net Banking", "Mobile Banking", "Payments"} <= apps
    assert all(r["collected"] for r in sc)
    assert all(r["verdict"] in {"PASS", "FAIL", "WARNING"} for r in sc)
    techs = {r["technology"] for r in sc}
    assert techs & {"linux_rhel", "kubernetes", "linux"}


def test_three_apps_least_privilege_where_applicable():
    sim = p2.simulate_application_control_reusability(
        user="tester",
        run_id="P2-LP",
        application_ids=CORE_APPS,
    )
    lp = [r for r in sim.receipts if r["control_slug"] == "identity-privileged-access"]
    apps = {r["application"] for r in lp}
    assert {"Net Banking", "Mobile Banking", "Payments"} <= apps
    assert all(r["collected"] for r in lp)
    techs = {r["technology"] for r in lp}
    assert techs & {"linux_rhel", "linux", "postgresql", "yugabyte", "aurora_mysql", "mysql"}


def test_completeness_complete_missing_stale():
    # Missing before collection
    before = intel.assess_completeness(application_ids=["payments"], control_slugs=["secure-configuration"])
    assert before["missing"] >= 1
    assert before["missing_requirements"]

    p2.simulate_application_control_reusability(
        user="tester", run_id="P2-COMP", application_ids=["payments"],
    )
    after = intel.assess_completeness(application_ids=["payments"], control_slugs=["secure-configuration"])
    assert after["complete"] >= 1

    # Force stale by rewriting uploaded_at
    for rec in ops_repo.evidence_repository:
        meta = dict(rec.get("metadata") or {})
        if meta.get("common_control_slug") == "secure-configuration":
            rec["uploaded_at"] = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
    stale = intel.assess_completeness(
        application_ids=["payments"],
        control_slugs=["secure-configuration"],
        stale_days=90,
    )
    assert stale["stale"] >= 1
    assert any(r["status"] == "STALE" for r in stale["bindings"])


def test_eligible_vs_ineligible_evidence_reuse():
    p2.simulate_application_control_reusability(
        user="tester", run_id="P2-REUSE", application_ids=["net_banking", "payments"],
    )
    nb = next(
        r for r in ops_repo.evidence_repository
        if (r.get("metadata") or {}).get("application") == "Net Banking"
        and (r.get("metadata") or {}).get("common_control_slug") == "encryption-in-transit"
    )
    pay = next(
        r for r in ops_repo.evidence_repository
        if (r.get("metadata") or {}).get("application") == "Payments"
        and (r.get("metadata") or {}).get("common_control_slug") == "encryption-in-transit"
    )
    # Cross-app similarity cannot be compliance-equivalent
    cross = intel.assess_reuse_eligibility(
        nb,
        {
            "application": "Payments",
            "environment": "UAT",
            "control_slug": "encryption-in-transit",
            "control": "CC-ENCRYPTION_IN_TRANSIT",
        },
    )
    assert cross["compliance_equivalent"] is False
    assert "cross_application_not_compliance_equivalent" in cross["reasons"]

    # Exact SHA duplicate same app is eligible
    twin = dict(nb)
    twin["metadata"] = dict(nb.get("metadata") or {})
    same = intel.assess_reuse_eligibility(twin, twin)
    assert same["exact_duplicate"] is True
    assert same["eligible"] is True


def test_deterministic_quality_score_and_reasons():
    p2.simulate_application_control_reusability(
        user="tester", run_id="P2-Q", application_ids=["payments"],
    )
    rec = ops_repo.evidence_repository[0]
    report = intel.score_evidence_quality(rec)
    assert report["ok"] is True
    assert 0 <= report["score"] <= 100
    assert report["rating"] in {"GREEN", "AMBER", "RED"}
    assert "metadata_completeness" in report["components"]
    assert "validation_result" in report["components"]
    assert "integrity_hash" in report["components"]
    assert report["reasons"]


def test_summary_fallback_without_llm():
    p2.simulate_application_control_reusability(
        user="tester", run_id="P2-SUM", application_ids=["net_banking"],
    )
    rec = ops_repo.evidence_repository[0]
    out = intel.summarize_evidence(rec, force_fallback=True)
    assert out["mode"] == "fallback"
    assert "Evidence" in out["summary"]
    assert (rec.get("metadata") or {}).get("application", "") in out["summary"] or "Net Banking" in out["summary"]


def test_phase2_query_metadata_visibility():
    p2.simulate_application_control_reusability(
        user="tester", run_id="P2-CEQ", application_ids=["net_banking"],
    )
    rows = intel.list_phase2_evidence(application="Net Banking", control_slug="encryption-at-rest")
    assert rows
    assert all(r["application"] == "Net Banking" for r in rows)
    assert all(r.get("technology") for r in rows)
    result = execute_preset_query(
        "phase2_evidence_by_app_control",
        role="owner",
        application="Net Banking",
    )
    assert result.get("ok") is True
    assert result.get("rows") is not None


def test_leadership_aggregation():
    p2.simulate_application_control_reusability(
        user="tester", run_id="P2-LEAD", application_ids=CORE_APPS,
    )
    lead = intel.build_leadership_aggregation(application_ids=CORE_APPS)
    assert lead["ok"] is True
    assert lead["totals"]["bindings"] >= 1
    assert lead["applications"]
    apps = {a["application"] for a in lead["applications"]}
    assert {"Net Banking", "Mobile Banking", "Payments"} <= apps
    api = client.get("/api/evidence-dashboard/phase2-leadership")
    assert api.status_code == 200
    body = api.json()
    assert body.get("ok") is True
    assert "totals" in body


def test_encryption_controls_still_collect():
    sim = p2.simulate_application_control_reusability(
        user="tester", run_id="P2-ENC", application_ids=["net_banking"],
    )
    slugs = {r["control_slug"] for r in sim.receipts}
    assert "encryption-at-rest" in slugs
    assert "encryption-in-transit" in slugs


def test_phase1_common_controls_unaffected():
    run = cc.collect_all_common_controls(user="tester", run_id="P1-REG")
    assert run.folders_discovered >= 10
    assert run.collected >= 1
