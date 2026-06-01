"""P1 demo polish — drilldowns, AI Ops, reports, pagination, data quality."""

from __future__ import annotations

from fastapi.testclient import TestClient

from modules.operations.engines.ai_ops_summary_engine import build_summary_page
from modules.executive_overview.engines.demo_kpi_drill_engine import drill_demo_kpi
from modules.executive_overview.engines.ecs_reports_engine import build_report
from app.main import app
from modules.shared.drilldowns.module_kpi_drill_engine import drill_module_kpi

client = TestClient(app, raise_server_exceptions=False)
Q = "?role=cio&user=cio@bank.com"


def test_top_risk_applications_table_css():
    resp = client.get(f"/mvp/demo-overview{Q}")
    assert resp.status_code == 200
    assert "col-app" in resp.text
    assert "min-width: 250px" in resp.text
    assert "word-break: normal" in resp.text
    assert "Customer Onboarding" in resp.text or "Net Banking" in resp.text


def test_demo_kpi_drill_minimum_rows():
    for metric in ("applications", "frameworks", "vapt", "tickets", "hallucinations"):
        body = drill_demo_kpi(metric)
        assert body["ok"] is True
        assert len(body["rows"]) >= 25, metric
        assert len(body["columns"]) >= 8


def test_demo_kpi_drill_api():
    resp = client.get("/api/demo/kpi-drill?metric=applications")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["rows"]) >= 25


def test_module_kpi_drill_minimum_rows():
    body = drill_module_kpi("scheduler", "failed_collections", "cio")
    assert body["ok"] is True
    assert len(body["rows"]) >= 25


def test_ai_ops_copilot_layout():
    resp = client.get(f"/mvp/ai-ops-assistant{Q}")
    assert resp.status_code == 200
    assert "ecs-copilot-shell" in resp.text
    assert "ecs-copilot-footer" in resp.text
    assert "ecs-copilot-left" in resp.text
    assert 'id="ecsChatInput"' in resp.text


def test_ai_ops_summary_pages():
    for mode in ("business", "technical", "executive"):
        resp = client.get(f"/mvp/ai-ops-assistant/summary/{mode}?scenario=net_banking&role=cio&user=cio@bank.com")
        assert resp.status_code == 200, mode
        page = build_summary_page(mode, "net_banking", "cio")
        assert page is not None
        assert len(page["rows"]) >= 25
        assert page["recommendations"]


def test_report_pages():
    for rtype in (
        "framework-adherence",
        "framework-readiness",
        "application-compliance",
        "evidence-coverage",
        "findings-remediation",
    ):
        report = build_report(rtype)
        assert report is not None
        assert len(report["rows"]) >= 25
        resp = client.get(f"/mvp/reports/view/{rtype}?role=cio&user=cio@bank.com")
        assert resp.status_code == 200, rtype


def test_reports_generate_button():
    resp = client.get(f"/mvp/reports{Q}")
    assert resp.status_code == 200
    assert "Generate Report" in resp.text
    assert "/mvp/reports/view/" in resp.text


def test_grc_drill_padded_rows():
    from modules.enterprise_grc.engines.grc_module_demo import drill_governance_analytics

    body = drill_governance_analytics("open_findings", role="cio")
    assert len(body["rows"]) >= 25


def test_cio_kpis_clickable():
    resp = client.get(f"/mvp/demo-overview{Q}")
    assert 'data-ecs-demo-kpi' in resp.text
    assert resp.text.count("data-ecs-demo-kpi") >= 10
