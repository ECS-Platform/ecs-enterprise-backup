"""Framework Control Master — repository, service, API, and dashboard tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from modules.frameworks.repositories.framework_control_repository import (
    FileFrameworkControlRepository,
)
from modules.frameworks.services.framework_control_master_service import (
    FrameworkControlMasterService,
)

client = TestClient(app, raise_server_exceptions=False)

EXPECTED_FRAMEWORK_IDS = {
    "itpp",
    "asst",
    "mbss",
    "pci_dss",
    "dpsc",
    "csite",
    "vapt",
    "os_baseline",
    "middleware_baseline",
    "database_baseline",
}


def test_catalog_lists_ten_frameworks():
    repo = FileFrameworkControlRepository()
    summaries = repo.list_framework_summaries()
    assert len(summaries) == 10
    assert {s["id"] for s in summaries} == EXPECTED_FRAMEWORK_IDS


def test_alias_resolution_pci_dss():
    repo = FileFrameworkControlRepository()
    doc = repo.get_framework("PCI DSS")
    assert doc is not None
    assert doc["framework"]["id"] == "pci_dss"
    assert doc["stats"]["control_count"] >= 6


def test_alias_resolution_csite():
    repo = FileFrameworkControlRepository()
    doc = repo.get_framework("C-SITE")
    assert doc is not None
    assert doc["framework"]["name"] == "C-SITE"


def test_control_has_procedures_and_evidence():
    repo = FileFrameworkControlRepository()
    detail = repo.get_control("itpp", "ITPP-C-01")
    assert detail is not None
    control = detail["control"]
    assert control.get("procedures")
    assert control.get("evidence_requirements")
    assert len(control["procedures"]) >= 1
    assert len(control["evidence_requirements"]) >= 2


def test_service_dashboard_payload():
    service = FrameworkControlMasterService()
    dash = service.build_dashboard(selected_framework_id="mbss")
    assert dash["stats"]["framework_count"] == 10
    assert dash["selected"]["framework"]["id"] == "mbss"
    assert dash["selected"]["stats"]["policy_count"] >= 1


def test_service_search_controls():
    service = FrameworkControlMasterService()
    result = service.search_controls(query="encryption", framework_id="pci_dss")
    assert result["ok"] is True
    assert result["count"] >= 1
    assert all(
        "encryption" in (c.get("title") or "").lower()
        or "encryption" in (c.get("description") or "").lower()
        for c in result["controls"]
    )


def test_api_list_frameworks():
    resp = client.get("/api/framework-control-master/frameworks")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["source_type"] == "file"
    assert len(body["frameworks"]) == 10


def test_api_framework_detail():
    resp = client.get("/api/framework-control-master/frameworks/asst")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["framework"]["code"] == "ASST"
    assert body["stats"]["control_count"] >= 6


def test_api_control_detail():
    resp = client.get("/api/framework-control-master/controls/dpsc/DPSC-C-01")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["control"]["id"] == "DPSC-C-01"


def test_api_search():
    resp = client.get("/api/framework-control-master/search?q=backup&framework_id=itpp")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["count"] >= 1


def test_dashboard_page_renders():
    resp = client.get(
        "/mvp/framework-control-master?role=compliance_head&user=ComplianceOfficer&framework_id=vapt"
    )
    assert resp.status_code == 200
    html = resp.text
    assert "Framework Control Master" in html
    assert "Vulnerability Assessment" in html
    assert "VAP-C-01" in html
