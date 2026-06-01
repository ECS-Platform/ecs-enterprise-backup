"""Module KPI drill API tests."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_module_kpi_drill_scheduler():
    resp = client.get("/api/module-kpi/drill?module=scheduler&metric=failed_collections&role=cio")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("ok") is True
    assert body.get("rows")


def test_module_kpi_drill_ai_ops():
    resp = client.get("/api/module-kpi/drill?module=ai_ops_assistant&metric=active_incidents&role=cio")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("ok") is True
    assert body.get("rows")
