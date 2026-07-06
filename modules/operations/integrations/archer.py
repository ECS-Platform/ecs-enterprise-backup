"""Archer (RSA/Archer GRC) integration skeleton.

Config-driven client for fetching controls / frameworks from Archer and mapping
them into ECS control/framework shapes. SKELETON only:
  * No real Archer call is made in tests — the HTTP transport is injectable and
    defaults to a stub that refuses to make a live call.
  * Credentials (API token) come from the environment / config only; never
    hard-coded, never logged.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

DEFAULT_TIMEOUT_SEC = 30

Transport = Callable[[str, str, dict, dict], dict]


def get_archer_config() -> dict[str, Any]:
    """Archer connection config (env / YAML). Secrets are read, never logged."""
    from modules.operations.integrations import lookup_yaml_config

    # Backward compatible: the "archer" block may live under either the
    # "connectors" or the (older) "integrations" section.
    cfg = lookup_yaml_config(("archer",))
    return {
        "base_url": (str(cfg.get("base_url")) if cfg.get("base_url") else "")
        or os.environ.get("ECS_ARCHER_BASE_URL", ""),
        "api_token": os.environ.get(
            str(cfg.get("api_token_env") or "ECS_ARCHER_API_TOKEN"), ""
        ),
        "timeout_sec": _safe_int(
            cfg.get("timeout_sec") or os.environ.get("ECS_ARCHER_TIMEOUT_SECONDS"),
            DEFAULT_TIMEOUT_SEC,
        ),
    }


def _safe_int(value: Any, default: int) -> int:
    try:
        s = str(value).strip()
        if not s or s.startswith("${"):
            return default
        return int(s)
    except (TypeError, ValueError):
        return default


def config_status(cfg: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Diagnostic-safe status: reports presence of config WITHOUT exposing the token."""
    cfg = cfg or get_archer_config()
    return {
        "integration": "Archer",
        "base_url_configured": bool(cfg.get("base_url")),
        "api_token": "SET" if cfg.get("api_token") else "MISSING",
        "ready": bool(cfg.get("base_url") and cfg.get("api_token")),
    }


@dataclass
class ArcherClient:
    """Skeleton Archer client. Inject `transport` in tests to supply mock responses."""

    config: dict[str, Any] = field(default_factory=get_archer_config)
    transport: Optional[Transport] = None

    def _require_ready(self) -> None:
        if not self.config.get("base_url"):
            raise IntegrationNotConfigured("Archer base URL is not configured.")

    def _headers(self) -> dict:
        # Token is used to build the auth header at request time; never logged.
        token = self.config.get("api_token") or ""
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Archer session-id={token}"
        return headers

    def fetch_controls(self, limit: int = 100) -> list[dict[str, Any]]:
        self._require_ready()
        transport = self.transport or _default_transport
        url = f"{self.config['base_url'].rstrip('/')}/api/core/content/controls"
        payload = transport("GET", url, self._headers(), {"limit": limit})
        return list(payload.get("records", payload.get("result", [])) or [])

    def fetch_frameworks(self, limit: int = 100) -> list[dict[str, Any]]:
        self._require_ready()
        transport = self.transport or _default_transport
        url = f"{self.config['base_url'].rstrip('/')}/api/core/content/frameworks"
        payload = transport("GET", url, self._headers(), {"limit": limit})
        return list(payload.get("records", payload.get("result", [])) or [])

    def fetch_mapped_controls(self, limit: int = 100) -> list[dict[str, Any]]:
        return [map_archer_control(rec) for rec in self.fetch_controls(limit=limit)]


def map_archer_control(record: dict[str, Any]) -> dict[str, Any]:
    """Mapping stub: Archer control record -> ECS control shape."""
    return {
        "control_id": record.get("id", record.get("Id", "")),
        "control_name": record.get("name", record.get("Name", "")),
        "framework": record.get("framework", record.get("Framework", "")),
        "status": record.get("status", record.get("Status", "")),
        "description": record.get("description", record.get("Description", "")),
        "source": "archer",
    }


def map_archer_framework(record: dict[str, Any]) -> dict[str, Any]:
    """Mapping stub: Archer framework record -> ECS framework shape."""
    return {
        "framework_id": record.get("id", record.get("Id", "")),
        "framework_name": record.get("name", record.get("Name", "")),
        "version": record.get("version", record.get("Version", "")),
        "source": "archer",
    }


class IntegrationNotConfigured(RuntimeError):
    """Raised when an integration is used without required configuration."""


def _default_transport(method: str, url: str, headers: dict, params: dict) -> dict:
    raise IntegrationNotConfigured(
        "Archer live transport is not wired in the skeleton. Inject a transport or "
        "provide a production HTTP client."
    )
