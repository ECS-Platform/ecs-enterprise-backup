"""Enterprise-wide drilldown and framework data consistency validation."""

from __future__ import annotations

from fastapi.testclient import TestClient

from modules.frameworks.engines.ecs_row_drill_engine import drill_framework_row
from modules.frameworks.engines.framework_kpi_drill_engine import FRAMEWORK_KPI_SPECS
from modules.frameworks.engines.framework_workflow_engine import ALL_FRAMEWORKS, build_framework_workflow_context, drill_framework_workflow
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

WORKFLOW_METRICS = [
    "draft", "submitted", "reupload", "auditor_approved",
    "approval_rate", "avg_review_time", "rejection_trend", "pending_aging",
    "findings", "controls", "applications_covered", "readiness_score",
]

FRAMEWORKS = ALL_FRAMEWORKS


def _workflow_signature(framework: str) -> tuple:
    ctx = build_framework_workflow_context(framework, "cio")
    s = ctx["summary"]
    cards = {c["metric"]: c["value"] for c in ctx.get("summary_cards", [])}
    analytics = {c["metric"]: c["value"] for c in ctx["analytics"]["cards"]}
    return (
        s.get("draft"), s.get("submitted"), s.get("reupload_requested"), s.get("approved"),
        analytics.get("approval_rate"), analytics.get("avg_review_time"),
        analytics.get("rejection_trend"), analytics.get("pending_aging"),
        cards.get("findings"), cards.get("controls"),
        cards.get("applications_covered"), cards.get("readiness_score"),
    )


def test_framework_workflow_metrics_are_unique_per_framework():
    signatures: dict[str, tuple] = {}
    for fw in FRAMEWORKS:
        sig = _workflow_signature(fw)
        signatures[fw] = sig
        assert all(v is not None for v in sig), f"{fw} missing workflow metric values"
    unique_sigs = set(signatures.values())
    assert len(unique_sigs) == len(FRAMEWORKS), (
        "Duplicate workflow signatures detected — frameworks share metrics"
    )


def test_framework_pages_workflow_kpis_clickable():
    for fw in FRAMEWORKS:
        resp = client.get(f"/framework/{fw.replace(' ', '%20')}?role=cio&user=cio@bank.com")
        assert resp.status_code == 200, fw
        html = resp.text
        assert "data-ecs-framework-wf-drill" in html, f"{fw} missing workflow drill attrs"
        assert "ecsOpenFrameworkWorkflowDrill" in html, f"{fw} missing workflow drill JS"
        for metric in WORKFLOW_METRICS:
            assert f'data-ecs-framework-wf-metric="{metric}"' in html, f"{fw}/{metric}"


def test_framework_pages_table_rows_clickable():
    sample_frameworks = ["PCI DSS", "VAPT", "RBI Cyber Security", "AppSec"]
    for fw in sample_frameworks:
        resp = client.get(f"/framework/{fw.replace(' ', '%20')}?role=cio&user=cio@bank.com")
        html = resp.text
        assert "data-ecs-framework-row-drill" in html, fw
        assert "ecsOpenFrameworkRowDrill" in html, fw
        assert html.count("data-ecs-framework-row-drill") >= 5, f"{fw} too few clickable rows"


def test_framework_tab_drill_buttons_present():
    resp = client.get("/framework/PCI%20DSS?role=cio&user=cio@bank.com")
    html = resp.text
    assert "data-ecs-framework-tab-drill" in html
    for tab in ("applications", "controls", "evidence", "findings", "pending", "exceptions", "reuse"):
        assert f'data-ecs-framework-tab-id="{tab}"' in html, tab


def test_workflow_drill_api_returns_25_rows_all_metrics():
    failures = []
    for fw in FRAMEWORKS:
        for metric in WORKFLOW_METRICS:
            resp = client.get(
                f"/api/framework/workflow-drill?framework={fw.replace(' ', '%20')}&metric={metric}"
            )
            if resp.status_code != 200:
                failures.append(f"{fw}/{metric} status={resp.status_code}")
                continue
            data = resp.json()
            if not data.get("ok") or len(data.get("rows", [])) < 25:
                failures.append(f"{fw}/{metric} rows={len(data.get('rows', []))}")
    assert not failures, "; ".join(failures[:8])


def test_row_drill_api_returns_25_rows_with_sections():
    row_types = ["application", "control", "finding", "evidence", "pending", "exception"]
    for fw in ["PCI DSS", "VAPT", "RBI Cyber Security"]:
        for row_type in row_types:
            body = drill_framework_row(fw, row_type, f"test-{row_type}")
            assert body["ok"] is True
            assert len(body["rows"]) >= 25, f"{fw}/{row_type}"
            assert body.get("sections"), f"{fw}/{row_type} missing sections"
            for sec in ("related_controls", "related_evidence", "related_findings"):
                assert len(body["sections"][sec]) >= 10, f"{fw}/{row_type}/{sec}"


def test_tab_drill_api_returns_25_rows():
    tabs = ["applications", "controls", "evidence", "findings", "pending", "exceptions", "reuse"]
    for tab in tabs:
        resp = client.get(f"/api/framework/tab-drill?framework=PCI%20DSS&tab={tab}")
        assert resp.status_code == 200, tab
        data = resp.json()
        assert data.get("ok") is True, tab
        assert len(data.get("rows", [])) >= 25, f"{tab} rows={len(data.get('rows', []))}"


def test_rbi_cyber_security_in_kpi_specs():
    assert "RBI Cyber Security" in FRAMEWORK_KPI_SPECS
    assert len(FRAMEWORK_KPI_SPECS["RBI Cyber Security"]) >= 6


def test_rbi_framework_page_loads_with_drills():
    resp = client.get("/framework/RBI%20Cyber%20Security?role=cio&user=cio@bank.com")
    assert resp.status_code == 200
    html = resp.text
    assert "RBI Maturity Score" in html
    assert "data-ecs-framework-kpi" in html
    assert "data-ecs-framework-wf-drill" in html


def test_drill_rows_contain_banking_fields():
    body = drill_framework_workflow("PCI DSS", "findings")
    row = body["rows"][0]
    for field in ("application", "framework", "owner", "status", "control"):
        assert field in row and row[field] and row[field] != "—", field
