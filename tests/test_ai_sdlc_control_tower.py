"""Tests for AI SDLC Control Tower — Phase 2."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.ai_sdlc_control_tower_engine import TAB_IDS, build_run_scheduler
from app.main import app

client = TestClient(app, follow_redirects=False)
Q = "?role=cio&user=CIO"

TABS = [
    ("run-scheduler", "execution_steps", "readiness_matrix"),
    ("framework-readiness", "heatmap", "stage_columns"),
    ("action-queue", "rows", "activity_id"),
    ("scheduler-log", "entries", "auto_refresh_seconds"),
    ("ai-recommendations", "rows", "stage"),
]


def test_control_tower_route_and_nav():
    resp = client.get(f"/mvp/ai-sdlc/control-tower{Q}")
    assert resp.status_code == 200
    html = resp.text
    assert "AI SDLC Control Tower" in html
    assert 'data-nav-module="ai_sdlc_control_tower"' in html
    assert 'class="aisdlc-kpi-grid"' not in html
    assert 'data-workspace-tab="live-scan"' not in html
    assert 'data-workspace-tab="lifecycle"' not in html


def test_tab_buttons_phase2():
    html = client.get(f"/mvp/ai-sdlc/control-tower{Q}").text
    for tab_id, label in [
        ("run-scheduler", "Run Scheduler"),
        ("framework-readiness", "Framework Readiness"),
        ("action-queue", "Action Queue"),
        ("scheduler-log", "Scheduler Log"),
        ("ai-recommendations", "AI Recommendations"),
    ]:
        assert f'data-workspace-tab="{tab_id}"' in html
        assert label in html
    assert 'data-workspace-tab="live-scan"' not in html


def test_all_tab_apis_load():
    for tab_id, key1, key2 in TABS:
        resp = client.get(f"/api/ai-sdlc/control-tower/tab/{tab_id}{Q}")
        assert resp.status_code == 200, tab_id
        body = resp.json()
        assert body["ok"] is True, tab_id
        data = body["data"]
        assert key1 in data, tab_id
        if key2 in ("activity_id", "stage"):
            assert data["rows"] and key2 in data["rows"][0], tab_id
        else:
            assert key2 in data, tab_id


def test_run_scheduler_data():
    data = build_run_scheduler()
    assert len(data["execution_steps"]) >= 10
    assert data["summary"]["applications_scanned"] == 142
    assert data["summary"]["controls_assessed"] == 4872
    assert data["summary"]["evidence_items_scanned"] == 18341
    assert data["summary"]["open_findings"] == 127
    matrix = data["readiness_matrix"]
    assert "VAPT" in [r["framework"] for r in matrix["rows"]]
    assert matrix["stage_columns"] == ["Req", "Design", "Dev", "Test", "Go-Live"]


def test_readiness_matrix_drilldown_api():
    resp = client.get(f"/api/ai-sdlc/control-tower/drill/readiness?framework=VAPT&stage=Testing{Q}")
    assert resp.status_code == 200
    d = resp.json()["data"]
    assert d["framework"] == "VAPT"
    assert len(d["rows"]) >= 1
    row = d["rows"][0]
    for k in ("application", "control", "status", "evidence"):
        assert k in row


def test_framework_readiness_drilldown_api():
    resp = client.get(
        f"/api/ai-sdlc/control-tower/drill/framework?framework=VAPT&stage_key=testing{Q}"
    )
    assert resp.status_code == 200
    d = resp.json()["data"]
    assert "applications" in d
    assert "controls" in d
    assert "evidence" in d
    assert len(d["applications"]) >= 1
    assert len(d["controls"]) >= 1


def test_action_queue_work_item_detail():
    queue = client.get(f"/api/ai-sdlc/control-tower/tab/action-queue{Q}").json()["data"]
    aid = queue["rows"][0]["activity_id"]
    resp = client.get(f"/api/ai-sdlc/control-tower/work-item/{aid}{Q}")
    assert resp.status_code == 200
    d = resp.json()["data"]
    for k in (
        "application", "framework", "control_id", "control_name", "stage",
        "artifact_required", "status", "owner", "comments", "approval_history", "audit_trail",
    ):
        assert k in d, k


def test_scheduler_log_realistic_values():
    data = client.get(f"/api/ai-sdlc/control-tower/tab/scheduler-log{Q}").json()["data"]
    messages = [e["message"] for e in data["entries"]]
    times = [e["time"] for e in data["entries"]]
    assert "142 Applications Loaded" in messages
    assert "4,872 Controls Assessed" in messages
    assert "18,341 Evidence Records Scanned" in messages
    assert "127 Open Findings Detected" in messages
    assert "Scheduler Run Completed" in messages
    assert all(":" in t for t in times)
    assert times[0] == "13:45:01"


def test_ai_recommendations_enhanced():
    data = client.get(f"/api/ai-sdlc/control-tower/tab/ai-recommendations{Q}").json()["data"]
    row = data["rows"][0]
    for k in (
        "application", "framework", "control_id", "control_name", "stage",
        "observation", "recommendation", "readiness_impact",
    ):
        assert k in row, k
    assert "readiness increases from" in row["readiness_impact"].lower()
    assert row.get("actionable") is True


def test_run_scheduler_ui_markup():
    html = client.get(f"/mvp/ai-sdlc/control-tower{Q}").text
    assert "ctRunSchedulerBtn" in html
    assert "ctDrillModal" in html


def test_tab_ids_complete():
    assert set(TAB_IDS) == {t[0] for t in TABS}
