"""Phase-1 predefined query registry and execution gating tests."""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.operations.engines import predefined_queries_engine as engine
from modules.operations.engines import predefined_query_phase1_registry as phase1
from modules.operations.engines.connector_common import build_execution_result
from modules.operations.engines.query_connectors import ConnectorResult


@pytest.fixture(autouse=True)
def _reload_catalog():
    phase1.load_phase1_registry.cache_clear()
    engine.load_predefined_queries(force=True)
    yield


def _controls():
    return engine.get_all_controls()


def test_full_catalog_loads_208_unique_ids():
    controls = _controls()
    assert len(controls) == 208
    ids = [c["control_id"] for c in controls]
    assert len(ids) == len(set(ids))


def test_phase1_filter_only_approved_technologies():
    selected = phase1.phase1_selected_ids()
    assert 70 <= len(selected) <= 100
    techs = {c.get("technology") for c in _controls() if c["control_id"] in selected}
    assert techs <= phase1.phase1_technologies()
    assert not techs & phase1.deferred_technologies()


def test_every_phase1_selected_has_query_text():
    missing = [
        c["control_id"]
        for c in _controls()
        if c["control_id"] in phase1.phase1_selected_ids() and not (c.get("query") or "").strip()
    ]
    assert not missing


def test_unsafe_sql_rejected_for_postgresql():
    control = engine.get_control_by_id("PGX-001")
    assert control
    bad = dict(control)
    bad["query"] = "DROP TABLE users;"
    assert engine._normalize_query_allowlist(bad["query"]) not in engine.ALLOWED_POSTGRESQL_QUERIES


def test_missing_target_returns_configuration_error(monkeypatch):
    monkeypatch.setattr(phase1, "has_configured_target", lambda t: False)
    ctrl = engine.get_control_by_id("PGX-001")
    cap = engine.assess_execution_capability(ctrl)
    assert cap["status"] == "Configuration Required"
    assert cap["executable"] is False


def test_missing_dependency_returns_structured_error(monkeypatch):
    monkeypatch.setattr(engine, "_dependency_available", lambda t: False)
    ctrl = engine.get_control_by_id("PGX-001")
    cap = engine.assess_execution_capability(ctrl)
    assert cap["status"] == "Dependency Missing"


def test_successful_execution_persists_evidence(monkeypatch):
    from modules.operations.engines import connector_common as cc

    recorded = {}

    def _register(evidence, framework=""):
        recorded["evidence_id"] = evidence.evidence_id
        return {"filename": "test.txt", "evidence_id": evidence.evidence_id}

    monkeypatch.setattr(cc, "register_with_evidence_repository", _register)
    control = engine.get_control_by_id("PGX-001")
    result = ConnectorResult(success=True, output="ssl=on", duration_ms=12, metadata={"rows_returned": 1})
    payload = cc.complete_connector_execution(control, "tester", "PostgreSQL", "SHOW ssl;", result)
    assert payload["ok"] is True
    assert payload["evidence_id"]
    assert payload["execution"]["status"] == "Success"
    assert payload["execution"]["control_id"] == "PGX-001"


def test_failed_execution_creates_no_successful_evidence(monkeypatch):
    from modules.operations.engines import connector_common as cc

    monkeypatch.setattr(cc, "register_with_evidence_repository", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not register")))
    control = engine.get_control_by_id("PGX-001")
    result = ConnectorResult(success=False, output="", error_message="connection refused", duration_ms=5)
    payload = cc.complete_connector_execution(control, "tester", "PostgreSQL", "SHOW ssl;", result)
    assert payload["ok"] is False
    assert payload["execution"]["validation_result"] == "FAIL"


def test_framework_mappings_retained_for_phase1_controls():
    for cid in sorted(phase1.phase1_selected_ids())[:10]:
        ctrl = engine.get_control_by_id(cid)
        assert ctrl.get("frameworks") or ctrl.get("framework_coverage")


def test_deferred_controls_are_not_executed():
    deferred_id = "MSX-001"
    res = engine.run_predefined_query(deferred_id, "tester")
    assert res["ok"] is False
    assert res.get("error_type") == "deferred_control"


def test_dry_run_performs_no_remote_changes(monkeypatch):
    called = {"n": 0}

    def _boom(*a, **k):
        called["n"] += 1
        raise RuntimeError("should not connect")

    monkeypatch.setattr(engine, "run_postgresql_query", _boom)
    cap = engine.assess_execution_capability(engine.get_control_by_id("PGX-001"))
    assert called["n"] == 0
    assert cap["status"] in {"Ready", "Configuration Required", "Dependency Missing"}


def test_build_execution_result_fields():
    control = engine.get_control_by_id("PGX-001")
    structured = build_execution_result(
        execution_id="PQ-EXEC-000001",
        control=control,
        technology="PostgreSQL",
        query="SHOW ssl;",
        started_at="2026-07-20T10:00:00+00:00",
        completed_at="2026-07-20T10:00:01+00:00",
        status="Success",
        result=ConnectorResult(success=True, output="on", metadata={"rows_returned": 1}),
        evidence_id="PQ-EVD-000001",
    )
    for key in (
        "execution_id", "control_id", "technology", "target", "command_or_query_reference",
        "started_at", "completed_at", "status", "raw_output_reference", "parsed_values",
        "validation_result", "error_code", "error_message",
    ):
        assert key in structured
