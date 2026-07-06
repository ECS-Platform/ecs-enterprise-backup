"""Mocked tests for all enterprise integration adapters.

No live systems, no network. Every adapter is exercised with an injected mock
transport (or config-only for the two skeleton-alias adapters). Covers: config +
masking (no secret leakage), is_configured, health_check, fetch_* normalization,
not-configured behavior, and error classification (timeout/auth/retry).
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.operations import integrations as I
from modules.operations.integrations import _base
from modules.operations.integrations import (
    checkmarx,
    confluence,
    jira,
    prisma_cloud,
    sharepoint_graph,
    sonarqube,
    tripwire,
)


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #
def test_registry_lists_nine_adapters():
    names = I.list_adapters()
    assert len(names) == 9
    for expected in ("servicenow_cmdb", "archer", "sharepoint_graph", "jira",
                     "confluence", "sonarqube", "checkmarx", "prisma_cloud", "tripwire"):
        assert expected in names


def test_health_check_all_no_config_graceful(monkeypatch):
    _clear_integration_env(monkeypatch)
    h = I.health_check_all()
    assert h["total"] == 9
    assert h["configured"] == 0
    assert all(not r["configured"] for r in h["adapters"].values())
    assert all(r["status"] == "not_configured" for r in h["adapters"].values())


def test_masked_config_all_never_leaks_secrets(monkeypatch):
    # Set fake secrets; masked view must show SET/MISSING only, never the value.
    monkeypatch.setenv("ECS_JIRA_API_TOKEN", "super-secret-token")
    monkeypatch.setenv("ECS_PRISMA_CLOUD_SECRET_KEY", "prisma-secret")
    mc = I.masked_config_all()
    blob = repr(mc)
    assert "super-secret-token" not in blob
    assert "prisma-secret" not in blob


def _clear_integration_env(monkeypatch):
    for k in list(os.environ):
        if k.startswith(("ECS_JIRA", "ECS_CONFLUENCE", "ECS_SONARQUBE", "ECS_CHECKMARX",
                         "ECS_PRISMA", "ECS_TRIPWIRE", "ECS_GRAPH", "ECS_SERVICENOW", "ECS_ARCHER")):
            monkeypatch.delenv(k, raising=False)


# --------------------------------------------------------------------------- #
# Per-adapter: configured fetch via mock transport
# --------------------------------------------------------------------------- #
def test_jira_fetch_normalizes():
    tp = lambda m, u, h, p: {"issues": [{"key": "J-1", "fields": {
        "summary": "Fix TLS", "status": {"name": "Open"}, "priority": {"name": "High"}}}]}
    c = jira.JiraClient(config={"base_url": "https://j", "username": "u", "api_token": "t",
                                "timeout_sec": 5}, transport=tp)
    r = c.fetch_issues(jql="project=X")
    assert r["ok"] and r["source"] == "jira" and len(r["items"]) == 1
    assert r["items"][0]["issue_key"] == "J-1"
    assert r["items"][0]["status"] == "Open"


def test_confluence_fetch_normalizes():
    tp = lambda m, u, h, p: {"results": [{"id": "1", "title": "Policy", "type": "page",
                                          "space": {"key": "SEC"}, "status": "current"}]}
    c = confluence.ConfluenceClient(config={"base_url": "https://c", "username": "u",
                                            "api_token": "t"}, transport=tp)
    r = c.fetch_pages(space_key="SEC")
    assert r["ok"] and r["items"][0]["space"] == "SEC"


def test_sonarqube_fetch_and_quality_gate():
    tp = lambda m, u, h, p: {"issues": [{"key": "S-1", "rule": "r", "severity": "MAJOR",
                                         "type": "VULNERABILITY", "status": "OPEN"}]}
    c = sonarqube.SonarQubeClient(config={"base_url": "https://s", "token": "t"}, transport=tp)
    r = c.fetch_issues(project_key="app")
    assert r["ok"] and r["items"][0]["severity"] == "MAJOR"
    tp2 = lambda m, u, h, p: {"projectStatus": {"status": "ERROR", "conditions": [{}, {}]}}
    c2 = sonarqube.SonarQubeClient(config={"base_url": "https://s", "token": "t"}, transport=tp2)
    q = c2.fetch_quality_gate("app")
    assert q["ok"] and q["items"][0]["status"] == "ERROR" and q["items"][0]["conditions"] == 2


def test_checkmarx_fetch_normalizes():
    tp = lambda m, u, h, p: {"scans": [{"id": "sc1", "projectId": "p1", "status": "Completed",
                                        "summary": {"high": 2, "medium": 5, "low": 9}}]}
    c = checkmarx.CheckmarxClient(config={"base_url": "https://x", "client_id": "i",
                                          "client_secret": "s"}, transport=tp)
    r = c.fetch_scans(project_id="p1")
    assert r["ok"] and r["items"][0]["high"] == 2


def test_prisma_cloud_fetch_normalizes():
    tp = lambda m, u, h, p: {"items": [{"id": "a1", "policy": {"name": "Public S3", "severity": "high"},
                                        "status": "open", "resource": {"name": "bucket", "cloudType": "aws"}}]}
    c = prisma_cloud.PrismaCloudClient(config={"base_url": "https://p", "access_key": "a",
                                               "secret_key": "s"}, transport=tp)
    r = c.fetch_alerts()
    assert r["ok"] and r["items"][0]["cloud_type"] == "aws"


def test_tripwire_fetch_normalizes():
    tp = lambda m, u, h, p: {"results": [{"id": "t1", "name": "CIS", "node": "srv1",
                                          "status": "pass", "score": 98}]}
    c = tripwire.TripwireClient(config={"base_url": "https://t", "username": "u",
                                        "password": "p"}, transport=tp)
    r = c.fetch_policy_results()
    assert r["ok"] and r["items"][0]["policy_name"] == "CIS"


def test_sharepoint_graph_fetch_normalizes():
    tp = lambda m, u, h, p: {"value": [{"id": "d1", "name": "evidence.pdf", "size": 1024,
                                        "lastModifiedDateTime": "2026-01-01T00:00:00Z", "webUrl": "https://x"}]}
    c = sharepoint_graph.SharePointGraphClient(config={"base_url": "https://graph", "tenant_id": "t",
        "client_id": "c", "client_secret": "s", "site_id": "site", "drive_id": "drv"}, transport=tp)
    r = c.fetch_documents()
    assert r["ok"] and r["items"][0]["name"] == "evidence.pdf"


# --------------------------------------------------------------------------- #
# Not-configured + error classification (representative adapter)
# --------------------------------------------------------------------------- #
def test_not_configured_returns_standard_shape():
    r = jira.JiraClient(config={"base_url": "", "username": "", "api_token": ""}).fetch_issues()
    assert r == {"ok": False, "source": "jira", "status": "not_configured",
                 "items": [], "errors": r["errors"]}
    assert r["errors"]


def test_timeout_classified():
    def tp(m, u, h, p):
        raise TimeoutError("read timed out")
    r = jira.JiraClient(config={"base_url": "https://j", "username": "u", "api_token": "t"},
                        transport=tp).fetch_issues()
    assert r["status"] == "timeout" and not r["ok"]


def test_auth_error_not_retried():
    attempts = {"n": 0}

    def tp(m, u, h, p):
        attempts["n"] += 1
        raise _base.IntegrationAuthError("401 Unauthorized")

    r = sonarqube.SonarQubeClient(config={"base_url": "https://s", "token": "t"},
                                  transport=tp).fetch_issues()
    assert r["status"] == "auth_error"
    assert attempts["n"] == 1  # not retried


def test_connection_error_retried():
    attempts = {"n": 0}

    def tp(m, u, h, p):
        attempts["n"] += 1
        raise ConnectionError("connection refused")

    payload, status = _base.call_with_retry(tp, "GET", "u", {}, {}, max_retries=2, backoff_base=0)
    assert status == "connection_error"
    assert attempts["n"] == 3  # 1 + 2 retries


def test_pagination_stops_on_short_page():
    calls = {"n": 0}

    def tp(m, u, h, p):
        calls["n"] += 1
        off = p.get("offset", 0)
        return {"items": [{"id": i} for i in range(2)]} if off < 4 else {"items": [{"id": "z"}]}

    c = prisma_cloud.PrismaCloudClient(config={"base_url": "https://p", "access_key": "a",
                                               "secret_key": "s"}, transport=tp)
    r = c.fetch_alerts(page_size=2, max_items=100)
    assert r["ok"] and len(r["items"]) == 5 and calls["n"] == 3


def test_health_check_configured_reports_ok():
    tp = lambda m, u, h, p: {"status": "UP"}
    c = sonarqube.SonarQubeClient(config={"base_url": "https://s", "token": "t"}, transport=tp)
    h = c.health_check()
    assert h["ok"] and h["configured"] and h["status"] == "ok"
    assert "masked_config" in h


def test_health_check_not_configured():
    h = jira.JiraClient(config={"base_url": "", "username": "", "api_token": ""}).health_check()
    assert not h["ok"] and h["configured"] is False and h["status"] == "not_configured"


# --------------------------------------------------------------------------- #
# Existing adapters keep their standard interface (aliases)
# --------------------------------------------------------------------------- #
def test_existing_adapters_expose_standard_interface():
    from modules.operations.integrations import archer, servicenow_cmdb

    for mod in (archer, servicenow_cmdb):
        assert callable(mod.get_config)
        assert callable(mod.is_configured)
        assert callable(mod.masked_config)
        assert callable(mod.health_check)
        mc = mod.masked_config()
        assert "ready" in mc
        h = mod.health_check()
        assert "status" in h and "masked_config" in h
