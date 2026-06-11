"""Shared helpers for predefined query connector execution."""

from __future__ import annotations

from typing import Any

from modules.operations.engines.predefined_query_audit import record_execution_audit
from modules.operations.engines.predefined_query_evidence import (
    prepare_evidence_record,
    register_with_evidence_repository,
)
from modules.operations.engines.query_connectors import ConnectorResult


def complete_connector_execution(
    control: dict[str, Any],
    user: str,
    technology: str,
    query: str,
    result: ConnectorResult,
    *,
    connect_error: str = "",
) -> dict[str, Any]:
    """Normalize result, write audit/evidence, and return API payload."""
    control_id = control["control_id"]
    framework_coverage = control.get("framework_coverage") or ""
    primary_fw = control.get("frameworks", [""])[0] if control.get("frameworks") else ""
    rows_returned = int(result.metadata.get("rows_returned", 0)) if result.metadata else 0
    evidence_filename = f"PREDEFINED_QUERY_{control_id}.txt"

    if connect_error or not result.success:
        error_message = connect_error or result.error_message or "Execution failed"
        record_execution_audit(
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
        return {
            "ok": False,
            "error": error_message,
            "error_type": (result.metadata or {}).get("error_type", "execution_failure"),
        }

    record_execution_audit(
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
    evidence = prepare_evidence_record(
        control_id=control_id,
        result=result.output,
        user=user,
        framework_coverage=framework_coverage,
    )
    upload = register_with_evidence_repository(evidence, framework=primary_fw)

    from modules.operations.engines.predefined_queries_engine import _refresh_control_last_execution
    from modules.shared.services.audit_trail import log_event
    from modules.shared.services.ecs_logging import info

    _refresh_control_last_execution(control_id)
    log_event(
        "Predefined Query Executed",
        user,
        primary_fw,
        control_id,
        f"{technology} — {rows_returned} rows — {result.duration_ms}ms — {upload.get('filename', evidence_filename)}",
    )
    info(
        "PredefinedQueries",
        f"{technology} {control_id} Success {result.duration_ms}ms evidence={upload.get('filename', evidence_filename)}",
    )
    return {
        "ok": True,
        "message": f"Query executed successfully — {rows_returned} row(s) returned in {result.duration_ms}ms",
        "control_id": control_id,
        "query": query,
        "status": "Success",
        "rows_returned": rows_returned,
        "output": result.output,
        "duration_ms": result.duration_ms,
        "evidence_id": evidence.evidence_id,
        "evidence_filename": upload.get("filename", evidence_filename),
    }
