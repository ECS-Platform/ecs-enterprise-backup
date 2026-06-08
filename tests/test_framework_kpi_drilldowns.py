"""Framework KPI drilldown — clickability, datasets, pagination, search."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from modules.frameworks.engines.framework_kpi_drill_engine import (
    FRAMEWORK_KPI_SPECS,
    METRIC_COLUMN_PROFILES,
    drill_framework_kpi,
    iter_framework_kpi_pairs,
)
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

FRAMEWORKS = list(FRAMEWORK_KPI_SPECS.keys())
ARTIFACT = Path(__file__).resolve().parent / "artifacts" / "framework_kpi_drilldown_validation.html"


def _count_kpis() -> int:
    return sum(len(specs) for specs in FRAMEWORK_KPI_SPECS.values())


def test_every_framework_kpi_has_metric_slug():
    pairs = iter_framework_kpi_pairs()
    assert len(pairs) >= 60, f"Expected 60+ KPIs, got {len(pairs)}"
    for fw, metric, label in pairs:
        assert metric, f"{fw}/{label} missing metric slug"
        assert label, f"{fw}/{metric} missing label"


def test_framework_pages_every_kpi_clickable():
    snippets: list[str] = []
    for fw in FRAMEWORKS:
        resp = client.get(f"/framework/{fw.replace(' ', '%20')}?role=cio&user=cio@bank.com")
        assert resp.status_code == 200, fw
        html = resp.text
        assert "data-ecs-framework-kpi" in html, fw
        assert "ecsOpenFrameworkKpiDrill" in html, fw
        assert "ecs-kpi-drill-search" in html, fw
        for spec in FRAMEWORK_KPI_SPECS[fw]:
            assert f'data-ecs-framework-kpi-metric="{spec["metric"]}"' in html, f"{fw}/{spec['metric']}"
            assert spec["label"] in html, f"{fw} missing label {spec['label']}"
        kpi_count = html.count("data-ecs-framework-kpi-metric=")
        assert kpi_count >= len(FRAMEWORK_KPI_SPECS[fw]), f"{fw} KPI count {kpi_count}"
        snippets.append(f"<h2>{fw} ({kpi_count} KPIs)</h2>")
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text("<html><body>" + "<hr>".join(snippets) + "</body></html>", encoding="utf-8")


def test_all_framework_kpi_drills_return_25_rows():
    for fw, metric, _label in iter_framework_kpi_pairs():
        body = drill_framework_kpi(fw, metric)
        assert body["ok"] is True, f"{fw}/{metric}"
        assert len(body["rows"]) >= 25, f"{fw}/{metric} rows={len(body['rows'])}"
        assert len(body["columns"]) >= 6, f"{fw}/{metric} columns"


def test_appsec_metric_specific_columns():
    sast = drill_framework_kpi("AppSec", "sast_open_items")
    assert "finding_id" in sast["columns"]
    assert "severity" in sast["columns"]
    assert sast["rows"][0]["finding_id"].startswith("FND-")

    dast = drill_framework_kpi("AppSec", "dast_critical")
    assert "url" in dast["columns"]
    assert dast["rows"][0]["url"].startswith("https://")

    sca = drill_framework_kpi("AppSec", "sca_vulnerabilities")
    assert "package" in sca["columns"]
    assert "cvss" in sca["columns"]
    assert sca["rows"][0]["package"]


def test_framework_kpi_drill_api_all_frameworks():
    failures = []
    for fw, metric, label in iter_framework_kpi_pairs():
        resp = client.get(
            f"/api/framework/kpi-drill?framework={fw.replace(' ', '%20')}&metric={metric}"
        )
        if resp.status_code != 200:
            failures.append(f"{fw}/{metric} status={resp.status_code}")
            continue
        data = resp.json()
        if not data.get("ok") or len(data.get("rows", [])) < 25:
            failures.append(f"{fw}/{metric} rows={len(data.get('rows', []))}")
    assert not failures, "Drill API failures: " + "; ".join(failures[:5])


def test_drill_rows_include_standard_fields():
    body = drill_framework_kpi("VAPT", "open_vulnerabilities")
    row = body["rows"][0]
    for col in ("application", "framework", "owner", "status"):
        assert col in row
        assert row[col] and row[col] != "—"


def test_pagination_markup_in_drill_client():
    resp = client.get(f"/framework/VAPT?role=cio&user=cio@bank.com")
    assert "ecs-force-paginate" in resp.text
    assert "ecsRefreshPagination" in resp.text


def test_search_box_in_drill_client():
    resp = client.get(f"/framework/AppSec?role=cio&user=cio@bank.com")
    assert 'placeholder="Search records' in resp.text or "Search records" in resp.text
    assert "ecs-kpi-drill-search" in resp.text
    assert "attachSearch" in resp.text


def test_framework_workflow_draft_submitted_counts_match_drill_totals():
    from modules.frameworks.engines.framework_workflow_engine import ALL_FRAMEWORKS, build_framework_workflow_context, drill_framework_workflow

    for fw in ALL_FRAMEWORKS:
        ctx = build_framework_workflow_context(fw, "cio")
        draft_expected = ctx["summary"]["draft"]
        submitted_expected = ctx["summary"]["submitted"]
        draft_drill = drill_framework_workflow(fw, "draft")
        submitted_drill = drill_framework_workflow(fw, "submitted")
        assert len(draft_drill["rows"]) == draft_expected, f"{fw} draft mismatch"
        assert len(submitted_drill["rows"]) == submitted_expected, f"{fw} submitted mismatch"
        assert draft_drill.get("summary", {}).get("total_draft_evidence") == draft_expected
        assert submitted_drill.get("summary", {}).get("total_submitted_evidence") == submitted_expected


def test_total_drilldown_count():
    total = _count_kpis()
    assert total == len(list(iter_framework_kpi_pairs()))
    assert total >= 78
