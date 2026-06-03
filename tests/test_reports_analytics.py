"""Reports module — overview metrics, KPI consistency, and drilldown APIs."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from modules.executive_overview.engines.reports_analytics_engine import (
    build_reports_overview,
    list_generated_report_records,
    list_pending_export_records,
    list_report_catalog,
    list_scheduled_export_records,
)
from modules.executive_overview.engines.reports_drill_engine import drill_reports_kpi

client = TestClient(app, raise_server_exceptions=False)


def test_kpi_counts_match_records():
    ov = build_reports_overview("cio")
    counts = ov["counts"]
    assert counts["available"] == len(ov["catalog"])
    assert counts["available"] == len(list_report_catalog())
    assert counts["generated"] == len(ov["generated_records"])
    assert counts["generated"] == len(list_generated_report_records())
    assert counts["scheduled"] == len(ov["scheduled_records"])
    assert counts["scheduled"] == len(list_scheduled_export_records())
    assert counts["pending"] == len(ov["pending_records"])
    assert counts["pending"] == len(list_pending_export_records())


def test_overview_has_required_sections():
    ov = build_reports_overview("cio")
    assert ov["export_distribution"]
    assert ov["generation_trend"]["daily"]
    assert ov["top_downloaded"]
    assert ov["recent_activity"]
    assert ov["upcoming_scheduled"]
    assert len(ov["kpis"]) == 6


def test_available_reports_drill_catalog_columns():
    body = drill_reports_kpi("available_reports", "cio")
    assert body["ok"] is True
    assert body["metric_trace"]["calculation_formula"]
    assert body["rows"]
    assert "report_name" in body["columns"]
    assert len(body["rows"]) == body["detail"]["count"]


def test_reports_page_overview_not_blank():
    resp = client.get("/mvp/reports?role=cio&user=cio@bank.com")
    assert resp.status_code == 200
    html = resp.text
    assert "Reporting Health" in html
    assert "Export Distribution" in html
    assert "Report Generation Trend" in html
    assert "Top Downloaded Reports" in html
    assert "Recent Export Activity" in html
    assert "Upcoming Scheduled Exports" in html
    assert "Available Reports" in html
    assert "Success Rate" in html
    assert "data-ecs-universal-kpi" in html
    assert "Loading reports…" not in html or "catalog reports" in html


def test_reports_universal_drill_api():
    resp = client.get("/api/ecs/universal-drill?scope=kpi&page=reports&metric=available_reports&count=30")
    assert resp.status_code == 200
    j = resp.json()
    assert j["ok"] is True
    assert j.get("metric_trace")
