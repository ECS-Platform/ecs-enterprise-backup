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
        # Basic-auth fallback (used when auth_mode="basic" or OAuth creds absent).
        "username": os.environ.get(
            str(cfg.get("username_env") or "ECS_SERVICENOW_USERNAME"), ""
        ),
        "password": os.environ.get(
            str(cfg.get("password_env") or "ECS_SERVICENOW_PASSWORD"), ""
        ),
        # "oauth" (default) | "basic". Resolved by the client at request time.
        "auth_mode": (str(cfg.get("auth_mode")) if cfg.get("auth_mode") else "")
        or os.environ.get("ECS_SERVICENOW_AUTH_MODE", "") or "oauth",
        "timeout_sec": _safe_int(
            cfg.get("timeout_sec") or os.environ.get("ECS_SERVICENOW_TIMEOUT_SECONDS"),
            DEFAULT_TIMEOUT_SEC,
        ),
        "max_retries": _safe_int(
            cfg.get("max_retries") or os.environ.get("ECS_SERVICENOW_MAX_RETRIES"),
            2,
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


# --------------------------------------------------------------------------- #
# Standard adapter interface (additive; consistent with the other adapters).
# The original get_servicenow_config / config_status / ServiceNowCmdbClient /
# map_ci_to_asset above are kept for backward compatibility.
# --------------------------------------------------------------------------- #
SOURCE = "servicenow_cmdb"


def get_config() -> dict[str, Any]:
    """Standard-interface alias for :func:`get_servicenow_config`."""
    return get_servicenow_config()


def is_configured() -> bool:
    return _standard_ready(get_config())


def masked_config(cfg: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Secret-safe config view (SET/MISSING). Superset of legacy config_status()."""
    cfg = cfg or get_config()
    return {
        "integration": "ServiceNow CMDB",
        "base_url_configured": bool(cfg.get("base_url")),
        "client_id": "SET" if cfg.get("client_id") else "MISSING",
        "client_secret": "SET" if cfg.get("client_secret") else "MISSING",
        "username": "SET" if cfg.get("username") else "MISSING",
        "password": "SET" if cfg.get("password") else "MISSING",
        "auth_mode": cfg.get("auth_mode") or "oauth",
        "timeout_sec": cfg.get("timeout_sec"),
        "max_retries": cfg.get("max_retries"),
        "ready": _standard_ready(cfg),
    }


def _standard_ready(cfg: dict[str, Any]) -> bool:
    """Ready when base_url + a usable credential pair (OAuth or Basic) are present."""
    if not cfg.get("base_url"):
        return False
    has_oauth = bool(cfg.get("client_id") and cfg.get("client_secret"))
    has_basic = bool(cfg.get("username") and cfg.get("password"))
    return has_oauth or has_basic


def normalize_asset(record: dict[str, Any]) -> dict[str, Any]:
    """Standard-interface alias for :func:`map_ci_to_asset`."""
    return map_ci_to_asset(record)


def health_check() -> dict[str, Any]:
    """Config-based readiness (skeleton has no live probe). Never reveals secrets."""
    from modules.operations.integrations import _base

    if not is_configured():
        return {**_base.not_configured_response(SOURCE), "configured": False,
                "masked_config": masked_config()}
    return {"ok": True, "source": SOURCE, "status": "ok", "configured": True,
            "items": [], "errors": [], "masked_config": masked_config()}


# --------------------------------------------------------------------------- #
# Modern BaseAdapter client (additive) — real UAT code path.
# Reuses the shared retry/backoff/timeout/masking machinery and adds the Table
# API with pagination, OAuth *and* Basic auth, and typed CMDB fetch methods.
# The legacy ServiceNowCmdbClient above is unchanged for backward compatibility.
# --------------------------------------------------------------------------- #
from dataclasses import dataclass as _dataclass, field as _field  # noqa: E402
from typing import Optional as _Optional  # noqa: E402

from modules.operations.integrations import _base as _b  # noqa: E402

#: Common CMDB CI classes -> logical ECS type.
CI_CLASS_SERVER = "cmdb_ci_server"
CI_CLASS_APPLICATION = "cmdb_ci_appl"
CI_CLASS_DATABASE = "cmdb_ci_database"
CI_CLASS_BASE = "cmdb_ci"


@_dataclass(repr=False)  # inherit BaseAdapter's secret-safe __repr__
class ServiceNowAdapter(_b.BaseAdapter):
    """Config-driven ServiceNow CMDB client using the shared adapter machinery.

    Supports OAuth client-credentials (default) with a Basic-auth fallback, the
    Table API with ``sysparm_query`` / ``sysparm_limit`` / ``sysparm_offset``
    pagination, and typed CMDB fetches. Inject ``transport`` in tests.
    """

    source: str = SOURCE
    config: dict[str, Any] = _field(default_factory=get_config)
    transport: _Optional[_b.Transport] = None
    _cached_token: _Optional[str] = _field(default=None, repr=False, compare=False)
    _token_attempted: bool = _field(default=False, repr=False, compare=False)

    def is_configured(self) -> bool:
        return _standard_ready(self.config)

    def masked_config(self) -> dict[str, Any]:
        return masked_config(self.config)

    def _auth_mode(self) -> str:
        mode = str(self.config.get("auth_mode") or "oauth").lower()
        # If OAuth is requested but only Basic creds exist, fall back to Basic.
        if mode == "oauth" and not (self.config.get("client_id") and self.config.get("client_secret")):
            if self.config.get("username") and self.config.get("password"):
                return "basic"
        return mode

    def _token_url(self) -> str:
        return f"{self.base_url()}/oauth_token.do"

    def authenticate(self) -> _Optional[str]:
        """OAuth client-credentials token (cached; Basic auth needs no token)."""
        if self._auth_mode() != "oauth":
            return None
        if self._cached_token or self._token_attempted:
            return self._cached_token
        self._token_attempted = True
        transport = self.transport
        if transport is None:
            return None
        payload, status = _b.call_with_retry(
            transport, "POST", self._token_url(),
            {"Accept": "application/json",
             "Content-Type": "application/x-www-form-urlencoded"},
            {"grant_type": "client_credentials",
             "client_id": self.config.get("client_id", ""),
             "client_secret": self.config.get("client_secret", "")},
            max_retries=self.max_retries(),
            backoff_base=self.backoff_base_sec(),
            timeout=self.timeout_sec(),
        )
        if status is not None:
            return None
        token = (payload or {}).get("access_token")
        if token:
            self._cached_token = str(token)
        return self._cached_token

    def auth_headers(self) -> dict:
        if self._auth_mode() == "basic":
            return _b.basic_auth_header(self.config.get("username"), self.config.get("password"))
        return _b.bearer_auth_header(self._cached_token)

    def _health_path(self) -> str:
        # Cheap table read (1 row) as a readiness probe.
        return "api/now/table/cmdb_ci"

    def _get(self, path: str, params: _Optional[dict] = None):
        # Auto-authenticate for OAuth before the request (Basic needs no token).
        self.authenticate()
        return super()._get(path, params)

    # ---- fetches ---------------------------------------------------------- #
    def fetch_cis(self, ci_class: str = CI_CLASS_BASE, sysparm_query: str = "",
                  page_size: int = _b.DEFAULT_PAGE_SIZE, max_items: int = 1000
                  ) -> dict[str, Any]:
        """Fetch CMDB CIs of a class via the Table API (offset pagination)."""
        if not self.is_configured():
            return _b.not_configured_response(SOURCE)
        base_params: dict[str, Any] = {}
        if sysparm_query:
            base_params["sysparm_query"] = sysparm_query
        return _b.collect_paginated(
            lambda off, lim: self._get(
                f"api/now/table/{ci_class}",
                {**base_params, "sysparm_limit": lim, "sysparm_offset": off}),
            lambda p: list(p.get("result", []) or []),
            normalize_ci,
            source=SOURCE, page_size=page_size, max_items=max_items,
        )

    def fetch_servers(self, sysparm_query: str = "", page_size: int = _b.DEFAULT_PAGE_SIZE,
                      max_items: int = 1000) -> dict[str, Any]:
        return self.fetch_cis(ci_class=CI_CLASS_SERVER, sysparm_query=sysparm_query,
                              page_size=page_size, max_items=max_items)

    def fetch_applications(self, sysparm_query: str = "", page_size: int = _b.DEFAULT_PAGE_SIZE,
                           max_items: int = 1000) -> dict[str, Any]:
        return self.fetch_cis(ci_class=CI_CLASS_APPLICATION, sysparm_query=sysparm_query,
                              page_size=page_size, max_items=max_items)

    def fetch_databases(self, sysparm_query: str = "", page_size: int = _b.DEFAULT_PAGE_SIZE,
                        max_items: int = 1000) -> dict[str, Any]:
        return self.fetch_cis(ci_class=CI_CLASS_DATABASE, sysparm_query=sysparm_query,
                              page_size=page_size, max_items=max_items)


def _ref_value(node: Any) -> str:
    """ServiceNow reference fields come as {'value','link'} or 'display_value'."""
    if isinstance(node, dict):
        return str(node.get("display_value") or node.get("value") or "")
    return str(node or "")


def normalize_ci(record: dict[str, Any]) -> dict[str, Any]:
    """Rich CMDB CI -> ECS asset/evidence shape."""
    return {
        "source": SOURCE,
        "sys_id": record.get("sys_id", ""),
        "name": record.get("name", ""),
        "fqdn": record.get("fqdn", record.get("dns_domain", "")),
        "ip_address": record.get("ip_address", ""),
        "class_name": record.get("sys_class_name", ""),
        "environment": record.get("used_for", record.get("environment", "")),
        "owner": _ref_value(record.get("owned_by", record.get("assigned_to", ""))),
        "application": _ref_value(record.get("u_application", record.get("business_service", ""))),
        "criticality": record.get("business_criticality", record.get("criticality", "")),
        "operational_status": record.get("operational_status", ""),
        "support_group": _ref_value(record.get("support_group", "")),
        "assignment_group": _ref_value(record.get("assignment_group", "")),
        "discovery_source": record.get("discovery_source", ""),
        "evidence_type": "cmdb_ci",
    }
