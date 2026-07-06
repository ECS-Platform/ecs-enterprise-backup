"""SharePoint / Microsoft Graph integration adapter (skeleton).

Fetches document-library items (evidence documents) from a SharePoint site drive
via Microsoft Graph and normalizes them to an ECS document shape. Config-driven;
OAuth client-credentials (tenant/client id/secret); injectable transport (no real
calls in tests); secrets never logged.
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

SOURCE = "sharepoint_graph"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
#: OAuth2 v2 token endpoint template (client-credentials grant).
TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"


def get_config() -> dict[str, Any]:
    cfg = _base.yaml_block(("sharepoint_graph", "sharepoint", "graph"))
    return {
        # Graph base URL is fixed but overridable for sovereign clouds / mocks.
        "base_url": (str(cfg.get("base_url")) if cfg.get("base_url") else "")
        or _base.env("ECS_GRAPH_BASE_URL") or GRAPH_BASE,
        "tenant_id": (str(cfg.get("tenant_id")) if cfg.get("tenant_id") else "")
        or _base.env("ECS_GRAPH_TENANT_ID"),
        "client_id": (str(cfg.get("client_id")) if cfg.get("client_id") else "")
        or _base.env("ECS_GRAPH_CLIENT_ID"),
        "client_secret": _base.env(str(cfg.get("client_secret_env") or "ECS_GRAPH_CLIENT_SECRET")),
        "site_id": (str(cfg.get("site_id")) if cfg.get("site_id") else "")
        or _base.env("ECS_GRAPH_SITE_ID"),
        "drive_id": (str(cfg.get("drive_id")) if cfg.get("drive_id") else "")
        or _base.env("ECS_GRAPH_DRIVE_ID"),
        # Optional token override (e.g. supplied by an upstream token broker).
        "access_token": _base.env(str(cfg.get("access_token_env") or "ECS_GRAPH_ACCESS_TOKEN")),
        "token_url": (str(cfg.get("token_url")) if cfg.get("token_url") else "")
        or _base.env("ECS_GRAPH_TOKEN_URL"),
        "timeout_sec": _base.safe_int(
            cfg.get("timeout_sec") or _base.env("ECS_GRAPH_TIMEOUT_SECONDS"),
            _base.DEFAULT_TIMEOUT_SEC,
        ),
        "max_retries": _base.safe_int(
            cfg.get("max_retries") or _base.env("ECS_GRAPH_MAX_RETRIES"),
            _base.DEFAULT_MAX_RETRIES,
        ),
    }


def is_configured() -> bool:
    c = get_config()
    return bool(c["tenant_id"] and c["client_id"] and c["client_secret"] and c["site_id"])


def masked_config(cfg: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cfg = cfg or get_config()
    return {
        "integration": "SharePoint / Microsoft Graph",
        "base_url_configured": bool(cfg.get("base_url")),
        "tenant_id": mask_secret(cfg.get("tenant_id")),
        "client_id": mask_secret(cfg.get("client_id")),
        "client_secret": mask_secret(cfg.get("client_secret")),
        "site_id": mask_secret(cfg.get("site_id")),
        "drive_id": mask_secret(cfg.get("drive_id")),
        "access_token": mask_secret(cfg.get("access_token")),
        "timeout_sec": cfg.get("timeout_sec"),
        "max_retries": cfg.get("max_retries"),
        "ready": bool(cfg.get("tenant_id") and cfg.get("client_id")
                      and cfg.get("client_secret") and cfg.get("site_id")),
    }


@dataclass(repr=False)  # inherit BaseAdapter's secret-safe __repr__
class SharePointGraphClient(BaseAdapter):
    source: str = SOURCE
    config: dict[str, Any] = field(default_factory=get_config)
    transport: Optional[Transport] = None
    _cached_token: Optional[str] = field(default=None, repr=False, compare=False)
    _token_attempted: bool = field(default=False, repr=False, compare=False)

    def is_configured(self) -> bool:
        c = self.config
        return bool(c.get("tenant_id") and c.get("client_id")
                    and c.get("client_secret") and c.get("site_id"))

    def masked_config(self) -> dict[str, Any]:
        return masked_config(self.config)

    def _token_url(self) -> str:
        return (self.config.get("token_url")
                or TOKEN_URL_TEMPLATE.format(tenant_id=self.config.get("tenant_id", "")))

    def authenticate(self) -> Optional[str]:
        """Explicitly obtain an OAuth access token (client-credentials grant).

        Order of preference: a configured ``access_token`` (token broker), a
        cached token, otherwise a token-endpoint exchange via the injected
        transport. Attempted at most once per client (success and failure cached).
        Returns the token or ``None``; the secret/token is never logged. Call this
        before ``fetch_*`` when you want ECS (rather than the transport) to manage
        the bearer token.
        """
        if self.config.get("access_token"):
            return str(self.config["access_token"])
        if self._cached_token or self._token_attempted:
            return self._cached_token
        self._token_attempted = True
        transport = self.transport
        if transport is None:
            return None  # skeleton: no live token exchange without a transport
        payload, status = _base.call_with_retry(
            transport, "POST", self._token_url(),
            {"Accept": "application/json"},
            {"grant_type": "client_credentials",
             "client_id": self.config.get("client_id", ""),
             "client_secret": self.config.get("client_secret", ""),
             "scope": GRAPH_SCOPE},
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
        # Uses a configured/cached bearer token only — no implicit token exchange
        # here (call authenticate() first, or let the transport attach auth).
        return bearer_auth_header(self.config.get("access_token") or self._cached_token)

    def _health_path(self) -> str:
        return f"sites/{self.config.get('site_id', '')}"

    def fetch_documents(self, page_size: int = _base.DEFAULT_PAGE_SIZE,
                        max_items: int = 1000) -> dict[str, Any]:
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        drive = self.config.get("drive_id") or ""
        site = self.config.get("site_id") or ""
        path = (f"drives/{drive}/root/children" if drive
                else f"sites/{site}/drive/root/children")
        return collect_paginated(
            lambda off, lim: self._get(path, {"$top": lim, "$skip": off}),
            lambda p: list(p.get("value", []) or []),
            normalize_document,
            source=SOURCE, page_size=page_size, max_items=max_items,
        )


def normalize_document(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_id": record.get("id", ""),
        "name": record.get("name", ""),
        "size_bytes": record.get("size", 0),
        "last_modified": record.get("lastModifiedDateTime", ""),
        "web_url": record.get("webUrl", ""),
        "is_folder": "folder" in record,
        "source": SOURCE,
    }


def health_check() -> dict[str, Any]:
    return SharePointGraphClient().health_check()
