"""Tests for the functional Evidence Reuse & Observation Lifecycle.

Covers the server-side service and the ``/api/evidence-reuse/*`` endpoints:
evidence retrieval + filters + integrity, reuse analysis, completeness
validation, observation generation (real engine, deduped), and closure
eligibility (maker-checker safe). Fully offline — uses the in-memory evidence
repository + observation engine.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from modules.audit_intelligence.engines import evidence_repository as repo
from modules.audit_intelligence.engines import observation_generation as obs
from modules.audit_intelligence.models import (
    OBS_STATUS_CLOSED,
    OBS_STATUS_SUBMITTED,
    VERDICT_FAIL,
    VERDICT_PASS,
)
from modules.audit_intelligence.services import evidence_reuse_service as ers

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_state():
    """Every test starts with an empty repository + observation store."""
    obs.reset_observations()
    repo.reset_repository()
    yield
    obs.reset_observations()
    repo.reset_repository()


def _seed_pass(control_id="DB-010", tech="PostgreSQL", app_name="Core Banking DB",
               frameworks=("PCI DSS", "RBI Cyber Security")):
    return repo.store_evidence(
        control_id=control_id, content="ssl on", technology=tech, asset_id=app_name,
        frameworks=frameworks, verdict=VERDICT_PASS, control_status="Compliant",
        evidence_quality=1.0, tags=(f"app:{app_name}",))


def _seed_fail(control_id="DB-011", tech="PostgreSQL", app_name="Core Banking DB",
               frameworks=("PCI DSS",)):
    return repo.store_evidence(
        control_id=control_id, content="ssl off", technology=tech, asset_id=app_name,
        frameworks=frameworks, verdict=VERDICT_FAIL, control_status="Non-Compliant",
        evidence_quality=0.2, tags=(f"app:{app_name}",))


# --------------------------------------------------------------------------- #
# 1. Evidence retrieval + filters + integrity
# --------------------------------------------------------------------------- #
def test_records_reads_real_repository_with_integrity():
    _seed_pass()
    out = ers.records(seed_if_empty=False)
    assert out["count"] == 1
    rec = out["records"][0]
    assert rec["control_id"] == "DB-010"
    assert rec["application"] == "Core Banking DB"
    assert rec["integrity"]["has_hash"] is True
    assert rec["integrity"]["algorithm"] == "sha256"
    assert rec["integrity"]["verified"] is True


def test_records_filters():
    _seed_pass(control_id="DB-010")
    _seed_fail(control_id="DB-011")
    assert ers.records(seed_if_empty=False, status="FAIL")["count"] == 1
    assert ers.records(seed_if_empty=False, status="PASS")["count"] == 1
    assert ers.records(seed_if_empty=False, control="DB-011")["count"] == 1
    assert ers.records(seed_if_empty=False, technology="PostgreSQL")["count"] == 2
    assert ers.records(seed_if_empty=False, technology="Oracle")["count"] == 0
    assert ers.records(seed_if_empty=False, framework="PCI DSS")["count"] == 2


def test_records_seeds_when_empty():
    out = ers.records()  # seed_if_empty defaults True
    assert out["count"] >= 1  # story evidence seeded via real repo API


# --------------------------------------------------------------------------- #
# 2. Reuse analysis
# --------------------------------------------------------------------------- #
def test_reuse_analysis_counts_obligations():
    _seed_pass(control_id="DB-010", frameworks=("PCI DSS", "RBI Cyber Security", "DPSC"))
    out = ers.analyze(seed_if_empty=False)
    s = out["reuse_summary"]
    assert s["unique_evidence"] == 1
    assert s["reuse_count"] == 3  # one evidence -> three framework obligations
    assert s["reuse_factor"] == 3.0
    assert s["frameworks_covered"] == 3
    assert s["collections_saved"] == 2
    assert s["effort_saved_hours"] == 2 * ers.HOURS_PER_COLLECTION


# --------------------------------------------------------------------------- #
# 3. Completeness + readiness
# --------------------------------------------------------------------------- #
def test_completeness_flags_gaps():
    _seed_pass(control_id="DB-010", frameworks=("PCI DSS",))
    _seed_fail(control_id="DB-011", frameworks=("PCI DSS",))
    comp = ers.validate_completeness(seed_if_empty=False)
    assert comp["total_controls"] == 2
    assert comp["covered_controls"] == 1  # only the PASS one is covered
    assert comp["gap_count"] == 1
    assert comp["complete"] is False
    states = {g["control_id"]: g["state"] for g in comp["gaps"]}
    assert states["DB-011"] == "failed"


def test_readiness_percentage():
    _seed_pass(control_id="DB-010", frameworks=("PCI DSS",))
    r = ers.readiness(seed_if_empty=False)
    assert r["readiness_pct"] == 100.0
    assert r["covered_controls"] == 1


# --------------------------------------------------------------------------- #
# 4. Observation generation (real engine, deduped)
# --------------------------------------------------------------------------- #
def test_generate_observations_uses_real_engine_and_dedupes():
    _seed_fail(control_id="DB-011", frameworks=("PCI DSS",))
    first = ers.generate_observations(seed_if_empty=False)
    assert first["created_count"] >= 1
    # The observation exists in the real observation store.
    assert len(obs.list_observations()) == first["created_count"]
    # Re-running does not duplicate.
    second = ers.generate_observations(seed_if_empty=False)
    assert second["created_count"] == 0
    assert second["skipped_existing"] >= 1


def test_generate_observations_none_when_all_covered():
    _seed_pass(control_id="DB-010", frameworks=("PCI DSS",))
    out = ers.generate_observations(seed_if_empty=False)
    assert out["created_count"] == 0
    assert not obs.list_observations()


# --------------------------------------------------------------------------- #
# 5. Closure eligibility (maker-checker safe)
# --------------------------------------------------------------------------- #
def test_closure_marks_ready_not_closed_with_approval():
    # Fail -> observation, then remediate with passing evidence (new version).
    _seed_fail(control_id="DB-011", frameworks=("PCI DSS",))
    ers.generate_observations(seed_if_empty=False)
    _seed_pass(control_id="DB-011", frameworks=("PCI DSS",))  # newer version passes

    res = ers.check_closure(require_approval=True, seed_if_empty=False)
    assert res["ready_count"] >= 1
    assert res["closed_count"] == 0  # maker-checker: NOT auto-closed
    o = obs.list_observations()[0]
    assert o.status == OBS_STATUS_SUBMITTED  # advanced but awaiting approval
    # Audit trail preserved.
    assert [h["event"] for h in o.history] == ["created", "transition"]


def test_closure_closes_without_approval():
    _seed_fail(control_id="DB-011", frameworks=("PCI DSS",))
    ers.generate_observations(seed_if_empty=False)
    _seed_pass(control_id="DB-011", frameworks=("PCI DSS",))

    res = ers.check_closure(require_approval=False, seed_if_empty=False)
    assert res["closed_count"] >= 1
    o = obs.list_observations()[0]
    assert o.status == OBS_STATUS_CLOSED


def test_closure_not_eligible_without_satisfying_evidence():
    _seed_fail(control_id="DB-011", frameworks=("PCI DSS",))
    ers.generate_observations(seed_if_empty=False)
    res = ers.check_closure(require_approval=True, seed_if_empty=False)
    assert res["ready_count"] == 0
    assert len(res["not_eligible"]) >= 1


# --------------------------------------------------------------------------- #
# 6. API route smoke tests
# --------------------------------------------------------------------------- #
def test_api_records():
    _seed_pass()
    r = client.get("/api/evidence-reuse/records?status=PASS")
    assert r.status_code == 200
    assert r.json()["count"] == 1


def test_api_analyze():
    _seed_pass(frameworks=("PCI DSS", "DPSC"))
    r = client.post("/api/evidence-reuse/analyze")
    assert r.status_code == 200
    assert r.json()["reuse_summary"]["reuse_factor"] == 2.0


def test_api_validate_completeness():
    _seed_fail()
    r = client.post("/api/evidence-reuse/validate-completeness")
    assert r.status_code == 200
    assert r.json()["gap_count"] >= 1


def test_api_generate_and_check_closure():
    _seed_fail(control_id="DB-011", frameworks=("PCI DSS",))
    g = client.post("/api/evidence-reuse/generate-observations")
    assert g.status_code == 200 and g.json()["created_count"] >= 1
    _seed_pass(control_id="DB-011", frameworks=("PCI DSS",))
    c = client.post("/api/evidence-reuse/check-closure?require_approval=true")
    assert c.status_code == 200
    body = c.json()
    assert body["ready_count"] >= 1 and body["closed_count"] == 0


def test_api_readiness_and_observations():
    _seed_pass()
    assert client.get("/api/evidence-reuse/readiness").status_code == 200
    assert client.get("/api/evidence-reuse/observations").status_code == 200


def test_api_no_secret_leak():
    # Evidence stores metadata only; ensure no hash content is mistaken for a secret
    # and error envelopes never leak internals.
    _seed_pass()
    blob = (client.get("/api/evidence-reuse/records").text
            + client.post("/api/evidence-reuse/analyze").text)
    assert "password" not in blob.lower()


# --------------------------------------------------------------------------- #
# 7. Page renders with functional workbench
# --------------------------------------------------------------------------- #
def test_page_renders_functional_workbench():
    r = client.get("/mvp/evidence-story?role=owner&user=UAT")
    assert r.status_code == 200
    assert "Functional Workbench" in r.text
    assert r.text.count("data-ers-action=") == 6  # six action buttons
    assert 'id="f-application"' in r.text  # filter inputs present
    assert "1 · Evidence Generated" in r.text  # narrative preserved
