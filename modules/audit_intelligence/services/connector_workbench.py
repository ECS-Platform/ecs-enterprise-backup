"""Connector Test Workbench — safe, read-only test orchestration for the ECS
enterprise integration adapters.

This service **reuses** the existing integration registry
(:mod:`modules.operations.integrations`) and the individual adapter modules — it
does **not** duplicate or reimplement any connector logic. It only exposes safe
test actions the frontend can trigger:

  * ``list_connectors``      — registry + configured flag + auth model + type.
  * ``config_status``        — masked config (SET/MISSING only; never a secret).
  * ``health_check``         — the adapter's own config-based health probe.
  * ``dry_run``              — config-only readiness (no network, no live call).
  * ``parser_test``          — runs the adapter's primary fetch/parse method
                               against an INJECTED MOCK transport (a deterministic
                               synthetic payload), so no network call is made and
                               the normalized output shape can be previewed safely.

Safety guarantees:
  * No destructive writes; every action is read-only.
  * No live network call by default. ``parser_test`` uses a local mock transport;
    ``health_check`` is the adapter's config-based probe (no live call in the
    skeleton). A live probe is only possible if the caller explicitly injects a
    real transport at the adapter level — the workbench never does.
  * Secrets are never returned or logged (only masked SET/MISSING views).
"""

from __future__ import annotations

import importlib
from typing import Any, Callable, Optional

#: Per-adapter test metadata: friendly label, auth model, the primary
#: "parser"/fetch method to exercise, and a deterministic mock payload the mock
#: transport returns so that method produces a normalized preview without any
#: network call. Everything here references EXISTING adapter methods only.
_ADAPTER_TESTS: dict[str, dict[str, Any]] = {
    "servicenow_cmdb": {
        "label": "ServiceNow CMDB", "auth": "OAuth client-credentials / Basic",
        "client": "ServiceNowAdapter", "method": "fetch_servers",
        "mock": {"result": [
            {"sys_id": "SNOW-1", "name": "srv-web-01",
             "sys_class_name": "cmdb_ci_server", "ip_address": "10.0.0.10"}]},
        "token_key": "access_token",
    },
    "archer": {
        "label": "Archer GRC", "auth": "API token",
        "client": "ArcherClient", "method": "fetch_mapped_controls",
        "mock": {"records": [
            {"id": "C1", "name": "Access Control", "framework": "ISO27001",
             "status": "Active"}]},
    },
    "sharepoint_graph": {
        "label": "SharePoint (Graph)", "auth": "OAuth (MS Graph)",
        "client": "SharePointGraphClient", "method": "fetch_drive_items",
        "mock": {"value": [
            {"id": "1", "name": "policy.pdf", "size": 1024, "webUrl": "https://x/1",
             "lastModifiedDateTime": "2026-01-01", "file": {"mimeType": "application/pdf"}}]},
        "graph": True,
    },
    "teams_graph": {
        "label": "Microsoft Teams (Graph)", "auth": "OAuth (MS Graph)",
        "client": "TeamsGraphClient", "method": "fetch_channels",
        "mock": {"value": [
            {"id": "c1", "displayName": "Governance", "membershipType": "standard"}]},
        "graph": True,
    },
    "outlook_graph": {
        "label": "Outlook (Graph)", "auth": "OAuth (MS Graph)",
        "client": "OutlookGraphClient", "method": "fetch_mail_folders",
        "mock": {"value": [
            {"id": "f1", "displayName": "Inbox", "totalItemCount": 10, "unreadItemCount": 2}]},
        "graph": True,
    },
    "jira": {
        "label": "Jira", "auth": "Basic (email + API token)",
        "client": "JiraClient", "method": "fetch_projects",
        "mock": {"values": [
            {"key": "OPS", "id": "1", "name": "Operations", "projectTypeKey": "software"}]},
    },
    "confluence": {
        "label": "Confluence", "auth": "Basic (email + API token)",
        "client": "ConfluenceClient", "method": "fetch_spaces",
        "mock": {"results": [
            {"key": "SEC", "id": "1", "name": "Security", "type": "global",
             "status": "current"}]},
    },
    "sonarqube": {
        "label": "SonarQube", "auth": "Token",
        "client": "SonarQubeClient", "method": "fetch_projects",
        "mock": {"components": [
            {"key": "proj", "name": "Proj", "qualifier": "TRK"}]},
    },
    "checkmarx": {
        "label": "Checkmarx", "auth": "OAuth client-credentials",
        "client": "CheckmarxClient", "method": "fetch_scans",
        "mock": {"scans": [
            {"id": "s1", "projectId": "p1", "status": "Completed",
             "statusDetails": {"highSeverity": 2, "mediumSeverity": 1, "lowSeverity": 0}}]},
        "token_key": "access_token",
    },
    "prisma_cloud": {
        "label": "Prisma Cloud", "auth": "Access key / secret key",
        "client": "PrismaCloudClient", "method": "fetch_alerts",
        "mock": {"items": [
            {"id": "a1", "policy": {"name": "S3 public", "severity": "high"},
             "status": "open", "resource": {"name": "bucket", "cloudType": "aws"}}]},
        "token_key": "token",
    },
    "tripwire": {
        "label": "Tripwire", "auth": "Basic (username + password)",
        "client": "TripwireClient", "method": "fetch_policy_results",
        "mock": {"results": [
            {"id": "P1", "name": "CIS", "node": "srv-1", "status": "pass", "score": 98}]},
    },
    "aws_connector": {
        "label": "AWS", "auth": "Access key / secret key",
        "client": "AWSClient", "method": "fetch_findings",
        "mock": {"Findings": [
            {"Id": "aws-1", "Title": "S3 bucket public", "Severity": {"Label": "HIGH"},
             "Compliance": {"Status": "FAILED"}, "Region": "us-east-1"}]},
    },
    "gcp_connector": {
        "label": "GCP", "auth": "Service-account JSON",
        "client": "GCPClient", "method": "fetch_findings",
        "mock": {"findings": [
            {"name": "gcp-1", "category": "PUBLIC_BUCKET_ACL", "severity": "HIGH",
             "state": "ACTIVE", "resourceName": "//storage/buckets/x"}]},
    },
    "azure_connector": {
        "label": "Azure", "auth": "OAuth client-credentials",
        "client": "AzureClient", "method": "fetch_security_assessments",
        "mock": {"value": [
            {"id": "az-1", "properties": {"displayName": "MFA enabled",
             "status": {"code": "Unhealthy", "severity": "High"}}}]},
        "token_key": "access_token",
    },
    "nessus": {
        "label": "Nessus / Tenable", "auth": "API keys (access + secret)",
        "client": "NessusClient", "method": "fetch_scans",
        "mock": {"scans": [
            {"id": "n1", "name": "Weekly scan", "status": "completed"}]},
    },
    "qualys": {
        "label": "Qualys", "auth": "Basic (username + password)",
        "client": "QualysClient", "method": "fetch_host_detections",
        "mock": {"hosts": [
            {"ID": "q1", "IP": "10.0.0.5", "QID": "38173", "SEVERITY": "3",
             "STATUS": "Active"}]},
    },
    # CI/CD + SCM adapters — thin wrappers over the ecs_platform connector clients
    # (no duplicate HTTP/auth). The mock payload mirrors each platform connector's
    # first REST response so parser_test drives the real collect_evidence offline.
    "github": {
        "label": "GitHub", "auth": "Bearer (PAT / GitHub App)",
        "client": "GitHubClient", "method": "fetch_repositories",
        # GitHubConnector._repos() GETs /orgs/{org}/repos -> a JSON array of repos.
        "mock": [
            {"full_name": "acme/payments", "name": "payments",
             "description": "Payments service", "html_url": "https://git/acme/payments",
             "owner": {"login": "acme"}, "private": True, "default_branch": "main"}],
    },
    "jenkins": {
        "label": "Jenkins", "auth": "Basic (user + API token)",
        "client": "JenkinsClient", "method": "fetch_jobs",
        # JenkinsConnector._jobs() GETs /api/json -> {"jobs": [...]}.
        "mock": {"jobs": [
            {"name": "build-payments", "url": "https://jenkins/job/build-payments",
             "color": "blue", "lastBuild": {"number": 42, "url": "https://jenkins/42"}}]},
    },
    "azure_devops": {
        "label": "Azure DevOps", "auth": "PAT (basic)",
        "client": "AzureDevOpsClient", "method": "fetch_repositories",
        # AzureDevOpsConnector reads {"value": [...]} for both projects and repos;
        # a single value payload satisfies the projects->repos call chain.
        "mock": {"value": [
            {"id": "repo-1", "name": "payments", "webUrl": "https://azdo/payments"}]},
    },
}

#: Config keys that make a client "configured enough" to run a mock parser test
#: (so we can exercise the parse path even before real creds are set).
#:
#: DEMO PLACEHOLDERS ONLY — never real secrets. These self-describing
#: ``${VAR}``-style tokens and ``*.example.internal`` URLs are what the workbench
#: substitutes when an adapter is not yet configured, so a demo/parser-test runs
#: end-to-end offline (the injected mock transport answers every call, so the
#: value content is never sent anywhere and never leaves the process). Replace by
#: setting the adapter's real environment variables — see
#: ``docs/connectors/connector_test_workbench_design.md``.
_TEST_STUB_CONFIG: dict[str, dict[str, Any]] = {
    "servicenow_cmdb": {"base_url": "https://servicenow.example.internal",
                        "client_id": "${SERVICENOW_CLIENT_ID}",
                        "client_secret": "${SERVICENOW_CLIENT_SECRET}"},
    "archer": {"base_url": "https://archer.example.internal",
               "api_token": "${ARCHER_API_TOKEN}"},
    "sharepoint_graph": {"base_url": "https://graph.example.internal",
                          "tenant_id": "${GRAPH_TENANT_ID}",
                          "client_id": "${GRAPH_CLIENT_ID}",
                          "client_secret": "${GRAPH_CLIENT_SECRET}",
                          "site_id": "${SHAREPOINT_SITE_ID}"},
    "teams_graph": {"base_url": "https://graph.example.internal",
                     "tenant_id": "${GRAPH_TENANT_ID}",
                     "client_id": "${GRAPH_CLIENT_ID}",
                     "client_secret": "${GRAPH_CLIENT_SECRET}",
                     "team_id": "${TEAMS_TEAM_ID}"},
    "outlook_graph": {"base_url": "https://graph.example.internal",
                       "tenant_id": "${GRAPH_TENANT_ID}",
                       "client_id": "${GRAPH_CLIENT_ID}",
                       "client_secret": "${GRAPH_CLIENT_SECRET}",
                       "user_id": "mailbox@example.internal"},
    "jira": {"base_url": "https://jira.example.internal",
             "username": "svc-audit@example.internal", "api_token": "${JIRA_API_TOKEN}"},
    "confluence": {"base_url": "https://confluence.example.internal",
                   "username": "svc-audit@example.internal", "api_token": "${CONFLUENCE_API_TOKEN}"},
    "sonarqube": {"base_url": "https://sonarqube.example.internal", "token": "${SONARQUBE_TOKEN}"},
    "checkmarx": {"base_url": "https://checkmarx.example.internal",
                  "client_id": "${CHECKMARX_CLIENT_ID}", "client_secret": "${CHECKMARX_CLIENT_SECRET}"},
    "prisma_cloud": {"base_url": "https://prisma.example.internal",
                     "access_key": "${PRISMA_ACCESS_KEY}", "secret_key": "${PRISMA_SECRET_KEY}"},
    "tripwire": {"base_url": "https://tripwire.example.internal",
                 "username": "${TRIPWIRE_USERNAME}", "password": "${TRIPWIRE_PASSWORD}"},
    "aws_connector": {"base_url": "https://aws-collector.example.internal", "region": "us-east-1",
                      "access_key_id": "${AWS_ACCESS_KEY_ID}", "secret_access_key": "${AWS_SECRET_ACCESS_KEY}"},
    "gcp_connector": {"base_url": "https://gcp-collector.example.internal",
                      "project_id": "${GCP_PROJECT_ID}", "access_token": "${GCP_ACCESS_TOKEN}"},
    "azure_connector": {"base_url": "https://management.example.internal",
                        "tenant_id": "${AZURE_TENANT_ID}", "client_id": "${AZURE_CLIENT_ID}",
                        "client_secret": "${AZURE_CLIENT_SECRET}", "subscription_id": "${AZURE_SUBSCRIPTION_ID}"},
    "nessus": {"base_url": "https://nessus.example.internal",
               "access_key": "${NESSUS_ACCESS_KEY}", "secret_key": "${NESSUS_SECRET_KEY}"},
    "qualys": {"base_url": "https://qualys.example.internal",
               "username": "${QUALYS_USERNAME}", "password": "${QUALYS_PASSWORD}"},
    "github": {"base_url": "https://api.github.example.internal",
               "org": "example-org", "token": "${GITHUB_TOKEN}"},
    "jenkins": {"base_url": "https://jenkins.example.internal",
                "username": "${JENKINS_USERNAME}", "api_token": "${JENKINS_API_TOKEN}"},
    "azure_devops": {"base_url": "https://azuredevops.example.internal",
                     "organization": "example-org", "token": "${AZURE_DEVOPS_TOKEN}"},
}


def _registry():
    from modules.operations import integrations
    return integrations


def _adapter_module(name: str):
    return importlib.import_module(f"modules.operations.integrations.{name}")


def _known(name: str) -> bool:
    try:
        return name in _registry().list_adapters()
    except Exception:  # noqa: BLE001
        return False


# --------------------------------------------------------------------------- #
# List + config status
# --------------------------------------------------------------------------- #
def list_connectors() -> list[dict[str, Any]]:
    """Registry view: name, label, configured, auth model, primary method."""
    out: list[dict[str, Any]] = []
    try:
        names = _registry().list_adapters()
    except Exception:  # noqa: BLE001
        names = list(_ADAPTER_TESTS)
    for name in names:
        meta = _ADAPTER_TESTS.get(name, {})
        configured = False
        try:
            configured = bool(_adapter_module(name).is_configured())
        except Exception:  # noqa: BLE001
            configured = False
        out.append({
            "name": name,
            "label": meta.get("label", name),
            "auth": meta.get("auth", ""),
            "primary_method": meta.get("method", ""),
            "testable_in_workbench": name in _ADAPTER_TESTS,
            "configured": configured,
        })
    return out


def config_status(name: str) -> dict[str, Any]:
    """Masked config for one adapter (SET/MISSING only; never a secret)."""
    if not _known(name):
        return {"ok": False, "name": name, "error": "unknown_connector"}
    try:
        masked = _adapter_module(name).masked_config()
        configured = bool(_adapter_module(name).is_configured())
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "name": name, "error": type(exc).__name__}
    return {"ok": True, "name": name, "configured": configured, "masked_config": masked}


# --------------------------------------------------------------------------- #
# Health check (config-based; adapter's own probe)
# --------------------------------------------------------------------------- #
def health_check(name: str) -> dict[str, Any]:
    """Run the adapter's own config-based health check (no live call)."""
    if not _known(name):
        return {"ok": False, "name": name, "error": "unknown_connector"}
    try:
        health = _adapter_module(name).health_check()
    except Exception as exc:  # noqa: BLE001 - never raise to the caller
        return {"ok": False, "name": name, "status": "adapter_error",
                "errors": [type(exc).__name__]}
    return {"ok": bool(health.get("ok")), "name": name,
            "status": health.get("status"), "configured": health.get("configured"),
            "errors": health.get("errors", []),
            "masked_config": health.get("masked_config", {})}


# --------------------------------------------------------------------------- #
# Dry-run (config-only readiness; no network)
# --------------------------------------------------------------------------- #
def dry_run(name: str) -> dict[str, Any]:
    """Config-only readiness for a connector: what WOULD run, no live call."""
    if not _known(name):
        return {"ok": False, "name": name, "error": "unknown_connector"}
    meta = _ADAPTER_TESTS.get(name, {})
    status = config_status(name)
    return {
        "ok": True,
        "name": name,
        "mode": "dry-run",
        "configured": status.get("configured", False),
        "would_call": meta.get("method", ""),
        "auth": meta.get("auth", ""),
        "masked_config": status.get("masked_config", {}),
        "note": "No network call was made. Provide real credentials + a live "
                "transport to collect actual evidence.",
    }


# --------------------------------------------------------------------------- #
# Parser test (safe: injected mock transport, no network)
# --------------------------------------------------------------------------- #
def _mock_transport(payload: dict[str, Any], *, graph: bool,
                    token_key: Optional[str]) -> Callable[..., dict]:
    """Return a transport that answers auth/login with a token and data with
    the given payload — so the adapter's real parse path runs with NO network."""
    def t(method, url, headers, params, timeout=None):
        u = str(url)
        if u.endswith("/oauth2/v2.0/token") or u.endswith("/oauth_token.do") \
                or u.endswith("/protocol/openid-connect/token"):
            return {"access_token": "WORKBENCH-MOCK"}
        if u.endswith("/login"):
            return {"token": "WORKBENCH-MOCK"}
        return payload
    return t


def parser_test(name: str, *, max_preview: int = 5) -> dict[str, Any]:
    """Exercise the adapter's PRIMARY parse/fetch method against a mock transport.

    Returns a normalized-output preview + object count with NO network call and
    NO secrets. This validates the parser/normalizer end-to-end safely.
    """
    if not _known(name):
        return {"ok": False, "name": name, "error": "unknown_connector"}
    meta = _ADAPTER_TESTS.get(name)
    if not meta:
        return {"ok": False, "name": name, "error": "not_testable_in_workbench"}
    try:
        mod = _adapter_module(name)
        client_cls = getattr(mod, meta["client"])
        # Real config is preferred; fall back to a harmless stub so the parse path
        # can run even before real creds are set. The stub is non-secret and never
        # leaves the process (mock transport answers everything).
        cfg = mod.get_config()
        if not mod.is_configured():
            cfg = {**cfg, **_TEST_STUB_CONFIG.get(name, {})}
        transport = _mock_transport(meta["mock"], graph=bool(meta.get("graph")),
                                    token_key=meta.get("token_key"))
        client = client_cls(config=cfg, transport=transport)
        # Graph / token clients acquire a (mock) token first, mirroring real use.
        if hasattr(client, "authenticate"):
            try:
                client.authenticate()
            except Exception:  # noqa: BLE001 - mock path never fails hard
                pass
        method = getattr(client, meta["method"])
        result = method()
    except Exception as exc:  # noqa: BLE001 - report safely, never raise
        return {"ok": False, "name": name, "status": "parser_error",
                "method": meta.get("method"), "errors": [type(exc).__name__]}

    items = list(result.get("items", []) if isinstance(result, dict) else result or [])
    # Count synthetic source objects in the mock. Most mocks are a dict whose first
    # value is the record list; some connectors (e.g. GitHub) return a bare JSON
    # array, so handle a list mock too.
    _mock = meta["mock"]
    if isinstance(_mock, list):
        _source_count = len(_mock)
    elif isinstance(_mock, dict) and _mock:
        _source_count = len(_mock.get(next(iter(_mock)), []) or [])
    else:
        _source_count = 0
    return {
        "ok": bool(result.get("ok", True)) if isinstance(result, dict) else True,
        "name": name,
        "method": meta["method"],
        "status": result.get("status") if isinstance(result, dict) else "ok",
        "source_object_count": _source_count,
        "evidence_objects_detected": len(items),
        "parser_output_preview": items[:max_preview],
        "note": "Mock transport — deterministic synthetic data, no network call, "
                "no secrets. Confirms the parser/normalizer works.",
    }
