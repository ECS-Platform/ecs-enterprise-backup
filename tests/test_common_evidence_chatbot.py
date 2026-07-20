"""Focused tests for hybrid common evidence querying in the ECS chatbot."""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest
from fastapi.testclient import TestClient

from app import ecs_state
from app.main import app, chatbot_answer
from modules.governance.engines import workflow_module as wf
from modules.operations.engines import evidence_repository as ops_repo
from modules.operations.engines import predefined_queries_engine as engine
from modules.operations.engines import predefined_query_publisher as publisher
from modules.operations.engines.query_connectors import ConnectorResult
from modules.shared.services.common_evidence_queries import (
    NO_EVIDENCE_MESSAGE,
    try_deterministic_evidence_query,
    try_rag_evidence_query,
)


client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean():
    ecs_state.submitted_controls.clear()
    ecs_state.approved_controls.clear()
    ecs_state.rejected_controls.clear()
    ecs_state.submitted_meta.clear()
    ecs_state.closed_observations.clear()
    ecs_state.uploaded_evidence_enrollments.clear()
    ecs_state.predefined_query_fingerprint_index.clear()
    ecs_state.predefined_query_content_index.clear()
    ecs_state.missing_evidence_registry.clear()
    ecs_state.missing_evidence_seed_loaded = False
    ecs_state.evidence_approval_trail.clear()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    engine.set_execution_persist(False)
    yield
    ecs_state.submitted_controls.clear()
    ecs_state.approved_controls.clear()
    ecs_state.rejected_controls.clear()
    ecs_state.submitted_meta.clear()
    ecs_state.closed_observations.clear()
    ecs_state.uploaded_evidence_enrollments.clear()
    ecs_state.predefined_query_fingerprint_index.clear()
    ecs_state.predefined_query_content_index.clear()
    ecs_state.missing_evidence_seed_loaded = False
    ecs_state.evidence_approval_trail.clear()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    engine.set_execution_persist(False)


def _persist_pgx001(*, rows=None) -> dict:
    engine.load_predefined_queries()
    control = engine.get_control_by_id("PGX-001")
    rows = rows if rows is not None else [["on"]]
    result = ConnectorResult(
        success=True,
        output="ssl | \n-----\n on",
        duration_ms=8,
        metadata={"rows_returned": len(rows), "columns": ["ssl"], "parsed_rows": rows},
    )
    return publisher.publish_predefined_query_evidence(
        control=control,
        technology="PostgreSQL",
        query="SHOW ssl;",
        result=result,
        user="scheduler",
        execution_id="EXEC-PGX-001",
        framework="DB Baselining",
    )


def _submit_and_approve(upload: dict) -> None:
    client.post(
        "/evidence/review/submit",
        data={
            "framework_name": upload["framework"],
            "control_name": upload["control_name"],
            "evidence_id": upload["evidence_id"],
            "role": "owner",
            "user": "App Owner",
        },
    )
    client.post(
        "/evidence/review/approve",
        data={
            "framework_name": upload["framework"],
            "control_name": upload["control_name"],
            "evidence_id": upload["evidence_id"],
            "role": "auditor",
            "user": "Auditor",
        },
    )


def test_latest_evidence_references_persisted_pgx001():
    upload = _persist_pgx001()
    result = try_deterministic_evidence_query(
        "Show latest evidence for control PGX-001 in Net Banking",
        role="owner",
        user="App Owner",
    )
    assert result is not None
    assert result["answer_source"] == "DETERMINISTIC"
    assert upload["evidence_id"] in result["answer"]
    assert any(c["evidence_id"] == upload["evidence_id"] for c in result["citations"])


def test_control_implementation_after_approval():
    upload = _persist_pgx001()
    _submit_and_approve(upload)
    result = try_deterministic_evidence_query(
        "Is control PGX-001 approved with current evidence?",
        role="owner",
        user="App Owner",
    )
    assert result is not None
    assert "Approved" in result["answer"]
    assert upload["evidence_id"] in result["answer"]


def test_rejected_evidence_returns_reason():
    upload = _persist_pgx001()
    reason = "JSON artifact missing timestamp metadata"
    client.post(
        "/evidence/review/submit",
        data={
            "framework_name": upload["framework"],
            "control_name": upload["control_name"],
            "evidence_id": upload["evidence_id"],
            "role": "owner",
            "user": "App Owner",
        },
    )
    client.post(
        "/evidence/review/reject",
        data={
            "framework_name": upload["framework"],
            "control_name": upload["control_name"],
            "evidence_id": upload["evidence_id"],
            "role": "auditor",
            "user": "Auditor",
            "reject_reason": reason,
        },
    )
    result = try_deterministic_evidence_query(
        "Show rejected evidence and rejection reason for PGX-001",
        role="owner",
        user="App Owner",
    )
    assert result is not None
    assert reason in result["answer"]
    assert upload["evidence_id"] in result["answer"] or any(
        c.get("rejection_reason") == reason for c in result["citations"]
    )


def test_missing_evidence_returns_no_supporting_evidence():
    result = try_deterministic_evidence_query(
        "Show missing evidence for control ZZZ-999 in Net Banking",
        role="owner",
        user="App Owner",
    )
    assert result is not None
    assert result["answer"] == NO_EVIDENCE_MESSAGE


def test_duplicate_attempt_not_counted_as_new_evidence(monkeypatch):
    monkeypatch.setattr(publisher, "_utc_now", lambda: "2026-07-20T10:00:00+00:00")
    first = _persist_pgx001()
    second = _persist_pgx001()
    assert second.get("status") == "DUPLICATE"
    assert second["evidence_id"] == first["evidence_id"]
    latest = try_deterministic_evidence_query(
        "Show latest evidence for control PGX-001",
        role="owner",
        user="App Owner",
    )
    assert latest is not None
    assert latest["answer"].count(first["evidence_id"]) == 1
    dup = try_deterministic_evidence_query(
        "Show duplicate evidence attempts for PGX-001",
        role="owner",
        user="App Owner",
    )
    assert dup is not None
    assert first["evidence_id"] in dup["answer"]


def test_app_owner_cannot_query_other_application():
    _persist_pgx001()
    result = try_deterministic_evidence_query(
        "Show latest evidence for Treasury",
        role="owner",
        user="App Owner",
    )
    assert result is not None
    assert "do not have access" in result["answer"].lower()


def test_auditor_can_query_permitted_review_evidence():
    upload = _persist_pgx001()
    client.post(
        "/evidence/review/submit",
        data={
            "framework_name": upload["framework"],
            "control_name": upload["control_name"],
            "evidence_id": upload["evidence_id"],
            "role": "owner",
            "user": "App Owner",
        },
    )
    result = try_deterministic_evidence_query(
        "Show evidence pending Auditor review for PGX-001",
        role="auditor",
        user="Auditor",
    )
    assert result is not None
    assert upload["evidence_id"] in result["answer"]
    queue = wf.build_auditor_review_queue(limit=50)
    assert any(item["evidence_id"] == upload["evidence_id"] for item in queue)


def test_deterministic_queries_work_with_llm_disabled(monkeypatch):
    upload = _persist_pgx001()

    class _DisabledProvider:
        configured = staticmethod(lambda: False)
        model = ""
        embedding_model = ""

    monkeypatch.setattr("ecs_platform.llm_engine.provider.get_provider", lambda: _DisabledProvider())
    answer = chatbot_answer(
        "Show latest evidence for control PGX-001",
        role="owner",
        user="App Owner",
    )
    assert upload["evidence_id"] in answer
    assert "[Source: DETERMINISTIC]" in answer


def test_free_text_rag_answer_contains_citations(monkeypatch):
    upload = _persist_pgx001()

    def _fake_retrieve(question, scope_filter, hints, top_k):
        return [upload["evidence_id"]], "repository", 1

    def _fake_enrich(uids):
        return [
            {
                "evidence_uid": upload["evidence_id"],
                "source_system": "PREDEFINED_QUERY",
                "object_type": "json",
                "application": "Net Banking",
                "collected_timestamp": upload.get("uploaded_at", ""),
                "frameworks": ["DB Baselining"],
                "framework_refs": [],
                "review_status": "Pending App Owner Review",
                "controls": ["PGX-001"],
                "url": upload.get("object_key", ""),
                "title": upload.get("filename", ""),
            }
        ]

    monkeypatch.setattr("ecs_platform.rag._retrieve", _fake_retrieve)
    monkeypatch.setattr("ecs_platform.rag._enrich", _fake_enrich)

    class _DisabledProvider:
        configured = staticmethod(lambda: False)
        model = ""
        embedding_model = ""

    monkeypatch.setattr("ecs_platform.llm_engine.provider.get_provider", lambda: _DisabledProvider())

    result = try_rag_evidence_query(
        "Describe PostgreSQL SSL evidence collected for Net Banking",
        role="owner",
        user="App Owner",
    )
    assert result is not None
    assert result["answer_source"] == "RAG"
    assert result["citations"]
    cite = result["citations"][0]
    assert cite["evidence_id"] == upload["evidence_id"]
    assert cite["control_id"] == "PGX-001"
    assert cite["application"] == "Net Banking"
    assert cite["source_connector"] == "PREDEFINED_QUERY"


def test_no_retrieved_context_produces_no_fabricated_answer(monkeypatch):
    monkeypatch.setattr("ecs_platform.rag._retrieve", lambda *args, **kwargs: ([], "repository", 0))
    monkeypatch.setattr("ecs_platform.rag._enrich", lambda uids: [])
    monkeypatch.setattr("ecs_platform.rag._governance_facts", lambda question: [])

    class _DisabledProvider:
        configured = staticmethod(lambda: False)
        model = ""
        embedding_model = ""

    monkeypatch.setattr("ecs_platform.llm_engine.provider.get_provider", lambda: _DisabledProvider())

    result = try_rag_evidence_query(
        "Explain undocumented control implementation for imaginary system",
        role="owner",
        user="App Owner",
    )
    assert result is not None
    assert result["answer"] == NO_EVIDENCE_MESSAGE
    assert result["citations"] == []
