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
    assert ">Overview" in t                       # renamed dashboard child
    # The Dashboard *group label* remains, but the child link is no longer "Dashboard".
    assert 'class="ecs-nav-group-label">Dashboard<' in t


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
    assert labels == ["Dashboard", "Operations", "Audit Intelligence",
                      "Governance", "Administration", "AI SDLC Governance"]


def test_nav_no_duplicate_link_labels():
    import re
    from collections import Counter
    t = _get("/dashboard").text
    links = [re.sub(r"\s+", " ", m).strip()
             for m in re.findall(r'ecs-sidebar-btn[^>]*>([^<{]+)', t)
             if m.strip() and not m.strip().startswith(".")]
    dups = {k: v for k, v in Counter(links).items() if v > 1}
    assert not dups, f"duplicate nav labels: {dups}"


def test_nav_users_and_roles_present_and_reachable():
    t = _get("/dashboard").text
    assert "Users &amp; Roles" in t or "Users & Roles" in t
    assert _get("/mvp/admin/users-roles").status_code == 200


# --------------------------------------------------------------------------- #
# Routes unbroken (old URLs still open)
# --------------------------------------------------------------------------- #
def test_benchmark_route_unbroken_and_highlighted():
    r = _get("/mvp/ecs-benchmark")
    assert r.status_code == 200
    assert "/mvp/ecs-benchmark" in r.text and "is-active" in r.text


def test_operations_group_target_items():
    t = _get("/dashboard").text
    for item in ["Predefined Queries", "Evidence Explorer", "Evidence Reuse Story",
                 "Integrations", "Connector Test Workbench", "ECS Benchmark"]:
        assert item in t, f"Operations missing {item}"
