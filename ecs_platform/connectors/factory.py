"""ConnectorFactory: dynamically instantiate connectors from integrations.yaml."""

from __future__ import annotations

from typing import Any

from ecs_platform.config import load_integrations
from ecs_platform.connectors.base import BaseConnector, ConnectorConfig


# Map connector "type" -> "module:ClassName". Loaded lazily to avoid import cost.
_REGISTRY: dict[str, str] = {
    "gitea": "ecs_platform.connectors.gitea_connector:GiteaConnector",
    "github": "ecs_platform.connectors.github_connector:GitHubConnector",
    "sonarqube": "ecs_platform.connectors.sonarqube_connector:SonarQubeConnector",
    "jenkins": "ecs_platform.connectors.jenkins_connector:JenkinsConnector",
    "jira": "ecs_platform.connectors.jira_connector:JiraConnector",
    "confluence": "ecs_platform.connectors.confluence_connector:ConfluenceConnector",
    "figma": "ecs_platform.connectors.figma_connector:FigmaConnector",
    "servicenow": "ecs_platform.connectors.servicenow_connector:ServiceNowConnector",
    "teams": "ecs_platform.connectors.teams_connector:TeamsConnector",
    "sharepoint": "ecs_platform.connectors.sharepoint_connector:SharePointConnector",
    "prisma": "ecs_platform.connectors.prisma_connector:PrismaConnector",
    "azure_devops": "ecs_platform.connectors.azure_devops_connector:AzureDevOpsConnector",
}

# Keys in each integration block that are NOT generic options.
_RESERVED = {"enabled", "type", "base_url", "auth_type", "collect", "verify_ssl"}


class ConnectorFactory:
    """Builds connectors from configuration; no hardcoded URLs or credentials."""

    def __init__(self, integrations: dict[str, Any] | None = None):
        cfg = integrations or load_integrations()
        self._raw = cfg.get("integrations", {})
        self._defaults = cfg.get("defaults", {})

    @staticmethod
    def _import(target: str):
        module_name, class_name = target.split(":")
        module = __import__(module_name, fromlist=[class_name])
        return getattr(module, class_name)

    def _build_config(self, name: str, block: dict[str, Any]) -> ConnectorConfig:
        ctype = block.get("type", name)
        options = {k: v for k, v in block.items() if k not in _RESERVED}
        return ConnectorConfig(
            name=name,
            type=ctype,
            enabled=bool(block.get("enabled", False)),
            base_url=str(block.get("base_url", "") or ""),
            auth_type=str(block.get("auth_type", "token")),
            options=options,
            collect=list(block.get("collect", []) or []),
            timeout_sec=int(self._defaults.get("timeout_sec", 30)),
            max_retries=int(self._defaults.get("max_retries", 3)),
            page_size=int(self._defaults.get("page_size", 100)),
            verify_ssl=bool(block.get("verify_ssl", True)),
        )

    def available(self) -> list[str]:
        return list(self._raw.keys())

    def create(self, name: str) -> BaseConnector:
        block = self._raw.get(name)
        if block is None:
            raise KeyError(f"Unknown integration: {name}")
        ctype = block.get("type", name)
        target = _REGISTRY.get(ctype)
        if not target:
            raise KeyError(f"No connector registered for type: {ctype}")
        cls = self._import(target)
        return cls(self._build_config(name, block))

    def create_enabled(self) -> dict[str, BaseConnector]:
        out: dict[str, BaseConnector] = {}
        for name, block in self._raw.items():
            if not block.get("enabled"):
                continue
            ctype = block.get("type", name)
            if ctype not in _REGISTRY:
                continue
            out[name] = self.create(name)
        return out

    def health_all(self) -> list[dict[str, Any]]:
        """Health snapshot for every configured integration (enabled or not)."""
        rows: list[dict[str, Any]] = []
        for name, block in self._raw.items():
            ctype = block.get("type", name)
            if not block.get("enabled"):
                rows.append(
                    {
                        "name": name,
                        "type": ctype,
                        "connected": False,
                        "authenticated": False,
                        "detail": "disabled",
                        "last_checked": "",
                    }
                )
                continue
            if ctype not in _REGISTRY:
                rows.append({"name": name, "type": ctype, "connected": False, "authenticated": False, "detail": "no connector", "last_checked": ""})
                continue
            try:
                rows.append(self.create(name).test_connection().to_dict())
            except Exception as exc:  # health must never raise
                rows.append({"name": name, "type": ctype, "connected": False, "authenticated": False, "detail": str(exc), "last_checked": ""})
        return rows
