"""Regression tests — AI SDLC Governance corrections (reports, controls, evidence, KB)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, follow_redirects=False)
Q = "?role=cio&user=CIO"

REPORT_IDS = [
    ("app-compliance", "Application Compliance Report", "Implementation Status"),
    ("fw-compliance", "Framework Compliance Report", "Compliance %"),
    ("readiness", "Readiness Report", "Readiness Score"),
    ("control-impl", "Control Implementation Report", "Go-Live"),
    ("evidence-status", "Evidence Collection Status Report", "Submitted"),
    ("findings", "Findings & Remediation Report", "Severity"),
]


def test_reports_hub_generate_buttons_link_to_pages():
    html = client.get(f"/mvp/ai-sdlc/reports{Q}").text
    assert "Generate Report" in html
    assert 'disabled>Generate Report' not in html
    for rid, name, _ in REPORT_IDS:
        assert name.replace("&", "&amp;") in html or name in html
        assert f"/mvp/ai-sdlc/reports/{rid}" in html


def test_all_report_pages_open():
    for rid, title, col_hint in REPORT_IDS:
        resp = client.get(f"/mvp/ai-sdlc/reports/{rid}{Q}")
        assert resp.status_code == 200, rid
        assert title.replace("&", "&amp;") in resp.text or title in resp.text, rid
        assert "ecs-gov-data-table" in resp.text, rid
        assert col_hint in resp.text, rid


def test_controls_tab_ecs_columns():
    html = client.get(f"/mvp/ai-governance{Q}").text
    for col in ("Framework", "Control ID", "Control Name", "Compliance %", "Violations", "Applications Affected", "Control Owner"):
        assert col in html
    assert "View Violations" in html
    assert "Policy Compliance Controls" not in html


def test_violation_drilldown_api():
    resp = client.get(f"/api/ai-sdlc/posture/drill?metric=controls&item_id=DPSC-002")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    payload = body["payload"]
    assert payload["type"] == "control_violations"
    if payload.get("rows"):
        row = payload["rows"][0]
        for key in ("framework", "control_id", "control_name", "violation_description", "affected_applications", "evidence_references", "remediation_status"):
            assert key in row, key


def test_evidence_tab_trend_and_coverage():
    html = client.get(f"/mvp/ai-governance{Q}").text
    assert "Evidence Collection Trend" in html
    assert "Submitted" in html
    assert "Approved" in html
    assert "Rejected" in html
    assert "Pending" in html
    assert "Framework Evidence Coverage" in html
    assert "Token &amp; Usage Evidence" not in html and "Token & Usage Evidence" not in html


def test_knowledge_base_ecs_assets():
    html = client.get(f"/mvp/ai-governance{Q}").text
    for section in (
        "Framework Library", "Control Library", "Requirement Templates",
        "Design Templates", "Development Checklists", "Testing Templates",
        "Go-Live Templates", "Evidence Templates",
    ):
        assert section in html, section
    assert "Guardrail Library" not in html
    assert "PII Detection" not in html


def test_posture_api_has_ecs_fields():
    resp = client.get("/api/ai-sdlc/posture")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "control_compliance" in data
    assert "evidence_collection_analytics" in data
    kb = data["knowledge_base"]
    assert "sections" in kb
    assert "framework_library" in kb["sections"]
