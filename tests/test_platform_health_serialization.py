"""Regression tests for /api/platform/health JSON serialization.

Guards against: "TypeError: Object of type datetime is not JSON serializable"
caused by PostgreSQL TIMESTAMPTZ columns (sync_runs/audit) flowing into JSONResponse.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from ecs_platform.ingestion import health_overview, to_jsonable

client = TestClient(app, raise_server_exceptions=False)


def test_to_jsonable_converts_nested_datetimes():
    now = datetime(2026, 6, 11, 13, 46, 48, tzinfo=timezone.utc)
    payload = {
        "sync_runs": [{"connector": "gitea", "started_at": now, "finished_at": now, "ok": True}],
        "audit": [{"actor": "Admin", "created_at": now, "detail": {"when": date(2026, 6, 11)}}],
        "counts": {"score": Decimal("0.95")},
        "nested": {"list": [{"ts": now}]},
    }
    clean = to_jsonable(payload)
    # Must be JSON-serializable without a custom encoder.
    text = json.dumps(clean)
    assert "2026-06-11T13:46:48+00:00" in text
    assert clean["sync_runs"][0]["started_at"] == now.isoformat()
    assert clean["audit"][0]["detail"]["when"] == "2026-06-11"
    assert clean["counts"]["score"] == 0.95
    assert clean["nested"]["list"][0]["ts"] == now.isoformat()


def test_health_overview_is_json_serializable():
    # Whether or not the DB is reachable, the result must serialize cleanly.
    overview = health_overview()
    json.dumps(overview)  # raises if any datetime/Decimal leaked through
    assert "connectors" in overview and "repository_ok" in overview


def test_platform_health_endpoint_returns_valid_json():
    resp = client.get("/api/platform/health")
    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()  # raises if body is not valid JSON
    assert isinstance(body["connectors"], list)
    assert "repository_ok" in body
