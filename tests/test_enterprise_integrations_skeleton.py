"""Tests for the ServiceNow CMDB and Archer integration skeletons.

All transports are mocked — NO real ServiceNow/Archer call is made. Verifies
config-status secret masking, fetch interfaces via injected transport, mapping
stubs, and the "not configured" guard.
"""

from __future__ import annotations

import os

os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.operations.integrations import servicenow_cmdb as snow
from modules.operations.integrations import archer


# --------------------------------------------------------------------------- #
# ServiceNow CMDB
# --------------------------------------------------------------------------- #
def test_servicenow_config_status_masks_secrets(monkeypatch):
    monkeypatch.setenv("ECS_SERVICENOW_BASE_URL", "https://demo.service-now.com")
    monkeypatch.setenv("ECS_SERVICENOW_CLIENT_ID", "abc")
    monkeypatch.setenv("ECS_SERVICENOW_CLIENT_SECRET", "topsecret")
    status = snow.config_status(snow.get_servicenow_config())
    assert status["base_url_configured"] is True
    assert status["client_id"] == "SET"
    assert status["client_secret"] == "SET"
    assert status["ready"] is True
    # The secret value must never appear in the status dict.
    assert "topsecret" not in str(status)


def test_servicenow_not_configured_raises():
    client = snow.ServiceNowCmdbClient(config={"base_url": ""})
    with pytest.raises(snow.IntegrationNotConfigured):
        client.fetch_configuration_items()


def test_servicenow_fetch_with_mock_transport():
    captured = {}

    def mock_transport(method, url, headers, params):
        captured["url"] = url
        return {"result": [
            {"sys_id": "1", "name": "srv-a", "sys_class_name": "cmdb_ci_server",
             "ip_address": "10.0.0.1", "operational_status": "1", "assigned_to": "ops"},
        ]}

    client = snow.ServiceNowCmdbClient(
        config={"base_url": "https://demo.service-now.com", "client_id": "x", "client_secret": "y"},
        transport=mock_transport,
    )
    cis = client.fetch_configuration_items(ci_class="cmdb_ci_server")
    assert len(cis) == 1
    assert "cmdb_ci_server" in captured["url"]


def test_servicenow_map_ci_to_asset():
    asset = snow.map_ci_to_asset(
        {"sys_id": "42", "name": "srv-a", "sys_class_name": "cmdb_ci_server", "ip_address": "10.0.0.9"}
    )
    assert asset["asset_id"] == "42"
    assert asset["name"] == "srv-a"
    assert asset["source"] == "servicenow_cmdb"


def test_servicenow_fetch_assets_maps():
    def mock_transport(method, url, headers, params):
        return {"result": [{"sys_id": "7", "name": "srv-b", "sys_class_name": "cmdb_ci_server"}]}

    client = snow.ServiceNowCmdbClient(
        config={"base_url": "https://x", "client_id": "a", "client_secret": "b"},
        transport=mock_transport,
    )
    assets = client.fetch_assets()
    assert assets[0]["asset_id"] == "7"
    assert assets[0]["source"] == "servicenow_cmdb"


# --------------------------------------------------------------------------- #
# Archer
# --------------------------------------------------------------------------- #
def test_archer_config_status_masks_token(monkeypatch):
    monkeypatch.setenv("ECS_ARCHER_BASE_URL", "https://demo.archer.local")
    monkeypatch.setenv("ECS_ARCHER_API_TOKEN", "tok-xyz")
    status = archer.config_status(archer.get_archer_config())
    assert status["base_url_configured"] is True
    assert status["api_token"] == "SET"
    assert status["ready"] is True
    assert "tok-xyz" not in str(status)


def test_archer_not_configured_raises():
    client = archer.ArcherClient(config={"base_url": ""})
    with pytest.raises(archer.IntegrationNotConfigured):
        client.fetch_controls()


def test_archer_fetch_controls_with_mock():
    def mock_transport(method, url, headers, params):
        # The token must not be exposed via the mock's captured params.
        assert "api_token" not in params
        return {"records": [
            {"id": "C1", "name": "Access Control", "framework": "ISO27001", "status": "Active"},
        ]}

    client = archer.ArcherClient(
        config={"base_url": "https://demo.archer.local", "api_token": "tok"},
        transport=mock_transport,
    )
    controls = client.fetch_controls()
    assert controls[0]["id"] == "C1"


def test_archer_map_control():
    mapped = archer.map_archer_control(
        {"id": "C9", "name": "Encryption", "framework": "RBI", "status": "Active"}
    )
    assert mapped["control_id"] == "C9"
    assert mapped["framework"] == "RBI"
    assert mapped["source"] == "archer"


def test_archer_fetch_mapped_controls():
    def mock_transport(method, url, headers, params):
        return {"records": [{"Id": "C2", "Name": "Logging", "Framework": "ISO27001"}]}

    client = archer.ArcherClient(
        config={"base_url": "https://x", "api_token": "t"},
        transport=mock_transport,
    )
    mapped = client.fetch_mapped_controls()
    assert mapped[0]["control_id"] == "C2"
    assert mapped[0]["source"] == "archer"


def test_archer_map_framework():
    fw = archer.map_archer_framework({"id": "F1", "name": "ISO27001", "version": "2022"})
    assert fw["framework_id"] == "F1"
    assert fw["source"] == "archer"
