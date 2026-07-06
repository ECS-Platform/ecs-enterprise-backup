"""Jira integration adapter (skeleton).

Fetches issues (e.g. remediation tickets / audit tasks) from Jira and normalizes
them to an ECS ticket shape. Config-driven; basic auth (username + API token);
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

SOURCE = "jira"


def get_config() -> dict[str, Any]:
    # Prefer the adapter-specific block; the legacy "jira" connector entry has a
    # different (url/enabled) shape, so it is intentionally not used here.
    cfg = _base.yaml_block(("jira_adapter",))
    return {
        "base_url": (str(cfg.get("base_url")) if cfg.get("base_url") else "")
        or _base.env("ECS_JIRA_BASE_URL"),
        "username": (str(cfg.get("username")) if cfg.get("username") else "")
        or _base.env("ECS_JIRA_USERNAME"),
        "api_token": _base.env(str(cfg.get("api_token_env") or "ECS_JIRA_API_TOKEN")),
        "timeout_sec": _base.safe_int(
            cfg.get("timeout_sec") or _base.env("ECS_JIRA_TIMEOUT_SECONDS"),
            _base.DEFAULT_TIMEOUT_SEC,
        ),
        "max_retries": _base.safe_int(
            cfg.get("max_retries") or _base.env("ECS_JIRA_MAX_RETRIES"),
            _base.DEFAULT_MAX_RETRIES,
        ),
    }


def is_configured() -> bool:
    c = get_config()
    return bool(c["base_url"] and c["username"] and c["api_token"])


def masked_config(cfg: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cfg = cfg or get_config()
    return {
        "integration": "Jira",
        "base_url_configured": bool(cfg.get("base_url")),
        "username": mask_secret(cfg.get("username")),
        "api_token": mask_secret(cfg.get("api_token")),
        "timeout_sec": cfg.get("timeout_sec"),
        "max_retries": cfg.get("max_retries"),
        "ready": bool(cfg.get("base_url") and cfg.get("username") and cfg.get("api_token")),
    }


@dataclass(repr=False)  # inherit BaseAdapter's secret-safe __repr__
class JiraClient(BaseAdapter):
    source: str = SOURCE
    config: dict[str, Any] = field(default_factory=get_config)
    transport: Optional[Transport] = None

    def is_configured(self) -> bool:
        c = self.config
        return bool(c.get("base_url") and c.get("username") and c.get("api_token"))

    def masked_config(self) -> dict[str, Any]:
        return masked_config(self.config)

    def auth_headers(self) -> dict:
        # Jira Cloud uses HTTP Basic (email + API token). Built per request; the
        # token is never logged and never placed in query params.
        return basic_auth_header(self.config.get("username"), self.config.get("api_token"))

    def _health_path(self) -> str:
        return "rest/api/2/myself"

    def fetch_issues(self, jql: str = "", page_size: int = _base.DEFAULT_PAGE_SIZE,
                     max_items: int = 1000) -> dict[str, Any]:
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        return collect_paginated(
            lambda off, lim: self._get(
                "rest/api/2/search", {"jql": jql, "startAt": off, "maxResults": lim}),
            lambda p: list(p.get("issues", []) or []),
            normalize_issue,
            source=SOURCE, page_size=page_size, max_items=max_items,
        )

    def fetch_issue(self, issue_key: str) -> dict[str, Any]:
        """Fetch a single issue by key (standard response; never raises)."""
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        if not issue_key:
            return _base.error_response(SOURCE, "http_error", "issue_key is required")
        payload, status = self._get(f"rest/api/2/issue/{issue_key}")
        if status is not None:
            return _base.error_response(SOURCE, status, f"issue fetch failed ({status})")
        return _base.ok_response(SOURCE, [normalize_issue(payload or {})])


def normalize_issue(record: dict[str, Any]) -> dict[str, Any]:
    fields = record.get("fields", {}) or {}
    return {
        "issue_key": record.get("key", ""),
        "summary": fields.get("summary", ""),
        "status": (fields.get("status", {}) or {}).get("name", ""),
        "assignee": (fields.get("assignee", {}) or {}).get("displayName", ""),
        "priority": (fields.get("priority", {}) or {}).get("name", ""),
        "source": SOURCE,
    }


def health_check() -> dict[str, Any]:
    return JiraClient().health_check()
