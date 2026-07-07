"""Shared Microsoft Graph connector foundation for ECS.

Common machinery for the Graph-backed evidence connectors (SharePoint, Teams,
Outlook). It reuses the shared adapter base (:mod:`_base`): the injectable
transport, retry/backoff, timeout handling, secret masking, secret-safe repr, and
the standard ``{ok, source, status, items, errors}`` response shape.

Authentication is OAuth2 **client-credentials**:
  * token endpoint: ``{authority}/{tenant_id}/oauth2/v2.0/token``
    (default authority ``https://login.microsoftonline.com``),
  * default scope: ``https://graph.microsoft.com/.default``,
  * the token is cached per client instance and applied as a Bearer header,
  * the token/secret is never logged, and there is NO live network call in tests
    (inject a transport; the default transport refuses live calls).

Graph pagination uses ``@odata.nextLink``; :func:`GraphAdapter.graph_collect`
follows it with a bounded page/item cap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from urllib.parse import urlparse

from modules.operations.integrations import _base
from modules.operations.integrations._base import (
    BaseAdapter,
    Transport,
    bearer_auth_header,
    mask_secret,
)

#: Default Microsoft Graph API base (overridable for sovereign clouds / mocks).
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
#: Default Azure AD authority (overridable for sovereign clouds).
DEFAULT_AUTHORITY = "https://login.microsoftonline.com"
#: OAuth2 v2 token endpoint template (client-credentials grant).
TOKEN_URL_TEMPLATE = "{authority}/{tenant_id}/oauth2/v2.0/token"
#: Default client-credentials scope.
GRAPH_SCOPE = "https://graph.microsoft.com/.default"

DEFAULT_MAX_PAGES = 50


def get_graph_config() -> dict[str, Any]:
    """Resolve shared Microsoft Graph config from env / YAML (secrets read, never logged).

    All Graph connectors share the same tenant/client credentials; connector-
    specific keys (site_id, team_id, user_id, ...) are added by the subclasses.
    """
    cfg = _base.yaml_block(("ms_graph", "graph", "sharepoint_graph", "sharepoint"))
    return {
        "base_url": (str(cfg.get("base_url")) if cfg.get("base_url") else "")
        or _base.env("ECS_GRAPH_BASE_URL") or GRAPH_BASE,
        "tenant_id": (str(cfg.get("tenant_id")) if cfg.get("tenant_id") else "")
        or _base.env("ECS_GRAPH_TENANT_ID"),
        "client_id": (str(cfg.get("client_id")) if cfg.get("client_id") else "")
        or _base.env("ECS_GRAPH_CLIENT_ID"),
        "client_secret": _base.env(str(cfg.get("client_secret_env") or "ECS_GRAPH_CLIENT_SECRET")),
        "scope": (str(cfg.get("scope")) if cfg.get("scope") else "")
        or _base.env("ECS_GRAPH_SCOPE") or GRAPH_SCOPE,
        "authority_url": (str(cfg.get("authority_url")) if cfg.get("authority_url") else "")
        or _base.env("ECS_GRAPH_AUTHORITY_URL") or DEFAULT_AUTHORITY,
        # Optional overrides.
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


def is_graph_configured(cfg: Optional[dict[str, Any]] = None) -> bool:
    """True when the shared Graph credentials (tenant/client id/secret) are present."""
    c = cfg or get_graph_config()
    return bool(c.get("tenant_id") and c.get("client_id") and c.get("client_secret"))


def graph_masked_config(cfg: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Secret-safe view of the shared Graph credentials (SET/MISSING only)."""
    cfg = cfg or get_graph_config()
    return {
        "tenant_id": mask_secret(cfg.get("tenant_id")),
        "client_id": mask_secret(cfg.get("client_id")),
        "client_secret": mask_secret(cfg.get("client_secret")),
        "access_token": mask_secret(cfg.get("access_token")),
        "scope": cfg.get("scope"),
        "authority_configured": bool(cfg.get("authority_url")),
        "base_url_configured": bool(cfg.get("base_url")),
        "timeout_sec": cfg.get("timeout_sec"),
        "max_retries": cfg.get("max_retries"),
    }


def normalize_error(status: Optional[str], detail: str = "") -> dict[str, Any]:
    """Uniform error record for Graph failures (never contains secrets)."""
    return {
        "ok": False,
        "status": status or "transport_error",
        "detail": detail or f"graph request failed ({status})",
    }


@dataclass(repr=False)  # inherit BaseAdapter's secret-safe __repr__
class GraphAdapter(BaseAdapter):
    """Base for Microsoft Graph connectors (SharePoint / Teams / Outlook).

    Subclasses set ``source`` and connector-specific config keys, and use
    :meth:`graph_get` / :meth:`graph_collect` for calls. Authentication (token
    acquisition) is explicit via :meth:`authenticate`; ``auth_headers`` applies a
    configured/cached token only (no implicit network I/O), matching the other
    ECS adapters.
    """

    source: str = "ms_graph"
    config: dict[str, Any] = field(default_factory=get_graph_config)
    transport: Optional[Transport] = None
    _cached_token: Optional[str] = field(default=None, repr=False, compare=False)
    _token_attempted: bool = field(default=False, repr=False, compare=False)

    # ---- configuration ---------------------------------------------------- #
    def is_configured(self) -> bool:
        return is_graph_configured(self.config)

    def masked_config(self) -> dict[str, Any]:
        return {"integration": self.source, **graph_masked_config(self.config)}

    def scope(self) -> str:
        return str(self.config.get("scope") or GRAPH_SCOPE)

    def _token_url(self) -> str:
        if self.config.get("token_url"):
            return str(self.config["token_url"])
        authority = str(self.config.get("authority_url") or DEFAULT_AUTHORITY).rstrip("/")
        return TOKEN_URL_TEMPLATE.format(authority=authority,
                                         tenant_id=self.config.get("tenant_id", ""))

    # ---- authentication --------------------------------------------------- #
    def authenticate(self) -> Optional[str]:
        """Obtain an OAuth2 client-credentials access token (cached per instance).

        Order of preference: a configured ``access_token`` (token broker), a
        cached token, otherwise a token-endpoint exchange via the injected
        transport. Attempted at most once per client (success and failure cached).
        Returns the token or ``None``; the secret/token is never logged.
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
            {"Accept": "application/json",
             "Content-Type": "application/x-www-form-urlencoded"},
            {"grant_type": "client_credentials",
             "client_id": self.config.get("client_id", ""),
             "client_secret": self.config.get("client_secret", ""),
             "scope": self.scope()},
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
        # Configured/cached bearer only — no implicit token exchange here.
        return bearer_auth_header(self.config.get("access_token") or self._cached_token)

    # ---- transport helpers ------------------------------------------------ #
    def graph_get(self, path: str, params: Optional[dict] = None
                  ) -> tuple[Optional[dict], Optional[str]]:
        """GET a Graph resource (relative path or absolute URL). Never raises.

        Auto-authenticates first (so callers do not have to remember), then issues
        the request through the retry/timeout machinery.
        """
        if not self.is_configured():
            return None, "not_configured"
        self.authenticate()
        transport = self.transport or _base._default_transport(self.source)
        url = path if _is_absolute_url(path) else f"{self.base_url()}/{path.lstrip('/')}"
        return _base.call_with_retry(
            transport, "GET", url, self.headers(), params or {},
            max_retries=self.max_retries(),
            backoff_base=self.backoff_base_sec(),
            timeout=self.timeout_sec(),
        )

    def graph_post(self, path: str, body: Optional[dict] = None
                   ) -> tuple[Optional[dict], Optional[str]]:
        """POST to a Graph resource (relative path or absolute URL). Never raises."""
        if not self.is_configured():
            return None, "not_configured"
        self.authenticate()
        transport = self.transport or _base._default_transport(self.source)
        url = path if _is_absolute_url(path) else f"{self.base_url()}/{path.lstrip('/')}"
        return _base.call_with_retry(
            transport, "POST", url, self.headers(), body or {},
            max_retries=self.max_retries(),
            backoff_base=self.backoff_base_sec(),
            timeout=self.timeout_sec(),
        )

    def graph_collect(
        self,
        path: str,
        normalize: Callable[[dict[str, Any]], dict[str, Any]],
        *,
        params: Optional[dict] = None,
        max_items: int = 1000,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> dict[str, Any]:
        """Follow ``@odata.nextLink`` pagination and return a standard response.

        Extracts items from the ``value`` array of each page, normalizes them, and
        stops at the last page, ``max_items``, or ``max_pages`` (safety cap).
        Returns a classified error response on any failure (never raises).
        """
        if not self.is_configured():
            return _base.not_configured_response(self.source)
        items: list[dict[str, Any]] = []
        next_url: Optional[str] = None
        for page_index in range(max_pages):
            if page_index == 0:
                payload, status = self.graph_get(path, params)
            else:
                if not next_url:
                    break
                payload, status = self.graph_get(next_url)
            if status is not None:
                return _base.error_response(self.source, status,
                                            f"fetch failed ({status})")
            payload = payload or {}
            page = list(payload.get("value", []) or [])
            items.extend(page)
            if len(items) >= max_items:
                break
            next_url = payload.get("@odata.nextLink")
            if not next_url:
                break
        return _base.ok_response(self.source, [normalize(x) for x in items[:max_items]])

    def graph_get_one(
        self,
        path: str,
        normalize: Callable[[dict[str, Any]], dict[str, Any]],
        *,
        params: Optional[dict] = None,
    ) -> dict[str, Any]:
        """GET a single Graph resource and return a normalized standard response."""
        if not self.is_configured():
            return _base.not_configured_response(self.source)
        payload, status = self.graph_get(path, params)
        if status is not None:
            return _base.error_response(self.source, status, f"fetch failed ({status})")
        return _base.ok_response(self.source, [normalize(payload or {})])


def _is_absolute_url(path: str) -> bool:
    try:
        return bool(urlparse(path).scheme)
    except (TypeError, ValueError):
        return False


# --------------------------------------------------------------------------- #
# Shared identity/date normalization helpers (used by SharePoint/Teams/Outlook)
# --------------------------------------------------------------------------- #
def identity_name(node: Any) -> str:
    """Extract a display name from a Graph identitySet/user node (non-secret)."""
    if not isinstance(node, dict):
        return ""
    # identitySet: {"user": {"displayName": ...}} | direct {"displayName": ...}
    user = node.get("user") if isinstance(node.get("user"), dict) else node
    if isinstance(user, dict):
        return str(user.get("displayName") or user.get("email") or "")
    return ""


def health_check() -> dict[str, Any]:
    """Config-based readiness for the shared Graph credentials (no live probe)."""
    cfg = get_graph_config()
    source = "ms_graph"
    if not is_graph_configured(cfg):
        return {**_base.not_configured_response(source), "configured": False,
                "masked_config": {"integration": source, **graph_masked_config(cfg)}}
    return {"ok": True, "source": source, "status": "ok", "configured": True,
            "items": [], "errors": [],
            "masked_config": {"integration": source, **graph_masked_config(cfg)}}
