"""Duplicate detection for predefined-query evidence persistence."""

from __future__ import annotations

import hashlib
import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from app import ecs_state
from modules.governance.engines import workflow_module as wf
from modules.operations.engines import evidence_repository as ops_repo
from modules.operations.engines import predefined_queries_engine as engine
from modules.operations.engines import predefined_query_publisher as publisher
from modules.operations.engines.query_connectors import ConnectorResult
from modules.shared.services.audit_trail import get_audit_trail


@pytest.fixture(autouse=True)
def _clean():
    ecs_state.uploaded_evidence_enrollments.clear()
    ecs_state.predefined_query_fingerprint_index.clear()
    ecs_state.predefined_query_content_index.clear()
    ecs_state.submitted_controls.clear()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    yield
    ecs_state.uploaded_evidence_enrollments.clear()
    ecs_state.predefined_query_fingerprint_index.clear()
    ecs_state.predefined_query_content_index.clear()
    ecs_state.submitted_controls.clear()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()


def _control(**overrides):
    engine.load_predefined_queries()
    control = dict(engine.get_control_by_id("PGX-001"))
    control.update(overrides)
    return control


def _result(rows=None) -> ConnectorResult:
    rows = rows if rows is not None else [["on"]]
    return ConnectorResult(
        success=True,
        output="ssl | \n-----\n on",
        duration_ms=5,
        metadata={"rows_returned": len(rows), "columns": ["ssl"], "parsed_rows": rows},
    )


def _publish(control=None, *, executed_at="2026-07-20T10:00:00+00:00", rows=None, user="tester"):
    control = control or _control()
    artifact = publisher.build_artifact_json(
        control=control,
        technology="PostgreSQL",
        query="SHOW ssl;",
        result=_result(rows),
        user=user,
        execution_id="EXEC-1",
        executed_at=executed_at,
    )
    return publisher.publish_predefined_query_evidence(
        control=control,
        technology="PostgreSQL",
        query="SHOW ssl;",
        result=_result(rows),
        user=user,
        execution_id="EXEC-1",
        framework="DB Baselining",
    ), artifact


def test_identical_artifact_detected_by_sha256(monkeypatch):
    monkeypatch.setattr(publisher, "_utc_now", lambda: "2026-07-20T10:00:00+00:00")
    first, _ = _publish()
    second, _ = _publish()
    assert first["status"] != "DUPLICATE"
    assert second["status"] == "DUPLICATE"
    assert second["duplicate_kind"] == "sha256"
    assert second["evidence_id"] == first["evidence_id"]
    assert len(ops_repo.evidence_repository) == 1


def test_logical_duplicate_ignores_execution_timestamp():
    first, artifact = _publish(executed_at="2026-07-20T08:00:00+00:00")
    artifact["executed_at"] = "2026-07-20T16:30:00+00:00"
    artifact["execution_id"] = "EXEC-OTHER"
    import json

    content = json.dumps(artifact, indent=2, sort_keys=True, default=str).encode("utf-8")
    content_hash = hashlib.sha256(content).hexdigest()
    fingerprint = publisher.build_canonical_fingerprint(
        artifact=artifact,
        framework="DB Baselining",
        evidence_period=publisher.evidence_period_from(artifact["executed_at"]),
    )
    canonical_hash = publisher.canonical_fingerprint_hash(fingerprint)
    existing, kind = publisher.find_existing_predefined_query_evidence(
        content_hash=content_hash,
        canonical_hash=canonical_hash,
    )
    assert existing is not None
    assert kind == "canonical"
    assert existing["evidence_id"] == first["evidence_id"]


def test_changed_result_is_accepted():
    first, _ = _publish(rows=[["on"]])
    second, _ = _publish(rows=[["off"]], executed_at="2026-07-20T11:00:00+00:00")
    assert first["status"] != "DUPLICATE"
    assert second["status"] != "DUPLICATE"
    assert second["evidence_id"] != first["evidence_id"]
    assert len(ops_repo.evidence_repository) == 2


def test_same_result_other_application_is_accepted():
    first, _ = _publish()
    second, _ = _publish(_control(application="Mobile Banking"))
    assert second["status"] != "DUPLICATE"
    assert second["evidence_id"] != first["evidence_id"]
    assert len(ops_repo.evidence_repository) == 2


def test_duplicate_not_enrolled_in_owner_queue(monkeypatch):
    monkeypatch.setattr(publisher, "_utc_now", lambda: "2026-07-20T10:00:00+00:00")
    first, _ = _publish()
    second, _ = _publish()
    assert second["status"] == "DUPLICATE"
    owner_items = [i for i in wf.build_owner_work_queue(limit=200) if i.get("evidence_id") == first["evidence_id"]]
    assert len(owner_items) == 1
    assert len(ecs_state.uploaded_evidence_enrollments) == 2  # evidence_id + workflow key for one enrollment


def test_duplicate_audit_event_references_original(monkeypatch):
    monkeypatch.setattr(publisher, "_utc_now", lambda: "2026-07-20T10:00:00+00:00")
    first, _ = _publish()
    second, _ = _publish()
    assert second["status"] == "DUPLICATE"
    dup_events = [e for e in get_audit_trail(50) if e.get("action") == "Predefined Query Evidence Duplicate"]
    assert dup_events
    assert first["evidence_id"] in dup_events[0].get("detail", "")


def test_canonical_fingerprint_hash_is_stable():
    artifact = {
        "application": "Net Banking",
        "environment": "local",
        "control_id": "PGX-001",
        "query_id": "PGX-001",
        "query_reference": "SHOW ssl;",
        "columns": ["ssl"],
        "result": [["on"]],
        "row_count": 1,
        "executed_at": "2026-07-20T08:00:00+00:00",
        "execution_id": "A",
    }
    fp = publisher.build_canonical_fingerprint(
        artifact=artifact,
        framework="DB Baselining",
        evidence_period="2026-07-20",
    )
    artifact["executed_at"] = "2026-07-20T18:00:00+00:00"
    artifact["execution_id"] = "B"
    fp2 = publisher.build_canonical_fingerprint(
        artifact=artifact,
        framework="DB Baselining",
        evidence_period="2026-07-20",
    )
    assert publisher.canonical_fingerprint_hash(fp) == publisher.canonical_fingerprint_hash(fp2)
