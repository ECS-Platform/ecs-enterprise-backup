"""Platform certification tests — wraps scripts/platform_certification.py checks."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)
ROOT = Path(__file__).resolve().parent.parent


def _load_cert_module():
    path = ROOT / "scripts" / "platform_certification.py"
    spec = importlib.util.spec_from_file_location("platform_certification", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_onboarding_no_duplicate_tab_buttons():
    resp = client.get("/mvp/onboarding?role=cio&user=cio@bank.com")
    assert resp.status_code == 200
    assert 'data-ecs-tab-switch="applications"' not in resp.text
    assert "ecs-workspace-tab" in resp.text


def test_governance_analytics_single_kpi_strip():
    resp = client.get("/mvp/governance-analytics?role=cio&user=cio@bank.com")
    assert resp.status_code == 200
    assert resp.text.count("ecs-exec-kpi-lbl") >= 3
    assert resp.text.count('class="ecs-ws-metric-row') == 0


def test_extended_roles_login_and_persona():
    for role, dest_fragment in (
        ("security_officer", "SecurityOfficer"),
        ("operations_owner", "OpsOwner"),
        ("ai_governance_owner", "AIGovOwner"),
        ("ai_sdlc_owner", "SDLCOwner"),
        ("framework_owner", "FrameworkOwner"),
    ):
        resp = client.post("/login", data={"role": role}, follow_redirects=False)
        assert resp.status_code == 303, role
        assert dest_fragment in resp.headers.get("location", ""), role


def test_platform_kpi_drills_return_rows():
    cert = _load_cert_module()
    issues = cert.validate_drilldowns()
    p1 = [i for i in issues if i.get("severity") == "P1"]
    assert not p1, p1


def test_platform_certification_passes():
    cert = _load_cert_module()
    page_issues, _, _ = cert.scan_pages()  # full role×route matrix
    kpi_issues = cert.validate_kpis()
    p1 = [i for i in page_issues + kpi_issues if i.get("severity") == "P1"]
    assert not p1, p1[:5]
