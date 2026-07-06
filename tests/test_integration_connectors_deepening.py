"""Deepening tests for the production integration connector skeletons.

Covers the seven "deepened" adapters (SharePoint/Graph, Jira, Confluence,
SonarQube, Checkmarx, Prisma Cloud, Tripwire) plus the shared ``_base`` machinery.

Guarantees exercised here:
  * NO real network calls — every transport is a local mock. The default skeleton
    transport is asserted to refuse live calls.
  * Secrets are never logged/exposed — masked_config uses SET/MISSING and the
    adapter ``repr`` never renders raw credentials.
  * Auth headers are assembled correctly (Basic / Bearer / x-redlock-auth) and are
    never placed into query params.
  * Consistent response shape ``{ok, source, status, items, errors}`` for success,
    not-configured, and classified transport failures.
  * Retry/backoff (bounded, non-retryable auth), timeout passthrough, and
    offset/page pagination behave deterministically.
"""

from __future__ import annotations

import base64
import os

os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

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
# Helpers
# --------------------------------------------------------------------------- #
STANDARD_KEYS = {"ok", "source", "status", "items", "errors"}


def _decode_basic(header_value: str) -> str:
    assert header_value.startswith("Basic ")
    return base64.b64decode(header_value.split(" ", 1)[1]).decode("utf-8")


def _configured_clients() -> list:
    """One fully-configured client per adapter (with a distinctive secret)."""
    return [
        sharepoint_graph.SharePointGraphClient(config={
            "base_url": "https://graph.example", "tenant_id": "TEN",
            "client_id": "CID", "client_secret": "SEC_GRAPH",
            "site_id": "SITE", "drive_id": "DRIVE", "access_token": "TOK_GRAPH",
            "timeout_sec": 7, "max_retries": 1}),
        jira.JiraClient(config={
            "base_url": "https://jira.example", "username": "u@x.com",
            "api_token": "SEC_JIRA", "timeout_sec": 7, "max_retries": 1}),
        confluence.ConfluenceClient(config={
            "base_url": "https://conf.example", "username": "u@x.com",
            "api_token": "SEC_CONF", "timeout_sec": 7, "max_retries": 1}),
        sonarqube.SonarQubeClient(config={
            "base_url": "https://sonar.example", "token": "SEC_SONAR",
            "timeout_sec": 7, "max_retries": 1}),
        checkmarx.CheckmarxClient(config={
            "base_url": "https://cx.example", "client_id": "CID",
            "client_secret": "SEC_CX", "access_token": "TOK_CX",
            "timeout_sec": 7, "max_retries": 1}),
        prisma_cloud.PrismaCloudClient(config={
            "base_url": "https://prisma.example", "access_key": "AK",
            "secret_key": "SEC_PRISMA", "token": "TOK_PRISMA",
            "timeout_sec": 7, "max_retries": 1}),
        tripwire.TripwireClient(config={
            "base_url": "https://tw.example", "username": "u",
            "password": "SEC_TW", "timeout_sec": 7, "max_retries": 1}),
    ]


ALL_MODULES = [
    sharepoint_graph, jira, confluence, sonarqube, checkmarx, prisma_cloud, tripwire,
]


# --------------------------------------------------------------------------- #
# _base: auth header builders
# --------------------------------------------------------------------------- #
def test_basic_auth_header_encodes_credentials():
    h = _base.basic_auth_header("alice", "pw123")
    assert _decode_basic(h["Authorization"]) == "alice:pw123"


def test_basic_auth_header_empty_when_missing():
    assert _base.basic_auth_header("", "pw") == {}
    assert _base.basic_auth_header("user", "") == {}
    assert _base.basic_auth_header(None, None) == {}


def test_bearer_auth_header():
    assert _base.bearer_auth_header("tok") == {"Authorization": "Bearer tok"}
    assert _base.bearer_auth_header("") == {}


def test_json_headers_merges_extra():
    h = _base.json_headers({"Authorization": "Bearer x"})
    assert h["Accept"] == "application/json"
    assert h["Authorization"] == "Bearer x"


# --------------------------------------------------------------------------- #
# _base: retry / backoff / timeout / classification
# --------------------------------------------------------------------------- #
def test_call_with_retry_success_first_try():
    calls = {"n": 0}

    def transport(method, url, headers, params):
        calls["n"] += 1
        return {"result": "ok"}

    payload, status = _base.call_with_retry(transport, "GET", "https://x", {}, {})
    assert status is None
    assert payload == {"result": "ok"}
    assert calls["n"] == 1


def test_call_with_retry_retries_then_succeeds():
    calls = {"n": 0}
    slept: list = []

    def transport(method, url, headers, params):
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("connection refused")
        return {"ok": True}

    payload, status = _base.call_with_retry(
        transport, "GET", "https://x", {}, {},
        max_retries=3, backoff_base=0.01, sleep=slept.append)
    assert status is None and payload == {"ok": True}
    assert calls["n"] == 3
    assert slept == [0.01, 0.02]  # exponential backoff, two sleeps before 3rd try


def test_call_with_retry_auth_not_retried():
    calls = {"n": 0}

    def transport(method, url, headers, params):
        calls["n"] += 1
        raise _base.IntegrationAuthError("401 unauthorized")

    payload, status = _base.call_with_retry(
        transport, "GET", "https://x", {}, {}, max_retries=5, backoff_base=1.0)
    assert payload is None and status == "auth_error"
    assert calls["n"] == 1  # never retried


def test_call_with_retry_exhausts_and_classifies():
    def transport(method, url, headers, params):
        raise TimeoutError("timed out")

    payload, status = _base.call_with_retry(
        transport, "GET", "https://x", {}, {}, max_retries=2, backoff_base=0.0)
    assert payload is None and status == "timeout"


def test_timeout_is_passed_only_to_supporting_transports():
    seen: dict = {}

    def transport_with_timeout(method, url, headers, params, timeout=None):
        seen["timeout"] = timeout
        return {"ok": True}

    _base.call_with_retry(
        transport_with_timeout, "GET", "https://x", {}, {}, timeout=13)
    assert seen["timeout"] == 13

    # A 4-arg mock must still be callable (no timeout kwarg forced on it).
    def transport_no_timeout(method, url, headers, params):
        seen["called"] = True
        return {"ok": True}

    payload, status = _base.call_with_retry(
        transport_no_timeout, "GET", "https://x", {}, {}, timeout=13)
    assert status is None and seen["called"] is True


@pytest.mark.parametrize("exc,expected", [
    (_base.IntegrationAuthError("x"), "auth_error"),
    (_base.IntegrationTimeout("x"), "timeout"),
    (TimeoutError("x"), "timeout"),
    (ConnectionError("connection refused"), "connection_error"),
    (RuntimeError("HTTP 500 error"), "http_error"),
    (ValueError("weird"), "transport_error"),
])
def test_classify_exception(exc, expected):
    assert _base.classify_exception(exc) == expected


# --------------------------------------------------------------------------- #
# _base: default transport refuses live calls; response builders
# --------------------------------------------------------------------------- #
def test_default_transport_refuses_live_call():
    t = _base._default_transport("sample")
    with pytest.raises(_base.IntegrationNotConfigured):
        t("GET", "https://x", {}, {})


def test_response_builders_shape():
    ok = _base.ok_response("s", [{"a": 1}])
    assert ok["ok"] is True and ok["status"] == "ok" and set(ok) == STANDARD_KEYS
    empty = _base.ok_response("s", [])
    assert empty["status"] == "empty"
    err = _base.error_response("s", "timeout", "boom")
    assert err["ok"] is False and err["errors"] == ["boom"] and set(err) == STANDARD_KEYS


# --------------------------------------------------------------------------- #
# Cross-adapter guarantees (parametrized over all 7 clients)
# --------------------------------------------------------------------------- #
def test_all_adapters_registered():
    from modules.operations.integrations import list_adapters

    registered = set(list_adapters())
    for mod in ALL_MODULES:
        assert mod.SOURCE in registered, f"{mod.SOURCE} not registered"


def test_all_clients_repr_never_leaks_secrets():
    for client in _configured_clients():
        r = repr(client)
        # None of the distinctive secret values may appear in the repr.
        for secret in ("SEC_GRAPH", "SEC_JIRA", "SEC_CONF", "SEC_SONAR",
                       "SEC_CX", "SEC_PRISMA", "SEC_TW", "TOK_GRAPH",
                       "TOK_CX", "TOK_PRISMA"):
            assert secret not in r, f"secret {secret} leaked in {r}"
        assert "SET" in r  # masked view is shown instead


def test_all_masked_configs_never_leak_secrets():
    for mod in ALL_MODULES:
        blob = str(mod.masked_config({}))  # empty cfg -> all MISSING, no secrets
        assert "SEC_" not in blob and "TOK_" not in blob


def test_all_clients_not_configured_returns_standard_response():
    empties = [
        sharepoint_graph.SharePointGraphClient(config={}),
        jira.JiraClient(config={}),
        confluence.ConfluenceClient(config={}),
        sonarqube.SonarQubeClient(config={}),
        checkmarx.CheckmarxClient(config={}),
        prisma_cloud.PrismaCloudClient(config={}),
        tripwire.TripwireClient(config={}),
    ]
    for client in empties:
        assert client.is_configured() is False
        hc = client.health_check()
        assert hc["ok"] is False and hc["status"] == "not_configured"
        assert hc["configured"] is False
        assert set(STANDARD_KEYS).issubset(hc)


def test_all_module_level_health_checks_not_configured(monkeypatch):
    # With no env configured, module-level health_check() must degrade gracefully.
    for var in list(os.environ):
        if var.startswith("ECS_") and var.endswith(
                ("_BASE_URL", "_TOKEN", "_API_TOKEN", "_CLIENT_ID",
                 "_CLIENT_SECRET", "_ACCESS_KEY", "_SECRET_KEY", "_PASSWORD",
                 "_USERNAME", "_TENANT_ID", "_SITE_ID", "_ACCESS_TOKEN")):
            monkeypatch.delenv(var, raising=False)
    for mod in ALL_MODULES:
        hc = mod.health_check()
        assert hc["status"] == "not_configured"
        assert hc["configured"] is False


# --------------------------------------------------------------------------- #
# SharePoint / Microsoft Graph
# --------------------------------------------------------------------------- #
def test_graph_masks_secrets(monkeypatch):
    monkeypatch.setenv("ECS_GRAPH_TENANT_ID", "ten")
    monkeypatch.setenv("ECS_GRAPH_CLIENT_ID", "cid")
    monkeypatch.setenv("ECS_GRAPH_CLIENT_SECRET", "supersecret")
    monkeypatch.setenv("ECS_GRAPH_SITE_ID", "site")
    mc = sharepoint_graph.masked_config()
    assert mc["client_secret"] == "SET" and mc["tenant_id"] == "SET"
    assert "supersecret" not in str(mc)


def test_graph_uses_configured_access_token_as_bearer():
    client = sharepoint_graph.SharePointGraphClient(config={
        "base_url": "https://graph", "tenant_id": "t", "client_id": "c",
        "client_secret": "s", "site_id": "sid", "access_token": "PRESET"})
    assert client.auth_headers() == {"Authorization": "Bearer PRESET"}


def test_graph_authenticate_exchanges_token_then_fetch_uses_bearer():
    captured = {"auth": None, "urls": []}

    def transport(method, url, headers, params, timeout=None):
        captured["urls"].append((method, url))
        if url.endswith("/oauth2/v2.0/token"):
            # secret must be in the token request body (params), never logged by us
            assert params["grant_type"] == "client_credentials"
            return {"access_token": "MINTED", "expires_in": 3600}
        captured["auth"] = headers.get("Authorization")
        return {"value": [
            {"id": "1", "name": "policy.pdf", "size": 10,
             "webUrl": "https://x/1", "lastModifiedDateTime": "2026-01-01"},
        ]}

    client = sharepoint_graph.SharePointGraphClient(
        config={"base_url": "https://graph", "tenant_id": "t", "client_id": "c",
                "client_secret": "s", "site_id": "sid", "timeout_sec": 5},
        transport=transport)
    # Explicit token exchange (production wiring pattern), then fetch.
    assert client.authenticate() == "MINTED"
    res = client.fetch_documents(page_size=100)
    assert res["ok"] is True and res["status"] == "ok"
    assert res["items"][0]["name"] == "policy.pdf"
    # The minted token was applied as a Bearer on the data request.
    assert captured["auth"] == "Bearer MINTED"


def test_graph_authenticate_cached_and_not_reattempted_on_failure():
    calls = {"token": 0}

    def transport(method, url, headers, params, timeout=None):
        if url.endswith("/oauth2/v2.0/token"):
            calls["token"] += 1
            return {}  # no access_token -> acquisition "fails"
        return {"value": []}

    client = sharepoint_graph.SharePointGraphClient(
        config={"base_url": "https://graph", "tenant_id": "t", "client_id": "c",
                "client_secret": "s", "site_id": "sid"},
        transport=transport)
    assert client.authenticate() is None
    assert client.authenticate() is None  # cached failure, no second exchange
    assert calls["token"] == 1
    # Without a token, no auth header is emitted (transport may handle its own).
    assert client.auth_headers() == {}


def test_graph_normalize_document():
    doc = sharepoint_graph.normalize_document(
        {"id": "9", "name": "f.docx", "size": 5, "folder": {}})
    assert doc["item_id"] == "9" and doc["is_folder"] is True
    assert doc["source"] == "sharepoint_graph"


# --------------------------------------------------------------------------- #
# Jira
# --------------------------------------------------------------------------- #
def test_jira_basic_auth_header_and_no_token_in_params():
    captured = {}

    def transport(method, url, headers, params, timeout=None):
        captured["auth"] = headers.get("Authorization")
        captured["params"] = params
        return {"issues": [
            {"key": "OPS-1", "fields": {"summary": "Do it",
                                        "status": {"name": "Open"},
                                        "assignee": {"displayName": "Ann"},
                                        "priority": {"name": "High"}}}]}

    client = jira.JiraClient(
        config={"base_url": "https://jira", "username": "u@x.com",
                "api_token": "TOKZ", "timeout_sec": 5},
        transport=transport)
    res = client.fetch_issues(jql="project=OPS")
    assert res["items"][0]["issue_key"] == "OPS-1"
    assert _decode_basic(captured["auth"]) == "u@x.com:TOKZ"
    assert "TOKZ" not in str(captured["params"])  # secret never in query params


def test_jira_fetch_single_issue():
    def transport(method, url, headers, params, timeout=None):
        assert url.endswith("/rest/api/2/issue/OPS-9")
        return {"key": "OPS-9", "fields": {"summary": "S"}}

    client = jira.JiraClient(
        config={"base_url": "https://jira", "username": "u", "api_token": "t"},
        transport=transport)
    res = client.fetch_issue("OPS-9")
    assert res["ok"] is True and res["items"][0]["issue_key"] == "OPS-9"


def test_jira_fetch_issue_requires_key():
    client = jira.JiraClient(
        config={"base_url": "https://jira", "username": "u", "api_token": "t"},
        transport=lambda *a, **k: {})
    res = client.fetch_issue("")
    assert res["ok"] is False


def test_jira_fetch_not_configured():
    res = jira.JiraClient(config={}).fetch_issues()
    assert res["status"] == "not_configured" and res["ok"] is False


def test_jira_transport_error_is_classified():
    def transport(method, url, headers, params, timeout=None):
        raise TimeoutError("timed out")

    client = jira.JiraClient(
        config={"base_url": "https://jira", "username": "u", "api_token": "t",
                "max_retries": 0},
        transport=transport)
    res = client.fetch_issues()
    assert res["ok"] is False and res["status"] == "timeout"


# --------------------------------------------------------------------------- #
# Confluence
# --------------------------------------------------------------------------- #
def test_confluence_basic_auth_and_fetch():
    captured = {}

    def transport(method, url, headers, params, timeout=None):
        captured["auth"] = headers.get("Authorization")
        return {"results": [
            {"id": "100", "title": "Policy", "type": "page",
             "space": {"key": "SEC"}, "status": "current"}]}

    client = confluence.ConfluenceClient(
        config={"base_url": "https://conf", "username": "u@x.com",
                "api_token": "CTOK"},
        transport=transport)
    res = client.fetch_pages(space_key="SEC")
    assert res["items"][0]["page_id"] == "100"
    assert res["items"][0]["space"] == "SEC"
    assert _decode_basic(captured["auth"]) == "u@x.com:CTOK"


def test_confluence_not_configured():
    assert confluence.ConfluenceClient(config={}).fetch_pages()["status"] == "not_configured"


# --------------------------------------------------------------------------- #
# SonarQube
# --------------------------------------------------------------------------- #
def test_sonarqube_token_is_basic_username_empty_password():
    captured = {}

    def transport(method, url, headers, params, timeout=None):
        captured["auth"] = headers.get("Authorization")
        return {"issues": [
            {"key": "AY", "rule": "java:S1", "severity": "MAJOR",
             "type": "BUG", "component": "proj:File.java", "status": "OPEN"}]}

    client = sonarqube.SonarQubeClient(
        config={"base_url": "https://sonar", "token": "SQ"},
        transport=transport)
    res = client.fetch_issues(project_key="proj")
    assert res["items"][0]["issue_key"] == "AY"
    assert _decode_basic(captured["auth"]) == "SQ:"  # token as user, empty pw


def test_sonarqube_quality_gate():
    def transport(method, url, headers, params, timeout=None):
        assert "api/qualitygates/project_status" in url
        return {"projectStatus": {"status": "OK", "conditions": [{}, {}]}}

    client = sonarqube.SonarQubeClient(
        config={"base_url": "https://sonar", "token": "SQ"},
        transport=transport)
    res = client.fetch_quality_gate("proj")
    assert res["items"][0]["status"] == "OK"
    assert res["items"][0]["conditions"] == 2


def test_sonarqube_paginates_pages():
    # Page index is 1-based (p = offset // limit + 1); verify two pages collected.
    pages = {
        1: {"issues": [{"key": f"I{i}"} for i in range(2)]},
        2: {"issues": [{"key": "I2"}]},  # short page -> stop
    }
    seen_pages: list = []

    def transport(method, url, headers, params, timeout=None):
        p = params["p"]
        seen_pages.append(p)
        return pages.get(p, {"issues": []})

    client = sonarqube.SonarQubeClient(
        config={"base_url": "https://sonar", "token": "SQ"},
        transport=transport)
    res = client.fetch_issues(page_size=2)
    assert seen_pages[:2] == [1, 2]
    assert len(res["items"]) == 3


# --------------------------------------------------------------------------- #
# Checkmarx
# --------------------------------------------------------------------------- #
def test_checkmarx_token_exchange_and_scan_fetch():
    captured = {"auth": None}

    def transport(method, url, headers, params, timeout=None):
        if url.endswith("/protocol/openid-connect/token"):
            assert params["grant_type"] == "client_credentials"
            return {"access_token": "CXMINT"}
        captured["auth"] = headers.get("Authorization")
        return {"scans": [
            {"id": "s1", "projectId": "p1", "status": "Completed",
             "statusDetails": {"highSeverity": 2, "mediumSeverity": 1,
                               "lowSeverity": 0}}]}

    client = checkmarx.CheckmarxClient(
        config={"base_url": "https://cx", "client_id": "c",
                "client_secret": "s"},
        transport=transport)
    assert client.authenticate() == "CXMINT"
    res = client.fetch_scans(project_id="p1")
    assert res["items"][0]["scan_id"] == "s1" and res["items"][0]["high"] == 2
    assert captured["auth"] == "Bearer CXMINT"


def test_checkmarx_preset_token():
    client = checkmarx.CheckmarxClient(config={
        "base_url": "https://cx", "client_id": "c", "client_secret": "s",
        "access_token": "PRE"})
    assert client.auth_headers() == {"Authorization": "Bearer PRE"}


# --------------------------------------------------------------------------- #
# Prisma Cloud
# --------------------------------------------------------------------------- #
def test_prisma_login_and_alert_fetch():
    captured = {"redlock": None}

    def transport(method, url, headers, params, timeout=None):
        if url.endswith("/login"):
            assert params["username"] and params["password"]
            return {"token": "PJWT"}
        captured["redlock"] = headers.get("x-redlock-auth")
        return {"items": [
            {"id": "a1", "policy": {"name": "S3 public", "severity": "high"},
             "status": "open", "resource": {"name": "bucket", "cloudType": "aws"}}]}

    client = prisma_cloud.PrismaCloudClient(
        config={"base_url": "https://prisma", "access_key": "ak",
                "secret_key": "sk"},
        transport=transport)
    assert client.authenticate() == "PJWT"
    res = client.fetch_alerts()
    assert res["items"][0]["alert_id"] == "a1"
    assert res["items"][0]["cloud_type"] == "aws"
    assert captured["redlock"] == "PJWT"


def test_prisma_preset_token_header():
    client = prisma_cloud.PrismaCloudClient(config={
        "base_url": "https://prisma", "access_key": "ak", "secret_key": "sk",
        "token": "PRE"})
    assert client.auth_headers() == {"x-redlock-auth": "PRE"}


# --------------------------------------------------------------------------- #
# Tripwire
# --------------------------------------------------------------------------- #
def test_tripwire_basic_auth_and_policy_fetch():
    captured = {}

    def transport(method, url, headers, params, timeout=None):
        captured["auth"] = headers.get("Authorization")
        return {"results": [
            {"id": "P1", "name": "CIS", "node": "srv-1",
             "status": "pass", "score": 98}]}

    client = tripwire.TripwireClient(
        config={"base_url": "https://tw", "username": "u", "password": "PW"},
        transport=transport)
    res = client.fetch_policy_results()
    assert res["items"][0]["policy_id"] == "P1"
    assert _decode_basic(captured["auth"]) == "u:PW"


def test_tripwire_pagination_stops_on_short_page():
    calls = {"n": 0}

    def transport(method, url, headers, params, timeout=None):
        calls["n"] += 1
        # First full page then a short page -> pagination stops.
        if params["offset"] == 0:
            return {"results": [{"id": str(i)} for i in range(100)]}
        return {"results": [{"id": "x"}]}

    client = tripwire.TripwireClient(
        config={"base_url": "https://tw", "username": "u", "password": "PW"},
        transport=transport)
    res = client.fetch_policy_results(page_size=100)
    assert len(res["items"]) == 101
    assert calls["n"] == 2
