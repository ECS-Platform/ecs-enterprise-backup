"""Jira integration adapter.

Fetches projects, issues (remediation tickets / audit tasks), a single issue, and
issue comments from Jira and normalizes them to ECS ticket shapes. Config-driven;
basic auth (email + API token); injectable transport (no real calls in tests);
secrets never logged.

Backward compatibility: ``fetch_issues`` / ``fetch_issue`` default to the Jira
REST API **v2** endpoints (``/rest/api/2/...``) that existing callers/tests rely
on. New deployments can select v3 via ``ECS_JIRA_API_VERSION=3`` (or the
``api_version`` config key); the new ``fetch_projects`` / ``fetch_issue_comments``
methods use the configured version. ``normalize_issue`` is enriched additively
(existing keys preserved).
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
#: Default REST API version (kept at v2 for backward compatibility).
DEFAULT_API_VERSION = "2"


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
        "project_key": (str(cfg.get("project_key")) if cfg.get("project_key") else "")
        or _base.env("ECS_JIRA_PROJECT_KEY"),
        "jql": (str(cfg.get("jql")) if cfg.get("jql") else "") or _base.env("ECS_JIRA_JQL"),
        "api_version": (str(cfg.get("api_version")) if cfg.get("api_version") else "")
        or _base.env("ECS_JIRA_API_VERSION") or DEFAULT_API_VERSION,
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
        "project_key": cfg.get("project_key") or "",
        "api_version": cfg.get("api_version") or DEFAULT_API_VERSION,
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

    def _api(self) -> str:
        return str(self.config.get("api_version") or DEFAULT_API_VERSION)

    def _health_path(self) -> str:
        return f"rest/api/{self._api()}/myself"

    # ---- projects --------------------------------------------------------- #
    def fetch_projects(self, page_size: int = _base.DEFAULT_PAGE_SIZE,
                       max_items: int = 1000) -> dict[str, Any]:
        """List Jira projects (paginated via startAt/maxResults)."""
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        api = self._api()
        return collect_paginated(
            lambda off, lim: self._get(
                f"rest/api/{api}/project/search", {"startAt": off, "maxResults": lim}),
            lambda p: list(p.get("values", p.get("results", [])) or []),
            normalize_project,
            source=SOURCE, page_size=page_size, max_items=max_items,
        )

    # ---- issues ----------------------------------------------------------- #
    def fetch_issues(self, jql: str = "", page_size: int = _base.DEFAULT_PAGE_SIZE,
                     max_items: int = 1000) -> dict[str, Any]:
        """Search issues by JQL. Defaults to the /rest/api/2/search endpoint."""
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        jql = jql or self.config.get("jql") or ""
        api = self._api()
        return collect_paginated(
            lambda off, lim: self._get(
                f"rest/api/{api}/search", {"jql": jql, "startAt": off, "maxResults": lim}),
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
        payload, status = self._get(f"rest/api/{self._api()}/issue/{issue_key}")
        if status is not None:
            return _base.error_response(SOURCE, status, f"issue fetch failed ({status})")
        return _base.ok_response(SOURCE, [normalize_issue(payload or {})])

    def fetch_issue_comments(self, issue_key: str,
                             page_size: int = _base.DEFAULT_PAGE_SIZE,
                             max_items: int = 1000) -> dict[str, Any]:
        """Fetch comments for an issue (paginated)."""
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        if not issue_key:
            return _base.error_response(SOURCE, "http_error", "issue_key is required")
        api = self._api()
        return collect_paginated(
            lambda off, lim: self._get(
                f"rest/api/{api}/issue/{issue_key}/comment",
                {"startAt": off, "maxResults": lim}),
            lambda p: list(p.get("comments", []) or []),
            normalize_comment,
            source=SOURCE, page_size=page_size, max_items=max_items,
        )


# --------------------------------------------------------------------------- #
# Normalizers
# --------------------------------------------------------------------------- #
def normalize_project(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": SOURCE,
        "project_key": record.get("key", ""),
        "project_id": record.get("id", ""),
        "name": record.get("name", ""),
        "project_type": record.get("projectTypeKey", ""),
        "lead": ((record.get("lead", {}) or {}).get("displayName", "")
                 if isinstance(record.get("lead"), dict) else ""),
        "evidence_type": "jira_project",
    }


def _names(nodes: Any, key: str = "name") -> list[str]:
    out: list[str] = []
    if isinstance(nodes, list):
        for n in nodes:
            if isinstance(n, dict) and n.get(key):
                out.append(str(n[key]))
            elif isinstance(n, str):
                out.append(n)
    return out


def normalize_issue(record: dict[str, Any]) -> dict[str, Any]:
    fields = record.get("fields", {}) or {}
    project = fields.get("project", {}) or {}
    return {
        # --- original keys (backward compatible) ---
        "issue_key": record.get("key", ""),
        "summary": fields.get("summary", ""),
        "status": (fields.get("status", {}) or {}).get("name", ""),
        "assignee": (fields.get("assignee", {}) or {}).get("displayName", ""),
        "priority": (fields.get("priority", {}) or {}).get("name", ""),
        "source": SOURCE,
        # --- enriched (additive) ---
        "issue_type": (fields.get("issuetype", {}) or {}).get("name", ""),
        "reporter": (fields.get("reporter", {}) or {}).get("displayName", ""),
        "created": fields.get("created", ""),
        "updated": fields.get("updated", ""),
        "project_key": project.get("key", ""),
        "labels": list(fields.get("labels", []) or []),
        "components": _names(fields.get("components")),
        "fix_versions": _names(fields.get("fixVersions")),
        "evidence_type": "jira_issue",
    }


def normalize_comment(record: dict[str, Any]) -> dict[str, Any]:
    author = record.get("author", {}) or {}
    body = record.get("body", "")
    # v3 bodies can be ADF (dict); keep a short, non-secret preview string.
    if isinstance(body, dict):
        body = "(rich text)"
    return {
        "source": SOURCE,
        "comment_id": record.get("id", ""),
        "author": author.get("displayName", "") if isinstance(author, dict) else "",
        "created": record.get("created", ""),
        "updated": record.get("updated", ""),
        "body_preview": str(body or "")[:280],
        "evidence_type": "jira_comment",
    }


def health_check() -> dict[str, Any]:
    return JiraClient().health_check()
