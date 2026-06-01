"""Framework-specific KPI configurations — uniqueness and drilldown validation."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.framework_dashboards import _catalog_stats, build_framework_dashboard
from app.framework_kpi_drill_engine import (
    FRAMEWORK_KPI_SPECS,
    build_framework_kpi_list,
    drill_framework_kpi,
    framework_kpi_labels,
)
from app.framework_catalog import get_framework_controls, resolve_framework_name
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

FRAMEWORKS = [
    "PCI DSS",
    "DPSC",
    "OS Baselining",
    "DB Baselining",
    "Nginx Baselining",
    "AppSec",
    "VAPT",
    "CSITE",
    "ITPP",
    "ITDRM",
    "SOC2",
    "ISO27001",
]

ARTIFACT = Path(__file__).resolve().parent / "artifacts" / "framework_kpi_validation.html"


def _controls(fw: str) -> list:
    return get_framework_controls(fw)


def test_all_frameworks_have_kpi_specs():
    for fw in FRAMEWORKS:
        assert fw in FRAMEWORK_KPI_SPECS, fw
        assert len(FRAMEWORK_KPI_SPECS[fw]) >= 5, fw


def test_framework_kpi_titles_differ():
    label_sets = {}
    for fw in FRAMEWORKS:
        labels = framework_kpi_labels(fw)
        label_sets[fw] = labels
        assert len(labels) >= 5
        assert len(set(labels)) == len(labels), f"Duplicate labels in {fw}"
    # VAPT vs DPSC must not share the same label set
    assert label_sets["VAPT"] != label_sets["DPSC"]
    assert label_sets["OS Baselining"] != label_sets["DB Baselining"]
    assert label_sets["ITDRM"] != label_sets["SOC2"]


def test_framework_kpi_values_differ():
    values_by_fw = {}
    for fw in FRAMEWORKS:
        controls = _controls(fw)
        stats = _catalog_stats(controls)
        kpis = build_framework_kpi_list(fw, controls, stats)
        values_by_fw[fw] = [k["value"] for k in kpis]
    assert values_by_fw["VAPT"] != values_by_fw["DPSC"]
    assert values_by_fw["CSITE"] != values_by_fw["AppSec"]


def test_required_framework_kpi_labels():
    required = {
        "VAPT": {"Open Vulnerabilities", "Critical CVEs", "Pen-Test Findings", "Remediation Backlog", "Retest Pass Rate"},
        "DPSC": {"Payment Controls", "UPI Security Controls", "Card Security Controls", "Encryption Compliance", "Open Payment Findings"},
        "OS Baselining": {"Servers Assessed", "Baseline Deviations", "Critical Deviations", "Patch Compliance", "Hardening Score"},
        "DB Baselining": {"Databases Assessed", "Critical DB Findings", "Privilege Violations", "Backup Compliance", "Encryption Coverage"},
        "ITPP": {"Policies Reviewed", "Process Controls", "Exceptions", "Compliance %", "Open Actions"},
        "CSITE": {"SAST Findings", "DAST Findings", "Code Review Coverage", "Secure Coding Controls", "Remediation Progress"},
    }
    for fw, labels in required.items():
        got = set(framework_kpi_labels(fw))
        missing = labels - got
        assert not missing, f"{fw} missing KPIs: {missing}"


def test_framework_pages_render_unique_kpis():
    snippets = []
    for fw in FRAMEWORKS:
        url_fw = fw.replace(" ", "%20")
        resp = client.get(f"/framework/{url_fw}?role=cio&user=cio@bank.com")
        assert resp.status_code == 200, fw
        assert "data-ecs-framework-kpi" in resp.text, fw
        assert fw in resp.text or resolve_framework_name(fw) in resp.text
        # First KPI label for this framework should appear
        first_label = FRAMEWORK_KPI_SPECS[fw][0]["label"]
        assert first_label in resp.text, f"{fw} missing {first_label}"
        snippets.append(f"<h2>{fw}</h2>\n" + resp.text[resp.text.find("ecs-exec-strip"):resp.text.find("ecs-exec-strip") + 1200])
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text("<html><body>" + "<hr>".join(snippets) + "</body></html>", encoding="utf-8")
    assert ARTIFACT.exists()


def test_framework_kpi_drill_api():
    body = drill_framework_kpi("VAPT", "critical_cves")
    assert body["ok"] is True
    assert body["framework"] == "VAPT"
    assert len(body["rows"]) >= 25
    assert "application" in body["columns"]
    assert "cvss" in body["columns"]
    resp = client.get("/api/framework/kpi-drill?framework=VAPT&metric=critical_cves")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["rows"]) >= 25
    row = data["rows"][0]
    for col in ("application", "framework", "finding_id", "owner", "status"):
        assert col in row
    assert row["framework"] == "VAPT"


def test_framework_kpi_drill_multiple_frameworks():
    samples = [
        ("DPSC", "payment_controls"),
        ("OS Baselining", "baseline_deviations"),
        ("DB Baselining", "privilege_violations"),
        ("ITPP", "open_actions"),
        ("CSITE", "sast_findings"),
        ("ITDRM", "dr_test_coverage"),
        ("SOC2", "trust_criteria_coverage"),
        ("ISO27001", "annex_a_controls"),
    ]
    for fw, metric in samples:
        resp = client.get(f"/api/framework/kpi-drill?framework={fw.replace(' ', '%20')}&metric={metric}")
        assert resp.status_code == 200, f"{fw}/{metric}"
        data = resp.json()
        assert data["ok"] is True
        assert data["framework"] == fw
        assert len(data["rows"]) >= 25


def test_build_framework_dashboard_includes_metrics():
    for fw in ("VAPT", "DPSC", "ITDRM"):
        controls = _controls(fw)
        dash = build_framework_dashboard(fw, controls)
        kpis = dash["kpis"]
        assert all(k.get("metric") for k in kpis)
        assert all(k.get("label") for k in kpis)
