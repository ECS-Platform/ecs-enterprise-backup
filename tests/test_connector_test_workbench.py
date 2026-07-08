"""Tests for the Connector Test Workbench (service + REST + UI).

Fully offline: the workbench reuses the existing integration adapters with an
INJECTED MOCK transport (no network). Verifies the 5 REST endpoints, the UI page,
the 11 target connectors' parser tests, safe error handling for unknown
connectors, and that no secret/mock-token value leaks into any output.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from modules.audit_intelligence.services import connector_workbench as wb

client = TestClient(app, follow_redirects=False)

#: The 11 enterprise connectors the workbench must be able to test.
TARGETS = ["sharepoint_graph", "teams_graph", "outlook_graph", "prisma_cloud",
           "jira", "confluence", "servicenow_cmdb", "sonarqube", "checkmarx", "tripwire"]


# --------------------------------------------------------------------------- #
# Service layer
# --------------------------------------------------------------------------- #
def test_list_connectors_includes_all_adapters():
    names = {c["name"] for c in wb.list_connectors()}
    for t in TARGETS:
        assert t in names, f"{t} missing from workbench connector list"
    assert "archer" in names  # 11th adapter also present


def test_config_status_masks_secrets():
    res = wb.config_status("jira")
    assert res["ok"] is True and "masked_config" in res
    assert "SET" in str(res["masked_config"]) or "MISSING" in str(res["masked_config"])


def test_config_status_unknown_connector():
    res = wb.config_status("nope")
    assert res["ok"] is False and res["error"] == "unknown_connector"


def test_health_check_never_raises():
    res = wb.health_check("servicenow_cmdb")
    assert "status" in res and "name" in res  # config-based; no live call


@pytest.mark.parametrize("name", TARGETS)
def test_parser_test_runs_with_mock_no_network(name):
    res = wb.parser_test(name)
    assert res["ok"] is True, f"{name} parser test failed: {res}"
    assert res["status"] == "ok"
    assert res["evidence_objects_detected"] >= 1
    assert isinstance(res["parser_output_preview"], list) and res["parser_output_preview"]
    assert res["method"]  # the real adapter method that was exercised


def test_parser_test_unknown_connector():
    res = wb.parser_test("nope")
    assert res["ok"] is False and res["error"] == "unknown_connector"


def test_dry_run_reports_would_call_no_network():
    res = wb.dry_run("prisma_cloud")
    assert res["ok"] is True and res["mode"] == "dry-run"
    assert res["would_call"] == "fetch_alerts"
    assert "No network call" in res["note"]


def test_no_mock_token_or_secret_in_service_output():
    import json
    blob = json.dumps(
        [wb.parser_test(n) for n in TARGETS]
        + [wb.config_status(n) for n in TARGETS]
        + [wb.dry_run(n) for n in TARGETS]
    )
    assert "WORKBENCH-MOCK" not in blob  # the mock token must never surface


# --------------------------------------------------------------------------- #
# REST endpoints
# --------------------------------------------------------------------------- #
def test_api_list_connectors():
    r = client.get("/api/connectors")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    # Count is dynamic (registry-driven) so adding connectors never breaks this.
    from modules.operations import integrations
    assert len(body["connectors"]) == len(integrations.list_adapters())
    assert len(body["connectors"]) >= 11  # the original enterprise set at minimum


def test_api_config_status():
    r = client.get("/api/connectors/sharepoint_graph/config-status")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_api_config_status_unknown_404():
    r = client.get("/api/connectors/does-not-exist/config-status")
    assert r.status_code == 404


def test_api_health_check_post():
    r = client.post("/api/connectors/jira/health-check")
    assert r.status_code == 200
    assert "status" in r.json()


def test_api_dry_run_post():
    r = client.post("/api/connectors/servicenow_cmdb/dry-run")
    assert r.status_code == 200
    assert r.json()["would_call"] == "fetch_servers"


@pytest.mark.parametrize("name", TARGETS)
def test_api_parser_test_post(name):
    r = client.post(f"/api/connectors/{name}/parser-test")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True and body["evidence_objects_detected"] >= 1


def test_api_parser_test_unknown_404():
    r = client.post("/api/connectors/nope/parser-test")
    assert r.status_code == 404


def test_api_outputs_never_leak_secret(monkeypatch):
    # Inject a distinctive secret; it must never appear in any workbench response.
    monkeypatch.setenv("ECS_JIRA_API_TOKEN", "LEAKCANARY_WB")
    monkeypatch.setenv("ECS_GRAPH_CLIENT_SECRET", "LEAKCANARY_WB")
    blob = (client.get("/api/connectors").text
            + client.get("/api/connectors/jira/config-status").text
            + client.post("/api/connectors/jira/parser-test").text
            + client.post("/api/connectors/sharepoint_graph/parser-test").text)
    assert "LEAKCANARY_WB" not in blob


# --------------------------------------------------------------------------- #
# UI page
# --------------------------------------------------------------------------- #
def test_ui_workbench_renders():
    r = client.get("/connectors/test-workbench?role=owner&user=UAT")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "Connector Test Workbench" in r.text
    assert 'id="cw-connector"' in r.text
    # Lists all connectors as options (registry-driven count).
    from modules.operations import integrations
    assert r.text.count("data-configured=") == len(integrations.list_adapters())


def test_ui_workbench_mvp_alias():
    r = client.get("/mvp/connectors/test-workbench")
    assert r.status_code == 200 and "Connector Test Workbench" in r.text


def test_ui_workbench_no_secret_in_html(monkeypatch):
    monkeypatch.setenv("ECS_GRAPH_CLIENT_SECRET", "LEAKCANARY_HTML")
    r = client.get("/connectors/test-workbench")
    assert "LEAKCANARY_HTML" not in r.text
