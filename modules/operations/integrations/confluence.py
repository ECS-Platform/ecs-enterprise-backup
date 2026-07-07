"""Confluence integration adapter.

Fetches spaces, pages (policy/procedure evidence), a single page, and page
attachment METADATA from Confluence and normalizes them to ECS document shapes.
Config-driven; basic auth (email + API token); injectable transport (no real
calls in tests); secrets never logged.

Backward compatibility: ``fetch_pages`` and ``normalize_page`` keep their existing
behavior/keys (using ``rest/api/content``). New methods (spaces / single page /
attachments) and richer normalizers are additive. The Confluence base URL may or
may not include the ``/wiki`` context path; endpoints here are relative to
``base_url`` and use ``rest/api/...`` so both Cloud (``.../wiki``) and Server
layouts work when the base URL is set accordingly.
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
        "space_key": (str(cfg.get("space_key")) if cfg.get("space_key") else "")
        or _base.env("ECS_CONFLUENCE_SPACE_KEY"),
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
        "space_key": cfg.get("space_key") or "",
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

    # ---- spaces ----------------------------------------------------------- #
    def fetch_spaces(self, page_size: int = _base.DEFAULT_PAGE_SIZE,
                     max_items: int = 1000) -> dict[str, Any]:
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        return collect_paginated(
            lambda off, lim: self._get(
                "rest/api/space", {"start": off, "limit": lim}),
            lambda p: list(p.get("results", []) or []),
            normalize_space,
            source=SOURCE, page_size=page_size, max_items=max_items,
        )

    # ---- pages ------------------------------------------------------------ #
    def fetch_pages(self, space_key: str = "", page_size: int = _base.DEFAULT_PAGE_SIZE,
                    max_items: int = 1000) -> dict[str, Any]:
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        space_key = space_key or self.config.get("space_key") or ""
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

    def fetch_page(self, page_id: str) -> dict[str, Any]:
        """Fetch a single page by id (expands version/history for metadata)."""
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        if not page_id:
            return _base.error_response(SOURCE, "http_error", "page_id is required")
        payload, status = self._get(
            f"rest/api/content/{page_id}",
            {"expand": "version,history,space"})
        if status is not None:
            return _base.error_response(SOURCE, status, f"page fetch failed ({status})")
        return _base.ok_response(SOURCE, [normalize_page(payload or {})])

    def fetch_attachments(self, page_id: str, page_size: int = _base.DEFAULT_PAGE_SIZE,
                          max_items: int = 1000) -> dict[str, Any]:
        """Fetch attachment METADATA for a page (contents are not downloaded)."""
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        if not page_id:
            return _base.error_response(SOURCE, "http_error", "page_id is required")
        return collect_paginated(
            lambda off, lim: self._get(
                f"rest/api/content/{page_id}/child/attachment",
                {"start": off, "limit": lim}),
            lambda p: list(p.get("results", []) or []),
            normalize_attachment_metadata,
            source=SOURCE, page_size=page_size, max_items=max_items,
        )


# --------------------------------------------------------------------------- #
# Normalizers
# --------------------------------------------------------------------------- #
def normalize_space(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": SOURCE,
        "space_key": record.get("key", ""),
        "space_id": record.get("id", ""),
        "name": record.get("name", ""),
        "type": record.get("type", ""),
        "status": record.get("status", ""),
        "evidence_type": "confluence_space",
    }


def _identity(node: Any) -> str:
    if isinstance(node, dict):
        by = node.get("by") if isinstance(node.get("by"), dict) else node
        if isinstance(by, dict):
            return str(by.get("displayName") or by.get("username") or "")
    return ""


def normalize_page(record: dict[str, Any]) -> dict[str, Any]:
    version = record.get("version", {}) or {}
    history = record.get("history", {}) or {}
    space = record.get("space", {}) or {}
    links = record.get("_links", {}) or {}
    web_url = links.get("webui", "") or links.get("self", "")
    return {
        # --- original keys (backward compatible) ---
        "page_id": record.get("id", ""),
        "title": record.get("title", ""),
        "type": record.get("type", ""),
        "space": space.get("key", ""),
        "status": record.get("status", ""),
        "source": SOURCE,
        # --- enriched (additive) ---
        "space_key": space.get("key", ""),
        "version": version.get("number", ""),
        "created_by": _identity(history.get("createdBy") or history),
        "updated_by": _identity(version),
        "created_date": history.get("createdDate", ""),
        "updated_date": version.get("when", ""),
        "web_url": web_url,
        "evidence_type": "confluence_page",
    }


def normalize_attachment_metadata(record: dict[str, Any]) -> dict[str, Any]:
    ext = record.get("extensions", {}) or {}
    links = record.get("_links", {}) or {}
    return {
        "source": SOURCE,
        "attachment_id": record.get("id", ""),
        "title": record.get("title", ""),
        "media_type": ext.get("mediaType", ""),
        "file_size": ext.get("fileSize", 0),
        "web_url": links.get("download", "") or links.get("webui", ""),
        "evidence_type": "confluence_attachment",
    }


def health_check() -> dict[str, Any]:
    return ConfluenceClient().health_check()
