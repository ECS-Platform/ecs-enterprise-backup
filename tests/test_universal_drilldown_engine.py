"""Universal drilldown engine validation."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from modules.shared.services.drilldown_engine import drill_heatmap_cell, drill_kpi
from modules.shared.services.metric_trace_service import build_metric_trace

client = TestClient(app)


def test_metric_trace_has_formula_and_banking_apps():
    trace = build_metric_trace(metric="readiness", page="audit_prep", label="Audit Readiness", count=79, framework="PCI DSS")
    assert trace["calculation_formula"]["implemented_controls"] > 0
    assert len(trace["contributing_applications"]) >= 3
    assert trace["contributing_evidence"]
    assert trace["related_observations"]
    assert len(trace["historical_trend"]) == 6


def test_drill_kpi_includes_metric_trace():
    body = drill_kpi("scheduler", "failed_jobs", count=36)
    assert body["ok"] is True
    assert body.get("metric_trace")
    assert body["metric_trace"]["calculation_formula"]


def test_heatmap_drill():
    body = drill_heatmap_cell("Mobile Banking", "PCI DSS", "56")
    assert body["ok"] is True
    assert body.get("metric_trace")
    assert body["heatmap_context"]["application"] == "Mobile Banking"


def test_universal_drill_api_metric_trace():
    r = client.get("/api/ecs/universal-drill?scope=kpi&page=audit-prep&metric=readiness&count=79&label=Audit%20Readiness")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data.get("metric_trace")
    assert len(data["rows"]) >= 25


def test_static_drilldown_js():
    r = client.get("/static/ecs/js/drilldown_engine.js")
    assert r.status_code == 200
    assert "ecsOpenUniversalKpiDrill" in r.text


def test_governance_pages_have_drill_modal():
    for page in ("audit-prep", "evidence-health", "completeness", "risk-register", "governance-analytics"):
        r = client.get(f"/mvp/{page}?role=cio&user=cio@bank.com")
        assert r.status_code == 200
        assert "ecsUniversalDrillModal" in r.text
        assert "drilldown_engine.js" in r.text


def test_grc_pages_have_drill():
    for page in ("risk-register", "cmdb", "regulatory", "exceptions"):
        r = client.get(f"/mvp/{page}?role=cio&user=cio@bank.com")
        assert r.status_code == 200
        assert "drilldown_engine.js" in r.text
