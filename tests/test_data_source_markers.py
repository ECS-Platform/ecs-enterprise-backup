"""Data-source markers — classification, propagation, and scoped screen rendering."""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")

from fastapi.testclient import TestClient

from app.main import app
from modules.executive_overview.engines.ecs_reports_engine import build_report
from modules.executive_overview.engines.enterprise_mock_service import build_pan_india_posture
from modules.executive_overview.engines.reports_analytics_engine import build_reports_overview
from modules.governance.engines.analytics_module import enterprise_dashboard
from modules.governance.engines.governance_intelligence import build_trends_module_view
from modules.governance.engines.trends_analytics_engine import build_trends_tab_payload
from modules.shared.services.module_capabilities import get_module_capability
from modules.shared.utils.data_source_marker import (
    DEMO,
    LIVE,
    PARTIAL,
    marker_payload,
)

client = TestClient(app, raise_server_exceptions=False)

SCOPED_ROUTES = [
    "/mvp/enterprise?role=cio&user=cio@bank.com",
    "/mvp/pan-india?role=cio&user=cio@bank.com",
    "/mvp/trends?role=cio&user=cio@bank.com",
    "/mvp/reports?role=cio&user=cio@bank.com",
    "/mvp/reports/view/framework-adherence?role=cio&user=cio@bank.com",
]


def test_marker_payload_live_provider():
    src = marker_payload(LIVE, "ecs_state.build_evidence_analytics", live_fields=["totals.approved"])
    assert src["status"] == LIVE
    assert src["label"] == "Live Data"
    assert "ecs_state.build_evidence_analytics" in src["tooltip"]


def test_enterprise_dashboard_marker_is_partial():
    ent = enterprise_dashboard()
    ds = ent["data_source"]
    assert ds["status"] == PARTIAL
    assert ds["provider"] == "analytics_module.enterprise_dashboard"
    assert ds["demo_fields"]
    assert ds["live_fields"]


def test_pan_india_marker_is_demo():
    posture = build_pan_india_posture()
    ds = posture["data_source"]
    assert ds["status"] == DEMO
    assert ds["provider"] == "enterprise_mock_service.build_pan_india_posture"


def test_trends_marker_is_partial():
    tab = build_trends_tab_payload()
    ds = tab["data_source"]
    assert ds["status"] == PARTIAL
    assert ds["provider"] == "trends_analytics_engine.build_trends_tab_payload"
    view = build_trends_module_view("cio")
    assert view["data_source"]["status"] == PARTIAL


def test_reports_overview_marker_is_partial():
    ov = build_reports_overview("cio")
    ds = ov["data_source"]
    assert ds["status"] == PARTIAL
    assert ds["provider"] == "reports_analytics_engine.build_reports_overview"


def test_regulatory_report_detail_marker_is_demo():
    report = build_report("framework-adherence")
    assert report is not None
    ds = report["data_source"]
    assert ds["status"] == DEMO
    assert "ecs_reports_engine.build_report" in ds["provider"]


def test_module_capability_propagates_data_source():
    ent = get_module_capability("enterprise", "cio")
    pan = get_module_capability("pan_india", "cio")
    trends = get_module_capability("trends", "cio")
    reports = get_module_capability("reports", "cio")
    assert ent["data_source"]["status"] == PARTIAL
    assert pan["data_source"]["status"] == DEMO
    assert trends["data_source"]["status"] == PARTIAL
    assert reports["data_source"]["status"] == PARTIAL


def test_scoped_screens_render_data_source_marker():
    expectations = {
        "/mvp/enterprise?role=cio&user=cio@bank.com": "PARTIAL",
        "/mvp/pan-india?role=cio&user=cio@bank.com": "DEMO",
        "/mvp/trends?role=cio&user=cio@bank.com": "PARTIAL",
        "/mvp/reports?role=cio&user=cio@bank.com": "PARTIAL",
        "/mvp/reports/view/framework-adherence?role=cio&user=cio@bank.com": "DEMO",
    }
    for route, status in expectations.items():
        resp = client.get(route)
        assert resp.status_code == 200, route
        html = resp.text
        assert "ecs-data-source-pill" in html, route
        assert f'data-ecs-data-source="{status}"' in html, route


def test_scoped_routes_remain_unchanged():
    for route in SCOPED_ROUTES:
        resp = client.get(route)
        assert resp.status_code == 200, route
