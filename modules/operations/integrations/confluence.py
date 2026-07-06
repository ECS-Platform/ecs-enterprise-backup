"""Confluence integration adapter (skeleton).

Fetches pages/spaces (e.g. policy/procedure evidence) from Confluence and
normalizes them to an ECS document shape. Config-driven; basic auth (username +
API token); injectable transport (no real calls in tests); secrets never logged.
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

SOURCE = "confluence"


def get_config() -> dict[str, Any]:
    cfg = _base.yaml_block(("confluence_adapter",))
    return {
        "base_url": (str(cfg.get("base_url")) if cfg.get("base_url") else "")
        or _base.env("ECS_CONFLUENCE_BASE_URL"),
        "username": (str(cfg.get("username")) if cfg.get("username") else "")
        or _base.env("ECS_CONFLUENCE_USERNAME"),
        "api_token": _base.env(str(cfg.get("api_token_env") or "ECS_CONFLUENCE_API_TOKEN")),
        "timeout_sec": _base.safe_int(
            cfg.get("timeout_sec") or _base.env("ECS_CONFLUENCE_TIMEOUT_SECONDS"),
            _base.DEFAULT_TIMEOUT_SEC,
        ),
        "max_retries": _base.safe_int(
            cfg.get("max_retries") or _base.env("ECS_CONFLUENCE_MAX_RETRIES"),
            _base.DEFAULT_MAX_RETRIES,
        ),
    }


def is_configured() -> bool:
    c = get_config()
    return bool(c["base_url"] and c["username"] and c["api_token"])


def masked_config(cfg: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cfg = cfg or get_config()
    return {
        "integration": "Confluence",
        "base_url_configured": bool(cfg.get("base_url")),
        "username": mask_secret(cfg.get("username")),
        "api_token": mask_secret(cfg.get("api_token")),
        "timeout_sec": cfg.get("timeout_sec"),
        "max_retries": cfg.get("max_retries"),
        "ready": bool(cfg.get("base_url") and cfg.get("username") and cfg.get("api_token")),
    }


@dataclass(repr=False)  # inherit BaseAdapter's secret-safe __repr__
class ConfluenceClient(BaseAdapter):
    source: str = SOURCE
    config: dict[str, Any] = field(default_factory=get_config)
    transport: Optional[Transport] = None

    def is_configured(self) -> bool:
        c = self.config
        return bool(c.get("base_url") and c.get("username") and c.get("api_token"))

    def masked_config(self) -> dict[str, Any]:
        return masked_config(self.config)

    def auth_headers(self) -> dict:
        # Confluence Cloud uses HTTP Basic (email + API token); built per request.
        return basic_auth_header(self.config.get("username"), self.config.get("api_token"))

    def _health_path(self) -> str:
        return "rest/api/space"

    def fetch_pages(self, space_key: str = "", page_size: int = _base.DEFAULT_PAGE_SIZE,
                    max_items: int = 1000) -> dict[str, Any]:
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        params_base = {"type": "page"}
        if space_key:
            params_base["spaceKey"] = space_key
        return collect_paginated(
            lambda off, lim: self._get(
                "rest/api/content", {**params_base, "start": off, "limit": lim}),
            lambda p: list(p.get("results", []) or []),
            normalize_page,
            source=SOURCE, page_size=page_size, max_items=max_items,
        )


def normalize_page(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "page_id": record.get("id", ""),
        "title": record.get("title", ""),
        "type": record.get("type", ""),
        "space": (record.get("space", {}) or {}).get("key", ""),
        "status": record.get("status", ""),
        "source": SOURCE,
    }


def health_check() -> dict[str, Any]:
    return ConfluenceClient().health_check()
