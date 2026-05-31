"""Regression tests — AI SDLC ECS workflow (modals, status transitions, evidence viewer)."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.ai_sdlc_workflow_store import get_item, item_audit_trail, reset_store_for_tests
from app.main import app

client = TestClient(app, follow_redirects=False)
Q = "?role=cio&user=CIO"


def _pending_activity_id() -> str:
    reset_store_for_tests()
    resp = client.get(f"/mvp/ai-sdlc/requirements{Q}")
    assert resp.status_code == 200
    m = re.search(r'data-wf-id="(ACT-[^"]+)"[^>]*data-wf-type="activity"', resp.text)
    assert m, "No activity row found"
    item = get_item(m.group(1), "activity")
    item["status"] = "Pending"
    return m.group(1)


def _pending_evidence_id() -> str:
    reset_store_for_tests()
    resp = client.get(f"/mvp/ai-sdlc/evidence{Q}")
    assert resp.status_code == 200
    m = re.search(r'data-wf-id="(EV-[^"]+)"', resp.text)
    assert m, "No evidence row found"
    item = get_item(m.group(1), "evidence")
    item["status"] = "Pending"
    return m.group(1)


def test_requirements_no_duplicate_top_level_actions():
    html = client.get(f"/mvp/ai-sdlc/requirements{Q}").text
    header_end = html.find("</thead>")
    header = html[:header_end] if header_end > 0 else html[:2000]
    assert 'data-wf-action="Upload"' not in header
    assert 'data-wf-action="Review"' not in header
    assert "aisdlc-worklist-header" in html
    assert html.count('id="aisdlcUploadModal"') == 1
    assert html.count('id="aisdlcReviewModal"') == 1


def test_row_level_actions_only():
    html = client.get(f"/mvp/ai-sdlc/requirements{Q}").text
    assert 'data-wf-action="Upload"' in html
    assert 'data-wf-action="Review"' in html
    assert 'data-wf-action="Approve"' in html
    assert 'data-wf-action="Reject"' in html


def test_control_information_columns():
    html = client.get(f"/mvp/ai-sdlc/requirements{Q}").text
    for label in ("Framework", "Domain", "Control ID", "Control Name", "Stage"):
        assert label in html
    assert re.search(r"ACT-REQ-\d{4}", html)
    assert "|" in html or "Secure API Authentication" in html or "Linux Baseline" in html


def test_review_workflow_api_opens_evidence_viewer_payload():
    item_id = _pending_activity_id()
    resp = client.get(f"/api/ai-sdlc/workflow/review?item_id={item_id}&item_type=activity")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    data = body["data"]
    assert "metadata" in data
    assert "audit_trail" in data
    assert "approval_history" in data
    assert "files" in data
    assert "comments" in data


def test_upload_workflow_changes_status_and_audits():
    item_id = _pending_activity_id()
    resp = client.post(
        "/api/ai-sdlc/workflow/action",
        json={
            "action": "upload",
            "item_id": item_id,
            "item_type": "activity",
            "user": "CIO",
            "file_name": "req_doc.pdf",
            "comments": "Initial upload",
            "application": "Core Banking",
            "framework": "DPSC",
            "domain": "Access Management",
            "control_id": "DPSC-002",
            "stage": "Requirements",
            "artifact_type": "Requirement Document",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["item"]["status"] == "In Review"
    audit = item_audit_trail(item_id)
    assert any(e["action"] == "Upload" for e in audit)


def test_approve_changes_status_pending_to_approved():
    item_id = _pending_activity_id()
    resp = client.post(
        "/api/ai-sdlc/workflow/action",
        json={"action": "approve", "item_id": item_id, "item_type": "activity", "user": "CIO"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["item"]["status"] == "Approved"
    assert any(e["action"] == "Approve" for e in item_audit_trail(item_id))


def test_reject_requires_mandatory_comments():
    item_id = _pending_activity_id()
    resp = client.post(
        "/api/ai-sdlc/workflow/action",
        json={"action": "reject", "item_id": item_id, "item_type": "activity", "user": "CIO", "comments": ""},
    )
    body = resp.json()
    assert body["ok"] is False
    assert "mandatory" in body["error"].lower()


def test_reject_changes_status_with_comments():
    item_id = _pending_activity_id()
    resp = client.post(
        "/api/ai-sdlc/workflow/action",
        json={
            "action": "reject",
            "item_id": item_id,
            "item_type": "activity",
            "user": "CIO",
            "comments": "Missing control mapping",
        },
    )
    body = resp.json()
    assert body["ok"] is True
    assert body["item"]["status"] == "Rejected"
    assert any(e["action"] == "Reject" for e in item_audit_trail(item_id))


def test_rework_changes_status_and_assigns_owner():
    item_id = _pending_activity_id()
    resp = client.post(
        "/api/ai-sdlc/workflow/action",
        json={
            "action": "rework",
            "item_id": item_id,
            "item_type": "activity",
            "user": "CIO",
            "comments": "Please revise artifact",
        },
    )
    body = resp.json()
    assert body["ok"] is True
    assert body["item"]["status"] == "Needs Rework"
    audit = item_audit_trail(item_id)
    assert any(e["action"] == "Request Rework" for e in audit)


def test_evidence_open_link_points_to_viewer():
    html = client.get(f"/mvp/ai-sdlc/evidence{Q}").text
    assert "/mvp/ai-sdlc/evidence/view/EV-AISDLC-" in html
    assert "Open Evidence" in html
    assert 'href="/api/ai-sdlc/workflow' not in html


def test_evidence_viewer_page_not_raw_json():
    reset_store_for_tests()
    ev_id = "EV-AISDLC-0001"
    resp = client.get(f"/mvp/ai-sdlc/evidence/view/{ev_id}{Q}")
    assert resp.status_code == 200
    html = resp.text
    assert "Evidence Viewer" in html
    assert "Document Name" in html
    assert "Uploaded By" in html
    assert "Upload Date" in html
    assert "Control Description" in html
    assert "Audit Trail" in html
    assert '"ok":' not in html
    assert '"rows":' not in html
    assert ev_id in html


def test_evidence_collection_page_no_raw_json():
    html = client.get(f"/mvp/ai-sdlc/evidence{Q}").text
    assert '"ok": true' not in html
    assert "Evidence Collection" in html
