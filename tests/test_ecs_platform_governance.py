"""Platform-wide governance, drilldown, and traceability validation."""

from __future__ import annotations

from fastapi.testclient import TestClient

from modules.shared.drilldowns.ecs_universal_drill_engine import drill_universal_kpi, parse_display_count
from modules.shared.services.evidence_workflow_engine import build_workflow_context, drill_workflow_metric
from modules.frameworks.engines.framework_workflow_engine import ALL_FRAMEWORKS, build_framework_workflow_context
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

ROLES = ["cio", "vertical_head", "functional_head", "owner", "auditor", "compliance_head"]
MVP_PAGES = [
    "scheduler", "audit-prep", "evidence-health", "completeness", "search",
    "risk-register", "governance-analytics", "ai-ops-assistant", "bulk-upload",
    "onboarding", "reuse", "lifecycle", "comparison", "reports", "trends",
]
WORKFLOW_METRICS = ["draft", "submitted", "reupload", "approval_rate", "pending_aging"]


def test_universal_drill_api_minimum_rows():
    resp = client.get("/api/ecs/universal-drill?scope=kpi&page=scheduler&metric=failed_jobs&count=36")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert len(data["rows"]) >= 25
    assert data.get("sections")


def test_traceability_count_matching():
    assert parse_display_count("79") == 79
    assert parse_display_count("73.4%") == 73
    body = drill_universal_kpi("demo", "applications", count=79)
    assert body["trace_count"] == 79
    assert len(body["rows"]) >= 25


def test_workflow_drill_all_roles():
    for role in ROLES:
        for metric in WORKFLOW_METRICS:
            resp = client.get(f"/api/ecs/workflow-drill?metric={metric}&role={role}&count=30")
            assert resp.status_code == 200, f"{role}/{metric}"
            data = resp.json()
            assert data["ok"] is True
            assert len(data["rows"]) >= 25


def test_enterprise_workflow_has_audit_history():
    body = drill_workflow_metric("cio", "submitted", 40)
    assert body["sections"]["audit_history"]
    entry = body["sections"]["audit_history"][0]
    for field in ("user", "role", "timestamp", "previous_status", "new_status", "comments"):
        assert field in entry


def test_framework_metrics_unique_including_extensions():
    sigs = set()
    for fw in ALL_FRAMEWORKS:
        ctx = build_framework_workflow_context(fw, "cio")
        s = ctx["summary"]
        cards = {c["metric"]: c["value"] for c in ctx.get("summary_cards", [])}
        sig = (s.get("draft"), s.get("submitted"), cards.get("readiness_score"))
        assert sig not in sigs, f"Duplicate metrics for {fw}"
        sigs.add(sig)


def test_mvp_pages_include_universal_drill():
    failures = []
    for page in MVP_PAGES:
        resp = client.get(f"/mvp/{page}?role=cio&user=cio@bank.com")
        if resp.status_code != 200:
            failures.append(f"{page} status={resp.status_code}")
            continue
        html = resp.text
        if "ecsUniversalDrillModal" not in html:
            failures.append(f"{page} missing universal drill")
        if "data-ecs-module-kpi" not in html and "data-ecs-universal-kpi" not in html and "data-grc-drill" not in html:
            if page not in ("search", "comparison"):
                failures.append(f"{page} no kpi drill attrs")
    assert not failures, "; ".join(failures[:8])


def test_dashboard_workflow_drillable():
    resp = client.get("/dashboard?role=cio&user=cio@bank.com")
    assert resp.status_code == 200
    html = resp.text
    assert "data-ecs-enterprise-wf-drill" in html
    assert "ecsOpenEnterpriseWorkflowDrill" in html


def test_governance_pages_workflow_drillable():
    for page in ("evidence-health", "evidence-approval", "completeness"):
        resp = client.get(f"/mvp/{page}?role=cio&user=cio@bank.com")
        assert "data-ecs-enterprise-wf-drill" in resp.text, page


def test_universal_row_drill_api():
    resp = client.get("/api/ecs/universal-drill?scope=row&page=scheduler&type=job&id=scan-001")
    data = resp.json()
    assert data["ok"] is True
    assert len(data["rows"]) >= 25
    assert data.get("sections")


def test_universal_chart_drill_api():
    resp = client.get("/api/ecs/universal-drill?scope=chart&page=trends&chart=compliance&element=PCI&count=25")
    data = resp.json()
    assert data["ok"] is True
    assert len(data["rows"]) >= 25


def test_workflow_context_has_metric_slugs():
    ctx = build_workflow_context("cio")
    for c in ctx["summary"]["counters"]:
        assert c.get("metric"), f"counter {c['label']} missing metric"
