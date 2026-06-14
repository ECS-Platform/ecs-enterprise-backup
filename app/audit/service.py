"""AuditService — central durable audit write API (Phase 4, Step 1).

A single entry point for writing tamper-aware, attributable audit records to the
PostgreSQL audit_log table (extended in Phase 4 Step 1 with before/after state,
request_id, auth_source, prev_hash).

SCOPE: foundation only. No workflow / approval / observation / dashboard / RBAC /
RAG code calls this yet. It exists so later steps can route mutations through one
durable, testable writer. All writes are best-effort: a DB outage returns False
rather than raising, so once wired it can never break a business request.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


def new_request_id() -> str:
    """Generate a correlation id for grouping audit rows from one request."""
    return uuid.uuid4().hex


@dataclass
class AuditRecord:
    """A single audit event to persist."""

    actor: str
    action: str
    role: str = ""
    resource: str = ""
    detail: dict[str, Any] = field(default_factory=dict)
    before_state: dict[str, Any] | None = None
    after_state: dict[str, Any] | None = None
    request_id: str = ""
    auth_source: str = ""
    prev_hash: str = ""


class AuditService:
    """Durable audit writer. Stateless; opens a short-lived repository per write.

    Optionally accepts a repository factory for testing (any object exposing a
    `record_audit(...)` method and usable as a context manager)."""

    def __init__(self, repository_factory=None) -> None:
        self._repository_factory = repository_factory

    def _repo(self):
        if self._repository_factory is not None:
            return self._repository_factory()
        from ecs_platform.repository import EvidenceRepository

        return EvidenceRepository()

    def record(self, record: AuditRecord) -> bool:
        """Persist one AuditRecord. Returns True on success, False on any failure
        (DB unavailable, driver missing, etc.) — never raises."""
        try:
            repo = self._repo()
            with repo:
                repo.record_audit(
                    record.actor, record.action,
                    role=record.role, resource=record.resource, detail=record.detail,
                    before_state=record.before_state, after_state=record.after_state,
                    request_id=record.request_id, auth_source=record.auth_source,
                    prev_hash=record.prev_hash,
                )
            return True
        except Exception:  # noqa: BLE001 - audit writes must never break callers
            return False

    def record_event(self, actor: str, action: str, *, role: str = "", resource: str = "",
                     detail: dict[str, Any] | None = None,
                     before_state: dict[str, Any] | None = None,
                     after_state: dict[str, Any] | None = None,
                     request_id: str = "", auth_source: str = "") -> bool:
        """Convenience wrapper that builds and persists an AuditRecord."""
        return self.record(AuditRecord(
            actor=actor, action=action, role=role, resource=resource,
            detail=detail or {}, before_state=before_state, after_state=after_state,
            request_id=request_id or new_request_id(), auth_source=auth_source,
        ))


# Process-wide default instance (no DB work until .record() is actually called).
default_audit_service = AuditService()
