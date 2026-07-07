"""UAT config-loading coverage for all enterprise connectors.

Verifies each connector loads config from environment variables, that the new UAT
placeholders exist in .env.example and the environment YAML files, that masked
config never leaks secrets, and that health_check reports not_configured when
nothing is set. No live calls.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest
import yaml

from modules.operations.integrations import (
    confluence,
    jira,
    outlook_graph,
    prisma_cloud,
    servicenow_cmdb,
    sharepoint_graph,
    sonarqube,
    teams_graph,
)
from modules.operations.integrations import ms_graph_base

ROOT = Path(__file__).resolve().parent.parent
ENV_EXAMPLE = ROOT / ".env.example"
BASE_YAML = ROOT / "config" / "environments" / "_base.yaml"
UAT_YAML = ROOT / "config" / "environments" / "uat.yaml"


@pytest.fixture(autouse=True)
def _fresh_config_cache():
    """Clear the env-config lru_cache so each test resolves YAML with its own env.

    The environment loader caches resolved YAML (which substitutes ${VAR}); without
    this, env vars set by one test leak into another's cached config.
    """
    try:
        from config.environment_loader import get_environment_config
        get_environment_config(refresh=True)
    except Exception:  # noqa: BLE001
        pass
    yield
    try:
        from config.environment_loader import get_environment_config
        get_environment_config(refresh=True)
    except Exception:  # noqa: BLE001
        pass

REQUIRED_ENV_VARS = [
    "ECS_GRAPH_TENANT_ID", "ECS_GRAPH_CLIENT_ID", "ECS_GRAPH_CLIENT_SECRET",
    "ECS_GRAPH_SCOPE", "ECS_GRAPH_AUTHORITY_URL", "ECS_GRAPH_TIMEOUT_SECONDS",
    "ECS_GRAPH_MAX_RETRIES",
    "ECS_GRAPH_SITE_ID", "ECS_GRAPH_DRIVE_ID", "ECS_SHAREPOINT_SITE_HOSTNAME",
    "ECS_SHAREPOINT_SITE_PATH", "ECS_SHAREPOINT_FOLDER_PATH",
    "ECS_TEAMS_TEAM_ID", "ECS_TEAMS_CHANNEL_ID", "ECS_TEAMS_MESSAGE_LIMIT",
    "ECS_OUTLOOK_USER_ID", "ECS_OUTLOOK_MAIL_FOLDER", "ECS_OUTLOOK_MESSAGE_LIMIT",
    "ECS_SERVICENOW_BASE_URL", "ECS_SERVICENOW_CLIENT_ID", "ECS_SERVICENOW_CLIENT_SECRET",
    "ECS_SERVICENOW_USERNAME", "ECS_SERVICENOW_PASSWORD", "ECS_SERVICENOW_AUTH_MODE",
    "ECS_SERVICENOW_TIMEOUT_SECONDS", "ECS_SERVICENOW_MAX_RETRIES",
    "ECS_JIRA_BASE_URL", "ECS_JIRA_USERNAME", "ECS_JIRA_API_TOKEN",
    "ECS_JIRA_PROJECT_KEY", "ECS_JIRA_JQL", "ECS_JIRA_TIMEOUT_SECONDS", "ECS_JIRA_MAX_RETRIES",
    "ECS_CONFLUENCE_BASE_URL", "ECS_CONFLUENCE_USERNAME", "ECS_CONFLUENCE_API_TOKEN",
    "ECS_CONFLUENCE_SPACE_KEY", "ECS_CONFLUENCE_TIMEOUT_SECONDS", "ECS_CONFLUENCE_MAX_RETRIES",
    "ECS_SONARQUBE_BASE_URL", "ECS_SONARQUBE_TOKEN", "ECS_SONARQUBE_PROJECT_KEY",
    "ECS_SONARQUBE_TIMEOUT_SECONDS", "ECS_SONARQUBE_MAX_RETRIES",
    "ECS_PRISMA_CLOUD_BASE_URL", "ECS_PRISMA_CLOUD_ACCESS_KEY", "ECS_PRISMA_CLOUD_SECRET_KEY",
    "ECS_PRISMA_CLOUD_TIMEOUT_SECONDS", "ECS_PRISMA_CLOUD_MAX_RETRIES",
]


def test_env_example_has_all_placeholders():
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    missing = [v for v in REQUIRED_ENV_VARS if f"{v}=" not in text]
    assert not missing, f".env.example missing: {missing}"


def test_yaml_files_valid_and_have_new_adapter_blocks():
    for path in (BASE_YAML, UAT_YAML):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        connectors = data.get("connectors", {}) or {}
        for key in ("ms_graph", "sharepoint_graph", "teams_graph", "outlook_graph",
                    "servicenow_cmdb", "jira_adapter", "confluence_adapter",
                    "sonarqube_adapter", "prisma_cloud"):
            assert key in connectors, f"{path.name} connectors missing {key}"


def test_yaml_has_no_inline_secret_values():
    for path in (BASE_YAML, UAT_YAML):
        raw = path.read_text(encoding="utf-8")
        for marker in ("client_secret:", "api_token:", "password:", "secret_key:", "token:"):
            for line in raw.splitlines():
                if line.strip().startswith(marker):
                    pytest.fail(f"{path.name} has inline secret field: {line.strip()!r}")


def test_no_real_ip_addresses_in_config():
    ip_re = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")
    for path in (ENV_EXAMPLE, BASE_YAML, UAT_YAML):
        for ip in ip_re.findall(path.read_text(encoding="utf-8")):
            assert ip.startswith(("127.", "0.0.0.0")), f"real IP {ip} in {path.name}"


def test_graph_common_config_from_env(monkeypatch):
    # tenant/client/secret have empty YAML defaults, so env fills them.
    monkeypatch.setenv("ECS_GRAPH_CLIENT_SECRET", "S")
    cfg = ms_graph_base.get_graph_config()
    assert cfg["client_secret"] == "S"
    # Scope always resolves to a non-empty value (env or default).
    assert cfg["scope"] == ms_graph_base.GRAPH_SCOPE


def test_sharepoint_config_from_env(monkeypatch):
    monkeypatch.setenv("ECS_GRAPH_SITE_ID", "SITE")
    monkeypatch.setenv("ECS_SHAREPOINT_FOLDER_PATH", "Evidence")
    cfg = sharepoint_graph.get_config()
    assert cfg["site_id"] == "SITE" and cfg["folder_path"] == "Evidence"


def test_teams_config_from_env(monkeypatch):
    # team_id/channel_id have empty YAML defaults so env fills them.
    monkeypatch.setenv("ECS_TEAMS_TEAM_ID", "TE")
    monkeypatch.setenv("ECS_TEAMS_CHANNEL_ID", "CH")
    cfg = teams_graph.get_config()
    assert cfg["team_id"] == "TE" and cfg["channel_id"] == "CH"
    assert isinstance(cfg["message_limit"], int)  # resolved (env or default)


def test_outlook_config_from_env(monkeypatch):
    monkeypatch.setenv("ECS_OUTLOOK_USER_ID", "svc@x.com")
    cfg = outlook_graph.get_config()
    assert cfg["user_id"] == "svc@x.com" and cfg["mail_folder"] == "inbox"


def test_servicenow_config_from_env(monkeypatch):
    # Secret-bearing creds resolve via *_env (env-direct), regardless of YAML.
    monkeypatch.setenv("ECS_SERVICENOW_BASE_URL", "https://snow")
    monkeypatch.setenv("ECS_SERVICENOW_USERNAME", "svc")
    monkeypatch.setenv("ECS_SERVICENOW_PASSWORD", "pw")
    cfg = servicenow_cmdb.get_config()
    assert cfg["base_url"] == "https://snow"
    assert cfg["username"] == "svc" and cfg["password"] == "pw"
    # Basic creds alone satisfy is_configured (OAuth or Basic).
    assert servicenow_cmdb.is_configured() is True


def test_jira_config_from_env(monkeypatch):
    # base_url/project_key have empty YAML defaults so env fills them.
    monkeypatch.setenv("ECS_JIRA_BASE_URL", "https://jira")
    monkeypatch.setenv("ECS_JIRA_PROJECT_KEY", "OPS")
    cfg = jira.get_config()
    assert cfg["base_url"] == "https://jira" and cfg["project_key"] == "OPS"
    assert cfg["api_version"] in ("2", "3")  # resolved (env or default)


def test_confluence_config_from_env(monkeypatch):
    monkeypatch.setenv("ECS_CONFLUENCE_SPACE_KEY", "SEC")
    cfg = confluence.get_config()
    assert cfg["space_key"] == "SEC"


def test_sonarqube_config_from_env(monkeypatch):
    monkeypatch.setenv("ECS_SONARQUBE_PROJECT_KEY", "proj")
    cfg = sonarqube.get_config()
    assert cfg["project_key"] == "proj"


def test_prisma_config_from_env(monkeypatch):
    monkeypatch.setenv("ECS_PRISMA_CLOUD_BASE_URL", "https://prisma")
    cfg = prisma_cloud.get_config()
    assert cfg["base_url"] == "https://prisma"
    assert isinstance(cfg["max_retries"], int)  # resolved (env or default)


CONNECTORS = [sharepoint_graph, teams_graph, outlook_graph, servicenow_cmdb,
              jira, confluence, sonarqube, prisma_cloud]


def test_all_masked_configs_never_leak(monkeypatch):
    for var in ("ECS_GRAPH_CLIENT_SECRET", "ECS_JIRA_API_TOKEN", "ECS_CONFLUENCE_API_TOKEN",
                "ECS_SONARQUBE_TOKEN", "ECS_PRISMA_CLOUD_SECRET_KEY",
                "ECS_SERVICENOW_CLIENT_SECRET", "ECS_SERVICENOW_PASSWORD"):
        monkeypatch.setenv(var, "CANARY_LEAK_XYZ")
    for mod in CONNECTORS:
        blob = str(mod.masked_config())
        assert "CANARY_LEAK_XYZ" not in blob, f"{mod.SOURCE} leaked a secret"


def test_all_health_checks_not_configured(monkeypatch):
    for var in list(os.environ):
        if var.startswith(("ECS_GRAPH", "ECS_TEAMS", "ECS_OUTLOOK", "ECS_SHAREPOINT",
                           "ECS_SERVICENOW", "ECS_JIRA", "ECS_CONFLUENCE",
                           "ECS_SONARQUBE", "ECS_PRISMA")):
            monkeypatch.delenv(var, raising=False)
    for mod in CONNECTORS:
        hc = mod.health_check()
        assert hc["status"] == "not_configured", f"{mod.SOURCE} should be not_configured"
        assert hc["configured"] is False


def test_registry_includes_new_graph_adapters():
    from modules.operations.integrations import list_adapters
    names = list_adapters()
    assert "teams_graph" in names and "outlook_graph" in names
    assert "sharepoint_graph" in names
