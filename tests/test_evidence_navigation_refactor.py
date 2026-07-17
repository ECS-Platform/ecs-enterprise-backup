"""Focused tests for evidence navigation refactor (Phase-1 CIO demo)."""

from __future__ import annotations

import os
import re

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from modules.shared.services.module_capabilities import get_module_capability

client = TestClient(app, follow_redirects=False)
Q = "role=owner&user=U"
CIO_Q = "role=cio&user=CIO"


def _get(path: str, q: str = Q):
    sep = "&" if "?" in path else "?"
    return client.get(f"{path}{sep}{q}")


OPS_NAV = [
    "Predefined Queries",
    "Evidence Dashboard",
    "Evidence Repository",
    "Evidence Reuse",
    "Reports",
]
ADMIN_NAV = [
    "Integrations",
    "Application Onboarding",
    "Scheduler",
    "Connector Test Workbench",
    "LLM Prompt Workbench",
    "Benchmark",
]
GOV_NAV = ["Audit Readiness", "Audit Prep"]
REMOVED_NAV = ["Evidence Packs", "Evidence Health", "Evidence Approval Analytics", "Evidence Reuse Story", "ECS Benchmark"]


def test_operations_nav_structure():
    t = _get("/dashboard").text
    ops = t.split('id="nav-ops"', 1)[1].split('id="nav-gov"', 1)[0]
    for label in OPS_NAV:
        assert label in ops, f"missing Operations item: {label}"
    for label in REMOVED_NAV:
        assert label not in ops, f"removed item still in Operations: {label}"
    positions = [ops.find(l) for l in OPS_NAV]
    assert all(p >= 0 for p in positions)
    assert positions == sorted(positions)


def test_administration_nav_structure():
    t = _get("/dashboard").text
    admin = t.split('id="nav-admin"', 1)[1].split('id="nav-ai-sdlc"', 1)[0]
    for label in ADMIN_NAV:
        assert label in admin, f"missing Administration item: {label}"


def test_governance_nav_trimmed():
    t = _get("/dashboard").text
    gov = t.split('id="nav-gov"', 1)[1].split('id="nav-admin"', 1)[0]
    for label in GOV_NAV:
        assert label in gov
    for label in ("Evidence Health", "Evidence Approval Analytics"):
        assert label not in gov


@pytest.mark.parametrize("path,needle", [
    ("/mvp/evidence-dashboard", "Evidence Dashboard"),
    ("/mvp/predefined-queries", "Predefined Queries"),
    ("/mvp/audit/repository", "Evidence Repository"),
    ("/mvp/evidence-story", "Evidence Reuse"),
    ("/mvp/reports", "Audit-Ready Export Center"),
    ("/mvp/evidence-health", "Evidence Health"),
    ("/mvp/evidence-approval", "Evidence Approval Analytics"),
    ("/mvp/audit/packs", "Evidence Packs"),
])
def test_key_routes_resolve(path, needle):
    r = _get(path)
    assert r.status_code == 200
    assert needle in r.text


def test_evidence_dashboard_tabs_render():
    r = _get("/mvp/evidence-dashboard")
    assert r.status_code == 200
    for tab in ("Overview", "Collection", "Health"):
        assert tab in r.text
    assert 'data-workspace-tab="overview"' in r.text or 'data-workspace-tab=' in r.text


def test_evidence_dashboard_cio_hides_approval_tab():
    r = _get("/mvp/evidence-dashboard", CIO_Q)
    assert r.status_code == 200
    assert 'data-workspace-tab="approval"' not in r.text


def test_evidence_dashboard_owner_has_approval_tab():
    r = _get("/mvp/evidence-dashboard")
    assert 'data-workspace-tab="approval"' in r.text


def test_reports_tabs_render():
    r = _get("/mvp/reports")
    for tab in ("Evidence", "Framework", "Application", "Audit", "Observation", "Evidence Packs"):
        assert tab in r.text


def test_reports_evidence_packs_tab_reachable():
    r = _get("/mvp/reports", f"{Q}&tab=evidence_packs")
    assert r.status_code == 200
    assert "Evidence Packs" in r.text
    assert 'name="pack_type"' in r.text


def test_evidence_dashboard_kpis_from_backend():
    view = get_module_capability("evidence_dashboard", "owner")
    assert view["kpis"]
    labels = {k["label"] for k in view["kpis"]}
    assert "Evidence Artifacts" in labels
    assert "Repository Keys" in labels
    for k in view["kpis"]:
        assert k["value"] is not None
        assert str(k["value"]) != ""


def test_reports_tab_rows_from_catalog():
    view = get_module_capability("reports", "owner")
    tabs = view.get("tab_rows", {})
    assert tabs.get("evidence")
    assert tabs.get("framework")
    assert tabs.get("audit")
    assert all(isinstance(rows, list) for rows in tabs.values())


def test_no_hardcoded_kpi_placeholders_in_dashboard_html():
    r = _get("/mvp/evidence-dashboard")
    assert "Loading filtered operations data" not in r.text
    nums = re.findall(r'ecs-exec-kpi-val">([^<]+)</span>', r.text)
    assert nums
    assert not any(n.strip() in ("—", "N/A", "???") for n in nums[:6])
