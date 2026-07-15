"""ECS governance workflow tests — SDLC navigation, registry tables, drill-downs, regression."""

from __future__ import annotations

import os
import re
from urllib.parse import urlparse

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, follow_redirects=False)
Q = "?role=cio&user=CIO"
RELEASE = "REL-2026-Q2-NB"

SDLC_WORKLIST_ROUTES = [
    ("/mvp/ai-sdlc/requirements", "My Requirement Activities"),
    ("/mvp/ai-sdlc/design", "My Design Activities"),
    ("/mvp/ai-sdlc/development", "My Development Activities"),
    ("/mvp/ai-sdlc/testing", "My Testing Activities"),
    ("/mvp/ai-sdlc/golive", "My Go-Live Activities"),
]

GOVERNANCE_ROUTES = [
    ("/mvp/ai-sdlc", "AI SDLC Governance"),
    ("/mvp/ai-registry", "Model"),
    ("/mvp/ai-governance", "AI Governance Posture"),
    ("/mvp/governance-quality", "Governance Quality"),
]

SIDEBAR_NAV_LABELS = ["Home", "Control Tower", "Phases", "Reports"]

DRILL_ENDPOINTS = [
    "/api/ai-sdlc/posture/drill?metric=inventory",
    "/api/ai-sdlc/registry/drill?metric=models",
    f"/api/ai-sdlc/sdlc/drill?metric=readiness&release={RELEASE}",
    f"/api/ai-sdlc/sdlc/drill?metric=gaps_drill&release={RELEASE}&stage=requirement",
]


# ── A. Functional Tests ──────────────────────────────────────────────────────


def test_nav_sdlc_gates_landing():
    resp = client.get(f"/mvp/sdlc-gates{Q}&release={RELEASE}")
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("/mvp/ai-sdlc?")


def test_nav_sdlc_stage_routes():
    for route, heading in SDLC_WORKLIST_ROUTES:
        resp = client.get(f"{route}{Q}")
        assert resp.status_code == 200, route
        assert heading in resp.text, route
        assert "ecs-gov-data-table" in resp.text


def test_nav_legacy_sdlc_redirects():
    resp = client.get(f"/mvp/sdlc-gates/requirement{Q}&release={RELEASE}")
    assert resp.status_code == 302
    loc = resp.headers.get("location", "")
    assert loc.startswith("/mvp/ai-sdlc/requirements?")


def test_nav_legacy_sdlc_slug_redirects():
    resp = client.get(f"/sdlc/requirements{Q}&release={RELEASE}")
    assert resp.status_code == 302
    assert "/mvp/ai-sdlc/requirements?" in resp.headers["location"]


def test_nav_no_self_loop_on_current_stage():
    resp = client.get(f"/mvp/ai-sdlc/requirements{Q}")
    assert resp.status_code == 200


def test_drill_down_apis():
    for url in DRILL_ENDPOINTS:
        resp = client.get(url)
        assert resp.status_code == 200, url
        data = resp.json()
        assert data.get("ok") is True, url
        assert data.get("payload") or data.get("data"), url


def test_workspace_tabs_present():
    resp = client.get(f"/mvp/ai-registry{Q}")
    assert resp.status_code == 200
    for tab in ("Overview", "Models", "Prompt Templates", "Audit Trail"):
        assert tab in resp.text


def test_tables_have_gov_enhancement_markup():
    resp = client.get(f"/mvp/ai-registry{Q}")
    html = resp.text
    assert "ecs-gov-data-table" in html
    assert "ecs-gov-table-scroll" in html


def test_registry_search_filter_toolbar():
    resp = client.get(f"/mvp/ai-registry{Q}")
    assert "Search records" in resp.text or "ecs-gov-search" in resp.text


# ── B. UI Tests ──────────────────────────────────────────────────────────────


def test_ui_applications_column_min_width():
    html = client.get(f"/mvp/ai-registry{Q}").text
    assert "min-width: 350px" in html
    assert "ecs-gov-col-applications" in html


def test_ui_text_wrapping_rules():
    html = client.get(f"/mvp/ai-registry{Q}").text
    assert re.search(r"word-break:\s*normal", html)
    assert re.search(r"overflow-wrap:\s*break-word", html)


def test_ui_no_character_stacking_css():
    html = client.get(f"/mvp/ai-registry{Q}").text
    section = html.split("ecs-gov-col-applications")[1][:1500]
    assert "overflow-wrap: anywhere" not in section


def test_ui_app_names_in_tag_cells():
    html = client.get(f"/mvp/ai-registry{Q}").text
    assert "ecs-gov-tag" in html
    assert "Net Banking AI Assistant" in html
    long_name = "Enterprise Retail Digital Banking AI Assistant Platform"
    assert long_name in html
    assert len(long_name) > 40


def test_ui_horizontal_scroll_containers():
    html = client.get(f"/mvp/ai-registry{Q}").text
    assert "overflow-x: auto" in html
    assert html.count("ecs-gov-table-scroll") >= 1


def test_ui_responsive_viewport_renders():
    for width in (1366, 1440, 1920):
        resp = client.get(f"/mvp/ai-registry{Q}", headers={"User-Agent": f"ECS/{width}"})
        assert resp.status_code == 200
        assert "ecs-gov-data-table" in resp.text


# ── C. Regression Tests ────────────────────────────────────────────────────


def test_regression_governance_pages():
    for route, label in GOVERNANCE_ROUTES:
        resp = client.get(f"{route}{Q}")
        assert resp.status_code == 200, route
        assert label in resp.text, route


def test_regression_sdlc_gates_redirects_to_home():
    resp = client.get(f"/mvp/sdlc-gates{Q}&release={RELEASE}")
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("/mvp/ai-sdlc?")


def test_regression_drill_modal_script_present():
    for route in ("/mvp/ai-registry", "/mvp/ai-governance"):
        html = client.get(f"{route}{Q}").text
        assert "openDrill" in html or "data-aisdlc-drill" in html


def test_regression_breadcrumb_trail():
    resp = client.get(f"/mvp/ai-sdlc/design{Q}")
    assert resp.status_code == 200
    assert "Design" in resp.text


def test_regression_api_data_endpoints():
    for path in ("/api/ai-sdlc/posture", "/api/ai-sdlc/sdlc", "/api/ai-sdlc/registry"):
        resp = client.get(path)
        assert resp.status_code == 200
        assert resp.json().get("ok") is True


# ── P1 — No duplicate top module navigation ─────────────────────────────────


def _assert_no_top_module_subnav(html: str) -> None:
    assert 'class="aisdlc-subnav"' not in html, "Top aisdlc-subnav must not render"
    assert 'aria-label="AI and SDLC Governance"' not in html, "Top module subnav aria-label must not render"


def _assert_sidebar_module_nav(html: str) -> None:
    assert 'id="nav-ai-sdlc"' in html, "Sidebar AI SDLC group must remain"
    ai_sdlc = html.split('id="nav-ai-sdlc"', 1)[1].split("</div>", 1)[0]
    for label in SIDEBAR_NAV_LABELS:
        assert label.replace("&", "&amp;") in ai_sdlc or label in ai_sdlc


def test_p1_001_ai_governance_posture_sidebar_only():
    html = client.get(f"/mvp/ai-governance{Q}").text
    _assert_no_top_module_subnav(html)
    _assert_sidebar_module_nav(html)


def test_p1_002_sdlc_home_sidebar_only():
    html = client.get(f"/mvp/ai-sdlc{Q}").text
    _assert_no_top_module_subnav(html)
    _assert_sidebar_module_nav(html)
    assert "My Applications" in html


def test_p1_003_model_registry_sidebar_only():
    html = client.get(f"/mvp/ai-registry{Q}").text
    _assert_no_top_module_subnav(html)
    _assert_sidebar_module_nav(html)
    for tab in ("Overview", "Models", "Prompt Templates", "Audit Trail"):
        assert tab in html


def test_p1_004_governance_quality_sidebar_only():
    html = client.get(f"/mvp/governance-quality{Q}").text
    _assert_no_top_module_subnav(html)
    _assert_sidebar_module_nav(html)


# ── Visual validation helpers ───────────────────────────────────────────────


def test_visual_no_blank_governance_pages():
    pages = [
        f"/mvp/ai-sdlc{Q}",
        f"/mvp/ai-sdlc/testing{Q}",
        f"/mvp/ai-registry{Q}",
        f"/mvp/ai-governance{Q}",
    ]
    for url in pages:
        resp = client.get(url)
        assert resp.status_code == 200, url
        assert len(resp.text) > 2000, url
        assert "<body" in resp.text


def test_visual_no_duplicate_subnav_active_loops():
    html = client.get(f"/mvp/ai-registry{Q}").text
    _assert_no_top_module_subnav(html)
    assert html.count('class="aisdlc-subnav"') == 0


def test_visual_stage_back_link_to_gates():
    html = client.get(f"/mvp/ai-sdlc/requirements{Q}").text
    assert "My Requirement Activities" in html
