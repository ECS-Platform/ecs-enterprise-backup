"""GitHub audit-intelligence adapter (reuses the platform GitHubConnector).

This is a THIN wrapper: it does not implement any HTTP client, authentication, or
evidence-collection logic — it delegates to
``ecs_platform.connectors.github_connector.GitHubConnector`` (real GitHub REST v3)
via :mod:`modules.operations.integrations._platform_bridge`, and exposes the
standard audit-intelligence adapter interface so GitHub is a first-class connector
in the registry, Connector Test Workbench, scheduler, and evidence executor.

Config (env or YAML ``github`` / ``github_connector`` block):
    ECS_GITHUB_BASE_URL (default https://api.github.com) · ECS_GITHUB_ORG ·
    ECS_GITHUB_TOKEN · ECS_GITHUB_TIMEOUT_SECONDS
Secrets are referenced by env-var name; masked_config() shows SET/MISSING only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from modules.operations.integrations import _base, _platform_bridge
from modules.operations.integrations._base import Transport, mask_secret

SOURCE = "github"
_DEFAULT_BASE = "https://api.github.com"


def get_config() -> dict[str, Any]:
    cfg = _base.yaml_block(("github", "github_connector"))
    return {
        "base_url": (str(cfg.get("base_url")) if cfg.get("base_url") else "")
        or _base.env("ECS_GITHUB_BASE_URL") or _DEFAULT_BASE,
        "org": (str(cfg.get("org")) if cfg.get("org") else "") or _base.env("ECS_GITHUB_ORG"),
        "token": _base.env(str(cfg.get("token_env") or "ECS_GITHUB_TOKEN")),
        "timeout_sec": _base.safe_int(
            cfg.get("timeout_sec") or _base.env("ECS_GITHUB_TIMEOUT_SECONDS"),
            _base.DEFAULT_TIMEOUT_SEC),
    }


def is_configured() -> bool:
    c = get_config()
    return bool(c["base_url"] and c["org"] and c["token"])


def masked_config(cfg: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cfg = cfg or get_config()
    return {
        "integration": "GitHub",
        "base_url_configured": bool(cfg.get("base_url")),
        "org": cfg.get("org") or "",
        "token": mask_secret(cfg.get("token")),
        "timeout_sec": cfg.get("timeout_sec"),
        "ready": bool(cfg.get("base_url") and cfg.get("org") and cfg.get("token")),
    }


def _platform_config(cfg: dict[str, Any]):
    # Expose the token under a stable env-var name the platform connector reads.
    import os

    token_env = "ECS_GITHUB_TOKEN"
    if cfg.get("token"):
        os.environ.setdefault(token_env, str(cfg["token"]))
    return _platform_bridge.build_connector_config(
        name=SOURCE, ctype="github", cfg=cfg,
        option_keys=("org",),
        secret_option_env={"token_env": token_env},
    )


@dataclass(repr=False)
class GitHubClient:
    """Adapter client. Reuses the platform GitHubConnector for collection."""

    source: str = SOURCE
    config: dict[str, Any] = field(default_factory=get_config)
    transport: Optional[Transport] = None

    def is_configured(self) -> bool:
        c = self.config
        return bool(c.get("base_url") and c.get("org") and c.get("token"))

    def masked_config(self) -> dict[str, Any]:
        return masked_config(self.config)

    def fetch_repositories(self) -> dict[str, Any]:
        """Collect repository evidence (GET /orgs/{org}/repos) via the platform client."""
        from ecs_platform.connectors.github_connector import GitHubConnector

        return _platform_bridge.run_collection(
            source=SOURCE, connector_cls=GitHubConnector,
            config=_platform_config(self.config), is_configured=self.is_configured(),
            transport=self.transport, object_types=["repositories"],
        )

    def fetch_evidence(self, object_types: Optional[list[str]] = None) -> dict[str, Any]:
        """Collect the connector's default evidence set (repos / PRs / branch protection)."""
        from ecs_platform.connectors.github_connector import GitHubConnector

        return _platform_bridge.run_collection(
            source=SOURCE, connector_cls=GitHubConnector,
            config=_platform_config(self.config), is_configured=self.is_configured(),
            transport=self.transport, object_types=object_types,
        )


def health_check() -> dict[str, Any]:
    from ecs_platform.connectors.github_connector import GitHubConnector

    return _platform_bridge.run_health(
        source=SOURCE, connector_cls=GitHubConnector,
        config=_platform_config(get_config()), is_configured=is_configured(),
    )
