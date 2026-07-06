"""Tripwire (file integrity monitoring) integration adapter (skeleton).

Fetches integrity/compliance policy results from Tripwire and normalizes them to
an ECS control-evidence shape. Config-driven; basic auth (username + password);
injectable transport (no real calls in tests); secrets never logged.
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

SOURCE = "tripwire"


def get_config() -> dict[str, Any]:
    cfg = _base.yaml_block(("tripwire",))
    return {
        "base_url": (str(cfg.get("base_url")) if cfg.get("base_url") else "")
        or _base.env("ECS_TRIPWIRE_BASE_URL"),
        "username": (str(cfg.get("username")) if cfg.get("username") else "")
        or _base.env("ECS_TRIPWIRE_USERNAME"),
        "password": _base.env(str(cfg.get("password_env") or "ECS_TRIPWIRE_PASSWORD")),
        "timeout_sec": _base.safe_int(
            cfg.get("timeout_sec") or _base.env("ECS_TRIPWIRE_TIMEOUT_SECONDS"),
            _base.DEFAULT_TIMEOUT_SEC,
        ),
        "max_retries": _base.safe_int(
            cfg.get("max_retries") or _base.env("ECS_TRIPWIRE_MAX_RETRIES"),
            _base.DEFAULT_MAX_RETRIES,
        ),
    }


def is_configured() -> bool:
    c = get_config()
    return bool(c["base_url"] and c["username"] and c["password"])


def masked_config(cfg: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cfg = cfg or get_config()
    return {
        "integration": "Tripwire",
        "base_url_configured": bool(cfg.get("base_url")),
        "username": mask_secret(cfg.get("username")),
        "password": mask_secret(cfg.get("password")),
        "timeout_sec": cfg.get("timeout_sec"),
        "max_retries": cfg.get("max_retries"),
        "ready": bool(cfg.get("base_url") and cfg.get("username") and cfg.get("password")),
    }


@dataclass(repr=False)  # inherit BaseAdapter's secret-safe __repr__
class TripwireClient(BaseAdapter):
    source: str = SOURCE
    config: dict[str, Any] = field(default_factory=get_config)
    transport: Optional[Transport] = None

    def is_configured(self) -> bool:
        c = self.config
        return bool(c.get("base_url") and c.get("username") and c.get("password"))

    def masked_config(self) -> dict[str, Any]:
        return masked_config(self.config)

    def auth_headers(self) -> dict:
        # Tripwire Enterprise REST uses HTTP Basic (username + password).
        return basic_auth_header(self.config.get("username"), self.config.get("password"))

    def _health_path(self) -> str:
        return "api/v1/version"

    def fetch_policy_results(self, page_size: int = _base.DEFAULT_PAGE_SIZE,
                             max_items: int = 1000) -> dict[str, Any]:
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        return collect_paginated(
            lambda off, lim: self._get("api/v1/policies/results",
                                       {"offset": off, "limit": lim}),
            lambda p: list(p.get("results", p.get("items", [])) or []),
            normalize_policy_result,
            source=SOURCE, page_size=page_size, max_items=max_items,
        )


def normalize_policy_result(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "policy_id": record.get("id", record.get("policyId", "")),
        "policy_name": record.get("name", record.get("policyName", "")),
        "node": record.get("node", record.get("nodeName", "")),
        "status": record.get("status", record.get("result", "")),
        "score": record.get("score", ""),
        "source": SOURCE,
    }


def health_check() -> dict[str, Any]:
    return TripwireClient().health_check()
