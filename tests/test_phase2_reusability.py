"""Phase-2 encryption-control reusability simulation tests."""

from __future__ import annotations

import ast
import copy
import os
from pathlib import Path

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")
os.environ.setdefault("AUDIT_WORKFLOW_ENABLED", "true")

import pytest

from ecs_platform.storage import LocalObjectStore, reset_object_store, set_object_store
from modules.audit_intelligence.engines import evidence_repository as ai_repo
from modules.audit_intelligence.engines import observation_generation as obs_gen
from modules.audit_intelligence.services import persistence as P
from modules.audit_intelligence.services.sql_persistence import SqlAuditPersistence
from modules.operations.engines import common_controls_collector as cc
from modules.operations.engines import evidence_repository as ops_repo
from modules.operations.engines import phase2_reusability as p2
from modules.operations.engines import phase2_tech_adapters as adapters
from modules.operations.engines import scheduler_module as sm

REPO = Path(__file__).resolve().parents[1]
ENCRYPTION_CONTROLS = ["encryption-at-rest", "encryption-in-transit"]


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
    sm._execution_history.clear()
    sm._run_progress.clear()
    yield
    reset_object_store()
    P.reset_persistence()
    ai_repo.reset_repository()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    obs_gen.reset_observations()
    sm._execution_history.clear()
    sm._run_progress.clear()


def _core_apps_portfolio() -> dict:
    data = copy.deepcopy(p2.load_application_portfolio())
    data["applications"] = [
        a for a in data["applications"] if a.get("id") in {"net_banking", "mobile_banking", "payments"}
    ]
    return data


def test_netbanking_both_encryption_controls():
    sim = p2.simulate_application_control_reusability(
        user="tester",
        run_id="P2-NB",
        application_ids=["net_banking"],
    )
    assert sim.collected >= 2
    slugs = {r["control_slug"] for r in sim.receipts}
    assert set(ENCRYPTION_CONTROLS) <= slugs
    techs = {r["technology"] for r in sim.receipts}
    assert "aurora_mysql" in techs
    assert "nginx" in techs


def test_mobile_banking_both_controls_across_applicable_technologies():
    sim = p2.simulate_application_control_reusability(
        user="tester",
        run_id="P2-MB",
        application_ids=["mobile_banking"],
    )
    assert set(ENCRYPTION_CONTROLS) <= {r["control_slug"] for r in sim.receipts}
    at_rest = [r for r in sim.receipts if r["control_slug"] == "encryption-at-rest"]
    transit = [r for r in sim.receipts if r["control_slug"] == "encryption-in-transit"]
    assert {r["technology"] for r in at_rest} >= {"postgresql", "mysql", "yugabyte", "aerospike"}
    assert "nginx" in {r["technology"] for r in transit}
    assert len(at_rest) >= 4
    assert len(transit) >= 2
    assert all(r["collected"] for r in sim.receipts)


def test_payments_both_controls_existing_technologies():
    sim = p2.simulate_application_control_reusability(
        user="tester",
        run_id="P2-PAY",
        application_ids=["payments"],
    )
    assert set(ENCRYPTION_CONTROLS) <= {r["control_slug"] for r in sim.receipts}
    techs = {r["technology"] for r in sim.receipts}
    assert "postgresql" in techs
    assert "tomcat" in techs
    assert all(r["collected"] for r in sim.receipts)


def test_full_portfolio_matrix_includes_dummy_app():
    sim = p2.simulate_application_control_reusability(user="tester", run_id="P2-FULL")
    apps = {r["application"] for r in sim.receipts}
    assert {"Net Banking", "Mobile Banking", "Payments", "Demo Card Portal"} <= apps
    assert sim.combinations == sim.collected
    assert sim.collected >= 12


def test_same_adapter_reused_by_multiple_applications():
    nb = next(p for p in p2.list_application_profiles() if p.id == "net_banking")
    mb = next(p for p in p2.list_application_profiles() if p.id == "mobile_banking")
    dummy = next(p for p in p2.list_application_profiles() if p.id == "demo_card_portal")
    assert p2.select_technology_for_control(nb, "encryption-in-transit") == "nginx"
    assert "nginx" in p2.select_technologies_for_control(mb, "encryption-in-transit")
    assert "nginx" in p2.select_technologies_for_control(dummy, "encryption-in-transit")
    fixture = adapters.adapt_control_evidence("nginx", "encryption-in-transit")
    assert fixture["tls_enabled"] is True


def test_no_application_specific_collector_exists():
    adapter_src = (REPO / "modules/operations/engines/phase2_tech_adapters.py").read_text()
    orch_src = (REPO / "modules/operations/engines/phase2_reusability.py").read_text()
    for banned in ("NetBankingCollector", "MobileBankingCollector", "PaymentsCollector", "if app_id =="):
        assert banned not in adapter_src
        assert banned not in orch_src
    tree = ast.parse(adapter_src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            assert "net_banking" not in node.name
            assert "mobile_banking" not in node.name
            assert "payments" not in node.name
    assert "collect_common_control_folder" in orch_src


def test_config_only_dummy_app_onboarding():
    """Adding an app to YAML is enough — no new adapter/collector code."""
    full = p2.load_application_portfolio()
    assert any(a.get("id") == "demo_card_portal" for a in full["applications"])
    without = _core_apps_portfolio()
    core = p2.simulate_application_control_reusability(
        user="tester", run_id="P2-CORE", portfolio=without
    )
    with_dummy = p2.simulate_application_control_reusability(
        user="tester", run_id="P2-DUMMY", application_ids=["demo_card_portal"]
    )
    assert with_dummy.collected >= 2
    assert with_dummy.combinations > 0
    assert all(r["application"] == "Demo Card Portal" for r in with_dummy.receipts)
    # Dummy uses already-supported postgresql + nginx adapters only
    assert {r["technology"] for r in with_dummy.receipts} <= {"postgresql", "nginx"}
    assert core.collected >= 2


def test_existing_lifecycle_reused():
    sim = p2.simulate_application_control_reusability(
        user="tester", run_id="P2-LIFE", application_ids=["net_banking", "payments"]
    )
    assert ops_repo.evidence_repository
    sample = ops_repo.evidence_repository[0]
    assert sample.get("sha256")
    assert sample.get("object_uri") or (sample.get("metadata") or {}).get("content_sha256")
    assert sample.get("source_connector") == "common_controls"
    assert (sample.get("metadata") or {}).get("collection_source") == "CommonControls"
    assert (sample.get("metadata") or {}).get("scheduler_run_id") == "P2-LIFE"


def test_scheduler_requires_no_application_specific_change():
    sched_src = (REPO / "modules/operations/engines/scheduler_module.py").read_text()
    for token in ("net_banking", "mobile_banking", "phase2_application_portfolio", "demo_card_portal"):
        assert token not in sched_src
    run = cc.collect_all_common_controls(user="tester", run_id="P1-STILL")
    assert run.folders_discovered >= 10
    assert run.collected >= 1


def test_evidence_tagged_by_app_env_asset_control():
    sim = p2.simulate_application_control_reusability(
        user="tester", run_id="P2-TAGS", application_ids=["net_banking", "payments"]
    )
    tagged = [
        r
        for r in ops_repo.evidence_repository
        if (r.get("metadata") or {}).get("scheduler_run_id") == "P2-TAGS"
    ]
    assert len(tagged) == sim.collected == sim.combinations
    apps = {(r.get("application_tags") or [""])[0] for r in tagged}
    assert {"Net Banking", "Payments"} <= apps
    allowed = {
        "encryption-at-rest",
        "encryption-in-transit",
        "secure-configuration",
        "identity-privileged-access",
    }
    for rec in tagged:
        meta = rec.get("metadata") or {}
        assert meta.get("application")
        assert meta.get("environment") == "UAT"
        assert meta.get("asset_id")
        assert meta.get("technology")
        assert meta.get("common_control_slug") in allowed
        assert rec.get("control")


def test_hashing_versioning_storage_still_work():
    first = p2.simulate_application_control_reusability(
        user="tester", run_id="P2-HASH-1", application_ids=["payments"]
    )
    hashes = {
        r.get("sha256") or (r.get("metadata") or {}).get("content_sha256")
        for r in ops_repo.evidence_repository
        if (r.get("metadata") or {}).get("scheduler_run_id") == "P2-HASH-1"
    }
    assert hashes and all(hashes)
    before = len(ops_repo.evidence_repository)
    second = p2.simulate_application_control_reusability(
        user="tester", run_id="P2-HASH-2", application_ids=["payments"]
    )
    assert first.collected == second.collected
    assert second.collected >= 2
    for rec in ops_repo.evidence_repository[before:]:
        assert rec.get("object_uri") or (rec.get("metadata") or {}).get("content_sha256")


def test_at_rest_adapters_cover_required_databases():
    for tech in ("aurora_mysql", "mysql", "postgresql", "yugabyte", "aerospike"):
        payload = adapters.adapt_control_evidence(tech, "encryption-at-rest")
        assert payload.get("encryption_at_rest") is True
        assert int(payload.get("encrypted_datastores_pct") or 0) >= 95


def test_in_transit_adapters_cover_web_and_db_tls():
    for tech in ("nginx", "tomcat", "postgresql", "mysql", "aurora_mysql", "yugabyte", "aerospike"):
        payload = adapters.adapt_control_evidence(tech, "encryption-in-transit")
        assert payload.get("tls_enabled") is True
        assert payload.get("min_protocol") in {"TLS1.2", "TLS1.3"}
