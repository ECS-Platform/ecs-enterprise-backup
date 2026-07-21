"""Unified evidence lifecycle for predefined-query and scheduler/connector sources."""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest
from fastapi.testclient import TestClient

from app import ecs_state
from app.main import app
from modules.governance.engines import workflow_module as wf
from modules.operations.engines import evidence_repository as ops_repo
from modules.operations.engines import predefined_queries_engine as engine
from modules.operations.engines import predefined_query_publisher as publisher
from modules.operations.engines import scheduler_module as sm
from modules.operations.engines.query_connectors import ConnectorResult
from modules.shared.services import evidence_workflow_engine as ewf
from modules.shared.services.common_evidence_presets import execute_preset_query


client = TestClient(app, follow_redirects=False)


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.setenv("ECS_COMMON_CONTROLS_COLLECTION_ENABLED", "false")
    monkeypatch.setenv("ECS_PREDEFINED_QUERY_SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("ECS_MOCK_EVIDENCE_COLLECTION_ENABLED", "true")
    ecs_state.submitted_controls.clear()
    ecs_state.approved_controls.clear()
    ecs_state.rejected_controls.clear()
    ecs_state.submitted_meta.clear()
    ecs_state.closed_observations.clear()
    ecs_state.uploaded_evidence_enrollments.clear()
    ecs_state.predefined_query_fingerprint_index.clear()
    ecs_state.predefined_query_content_index.clear()
    ecs_state.missing_evidence_registry.clear()
    ecs_state.evidence_approval_trail.clear()
    sm._execution_history.clear()
    sm._run_progress.clear()
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
    ecs_state.evidence_approval_trail.clear()
    sm._execution_history.clear()
    sm._run_progress.clear()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    engine.set_execution_persist(False)


def _persist_pq(*, rows=None) -> dict:
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


def _persist_connector(*, application: str = "Net Banking", control: str = "SP-001") -> dict:
    record = ops_repo.register_upload(
        filename=f"sharepoint_{control}.json",
        content=b'{"source":"sharepoint","status":"ok"}',
        uploaded_by="scheduler",
        framework="PCI DSS",
        application=application,
        control=control,
        source_connector="sharepoint_graph",
        metadata={
            "source_type": "connector",
            "scheduler_run_id": "COLL-TEST-001",
            "object_key": "sharepoint/mock.json",
        },
    )
    ewf.enroll_collected_evidence(record, source_type="connector")
    return record


def _seed_observation(*, framework: str, control_name: str, control_id: str) -> str:
    obs_id = ewf.observation_id_for(framework, control_name, control_id)
    ecs_state.missing_evidence_registry[obs_id] = {
        "observation_id": obs_id,
        "framework": framework,
        "control_id": control_id,
        "control_name": control_name,
        "control": control_name,
        "application": "Net Banking",
        "status": "Open",
        "missing_evidence": "Awaiting evidence",
        "history": [],
    }
    return obs_id


def _submit(framework: str, control_name: str, evidence_id: str):
    return client.post(
        "/evidence/review/submit",
        data={
            "framework_name": framework,
            "control_name": control_name,
            "evidence_id": evidence_id,
            "role": "owner",
            "user": "App Owner",
        },
        follow_redirects=False,
    )


def test_scheduler_mock_persists_to_same_repository():
    result = sm.run_scheduler_collection(applications=["Net Banking"], frameworks=["PCI DSS"])
    assert ops_repo.evidence_repository
    rec = ops_repo.evidence_repository[-1]
    assert (rec.get("metadata") or {}).get("scheduler_run_id") == result["run_id"]
    assert ewf.get_enrollment(evidence_id=rec["evidence_id"])


def test_predefined_query_persists_to_same_repository():
    upload = _persist_pq()
    assert any(r.get("evidence_id") == upload["evidence_id"] for r in ops_repo.evidence_repository)
    assert ewf.get_enrollment(evidence_id=upload["evidence_id"])


def test_both_sources_appear_in_latest_five_chatbot():
    pq = _persist_pq()
    conn = _persist_connector()
    result = execute_preset_query("latest_5_evidences", role="owner", user="Owner")
    ids = {r.get("evidence_id") for r in result["rows"]}
    assert pq["evidence_id"] in ids
    assert conn["evidence_id"] in ids
    sources = {r.get("source_type") or r.get("source_connector") for r in result["rows"]}
    assert "predefined_query" in sources or "PREDEFINED_QUERY" in sources
    assert "connector" in sources or "sharepoint_graph" in sources


def test_app_owner_can_view_and_submit_both_sources():
    pq = _persist_pq()
    conn = _persist_connector(control="SP-002")
    owner_items = wf.build_owner_work_queue(limit=200)
    owner_ids = {item.get("evidence_id") for item in owner_items}
    assert pq["evidence_id"] in owner_ids
    assert conn["evidence_id"] in owner_ids

    _submit(pq["framework"], pq["control_name"], pq["evidence_id"])
    _submit("PCI DSS", "SP-002", conn["evidence_id"])
    auditor_items = wf.build_auditor_review_queue(limit=200)
    auditor_ids = {item.get("evidence_id") for item in auditor_items}
    assert pq["evidence_id"] in auditor_ids
    assert conn["evidence_id"] in auditor_ids


def test_unauthorized_app_owner_cannot_view_out_of_scope():
    _persist_connector(application="Net Banking", control="SP-RBAC")
    result = execute_preset_query(
        "latest_evidence_by_application",
        role="functional_head",
        user="FunctionalHead",
        application="Net Banking",
    )
    assert result.get("ok") is False
    assert "access" in result.get("answer", "").lower()


def test_auditor_rejection_returns_evidence_to_owner():
    upload = _persist_pq()
    framework, control_name, key = upload["framework"], upload["control_name"], upload["workflow_key"]
    _submit(framework, control_name, upload["evidence_id"])
    reason = "Missing execution timestamp"
    resp = client.post(
        "/evidence/review/reject",
        data={
            "framework_name": framework,
            "control_name": control_name,
            "evidence_id": upload["evidence_id"],
            "role": "auditor",
            "user": "Auditor",
            "reject_reason": reason,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert key in ecs_state.rejected_controls
    owner_items = wf.build_owner_work_queue(limit=200)
    assert any(item["key"] == key and item["workflow_code"] == "rejected" for item in owner_items)


def test_approval_closes_only_linked_observation():
    upload = _persist_connector(control="SP-CLOSE")
    framework = "PCI DSS"
    control_name = "SP-CLOSE"
    key = upload["metadata"]["workflow_key"]
    obs_id = _seed_observation(framework=framework, control_name=control_name, control_id="SP-CLOSE")
    other_id = "OBS-OTHER-999"
    ecs_state.missing_evidence_registry[other_id] = {
        "observation_id": other_id,
        "framework": framework,
        "control_id": "OTHER",
        "status": "Open",
        "history": [],
    }
    enrollment = ewf.get_enrollment(evidence_id=upload["evidence_id"])
    enrollment["observation_id"] = obs_id
    ecs_state.uploaded_evidence_enrollments[upload["evidence_id"]]["observation_id"] = obs_id

    _submit(framework, control_name, upload["evidence_id"])
    resp = client.post(
        "/evidence/review/approve",
        data={
            "framework_name": framework,
            "control_name": control_name,
            "evidence_id": upload["evidence_id"],
            "role": "auditor",
            "user": "Auditor",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert obs_id in ecs_state.closed_observations
    assert other_id not in ecs_state.closed_observations


def test_rejection_does_not_close_observation():
    upload = _persist_pq()
    framework, control_name = upload["framework"], upload["control_name"]
    obs_id = _seed_observation(framework=framework, control_name=control_name, control_id="PGX-001")
    _submit(framework, control_name, upload["evidence_id"])
    client.post(
        "/evidence/review/reject",
        data={
            "framework_name": framework,
            "control_name": control_name,
            "evidence_id": upload["evidence_id"],
            "role": "auditor",
            "user": "Auditor",
            "reject_reason": "Incomplete",
        },
    )
    assert obs_id not in ecs_state.closed_observations
    assert ecs_state.missing_evidence_registry[obs_id]["status"] == "Rejected"


def test_resubmission_returns_to_auditor():
    upload = _persist_pq()
    framework, control_name = upload["framework"], upload["control_name"]
    submit = {
        "framework_name": framework,
        "control_name": control_name,
        "evidence_id": upload["evidence_id"],
        "role": "owner",
        "user": "App Owner",
    }
    client.post("/evidence/review/submit", data=submit)
    client.post(
        "/evidence/review/reject",
        data={
            **submit,
            "role": "auditor",
            "user": "Auditor",
            "reject_reason": "Fix output",
        },
    )
    client.post("/evidence/review/upload-revised", data=submit)
    client.post("/evidence/review/reevaluate", data=submit)
    resp = client.post("/evidence/review/submit", data=submit, follow_redirects=False)
    assert resp.status_code == 303
    auditor_items = wf.build_auditor_review_queue(limit=200)
    assert any(item["evidence_id"] == upload["evidence_id"] for item in auditor_items)


def test_audit_trail_retained_on_approval():
    upload = _persist_pq()
    framework, control_name, key = upload["framework"], upload["control_name"], upload["workflow_key"]
    _submit(framework, control_name, upload["evidence_id"])
    client.post(
        "/evidence/review/approve",
        data={
            "framework_name": framework,
            "control_name": control_name,
            "evidence_id": upload["evidence_id"],
            "role": "auditor",
            "user": "Auditor",
        },
    )
    assert key in ecs_state.evidence_approval_trail
    assert len(ecs_state.evidence_approval_trail[key]) >= 2


def test_duplicate_scheduler_rerun_does_not_create_duplicate_workflow_item():
    first = sm.run_scheduler_collection(applications=["Net Banking"], frameworks=["PCI DSS"])
    enroll_count = len(ecs_state.uploaded_evidence_enrollments)
    second = sm.run_scheduler_collection(applications=["Net Banking"], frameworks=["PCI DSS"])
    assert second["summary"]["duplicates_skipped"] >= 1
    assert second["summary"]["new_evidence"] == 0
    assert len(ecs_state.uploaded_evidence_enrollments) <= enroll_count + 1


def test_app_owner_cannot_approve_own_evidence():
    upload = _persist_pq()
    framework, control_name = upload["framework"], upload["control_name"]
    _submit(framework, control_name, upload["evidence_id"])
    resp = client.post(
        "/evidence/review/approve",
        data={
            "framework_name": framework,
            "control_name": control_name,
            "evidence_id": upload["evidence_id"],
            "role": "owner",
            "user": "App Owner",
        },
        follow_redirects=False,
    )
    assert resp.status_code in {303, 403}
    assert upload["workflow_key"] not in ecs_state.approved_controls
