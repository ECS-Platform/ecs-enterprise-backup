"""Nessus (Tenable) vulnerability scanner integration adapter (skeleton).

Fetches scan results / vulnerability findings from a Nessus/Tenable.sc instance
and normalizes them to an ECS vulnerability-evidence shape. Config-driven; API
key auth (access key + secret key via the ``X-ApiKeys`` header); injectable
transport (no real calls in tests); secrets never logged.

Safe-by-default: no live network call unless a transport is injected or the
adapter is configured AND connector execution is explicitly enabled upstream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from modules.operations.integrations import _base
from modules.operations.integrations._base import (
    BaseAdapter,
    Transport,
    collect_paginated,
    mask_secret,
)

SOURCE = "nessus"


def get_config() -> dict[str, Any]:
    cfg = _base.yaml_block(("nessus",))
    return {
        "base_url": (str(cfg.get("base_url")) if cfg.get("base_url") else "")
        or _base.env("NESSUS_BASE_URL"),
        "access_key": _base.env(str(cfg.get("access_key_env") or "NESSUS_ACCESS_KEY")),
        "secret_key": _base.env(str(cfg.get("secret_key_env") or "NESSUS_SECRET_KEY")),
        "timeout_sec": _base.safe_int(
            cfg.get("timeout_sec") or _base.env("NESSUS_TIMEOUT_SECONDS"),
            _base.DEFAULT_TIMEOUT_SEC),
        "max_retries": _base.safe_int(
            cfg.get("max_retries") or _base.env("NESSUS_MAX_RETRIES"),
            _base.DEFAULT_MAX_RETRIES),
    }


def is_configured() -> bool:
    c = get_config()
    return bool(c["base_url"] and c["access_key"] and c["secret_key"])


def masked_config(cfg: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cfg = cfg or get_config()
    return {
        "integration": "Nessus / Tenable",
        "base_url_configured": bool(cfg.get("base_url")),
        "access_key": mask_secret(cfg.get("access_key")),
        "secret_key": mask_secret(cfg.get("secret_key")),
        "timeout_sec": cfg.get("timeout_sec"),
        "max_retries": cfg.get("max_retries"),
        "ready": bool(cfg.get("base_url") and cfg.get("access_key") and cfg.get("secret_key")),
    }


@dataclass(repr=False)  # inherit BaseAdapter's secret-safe __repr__
class NessusClient(BaseAdapter):
    source: str = SOURCE
    config: dict[str, Any] = field(default_factory=get_config)
    transport: Optional[Transport] = None

    def is_configured(self) -> bool:
        c = self.config
        return bool(c.get("base_url") and c.get("access_key") and c.get("secret_key"))

    def masked_config(self) -> dict[str, Any]:
        return masked_config(self.config)

    def auth_headers(self) -> dict:
        # Nessus REST uses the X-ApiKeys header (never logged; assembled per call).
        ak, sk = self.config.get("access_key"), self.config.get("secret_key")
        if not ak or not sk:
            return {}
        return {"X-ApiKeys": f"accessKey={ak}; secretKey={sk}"}

    def _health_path(self) -> str:
        return "server/status"

    def fetch_scans(self, page_size: int = _base.DEFAULT_PAGE_SIZE,
                    max_items: int = 1000) -> dict[str, Any]:
        """List scans (GET /scans)."""
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        payload, status = self._get("scans")
        if status is not None:
            return _base.error_response(SOURCE, status, f"scans fetch failed ({status})")
        scans = list((payload or {}).get("scans", []) or [])
        return _base.ok_response(SOURCE, [normalize_scan(s) for s in scans[:max_items]])

    def fetch_vulnerabilities(self, scan_id: str = "", page_size: int = _base.DEFAULT_PAGE_SIZE,
                              max_items: int = 1000) -> dict[str, Any]:
        """Vulnerability findings for a scan (GET /scans/{id})."""
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        if not scan_id:
            return _base.error_response(SOURCE, "http_error", "scan_id is required")
        payload, status = self._get(f"scans/{scan_id}")
        if status is not None:
            return _base.error_response(SOURCE, status, f"vuln fetch failed ({status})")
        vulns = list((payload or {}).get("vulnerabilities", []) or [])
        return _base.ok_response(SOURCE, [normalize_vulnerability(v) for v in vulns[:max_items]])


def normalize_scan(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": SOURCE,
        "scan_id": record.get("id", ""),
        "name": record.get("name", ""),
        "status": record.get("status", ""),
        "last_modification": record.get("last_modification_date", ""),
        "folder_id": record.get("folder_id", ""),
        "evidence_type": "nessus_scan",
    }


def normalize_vulnerability(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": SOURCE,
        "plugin_id": record.get("plugin_id", ""),
        "plugin_name": record.get("plugin_name", record.get("pluginName", "")),
        "severity": record.get("severity", ""),
        "count": record.get("count", 0),
        "vuln_index": record.get("vuln_index", ""),
        "evidence_type": "nessus_vulnerability",
    }


def health_check() -> dict[str, Any]:
    return NessusClient().health_check()
