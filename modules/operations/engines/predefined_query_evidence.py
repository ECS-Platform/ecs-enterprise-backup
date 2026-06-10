"""Evidence integration for predefined query results (prepare only — no runtime execution)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class PredefinedQueryEvidence:
    evidence_id: str
    control_id: str
    result: str
    timestamp: str
    user: str
    framework_coverage: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "control_id": self.control_id,
            "result": self.result,
            "timestamp": self.timestamp,
            "user": self.user,
            "framework_coverage": self.framework_coverage,
        }


_evidence_counter = 0
_predefined_evidence_store: list[dict[str, Any]] = []


def _next_evidence_id() -> str:
    global _evidence_counter
    _evidence_counter += 1
    return f"PQ-EVD-{_evidence_counter:06d}"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def prepare_evidence_record(
    control_id: str,
    result: str,
    user: str,
    framework_coverage: str,
) -> PredefinedQueryEvidence:
    """Build evidence payload for a successful predefined query execution."""
    return PredefinedQueryEvidence(
        evidence_id=_next_evidence_id(),
        control_id=control_id,
        result=result,
        timestamp=_ts(),
        user=user,
        framework_coverage=framework_coverage,
    )


def store_predefined_evidence(record: PredefinedQueryEvidence) -> dict[str, Any]:
    """Store evidence in the predefined-query evidence store (execution not yet enabled)."""
    payload = record.to_dict()
    _predefined_evidence_store.insert(0, payload)
    return payload


def register_with_evidence_repository(record: PredefinedQueryEvidence, framework: str = "") -> dict[str, Any]:
    """
    Bridge to ECS evidence_repository — called after successful execution.
    Execution is not yet enabled; this prepares the integration contract.
    """
    primary_framework = framework or (record.framework_coverage.split(",")[0].strip() if record.framework_coverage else "")
    from modules.operations.engines.evidence_repository import register_upload

    content = record.result.encode("utf-8") if record.result else b""
    filename = f"PREDEFINED_QUERY_{record.control_id}.txt"
    upload = register_upload(
        filename=filename,
        content=content,
        uploaded_by=record.user,
        framework=primary_framework,
        control=record.control_id,
    )
    store_predefined_evidence(record)
    return upload


def get_latest_evidence_for_control(control_id: str) -> dict[str, Any] | None:
    for row in _predefined_evidence_store:
        if row.get("control_id") == control_id:
            return row
    return None


def get_predefined_evidence_store(limit: int = 50) -> list[dict[str, Any]]:
    return _predefined_evidence_store[:limit]
