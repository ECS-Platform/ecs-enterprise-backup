"""Prisma Cloud (CSPM) integration adapter (skeleton).

Fetches cloud posture alerts / compliance findings from Prisma Cloud and
normalizes them to an ECS cloud-control-evidence shape. Config-driven; access-key
/ secret-key auth; injectable transport (no real calls in tests); secrets never
logged.
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

SOURCE = "prisma_cloud"


def get_config() -> dict[str, Any]:
    cfg = _base.yaml_block(("prisma_cloud", "prisma"))
    return {
        "base_url": (str(cfg.get("base_url")) if cfg.get("base_url") else "")
        or _base.env("ECS_PRISMA_CLOUD_BASE_URL"),
        "access_key": (str(cfg.get("access_key")) if cfg.get("access_key") else "")
        or _base.env("ECS_PRISMA_CLOUD_ACCESS_KEY"),
        "secret_key": _base.env(str(cfg.get("secret_key_env") or "ECS_PRISMA_CLOUD_SECRET_KEY")),
        # Optional pre-issued JWT (token broker); otherwise obtained via /login.
        "token": _base.env(str(cfg.get("token_env") or "ECS_PRISMA_CLOUD_TOKEN")),
        "timeout_sec": _base.safe_int(
            cfg.get("timeout_sec") or _base.env("ECS_PRISMA_CLOUD_TIMEOUT_SECONDS"),
            _base.DEFAULT_TIMEOUT_SEC,
        ),
        "max_retries": _base.safe_int(
            cfg.get("max_retries") or _base.env("ECS_PRISMA_CLOUD_MAX_RETRIES"),
            _base.DEFAULT_MAX_RETRIES,
        ),
    }


def is_configured() -> bool:
    c = get_config()
    return bool(c["base_url"] and c["access_key"] and c["secret_key"])


def masked_config(cfg: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cfg = cfg or get_config()
    return {
        "integration": "Prisma Cloud",
        "base_url_configured": bool(cfg.get("base_url")),
        "access_key": mask_secret(cfg.get("access_key")),
        "secret_key": mask_secret(cfg.get("secret_key")),
        "token": mask_secret(cfg.get("token")),
        "timeout_sec": cfg.get("timeout_sec"),
        "max_retries": cfg.get("max_retries"),
        "ready": bool(cfg.get("base_url") and cfg.get("access_key") and cfg.get("secret_key")),
    }


@dataclass(repr=False)  # inherit BaseAdapter's secret-safe __repr__
class PrismaCloudClient(BaseAdapter):
    source: str = SOURCE
    config: dict[str, Any] = field(default_factory=get_config)
    transport: Optional[Transport] = None
    _cached_token: Optional[str] = field(default=None, repr=False, compare=False)
    _token_attempted: bool = field(default=False, repr=False, compare=False)

    def is_configured(self) -> bool:
        c = self.config
        return bool(c.get("base_url") and c.get("access_key") and c.get("secret_key"))

    def masked_config(self) -> dict[str, Any]:
        return masked_config(self.config)

    def authenticate(self) -> Optional[str]:
        """Explicitly obtain a Prisma Cloud JWT via ``POST /login``.

        Prefers a configured/cached ``token``. Performs the login exchange via the
        injected transport at most once per client (success and failure cached),
        so it is safe to call before every fetch. Returns the token or ``None``;
        the JWT/keys are never logged. Call this before ``fetch_*`` (or let the
        transport attach auth) — ``auth_headers`` uses a configured/cached token
        and never triggers an implicit login.
        """
        if self.config.get("token"):
            return str(self.config["token"])
        if self._cached_token or self._token_attempted:
            return self._cached_token
        self._token_attempted = True
        transport = self.transport
        if transport is None:
            return None
        payload, status = _base.call_with_retry(
            transport, "POST", f"{self.base_url()}/login",
            {"Accept": "application/json", "Content-Type": "application/json"},
            {"username": self.config.get("access_key", ""),
             "password": self.config.get("secret_key", "")},
            max_retries=self.max_retries(),
            backoff_base=self.backoff_base_sec(),
            timeout=self.timeout_sec(),
        )
        if status is not None:
            return None
        token = (payload or {}).get("token")
        if token:
            self._cached_token = str(token)
        return self._cached_token

    def auth_headers(self) -> dict:
        # Prisma Cloud carries the session JWT in the x-redlock-auth header. Uses
        # a configured/cached token only — no implicit network call here; callers
        # (fetch_*) invoke authenticate() first.
        token = self.config.get("token") or self._cached_token
        return {"x-redlock-auth": str(token)} if token else {}

    def _health_path(self) -> str:
        return "check"

    def fetch_alerts(self, page_size: int = _base.DEFAULT_PAGE_SIZE,
                     max_items: int = 1000) -> dict[str, Any]:
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        return collect_paginated(
            lambda off, lim: self._get("v2/alert", {"offset": off, "limit": lim}),
            lambda p: list(p.get("items", p.get("alerts", [])) or []),
            normalize_alert,
            source=SOURCE, page_size=page_size, max_items=max_items,
        )


def normalize_alert(record: dict[str, Any]) -> dict[str, Any]:
    policy = record.get("policy", {}) or {}
    resource = record.get("resource", {}) or {}
    return {
        "alert_id": record.get("id", ""),
        "policy_name": policy.get("name", ""),
        "severity": policy.get("severity", record.get("severity", "")),
        "status": record.get("status", ""),
        "cloud_type": resource.get("cloudType", record.get("cloudType", "")),
        "resource": resource.get("name", ""),
        "source": SOURCE,
    }


def health_check() -> dict[str, Any]:
    return PrismaCloudClient().health_check()
