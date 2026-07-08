"""GCP cloud-posture integration adapter (skeleton).

Collects Security Command Center findings / asset compliance via a configurable
HTTP endpoint using the shared transport abstraction — no google-cloud SDK is
added. Credentials come from env / YAML only (service-account JSON is read as an
opaque secret, never logged); the adapter degrades to ``not_configured`` when
absent and makes no live call unless a transport is injected or connector
execution is enabled upstream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from modules.operations.integrations import _base
from modules.operations.integrations._base import (
    BaseAdapter, Transport, bearer_auth_header, mask_secret,
)

SOURCE = "gcp"


def get_config() -> dict[str, Any]:
    cfg = _base.yaml_block(("gcp", "gcp_connector"))
    return {
        "base_url": (str(cfg.get("base_url")) if cfg.get("base_url") else "")
        or _base.env("GCP_POSTURE_BASE_URL"),
        "project_id": (str(cfg.get("project_id")) if cfg.get("project_id") else "")
        or _base.env("GCP_PROJECT_ID"),
        "region": (str(cfg.get("region")) if cfg.get("region") else "")
        or _base.env("GCP_REGION"),
        # Service-account JSON (opaque secret) or a pre-issued access token.
        "service_account_json": _base.env(
            str(cfg.get("service_account_env") or "GCP_SERVICE_ACCOUNT_JSON")),
        "access_token": _base.env(str(cfg.get("access_token_env") or "GCP_ACCESS_TOKEN")),
        "timeout_sec": _base.safe_int(
            cfg.get("timeout_sec") or _base.env("GCP_TIMEOUT_SECONDS"),
            _base.DEFAULT_TIMEOUT_SEC),
        "max_retries": _base.safe_int(
            cfg.get("max_retries") or _base.env("GCP_MAX_RETRIES"),
            _base.DEFAULT_MAX_RETRIES),
    }


def is_configured() -> bool:
    c = get_config()
    return bool(c["project_id"] and (c["service_account_json"] or c["access_token"]))


def masked_config(cfg: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cfg = cfg or get_config()
    return {
        "integration": "GCP",
        "base_url_configured": bool(cfg.get("base_url")),
        "project_id": mask_secret(cfg.get("project_id")),
        "region": cfg.get("region") or "",
        "service_account_json": mask_secret(cfg.get("service_account_json")),
        "access_token": mask_secret(cfg.get("access_token")),
        "timeout_sec": cfg.get("timeout_sec"),
        "max_retries": cfg.get("max_retries"),
        "ready": bool(cfg.get("project_id") and (cfg.get("service_account_json") or cfg.get("access_token"))),
    }


@dataclass(repr=False)  # inherit BaseAdapter's secret-safe __repr__
class GCPClient(BaseAdapter):
    source: str = SOURCE
    config: dict[str, Any] = field(default_factory=get_config)
    transport: Optional[Transport] = None

    def is_configured(self) -> bool:
        c = self.config
        return bool(c.get("project_id") and (c.get("service_account_json") or c.get("access_token")))

    def masked_config(self) -> dict[str, Any]:
        return masked_config(self.config)

    def auth_headers(self) -> dict:
        # A configured OAuth access token is applied as Bearer. Minting a token from
        # the service-account JSON is the production transport's job (no SDK here).
        return bearer_auth_header(self.config.get("access_token"))

    def _health_path(self) -> str:
        return "posture/health"

    def fetch_findings(self, page_size: int = _base.DEFAULT_PAGE_SIZE,
                       max_items: int = 1000) -> dict[str, Any]:
        """Security Command Center findings (GET {base}/scc/findings)."""
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        if not self.base_url():
            return _base.error_response(SOURCE, "not_configured",
                                        "GCP_POSTURE_BASE_URL (collector endpoint) is required for live fetch")
        return _base.collect_paginated(
            lambda off, lim: self._get("scc/findings", {"pageToken": off, "pageSize": lim}),
            lambda p: list(p.get("findings", p.get("items", [])) or []) if isinstance(p, dict) else [],
            normalize_finding,
            source=SOURCE, page_size=page_size, max_items=max_items,
        )

    def fetch_assets(self, page_size: int = _base.DEFAULT_PAGE_SIZE,
                     max_items: int = 1000) -> dict[str, Any]:
        """Cloud Asset Inventory (GET {base}/assets)."""
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        if not self.base_url():
            return _base.error_response(SOURCE, "not_configured",
                                        "GCP_POSTURE_BASE_URL (collector endpoint) is required for live fetch")
        return _base.collect_paginated(
            lambda off, lim: self._get("assets", {"pageToken": off, "pageSize": lim}),
            lambda p: list(p.get("assets", p.get("items", [])) or []) if isinstance(p, dict) else [],
            normalize_asset,
            source=SOURCE, page_size=page_size, max_items=max_items,
        )


def normalize_finding(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": SOURCE,
        "finding_id": record.get("name", record.get("id", "")),
        "category": record.get("category", ""),
        "severity": record.get("severity", ""),
        "state": record.get("state", ""),
        "resource_name": record.get("resourceName", record.get("resource", "")),
        "evidence_type": "gcp_finding",
    }


def normalize_asset(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": SOURCE,
        "asset_name": record.get("name", ""),
        "asset_type": record.get("assetType", record.get("asset_type", "")),
        "project": record.get("project", ""),
        "evidence_type": "gcp_asset",
    }


def health_check() -> dict[str, Any]:
    return GCPClient().health_check()
