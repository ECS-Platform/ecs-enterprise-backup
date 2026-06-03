"""Trends module — KPI data, tab series, and drilldown APIs."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from modules.governance.engines.governance_intelligence import build_contextual_trends, parse_analytics_filters
from modules.governance.engines.trends_analytics_engine import build_trends_tab_payload, enterprise_control_totals
from modules.governance.engines.trends_drill_engine import drill_trends_kpi

client = TestClient(app, raise_server_exceptions=False)


def test_enterprise_control_totals_scale():
    totals = enterprise_control_totals(parse_analytics_filters())
    assert totals["total_controls"] >= 50_000
    assert totals["implemented_controls"] >= 20_000
    assert 35 <= totals["coverage_pct"] <= 50
    assert totals["implemented_controls"] + totals["missing_controls"] + totals["pending_controls"] == totals["total_controls"]


def test_trends_tab_series_have_required_fields():
    tab = build_trends_tab_payload()
    assert tab["coverage_series"]
    row = tab["coverage_series"][0]
    assert "implemented" in row and "missing" in row and "pending" in row
    assert "pct_implemented" in row
    obs = tab["observations_series"][0]
    assert {"opened", "closed", "net", "closure_rate_pct"} <= obs.keys()
    rej = tab["rejections_series"][0]
    assert {"submitted", "rejected", "rate_pct"} <= rej.keys()
    sla = tab["sla_series"][0]
    assert {"within_sla_pct", "near_breach", "breached"} <= sla.keys()


def test_executive_kpis_no_failed_label():
    intel = build_contextual_trends()
    for k in intel["executive_kpis"]:
        assert "Failed" not in str(k["value"])
        assert k["value"] not in ("Failed", "—", "")


def test_implementation_coverage_drill_has_formula():
    body = drill_trends_kpi("implementation_coverage", "cio")
    assert body["ok"] is True
    trace = body["metric_trace"]
    assert trace["calculation_formula"]["implemented_controls"] > 0
    assert trace["calculation_formula"]["applicable_controls"] > trace["calculation_formula"]["implemented_controls"]
    assert "PCI DSS" in trace["contributing_frameworks"] or trace.get("framework_contributions")


def test_trends_page_renders_kpis_and_tabs():
    resp = client.get("/mvp/trends?role=cio&user=cio@bank.com")
    assert resp.status_code == 200
    html = resp.text
    assert "Implementation Coverage" in html
    assert "Observations Net" in html
    assert "Auditor Rejection Rate" in html
    assert "Remediation SLA Compliance" in html
    assert "Failed Evidence" not in html
    assert "Evidence Rejections" in html
    assert "Implemented Controls" in html or "implemented_controls" in html.lower()
    assert "data-ecs-universal-kpi" in html
    assert "trends_analytics_client" in html or "ecsTrendCoverageChart" in html


def test_trends_universal_drill_api():
    resp = client.get("/api/ecs/universal-drill?scope=kpi&page=trends&metric=implementation_coverage&count=42")
    assert resp.status_code == 200
    j = resp.json()
    assert j["ok"] is True
    assert j.get("metric_trace", {}).get("calculation_formula")


def test_granularity_trend_labels_are_business_friendly():
    from modules.executive_overview.engines.executive_analytics_engine import build_granularity_trends

    trends = build_granularity_trends()
    daily = trends["daily"]["compliance"]
    assert daily
    labels = [p["label"] for p in daily]
    assert not any(lb.startswith("D") and lb[1:].isdigit() for lb in labels), labels
    assert any("-" in lb for lb in labels), labels
    weekly = trends["weekly"]["observations"]
    wlabels = [p["label"] for p in weekly]
    assert wlabels[0] == "Week 1"
    assert not any(lb.startswith("W") and len(lb) <= 3 and lb[1:].isdigit() for lb in wlabels)
    monthly = trends["monthly"]["compliance"]
    mlabels = [p["label"] for p in monthly]
    assert mlabels[0] in ("Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun")
    quarterly = trends["quarterly"]["compliance"]
    qlabels = [p["label"] for p in quarterly]
    assert qlabels[0].startswith("Q")


def test_trends_page_granularity_json_has_no_placeholder_days():
    resp = client.get("/mvp/trends?role=cio&user=cio@bank.com")
    assert resp.status_code == 200
    assert '"D1"' not in resp.text and '"D13"' not in resp.text
    assert "Week 1" in resp.text or "Week 1" in resp.text.replace("\\u0020", " ")


def test_analytics_intel_api():
    resp = client.get("/mvp/api/analytics-intel")
    assert resp.status_code == 200
    data = resp.json()
    assert data["kpis"]
    assert data["intel"]["trends_payload"]["coverage_series"]


def test_observations_closure_rate_label_and_subtitle():
    from modules.governance.engines.governance_intelligence import build_contextual_trends

    intel = build_contextual_trends()
    obs = intel["observations"]
    assert obs["subtitle"] == "Monthly opened vs closed audit observations"
    assert obs["closure_rate_label"] == "Closed vs Newly Opened Rate"
    assert "backlog reduction" in obs["closure_rate_tooltip"].lower()
    assert obs["closure_rate_pct"] > 100


def test_observations_chart_drill_row_count_matches_bar():
    from modules.governance.engines.trends_drill_engine import drill_observations_chart_bar

    tab = build_trends_tab_payload()
    mar = next(s for s in tab["observations_series"] if s["label"] == "Mar")
    for role in ("cio", "owner", "auditor", "vertical_head"):
        opened = drill_observations_chart_bar("Mar", "opened", role=role)
        assert opened["ok"] is True
        assert opened["row_count"] == mar["opened"]
        assert opened["trace_count"] == mar["opened"]
        assert "observation_id" in opened["columns"]
        assert "opened_date" in opened["columns"]

        closed = drill_observations_chart_bar("Mar", "closed", role=role)
        assert closed["row_count"] == mar["closed"]
        assert "closure_date" in closed["columns"]


def test_observations_universal_drill_period_element():
    tab = build_trends_tab_payload()
    mar = next(s for s in tab["observations_series"] if s["label"] == "Mar")
    resp = client.get(
        "/api/ecs/universal-drill?scope=chart&page=trends&chart=observations&element=Mar|opened&count="
        + str(mar["opened"])
        + "&role=auditor"
    )
    assert resp.status_code == 200
    j = resp.json()
    assert j["ok"] is True
    assert j["row_count"] == mar["opened"]


def test_trends_page_observations_tab_copy():
    for role in ("cio", "owner", "auditor", "vertical_head"):
        resp = client.get(f"/mvp/trends?role={role}&user={role}@bank.com")
        assert resp.status_code == 200
        html = resp.text
        assert "Monthly opened vs closed audit observations" in html
        assert "Closed vs Newly Opened Rate" in html
        assert "Opened Observations" in html
        assert "Closed Observations" in html
        assert "Control observations · evidence gaps" not in html
