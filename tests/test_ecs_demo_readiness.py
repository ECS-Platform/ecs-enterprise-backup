"""ECS demo readiness — Executive, Frameworks, Operations, Governance, Enterprise GRC."""

from __future__ import annotations

import re
from urllib.parse import quote

from fastapi.testclient import TestClient

from app import ecs_state
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

ROLES = [
    ("cio", "cio@bank.com"),
    ("compliance_head", "compliance.head@bank.com"),
    ("auditor", "audit.lead@bank.com"),
    ("owner", "owner.app1@bank.com"),
]

PLACEHOLDER_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"\bLorem Ipsum\b",
        r"\bMock Data\b",
        r"\bSample Data\b",
        r"\bDummy\b",
        r"\bPlaceholder content\b",
        r"\bTODO\b",
        r"\bcoming soon\b",
    )
]

EXECUTIVE_ROUTES = [
    "/mvp/demo-overview",
    "/mvp/enterprise",
    "/mvp/pan-india",
    "/mvp/reports",
    "/mvp/trends",
    "/dashboard",
    "/dashboard/cio",
    "/dashboard/vertical-head",
    "/dashboard/compliance-head",
    "/dashboard/functional-head",
]

OPERATIONS_ROUTES = [
    "/mvp/scheduler",
    "/mvp/ai-ops-assistant",
    "/mvp/upload",
    "/mvp/integrations",
    "/mvp/onboarding",
    "/mvp/integrations-hub",
]

GOVERNANCE_ROUTES = [
    "/mvp/audit-prep",
    "/mvp/evidence-health",
    "/mvp/reuse",
    "/mvp/lifecycle",
    "/mvp/completeness",
    "/mvp/comparison",
    "/mvp/search",
    "/mvp/evidence-approval",
    "/mvp/workflow/close-gap",
    "/mvp/workflow/assign-owner",
    "/mvp/workflow/upload-missing",
    "/mvp/workflow/mock-audit",
]

GRC_ROUTES = [
    "/mvp/risk-register",
    "/mvp/exceptions",
    "/mvp/exception-governance",
    "/mvp/cmdb",
    "/mvp/regulatory",
    "/mvp/heatmaps",
    "/mvp/correlation",
    "/mvp/governance-analytics",
]

FRAMEWORK_ROUTES = [
    "/mvp/framework-loader",
    "/mvp/framework-admin",
]

DEMO_FLOW = (
    EXECUTIVE_ROUTES[:5]
    + FRAMEWORK_ROUTES
    + OPERATIONS_ROUTES
    + GOVERNANCE_ROUTES[:8]
    + GRC_ROUTES
)


def _url(route: str, role: str = "cio", user: str = "cio@bank.com") -> str:
    sep = "&" if "?" in route else "?"
    return f"{route}{sep}role={role}&user={user}"


def _assert_page_ok(route: str, role: str = "cio", user: str = "cio@bank.com") -> str:
    url = _url(route, role, user)
    resp = client.get(url)
    assert resp.status_code == 200, f"{url} returned {resp.status_code}"
    text = resp.text
    assert "Internal Server Error" not in text
    assert "UndefinedError" not in text
    assert not text.strip().startswith("{"), f"{url} returned raw JSON"
    for pat in PLACEHOLDER_PATTERNS:
        match = pat.search(text)
        assert match is None, f"{url} contains placeholder: {match.group(0)}"
    return text


def test_executive_routes_load():
    for route in EXECUTIVE_ROUTES:
        _assert_page_ok(route)


def test_operations_routes_load():
    for route in OPERATIONS_ROUTES:
        _assert_page_ok(route)


def test_governance_routes_load():
    for route in GOVERNANCE_ROUTES:
        _assert_page_ok(route)


def test_grc_routes_load():
    for route in GRC_ROUTES:
        _assert_page_ok(route)


def test_framework_admin_routes_load():
    for route in FRAMEWORK_ROUTES:
        _assert_page_ok(route)


def test_all_framework_dashboards_load():
    for framework in ecs_state.frameworks:
        fw = quote(framework, safe="")
        _assert_page_ok(f"/framework/{fw}")


def test_demo_overview_sections():
    resp = client.get(_url("/mvp/demo-overview"))
    assert resp.status_code == 200
    for needle in (
        "Banking Applications Registry",
        "Risk Heatmap",
        "Framework Catalogue",
        "VAPT Findings Dashboard",
        "CIO Executive Snapshot",
    ):
        assert needle in resp.text, needle


def test_demo_overview_apis():
    overview = client.get("/api/demo/overview").json()
    assert overview.get("ok") is True
    data = overview.get("data", {})
    for key in (
        "banking_applications",
        "frameworks",
        "risk_heatmap",
        "vapt",
        "cio_executive",
        "audit_history",
    ):
        assert data.get(key), f"missing demo overview section: {key}"


def test_audit_prep_drill_apis():
    for metric in (
        "draft",
        "submitted",
        "controls_pending_review",
        "evidence_pending_upload",
        "blockers",
    ):
        resp = client.get(f"/api/audit-prep/kpi-drill?metric={metric}")
        assert resp.status_code == 200, metric
        body = resp.json()
        assert body.get("ok") is True, body
        assert body.get("drill"), f"empty drill for {metric}"


def test_grc_drill_apis():
    risk = client.get("/api/grc-demo/risk/drill?metric=open_risks&role=cio")
    assert risk.status_code == 200
    assert risk.json().get("ok") is True
    gov = client.get("/api/grc-demo/governance/drill?metric=controls&role=cio")
    assert gov.status_code == 200
    assert gov.json().get("ok") is True


def test_framework_loader_drill_apis():
    resp = client.get("/api/framework-loader/control-drill?theme=encryption_rest")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("ok") is True
    assert body.get("linked_frameworks")
    assert body.get("linked_evidence")


def test_nav_module_present_on_framework_and_dashboard():
    for route in ("/framework/PCI%20DSS", "/dashboard"):
        resp = client.get(_url(route, "owner", "owner.app1@bank.com"))
        assert resp.status_code == 200, route
        assert "AI SDLC Governance" in resp.text


def test_demo_flow_cio():
    for route in DEMO_FLOW:
        _assert_page_ok(route)


def test_all_roles_executive_overview():
    for role, user in ROLES:
        _assert_page_ok("/mvp/demo-overview", role, user)


def test_framework_pages_have_tables_or_kpis():
    fw = quote("PCI DSS", safe="")
    text = _assert_page_ok(f"/framework/{fw}")
    assert "ecs-exec-kpi" in text or "table" in text.lower() or "ecs-kpi" in text


def test_scheduler_has_queue_data():
    text = _assert_page_ok("/mvp/scheduler")
    assert "Scheduler" in text
    assert "ecs-table" in text or "table" in text.lower()


def test_governance_audit_prep_has_kpis():
    text = _assert_page_ok("/mvp/audit-prep")
    assert "Audit Prep" in text or "audit" in text.lower()
    assert "ecs-kpi" in text or "kpi" in text.lower()
