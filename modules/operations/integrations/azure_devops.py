"""Azure DevOps audit-intelligence adapter (reuses the platform connector).

Thin wrapper delegating to
``ecs_platform.connectors.azure_devops_connector.AzureDevOpsConnector`` (real
Azure DevOps REST, PAT auth) via :mod:`_platform_bridge`. No HTTP/auth/collection
logic is duplicated. Exposes the standard adapter interface for the registry,
Connector Test Workbench, scheduler, and executor.

Config (env or YAML ``azure_devops`` / ``azure_devops_connector`` block):
    ECS_AZDO_BASE_URL (default https://dev.azure.com) · ECS_AZDO_ORG ·
    ECS_AZDO_TOKEN (PAT) · ECS_AZDO_TIMEOUT_SECONDS
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from modules.operations.integrations import _base, _platform_bridge
from modules.operations.integrations._base import Transport, mask_secret

SOURCE = "azure_devops"
_DEFAULT_BASE = "https://dev.azure.com"


def get_config() -> dict[str, Any]:
    cfg = _base.yaml_block(("azure_devops", "azure_devops_connector"))
    return {
        "base_url": (str(cfg.get("base_url")) if cfg.get("base_url") else "")
        or _base.env("ECS_AZDO_BASE_URL") or _DEFAULT_BASE,
        "organization": (str(cfg.get("organization")) if cfg.get("organization") else "")
        or _base.env("ECS_AZDO_ORG"),
        "token": _base.env(str(cfg.get("token_env") or "ECS_AZDO_TOKEN")),
        "timeout_sec": _base.safe_int(
            cfg.get("timeout_sec") or _base.env("ECS_AZDO_TIMEOUT_SECONDS"),
            _base.DEFAULT_TIMEOUT_SEC),
    }


def is_configured() -> bool:
    c = get_config()
    return bool(c["base_url"] and c["organization"] and c["token"])


def masked_config(cfg: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cfg = cfg or get_config()
    return {
        "integration": "Azure DevOps",
        "base_url_configured": bool(cfg.get("base_url")),
        "organization": cfg.get("organization") or "",
        "token": mask_secret(cfg.get("token")),
        "timeout_sec": cfg.get("timeout_sec"),
        "ready": bool(cfg.get("base_url") and cfg.get("organization") and cfg.get("token")),
    }


def _platform_config(cfg: dict[str, Any]):
    import os

    token_env = "ECS_AZDO_TOKEN"
    if cfg.get("token"):
        os.environ.setdefault(token_env, str(cfg["token"]))
    return _platform_bridge.build_connector_config(
        name=SOURCE, ctype="azure_devops", cfg=cfg,
        option_keys=("organization",),
        secret_option_env={"token_env": token_env},
    )


@dataclass(repr=False)
class AzureDevOpsClient:
    """Adapter client. Reuses the platform AzureDevOpsConnector for collection."""

    source: str = SOURCE
    config: dict[str, Any] = field(default_factory=get_config)
    transport: Optional[Transport] = None

    def is_configured(self) -> bool:
        c = self.config
        return bool(c.get("base_url") and c.get("organization") and c.get("token"))

    def masked_config(self) -> dict[str, Any]:
        return masked_config(self.config)

    def fetch_repositories(self) -> dict[str, Any]:
        """Collect repository evidence (GET /{org}/{project}/_apis/git/repositories)."""
        from ecs_platform.connectors.azure_devops_connector import AzureDevOpsConnector

        return _platform_bridge.run_collection(
            source=SOURCE, connector_cls=AzureDevOpsConnector,
            config=_platform_config(self.config), is_configured=self.is_configured(),
            transport=self.transport, object_types=["repositories"],
        )

    def fetch_evidence(self, object_types: Optional[list[str]] = None) -> dict[str, Any]:
        """Collect the connector's default evidence set (repos / PRs / pipelines)."""
        from ecs_platform.connectors.azure_devops_connector import AzureDevOpsConnector

        return _platform_bridge.run_collection(
            source=SOURCE, connector_cls=AzureDevOpsConnector,
            config=_platform_config(self.config), is_configured=self.is_configured(),
            transport=self.transport, object_types=object_types,
        )


def health_check() -> dict[str, Any]:
    from ecs_platform.connectors.azure_devops_connector import AzureDevOpsConnector

    return _platform_bridge.run_health(
        source=SOURCE, connector_cls=AzureDevOpsConnector,
        config=_platform_config(get_config()), is_configured=is_configured(),
    )
