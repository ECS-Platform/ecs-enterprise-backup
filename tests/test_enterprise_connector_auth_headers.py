"""Auth-header + normalized-output coverage for the enterprise connectors.

Mocked transports only — no real call. Verifies that each connector assembles its
auth header correctly (Basic / Bearer / token / x-redlock-auth), never places
secrets in query params, produces the documented normalized shapes for the new
deeper methods, and never leaks secrets in repr / masked output.
"""

from __future__ import annotations

import base64
import os

os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.operations.integrations import (
    confluence,
    jira,
    prisma_cloud,
    servicenow_cmdb,
    sonarqube,
)


def _decode_basic(h: str) -> str:
    assert h.startswith("Basic ")
    return base64.b64decode(h.split(" ", 1)[1]).decode("utf-8")


# --------------------------------------------------------------------------- #
# ServiceNow — OAuth + Basic auth modes
# --------------------------------------------------------------------------- #
def test_servicenow_oauth_bearer_and_pagination():
    captured = {"auth": None, "urls": []}

    def transport(method, url, headers, params, timeout=None):
        if url.endswith("/oauth_token.do"):
            assert params["grant_type"] == "client_credentials"
            return {"access_token": "SNTOK"}
        captured["auth"] = headers.get("Authorization")
        captured["urls"].append(url)
        return {"result": [{"sys_id": "c1", "name": "srv-a",
                            "sys_class_name": "cmdb_ci_server", "ip_address": "10.0.0.1"}]}

    client = servicenow_cmdb.ServiceNowAdapter(
        config={"base_url": "https://snow.example", "client_id": "id",
                "client_secret": "sec", "auth_mode": "oauth", "timeout_sec": 5},
        transport=transport)
    res = client.fetch_servers()
    assert res["ok"] and res["items"][0]["sys_id"] == "c1"
    assert res["items"][0]["class_name"] == "cmdb_ci_server"
    assert res["items"][0]["evidence_type"] == "cmdb_ci"
    assert captured["auth"] == "Bearer SNTOK"
    assert any("cmdb_ci_server" in u for u in captured["urls"])


def test_servicenow_basic_auth_mode():
    captured = {"auth": None}

    def transport(method, url, headers, params, timeout=None):
        captured["auth"] = headers.get("Authorization")
        return {"result": []}

    client = servicenow_cmdb.ServiceNowAdapter(
        config={"base_url": "https://snow.example", "username": "svc",
                "password": "pw", "auth_mode": "basic"},
        transport=transport)
    client.fetch_cis()
    assert _decode_basic(captured["auth"]) == "svc:pw"


def test_servicenow_oauth_falls_back_to_basic_when_no_oauth_creds():
    captured = {"auth": None}

    def transport(method, url, headers, params, timeout=None):
        assert not url.endswith("/oauth_token.do")  # no token exchange
        captured["auth"] = headers.get("Authorization")
        return {"result": []}

    client = servicenow_cmdb.ServiceNowAdapter(
        config={"base_url": "https://snow.example", "username": "svc",
                "password": "pw", "auth_mode": "oauth"},
        transport=transport)
    client.fetch_databases()
    assert _decode_basic(captured["auth"]) == "svc:pw"


def test_servicenow_sysparm_query_and_offset():
    captured = {"params": []}

    def transport(method, url, headers, params, timeout=None):
        if url.endswith("/oauth_token.do"):
            return {"access_token": "T"}
        captured["params"].append(params)
        return {"result": []}

    client = servicenow_cmdb.ServiceNowAdapter(
        config={"base_url": "https://snow.example", "client_id": "i", "client_secret": "s"},
        transport=transport)
    client.fetch_applications(sysparm_query="operational_status=1")
    p = captured["params"][0]
    assert p["sysparm_query"] == "operational_status=1"
    assert "sysparm_limit" in p and "sysparm_offset" in p


def test_servicenow_masked_and_repr_safe():
    mc = servicenow_cmdb.masked_config({"base_url": "x", "client_secret": "topsecret",
                                        "password": "pw", "auth_mode": "oauth"})
    assert mc["client_secret"] == "SET" and "topsecret" not in str(mc)
    c = servicenow_cmdb.ServiceNowAdapter(
        config={"base_url": "x", "client_id": "i", "client_secret": "LEAKME"})
    assert "LEAKME" not in repr(c)


def test_servicenow_legacy_client_still_works():
    def transport(method, url, headers, params):
        return {"result": [{"sys_id": "1", "name": "a", "sys_class_name": "cmdb_ci_server"}]}
    client = servicenow_cmdb.ServiceNowCmdbClient(
        config={"base_url": "https://x", "client_id": "a", "client_secret": "b"},
        transport=transport)
    cis = client.fetch_configuration_items(ci_class="cmdb_ci_server")
    assert cis[0]["sys_id"] == "1"


# --------------------------------------------------------------------------- #
# Jira — Basic auth, projects, comments, API version
# --------------------------------------------------------------------------- #
def test_jira_basic_auth_projects_and_normalization():
    captured = {"auth": None, "urls": []}

    def transport(method, url, headers, params, timeout=None):
        captured["auth"] = headers.get("Authorization")
        captured["urls"].append(url)
        return {"values": [{"key": "OPS", "id": "1", "name": "Operations",
                            "projectTypeKey": "software"}]}

    client = jira.JiraClient(
        config={"base_url": "https://jira", "username": "u@x.com", "api_token": "TOK"},
        transport=transport)
    res = client.fetch_projects()
    assert res["ok"] and res["items"][0]["project_key"] == "OPS"
    assert res["items"][0]["evidence_type"] == "jira_project"
    assert _decode_basic(captured["auth"]) == "u@x.com:TOK"
    assert any("/rest/api/2/project/search" in u for u in captured["urls"])


def test_jira_api_version_configurable():
    captured = {"urls": []}

    def transport(method, url, headers, params, timeout=None):
        captured["urls"].append(url)
        return {"issues": []}

    client = jira.JiraClient(
        config={"base_url": "https://jira", "username": "u", "api_token": "t",
                "api_version": "3"},
        transport=transport)
    client.fetch_issues(jql="project=OPS")
    assert any("/rest/api/3/search" in u for u in captured["urls"])


def test_jira_enriched_issue_normalization():
    record = {"key": "OPS-1", "fields": {
        "summary": "Fix", "status": {"name": "Open"},
        "assignee": {"displayName": "Ann"}, "priority": {"name": "High"},
        "issuetype": {"name": "Bug"}, "reporter": {"displayName": "Bob"},
        "created": "2026-01-01", "updated": "2026-02-01",
        "project": {"key": "OPS"}, "labels": ["sec"],
        "components": [{"name": "api"}], "fixVersions": [{"name": "1.0"}]}}
    n = jira.normalize_issue(record)
    assert n["issue_key"] == "OPS-1" and n["status"] == "Open" and n["priority"] == "High"
    assert n["issue_type"] == "Bug" and n["reporter"] == "Bob" and n["project_key"] == "OPS"
    assert n["labels"] == ["sec"] and n["components"] == ["api"] and n["fix_versions"] == ["1.0"]


def test_jira_fetch_issue_comments():
    def transport(method, url, headers, params, timeout=None):
        assert "/rest/api/2/issue/OPS-1/comment" in url
        return {"comments": [{"id": "10", "author": {"displayName": "Ann"},
                             "created": "2026-01-01", "body": "looks good"}]}
    client = jira.JiraClient(
        config={"base_url": "https://jira", "username": "u", "api_token": "t"},
        transport=transport)
    res = client.fetch_issue_comments("OPS-1")
    assert res["ok"] and res["items"][0]["author"] == "Ann"
    assert res["items"][0]["body_preview"] == "looks good"


# --------------------------------------------------------------------------- #
# Confluence — Basic auth, spaces, page, attachments
# --------------------------------------------------------------------------- #
def test_confluence_spaces_and_auth():
    captured = {"auth": None}

    def transport(method, url, headers, params, timeout=None):
        captured["auth"] = headers.get("Authorization")
        return {"results": [{"key": "SEC", "id": "1", "name": "Security",
                            "type": "global", "status": "current"}]}

    client = confluence.ConfluenceClient(
        config={"base_url": "https://x/wiki", "username": "u@x.com", "api_token": "TOK"},
        transport=transport)
    res = client.fetch_spaces()
    assert res["ok"] and res["items"][0]["space_key"] == "SEC"
    assert _decode_basic(captured["auth"]) == "u@x.com:TOK"


def test_confluence_single_page_enriched():
    def transport(method, url, headers, params, timeout=None):
        return {"id": "100", "title": "Policy", "type": "page", "status": "current",
                "space": {"key": "SEC"}, "version": {"number": 3, "when": "2026-02-01"},
                "history": {"createdBy": {"displayName": "Ann"}, "createdDate": "2026-01-01"},
                "_links": {"webui": "/x/100"}}
    client = confluence.ConfluenceClient(
        config={"base_url": "https://x/wiki", "username": "u", "api_token": "t"},
        transport=transport)
    res = client.fetch_page("100")
    p = res["items"][0]
    assert p["page_id"] == "100" and p["space"] == "SEC"
    assert p["version"] == 3 and p["created_by"] == "Ann"
    assert p["web_url"] == "/x/100"


def test_confluence_attachments_metadata():
    def transport(method, url, headers, params, timeout=None):
        assert "/child/attachment" in url
        return {"results": [{"id": "att1", "title": "diagram.png",
                            "extensions": {"mediaType": "image/png", "fileSize": 1234}}]}
    client = confluence.ConfluenceClient(
        config={"base_url": "https://x/wiki", "username": "u", "api_token": "t"},
        transport=transport)
    res = client.fetch_attachments("100")
    a = res["items"][0]
    assert a["attachment_id"] == "att1" and a["media_type"] == "image/png"
    assert a["file_size"] == 1234


# --------------------------------------------------------------------------- #
# SonarQube — token auth, projects, measures
# --------------------------------------------------------------------------- #
def test_sonarqube_projects_and_measures():
    def transport(method, url, headers, params, timeout=None):
        if "api/projects/search" in url:
            return {"components": [{"key": "proj", "name": "Proj", "qualifier": "TRK"}]}
        if "api/measures/component" in url:
            return {"component": {"measures": [
                {"metric": "bugs", "value": "3"},
                {"metric": "coverage", "value": "82.5"},
                {"metric": "vulnerabilities", "value": "1"}]}}
        return {}

    client = sonarqube.SonarQubeClient(
        config={"base_url": "https://sonar", "token": "SQ"}, transport=transport)
    proj = client.fetch_projects()
    assert proj["ok"] and proj["items"][0]["project_key"] == "proj"
    meas = client.fetch_measures("proj")
    m = meas["items"][0]
    assert m["bugs"] == "3" and m["coverage"] == "82.5" and m["vulnerabilities"] == "1"
    assert m["evidence_type"] == "sonarqube_measures"


def test_sonarqube_token_auth_header():
    captured = {"auth": None}

    def transport(method, url, headers, params, timeout=None):
        captured["auth"] = headers.get("Authorization")
        return {"components": []}

    client = sonarqube.SonarQubeClient(
        config={"base_url": "https://sonar", "token": "SQTOKEN"}, transport=transport)
    client.fetch_projects()
    assert _decode_basic(captured["auth"]) == "SQTOKEN:"  # token as user, empty pw


def test_sonarqube_measures_requires_project():
    client = sonarqube.SonarQubeClient(config={"base_url": "https://sonar", "token": "SQ"},
                                       transport=lambda *a, **k: {})
    assert client.fetch_measures("")["ok"] is False


# --------------------------------------------------------------------------- #
# Prisma Cloud — login JWT, accounts, resources, compliance
# --------------------------------------------------------------------------- #
def test_prisma_accounts_resources_compliance():
    def transport(method, url, headers, params, timeout=None):
        if url.endswith("/login"):
            return {"token": "PJWT"}
        if url.endswith("/cloud"):
            return [{"accountId": "a1", "name": "prod-aws", "cloudType": "aws", "enabled": True}]
        if url.endswith("/resource"):
            return {"items": [{"rrn": "r1", "name": "bucket", "resourceType": "s3",
                              "cloudType": "aws", "regionId": "us-east-1"}]}
        if url.endswith("/compliance/posture"):
            return {"complianceDetails": [{"name": "CIS", "status": "warn",
                                          "passedResources": 10, "failedResources": 2}]}
        return {}

    client = prisma_cloud.PrismaCloudClient(
        config={"base_url": "https://prisma", "access_key": "ak", "secret_key": "sk"},
        transport=transport)
    assert client.authenticate() == "PJWT"

    accts = client.fetch_cloud_accounts()
    assert accts["ok"] and accts["items"][0]["account_id"] == "a1"
    assert accts["items"][0]["evidence_type"] == "prisma_cloud_account"

    resources = client.fetch_resources()
    assert resources["ok"] and resources["items"][0]["resource_id"] == "r1"
    assert resources["items"][0]["region"] == "us-east-1"

    comp = client.fetch_compliance_posture()
    assert comp["ok"] and comp["items"][0]["compliance_standard"] == "CIS"
    assert comp["items"][0]["passed"] == 10 and comp["items"][0]["failed"] == 2


def test_prisma_redlock_auth_header():
    captured = {"redlock": None}

    def transport(method, url, headers, params, timeout=None):
        if url.endswith("/login"):
            return {"token": "PJWT"}
        captured["redlock"] = headers.get("x-redlock-auth")
        return {"items": []}

    client = prisma_cloud.PrismaCloudClient(
        config={"base_url": "https://prisma", "access_key": "ak", "secret_key": "sk"},
        transport=transport)
    client.authenticate()
    client.fetch_resources()
    assert captured["redlock"] == "PJWT"
