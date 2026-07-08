"""Tests for the cloud + vulnerability-scanner connector adapters.

Covers AWS, GCP, Azure, Nessus, Qualys — all built on the existing BaseAdapter /
transport framework (no cloud SDKs). Verifies registry membership, safe
not_configured behavior, masked config (no secret leakage), config-based health,
and deterministic parser output via an injected mock transport (no live network).
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

NEW_CONNECTORS = ["aws_connector", "gcp_connector", "azure_connector", "nessus", "qualys"]


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #
def test_new_connectors_registered():
    adapters = integrations.list_adapters()
    for name in NEW_CONNECTORS:
        assert name in adapters, f"{name} not registered"


def test_registry_health_check_all_includes_new():
    health = integrations.health_check_all()
    for name in NEW_CONNECTORS:
        assert name in health["adapters"]


# --------------------------------------------------------------------------- #
# Config / masking / health (module-level interface, per connector)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", NEW_CONNECTORS)
def test_not_configured_by_default(name):
    mod = importlib.import_module(f"modules.operations.integrations.{name}")
    assert mod.is_configured() is False  # no creds in the test env


@pytest.mark.parametrize("name", NEW_CONNECTORS)
def test_masked_config_hides_secrets(name):
    mod = importlib.import_module(f"modules.operations.integrations.{name}")
    masked = mod.masked_config()
    blob = str(masked)
    # Masked view must only ever show SET/MISSING for secret fields.
    assert "MISSING" in blob or "SET" in blob
    assert masked.get("ready") is False


@pytest.mark.parametrize("name", NEW_CONNECTORS)
def test_health_check_safe_when_unconfigured(name):
    mod = importlib.import_module(f"modules.operations.integrations.{name}")
    health = mod.health_check()
    assert health["status"] == "not_configured"
    assert health["configured"] is False
    assert health["ok"] is False


# --------------------------------------------------------------------------- #
# Parser test (deterministic, mock transport, no network)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", NEW_CONNECTORS)
def test_parser_test_deterministic(name):
    res = wb.parser_test(name)
    assert res["ok"] is True, f"{name}: {res}"
    assert res["evidence_objects_detected"] >= 1
    assert res["parser_output_preview"]
    assert res["method"]


def test_no_secret_leak_in_outputs():
    import json
    blob = json.dumps([wb.parser_test(n) for n in NEW_CONNECTORS]
                      + [wb.config_status(n) for n in NEW_CONNECTORS])
    assert "WORKBENCH-MOCK" not in blob  # mock token never surfaces


# --------------------------------------------------------------------------- #
# REST surface (they plug into the existing connector endpoints)
# --------------------------------------------------------------------------- #
def test_rest_connector_list_includes_new():
    names = [c["name"] for c in client.get("/api/connectors").json()["connectors"]]
    for name in NEW_CONNECTORS:
        assert name in names


@pytest.mark.parametrize("name", NEW_CONNECTORS)
def test_rest_health_and_parser(name):
    assert client.post(f"/api/connectors/{name}/health-check").status_code == 200
    r = client.post(f"/api/connectors/{name}/parser-test")
    assert r.status_code == 200
    assert r.json()["evidence_objects_detected"] >= 1


@pytest.mark.parametrize("name", NEW_CONNECTORS)
def test_rest_config_status(name):
    r = client.get(f"/api/connectors/{name}/config-status")
    assert r.status_code == 200
    assert r.json()["configured"] is False


# --------------------------------------------------------------------------- #
# Scheduler routing recognizes the new connector asset types
# --------------------------------------------------------------------------- #
def test_scheduler_routes_new_asset_types():
    from modules.audit_intelligence.services.asset_scheduler import connector_routes

    routes = connector_routes()
    assert routes.get("aws") == "aws_connector"
    assert routes.get("gcp") == "gcp_connector"
    assert routes.get("azure") == "azure_connector"
    assert routes.get("nessus") == "nessus"
    assert routes.get("qualys") == "qualys"


# --------------------------------------------------------------------------- #
# A connector actually parses injected mock data end-to-end (Nessus example)
# --------------------------------------------------------------------------- #
def test_nessus_fetch_scans_with_mock_transport():
    from modules.operations.integrations.nessus import NessusClient

    def transport(method, url, headers, params, timeout=None):
        return {"scans": [{"id": "s1", "name": "Weekly", "status": "completed"}]}

    cfg = {"base_url": "https://nessus.example", "access_key": "ak", "secret_key": "sk"}
    client_ = NessusClient(config=cfg, transport=transport)
    out = client_.fetch_scans()
    assert out["ok"] is True
    assert out["items"][0]["scan_id"] == "s1"
    assert out["items"][0]["evidence_type"] == "nessus_scan"


def test_azure_auth_uses_mock_token():
    from modules.operations.integrations.azure_connector import AzureClient

    calls = {"token": 0}

    def transport(method, url, headers, params, timeout=None):
        if url.endswith("/oauth2/v2.0/token"):
            calls["token"] += 1
            return {"access_token": "MOCKTOKEN"}
        return {"value": [{"id": "az-1", "properties": {"displayName": "MFA",
                "status": {"code": "Unhealthy", "severity": "High"}}}]}

    cfg = {"base_url": "https://management.example", "tenant_id": "t", "client_id": "c",
           "client_secret": "s", "subscription_id": "sub",
           "authority_url": "https://login.microsoftonline.com",
           "scope": "https://management.azure.com/.default"}
    client_ = AzureClient(config=cfg, transport=transport)
    out = client_.fetch_security_assessments()
    assert out["ok"] is True
    assert calls["token"] == 1  # token acquired once
    assert out["items"][0]["evidence_type"] == "azure_security_assessment"


def test_aws_fetch_findings_with_mock_transport():
    from modules.operations.integrations.aws_connector import AWSClient

    def transport(method, url, headers, params, timeout=None):
        return {"Findings": [{"Id": "aws-f1", "Title": "Public S3 bucket",
                "Severity": {"Label": "HIGH"},
                "Resources": [{"Id": "arn:aws:s3:::bucket"}],
                "Compliance": {"Status": "FAILED"}, "Region": "us-east-1"}]}

    cfg = {"base_url": "https://collector.example", "region": "us-east-1",
           "access_key_id": "ak", "secret_access_key": "sk"}
    out = AWSClient(config=cfg, transport=transport).fetch_findings()
    assert out["ok"] is True
    assert out["items"][0]["finding_id"] == "aws-f1"
    assert out["items"][0]["severity"] == "HIGH"
    assert out["items"][0]["evidence_type"] == "aws_finding"


def test_aws_fetch_requires_collector_endpoint_when_configured():
    # Credentials present but no collector base_url -> safe not_configured, no crash.
    from modules.operations.integrations.aws_connector import AWSClient

    cfg = {"base_url": "", "region": "us-east-1",
           "access_key_id": "ak", "secret_access_key": "sk"}
    out = AWSClient(config=cfg, transport=lambda *a, **k: {}).fetch_findings()
    assert out["ok"] is False
    assert out["status"] == "not_configured"


def test_gcp_fetch_findings_with_mock_transport():
    from modules.operations.integrations.gcp_connector import GCPClient

    def transport(method, url, headers, params, timeout=None):
        return {"findings": [{"name": "gcp-f1", "category": "PUBLIC_BUCKET",
                "severity": "HIGH", "state": "ACTIVE",
                "resourceName": "//storage.googleapis.com/bucket"}]}

    cfg = {"base_url": "https://collector.example", "project_id": "proj",
           "access_token": "tok"}
    out = GCPClient(config=cfg, transport=transport).fetch_findings()
    assert out["ok"] is True
    assert out["items"][0]["finding_id"] == "gcp-f1"
    assert out["items"][0]["evidence_type"] == "gcp_finding"


def test_qualys_fetch_host_detections_with_mock_transport():
    from modules.operations.integrations.qualys import QualysClient

    def transport(method, url, headers, params, timeout=None):
        return {"hosts": [{"ID": "q-h1", "IP": "10.0.0.5", "DNS": "host.internal",
                "OS": "Linux", "QID": "38173", "SEVERITY": "4", "STATUS": "Active"}]}

    cfg = {"base_url": "https://qualysapi.example", "username": "u", "password": "p"}
    out = QualysClient(config=cfg, transport=transport).fetch_host_detections()
    assert out["ok"] is True
    assert out["items"][0]["host_id"] == "q-h1"
    assert out["items"][0]["evidence_type"] == "qualys_detection"
