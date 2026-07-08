"""Tests for the GitHub / Jenkins / Azure DevOps audit-intelligence adapters.

These are thin wrappers that reuse the existing ``ecs_platform.connectors``
clients (no duplicate HTTP/auth). The tests verify they are first-class
audit-intelligence connectors: registered, workbench-testable (config-status /
dry-run / parser-test), health-safe, scheduler-routed, executor-ingestable, and
that they map platform ``EvidenceItem`` output into the standard adapter shape —
all offline via injected/mock transports.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import importlib

import pytest
from fastapi.testclient import TestClient

from app.main import app
from modules.operations import integrations
from modules.audit_intelligence.services import connector_workbench as wb

client = TestClient(app)

CICD = ["github", "jenkins", "azure_devops"]


def _mock(payload):
    def t(method, url, headers, params, timeout=None):
        u = str(url)
        if "token" in u or u.endswith("/login"):
            return {"access_token": "T", "token": "T"}
        return payload
    return t


# --------------------------------------------------------------------------- #
# Registry / workbench membership
# --------------------------------------------------------------------------- #
def test_registered_in_adapter_registry():
    adapters = integrations.list_adapters()
    for name in CICD:
        assert name in adapters, f"{name} not registered"


def test_included_in_registry_health_check_all():
    health = integrations.health_check_all()
    for name in CICD:
        assert name in health["adapters"]


@pytest.mark.parametrize("name", CICD)
def test_listed_and_testable_in_workbench(name):
    listed = {c["name"]: c for c in wb.list_connectors()}
    assert name in listed
    assert listed[name]["testable_in_workbench"] is True
    assert listed[name]["primary_method"]


# --------------------------------------------------------------------------- #
# Config / masking / health (safe, no secrets)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", CICD)
def test_not_configured_by_default(name):
    mod = importlib.import_module(f"modules.operations.integrations.{name}")
    assert mod.is_configured() is False


@pytest.mark.parametrize("name", CICD)
def test_masked_config_hides_secrets(name):
    mod = importlib.import_module(f"modules.operations.integrations.{name}")
    masked = mod.masked_config()
    assert masked.get("ready") is False
    # token/secret fields only ever show SET/MISSING.
    blob = str(masked)
    assert "MISSING" in blob


@pytest.mark.parametrize("name", CICD)
def test_health_safe_when_unconfigured(name):
    mod = importlib.import_module(f"modules.operations.integrations.{name}")
    health = mod.health_check()
    assert health["status"] == "not_configured"
    assert health["configured"] is False
    assert health["ok"] is False


# --------------------------------------------------------------------------- #
# Dry-run + parser-test (mock transport drives the REAL platform connector)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", CICD)
def test_dry_run_reports_would_call(name):
    res = wb.dry_run(name)
    assert res["ok"] is True
    assert res["mode"] == "dry-run"
    assert res["would_call"]


@pytest.mark.parametrize("name", CICD)
def test_parser_test_deterministic(name):
    res = wb.parser_test(name)
    assert res["ok"] is True, f"{name}: {res}"
    assert res["evidence_objects_detected"] >= 1
    assert res["source_object_count"] >= 1
    item = res["parser_output_preview"][0]
    assert item["evidence_type"]           # normalized adapter shape
    assert "source_object_id" in item


def test_no_secret_leak_in_workbench_outputs():
    import json
    blob = json.dumps([wb.parser_test(n) for n in CICD]
                      + [wb.config_status(n) for n in CICD])
    assert "WORKBENCH-MOCK" not in blob


# --------------------------------------------------------------------------- #
# Direct client mock-fetch — reuses the platform connector's collect_evidence
# --------------------------------------------------------------------------- #
def test_github_client_fetch_maps_repository_evidence():
    from modules.operations.integrations.github import GitHubClient

    cfg = {"base_url": "https://api.github.example", "org": "acme", "token": "t"}
    payload = [{"full_name": "acme/payments", "name": "payments",
                "owner": {"login": "acme"}, "default_branch": "main",
                "html_url": "https://git/acme/payments"}]
    out = GitHubClient(config=cfg, transport=_mock(payload)).fetch_repositories()
    assert out["ok"] is True
    assert out["items"][0]["source"] == "github"
    assert out["items"][0]["object_type"] == "repository"
    assert out["items"][0]["evidence_type"] == "repository"


def test_jenkins_client_fetch_maps_job_evidence():
    from modules.operations.integrations.jenkins import JenkinsClient

    cfg = {"base_url": "https://jenkins.example", "username": "u", "api_token": "t"}
    payload = {"jobs": [{"name": "build-payments", "url": "https://j/build",
                         "color": "blue"}]}
    out = JenkinsClient(config=cfg, transport=_mock(payload)).fetch_jobs()
    assert out["ok"] is True
    assert out["items"][0]["source"] == "jenkins"
    assert out["items"][0]["object_type"] == "ci_job"


def test_azure_devops_client_fetch_maps_repository_evidence():
    from modules.operations.integrations.azure_devops import AzureDevOpsClient

    cfg = {"base_url": "https://azdo.example", "organization": "acme", "token": "t"}
    payload = {"value": [{"id": "r1", "name": "payments",
                          "webUrl": "https://azdo/payments"}]}
    out = AzureDevOpsClient(config=cfg, transport=_mock(payload)).fetch_repositories()
    assert out["ok"] is True
    assert out["items"][0]["source"] == "azure_devops"
    assert out["items"][0]["object_type"] == "repository"


def test_fetch_not_configured_without_transport_or_creds():
    # No creds AND no injected transport -> safe not_configured (no network).
    from modules.operations.integrations.github import GitHubClient

    out = GitHubClient(config={"base_url": "", "org": "", "token": ""}).fetch_repositories()
    assert out["ok"] is False
    assert out["status"] == "not_configured"


# --------------------------------------------------------------------------- #
# REST surface (existing connector endpoints) + scheduler + executor
# --------------------------------------------------------------------------- #
def test_rest_connector_list_includes_cicd():
    names = [c["name"] for c in client.get("/api/connectors").json()["connectors"]]
    for name in CICD:
        assert name in names


@pytest.mark.parametrize("name", CICD)
def test_rest_parser_and_config(name):
    assert client.post(f"/api/connectors/{name}/parser-test").json()["evidence_objects_detected"] >= 1
    assert client.get(f"/api/connectors/{name}/config-status").json()["configured"] is False


def test_scheduler_routes_cicd_asset_types():
    from modules.audit_intelligence.services.asset_scheduler import connector_routes

    routes = connector_routes()
    assert routes.get("github") == "github"
    assert routes.get("jenkins") == "jenkins"
    assert routes.get("azure_devops") == "azure_devops"
    assert routes.get("azuredevops") == "azure_devops"


@pytest.mark.parametrize("name,payload", [
    ("github", [{"full_name": "a/b", "name": "b", "owner": {"login": "a"},
                 "default_branch": "main"}]),
    ("jenkins", {"jobs": [{"name": "j1", "url": "u", "color": "blue"}]}),
    ("azure_devops", {"value": [{"id": "r1", "name": "b", "webUrl": "u"}]}),
])
def test_executor_collects_and_ingests(name, payload):
    from modules.audit_intelligence.services import connector_executor as ce
    from modules.operations.engines import evidence_repository as ops_repo

    before = len(ops_repo.evidence_repository)
    res = ce.collect_evidence(name, framework="SOC2", application="Payments",
                              transport=_mock(payload))
    assert res["ok"] is True
    assert res["ingested"] >= 1
    assert len(ops_repo.evidence_repository) > before  # reached the evidence bridge
