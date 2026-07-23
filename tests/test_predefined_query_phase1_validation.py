"""Phase-1 predefined query lifecycle validation tests."""

from __future__ import annotations

import hashlib
import json
import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest
from fastapi.testclient import TestClient

from app import ecs_state
from app.main import app
from ecs_platform.storage import LocalObjectStore, reset_object_store, set_object_store
from modules.audit_intelligence.engines import evidence_repository as ai_repo
from modules.governance.engines.search_module import search_evidences
from modules.operations.engines import evidence_repository as ops_repo
from modules.operations.engines import predefined_queries_engine as engine
from modules.operations.engines import predefined_query_publisher as publisher
from modules.operations.engines.query_connectors import ConnectorResult
from modules.shared.services.common_evidence_presets import execute_preset_query
from modules.shared.services.evidence_authoritative_reader import collect_authoritative_evidence_rows


@pytest.fixture(autouse=True)
def _clean(tmp_path, monkeypatch):
    monkeypatch.setenv("ECS_EVIDENCE_SNAPSHOT_ENABLED", "true")
    monkeypatch.setenv("ECS_EVIDENCE_CUSTODY_MODE", "SNAPSHOT")
    set_object_store(LocalObjectStore(tmp_path / "objects"))
    ecs_state.predefined_query_fingerprint_index.clear()
    ecs_state.predefined_query_content_index.clear()
    ecs_state.uploaded_evidence_enrollments.clear()
    ops_repo.evidence_repository.clear()
    ai_repo.reset_repository()
    engine.set_execution_persist(True)
    yield
    reset_object_store()
    ops_repo.evidence_repository.clear()
    ai_repo.reset_repository()


def _pgx_control():
    engine.load_predefined_queries()
    return engine.get_control_by_id("PGX-001")


def _success_result() -> ConnectorResult:
    return ConnectorResult(
        success=True,
        output="ssl | \n-----\n on",
        duration_ms=12,
        metadata={"rows_returned": 1, "columns": ["ssl"], "parsed_rows": [["on"]]},
    )


def test_publish_creates_json_artifact_with_sha256_and_object_key():
    upload = publisher.publish_predefined_query_evidence(
        control=_pgx_control(),
        technology="PostgreSQL",
        query="SHOW ssl;",
        result=_success_result(),
        user="tester",
        execution_id="EXEC-1",
    )
    assert upload["object_key"].startswith("predefined-query/")
    assert len(upload["sha256"]) == 64
    artifact = upload["artifact"]
    assert artifact["source_type"] == "predefined_query"
    assert artifact["status"] == "SUCCESS"
    meta = upload.get("metadata") or {}
    assert meta.get("common_control_slugs")
    assert int(meta.get("fcm_reference_count") or 0) > 0


def test_duplicate_sha256_detected_on_identical_rerun():
    first = publisher.publish_predefined_query_evidence(
        control=_pgx_control(),
        technology="PostgreSQL",
        query="SHOW ssl;",
        result=_success_result(),
        user="tester",
    )
    second = publisher.publish_predefined_query_evidence(
        control=_pgx_control(),
        technology="PostgreSQL",
        query="SHOW ssl;",
        result=_success_result(),
        user="tester",
    )
    assert first["status"] != "DUPLICATE"
    assert second["status"] == "DUPLICATE"
    assert len(ops_repo.evidence_repository) == 1


def test_authoritative_reader_and_search_see_predefined_query_evidence():
    publisher.publish_predefined_query_evidence(
        control=_pgx_control(),
        technology="PostgreSQL",
        query="SHOW ssl;",
        result=_success_result(),
        user="tester",
    )
    rows = [
        r for r in collect_authoritative_evidence_rows()
        if (r.get("metadata") or {}).get("query_id") == "PGX-001"
    ]
    assert rows
    assert rows[0]["source_connector"] == "predefined_query"
    hits = search_evidences(q="PGX-001")
    assert any(h.get("evidence_id") for h in hits)


def test_chatbot_preset_can_find_predefined_query_evidence():
    publisher.publish_predefined_query_evidence(
        control=_pgx_control(),
        technology="PostgreSQL",
        query="SHOW ssl;",
        result=_success_result(),
        user="tester",
    )
    result = execute_preset_query("latest_5_evidences", role="owner", limit=5)
    assert result.get("rows") or result.get("citations")


def test_predefined_query_api_exposure():
    client = TestClient(app)
    listing = client.get("/api/predefined-queries")
    assert listing.status_code == 200
    body = listing.json()
    assert body["count"] >= 70
    assert any(c["control_id"] == "PGX-001" for c in body["controls"])

    detail = client.get("/api/predefined-queries/PGX-001")
    assert detail.status_code == 200
    assert detail.json()["ok"] is True

    mappings = client.get("/api/predefined-queries/PGX-001/mappings")
    assert mappings.status_code == 200
    mbody = mappings.json()
    assert mbody["common_controls"]
    assert mbody["fcm_references"]


def test_common_control_reuse_linkage_for_query_id():
    from modules.operations.engines.common_controls_catalog import common_controls_for_query_id

    linked = common_controls_for_query_id("PGX-001")
    assert any(c.slug == "encryption-in-transit" for c in linked)


def test_changed_artifact_content_creates_new_audit_version():
    control = _pgx_control()
    publisher.publish_predefined_query_evidence(
        control=control,
        technology="PostgreSQL",
        query="SHOW ssl;",
        result=_success_result(),
        user="tester",
    )
    key = ai_repo.make_evidence_key("Net Banking", "PGX-001")
    v1 = ai_repo.get_latest(key)
    assert v1 is not None
    alt = _success_result()
    alt.metadata["parsed_rows"] = [["off"]]
    alt.output = "ssl | \n-----\n off"
    publisher.publish_predefined_query_evidence(
        control=control,
        technology="PostgreSQL",
        query="SHOW ssl;",
        result=alt,
        user="tester",
    )
    versions = ai_repo.get_versions(key)
    assert len(versions) >= 2
    assert versions[-1].content_hash != versions[0].content_hash
