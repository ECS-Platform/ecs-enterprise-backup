"""Verify UAT config files contain placeholders for all integration adapters.

Checks .env.example, config/environments/_base.yaml and config/environments/uat.yaml
for the required ECS_* variables (as placeholders only) and asserts no real
secrets / public IPs are present. No live systems required.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
ENV_EXAMPLE = ROOT / ".env.example"
BASE_YAML = ROOT / "config" / "environments" / "_base.yaml"
UAT_YAML = ROOT / "config" / "environments" / "uat.yaml"

REQUIRED_ENV_VARS = [
    # ServiceNow
    "ECS_SERVICENOW_BASE_URL", "ECS_SERVICENOW_CLIENT_ID", "ECS_SERVICENOW_CLIENT_SECRET",
    "ECS_SERVICENOW_TIMEOUT_SECONDS",
    # Archer
    "ECS_ARCHER_BASE_URL", "ECS_ARCHER_API_TOKEN", "ECS_ARCHER_TIMEOUT_SECONDS",
    # SharePoint / Graph
    "ECS_GRAPH_TENANT_ID", "ECS_GRAPH_CLIENT_ID", "ECS_GRAPH_CLIENT_SECRET",
    "ECS_GRAPH_SITE_ID", "ECS_GRAPH_DRIVE_ID", "ECS_GRAPH_TIMEOUT_SECONDS",
    # Jira
    "ECS_JIRA_BASE_URL", "ECS_JIRA_USERNAME", "ECS_JIRA_API_TOKEN", "ECS_JIRA_TIMEOUT_SECONDS",
    # Confluence
    "ECS_CONFLUENCE_BASE_URL", "ECS_CONFLUENCE_USERNAME", "ECS_CONFLUENCE_API_TOKEN",
    "ECS_CONFLUENCE_TIMEOUT_SECONDS",
    # SonarQube
    "ECS_SONARQUBE_BASE_URL", "ECS_SONARQUBE_TOKEN", "ECS_SONARQUBE_TIMEOUT_SECONDS",
    # Checkmarx
    "ECS_CHECKMARX_BASE_URL", "ECS_CHECKMARX_CLIENT_ID", "ECS_CHECKMARX_CLIENT_SECRET",
    "ECS_CHECKMARX_TIMEOUT_SECONDS",
    # Prisma Cloud
    "ECS_PRISMA_CLOUD_BASE_URL", "ECS_PRISMA_CLOUD_ACCESS_KEY", "ECS_PRISMA_CLOUD_SECRET_KEY",
    "ECS_PRISMA_CLOUD_TIMEOUT_SECONDS",
    # Tripwire
    "ECS_TRIPWIRE_BASE_URL", "ECS_TRIPWIRE_USERNAME", "ECS_TRIPWIRE_PASSWORD",
    "ECS_TRIPWIRE_TIMEOUT_SECONDS",
]


def test_env_example_has_all_placeholders():
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    missing = [v for v in REQUIRED_ENV_VARS if f"{v}=" not in text]
    assert not missing, f".env.example missing placeholders: {missing}"


def test_env_example_secrets_are_blank_placeholders():
    """Secret vars must be blank (=), 'change-me', or a documented demo default."""
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    secret_vars = [v for v in REQUIRED_ENV_VARS
                   if any(s in v for s in ("SECRET", "TOKEN", "PASSWORD", "ACCESS_KEY"))]
    for v in secret_vars:
        m = re.search(rf"^{re.escape(v)}=(.*)$", text, re.MULTILINE)
        assert m, f"{v} not found"
        val = m.group(1).strip()
        assert val in ("", "change-me") or val.startswith("<"), f"{v} has a non-placeholder value: {val!r}"


def test_no_public_ips_in_config_files():
    ip_re = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")
    for path in (ENV_EXAMPLE, BASE_YAML, UAT_YAML):
        for ip in ip_re.findall(path.read_text(encoding="utf-8")):
            assert ip.startswith(("127.", "0.0.0.0")), f"public IP {ip} in {path.name}"


def test_base_yaml_has_adapter_blocks():
    data = yaml.safe_load(BASE_YAML.read_text(encoding="utf-8"))
    connectors = data.get("connectors", {}) or {}
    for key in ("servicenow_cmdb", "archer", "sharepoint_graph", "jira_adapter",
                "confluence_adapter", "sonarqube_adapter", "checkmarx", "prisma_cloud", "tripwire"):
        assert key in connectors, f"_base.yaml connectors missing {key}"


def test_uat_yaml_has_adapter_blocks_and_no_secrets():
    raw = UAT_YAML.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    connectors = data.get("connectors", {}) or {}
    for key in ("sharepoint_graph", "jira_adapter", "confluence_adapter", "sonarqube_adapter",
                "checkmarx", "prisma_cloud", "tripwire"):
        assert key in connectors, f"uat.yaml connectors missing {key}"
    # Secrets are referenced by *_env name only, never inline values.
    for secret_marker in ("client_secret:", "api_token:", "password:", "secret_key:", "token:"):
        assert secret_marker not in raw, f"uat.yaml contains inline secret field {secret_marker!r}"


def test_yaml_files_are_valid():
    for path in (BASE_YAML, UAT_YAML):
        yaml.safe_load(path.read_text(encoding="utf-8"))  # raises if invalid
