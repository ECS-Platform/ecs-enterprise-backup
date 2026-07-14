"""UI smoke tests for the navigation cleanup + de-duplicated owner summary.

Verifies (offline, DEMO_MODE):
  * key pages render (200);
  * the repeated "Application Owner Summary" role-metrics strip appears only on the
    main dashboard, not on other pages;
  * the left nav has no "Dashboard -> Dashboard" redundancy (child is "Overview")
    and no standalone "ECS Benchmark -> Benchmark Simulation" one-child nesting;
  * "ECS Benchmark" is a single item under Operations and its route still works;
  * target nav items exist and existing routes are unbroken.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, follow_redirects=False)
Q = "role=owner&user=U"

#: The role-metrics strip's unique card class (from role_metrics_strip.html).
_STRIP_MARKER = "border-primary border-opacity-25"


def _get(path: str):
    sep = "&" if "?" in path else "?"
    return client.get(f"{path}{sep}{Q}")


# --------------------------------------------------------------------------- #
# Key pages render
# --------------------------------------------------------------------------- #
_KEY_PAGES = [
    "/dashboard",
    "/mvp/predefined-queries",
    "/mvp/integrations",
    "/mvp/evidence-health",
    "/mvp/evidence-approval",
    "/mvp/audit-prep",
    "/mvp/admin/application-management",
    "/mvp/admin/evidence",
    "/mvp/search",                 # "Evidence" (metadata search)
    "/mvp/ecs-benchmark",
    "/mvp/audit/llm-workbench",
    "/mvp/connectors/test-workbench",
    "/mvp/audit/repository",
    "/mvp/audit/packs",
    "/mvp/scheduler",
]


@pytest.mark.parametrize("path", _KEY_PAGES)
def test_key_pages_render(path):
    r = _get(path)
    assert r.status_code == 200, f"{path} -> {r.status_code}"
    assert "text/html" in r.headers.get("content-type", "")


# --------------------------------------------------------------------------- #
# Repeated "Application Owner Summary" removed from non-dashboard pages
# --------------------------------------------------------------------------- #
_NON_DASHBOARD_PAGES = [
    "/mvp/evidence-health",
    "/mvp/evidence-approval",
    "/mvp/audit-prep",
    "/mvp/admin/application-management",
    "/mvp/search",
    "/mvp/integrations",
    "/mvp/predefined-queries",
    "/mvp/completeness",
    "/mvp/reuse",
    "/mvp/onboarding",
]


@pytest.mark.parametrize("path", _NON_DASHBOARD_PAGES)
def test_no_repeated_owner_summary_on_non_dashboard_pages(path):
    r = _get(path)
    assert r.status_code == 200
    assert "Application Owner Summary" not in r.text, f"repeated strip title on {path}"
    assert _STRIP_MARKER not in r.text, f"repeated role-metrics strip card on {path}"


def test_owner_summary_strip_suppressed_for_all_roles_on_subpages():
    # The suppression is role-agnostic: no role's summary strip should appear on a
    # sub-page (e.g. CIO Summary must not show on Integrations).
    for role, title in [("cio", "CIO Summary"),
                        ("compliance_head", "Compliance Overview"),
                        ("owner", "Application Owner Summary")]:
        r = client.get(f"/mvp/integrations?role={role}&user=U")
        assert r.status_code == 200
        assert title not in r.text
        assert _STRIP_MARKER not in r.text


def test_dashboard_keeps_owner_summary_context():
    # The main dashboard is the single home for the owner summary: it renders the
    # "Application Owner Dashboard" experience and its role_metrics keeps show_strip.
    r = _get("/dashboard")
    assert r.status_code == 200
    assert "Application Owner Dashboard" in r.text
    from modules.shared.services.enterprise_context import enterprise_widgets_context
    dash_ctx = enterprise_widgets_context("owner", user="U")            # no page_module
    sub_ctx = enterprise_widgets_context("owner", page_module="evidence_health", user="U")
    assert dash_ctx["role_metrics"].get("show_strip") is True
    assert sub_ctx["role_metrics"].get("show_strip") is False


# --------------------------------------------------------------------------- #
# Navigation structure
# --------------------------------------------------------------------------- #
def test_nav_has_overview_not_duplicate_dashboard():
    t = _get("/dashboard").text
    assert ">Overview" in t
    # Dashboard is a direct link (no expandable group / chevron).
    assert 'data-bs-target="#nav-dash"' not in t
    assert 'ecs-sidebar-btn-dashboard' in t


def test_nav_ecs_benchmark_single_item_under_operations():
    t = _get("/dashboard").text
    assert "ECS Benchmark" in t                    # single Operations item
    assert "Benchmark Simulation" not in t         # old one-child label gone
    # It must not be a standalone nav group anymore.
    assert 'data-bs-target="#nav-ecs-benchmark"' not in t


def test_nav_top_level_groups():
    import re
    t = _get("/dashboard").text
    labels = [re.sub(r"\s+", " ", m).strip()
              for m in re.findall(r'ecs-nav-group-label">([^<]+)</span>', t)]
    # 5 target sections + AI SDLC Governance (kept: has 4 active children).
    assert labels == ["Operations", "Governance", "Administration", "AI SDLC Governance"]


def test_nav_no_duplicate_link_labels():
    import re
    from collections import Counter
    t = _get("/dashboard").text
    links = [re.sub(r"\s+", " ", m).strip()
             for m in re.findall(r'ecs-sidebar-btn[^>]*>([^<{]+)', t)
             if m.strip() and not m.strip().startswith(".")]
    dups = {k: v for k, v in Counter(links).items() if v > 1}
    assert not dups, f"duplicate nav labels: {dups}"


def test_nav_users_and_roles_route_still_reachable():
    # Removed from sidebar; URL remains live.
    assert _get("/mvp/admin/users-roles").status_code == 200


def test_nav_evidence_items_under_operations():
    t = _get("/dashboard").text
    assert "Evidence Management" not in t
    assert 'id="nav-evidence-mgmt"' not in t
    ops = t.split('id="nav-ops"', 1)[1].split('id="nav-gov"', 1)[0]
    labels = [
        "Predefined Queries",
        "Evidence Repository",
        "Evidence Packs",
        "Evidence Reuse Story",
        "Integrations",
        "Application Onboarding",
        "ECS Benchmark",
    ]
    positions = [ops.find(item) for item in labels]
    assert all(p >= 0 for p in positions), f"missing Operations items in: {ops[:500]}"
    assert positions == sorted(positions), f"Operations order wrong: {labels}"
    assert "/mvp/audit/repository" in ops
    assert "/mvp/audit/packs" in ops
    assert "Evidence Runs" not in t


def test_nav_governance_and_administration_groups_expanded():
    t = _get("/dashboard").text
    assert 'id="nav-gov" class="collapse show"' in t
    assert 'id="nav-admin" class="collapse show"' in t
    gov = t.split('id="nav-gov"', 1)[1].split('id="nav-admin"', 1)[0]
    admin = t.split('id="nav-admin"', 1)[1].split('id="nav-ai-sdlc"', 1)[0]
    for item in ["Audit Readiness", "Audit Prep", "Evidence Health", "Evidence Approval Analytics"]:
        assert item in gov
    for item in ["LLM Prompt Workbench", "Connector Test Workbench", "Scheduler"]:
        assert item in admin


# --------------------------------------------------------------------------- #
# Routes unbroken (old URLs still open)
# --------------------------------------------------------------------------- #
def test_benchmark_route_unbroken_and_highlighted():
    r = _get("/mvp/ecs-benchmark")
    assert r.status_code == 200
    assert "/mvp/ecs-benchmark" in r.text and "is-active" in r.text


def test_operations_group_target_items():
    t = _get("/dashboard").text
    ops = t.split('id="nav-ops"', 1)[1].split('id="nav-gov"', 1)[0]
    for item in ["Predefined Queries", "Evidence Repository", "Evidence Packs",
                 "Evidence Reuse Story", "Integrations", "Application Onboarding", "ECS Benchmark"]:
        assert item in ops, f"Operations missing {item}"
    assert "Connector Test Workbench" not in ops, "Connector Test Workbench belongs under Administration"
    assert "Evidence Explorer" not in ops.split("Integrations")[0], "Evidence Explorer should be under Integrations tabs"


def test_operations_has_application_onboarding():
    t = _get("/dashboard").text
    assert "Application Onboarding" in t
    assert "/mvp/onboarding" in t
    assert "Application Onboarding" not in t.split("Administration")[1].split("AI SDLC")[0] if "Administration" in t else True
    r = _get("/mvp/onboarding")
    assert r.status_code == 200
    assert "ecs-nav-groups" in r.text and "ecs-workspace-main" in r.text
    assert "ecsOnboardStartBtn" in r.text
    assert "Start Application Onboarding" in r.text
    assert "ecsOnboarderRunBtn" in r.text
    assert "Run Application Onboarder" in r.text
    assert "customer_criticality" in r.text or "Customer Criticality" in r.text


def test_onboarding_run_onboarder_api():
    r = client.post("/api/onboarding/simulate", json={"action": "run_onboarder", "role": "owner"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    assert "dashboard" in body
    assert body["dashboard"]["summary"]["remaining"] >= 0


def test_onboarding_simulate_progress_steps():
    r = client.post("/api/onboarding/simulate", json={
        "application_name": "Demo App X",
        "owner": "U",
        "pci_dss_in_scope": "No",
        "role": "owner",
    })
    assert r.status_code == 200
    body = r.json()
    assert "progress_steps" in body
    assert len(body["progress_steps"]) == 8
    assert body["progress_steps"][1]["label"] == "Loading CMDB data"
    fw_names = [f["framework"] for f in body["framework_results"]]
    assert "PCI DSS" not in fw_names


def test_application_management_aggregator_still_reachable():
    r = _get("/mvp/admin/application-management")
    assert r.status_code == 200
    assert "Application Inventory" in r.text
    assert "App Comparison" in r.text


def test_onboarding_start_uses_existing_simulate_api():
    r = _get("/mvp/onboarding")
    assert r.status_code == 200
    html = r.text
    assert "ecsOnboardStartBtn" in html
    assert "/api/onboarding/simulate" in html
    assert "ecsOnboardIntakeForm" in html
    assert "ecs-nav-groups" in html


def test_integrations_has_evidence_explorer_tab():
    t = _get("/mvp/integrations").text
    assert "Evidence Explorer" in t
    assert 'data-workspace-tab="evidence_explorer"' in t
    assert "/mvp/evidence-explorer" in t
