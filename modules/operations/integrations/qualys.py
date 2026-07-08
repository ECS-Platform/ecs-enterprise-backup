"""Qualys (VM/compliance) integration adapter (skeleton).

Fetches host detections / compliance posture from the Qualys API and normalizes
them to an ECS vulnerability-evidence shape. Config-driven; HTTP Basic auth
(username + password); injectable transport (no real calls in tests); secrets
never logged.

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
    basic_auth_header,
    collect_paginated,
    mask_secret,
)

SOURCE = "qualys"


def get_config() -> dict[str, Any]:
    cfg = _base.yaml_block(("qualys",))
    return {
        "base_url": (str(cfg.get("base_url")) if cfg.get("base_url") else "")
        or _base.env("QUALYS_BASE_URL"),
        "username": (str(cfg.get("username")) if cfg.get("username") else "")
        or _base.env("QUALYS_USERNAME"),
        "password": _base.env(str(cfg.get("password_env") or "QUALYS_PASSWORD")),
        "timeout_sec": _base.safe_int(
            cfg.get("timeout_sec") or _base.env("QUALYS_TIMEOUT_SECONDS"),
            _base.DEFAULT_TIMEOUT_SEC),
        "max_retries": _base.safe_int(
            cfg.get("max_retries") or _base.env("QUALYS_MAX_RETRIES"),
            _base.DEFAULT_MAX_RETRIES),
    }


def is_configured() -> bool:
    c = get_config()
    return bool(c["base_url"] and c["username"] and c["password"])


def masked_config(cfg: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cfg = cfg or get_config()
    return {
        "integration": "Qualys",
        "base_url_configured": bool(cfg.get("base_url")),
        "username": mask_secret(cfg.get("username")),
        "password": mask_secret(cfg.get("password")),
        "timeout_sec": cfg.get("timeout_sec"),
        "max_retries": cfg.get("max_retries"),
        "ready": bool(cfg.get("base_url") and cfg.get("username") and cfg.get("password")),
    }


@dataclass(repr=False)  # inherit BaseAdapter's secret-safe __repr__
class QualysClient(BaseAdapter):
    source: str = SOURCE
    config: dict[str, Any] = field(default_factory=get_config)
    transport: Optional[Transport] = None

    def is_configured(self) -> bool:
        c = self.config
        return bool(c.get("base_url") and c.get("username") and c.get("password"))

    def masked_config(self) -> dict[str, Any]:
        return masked_config(self.config)

    def auth_headers(self) -> dict:
        # Qualys API uses HTTP Basic + a required custom header on some endpoints.
        headers = basic_auth_header(self.config.get("username"), self.config.get("password"))
        if headers:
            headers["X-Requested-With"] = "ECS"
        return headers

    def _health_path(self) -> str:
        return "msp/about.php"

    def fetch_host_detections(self, page_size: int = _base.DEFAULT_PAGE_SIZE,
                              max_items: int = 1000) -> dict[str, Any]:
        """Host vulnerability detections (GET /api/2.0/fo/asset/host/vm/detection/)."""
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        return collect_paginated(
            lambda off, lim: self._get("api/2.0/fo/asset/host/vm/detection/",
                                       {"action": "list", "truncation_limit": lim,
                                        "id_min": off}),
            lambda p: list(p.get("hosts", p.get("HOST_LIST", [])) or [])
            if isinstance(p, dict) else [],
            normalize_detection,
            source=SOURCE, page_size=page_size, max_items=max_items,
        )

    def fetch_compliance_posture(self) -> dict[str, Any]:
        """Compliance posture summary (GET /api/2.0/fo/compliance/posture/info/)."""
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        payload, status = self._get("api/2.0/fo/compliance/posture/info/",
                                    {"action": "list"})
        if status is not None:
            return _base.error_response(SOURCE, status, f"posture fetch failed ({status})")
        items = (payload or {}).get("posture", (payload or {}).get("items", [])) or []
        return _base.ok_response(SOURCE, [normalize_posture(c) for c in items])


def normalize_detection(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": SOURCE,
        "host_id": record.get("ID", record.get("id", "")),
        "ip": record.get("IP", record.get("ip", "")),
        "dns": record.get("DNS", record.get("dns", "")),
        "os": record.get("OS", record.get("os", "")),
        "qid": record.get("QID", record.get("qid", "")),
        "severity": record.get("SEVERITY", record.get("severity", "")),
        "status": record.get("STATUS", record.get("status", "")),
        "evidence_type": "qualys_detection",
    }


def normalize_posture(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": SOURCE,
        "control_id": record.get("CONTROL_ID", record.get("control_id", "")),
        "posture": record.get("STATUS", record.get("posture", "")),
        "host_id": record.get("HOST_ID", record.get("host_id", "")),
        "technology": record.get("TECHNOLOGY", record.get("technology", "")),
        "evidence_type": "qualys_compliance",
    }


def health_check() -> dict[str, Any]:
    return QualysClient().health_check()
