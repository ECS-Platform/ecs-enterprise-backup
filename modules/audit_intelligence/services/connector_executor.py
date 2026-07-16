"""Connector execution + evidence ingestion (opt-in, live).

This closes the genuine gap between the enterprise integration *adapters*
(:mod:`modules.operations.integrations`) and the ECS evidence repository: the
adapters can fetch + normalize, but nothing wired their normalized output into
stored evidence, and the asset scheduler explicitly skipped connector jobs.

This service is the thin bridge — it **reuses** existing pieces and adds no new
connector, HTTP, hashing, or evidence-store logic:

  * the adapter client + primary ``fetch_*`` method map from the Connector Test
    Workbench (:data:`connector_workbench._ADAPTER_TESTS`),
  * the **real** HTTP transport factory (``integrations.build_http_transport``),
  * the existing evidence bridge
    (``operations.evidence_repository.register_upload`` → which already mirrors
    into the audit-intelligence evidence repository).

Safety guarantees:
  * **Opt-in / offline by default.** Live collection requires BOTH the flag
    ``ECS_CONNECTOR_EXECUTION_ENABLED=true`` AND a configured adapter, OR an
    explicitly injected ``transport`` (used by tests). Otherwise the call is a
    no-op that reports ``skipped``/``not_configured`` — it never hits a network.
  * **Read-only upstream.** Only adapter ``fetch_*`` (GET) methods run.
  * **Bounded.** ``max_items`` caps how many normalized objects become evidence.
  * **Never raises** to the caller; failures are classified + returned.
  * Secrets are never logged or returned (adapters assemble auth per request).
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Optional

from modules.audit_intelligence.services.connector_workbench import (
    _ADAPTER_TESTS,
    _TEST_STUB_CONFIG,
    _adapter_module,
    _known,
)

#: Env flag that must be truthy for *implicit* live collection (configured adapter
#: + real transport). An explicitly injected transport bypasses the flag (tests).
EXECUTION_FLAG = "ECS_CONNECTOR_EXECUTION_ENABLED"

#: Safety cap: max normalized objects ingested as evidence per connector run.
DEFAULT_MAX_ITEMS = 200


def execution_enabled() -> bool:
    """True when live connector execution is explicitly enabled via env flag."""
    return os.environ.get(EXECUTION_FLAG, "").strip().lower() in ("1", "true", "yes", "on")


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _demo_mode_enabled() -> bool:
    """True when global demo mode is explicitly enabled."""
    return _truthy(os.environ.get("DEMO_MODE", ""))


def _workbench_mock_transport(payload: Any) -> Callable[..., dict]:
    """Deterministic mock transport used for demo fallback collection."""
    def t(method, url, headers, params, timeout=None):
        u = str(url)
        if u.endswith("/oauth2/v2.0/token") or u.endswith("/oauth_token.do") \
                or u.endswith("/protocol/openid-connect/token"):
            return {"access_token": "WORKBENCH-MOCK"}
        if u.endswith("/login"):
            return {"token": "WORKBENCH-MOCK"}
        return payload if isinstance(payload, dict) else {"value": list(payload or [])}
    return t


# --------------------------------------------------------------------------- #
# Evidence bridge
# --------------------------------------------------------------------------- #
def _item_to_content(item: dict[str, Any]) -> bytes:
    """Serialize one normalized connector object into deterministic evidence bytes."""
    try:
        return json.dumps(item, sort_keys=True, default=str).encode("utf-8")
    except (TypeError, ValueError):
        return str(item).encode("utf-8")


def _item_filename(connector: str, item: dict[str, Any], index: int) -> str:
    """Build a stable, human-readable filename for a collected evidence object."""
    ident = (
        item.get("id")
        or item.get("evidence_id")
        or item.get("key")
        or item.get("sys_id")
        or item.get("name")
        or f"{index:04d}"
    )
    safe = "".join(c if (c.isalnum() or c in "._-") else "_" for c in str(ident))[:60]
    return f"{connector}_{safe}.json"


def _ingest_items(
    connector: str,
    items: list[dict[str, Any]],
    *,
    framework: str,
    application: str,
    control: str,
    collected_by: str,
    max_items: int,
    transport: Optional[Callable[..., dict]] = None,
) -> list[dict[str, Any]]:
    """Bridge normalized connector objects into evidence via ``register_upload``.

    Reuses the manual/bulk upload bridge (which SHA-256s, versions, and mirrors
    into the audit-intelligence repository). Returns per-item ingestion receipts.
    """
    from modules.operations.engines import evidence_repository as ops_repo

    receipts: list[dict[str, Any]] = []
    for idx, item in enumerate(items[: max(0, max_items)]):
        if not isinstance(item, dict):
            item = {"value": item}
        try:
            source_item_id = str(
                item.get("item_id") or item.get("id") or item.get("source_object_id") or "",
            )
            source_url = str(item.get("web_url") or item.get("url") or "")
            source_modified = str(
                item.get("modified_datetime") or item.get("last_modified") or "",
            )
            mime_type = str(item.get("mime_type") or "")
            environment = str(item.get("environment") or "")
            item_control = str(
                item.get("control_or_observation") or control or "",
            )
            item_framework = str(item.get("framework") or framework or "")
            filename = str(
                item.get("filename") or item.get("name") or _item_filename(connector, item, idx),
            )
            metadata = {
                k: str(v)
                for k, v in item.items()
                if k not in {"content_bytes", "content"}
            }
            content = item.get("content_bytes")
            if content is None and isinstance(item.get("content"), (bytes, bytearray)):
                content = item.get("content")
            if content is None:
                from modules.audit_intelligence.services import evidence_custody as custody

                if (
                    custody.snapshot_enabled()
                    and connector == "sharepoint_graph"
                    and source_item_id
                ):
                    try:
                        from modules.operations.integrations import sharepoint_graph as sp

                        client = sp.SharePointGraphClient(transport=transport)
                        fetched = client.stream_file_content(
                            source_item_id,
                            drive_id=str(item.get("drive_id") or ""),
                        )
                        if fetched.get("ok"):
                            content = fetched.get("content_bytes")
                    except Exception:  # noqa: BLE001
                        content = None
            if content is None:
                content = _item_to_content(item)
            record = ops_repo.register_upload(
                filename=filename,
                content=content if isinstance(content, (bytes, bytearray)) else str(content).encode(),
                uploaded_by=collected_by,
                framework=item_framework,
                application=application or "Net Banking",
                control=item_control,
                source_connector=connector,
                source_item_id=source_item_id,
                source_url=source_url,
                environment=environment,
                mime_type=mime_type,
                metadata=metadata,
                source_modified_at=source_modified,
            )
            receipts.append({
                "evidence_id": record.get("evidence_id"),
                "filename": record.get("filename"),
                "audit_repository_synced": record.get("audit_repository_synced", False),
                "sha256": record.get("sha256"),
                "custody_mode": record.get("custody_mode"),
                "object_uri": record.get("object_uri", ""),
            })
        except Exception as exc:  # noqa: BLE001 - one bad item must not abort the run
            receipts.append({"error": type(exc).__name__, "index": idx})
    return receipts


# --------------------------------------------------------------------------- #
# Adapter fetch (live, with an injected real transport)
# --------------------------------------------------------------------------- #
def _run_adapter_fetch(
    connector: str,
    *,
    transport: Optional[Callable[..., dict]],
    verify_ssl: bool = True,
) -> dict[str, Any]:
    """Construct the adapter's client with a transport and run its primary fetch.

    Returns the adapter's standard ``{ok, status, items, ...}`` response, or a
    classified error dict. Never raises.
    """
    meta = _ADAPTER_TESTS.get(connector)
    if not meta:
        return {"ok": False, "status": "not_supported", "items": [],
                "errors": ["connector has no execution mapping"]}
    try:
        mod = _adapter_module(connector)
        client_cls = getattr(mod, meta["client"])
        cfg = mod.get_config()
        # Build the real transport lazily unless the caller injected one (tests).
        active_transport = transport
        if active_transport is None:
            from modules.operations.integrations import build_http_transport

            active_transport = build_http_transport(verify_ssl=verify_ssl)
        elif not mod.is_configured():
            # An injected transport means mock/test mode: merge a harmless non-secret
            # stub config so the adapter's parse path can run against the mock (the
            # same approach the Connector Test Workbench uses). Live mode (no injected
            # transport) never reaches here — it requires real config upstream.
            cfg = {**cfg, **_TEST_STUB_CONFIG.get(connector, {})}
        client = client_cls(config=cfg, transport=active_transport)
        # OAuth/token clients acquire a token first, mirroring real use.
        if hasattr(client, "authenticate"):
            try:
                client.authenticate()
            except Exception as exc:  # noqa: BLE001 - surface as classified error
                return {"ok": False, "status": "auth_error", "items": [],
                        "errors": [type(exc).__name__]}
        method = getattr(client, meta["method"])
        result = method()
    except Exception as exc:  # noqa: BLE001 - never raise to the caller
        return {"ok": False, "status": "adapter_error", "items": [],
                "errors": [type(exc).__name__]}
    if isinstance(result, dict):
        return result
    return {"ok": True, "status": "ok", "items": list(result or [])}


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def collect_evidence(
    connector: str,
    *,
    framework: str = "",
    application: str = "",
    control: str = "",
    collected_by: str = "connector_executor",
    max_items: int = DEFAULT_MAX_ITEMS,
    transport: Optional[Callable[..., dict]] = None,
    verify_ssl: bool = True,
) -> dict[str, Any]:
    """Collect evidence from one enterprise connector and ingest it (opt-in).

    Live collection runs only when a real ``transport`` is injected (tests /
    explicit callers) OR the ``ECS_CONNECTOR_EXECUTION_ENABLED`` flag is set AND
    the adapter is configured. Otherwise this is a safe no-op (``skipped``).

    Returns a receipt: connector, mode, upstream status, object counts, and the
    per-evidence ingestion results. Never raises; never hits a network implicitly.
    """
    if not _known(connector):
        return {"ok": False, "connector": connector, "status": "unknown_connector",
                "ingested": 0, "receipts": []}

    injected = transport is not None
    if not injected:
        if not execution_enabled():
            return {"ok": False, "connector": connector, "status": "skipped",
                    "reason": f"{EXECUTION_FLAG} is not enabled", "mode": "disabled",
                    "ingested": 0, "receipts": []}
        try:
            if not _adapter_module(connector).is_configured():
                if _demo_mode_enabled() and connector in _ADAPTER_TESTS:
                    meta = _ADAPTER_TESTS.get(connector, {})
                    transport = _workbench_mock_transport(meta.get("mock", {}))
                    injected = True
                else:
                    return {"ok": False, "connector": connector, "status": "not_configured",
                            "reason": "adapter is not configured", "mode": "live",
                            "ingested": 0, "receipts": []}
        except Exception:  # noqa: BLE001
            return {"ok": False, "connector": connector, "status": "not_configured",
                    "mode": "live", "ingested": 0, "receipts": []}

    resp = _run_adapter_fetch(connector, transport=transport, verify_ssl=verify_ssl)
    items = list(resp.get("items", []) if isinstance(resp, dict) else [])
    upstream_status = resp.get("status", "ok") if isinstance(resp, dict) else "ok"
    upstream_ok = bool(resp.get("ok", True)) if isinstance(resp, dict) else True

    receipts: list[dict[str, Any]] = []
    if upstream_ok and items:
        receipts = _ingest_items(
            connector, items, framework=framework, application=application,
            control=control, collected_by=collected_by, max_items=max_items,
            transport=transport,
        )
    ingested = sum(1 for r in receipts if r.get("evidence_id"))
    return {
        "ok": bool(upstream_ok and (ingested > 0 or not items)),
        "connector": connector,
        "mode": "mock" if injected else "live",
        "status": upstream_status,
        "objects_fetched": len(items),
        "ingested": ingested,
        "errors": resp.get("errors", []) if isinstance(resp, dict) else [],
        "receipts": receipts,
    }


def collect_for_job(job: Any, *, transport: Optional[Callable[..., dict]] = None,
                    collected_by: str = "asset_scheduler",
                    max_items: int = DEFAULT_MAX_ITEMS) -> dict[str, Any]:
    """Collect evidence for a scheduler ``PlannedJob`` (route == connector).

    Maps the planned job's connector/scope/frameworks/control onto
    :func:`collect_evidence`. Used by ``asset_scheduler.execute_plan``.
    """
    connector = getattr(job, "connector", "") or ""
    frameworks = getattr(job, "frameworks", ()) or ()
    control_ids = getattr(job, "control_ids", ()) or ()
    result = collect_evidence(
        connector,
        framework=frameworks[0] if frameworks else "",
        application=getattr(job, "scope_value", "") or "",
        control=control_ids[0] if control_ids else "",
        collected_by=collected_by,
        max_items=max_items,
        transport=transport,
    )
    result["asset_id"] = getattr(job, "asset_id", "")
    result["route"] = getattr(job, "route", "")
    return result
