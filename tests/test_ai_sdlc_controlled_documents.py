"""Validation tests for controlled SDLC document generation (CRD/CDD/CDVD/CTD/CGLD)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from modules.ai_sdlc.engines.ai_sdlc_controlled_documents import (
    DOC_TYPES,
    STAGE_KEYS,
    document_counts,
    generate_controlled_document,
)
from modules.ai_sdlc.engines.ai_sdlc_workflow_engine import _worklist_items
from modules.ai_sdlc.engines.ai_sdlc_workflow_store import reset_store_for_tests


client = TestClient(app)

STAGE_PAGES = {
    "requirement": "/mvp/ai-sdlc/requirements",
    "design": "/mvp/ai-sdlc/design",
    "development": "/mvp/ai-sdlc/development",
    "testing": "/mvp/ai-sdlc/testing",
    "go-live": "/mvp/ai-sdlc/golive",
}

DOC_TYPE_BY_STAGE = {k: v["code"] for k, v in DOC_TYPES.items()}


def test_dpsc_auth_control_generates_all_document_types():
    app_name = "Net Banking"
    fw = "DPSC"
    domain = "Authentication"
    cid = "DPSC-AUTH-01"
    docs = []
    for stage in STAGE_KEYS:
        doc = generate_controlled_document(stage, app_name, fw, domain, cid)
        assert doc["ok"] is True
        assert doc["document_type"] == DOC_TYPE_BY_STAGE[stage]
        assert doc["application"] == app_name
        assert doc["framework"] == fw
        assert doc["domain"] == domain
        assert doc["control_id"] == cid
        assert len(doc.get("sections", [])) >= 8
        docs.append(doc["document_id"])
    assert len(set(docs)) == 5


def test_document_content_varies_by_control():
    base = generate_controlled_document("requirement", "Net Banking", "DPSC", "Authentication", "DPSC-AUTH-01")
    other = generate_controlled_document("requirement", "Net Banking", "DPSC", "Encryption", "DPSC-ENC-01")
    assert base["document_id"] != other["document_id"]
    assert base["sections"][0]["body"] != other["sections"][0]["body"]


def test_worklist_rows_have_document_metadata():
    reset_store_for_tests()
    for stage in STAGE_KEYS:
        rows = _worklist_items(stage, 48)
        assert len(rows) == 48
        for row in rows[:5]:
            assert row.get("document_id")
            assert row.get("document_type") == DOC_TYPE_BY_STAGE[stage]
            assert row.get("document_link_label") == DOC_TYPES[stage]["link_label"]
            assert row.get("observation_id")
            assert row.get("evidence_id")


def test_stage_pages_have_document_columns():
    reset_store_for_tests()
    stage_columns = {
        "requirement": ("Controlled Requirement Document", "Open Requirement Document"),
        "design": ("Controlled Design Document", "Open Design Document"),
        "development": ("Controlled Development Document", "Open Development Document"),
        "testing": ("Controlled Testing Document", "Open Testing Document"),
        "go-live": ("Controlled Go-Live Document", "Open Go-Live Document"),
    }
    for stage, path in STAGE_PAGES.items():
        r = client.get(path, params={"role": "cio", "user": "CIO"})
        assert r.status_code == 200, path
        html = r.text
        col_label, link_label = stage_columns[stage]
        assert col_label in html
        assert link_label in html
        assert 'data-aisdlc-drill="document"' in html
        assert "View Evidence" in html
        assert "View Observation" in html
        assert "View Control" in html
        assert "View Controlled" not in html
        assert "aisdlcControlledDocModal" in html


def test_home_applications_table_renders_frameworks():
    r = client.get("/mvp/ai-sdlc", params={"role": "cio", "user": "CIO"})
    assert r.status_code == 200
    html = r.text
    assert "aisdlc-home-apps-table" in html
    assert "VAPT" in html
    assert "DPSC" in html
    assert "aisdlc-fw-list" in html
    assert "ecs-no-gov-enhance" in html


def test_document_counts_match_worklist():
    reset_store_for_tests()
    counts = document_counts()
    assert counts["CRD"] == 48
    assert counts["CDD"] == 48
    assert counts["CDVD"] == 48
    assert counts["CTD"] == 48
    assert counts["CGLD"] == 48
    assert counts["total"] == 240


def test_controlled_document_api():
    reset_store_for_tests()
    r = client.get(
        "/api/ai-sdlc/controlled-document",
        params={
            "stage": "requirement",
            "application": "Net Banking",
            "framework": "DPSC",
            "domain": "Authentication",
            "control_id": "DPSC-AUTH-01",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["data"]["document_type"] == "CRD"
    assert "html" in data["data"]
    assert "Acceptance Criteria" in data["data"]["html"]


def test_drill_apis():
    reset_store_for_tests()
    r1 = client.get(
        "/api/ai-sdlc/control-drill",
        params={
            "application": "Net Banking",
            "framework": "DPSC",
            "domain": "Authentication",
            "control_id": "DPSC-AUTH-01",
        },
    )
    assert r1.status_code == 200
    assert r1.json()["data"]["control_id"] == "DPSC-AUTH-01"

    r2 = client.get(
        "/api/ai-sdlc/observation-drill",
        params={"observation_id": "OBS-DPS-DPSCAUTH-001", "application": "Net Banking"},
    )
    assert r2.status_code == 200
    assert r2.json()["data"]["observation_id"]


def test_evidence_viewer_for_controlled_evidence():
    reset_store_for_tests()
    doc = generate_controlled_document("requirement", "Net Banking", "DPSC", "Authentication", "DPSC-AUTH-01")
    eid = doc["evidence_id"]
    r = client.get(f"/mvp/ai-sdlc/evidence/view/{eid}", params={"role": "cio", "user": "CIO"})
    assert r.status_code == 200
    assert eid in r.text


def test_counts_api():
    reset_store_for_tests()
    r = client.get("/api/ai-sdlc/controlled-document/counts")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["total"] == 240
