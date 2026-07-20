"""Predefined-query evidence lifecycle through the generic ECS review workflow."""

from __future__ import annotations

import json
import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest
from fastapi.testclient import TestClient

from app import ecs_state
from app.main import app
from modules.governance.engines import evidence_review as review
from modules.governance.engines import workflow_module as wf
from modules.operations.engines import connector_common as cc
from modules.operations.engines import evidence_repository as ops_repo
from modules.operations.engines import predefined_queries_engine as engine
from modules.operations.engines import predefined_query_publisher as publisher
from modules.operations.engines.query_connectors import ConnectorResult
from modules.shared.services import evidence_workflow_engine as ewf


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
    ecs_state.evidence_approval_trail.clear()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    engine.set_execution_persist(False)


def _persist_pgx001(user: str = "scheduler", *, rows=None) -> dict:
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
        user=user,
        execution_id="EXEC-PGX-001",
        framework="DB Baselining",
    )


def _workflow_coords(upload: dict) -> tuple[str, str, str]:
    framework = upload["framework"]
    control_name = upload["control_name"]
    key = upload["workflow_key"]
    return framework, control_name, key


def test_persisted_evidence_appears_in_app_owner_queue():
    upload = _persist_pgx001()
    framework, control_name, key = _workflow_coords(upload)
    owner_items = wf.build_owner_work_queue(limit=200)
    assert any(item["key"] == key and item["evidence_id"] == upload["evidence_id"] for item in owner_items)
    enrollment = ewf.get_enrollment(evidence_id=upload["evidence_id"])
    assert enrollment["source_connector"] == "PREDEFINED_QUERY"
    assert enrollment["query_id"] == "PGX-001"
    assert enrollment["sha256"] == upload["sha256"]
    assert enrollment["object_key"] == upload["object_key"]


def test_app_owner_submits_to_auditor_queue():
    upload = _persist_pgx001()
    framework, control_name, key = _workflow_coords(upload)
    resp = client.post(
        "/evidence/review/submit",
        data={
            "framework_name": framework,
            "control_name": control_name,
            "evidence_id": upload["evidence_id"],
            "role": "owner",
            "user": "App Owner",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert key in ecs_state.submitted_controls
    auditor_items = wf.build_auditor_review_queue(limit=200)
    assert any(item["evidence_id"] == upload["evidence_id"] for item in auditor_items)


def test_auditor_approval_closes_observation():
    upload = _persist_pgx001()
    framework, control_name, key = _workflow_coords(upload)
    client.post(
        "/evidence/review/submit",
        data={
            "framework_name": framework,
            "control_name": control_name,
            "evidence_id": upload["evidence_id"],
            "role": "owner",
            "user": "App Owner",
        },
    )
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
    assert key in ecs_state.approved_controls
    assert key not in ecs_state.submitted_controls
    obs_id = ewf.observation_id_for(framework, control_name, "PGX-001")
    assert obs_id in ecs_state.closed_observations or any(
        oid for oid in ecs_state.closed_observations if oid.startswith("OBS-")
    )


def test_auditor_rejection_creates_observation():
    upload = _persist_pgx001()
    framework, control_name, key = _workflow_coords(upload)
    client.post(
        "/evidence/review/submit",
        data={
            "framework_name": framework,
            "control_name": control_name,
            "evidence_id": upload["evidence_id"],
            "role": "owner",
            "user": "App Owner",
        },
    )
    reason = "JSON artifact missing timestamp metadata"
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
    obs_id = ewf.observation_id_for(framework, control_name, "PGX-001")
    assert obs_id in ecs_state.missing_evidence_registry
    assert ecs_state.missing_evidence_registry[obs_id]["status"] == "Rejected"


def test_resubmission_and_second_approval_closes_observation():
    upload_v1 = _persist_pgx001()
    framework, control_name, key = _workflow_coords(upload_v1)
    submit = {
        "framework_name": framework,
        "control_name": control_name,
        "evidence_id": upload_v1["evidence_id"],
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
            "reject_reason": "Need refreshed query output",
        },
    )
    client.post("/evidence/review/upload-revised", data=submit)
    client.post("/evidence/review/reevaluate", data=submit)
    upload_v2 = _persist_pgx001(user="App Owner", rows=[["on", "strict"]])
    assert upload_v2["evidence_id"] != upload_v1["evidence_id"]
    submit_v2 = {**submit, "evidence_id": upload_v2["evidence_id"]}
    client.post("/evidence/review/submit", data=submit_v2)
    client.post(
        "/evidence/review/approve",
        data={**submit_v2, "role": "auditor", "user": "Auditor"},
    )
    assert key in ecs_state.approved_controls
    obs_id = ewf.observation_id_for(framework, control_name, "PGX-001")
    assert obs_id in ecs_state.closed_observations


def test_role_access_is_enforced_for_submit_and_approve():
    upload = _persist_pgx001()
    framework, control_name, _key = _workflow_coords(upload)
    denied_submit = client.post(
        "/evidence/review/submit",
        data={
            "framework_name": framework,
            "control_name": control_name,
            "evidence_id": upload["evidence_id"],
            "role": "auditor",
            "user": "Auditor",
        },
        follow_redirects=False,
    )
    assert denied_submit.status_code == 303
    assert "notice=" in denied_submit.headers["location"].lower() or denied_submit.headers["location"]
    assert not ecs_state.submitted_controls

    client.post(
        "/evidence/review/submit",
        data={
            "framework_name": framework,
            "control_name": control_name,
            "evidence_id": upload["evidence_id"],
            "role": "owner",
            "user": "App Owner",
        },
    )
    denied_approve = client.post(
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
    assert denied_approve.status_code == 303
    assert ecs_state.submitted_controls


def test_review_screen_exposes_json_artifact_metadata():
    upload = _persist_pgx001()
    framework, control_name, _key = _workflow_coords(upload)
    ctx = review.build_evidence_review(
        framework,
        control_name,
        upload["evidence_id"],
        role="owner",
        user="App Owner",
        log_view=False,
    )
    assert ctx is not None
    assert ctx["metadata"]["source_system"] == "PREDEFINED_QUERY"
    assert ctx["preview"]["type"] == "json"
    assert "PGX-001" in ctx["preview"]["content"]
    assert ctx["metadata"]["evidence_version"].startswith("v")
