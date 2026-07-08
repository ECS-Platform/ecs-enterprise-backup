"""Jenkins audit-intelligence adapter (reuses the platform JenkinsConnector).

Thin wrapper delegating to
``ecs_platform.connectors.jenkins_connector.JenkinsConnector`` (real Jenkins JSON
REST API, basic auth) via :mod:`_platform_bridge`. No HTTP/auth/collection logic
is duplicated. Exposes the standard adapter interface for the registry, Connector
Test Workbench, scheduler, and executor.

Config (env or YAML ``jenkins`` / ``jenkins_connector`` block):
    ECS_JENKINS_BASE_URL · ECS_JENKINS_USERNAME · ECS_JENKINS_API_TOKEN ·
    ECS_JENKINS_TIMEOUT_SECONDS
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from modules.operations.integrations import _base, _platform_bridge
from modules.operations.integrations._base import Transport, mask_secret

SOURCE = "jenkins"


def get_config() -> dict[str, Any]:
    cfg = _base.yaml_block(("jenkins", "jenkins_connector"))
    return {
        "base_url": (str(cfg.get("base_url")) if cfg.get("base_url") else "")
        or _base.env("ECS_JENKINS_BASE_URL"),
        "username": (str(cfg.get("username")) if cfg.get("username") else "")
        or _base.env("ECS_JENKINS_USERNAME"),
        "api_token": _base.env(str(cfg.get("password_env") or "ECS_JENKINS_API_TOKEN")),
        "timeout_sec": _base.safe_int(
            cfg.get("timeout_sec") or _base.env("ECS_JENKINS_TIMEOUT_SECONDS"),
            _base.DEFAULT_TIMEOUT_SEC),
    }


def is_configured() -> bool:
    c = get_config()
    return bool(c["base_url"] and c["username"] and c["api_token"])


def masked_config(cfg: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cfg = cfg or get_config()
    return {
        "integration": "Jenkins",
        "base_url_configured": bool(cfg.get("base_url")),
        "username": mask_secret(cfg.get("username")),
        "api_token": mask_secret(cfg.get("api_token")),
        "timeout_sec": cfg.get("timeout_sec"),
        "ready": bool(cfg.get("base_url") and cfg.get("username") and cfg.get("api_token")),
    }


def _platform_config(cfg: dict[str, Any]):
    import os

    user_env, token_env = "ECS_JENKINS_USERNAME", "ECS_JENKINS_API_TOKEN"
    if cfg.get("username"):
        os.environ.setdefault(user_env, str(cfg["username"]))
    if cfg.get("api_token"):
        os.environ.setdefault(token_env, str(cfg["api_token"]))
    return _platform_bridge.build_connector_config(
        name=SOURCE, ctype="jenkins", cfg=cfg,
        option_keys=(),
        secret_option_env={"username_env": user_env, "password_env": token_env},
    )


@dataclass(repr=False)
class JenkinsClient:
    """Adapter client. Reuses the platform JenkinsConnector for collection."""

    source: str = SOURCE
    config: dict[str, Any] = field(default_factory=get_config)
    transport: Optional[Transport] = None

    def is_configured(self) -> bool:
        c = self.config
        return bool(c.get("base_url") and c.get("username") and c.get("api_token"))

    def masked_config(self) -> dict[str, Any]:
        return masked_config(self.config)

    def fetch_jobs(self) -> dict[str, Any]:
        """Collect CI job evidence (GET /api/json) via the platform client."""
        from ecs_platform.connectors.jenkins_connector import JenkinsConnector

        return _platform_bridge.run_collection(
            source=SOURCE, connector_cls=JenkinsConnector,
            config=_platform_config(self.config), is_configured=self.is_configured(),
            transport=self.transport, object_types=["jobs"],
        )

    def fetch_evidence(self, object_types: Optional[list[str]] = None) -> dict[str, Any]:
        """Collect the connector's default evidence set (jobs / builds / test results)."""
        from ecs_platform.connectors.jenkins_connector import JenkinsConnector

        return _platform_bridge.run_collection(
            source=SOURCE, connector_cls=JenkinsConnector,
            config=_platform_config(self.config), is_configured=self.is_configured(),
            transport=self.transport, object_types=object_types,
        )


def health_check() -> dict[str, Any]:
    from ecs_platform.connectors.jenkins_connector import JenkinsConnector

    return _platform_bridge.run_health(
        source=SOURCE, connector_cls=JenkinsConnector,
        config=_platform_config(get_config()), is_configured=is_configured(),
    )
