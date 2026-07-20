"""Focused tests for predefined-query JSON evidence persistence."""

from __future__ import annotations

import json
import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from app import ecs_state
from modules.operations.engines import connector_common as cc
from modules.operations.engines import predefined_queries_engine as engine
from modules.operations.engines import predefined_query_publisher as publisher
from modules.operations.engines import evidence_repository as ops_repo
from modules.operations.engines.query_connectors import ConnectorResult


@pytest.fixture(autouse=True)
def _clean_stores():
    ecs_state.uploaded_evidence_enrollments.clear()
    ecs_state.predefined_query_fingerprint_index.clear()
    ecs_state.predefined_query_content_index.clear()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    engine.set_execution_persist(False)
    yield
    ecs_state.uploaded_evidence_enrollments.clear()
    ecs_state.predefined_query_fingerprint_index.clear()
    ecs_state.predefined_query_content_index.clear()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    engine.set_execution_persist(False)


def _pgx_control():
    engine.load_predefined_queries()
    return engine.get_control_by_id("PGX-001")


def _success_result() -> ConnectorResult:
    return ConnectorResult(
        success=True,
        output="ssl | \n-----\n on",
        duration_ms=12,
        metadata={"rows_returned": 1},
    )


def test_preview_does_not_persist(monkeypatch):
    calls: list[dict] = []

    def _publish(**kwargs):
        calls.append(kwargs)
        return {"evidence_id": "EV-1"}

    monkeypatch.setattr(publisher, "publish_predefined_query_evidence", _publish)
    control = _pgx_control()
    payload = cc.complete_connector_execution(control, "tester", "PostgreSQL", "SHOW ssl;", _success_result())
    assert payload["ok"] is True
    assert payload["evidence_persisted"] is False
    assert payload["evidence_id"] == ""
    assert calls == []


def test_persist_true_creates_one_evidence_artifact(monkeypatch):
    captured: dict = {}

    def _register_upload(**kwargs):
        captured.update(kwargs)
        return {
            "evidence_id": "EV-PQ-001",
            "filename": kwargs["filename"],
            "sha256": "abc123",
            "object_uri": "file:///tmp/demo.json",
        }

    import modules.operations.engines.evidence_repository as ops_repo

    monkeypatch.setattr(ops_repo, "register_upload", _register_upload)
    control = _pgx_control()
    payload = cc.complete_connector_execution(
        control, "tester", "PostgreSQL", "SHOW ssl;", _success_result(), persist=True
    )
    assert payload["ok"] is True
    assert payload["evidence_persisted"] is True
    assert payload["evidence_id"] == "EV-PQ-001"
    assert captured["source_connector"] == "PREDEFINED_QUERY"
    assert captured["mime_type"] == "application/json"
    assert captured["control"] == "PGX-001"
    artifact = json.loads(captured["content"].decode())
    assert artifact["source_type"] == "PREDEFINED_QUERY"
    assert artifact["query_id"] == "PGX-001"
    assert artifact["status"] == "SUCCESS"


def test_scheduled_execution_uses_same_persistence_path(monkeypatch):
    calls: list[str] = []

    def _publish(**kwargs):
        calls.append(kwargs["control"]["control_id"])
        return {
            "evidence_id": "EV-SCHED",
            "object_key": "predefined-query/Net-Banking/local/PGX-001/t.json",
            "sha256": "deadbeef",
        }

    monkeypatch.setattr(publisher, "publish_predefined_query_evidence", _publish)
    monkeypatch.setattr(
        engine,
        "run_postgresql_query",
        lambda cid, user: cc.complete_connector_execution(
            _pgx_control(), user, "PostgreSQL", "SHOW ssl;", _success_result()
        ),
    )
    outcome = engine.run_predefined_query("PGX-001", "scheduler", scheduled=True)
    assert outcome["ok"] is True
    assert outcome["evidence_persisted"] is True
    assert calls == ["PGX-001"]


def test_object_key_hash_and_metadata_stored(monkeypatch):
    captured: dict = {}

    def _register_upload(**kwargs):
        captured.update(kwargs)
        return {"evidence_id": "EV-META", "sha256": "hash-meta", "filename": kwargs["filename"]}

    import modules.operations.engines.evidence_repository as ops_repo

    monkeypatch.setattr(ops_repo, "register_upload", _register_upload)
    control = _pgx_control()
    upload = publisher.publish_predefined_query_evidence(
        control=control,
        technology="PostgreSQL",
        query="SHOW ssl;",
        result=_success_result(),
        user="tester",
        execution_id="EXEC-1",
    )
    assert upload["object_key"].startswith("predefined-query/")
    assert upload["object_key"].endswith(".json")
    assert "PGX-001" in upload["object_key"]
    assert captured["metadata"]["source_type"] == "PREDEFINED_QUERY"
    assert captured["metadata"]["object_key"] == upload["object_key"]
    assert captured["source_url"] == f"object://{upload['object_key']}"
    assert len(captured["metadata"]["content_sha256"]) == 64


def test_failed_query_does_not_create_successful_evidence(monkeypatch):
    monkeypatch.setattr(
        publisher,
        "publish_predefined_query_evidence",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("must not publish")),
    )
    control = _pgx_control()
    result = ConnectorResult(success=False, output="", error_message="connection refused", duration_ms=5)
    payload = cc.complete_connector_execution(
        control, "tester", "PostgreSQL", "SHOW ssl;", result, persist=True
    )
    assert payload["ok"] is False
    assert payload.get("evidence_persisted") is not True
    assert not ops_repo.evidence_repository
