"""Shared machinery for ECS enterprise integration adapters.

Every adapter (ServiceNow, Archer, SharePoint/Graph, Jira, Confluence, SonarQube,
Checkmarx, Prisma Cloud, Tripwire) is a config-driven *skeleton*: credentials come
from the environment/YAML only (never hard-coded, never logged), the HTTP transport
is injectable so unit tests supply mocked responses (no real API calls), and every
adapter exposes a consistent interface + response shape.

Consistent response format (used by fetch_*/health_check):
    {
      "ok": bool,
      "source": "<adapter>",
      "status": "ok" | "not_configured" | "auth_error" | "timeout" |
                "connection_error" | "http_error" | "transport_error" | "empty",
      "items": [...],
      "errors": [...],
    }

Safety guarantees:
  * ``mask_secret`` / ``masked_config`` never reveal secret values (SET/MISSING).
  * ``call_with_retry`` applies bounded retries with backoff and never raises to
    the caller — failures are classified into the status vocabulary above.
  * Missing configuration degrades gracefully (status="not_configured").
"""

from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

DEFAULT_TIMEOUT_SEC = 30
DEFAULT_MAX_RETRIES = 2          # total attempts = 1 + retries
DEFAULT_BACKOFF_BASE_SEC = 0.0   # 0 in tests; real transports can raise this
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000

#: An HTTP transport is a callable: (method, url, headers, params) -> dict (JSON).
#: Production transports MAY additionally accept a ``timeout`` keyword; the retry
#: helper passes it only when the transport advertises support, so simple test
#: mocks with the ``(method, url, headers, params)`` signature keep working.
Transport = Callable[..., dict]


class IntegrationNotConfigured(RuntimeError):
    """Raised internally when an adapter is used without required configuration."""


class IntegrationAuthError(RuntimeError):
    """Raised by a transport to signal an authentication/authorization failure."""


class IntegrationTimeout(RuntimeError):
    """Raised by a transport to signal a timeout."""


# --------------------------------------------------------------------------- #
# Config helpers
# --------------------------------------------------------------------------- #
def safe_int(value: Any, default: int) -> int:
    """Parse an int, tolerating unresolved ``${VAR}`` placeholders and blanks."""
    try:
        s = str(value).strip()
        if not s or s.startswith("${"):
            return default
        return int(float(s))
    except (TypeError, ValueError):
        return default


def env(name: str, default: str = "") -> str:
    val = os.environ.get(name, default)
    # Treat an unresolved placeholder as unset.
    return "" if isinstance(val, str) and val.startswith("${") else val


def yaml_block(keys: tuple[str, ...]) -> dict[str, Any]:
    """Resolve an adapter's YAML block from connectors/integrations sections."""
    try:
        from modules.operations.integrations import lookup_yaml_config

        return lookup_yaml_config(keys)
    except Exception:  # noqa: BLE001
        return {}


def mask_secret(value: Any) -> str:
    """Return SET / MISSING for a secret — never the value itself."""
    return "SET" if value not in (None, "") else "MISSING"


# --------------------------------------------------------------------------- #
# Auth header builders (never logged; only assembled at request time)
# --------------------------------------------------------------------------- #
def basic_auth_header(username: Any, secret: Any) -> dict[str, str]:
    """Build an HTTP Basic ``Authorization`` header from a username + secret.

    Returns ``{}`` when either credential is missing so unconfigured adapters do
    not emit a malformed header. The encoded value is assembled on demand and is
    never logged (callers pass the returned dict straight to the transport).
    """
    if not username or not secret:
        return {}
    raw = f"{username}:{secret}".encode("utf-8")
    return {"Authorization": "Basic " + base64.b64encode(raw).decode("ascii")}


def bearer_auth_header(token: Any) -> dict[str, str]:
    """Build a ``Bearer`` ``Authorization`` header. Empty dict when no token."""
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def json_headers(extra: Optional[dict[str, str]] = None) -> dict[str, str]:
    """Standard JSON request headers, merged with any adapter-specific extras."""
    headers = {"Accept": "application/json"}
    if extra:
        headers.update(extra)
    return headers


def clamp_page_size(size: Any, default: int = DEFAULT_PAGE_SIZE) -> int:
    n = safe_int(size, default)
    if n <= 0:
        return default
    return min(n, MAX_PAGE_SIZE)


# --------------------------------------------------------------------------- #
# Standard responses
# --------------------------------------------------------------------------- #
def ok_response(source: str, items: list[Any], status: str = "ok") -> dict[str, Any]:
    if not items and status == "ok":
        status = "empty"
    return {"ok": True, "source": source, "status": status, "items": list(items), "errors": []}


def error_response(source: str, status: str, message: str) -> dict[str, Any]:
    return {"ok": False, "source": source, "status": status, "items": [], "errors": [message]}


def not_configured_response(source: str) -> dict[str, Any]:
    return error_response(source, "not_configured",
                          f"{source} is not configured (set the required environment variables).")


# --------------------------------------------------------------------------- #
# Retry / backoff + error classification
# --------------------------------------------------------------------------- #
def classify_exception(exc: Exception) -> str:
    """Map an exception to the status vocabulary (never leaks secret detail)."""
    if isinstance(exc, IntegrationNotConfigured):
        return "not_configured"
    if isinstance(exc, IntegrationAuthError):
        return "auth_error"
    if isinstance(exc, IntegrationTimeout) or isinstance(exc, TimeoutError):
        return "timeout"
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    if "timeout" in name or "timeout" in msg:
        return "timeout"
    if "auth" in msg or "401" in msg or "403" in msg or "unauthor" in msg or "forbidden" in msg:
        return "auth_error"
    if "connection" in name or "connection" in msg or "refused" in msg or "dns" in msg or "resolve" in msg:
        return "connection_error"
    if "http" in name or any(code in msg for code in ("500", "502", "503", "504", "404", "400")):
        return "http_error"
    return "transport_error"


def _transport_accepts_timeout(transport: Transport) -> bool:
    """True when ``transport`` declares a ``timeout`` parameter (or **kwargs).

    Lets production transports receive a per-call timeout while keeping simple
    4-positional test mocks working (they are called without the kwarg).
    """
    try:
        import inspect

        params = inspect.signature(transport).parameters
        for p in params.values():
            if p.kind is inspect.Parameter.VAR_KEYWORD:
                return True
        return "timeout" in params
    except (TypeError, ValueError):
        return False


def _invoke_transport(
    transport: Transport,
    method: str,
    url: str,
    headers: dict,
    params: dict,
    timeout: Optional[int],
) -> dict:
    """Call the transport, passing ``timeout`` only when it is supported."""
    if timeout is not None and _transport_accepts_timeout(transport):
        return transport(method, url, headers, params, timeout=timeout)
    return transport(method, url, headers, params)


def call_with_retry(
    transport: Transport,
    method: str,
    url: str,
    headers: dict,
    params: dict,
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_base: float = DEFAULT_BACKOFF_BASE_SEC,
    timeout: Optional[int] = None,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[Optional[dict], Optional[str]]:
    """Call a transport with bounded retries + backoff.

    Returns ``(payload, None)`` on success or ``(None, status)`` on failure, where
    status is from the classification vocabulary. Never raises. Auth/not-configured
    failures are NOT retried (they will not self-heal); timeouts/connection/http are.

    ``timeout`` (when provided) is forwarded to transports that accept it; simple
    test mocks without a ``timeout`` parameter are called unchanged.
    """
    attempts = max(1, 1 + max_retries)
    last_status = "transport_error"
    for i in range(attempts):
        try:
            payload = _invoke_transport(transport, method, url, headers, params, timeout)
            return payload, None
        except Exception as exc:  # noqa: BLE001 - classified, never propagated
            last_status = classify_exception(exc)
            if last_status in ("auth_error", "not_configured"):
                break  # non-retryable
            if i < attempts - 1 and backoff_base > 0:
                sleep(backoff_base * (2 ** i))
    return None, last_status


# --------------------------------------------------------------------------- #
# Pagination
# --------------------------------------------------------------------------- #
def paginate(
    fetch_page: Callable[[int, int], list[dict[str, Any]]],
    *,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_items: int = 1000,
    max_pages: int = 50,
) -> list[dict[str, Any]]:
    """Generic offset pagination over a ``fetch_page(offset, limit)`` callable.

    Stops when a page is short (last page), max_items is reached, or max_pages is
    hit (safety cap). Deterministic and bounded — safe for tests.
    """
    page_size = clamp_page_size(page_size)
    items: list[dict[str, Any]] = []
    offset = 0
    for _ in range(max_pages):
        page = fetch_page(offset, page_size) or []
        items.extend(page)
        if len(page) < page_size or len(items) >= max_items:
            break
        offset += page_size
    return items[:max_items]


def collect_paginated(
    page_getter: Callable[[int, int], tuple[Optional[dict], Optional[str]]],
    extract: Callable[[dict], list[dict[str, Any]]],
    normalize: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    source: str,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_items: int = 1000,
    max_pages: int = 50,
) -> dict[str, Any]:
    """Paginate transport calls and return a standard response (no raising).

    ``page_getter(offset, limit)`` returns ``(payload, status)`` (as from
    ``BaseAdapter._get``). On any non-None status the pagination stops and a
    classified error response is returned. Otherwise items are extracted +
    normalized and wrapped in an ``ok_response``.
    """
    page_size = clamp_page_size(page_size)
    items: list[dict[str, Any]] = []
    offset = 0
    for _ in range(max_pages):
        payload, status = page_getter(offset, page_size)
        if status is not None:
            return error_response(source, status, f"fetch failed ({status})")
        page = extract(payload or {}) or []
        items.extend(page)
        if len(page) < page_size or len(items) >= max_items:
            break
        offset += page_size
    return ok_response(source, [normalize(x) for x in items[:max_items]])


# --------------------------------------------------------------------------- #
# Base adapter
# --------------------------------------------------------------------------- #
@dataclass
class BaseAdapter:
    """Common base for integration adapters.

    Subclasses set ``source`` and ``base_url``/secret fields via ``config`` and use
    ``_get(path, params)`` for transport calls. The default transport refuses live
    calls (skeleton) so nothing hits a network unless a real transport is injected.
    """

    source: str = "integration"
    config: dict[str, Any] = field(default_factory=dict)
    transport: Optional[Transport] = None

    def __repr__(self) -> str:
        # Secret-safe repr: never render the raw config (it holds credentials),
        # so tokens cannot leak into logs/tracebacks. Show the masked view only.
        try:
            masked = self.masked_config()
        except Exception:  # noqa: BLE001 - repr must never raise
            masked = {"integration": self.source}
        return (f"{type(self).__name__}(source={self.source!r}, "
                f"configured={self._safe_is_configured()}, masked_config={masked})")

    def _safe_is_configured(self) -> bool:
        try:
            return self.is_configured()
        except Exception:  # noqa: BLE001
            return False

    # ---- configuration ---------------------------------------------------- #
    def is_configured(self) -> bool:
        return bool(self.config.get("base_url"))

    def base_url(self) -> str:
        return str(self.config.get("base_url") or "").rstrip("/")

    def timeout_sec(self) -> int:
        return safe_int(self.config.get("timeout_sec"), DEFAULT_TIMEOUT_SEC)

    def max_retries(self) -> int:
        n = safe_int(self.config.get("max_retries"), DEFAULT_MAX_RETRIES)
        return max(0, n)

    def backoff_base_sec(self) -> float:
        try:
            v = self.config.get("backoff_base_sec")
            s = str(v).strip()
            if not s or s.startswith("${"):
                return DEFAULT_BACKOFF_BASE_SEC
            return max(0.0, float(s))
        except (TypeError, ValueError):
            return DEFAULT_BACKOFF_BASE_SEC

    def auth_headers(self) -> dict:  # overridden by subclasses that add auth
        """Adapter-specific auth headers (empty in the base). Never logged."""
        return {}

    def headers(self) -> dict:
        """JSON headers merged with adapter auth headers (assembled per request)."""
        return json_headers(self.auth_headers())

    def masked_config(self) -> dict[str, Any]:  # overridden per adapter
        return {
            "integration": self.source,
            "base_url_configured": self.is_configured(),
            "timeout_sec": self.timeout_sec(),
        }

    # ---- transport -------------------------------------------------------- #
    def _get(self, path: str, params: Optional[dict] = None) -> tuple[Optional[dict], Optional[str]]:
        if not self.is_configured():
            return None, "not_configured"
        transport = self.transport or _default_transport(self.source)
        url = f"{self.base_url()}/{path.lstrip('/')}"
        return call_with_retry(
            transport, "GET", url, self.headers(), params or {},
            max_retries=self.max_retries(),
            backoff_base=self.backoff_base_sec(),
            timeout=self.timeout_sec(),
        )

    # ---- health ----------------------------------------------------------- #
    def health_check(self) -> dict[str, Any]:
        """Lightweight readiness probe. Never raises; never reveals secrets.

        When not configured, returns not_configured. When a transport is present,
        performs a single classified probe call to the adapter's health path.
        """
        if not self.is_configured():
            return {**not_configured_response(self.source), "configured": False,
                    "masked_config": self.masked_config()}
        payload, status = self._get(self._health_path())
        if status is None:
            return {"ok": True, "source": self.source, "status": "ok",
                    "configured": True, "items": [], "errors": [],
                    "masked_config": self.masked_config()}
        return {**error_response(self.source, status, f"health check failed ({status})"),
                "configured": True, "masked_config": self.masked_config()}

    def _health_path(self) -> str:  # overridden per adapter
        return ""


def _default_transport(source: str) -> Transport:
    def _t(method: str, url: str, headers: dict, params: dict) -> dict:
        raise IntegrationNotConfigured(
            f"{source} live transport is not wired in the skeleton. Inject a "
            f"transport (mock in tests) or provide a production HTTP client."
        )
    return _t


# --------------------------------------------------------------------------- #
# Production HTTP transport (opt-in; wraps the stdlib client — no new dependency)
# --------------------------------------------------------------------------- #
def build_http_transport(*, verify_ssl: bool = True, max_retries: int = 1) -> Transport:
    """Return a REAL HTTP ``Transport`` backed by the stdlib connector client.

    This is the production counterpart to :func:`_default_transport`. It performs
    an actual network request and returns parsed JSON, so an adapter constructed
    with ``transport=build_http_transport()`` collects live data. It is **never**
    the adapter default — a caller (e.g. the connector executor) must inject it
    explicitly, so nothing hits a network implicitly and tests/dry-run stay offline.

    Reuses :class:`ecs_platform.connectors.http_client.HttpClient` (urllib, already
    in the repo) rather than adding ``requests``/``httpx``. Auth headers are passed
    straight through from the adapter (assembled per request; never logged here).

    Errors are translated into this module's vocabulary so ``call_with_retry`` /
    ``classify_exception`` produce the right status:
      * HTTP 401/403                -> :class:`IntegrationAuthError`
      * connection error / timeout  -> :class:`IntegrationTimeout` (retryable class)
      * other HTTP errors           -> ``RuntimeError`` ("http_error"/... classified)
    """
    from ecs_platform.connectors.http_client import HttpClient, HttpError

    def _t(method: str, url: str, headers: dict, params: dict, timeout: int = DEFAULT_TIMEOUT_SEC) -> dict:
        # A fresh client per call keeps this stateless + thread-safe; the URL is
        # already absolute (adapters build base_url + path), so base_url stays "".
        client = HttpClient(
            base_url="",
            timeout_sec=safe_int(timeout, DEFAULT_TIMEOUT_SEC),
            max_retries=max(1, max_retries),
            verify_ssl=verify_ssl,
            default_headers={},
        )
        try:
            resp = client.request(method, url, params=params or {}, headers=headers or {})
        except HttpError as exc:
            status = getattr(exc, "status", 0)
            if status in (401, 403):
                raise IntegrationAuthError(f"auth failed ({status})") from exc
            if status == 0:
                # status 0 == connection/timeout in the stdlib client vocabulary.
                raise IntegrationTimeout(str(exc)) from exc
            raise RuntimeError(f"http_error {status}") from exc
        data = resp.json()
        # Adapters expect a JSON object; wrap bare arrays / null defensively so a
        # non-dict body never crashes a normalizer that does ``payload.get(...)``.
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {"value": data, "items": data, "results": data}
        return {}

    return _t
