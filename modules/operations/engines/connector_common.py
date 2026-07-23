"""Shared helpers for predefined query connector execution."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from modules.operations.engines.predefined_query_audit import record_execution_audit
from modules.operations.engines.query_connectors import ConnectorResult


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_execution_result(
    *,
    execution_id: str,
    control: dict[str, Any],
    technology: str,
    query: str,
    started_at: str,
    completed_at: str,
    status: str,
    result: ConnectorResult | None = None,
    connect_error: str = "",
    evidence_id: str = "",
    parsed_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Structured execution payload returned to callers and audit surfaces."""
    meta = dict(getattr(result, "metadata", None) or {})
    ok = status.lower() == "success"
    error_message = "" if ok else (connect_error or getattr(result, "error_message", "") or "Execution failed")
    error_code = "" if ok else str(meta.get("error_type") or "execution_failure")
    return {
        "execution_id": execution_id,
        "control_id": control.get("control_id") or "",
        "technology": technology,
        "target": meta.get("target") or meta.get("host") or technology,
        "command_or_query_reference": query,
        "started_at": started_at,
        "completed_at": completed_at,
        "status": status,
        "raw_output_reference": evidence_id or meta.get("raw_output_reference") or "",
        "parsed_values": parsed_values or meta.get("parsed_values") or {},
        "validation_result": meta.get("validation_result") or ("PASS" if ok else "FAIL"),
        "error_code": error_code,
        "error_message": error_message,
    }


def complete_connector_execution(
    control: dict[str, Any],
    user: str,
    technology: str,
    query: str,
    result: ConnectorResult,
    *,
    connect_error: str = "",
    started_at: str = "",
    persist: bool | None = None,
) -> dict[str, Any]:
    """Normalize result, write audit/evidence, and return API payload."""
    started = started_at or _utc_now()
    completed = _utc_now()
    control_id = control["control_id"]
    framework_coverage = control.get("framework_coverage") or ""
    primary_fw = control.get("frameworks", [""])[0] if control.get("frameworks") else ""
    rows_returned = int(result.metadata.get("rows_returned", 0)) if result.metadata else 0
    evidence_filename = f"PREDEFINED_QUERY_{control_id}.txt"

    if connect_error or not result.success:
        error_message = connect_error or result.error_message or "Execution failed"
        audit = record_execution_audit(
            control_id,
            user,
            technology,
            "Failed",
            duration_ms=result.duration_ms,
            error_message=error_message,
            framework_coverage=framework_coverage,
            query=query,
            result=result.output,
            rows_returned=rows_returned,
        )
        from modules.operations.engines.predefined_queries_engine import _refresh_control_last_execution

        _refresh_control_last_execution(control_id)
        from modules.shared.services.ecs_logging import info

        info(
            "PredefinedQueries",
            f"{technology} {control_id} Failed {result.duration_ms}ms evidence={evidence_filename}",
        )
        structured = build_execution_result(
            execution_id=audit.execution_id,
            control=control,
            technology=technology,
            query=query,
            started_at=started,
            completed_at=completed,
            status="Failed",
            result=result,
            connect_error=connect_error,
        )
        return {
            "ok": False,
            "error": error_message,
            "error_type": (result.metadata or {}).get("error_type", "execution_failure"),
            "execution": structured,
        }

    audit = record_execution_audit(
        control_id,
        user,
        technology,
        "Success",
        duration_ms=result.duration_ms,
        framework_coverage=framework_coverage,
        query=query,
        result=result.output,
        rows_returned=rows_returned,
    )
    from modules.operations.engines.predefined_queries_engine import (
        _refresh_control_last_execution,
        execution_persist_enabled,
    )

    should_persist = execution_persist_enabled() if persist is None else bool(persist)
    upload: dict[str, Any] = {}
    evidence_id = ""
    if should_persist:
        from modules.operations.engines.predefined_query_publisher import publish_predefined_query_evidence

        upload = publish_predefined_query_evidence(
            control=control,
            technology=technology,
            query=query,
            result=result,
            user=user,
            execution_id=audit.execution_id,
            framework=primary_fw,
        )
        if upload.get("status") == "DUPLICATE":
            evidence_id = str(upload.get("evidence_id") or upload.get("original_evidence_id") or "")
        else:
            evidence_id = str(upload.get("evidence_id") or "")

    from modules.shared.services.audit_trail import log_event
    from modules.shared.services.ecs_logging import info

    _refresh_control_last_execution(control_id)
    log_event(
        "Predefined Query Executed",
        user,
        primary_fw,
        control_id,
        f"{technology} — {rows_returned} rows — {result.duration_ms}ms — {upload.get('filename', evidence_filename) if should_persist else 'preview'}",
    )
    info(
        "PredefinedQueries",
        f"{technology} {control_id} Success {result.duration_ms}ms evidence={'persisted' if should_persist else 'preview'}",
    )
    structured = build_execution_result(
        execution_id=audit.execution_id,
        control=control,
        technology=technology,
        query=query,
        started_at=started,
        completed_at=completed,
        status="Success",
        result=result,
        evidence_id=evidence_id,
    )
    persisted = bool(should_persist and evidence_id and upload.get("status") != "DUPLICATE")
    duplicate = upload.get("status") == "DUPLICATE"
    message = f"Query executed successfully — {rows_returned} row(s) returned in {result.duration_ms}ms"
    if duplicate:
        message = f"{message} — {upload.get('duplicate_reason', 'Duplicate evidence detected.')}"
    return {
        "ok": True,
        "message": message,
        "control_id": control_id,
        "query": query,
        "status": "Success",
        "rows_returned": rows_returned,
        "output": result.output,
        "duration_ms": result.duration_ms,
        "evidence_id": evidence_id,
        "evidence_persisted": persisted,
        "duplicate": duplicate,
        "embedding_skipped": duplicate or bool(upload.get("embedding_skipped")),
        "duplicate_reason": upload.get("duplicate_reason", "") if duplicate else "",
        "original_evidence_id": upload.get("original_evidence_id", "") if duplicate else "",
        "evidence_filename": upload.get("filename", "") if persisted else "",
        "evidence_object_key": upload.get("object_key", "") if (persisted or duplicate) else "",
        "evidence_sha256": upload.get("sha256", "") if (persisted or duplicate) else "",
        "upload": upload,
        "execution": structured,
    }
