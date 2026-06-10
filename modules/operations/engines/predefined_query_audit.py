"""Audit logging model for predefined query execution (prepare only — no runtime execution)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

_execution_audit_log: list[dict[str, Any]] = []
_execution_counter = 0


def _next_execution_id() -> str:
    global _execution_counter
    _execution_counter += 1
    return f"PQ-EXEC-{_execution_counter:06d}"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


@dataclass
class ExecutionAuditRecord:
    execution_id: str
    control_id: str
    user: str
    technology: str
    execution_time: str
    status: str
    duration_ms: int = 0
    error_message: str = ""
    framework_coverage: str = ""
    query: str = ""
    result: str = ""
    rows_returned: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "control_id": self.control_id,
            "user": self.user,
            "technology": self.technology,
            "execution_time": self.execution_time,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "framework_coverage": self.framework_coverage,
            "query": self.query,
            "result": self.result,
            "rows_returned": self.rows_returned,
        }


def record_execution_audit(
    control_id: str,
    user: str,
    technology: str,
    status: str,
    *,
    duration_ms: int = 0,
    error_message: str = "",
    framework_coverage: str = "",
    query: str = "",
    result: str = "",
    rows_returned: int = 0,
) -> ExecutionAuditRecord:
    """Persist an execution audit entry (in-memory until execution is enabled)."""
    record = ExecutionAuditRecord(
        execution_id=_next_execution_id(),
        control_id=control_id,
        user=user,
        technology=technology,
        execution_time=_ts(),
        status=status,
        duration_ms=duration_ms,
        error_message=error_message,
        framework_coverage=framework_coverage,
        query=query,
        result=result,
        rows_returned=rows_returned,
    )
    _execution_audit_log.insert(0, record.to_dict())
    return record


def get_execution_audit_log(limit: int = 50) -> list[dict[str, Any]]:
    return _execution_audit_log[:limit]


def get_execution_history_for_control(control_id: str, limit: int = 20) -> list[dict[str, Any]]:
    return [row for row in _execution_audit_log if row.get("control_id") == control_id][:limit]
