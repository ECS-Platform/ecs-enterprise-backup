"""Tests for AI SDLC Governance strategic redesign — workflow execution layer."""

from __future__ import annotations

import os
import re
from collections import Counter

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, follow_redirects=False)
Q = "?role=cio&user=CIO"

NEW_NAV_ROUTES = [
    ("/mvp/ai-sdlc", "ai_sdlc_home", "AI SDLC Governance"),
    ("/mvp/ai-sdlc/control-tower", "ai_sdlc_control_tower", "AI SDLC Control Tower"),
    ("/mvp/ai-sdlc/phases", "ai_sdlc_phases", "AI SDLC Phases"),
    ("/mvp/ai-sdlc/onboarding", "ai_sdlc_onboarding", "Application Onboarding"),
    ("/mvp/ai-sdlc/requirements", "ai_sdlc_requirements", "My Requirement Activities"),
    ("/mvp/ai-sdlc/design", "ai_sdlc_design", "My Design Activities"),
    ("/mvp/ai-sdlc/development", "ai_sdlc_development", "My Development Activities"),
    ("/mvp/ai-sdlc/testing", "ai_sdlc_testing", "My Testing Activities"),
    ("/mvp/ai-sdlc/golive", "ai_sdlc_golive", "My Go-Live Activities"),
    ("/mvp/ai-sdlc/evidence", "ai_sdlc_evidence", "Evidence Collection"),
    ("/mvp/ai-sdlc/findings", "ai_sdlc_findings", "Findings & Remediation"),
    ("/mvp/ai-sdlc/reports", "ai_sdlc_reports", "Reports"),
]

APPROVED_SIDEBAR_ITEMS = ["Home", "Control Tower", "Phases", "Reports"]

REMOVED_SIDEBAR_ITEMS = [
    "Application Onboarding", "Requirements", "Design", "Development", "Testing", "Go-Live",
    "Evidence Collection", "Findings & Remediation",
]


def test_nav_all_workflow_routes():
    for route, nav_mod, heading in NEW_NAV_ROUTES:
        resp = client.get(f"{route}{Q}")
        assert resp.status_code == 200, route
        assert heading in resp.text, route
        assert f'data-nav-module="{nav_mod}"' in resp.text, route


def test_sidebar_approved_consolidated_menu():
    html = client.get(f"/mvp/ai-sdlc{Q}").text
    ai_sdlc = html.split('id="nav-ai-sdlc"', 1)[1].split("</div>", 1)[0]
    for item in APPROVED_SIDEBAR_ITEMS:
        assert item in ai_sdlc, item
    for item in REMOVED_SIDEBAR_ITEMS:
        assert item not in ai_sdlc, item
    assert "AI Governance Posture" not in ai_sdlc
    assert "SDLC Compliance Gates" not in ai_sdlc
    assert 'class="aisdlc-subnav"' not in html


def test_sidebar_no_duplicate_ai_sdlc_links():
    html = client.get(f"/mvp/ai-sdlc{Q}").text
    ai_sdlc = html.split('id="nav-ai-sdlc"', 1)[1].split("</nav>", 1)[0]
    links = [
        re.sub(r"\s+", " ", m).strip()
        for m in re.findall(r'ecs-sidebar-btn[^>]*>([^<{]+)', ai_sdlc)
        if m.strip()
    ]
    dups = {k: v for k, v in Counter(links).items() if v > 1}
    assert not dups, f"duplicate AI SDLC nav labels: {dups}"


def test_llm_workbench_route_reachable():
    resp = client.get(f"/mvp/audit/llm-workbench{Q}")
    assert resp.status_code == 200
    assert "LLM Prompt Workbench" in resp.text
    assert "/mvp/audit/llm-workbench" in resp.text


def test_onboarding_screen_and_api_reachable():
    resp = client.get(f"/mvp/ai-sdlc/onboarding{Q}")
    assert resp.status_code == 200
    html = resp.text
    assert "Onboard Application" in html
    assert "ecsRunOnboarderBtn" in html
    assert "/api/ai-sdlc/onboarding/run" in html
    api = client.get(f"/api/ai-sdlc/onboarding/run{Q}")
    assert api.status_code == 200
    assert api.json().get("ok") is True


def test_legacy_sdlc_gates_redirects():
    resp = client.get(f"/mvp/sdlc-gates{Q}")
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("/mvp/ai-sdlc?")


def test_legacy_sdlc_stage_redirects():
    resp = client.get(f"/sdlc/requirements{Q}&release=REL-2026-Q2-NB")
    assert resp.status_code == 302
    assert "/mvp/ai-sdlc/requirements?" in resp.headers["location"]


def test_worklist_has_table_and_actions():
    html = client.get(f"/mvp/ai-sdlc/requirements{Q}").text
    assert "ecs-gov-data-table" in html
    assert "Application" in html
    assert "Framework" in html
    assert "Control" in html
    assert "Upload" in html or "Review" in html


def test_evidence_primary_workspace():
    html = client.get(f"/mvp/ai-sdlc/evidence{Q}").text
    assert "Evidence Collection" in html
    assert "ecs-gov-table-scroll" in html
    assert "Artifact Type" in html


def test_onboarding_execution_workspace():
    html = client.get(f"/mvp/ai-sdlc/onboarding{Q}").text
    assert "Onboard Application" in html
    assert "Applications Discovered" in html
    assert "Supported Frameworks" not in html
    assert "ITPP Domain Structure" not in html


def test_findings_remediation_sources():
    html = client.get(f"/mvp/ai-sdlc/findings{Q}").text
    assert "VAPT Finding" in html or "Audit Finding" in html
    assert "Severity" in html


def test_reports_only_reporting_hub():
    html = client.get(f"/mvp/ai-sdlc/reports{Q}").text
    assert "Application Compliance Report" in html
    assert "Supporting Capabilities" in html
    assert "Model &amp; Prompt Registry" in html or "Model & Prompt Registry" in html


def test_landing_actionable_work_items():
    html = client.get(f"/mvp/ai-sdlc{Q}").text
    assert "My Applications" in html
    assert "Evidence Awaiting Submission" in html
    assert "Overdue Activities" in html
    assert "aisdlc-kpi-grid" not in html or "governance_workspace" not in html


def test_workflow_api():
    resp = client.get("/api/ai-sdlc/workflow?stage=requirement")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert len(data["data"]["rows"]) >= 40


def test_supporting_registry_still_accessible():
    resp = client.get(f"/mvp/ai-registry{Q}")
    assert resp.status_code == 200
