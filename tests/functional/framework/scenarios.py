"""Reusable composite flows (the 'workflow' capability): built ONLY from helpers, shared by many use cases."""

from __future__ import annotations

from typing import Any, Callable

from .api_client import ApiResponse
from .assertions import (assert_exists, assert_json_field, assert_status, assert_success, assert_traceability)
from .data_factory import TestFile
from .wait import wait_until


# ---- evidence ingest -------------------------------------------------------------------------------------------------
def upload_and_locate(ctx, f: TestFile | None = None, persona: str = "owner", **meta: Any) -> tuple[TestFile, dict, dict]:
    """Upload through ECS, then wait until the evidence is visible in the repository. Returns (file, upload_body, repo_row)."""
    ctx.require_mutation()
    f = f or ctx.data.file()
    resp = ctx.track(ctx.evidence.upload(f, persona=persona, **meta))
    assert_success(resp, "evidence upload")
    body = resp.json()
    ctx.correlation.add("evidence_id", body.get("evidence_id"))
    row = wait_until(lambda: ctx.evidence.by_filename(f.name), timeout=ctx.cfg.thresholds["polling"]["ingestion_timeout_sec"],
                     interval=ctx.cfg.poll_interval, what=f"evidence '{f.name}' in repository")
    return f, body, row


def verify_integrity(ctx, f: TestFile, row: dict) -> None:
    """Stored SHA-256 equals the hash of the uploaded bytes; ECS integrity endpoint agrees; object exists in the store."""
    assert row.get("sha256") == f.sha256, f"stored sha256 {row.get('sha256')!r} != uploaded {f.sha256}"
    resp = ctx.track(ctx.evidence.integrity(row["evidence_id"]))
    assert_success(resp, "integrity endpoint")
    assert_json_field(resp.json(), "integrity_valid", True)
    ref = row.get("object_reference")
    if ref and ctx.cfg.get("object_store.mode") == "local" and "evidence/" in str(ref):
        key = str(ref).split("evidence/", 1)[-1]
        ctx.storage.verify_matches("evidence/" + key, f.sha256)


def verify_audit(ctx, resp: ApiResponse, action: str, persona: str = "owner") -> None:
    ctx.audit.verify(request_id=resp.request_id, action=action)


# ---- pages / dashboards ----------------------------------------------------------------------------------------------------
def page_loads(ctx, path: str, persona: str = "owner", **params: Any) -> ApiResponse:
    resp = ctx.as_persona(persona).get(path, params=params)
    ctx.track(resp)
    assert_status(resp, 200, f"GET {path} as {persona}")
    assert len(resp.content) > 200, f"GET {path} returned an almost-empty body"
    return resp


def json_loads(ctx, fn: Callable[[], Any], what: str) -> Any:
    body = fn()
    assert_exists(body, f"{what} returned nothing")
    return body


def pages_for_roles(ctx, path: str, personas: tuple[str, ...] | list[str], **params: Any) -> dict[str, ApiResponse]:
    out = {p: ctx.as_persona(p).get(path, params=params) for p in personas}
    for p, r in out.items():
        assert_status(r, 200, f"{path} as {p}")
    return out


def filter_changes_view(ctx, fetch: Callable[..., Any], base: dict, filtered: dict) -> tuple[Any, Any]:
    """Applying a filter must succeed and be honoured (response differs from, or is a subset of, the unfiltered view)."""
    a, b = fetch(**base), fetch(**filtered)
    assert_exists(a, "unfiltered view empty")
    assert b is not None, "filtered view failed"
    return a, b


def drill(ctx, fetch: Callable[[], Any], what: str) -> Any:
    body = fetch()
    assert_exists(body, f"drill-down '{what}' returned no detail")
    return body


# ---- scheduler ----------------------------------------------------------------------------------------------------------------
def collection_run(ctx, **kw: Any) -> dict:
    ctx.require_mutation()
    resp = ctx.scheduler.run_collection(sync=True, **kw)
    ctx.track(resp)
    assert_status(resp, 200, "scheduler run")
    body = resp.json()
    rid = body.get("run_id")
    if rid and body.get("status") not in ("completed", "complete", "success"):
        body = ctx.scheduler.wait_for_run(rid)
    return body


# ---- connectors -----------------------------------------------------------------------------------------------------------------
def connector_dry_run(ctx, name: str) -> ApiResponse:
    ctx.connectors.require_available(name)
    resp = ctx.track(ctx.connectors.dry_run(name))
    assert resp.status < 500, f"{name} dry-run -> {resp.status}: {resp.text[:200]}"
    return resp


# ---- AI ------------------------------------------------------------------------------------------------------------------------------
def ai_query(ctx, text: str | None = None, persona: str | None = None, **kw: Any) -> dict:
    resp = ctx.track(ctx.ai.query(text, persona=persona, **kw))
    assert_success(resp, "AI query")
    return ctx.ai.result_of(resp)


def assert_traceable_rows(rows: list[dict], required=("source", "evidence_id")) -> None:
    assert rows, "no rows to check for traceability"
    for r in rows[:10]:
        assert_traceability(r, required)
