"""Publish successful predefined-query runs as JSON evidence artifacts."""

from __future__ import annotations

import contextvars
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from typing import Any

from modules.operations.engines.predefined_query_evidence import (
    prepare_evidence_record,
    store_predefined_evidence,
)
from modules.operations.engines.query_connectors import ConnectorResult

from app import ecs_state

_active_scheduler_run_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "ecs_pq_scheduler_run_id", default=""
)


def set_active_scheduler_run_id(run_id: str = ""):
    """Bind scheduler_run_id for the current collection thread/context."""
    return _active_scheduler_run_id.set(str(run_id or "").strip())


def reset_active_scheduler_run_id(token) -> None:
    try:
        _active_scheduler_run_id.reset(token)
    except Exception:  # noqa: BLE001
        _active_scheduler_run_id.set("")


def get_active_scheduler_run_id() -> str:
    return str(_active_scheduler_run_id.get() or "").strip()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "unknown")).strip("-")
    return cleaned or "unknown"


def resolve_execution_context(control: dict[str, Any]) -> dict[str, str]:
    application = str(control.get("application") or "").strip()
    environment = str(control.get("environment") or "").strip()
    asset_id = str(control.get("asset_id") or "").strip()
    try:
        from config.environment_loader import active_environment

        if not environment:
            environment = active_environment()
    except Exception:  # noqa: BLE001
        environment = environment or "local"
    if not application:
        application = "Net Banking"
    if not asset_id:
        asset_id = application
    return {"application": application, "environment": environment, "asset_id": asset_id}


def _parse_tabular_output(output: str) -> tuple[list[str], list[list[Any]]]:
    lines = [ln.rstrip() for ln in (output or "").splitlines() if ln.strip()]
    if len(lines) < 2 or " | " not in lines[0]:
        return [], []
    columns = [c.strip() for c in lines[0].split(" | ")]
    rows: list[list[Any]] = []
    for line in lines[2:]:
        if " | " not in line:
            continue
        rows.append([cell.strip() for cell in line.split(" | ")])
    return columns, rows


def build_artifact_json(
    *,
    control: dict[str, Any],
    technology: str,
    query: str,
    result: ConnectorResult,
    user: str,
    execution_id: str = "",
    executed_at: str = "",
) -> dict[str, Any]:
    meta = dict(result.metadata or {})
    ctx = resolve_execution_context(control)
    control_id = str(control.get("control_id") or "")
    columns = list(meta.get("columns") or [])
    rows = list(meta.get("parsed_rows") or meta.get("result") or [])
    if not columns and not rows:
        columns, rows = _parse_tabular_output(result.output or "")
    row_count = int(meta.get("rows_returned", len(rows)))
    artifact: dict[str, Any] = {
        "source_type": "predefined_query",
        "query_id": control_id,
        "technology": technology,
        "application": ctx["application"],
        "environment": ctx["environment"],
        "asset_id": ctx["asset_id"],
        "control_id": control_id,
        "executed_at": executed_at or _utc_now(),
        "status": "SUCCESS",
        "row_count": row_count,
        "columns": columns,
        "result": rows,
    }
    if control.get("control_name"):
        artifact["control_name"] = control["control_name"]
    if control.get("framework_coverage"):
        artifact["framework_coverage"] = control["framework_coverage"]
    if control.get("frameworks"):
        artifact["frameworks"] = list(control["frameworks"])
    if execution_id:
        artifact["execution_id"] = execution_id
    if user:
        artifact["executed_by"] = user
    artifact["query_reference"] = query
    artifact["duration_ms"] = int(result.duration_ms or 0)
    return artifact


def artifact_object_key(
    *,
    application: str,
    environment: str,
    query_id: str,
    executed_at: str,
) -> str:
    ts = executed_at.replace(":", "").replace("+", "Z").replace(" ", "T")
    ts = ts.replace(".", "")[:17]
    return f"predefined-query/{_slug(application)}/{_slug(environment)}/{_slug(query_id)}/{ts}.json"


def evidence_period_from(timestamp: str = "") -> str:
    ts = (timestamp or "").strip()
    if len(ts) >= 10:
        return ts[:10]
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def build_canonical_fingerprint(
    *,
    artifact: dict[str, Any],
    framework: str,
    source_connector: str = "predefined_query",
    evidence_period: str = "",
) -> dict[str, Any]:
    """Stable logical identity for predefined-query evidence (volatile fields excluded)."""
    period = evidence_period or evidence_period_from(str(artifact.get("executed_at") or ""))
    return {
        "application": artifact.get("application"),
        "environment": artifact.get("environment"),
        "framework": framework,
        "control_id": artifact.get("control_id") or artifact.get("query_id"),
        "query_id": artifact.get("query_id") or artifact.get("control_id"),
        "source_connector": source_connector,
        "query_reference": artifact.get("query_reference") or "",
        "columns": list(artifact.get("columns") or []),
        "result": list(artifact.get("result") or []),
        "row_count": int(artifact.get("row_count") or 0),
        "evidence_period": period,
    }


def canonical_fingerprint_hash(fingerprint: dict[str, Any]) -> str:
    payload = json.dumps(fingerprint, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _duplicate_receipt(existing: dict, *, reason: str, duplicate_kind: str) -> dict[str, Any]:
    meta = dict(existing.get("metadata") or {})
    return {
        "status": "DUPLICATE",
        "duplicate": True,
        "duplicate_kind": duplicate_kind,
        "duplicate_reason": reason,
        "evidence_id": existing.get("evidence_id", ""),
        "evidence_version": int(existing.get("version") or existing.get("evidence_version") or 1),
        "object_key": meta.get("object_key") or existing.get("object_key") or "",
        "sha256": existing.get("sha256") or meta.get("content_sha256") or "",
        "original_evidence_id": existing.get("evidence_id", ""),
        "filename": existing.get("filename", ""),
        "custody_mode": existing.get("custody_mode", ""),
        "workflow_status": existing.get("workflow_status") or existing.get("status") or "",
        "evidence_persisted": False,
        "ok": True,
    }


def find_existing_predefined_query_evidence(
    *,
    content_hash: str,
    canonical_hash: str,
) -> tuple[dict | None, str]:
    """Reuse existing upload indexes; returns (record, duplicate_kind)."""
    from modules.operations.engines.evidence_repository import (
        find_upload_by_canonical_fingerprint,
        find_upload_by_sha256,
    )

    exact = find_upload_by_sha256(content_hash)
    if exact is not None:
        return exact, "sha256"
    logical = find_upload_by_canonical_fingerprint(canonical_hash)
    if logical is not None:
        return logical, "canonical"
    return None, ""


def register_predefined_query_indexes(
    *,
    content_hash: str,
    canonical_hash: str,
    record: dict[str, Any],
) -> None:
    receipt = {
        "evidence_id": record.get("evidence_id", ""),
        "evidence_version": int(record.get("version") or 1),
        "object_key": (record.get("metadata") or {}).get("object_key") or record.get("object_key") or "",
        "sha256": record.get("sha256") or content_hash,
        "canonical_fingerprint": canonical_hash,
        "framework": (record.get("framework_tags") or [""])[0],
        "control_id": record.get("control") or (record.get("metadata") or {}).get("query_id") or "",
    }
    if content_hash:
        ecs_state.predefined_query_content_index[content_hash] = receipt
    if canonical_hash:
        ecs_state.predefined_query_fingerprint_index[canonical_hash] = receipt


def publish_predefined_query_evidence(
    *,
    control: dict[str, Any],
    technology: str,
    query: str,
    result: ConnectorResult,
    user: str,
    execution_id: str = "",
    framework: str = "",
    scheduler_run_id: str = "",
) -> dict[str, Any]:
    executed_at = _utc_now()
    run_stamp = str(scheduler_run_id or get_active_scheduler_run_id() or "").strip()
    artifact = build_artifact_json(
        control=control,
        technology=technology,
        query=query,
        result=result,
        user=user,
        execution_id=execution_id,
        executed_at=executed_at,
    )
    if run_stamp:
        artifact["scheduler_run_id"] = run_stamp
    content = json.dumps(artifact, indent=2, sort_keys=True, default=str).encode("utf-8")
    content_hash = hashlib.sha256(content).hexdigest()
    ctx = resolve_execution_context(control)
    control_id = str(control.get("control_id") or "")
    primary_fw = framework or (control.get("frameworks", [""])[0] if control.get("frameworks") else "")
    evidence_period = evidence_period_from(executed_at)
    fingerprint = build_canonical_fingerprint(
        artifact=artifact,
        framework=primary_fw,
        source_connector="predefined_query",
        evidence_period=evidence_period,
    )
    canonical_hash = canonical_fingerprint_hash(fingerprint)
    existing, duplicate_kind = find_existing_predefined_query_evidence(
        content_hash=content_hash,
        canonical_hash=canonical_hash,
    )
    if existing is not None:
        reason = (
            "Identical artifact content (SHA-256 match)."
            if duplicate_kind == "sha256"
            else "Logically identical predefined-query result for the same evidence period."
        )
        from modules.shared.services.audit_trail import log_event

        log_event(
            "Predefined Query Evidence Duplicate",
            user,
            primary_fw,
            control_id,
            f"{reason} Existing evidence {existing.get('evidence_id', '')}.",
            existing.get("evidence_id", ""),
        )
        return _duplicate_receipt(existing, reason=reason, duplicate_kind=duplicate_kind)

    object_key = artifact_object_key(
        application=ctx["application"],
        environment=ctx["environment"],
        query_id=control_id,
        executed_at=executed_at,
    )
    filename = f"PREDEFINED_QUERY_{control_id}.json"
    stable_source_item_id = (
        f"predefined-query/{_slug(ctx['application'])}/{_slug(ctx['environment'])}/"
        f"{_slug(control_id)}/{evidence_period}"
    )
    custody_mode = os.environ.get("ECS_PREDEFINED_QUERY_CUSTODY", "").strip() or os.environ.get(
        "ECS_EVIDENCE_DEFAULT_CUSTODY", "SNAPSHOT"
    )
    from modules.operations.engines.evidence_repository import register_upload

    metadata = {
        "source_type": "predefined_query",
        "collection_source": "predefined_query",
        "source_name": f"Predefined Query {control_id}",
        "query_id": control_id,
        "technology": technology,
        "object_key": object_key,
        "content_sha256": content_hash,
        "canonical_fingerprint": canonical_hash,
        "evidence_period": evidence_period,
        "execution_id": execution_id,
        "row_count": artifact["row_count"],
    }
    if run_stamp:
        metadata["scheduler_run_id"] = run_stamp
    upload = register_upload(
        filename=filename,
        content=content,
        uploaded_by=user,
        framework=primary_fw,
        application=ctx["application"],
        control=control_id,
        source_connector="predefined_query",
        source_item_id=stable_source_item_id,
        source_url=f"object://{object_key}",
        environment=ctx["environment"],
        mime_type="application/json",
        metadata=metadata,
        custody_mode=custody_mode,
    )
    register_predefined_query_indexes(
        content_hash=content_hash,
        canonical_hash=canonical_hash,
        record=upload,
    )
    evidence = prepare_evidence_record(
        control_id=control_id,
        result=json.dumps(artifact),
        user=user,
        framework_coverage=control.get("framework_coverage") or "",
    )
    store_predefined_evidence(evidence)
    from modules.shared.services.evidence_workflow_engine import enroll_collected_evidence

    enrollment = enroll_collected_evidence(
        upload,
        source_type="predefined_query",
        artifact=artifact,
        skip_if_enrolled=False,
    )
    upload["metadata"] = dict(upload.get("metadata") or {})
    upload["metadata"]["workflow_key"] = enrollment["key"]
    upload["metadata"]["artifact_preview"] = artifact.get("result") or []
    return {
        **upload,
        "evidence_id": upload.get("evidence_id") or evidence.evidence_id,
        "object_key": object_key,
        "sha256": upload.get("sha256") or content_hash,
        "artifact": artifact,
        "workflow_key": enrollment["key"],
        "framework": enrollment["framework"],
        "control_name": enrollment["control_name"],
        "evidence_version": enrollment["evidence_version"],
        "workflow_status": enrollment["status"],
    }
