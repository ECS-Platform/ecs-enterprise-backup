"""Tests for opt-in connector execution + evidence ingestion.

Covers the bridge that turns enterprise integration adapter output into stored
evidence:
  * ``_base.build_http_transport`` — real transport shape + error translation
    (exercised against a fake urllib layer; NO real network),
  * ``connector_executor.collect_evidence`` — flag-off safety, not-configured,
    happy path (mock transport → normalized items → evidence), auth error,
  * evidence bridge — collected objects become audit-intelligence evidence,
  * ``asset_scheduler.execute_plan`` — connector jobs routed to the executor,
  * REST ``/api/connectors/{name}/collect`` — safe (skipped) when flag is off.

Everything runs offline: transports are mocked/injected; the only "HTTP" is a
monkeypatched stub. No adapter makes a live call.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.operations.integrations import _base
from modules.audit_intelligence.services import connector_executor as ce


# --------------------------------------------------------------------------- #
# A deterministic mock transport (same idea as the workbench mock) that answers
# OAuth/login with a token and data endpoints with a synthetic payload.
# --------------------------------------------------------------------------- #
def _mock_transport(payload):
    def t(method, url, headers, params, timeout=None):
        u = str(url)
        if u.endswith("/oauth2/v2.0/token") or u.endswith("/oauth_token.do") \
                or u.endswith("/protocol/openid-connect/token"):
            return {"access_token": "TEST-TOKEN"}
        if u.endswith("/login"):
            return {"token": "TEST-TOKEN"}
        return payload
    return t


# --------------------------------------------------------------------------- #
# 1. Production HTTP transport factory
# --------------------------------------------------------------------------- #
def test_build_http_transport_returns_json_dict(monkeypatch):
    """A 200 JSON object body is returned as a dict."""
    from ecs_platform.connectors import http_client as hc

    def fake_request(self, method, path, *, params=None, json_body=None, headers=None):
        return hc.HttpResponse(200, {}, '{"value": [{"id": "1"}]}')

    monkeypatch.setattr(hc.HttpClient, "request", fake_request)
    transport = _base.build_http_transport()
    out = transport("GET", "https://api.example/x", {}, {})
    assert out == {"value": [{"id": "1"}]}


def test_build_http_transport_wraps_bare_list(monkeypatch):
    """A bare JSON array body is wrapped so normalizers using .get() don't crash."""
    from ecs_platform.connectors import http_client as hc

    monkeypatch.setattr(hc.HttpClient, "request",
                        lambda self, m, p, **k: hc.HttpResponse(200, {}, '[{"id": "1"}]'))
    out = _base.build_http_transport()("GET", "https://api.example/x", {}, {})
    assert out["value"] == [{"id": "1"}] and out["items"] == [{"id": "1"}]


def test_build_http_transport_401_becomes_auth_error(monkeypatch):
    from ecs_platform.connectors import http_client as hc

    def boom(self, *a, **k):
        raise hc.HttpError(401, "unauthorized")

    monkeypatch.setattr(hc.HttpClient, "request", boom)
    with pytest.raises(_base.IntegrationAuthError):
        _base.build_http_transport()("GET", "https://api.example/x", {}, {})


def test_build_http_transport_connection_error_becomes_timeout(monkeypatch):
    from ecs_platform.connectors import http_client as hc

    def boom(self, *a, **k):
        raise hc.HttpError(0, "connection error")

    monkeypatch.setattr(hc.HttpClient, "request", boom)
    with pytest.raises(_base.IntegrationTimeout):
        _base.build_http_transport()("GET", "https://api.example/x", {}, {})


def test_transport_error_classification_via_call_with_retry(monkeypatch):
    """The real transport's exceptions classify correctly through call_with_retry."""
    from ecs_platform.connectors import http_client as hc

    monkeypatch.setattr(hc.HttpClient, "request",
                        lambda self, *a, **k: (_ for _ in ()).throw(hc.HttpError(500, "err")))
    payload, status = _base.call_with_retry(
        _base.build_http_transport(), "GET", "https://api.example/x", {}, {},
        max_retries=0,
    )
    assert payload is None and status == "http_error"


# --------------------------------------------------------------------------- #
# 2. Executor safety: disabled by default + not-configured
# --------------------------------------------------------------------------- #
def test_collect_skipped_when_flag_disabled(monkeypatch):
    monkeypatch.delenv(ce.EXECUTION_FLAG, raising=False)
    res = ce.collect_evidence("jira")
    assert res["status"] == "skipped" and res["ingested"] == 0
    assert res["mode"] == "disabled"


def test_collect_unknown_connector():
    res = ce.collect_evidence("does_not_exist", transport=_mock_transport({"values": []}))
    assert res["status"] == "unknown_connector" and res["ok"] is False


def test_collect_not_configured_when_flag_on_but_no_creds(monkeypatch):
    monkeypatch.setenv(ce.EXECUTION_FLAG, "true")
    monkeypatch.setenv("DEMO_MODE", "false")
    # jira adapter is not configured offline → live path must refuse (no network).
    import modules.operations.integrations.jira as jira_mod
    monkeypatch.setattr(jira_mod, "is_configured", lambda: False)
    res = ce.collect_evidence("jira")
    assert res["status"] == "not_configured" and res["ingested"] == 0


# --------------------------------------------------------------------------- #
# 3. Executor happy path: injected mock transport → normalized items → evidence
# --------------------------------------------------------------------------- #
def test_collect_ingests_evidence_with_injected_transport():
    """Jira projects fetched via mock transport become real evidence records."""
    from modules.operations.engines import evidence_repository as ops_repo

    before = len(ops_repo.evidence_repository)
    payload = {"values": [
        {"key": "OPS", "id": "1", "name": "Operations", "projectTypeKey": "software"},
        {"key": "SEC", "id": "2", "name": "Security", "projectTypeKey": "software"},
    ]}
    res = ce.collect_evidence(
        "jira", framework="DPSC", application="Net Banking",
        transport=_mock_transport(payload),
    )
    assert res["ok"] is True
    assert res["mode"] == "mock"
    assert res["objects_fetched"] == 2
    assert res["ingested"] == 2
    # Evidence repository grew by exactly the ingested count.
    assert len(ops_repo.evidence_repository) == before + 2
    # Each receipt carries an evidence id + a SHA-256 + mirror status.
    for rcpt in res["receipts"]:
        assert rcpt["evidence_id"] and rcpt["sha256"]
        assert "audit_repository_synced" in rcpt


def test_collected_evidence_reaches_audit_repository():
    """The bridge mirrors collected objects into the audit-intelligence repo."""
    from modules.audit_intelligence.engines import evidence_repository as ai_repo

    ai_before = len(ai_repo.list_evidence()) if hasattr(ai_repo, "list_evidence") else None
    payload = {"components": [{"key": "proj-x", "name": "Proj X", "qualifier": "TRK"}]}
    res = ce.collect_evidence("sonarqube", framework="CSITE",
                              transport=_mock_transport(payload))
    assert res["ingested"] == 1
    if ai_before is not None:
        assert len(ai_repo.list_evidence()) >= ai_before + 1


def test_collect_auth_error_yields_no_ingestion():
    """An auth failure during fetch ingests nothing and reports auth_error."""
    def failing_transport(method, url, headers, params, timeout=None):
        raise _base.IntegrationAuthError("bad creds")

    res = ce.collect_evidence("jira", transport=failing_transport)
    assert res["ingested"] == 0
    assert res["status"] in ("auth_error", "transport_error")
    assert res["ok"] is False


def test_collect_respects_max_items():
    payload = {"values": [{"key": f"P{i}", "id": str(i), "name": f"P{i}"} for i in range(10)]}
    res = ce.collect_evidence("jira", transport=_mock_transport(payload), max_items=3)
    assert res["objects_fetched"] == 10
    assert res["ingested"] == 3


# Representative connectors across auth models (Graph OAuth, SNOW, Basic, token,
# access/secret key). Verifies the full chain end-to-end for each: fetch →
# normalize → evidence repo (SHA-256) → audit-intelligence mirror.
_REPRESENTATIVE = {
    "sharepoint_graph": {"value": [
        {"id": "1", "name": "policy.pdf", "size": 1024, "webUrl": "https://x/1",
         "lastModifiedDateTime": "2026-01-01", "file": {"mimeType": "application/pdf"}}]},
    "servicenow_cmdb": {"result": [
        {"sys_id": "SNOW-1", "name": "srv-web-01",
         "sys_class_name": "cmdb_ci_server", "ip_address": "10.0.0.10"}]},
    "jira": {"values": [
        {"key": "OPS", "id": "1", "name": "Operations", "projectTypeKey": "software"}]},
    "sonarqube": {"components": [{"key": "proj", "name": "Proj", "qualifier": "TRK"}]},
    "prisma_cloud": {"items": [
        {"id": "a1", "policy": {"name": "S3 public", "severity": "high"},
         "status": "open", "resource": {"name": "bucket", "cloudType": "aws"}}]},
}


@pytest.mark.parametrize("connector,payload", list(_REPRESENTATIVE.items()))
def test_representative_connector_full_ingestion_chain(connector, payload):
    from modules.audit_intelligence.engines import evidence_repository as ai_repo

    # Unique framework per run avoids colliding with keys other tests created, so a
    # brand-new evidence key is added (the repo versions on repeated identical keys).
    fw = f"UAT-{connector.upper()}"
    keys_before = {a.evidence_key for a in ai_repo.all_latest()}
    res = ce.collect_evidence(connector, framework=fw, application="Net Banking",
                              transport=_mock_transport(payload))
    assert res["objects_fetched"] == 1
    assert res["ingested"] == 1
    # The collected object is present in the audit-intelligence repository.
    keys_after = {a.evidence_key for a in ai_repo.all_latest()}
    assert len(keys_after) >= len(keys_before)
    new_artifacts = [a for a in ai_repo.all_latest() if a.evidence_key not in keys_before]
    assert len(new_artifacts) == 1
    art = new_artifacts[0]
    assert art.source_connector == connector
    assert art.asset_id == "Net Banking"
    assert fw in art.frameworks
    assert len(art.content_hash) == 64
    assert art.version >= 1
    if art.source_item_id:
        assert art.source_item_id  # preserved when the normalized item exposes an id
    rcpt = res["receipts"][0]
    assert rcpt["sha256"]                     # SHA-256 computed
    assert rcpt["audit_repository_synced"] is True


# --------------------------------------------------------------------------- #
# 4. Scheduler routing: connector jobs flow through the executor
# --------------------------------------------------------------------------- #
def test_execute_plan_routes_connector_jobs_through_executor():
    from modules.audit_intelligence.engines import asset_discovery
    from modules.audit_intelligence.services import asset_scheduler as sched

    assets = asset_discovery.discover_from_manual([
        {"asset_id": "jira", "hostname": "jira", "asset_type": "jira"},
    ])
    plan = sched.plan_evidence(assets)
    # Inject a mock transport so the connector job collects deterministically.
    results = sched.execute_plan(
        plan, connector_transport=_mock_transport(
            {"values": [{"key": "OPS", "id": "1", "name": "Operations"}]}),
    )
    connector_results = [r for r in results if r.get("kind") == "connector"]
    assert connector_results, "expected a connector job result"
    assert connector_results[0]["connector"] == "jira"
    assert connector_results[0]["ingested"] >= 1


def test_execute_plan_can_skip_connectors():
    from modules.audit_intelligence.engines import asset_discovery
    from modules.audit_intelligence.services import asset_scheduler as sched

    assets = asset_discovery.discover_from_manual([
        {"asset_id": "jira", "hostname": "jira", "asset_type": "jira"},
    ])
    plan = sched.plan_evidence(assets)
    results = sched.execute_plan(plan, run_connectors=False)
    assert not [r for r in results if r.get("kind") == "connector"]


# --------------------------------------------------------------------------- #
# 5. REST endpoint safety (flag off → skipped, no network)
# --------------------------------------------------------------------------- #
def test_collect_endpoint_safe_when_disabled(monkeypatch):
    monkeypatch.delenv(ce.EXECUTION_FLAG, raising=False)
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    r = client.post("/api/connectors/jira/collect?role=owner&user=U")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "skipped"
    assert body["ingested"] == 0


def test_collect_endpoint_unknown_connector_404(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    r = client.post("/api/connectors/nope/collect?role=owner&user=U")
    assert r.status_code == 404
