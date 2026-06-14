"""Write-through durable observation store (Phase 4, Step 3).

This module is the single chokepoint through which observation lifecycle changes
become durable. It deliberately does NOT replace the in-memory model — the live
read path for dashboards/workflows stays exactly as-is. Instead it mirrors each
mutation to the PostgreSQL `observations` table and, at startup, hydrates persisted
rows back into memory so the experience survives restarts.

Design guarantees:
  * Feature flag OBSERVATIONS_DURABLE_ENABLED (default FALSE) -> all functions are
    no-ops; ECS behaves exactly as before.
  * Best-effort: every public function swallows backend errors and returns a bool;
    none of them ever raise, so a DB outage cannot break a business workflow.
  * Reuses existing infrastructure: EvidenceRepository (persistence) and the
    Phase 4 AuditService (observation.* audit events). No new persistence model,
    no new audit framework.
"""

from __future__ import annotations

import os
from typing import Any


def durable_observations_enabled() -> bool:
    """Feature flag. Default FALSE: no durable observation writes/hydration."""
    return str(os.environ.get("OBSERVATIONS_DURABLE_ENABLED", "")).strip().lower() in {
        "1", "true", "yes", "on",
    }


def _repo_factory():
    """Overridable in tests. Returns a context-manageable repository."""
    from ecs_platform.repository import EvidenceRepository

    return EvidenceRepository()


# Tests may set this to a callable returning a fake repository.
repository_factory = _repo_factory


def _audit(action: str, *, observation_id: str, actor: str, role: str = "",
           before_state: dict[str, Any] | None = None,
           after_state: dict[str, Any] | None = None,
           detail: dict[str, Any] | None = None) -> None:
    """Emit an observation.* audit event via the existing AuditService. Best-effort."""
    try:
        from app.audit.service import AuditRecord, default_audit_service, new_request_id

        default_audit_service.record(AuditRecord(
            actor=actor or "system", action=action, role=role,
            resource=observation_id, detail=detail or {},
            before_state=before_state, after_state=after_state,
            request_id=new_request_id(), auth_source="workflow"))
    except Exception:  # noqa: BLE001 - audit must never break a workflow
        pass


def persist_observation(observation_id: str, *, title: str = "", application_id: str = "",
                        framework: str = "", control_id: str = "", description: str = "",
                        severity: str = "", status: str = "Open", owner: str = "",
                        due_date: str = "", remediation_plan: str = "",
                        actor: str = "", role: str = "",
                        emit_audit: bool = True) -> bool:
    """Create-or-update an observation durably (write-through upsert).

    No-op (returns False) when the flag is off. Emits observation.create when the
    row is new, observation.update otherwise. Never raises."""
    if not durable_observations_enabled():
        return False
    try:
        repo = repository_factory()
        with repo:
            existed = repo.get_observation(observation_id) is not None
            before = {"status": existed} if existed else None
            repo.upsert_observation(
                observation_id, title=title or observation_id,
                application_id=application_id, framework=framework, control_id=control_id,
                description=description, severity=severity, status=status, owner=owner,
                due_date=due_date, remediation_plan=remediation_plan,
                created_by=actor, updated_by=actor)
        if emit_audit:
            action = "observation.update" if existed else "observation.create"
            _audit(action, observation_id=observation_id, actor=actor, role=role,
                   before_state=before, after_state={"status": status},
                   detail={"framework": framework, "control_id": control_id,
                           "application_id": application_id})
        return True
    except Exception:  # noqa: BLE001 - durability is best-effort
        return False


def persist_close(observation_id: str, *, closed_by: str = "", role: str = "",
                  status: str = "Closed", detail: dict[str, Any] | None = None,
                  emit_audit: bool = False) -> bool:
    """Durably close an observation. Ensures the row exists first (write-through).

    emit_audit defaults False because the workflow handlers already emit
    observation.close in Phase 4 Step 2; set True for code paths that do not."""
    if not durable_observations_enabled():
        return False
    try:
        repo = repository_factory()
        with repo:
            if repo.get_observation(observation_id) is None:
                repo.upsert_observation(observation_id, title=observation_id,
                                        status="Open", created_by=closed_by)
            repo.close_observation(observation_id, closed_by=closed_by, status=status)
        if emit_audit:
            _audit("observation.close", observation_id=observation_id, actor=closed_by,
                   role=role, before_state={"status": "Open"},
                   after_state={"status": status}, detail=detail or {})
        return True
    except Exception:  # noqa: BLE001
        return False


def persist_reopen(observation_id: str, *, reopened_by: str = "", role: str = "",
                   status: str = "Open", detail: dict[str, Any] | None = None,
                   emit_audit: bool = False) -> bool:
    """Durably reopen an observation. Ensures the row exists first (write-through)."""
    if not durable_observations_enabled():
        return False
    try:
        repo = repository_factory()
        with repo:
            if repo.get_observation(observation_id) is None:
                repo.upsert_observation(observation_id, title=observation_id,
                                        status=status, created_by=reopened_by)
            else:
                repo.reopen_observation(observation_id, reopened_by=reopened_by, status=status)
        if emit_audit:
            _audit("observation.reopen", observation_id=observation_id, actor=reopened_by,
                   role=role, before_state={"status": "Closed"},
                   after_state={"status": status}, detail=detail or {})
        return True
    except Exception:  # noqa: BLE001
        return False


def hydrate_into_memory() -> int:
    """Reload persisted observations into in-memory ECS state (restart durability).

    Repopulates ecs_state.missing_evidence_registry (open/active observations) and
    ecs_state.closed_observations (closed ones) so dashboards render the same data
    after a restart WITHOUT any UI/dashboard change. Existing in-memory entries are
    never overwritten (memory wins for the current process). Returns the number of
    rows hydrated. No-op (returns 0) when the flag is off. Never raises."""
    if not durable_observations_enabled():
        return 0
    try:
        from modules.shared.services import ecs_state

        repo = repository_factory()
        with repo:
            rows = repo.list_observations(limit=100000)
        hydrated = 0
        for row in rows:
            oid = row.get("observation_id")
            if not oid:
                continue
            status = (row.get("status") or "").strip()
            if status.lower() == "closed":
                if oid not in ecs_state.closed_observations:
                    ecs_state.closed_observations[oid] = {
                        "observation_id": oid,
                        "framework": row.get("framework") or "",
                        "control": row.get("title") or "",
                        "control_id": row.get("control_id") or "",
                        "closed_by": row.get("closed_by") or "",
                        "closed_at": _ts(row.get("closed_at")),
                        "detail": row.get("description") or "Restored from durable store",
                        "auto_closed": False,
                    }
                    hydrated += 1
            else:
                if oid not in ecs_state.missing_evidence_registry:
                    ecs_state.missing_evidence_registry[oid] = {
                        "observation_id": oid,
                        "application": row.get("application_id") or "",
                        "framework": row.get("framework") or "",
                        "control_id": row.get("control_id") or "",
                        "control": row.get("title") or "",
                        "control_description": row.get("description") or "",
                        "observation_severity": row.get("severity") or "",
                        "status": status or "Pending Upload",
                        "owner": row.get("owner") or "",
                        "due_date": row.get("due_date") or "",
                        "history": [],
                    }
                    hydrated += 1
        return hydrated
    except Exception:  # noqa: BLE001 - hydration must never block startup
        return 0


def migrate_memory_to_durable() -> dict[str, int]:
    """One-time, idempotent migration of current in-memory observations to Postgres.

    Safe to re-run: every write is an upsert keyed by observation_id. Migrates both
    the active registry and closed observations. Returns counts. No-op when the flag
    is off. Never raises (returns whatever it managed before any error)."""
    result = {"registry": 0, "closed": 0, "errors": 0}
    if not durable_observations_enabled():
        return result
    try:
        from modules.shared.services import ecs_state

        repo = repository_factory()
        with repo:
            for oid, rec in dict(ecs_state.missing_evidence_registry).items():
                try:
                    repo.upsert_observation(
                        oid, title=rec.get("control") or oid,
                        application_id=rec.get("application", ""),
                        framework=rec.get("framework", ""),
                        control_id=rec.get("control_id", ""),
                        description=rec.get("control_description", "") or rec.get("missing_evidence", ""),
                        severity=rec.get("observation_severity", "") or rec.get("risk", ""),
                        status=rec.get("status", "Open") or "Open",
                        owner=rec.get("owner", "") or rec.get("remediation_owner", ""),
                        due_date=rec.get("due_date", ""),
                        created_by=rec.get("requested_by", "") or "migration")
                    result["registry"] += 1
                except Exception:  # noqa: BLE001
                    result["errors"] += 1
            for oid, rec in dict(ecs_state.closed_observations).items():
                try:
                    repo.upsert_observation(
                        oid, title=rec.get("control") or oid,
                        framework=rec.get("framework", ""),
                        control_id=rec.get("control_id", ""),
                        description=rec.get("detail", ""),
                        status="Closed", created_by=rec.get("closed_by", "") or "migration")
                    repo.close_observation(oid, closed_by=rec.get("closed_by", ""))
                    result["closed"] += 1
                except Exception:  # noqa: BLE001
                    result["errors"] += 1
        return result
    except Exception:  # noqa: BLE001
        return result


def _ts(value: Any) -> str:
    """Render a DB timestamp to the string format the in-memory model uses."""
    if not value:
        return ""
    try:
        return value.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:  # noqa: BLE001
        return str(value)
