"""Regression tests — AI SDLC Application Onboarding execution workspace."""

from __future__ import annotations

from fastapi.testclient import TestClient

from modules.ai_sdlc.engines.ai_sdlc_onboarding_engine import build_onboarding_run
from app.main import app

client = TestClient(app, follow_redirects=False)
Q = "?role=cio&user=CIO"

LEGACY_MARKERS = [
    "Supported Frameworks",
    "Onboarded Applications",
    "Sample Control Matrix",
    "ITPP Domain Structure",
    "onboarding-apps",
    "onboarding-matrix",
    "Change Management",
]


def test_onboarding_page_shell():
    resp = client.get(f"/mvp/ai-sdlc/onboarding{Q}")
    assert resp.status_code == 200
    html = resp.text
    assert "Application Onboarding" in html
    assert "generate" in html.lower() and "sdlc" in html.lower()
    assert "ecsRunOnboarderBtn" in html
    assert "ecsObDrillModal" in html


def test_no_legacy_onboarding_widgets():
    html = client.get(f"/mvp/ai-sdlc/onboarding{Q}").text
    for marker in LEGACY_MARKERS:
        assert marker not in html, marker


def test_onboarding_run_api():
    resp = client.get(f"/api/ai-sdlc/onboarding/run{Q}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["execution_steps"]) == 7
    assert data["summary"]["applications_discovered"] == 142
    assert data["summary"]["controls_assigned"] == 4872
    assert data["summary"]["evidence_requests"] == 2140
    assert data["summary"]["success_rate_pct"] == 98.7
    step2 = data["execution_steps"][1]
    assert "VAPT mapped to 102 applications" in step2["results"]
    assert len(data["framework_readiness"]) >= 5
    assert len(data["application_results"]) >= 4


def test_execution_steps_content():
    data = build_onboarding_run()
    messages = " ".join(
        r for step in data["execution_steps"] for r in step.get("results", [])
    )
    assert "4,872" in messages or "4872" in messages.replace(",", "")
    assert "Requirement tasks generated" in messages
    assert "Evidence requests created" in messages


def test_framework_drilldown_api():
    resp = client.get(f"/api/ai-sdlc/onboarding/drill/framework?framework=VAPT{Q}")
    assert resp.status_code == 200
    d = resp.json()["data"]
    for k in (
        "applications_mapped", "domains", "controls_assigned", "readiness_pct",
        "open_gaps", "pending_requirements", "pending_design", "pending_testing", "evidence_pending",
    ):
        assert k in d, k


def test_application_drilldown_api():
    resp = client.get(f"/api/ai-sdlc/onboarding/drill/application?application=Net Banking{Q}")
    assert resp.status_code == 200
    d = resp.json()["data"]
    for k in (
        "frameworks", "controls_assigned", "open_requirements", "open_design",
        "open_development", "open_testing", "open_golive", "evidence_pending",
        "open_findings", "remediation_status", "controls",
    ):
        assert k in d, k


def test_application_results_include_examples():
    data = client.get(f"/api/ai-sdlc/onboarding/run{Q}").json()["data"]
    apps = {r["application"]: r for r in data["application_results"]}
    assert "Net Banking" in apps
    assert apps["Net Banking"]["readiness_pct"] == 84
    assert apps["Core Banking"]["controls_assigned"] == 61


def test_framework_readiness_table_data():
    data = client.get(f"/api/ai-sdlc/onboarding/run{Q}").json()["data"]
    fws = {r["framework"]: r for r in data["framework_readiness"]}
    assert fws["VAPT"]["coverage_pct"] == 72
    assert fws["ITPP"]["status"] == "Ready"
