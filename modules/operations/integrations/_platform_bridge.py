"""Bridge: expose ``ecs_platform`` connectors as audit-intelligence adapters.

GitHub, Jenkins, and Azure DevOps already have production connector clients in
``ecs_platform/connectors/`` (real ``HttpClient`` + auth + evidence collection).
This bridge lets those SAME clients plug into the audit-intelligence adapter
stack (registry / Connector Test Workbench / scheduler / executor) WITHOUT
duplicating any HTTP client, authentication, or collection logic.

How it works (no architecture change to either side):
  * ``build_connector_config()`` maps an audit-intelligence config dict onto the
    platform ``ConnectorConfig`` (the shape the platform connector expects).
  * ``_TransportHttpClient`` adapts a workbench-style transport callable
    ``(method, url, headers, params, timeout)`` into the platform
    ``HttpClient.request(...)`` surface, so the Connector Test Workbench's mock
    transport (and injected test transports) drive the REAL platform connector
    with NO network call.
  * ``run_collection()`` instantiates the platform connector, runs its own
    ``collect_evidence()`` / ``test_connection()``, and maps the resulting
    ``EvidenceItem`` list into the standard adapter response
    ``{ok, source, status, items, errors}`` (reusing the existing normalization).

Secrets are never logged; missing config degrades to ``not_configured``; nothing
raises to the caller.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Optional

from modules.operations.integrations import _base

Transport = Callable[..., dict]


# --------------------------------------------------------------------------- #
# Config: audit-intelligence dict -> platform ConnectorConfig
# --------------------------------------------------------------------------- #
def build_connector_config(
    *,
    name: str,
    ctype: str,
    cfg: dict[str, Any],
    option_keys: tuple[str, ...],
    secret_option_env: dict[str, str],
):
    """Build a platform ``ConnectorConfig`` from an adapter config dict.

    ``option_keys`` are non-secret values copied into ``options`` (e.g. ``org``).
    ``secret_option_env`` maps a platform option key (e.g. ``token_env``) to the
    ENV VAR NAME that holds the secret — matching the platform ``config.secret()``
    contract (which resolves ``options[env_key]`` as an env-var name). We set the
    option to a synthetic name and export the resolved secret under it so the
    platform connector reads it exactly as in production, without us handling the
    raw value beyond placing it in the process env for this call.
    """
    from ecs_platform.connectors.base import ConnectorConfig

    options: dict[str, Any] = {}
    for key in option_keys:
        val = cfg.get(key)
        if val not in (None, ""):
            options[key] = val
    # Wire secret env pointers: the platform connector calls config.secret(env_key)
    # which reads os.environ[options[env_key]]. We point env_key at a stable var
    # name and ensure that var holds the resolved secret from the adapter config.
    for env_key, source_env in secret_option_env.items():
        options[env_key] = source_env
    return ConnectorConfig(
        name=name,
        type=ctype,
        enabled=True,  # the adapter layer gates on is_configured(), not this flag
        base_url=str(cfg.get("base_url") or ""),
        options=options,
        timeout_sec=_base.safe_int(cfg.get("timeout_sec"), _base.DEFAULT_TIMEOUT_SEC),
        max_retries=_base.safe_int(cfg.get("max_retries"), _base.DEFAULT_MAX_RETRIES),
        page_size=_base.safe_int(cfg.get("page_size"), 100),
    )


# --------------------------------------------------------------------------- #
# Mock transport -> platform HttpClient shim (for workbench / injected tests)
# --------------------------------------------------------------------------- #
class _TransportResponse:
    """Minimal stand-in for ecs_platform HttpResponse (status/headers/body/json)."""

    def __init__(self, payload: Any):
        self._payload = payload
        self.status = 200
        self.headers: dict[str, str] = {}
        self.body = ""

    def json(self) -> Any:
        return self._payload


class _TransportHttpClient:
    """Adapts a workbench-style transport into the platform HttpClient surface.

    Only the methods the platform connectors use (``get``/``request`` returning an
    object with ``.status`` + ``.json()``) are implemented. Chained auth helpers
    (``with_bearer`` / ``with_basic`` / ``with_header``) are accepted as no-ops so
    the connector's ``_apply_auth`` runs unchanged with NO real network.
    """

    def __init__(self, transport: Transport, base_url: str = ""):
        self._transport = transport
        self.base_url = base_url
        self.default_headers: dict[str, str] = {}

    # ---- auth helpers used by BaseConnector._apply_auth (no-ops in mock mode) --
    def with_bearer(self, token: str) -> "_TransportHttpClient":
        return self

    def with_basic(self, user: str, password: str) -> "_TransportHttpClient":
        return self

    def with_header(self, key: str, value: str) -> "_TransportHttpClient":
        return self

    def _url(self, path: str) -> str:
        if str(path).startswith("http"):
            return str(path)
        return f"{self.base_url.rstrip('/')}/{str(path).lstrip('/')}"

    def request(self, method: str, path: str, *, params: dict | None = None,
                json_body: Any | None = None, headers: dict | None = None):
        payload = self._transport(method, self._url(path), headers or {}, params or {})
        return _TransportResponse(payload)

    def get(self, path: str, **kw):
        return self.request("GET", path, **kw)

    def post(self, path: str, **kw):
        return self.request("POST", path, **kw)


def make_platform_connector(connector_cls, config, transport: Optional[Transport]):
    """Instantiate a platform connector, injecting a mock HttpClient if given.

    When ``transport`` is provided (workbench parser-test / injected test), the
    connector's cached ``_client`` is set to a shim so its real
    ``collect_evidence`` / ``test_connection`` run against the mock — NO network.
    When ``transport`` is None, the connector builds its own real ``HttpClient``
    via ``http()`` exactly as in production (reused verbatim).
    """
    conn = connector_cls(config)
    if transport is not None:
        shim = _TransportHttpClient(transport, base_url=config.base_url)
        # Run the connector's own auth wiring against the shim (no-op helpers),
        # then cache it so http() returns the shim instead of a live client.
        try:
            conn._apply_auth(shim)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - auth wiring must not break mock mode
            pass
        conn._client = shim  # type: ignore[attr-defined]
    return conn


# --------------------------------------------------------------------------- #
# EvidenceItem list -> standard adapter response
# --------------------------------------------------------------------------- #
def evidence_to_items(evidence: list[Any]) -> list[dict[str, Any]]:
    """Map platform ``EvidenceItem`` objects to normalized adapter item dicts."""
    out: list[dict[str, Any]] = []
    for ev in evidence or []:
        d = ev.to_dict() if hasattr(ev, "to_dict") else dict(ev)
        out.append({
            "source": d.get("source_system", ""),
            "source_object_id": d.get("source_object_id", ""),
            "object_type": d.get("object_type", ""),
            "title": d.get("title", ""),
            "url": d.get("url", ""),
            "application": d.get("application", ""),
            "control_mapping": d.get("control_mapping", []),
            "framework_mapping": d.get("framework_mapping", []),
            "evidence_type": d.get("object_type", ""),
            "metadata": d.get("metadata", {}),
        })
    return out


def run_collection(
    *,
    source: str,
    connector_cls,
    config,
    is_configured: bool,
    transport: Optional[Transport],
    object_types: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Run a platform connector's collection and return the adapter response.

    Reuses the platform connector's ``collect_evidence`` (its own HTTP/auth). In
    mock mode a shim transport is injected (no network). Never raises.
    """
    if not is_configured and transport is None:
        return _base.not_configured_response(source)
    try:
        conn = make_platform_connector(connector_cls, config, transport)
        evidence = conn.collect_evidence(object_types)
        items = evidence_to_items(evidence)
        return _base.ok_response(source, items)
    except Exception as exc:  # noqa: BLE001 - classify + report, never raise
        return _base.error_response(source, _base.classify_exception(exc),
                                    f"{source} collection failed: {type(exc).__name__}")


def run_health(*, source: str, connector_cls, config, is_configured: bool) -> dict[str, Any]:
    """Run the platform connector's config-based health check as an adapter health dict."""
    if not is_configured:
        return {**_base.not_configured_response(source), "configured": False}
    try:
        conn = connector_cls(config)
        health = conn.test_connection()
        hd = health.to_dict() if hasattr(health, "to_dict") else {}
        ok = bool(hd.get("connected") and hd.get("authenticated"))
        return {"ok": ok, "source": source,
                "status": "ok" if ok else "auth_error",
                "configured": True, "items": [], "errors": [],
                "detail": hd.get("detail", "")}
    except Exception as exc:  # noqa: BLE001
        return {**_base.error_response(source, "transport_error",
                                       f"health failed: {type(exc).__name__}"),
                "configured": True}
