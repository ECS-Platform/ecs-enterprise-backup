"""ServiceNow CMDB integration skeleton.

Config-driven client for fetching CMDB Configuration Items (CIs) / assets and
mapping them into ECS application/asset shapes. This is a SKELETON:
  * No real ServiceNow call is made in tests — the HTTP transport is injectable
    and defaults to a stub that raises unless a base URL + token are configured.
  * Credentials come from the environment / config only; never hard-coded, never
    logged.

Typical use (production, once wired):
    client = ServiceNowCmdbClient(get_servicenow_config())
    cis = client.fetch_configuration_items(ci_class="cmdb_ci_server")
    assets = [map_ci_to_asset(ci) for ci in cis]
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

DEFAULT_TIMEOUT_SEC = 30

#: An HTTP transport is a callable: (method, url, headers, params) -> dict (JSON).
Transport = Callable[[str, str, dict, dict], dict]


def get_servicenow_config() -> dict[str, Any]:
    """ServiceNow connection config (env / YAML). Secrets are read, never logged."""
    from modules.operations.integrations import lookup_yaml_config

    # Backward-compatible YAML lookup. Integration config may live under either
    # the "connectors" or the (older) "integrations" section, keyed as
    # "servicenow_cmdb" (preferred) or the legacy "servicenow". Checked in
    # priority order so all historical layouts keep working:
    #   connectors.servicenow_cmdb -> integrations.servicenow_cmdb
    #   -> connectors.servicenow    -> integrations.servicenow
    cfg = lookup_yaml_config(("servicenow_cmdb", "servicenow"))
    return {
        "base_url": (str(cfg.get("base_url")) if cfg.get("base_url") else "")
        or os.environ.get("ECS_SERVICENOW_BASE_URL", ""),
        "client_id": os.environ.get(
            str(cfg.get("client_id_env") or "ECS_SERVICENOW_CLIENT_ID"), ""
        ),
        "client_secret": os.environ.get(
            str(cfg.get("client_secret_env") or "ECS_SERVICENOW_CLIENT_SECRET"), ""
        ),
        "timeout_sec": _safe_int(
            cfg.get("timeout_sec") or os.environ.get("ECS_SERVICENOW_TIMEOUT_SECONDS"),
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
    """Diagnostic-safe status: reports presence of config WITHOUT exposing secrets."""
    cfg = cfg or get_servicenow_config()
    return {
        "integration": "ServiceNow CMDB",
        "base_url_configured": bool(cfg.get("base_url")),
        "client_id": "SET" if cfg.get("client_id") else "MISSING",
        "client_secret": "SET" if cfg.get("client_secret") else "MISSING",
        "ready": bool(cfg.get("base_url") and cfg.get("client_id") and cfg.get("client_secret")),
    }


@dataclass
class ServiceNowCmdbClient:
    """Skeleton CMDB client. Inject `transport` in tests to supply mock responses."""

    config: dict[str, Any] = field(default_factory=get_servicenow_config)
    transport: Optional[Transport] = None

    def _require_ready(self) -> None:
        if not self.config.get("base_url"):
            raise IntegrationNotConfigured("ServiceNow base URL is not configured.")

    def _headers(self) -> dict:
        # OAuth token exchange is intentionally NOT implemented in the skeleton;
        # production wiring would obtain a bearer token from client_id/secret.
        return {"Accept": "application/json"}

    def fetch_configuration_items(self, ci_class: str = "cmdb_ci",
                                  limit: int = 100) -> list[dict[str, Any]]:
        """Return CMDB CIs of a class. Uses the injected transport (mock in tests)."""
        self._require_ready()
        transport = self.transport or _default_transport
        url = f"{self.config['base_url'].rstrip('/')}/api/now/table/{ci_class}"
        params = {"sysparm_limit": limit}
        payload = transport("GET", url, self._headers(), params)
        return list(payload.get("result", []) or [])

    def fetch_assets(self, limit: int = 100) -> list[dict[str, Any]]:
        """Convenience: fetch server CIs and map them to ECS asset shapes."""
        cis = self.fetch_configuration_items(ci_class="cmdb_ci_server", limit=limit)
        return [map_ci_to_asset(ci) for ci in cis]


def map_ci_to_asset(ci: dict[str, Any]) -> dict[str, Any]:
    """Mapping stub: ServiceNow CI -> ECS asset shape (extend as needed)."""
    return {
        "asset_id": ci.get("sys_id", ""),
        "name": ci.get("name", ""),
        "asset_class": ci.get("sys_class_name", ""),
        "ip_address": ci.get("ip_address", ""),
        "environment": ci.get("used_for", ""),
        "operational_status": ci.get("operational_status", ""),
        "owner": ci.get("assigned_to", ""),
        "source": "servicenow_cmdb",
    }


class IntegrationNotConfigured(RuntimeError):
    """Raised when an integration is used without required configuration."""


def _default_transport(method: str, url: str, headers: dict, params: dict) -> dict:
    """Default transport — refuses to make a real call from the skeleton.

    Production wiring replaces this with an httpx/requests-based transport. Tests
    inject their own mock transport, so this never runs in the test suite.
    """
    raise IntegrationNotConfigured(
        "ServiceNow live transport is not wired in the skeleton. Inject a transport "
        "or provide a production HTTP client."
    )
