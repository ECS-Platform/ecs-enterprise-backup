"""Checkmarx (SAST) integration adapter (skeleton).

Fetches scan / vulnerability results from Checkmarx and normalizes them to an ECS
AppSec-evidence shape. Config-driven; OAuth client-credentials (client id/secret);
injectable transport (no real calls in tests); secrets never logged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from modules.operations.integrations import _base
from modules.operations.integrations._base import (
    BaseAdapter,
    Transport,
    bearer_auth_header,
    collect_paginated,
    mask_secret,
)

SOURCE = "checkmarx"


def get_config() -> dict[str, Any]:
    cfg = _base.yaml_block(("checkmarx",))
    return {
        "base_url": (str(cfg.get("base_url")) if cfg.get("base_url") else "")
        or _base.env("ECS_CHECKMARX_BASE_URL"),
        "client_id": (str(cfg.get("client_id")) if cfg.get("client_id") else "")
        or _base.env("ECS_CHECKMARX_CLIENT_ID"),
        "client_secret": _base.env(str(cfg.get("client_secret_env") or "ECS_CHECKMARX_CLIENT_SECRET")),
        # Optional token override + token endpoint (Checkmarx One IAM).
        "access_token": _base.env(str(cfg.get("access_token_env") or "ECS_CHECKMARX_ACCESS_TOKEN")),
        "token_url": (str(cfg.get("token_url")) if cfg.get("token_url") else "")
        or _base.env("ECS_CHECKMARX_TOKEN_URL"),
        "timeout_sec": _base.safe_int(
            cfg.get("timeout_sec") or _base.env("ECS_CHECKMARX_TIMEOUT_SECONDS"),
            _base.DEFAULT_TIMEOUT_SEC,
        ),
        "max_retries": _base.safe_int(
            cfg.get("max_retries") or _base.env("ECS_CHECKMARX_MAX_RETRIES"),
            _base.DEFAULT_MAX_RETRIES,
        ),
    }


def is_configured() -> bool:
    c = get_config()
    return bool(c["base_url"] and c["client_id"] and c["client_secret"])


def masked_config(cfg: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cfg = cfg or get_config()
    return {
        "integration": "Checkmarx",
        "base_url_configured": bool(cfg.get("base_url")),
        "client_id": mask_secret(cfg.get("client_id")),
        "client_secret": mask_secret(cfg.get("client_secret")),
        "access_token": mask_secret(cfg.get("access_token")),
        "timeout_sec": cfg.get("timeout_sec"),
        "max_retries": cfg.get("max_retries"),
        "ready": bool(cfg.get("base_url") and cfg.get("client_id") and cfg.get("client_secret")),
    }


@dataclass(repr=False)  # inherit BaseAdapter's secret-safe __repr__
class CheckmarxClient(BaseAdapter):
    source: str = SOURCE
    config: dict[str, Any] = field(default_factory=get_config)
    transport: Optional[Transport] = None
    _cached_token: Optional[str] = field(default=None, repr=False, compare=False)
    _token_attempted: bool = field(default=False, repr=False, compare=False)

    def is_configured(self) -> bool:
        c = self.config
        return bool(c.get("base_url") and c.get("client_id") and c.get("client_secret"))

    def masked_config(self) -> dict[str, Any]:
        return masked_config(self.config)

    def _token_url(self) -> str:
        # Default to the IAM realm token endpoint relative to the base URL.
        return (self.config.get("token_url")
                or f"{self.base_url()}/auth/realms/checkmarx/protocol/openid-connect/token")

    def authenticate(self) -> Optional[str]:
        """Explicitly obtain an OAuth client-credentials token (Checkmarx IAM).

        Prefers a configured ``access_token`` / cached token; otherwise performs
        the token exchange via the injected transport, at most once per client
        (success and failure cached). Returns the token or ``None``; the token is
        never logged. Call before ``fetch_*`` when ECS should manage the token.
        """
        if self.config.get("access_token"):
            return str(self.config["access_token"])
        if self._cached_token or self._token_attempted:
            return self._cached_token
        self._token_attempted = True
        transport = self.transport
        if transport is None:
            return None
        payload, status = _base.call_with_retry(
            transport, "POST", self._token_url(),
            {"Accept": "application/json"},
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
        # Uses a configured/cached bearer token only — no implicit token exchange.
        return bearer_auth_header(self.config.get("access_token") or self._cached_token)

    def _health_path(self) -> str:
        return "api/scans"

    def fetch_scans(self, project_id: str = "", page_size: int = _base.DEFAULT_PAGE_SIZE,
                    max_items: int = 1000) -> dict[str, Any]:
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        # Ensure a bearer token is obtained/cached before the fetch so _get()'s
        # headers() include it (Checkmarx IAM client-credentials exchange).
        self.authenticate()
        params_base = {}
        if project_id:
            params_base["project-id"] = project_id
        return collect_paginated(
            lambda off, lim: self._get(
                "api/scans", {**params_base, "offset": off, "limit": lim}),
            lambda p: list(p.get("scans", p.get("results", [])) or []),
            normalize_scan,
            source=SOURCE, page_size=page_size, max_items=max_items,
        )


def normalize_scan(record: dict[str, Any]) -> dict[str, Any]:
    stats = record.get("statusDetails", record.get("summary", {})) or {}
    return {
        "scan_id": record.get("id", ""),
        "project_id": record.get("projectId", record.get("project-id", "")),
        "status": record.get("status", ""),
        "high": stats.get("highSeverity", stats.get("high", 0)),
        "medium": stats.get("mediumSeverity", stats.get("medium", 0)),
        "low": stats.get("lowSeverity", stats.get("low", 0)),
        "source": SOURCE,
    }


def health_check() -> dict[str, Any]:
    return CheckmarxClient().health_check()
