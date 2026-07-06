"""Evidence Collection Orchestrator (Milestone 2).

Turns a *scope* (asset / application / environment / framework / technology / the
whole bank) into a set of applicable controls, executes each through the EXISTING
predefined-query engine (the execution layer), captures normalized evidence
metadata, tracks per-control and overall status, supports retry, and records an
audit trail. Scheduler hooks let an external scheduler enqueue/trigger runs.

Design / safety:
  * Reuses ``predefined_queries_engine`` for execution — no new execution logic and
    no connector changes. Non-executable controls are marked without attempting a
    connection, so a run never crashes on missing drivers/targets.
  * A pluggable ``executor`` (defaulting to the real engine) makes runs fully
    unit-testable offline with mocked results.
  * State is in-memory (a run store); durable persistence is the Evidence
    Repository (Milestone 3). Nothing here stores credentials/secrets.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from modules.audit_intelligence.engines import technology_control_mapping as mapping
from modules.audit_intelligence.models import (
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_CONFIG_REQUIRED,
    STATUS_CONNECTOR_MISSING,
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_QUEUED,
    STATUS_RUNNING,
    EvidenceRecord,
    EvidenceRun,
)

#: An executor runs one control and returns the engine's result dict.
Executor = Callable[[str, str], dict[str, Any]]

_OUTPUT_EXCERPT_CHARS = 500

# Map an engine error_type -> a run status (so the UI/report can act on it).
_ERROR_TYPE_STATUS = {
    "connector_unavailable": STATUS_CONNECTOR_MISSING,
    "missing_connector": STATUS_CONNECTOR_MISSING,
    "configuration_required": STATUS_CONFIG_REQUIRED,
    "config_required": STATUS_CONFIG_REQUIRED,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_run_id() -> str:
    return f"RUN-{uuid.uuid4().hex[:12]}"


def _invalidate_dashboard_cache() -> None:
    """Best-effort dashboard-cache drop after a run change (never raises)."""
    try:
        from modules.audit_intelligence.services import dashboard_service

        dashboard_service.invalidate_dashboard_cache()
    except Exception:  # noqa: BLE001 - cache invalidation must never raise
        pass


# --------------------------------------------------------------------------- #
# In-memory run store (Milestone 3 adds durable persistence)
# --------------------------------------------------------------------------- #
_RUNS: dict[str, EvidenceRun] = {}

#: Safety cap on retained runs (prevents unbounded memory growth in a long-lived
#: process). Oldest runs are evicted first. Durable persistence lifts this.
MAX_RETAINED_RUNS = 500


def _store(run: EvidenceRun) -> EvidenceRun:
    _RUNS[run.run_id] = run
    if len(_RUNS) > MAX_RETAINED_RUNS:
        # Evict oldest by creation time.
        for rid, _ in sorted(_RUNS.items(), key=lambda kv: kv[1].created_at)[
            : len(_RUNS) - MAX_RETAINED_RUNS
        ]:
            _RUNS.pop(rid, None)
    _invalidate_dashboard_cache()
    return run


def get_run(run_id: str) -> EvidenceRun | None:
    return _RUNS.get(run_id)


def list_runs() -> list[EvidenceRun]:
    return sorted(_RUNS.values(), key=lambda r: r.created_at, reverse=True)


def reset_runs() -> None:
    """Clear the in-memory run store (used by tests)."""
    _RUNS.clear()
    _invalidate_dashboard_cache()


# --------------------------------------------------------------------------- #
# Default executor (real engine) — replaceable in tests
# --------------------------------------------------------------------------- #
def _default_executor(control_id: str, user: str) -> dict[str, Any]:
    from modules.operations.engines import predefined_queries_engine as engine

    return engine.run_predefined_query(control_id, user)


# --------------------------------------------------------------------------- #
# Scope resolution -> control ids
# --------------------------------------------------------------------------- #
def resolve_scope(scope_kind: str, scope_value: str = "") -> list[str]:
    """Return the control_ids applicable to a scope.

    scope_kind:
      * technology  -> controls for that technology
      * framework   -> controls for that framework
      * control     -> a single control (scope_value = control_id)
      * asset       -> controls applicable to the asset's technology (scope_value
                        may be an Asset dict or an asset technology name)
      * application / environment -> best-effort: all controls (assets are not yet
                        persisted; Milestone 3 narrows this). Documented assumption.
      * all         -> every control in the catalog
    """
    kind = (scope_kind or "").strip().lower()
    if kind == "technology":
        return [c.control_id for c in mapping.controls_for_technology(scope_value)]
    if kind == "framework":
        return [c.control_id for c in mapping.controls_for_framework(scope_value)]
    if kind == "control":
        ctrl = mapping.get_control(scope_value)
        return [ctrl.control_id] if ctrl else []
    if kind == "asset":
        tech = scope_value if isinstance(scope_value, str) else ""
        if isinstance(scope_value, dict):
            tech = scope_value.get("technology", "")
        return [c.control_id for c in mapping.controls_for_technology(tech)] if tech else []
    if kind in ("application", "environment", "all"):
        return [c.control_id for c in mapping.all_controls()]
    return []


# --------------------------------------------------------------------------- #
# Run lifecycle
# --------------------------------------------------------------------------- #
def create_run(
    *,
    scope_kind: str,
    scope_value: str = "",
    requested_by: str = "system",
    control_ids: list[str] | None = None,
    asset_id: str = "",
) -> EvidenceRun:
    """Create a QUEUED run for a scope (or an explicit control_ids list)."""
    ids = list(control_ids) if control_ids is not None else resolve_scope(scope_kind, scope_value)
    run = EvidenceRun(
        run_id=_new_run_id(),
        scope_kind=scope_kind,
        scope_value=str(scope_value),
        requested_by=requested_by,
        status=STATUS_QUEUED,
        created_at=_now(),
    )
    for cid in ids:
        ctrl = mapping.get_control(cid)
        run.records.append(
            EvidenceRecord(
                control_id=cid,
                technology=ctrl.technology if ctrl else "",
                frameworks=ctrl.frameworks if ctrl else (),
                executable=bool(ctrl and ctrl.executable),
                asset_id=asset_id,
                status=STATUS_QUEUED,
            )
        )
    _audit(run, "run_created", f"{len(run.records)} control(s) queued for {scope_kind}:{scope_value}")
    return _store(run)


def _audit(run: EvidenceRun, event: str, detail: str, control_id: str = "") -> None:
    run.audit_trail.append(
        {"at": _now(), "event": event, "control_id": control_id, "detail": detail}
    )


def _apply_result(record: EvidenceRecord, result: dict[str, Any]) -> None:
    """Fold an engine result dict into an EvidenceRecord (mutates in place)."""
    record.attempts += 1
    record.ok = bool(result.get("ok"))
    if record.ok:
        record.status = STATUS_COMPLETED
        record.message = str(result.get("message") or "")
        record.rows_returned = int(result.get("rows_returned") or 0)
        record.duration_ms = int(result.get("duration_ms") or 0)
        record.evidence_id = str(result.get("evidence_id") or "")
        record.evidence_filename = str(result.get("evidence_filename") or "")
        output = str(result.get("output") or "")
        record.output_excerpt = output[:_OUTPUT_EXCERPT_CHARS]
        record.error_type = ""
    else:
        error_type = str(result.get("error_type") or "error")
        record.error_type = error_type
        record.message = str(result.get("error") or result.get("reason") or "Execution failed")
        record.status = _ERROR_TYPE_STATUS.get(error_type, STATUS_FAILED)


def _finalize_status(run: EvidenceRun) -> None:
    total = len(run.records)
    completed = sum(1 for r in run.records if r.status == STATUS_COMPLETED)
    cancelled = sum(1 for r in run.records if r.status == STATUS_CANCELLED)
    if total == 0:
        run.status = STATUS_COMPLETED
    elif completed == total:
        run.status = STATUS_COMPLETED
    elif completed == 0 and cancelled == 0:
        run.status = STATUS_FAILED
    else:
        run.status = STATUS_PARTIAL
    run.finished_at = _now()


def execute_run(
    run_id: str,
    *,
    executor: Executor | None = None,
    user: str = "",
    skip_non_executable: bool = True,
) -> EvidenceRun:
    """Execute all QUEUED records of a run through the executor.

    Non-executable controls are marked CONFIG_REQUIRED without attempting a
    connection (safe default). Returns the updated run.
    """
    run = get_run(run_id)
    if run is None:
        raise KeyError(f"Unknown run_id: {run_id}")
    exec_fn = executor or _default_executor
    actor = user or run.requested_by

    run.status = STATUS_RUNNING
    run.started_at = _now()
    _audit(run, "run_started", f"executing {len(run.records)} record(s)")

    for record in run.records:
        if record.status == STATUS_CANCELLED:
            continue
        if skip_non_executable and not record.executable:
            record.status = STATUS_CONFIG_REQUIRED
            record.message = "Control is not enabled for live execution in this environment."
            _audit(run, "control_skipped", record.message, record.control_id)
            continue
        try:
            result = exec_fn(record.control_id, actor)
        except Exception as exc:  # noqa: BLE001 - never let one control kill the run
            record.attempts += 1
            record.ok = False
            record.status = STATUS_FAILED
            record.error_type = "executor_exception"
            record.message = f"Executor raised: {type(exc).__name__}"
            _audit(run, "control_error", record.message, record.control_id)
            continue
        _apply_result(record, result)
        _audit(run, "control_executed", f"{record.status} ({record.error_type or 'ok'})", record.control_id)

    _finalize_status(run)
    _audit(run, "run_finished", run.status)
    return run


def retry_failed(
    run_id: str,
    *,
    executor: Executor | None = None,
    user: str = "",
) -> EvidenceRun:
    """Re-execute only the records that failed (FAILED / connector / config).

    Retryable statuses reset to QUEUED and are re-run. Non-executable controls stay
    CONFIG_REQUIRED. Returns the updated run.
    """
    run = get_run(run_id)
    if run is None:
        raise KeyError(f"Unknown run_id: {run_id}")
    retryable = {STATUS_FAILED, STATUS_CONNECTOR_MISSING, STATUS_CONFIG_REQUIRED}
    to_retry = [r for r in run.records if r.status in retryable and r.executable]
    if not to_retry:
        _audit(run, "retry_noop", "no retryable records")
        return run

    exec_fn = executor or _default_executor
    actor = user or run.requested_by
    run.status = STATUS_RUNNING
    _audit(run, "retry_started", f"retrying {len(to_retry)} record(s)")
    for record in to_retry:
        try:
            result = exec_fn(record.control_id, actor)
        except Exception as exc:  # noqa: BLE001
            record.attempts += 1
            record.status = STATUS_FAILED
            record.error_type = "executor_exception"
            record.message = f"Executor raised: {type(exc).__name__}"
            continue
        _apply_result(record, result)
        _audit(run, "control_retried", f"{record.status}", record.control_id)
    _finalize_status(run)
    _audit(run, "retry_finished", run.status)
    return run


def cancel_run(run_id: str, *, user: str = "") -> EvidenceRun:
    """Cancel a run: any not-yet-completed record becomes CANCELLED."""
    run = get_run(run_id)
    if run is None:
        raise KeyError(f"Unknown run_id: {run_id}")
    for record in run.records:
        if record.status in (STATUS_QUEUED, STATUS_RUNNING):
            record.status = STATUS_CANCELLED
    run.status = STATUS_CANCELLED
    run.finished_at = _now()
    _audit(run, "run_cancelled", f"cancelled by {user or 'system'}")
    return run


# --------------------------------------------------------------------------- #
# Convenience: create + execute in one call, plus scheduler hooks
# --------------------------------------------------------------------------- #
def run_scope(
    *,
    scope_kind: str,
    scope_value: str = "",
    requested_by: str = "system",
    executor: Executor | None = None,
    control_ids: list[str] | None = None,
    asset_id: str = "",
) -> EvidenceRun:
    """Create a run for a scope and execute it immediately."""
    run = create_run(
        scope_kind=scope_kind, scope_value=scope_value,
        requested_by=requested_by, control_ids=control_ids, asset_id=asset_id,
    )
    return execute_run(run.run_id, executor=executor, user=requested_by)


def enqueue_scheduled_run(
    *,
    scope_kind: str,
    scope_value: str = "",
    schedule_id: str = "",
    requested_by: str = "scheduler",
) -> EvidenceRun:
    """Scheduler hook: create (but do NOT execute) a run for later pickup.

    An external scheduler calls this to enqueue work, then calls
    :func:`execute_run` (e.g. from a worker). Kept execution-free so scheduling is
    decoupled from execution.
    """
    run = create_run(scope_kind=scope_kind, scope_value=scope_value, requested_by=requested_by)
    if schedule_id:
        _audit(run, "scheduled", f"schedule_id={schedule_id}")
    return run


def due_runs() -> list[EvidenceRun]:
    """Scheduler hook: queued runs awaiting execution (FIFO by creation time)."""
    return sorted(
        (r for r in _RUNS.values() if r.status == STATUS_QUEUED),
        key=lambda r: r.created_at,
    )
