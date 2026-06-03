"""Validation — three distinct ECS execution engines (terminology and UX)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from modules.shared.services.execution_engine_registry import (
    application_onboarding_engine,
    evidence_collection_engine,
    governance_assessment_engine,
)

client = TestClient(app)
Q = "?role=cio&user=CIO"


def test_three_engines_have_unique_names_and_descriptions():
    e1 = evidence_collection_engine()
    e2 = application_onboarding_engine()
    e3 = governance_assessment_engine()
    titles = {e1["title"], e2["title"], e3["title"]}
    assert len(titles) == 3
    for eng in (e1, e2, e3):
        assert eng["description"]
        assert eng["run_button_label"]
        assert eng["dashboard"]["last_run_timestamp"]
        assert eng["dashboard"]["successful_runs"] >= 0


def test_operations_evidence_collection_page():
    html = client.get(f"/mvp/scheduler{Q}").text
    assert "Evidence Collection Engine" in html
    assert "Run Evidence Collection" in html
    assert "Collects and refreshes evidence from integrated enterprise platforms." in html
    assert "Run Scheduler" not in html
    assert "Run Onboarder" not in html
    assert ">Run Now<" not in html


def test_ai_sdlc_onboarding_page():
    html = client.get(f"/mvp/ai-sdlc/onboarding{Q}").text
    assert "Application Onboarding Engine" in html
    assert "Onboard Application" in html
    assert "Registers a new application and generates governance structures" in html
    assert "Run Onboarder" not in html
    assert "Run Scheduler" not in html


def test_ai_sdlc_control_tower_page():
    html = client.get(f"/mvp/ai-sdlc/control-tower{Q}").text
    assert "Run Governance Assessment" in html
    assert "Assessment Log" in html
    assert "Governance assessment orchestration" in html
    assert "Run Scheduler" not in html
    assert "Run Onboarder" not in html


def test_governance_assessment_api_engine_metadata():
    data = client.get(f"/api/ai-sdlc/control-tower/tab/run-scheduler{Q}").json()["data"]
    assert data["engine"]["title"] == "Governance Assessment Engine"
    assert data["engine"]["run_button_label"] == "Run Governance Assessment"


def test_assessment_log_terminology():
    messages = [e["message"] for e in client.get(f"/api/ai-sdlc/control-tower/tab/scheduler-log{Q}").json()["data"]["entries"]]
    assert "Governance Assessment Completed" in messages
    assert "Scheduler Run Completed" not in messages
