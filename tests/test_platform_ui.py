"""EP-UI-001 — platform-wide persona branding, tabs, and layout validation."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from modules.shared.services.persona_display import resolve_persona_context

client = TestClient(app, raise_server_exceptions=False)

PERSONA_ROUTES = [
    ("/dashboard/cio?role=cio&user=CIO", "cio"),
    ("/dashboard/vertical-head?role=vertical_head&user=VerticalHead", "vertical_head"),
    ("/dashboard?role=owner&user=AppOwner", "owner"),
    ("/dashboard?role=auditor&user=Auditor", "auditor"),
    ("/dashboard/compliance-head?role=compliance_head&user=ComplianceOfficer", "compliance_head"),
    ("/mvp/demo-overview?role=cio&user=cio@bank.com", "cio"),
    ("/mvp/governance-analytics?role=cio&user=cio@bank.com", "cio"),
    ("/mvp/ai-sdlc?role=cio&user=cio@bank.com", "cio"),
    ("/mvp/trends?role=cio&user=cio@bank.com", "cio"),
    ("/mvp/reports?role=cio&user=cio@bank.com", "cio"),
]

def test_executive_overview_tabs():
    resp = client.get("/mvp/demo-overview?role=cio&user=cio@bank.com")
    assert resp.status_code == 200
    html = resp.text
    assert "ecs-persona-tabs" in html
    assert 'id="tab-overview"' in html
    assert 'id="tab-analytics"' in html
    assert "R. Khanna" in html


def test_enterprise_grc_persona():
    resp = client.get("/mvp/governance-analytics?role=cio&user=cio@bank.com")
    assert resp.status_code == 200
    html = resp.text
    assert "ECS Platform" in html
    assert "R. Khanna" in html
    assert "Chief Information Officer" in html
    assert "ECS CIO" not in html


def test_ai_sdlc_tabs_and_table():
    resp = client.get("/mvp/ai-sdlc?role=cio&user=cio@bank.com")
    assert resp.status_code == 200
    html = resp.text
    assert "ecs-persona-tabs" in html
    assert 'id="tab-applications"' in html
    assert "ecs-risk-table" in html
    assert "R. Khanna" in html

FORBIDDEN_PATTERNS = [
    "ECS CIO",
    "CIO CIO",
    "App Owner App Owner",
    "ECS\nECS",
    "ecs-sidebar-tagline\">ECS</p>",
]


def test_persona_context_names_differ():
    for role in ("cio", "owner", "auditor", "vertical_head", "compliance_head"):
        p = resolve_persona_context(role, "test@bank.com")
        assert p["display_name"] != p["role_title"], role
        assert p["sidebar_brand"] == "ECS Platform"
        assert p["sidebar_role_line"].startswith("Role:")


def test_persona_tabs_by_role():
    cio = resolve_persona_context("cio")
    assert [t["label"] for t in cio["tabs"]] == ["Overview", "Approvals", "Escalations", "Analytics"]
    owner = resolve_persona_context("owner")
    assert "Remediation" in [t["label"] for t in owner["tabs"]]


def test_no_duplicate_branding_on_persona_pages():
    for url, role in PERSONA_ROUTES:
        resp = client.get(url)
        assert resp.status_code == 200, url
        html = resp.text
        assert "ECS Platform" in html, url
        assert "ecs-persona-tabs" in html or "ecs-sidebar-profile" in html, url
        for bad in FORBIDDEN_PATTERNS:
            assert bad not in html, f"{url} contains forbidden pattern: {bad}"


def test_cio_dashboard_section_order_and_tabs():
    resp = client.get("/dashboard/cio?role=cio&user=CIO")
    assert resp.status_code == 200
    html = resp.text
    assert "Executive KPI Cards" in html
    assert "Executive Escalations &amp; Approvals" in html or "Executive Escalations & Approvals" in html
    assert "Framework Compliance Overview" in html
    assert "Top Risk Applications" in html
    assert "Top Risk Controls" in html
    assert 'id="tab-overview"' in html
    assert 'id="tab-analytics"' in html
    assert "ecs-risk-table" in html
    assert "R. Khanna" in html
    assert "Chief Information Officer" in html


def test_risk_table_columns():
    resp = client.get("/dashboard/cio?role=cio&user=CIO")
    html = resp.text
    for col in ("Control Name", "Application", "Framework", "Risk", "Age", "Status"):
        assert col in html


def test_copilot_dock_controls():
    resp = client.get("/dashboard/cio?role=cio&user=CIO")
    html = resp.text
    assert "ecs-chat-dock-btn" in html
    assert 'data-dock="bottom"' in html
    assert 'data-dock="right"' in html
    assert "localStorage" in html
