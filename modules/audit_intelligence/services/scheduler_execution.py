"""Scheduler execution orchestration — priority queue, dead-letter queue, and
bounded parallel workers over the EXISTING asset scheduler.

This is an **additive orchestration layer**. It does NOT replace or duplicate the
scheduler: it reuses :mod:`modules.audit_intelligence.services.asset_scheduler`
(``plan_evidence`` / ``execute_plan``) for planning and per-job execution, and the
existing audit persistence (:func:`persistence.get_persistence`) for history. The
classic sequential ``asset_scheduler.execute_plan`` remains the backward-compatible
default; this module adds:

  * **Priority queue** — jobs are ordered ``high`` > ``medium`` > ``low`` from a
    deterministic, backward-compatible rule (never mutates the plan schema).
  * **Dead-letter queue (DLQ)** — a job that fails after ``max_retries`` lands in
    an in-process DLQ with its retry count + failure reason; it can be requeued.
  * **Bounded parallel workers** — a configurable, small worker pool (default 1;
    hard-capped) using a thread pool. Deterministic in tests (a per-job executor
    can be injected; nothing live is hit unless the caller opts in exactly as with
    ``execute_plan``).

Safety: no uncontrolled concurrency (``MAX_WORKERS`` cap), no live network unless
the caller injects an executor/transport (same contract as ``execute_plan``), and
every failure is captured rather than raised.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from modules.audit_intelligence.services import asset_scheduler

#: Priority levels (ordering weight; higher runs first).
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"
_PRIORITY_WEIGHT = {PRIORITY_HIGH: 0, PRIORITY_MEDIUM: 1, PRIORITY_LOW: 2}
DEFAULT_PRIORITY = PRIORITY_MEDIUM

#: Hard cap so a hostile/erroneous config can never spawn unbounded workers.
MAX_WORKERS = 8
DEFAULT_WORKERS = 1
DEFAULT_MAX_RETRIES = 2


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Priority derivation (deterministic; no plan-schema change)
# --------------------------------------------------------------------------- #
#: Technologies whose evidence is treated as higher priority (regulated data /
#: security posture). Deterministic + conservative; callers can override.
_HIGH_PRIORITY_TECHS = {
    "oracle", "postgresql", "sql server", "mysql", "mongodb", "aerospike",
    "yugabyte", "prisma cloud", "checkmarx", "sonarqube",
}
_HIGH_PRIORITY_CONNECTORS = {"prisma_cloud", "checkmarx", "servicenow_cmdb", "archer"}


def job_priority(job: "asset_scheduler.PlannedJob") -> str:
    """Deterministic priority for a planned job (backward-compatible default).

    High: security/GRC connectors or regulated database technologies.
    Low:  jobs with no controls (nothing to assess yet).
    Medium: everything else (the default).
    """
    if job.connector and job.connector.lower() in _HIGH_PRIORITY_CONNECTORS:
        return PRIORITY_HIGH
    if (job.technology or "").strip().lower() in _HIGH_PRIORITY_TECHS:
        return PRIORITY_HIGH
    if not job.control_ids and job.route == asset_scheduler.ROUTE_BASELINE:
        return PRIORITY_LOW
    return DEFAULT_PRIORITY


# --------------------------------------------------------------------------- #
# Queue model
# --------------------------------------------------------------------------- #
@dataclass
class QueueItem:
    """One prioritized unit of scheduler work wrapping a PlannedJob."""

    job: "asset_scheduler.PlannedJob"
    priority: str = DEFAULT_PRIORITY
    attempts: int = 0
    max_retries: int = DEFAULT_MAX_RETRIES
    last_error: str = ""
    enqueued_at: str = field(default_factory=_now)

    @property
    def item_id(self) -> str:
        # Stable within a process for DLQ addressing (asset + connector/scope).
        return f"{self.job.asset_id}::{self.job.connector or self.job.scope_value}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "priority": self.priority,
            "attempts": self.attempts,
            "max_retries": self.max_retries,
            "last_error": self.last_error,
            "enqueued_at": self.enqueued_at,
            "job": self.job.to_dict(),
        }


def build_queue(plan: "asset_scheduler.EvidencePlan", *,
                max_retries: int = DEFAULT_MAX_RETRIES) -> list[QueueItem]:
    """Turn a plan into a priority-ordered queue (high -> medium -> low).

    Ordering is deterministic: (priority weight, route, technology, asset_id).
    Never mutates the plan.
    """
    items = [QueueItem(job=j, priority=job_priority(j), max_retries=max_retries)
             for j in plan.jobs]
    items.sort(key=lambda it: (
        _PRIORITY_WEIGHT.get(it.priority, 1),
        it.job.route, (it.job.technology or "").lower(), it.job.asset_id.lower(),
    ))
    return items


# --------------------------------------------------------------------------- #
# Dead-letter queue (in-process, thread-safe)
# --------------------------------------------------------------------------- #
_DLQ_LOCK = threading.RLock()
_DEAD_LETTERS: dict[str, QueueItem] = {}


def reset_dead_letters() -> None:
    """Test hook: clear the DLQ."""
    with _DLQ_LOCK:
        _DEAD_LETTERS.clear()


def _to_dlq(item: QueueItem) -> None:
    with _DLQ_LOCK:
        _DEAD_LETTERS[item.item_id] = item


def list_dead_letters() -> list[dict[str, Any]]:
    with _DLQ_LOCK:
        return [it.to_dict() for it in _DEAD_LETTERS.values()]


def get_dead_letter(item_id: str) -> Optional[QueueItem]:
    with _DLQ_LOCK:
        return _DEAD_LETTERS.get(item_id)


def remove_dead_letter(item_id: str) -> bool:
    with _DLQ_LOCK:
        return _DEAD_LETTERS.pop(item_id, None) is not None


# --------------------------------------------------------------------------- #
# Execution (bounded parallel workers; reuses asset_scheduler.execute_plan)
# --------------------------------------------------------------------------- #
def _receipt_ok(receipt: Any) -> tuple[bool, str]:
    """Classify an execute_plan receipt as success/failure (handles both shapes).

    * Connector receipts carry an explicit ``ok`` boolean.
    * Baseline run receipts carry a run ``status`` + ``summary`` (from EvidenceRun);
      a run is a failure when it has no completed records but has failures, or its
      status is Failed/Cancelled.
    Returns ``(ok, reason)``. Empty/None receipts are treated as success (nothing
    to collect is not an error).
    """
    if not isinstance(receipt, dict) or not receipt:
        return True, ""
    if "ok" in receipt:  # connector receipt
        return bool(receipt["ok"]), str(receipt.get("status") or receipt.get("error") or "failed")
    status = str(receipt.get("status") or "")
    summ = receipt.get("summary") or {}
    # A baseline run is a failure when it had work to do (total > 0) but nothing
    # completed — covers Failed, Cancelled, Connector Missing, and Configuration
    # Required outcomes uniformly, so unresolved jobs surface in the DLQ.
    if summ.get("total", 0) > 0 and summ.get("completed", 0) == 0:
        return False, status or "run_failed"
    if status in ("Failed", "Cancelled"):
        return False, status
    return True, ""


def _run_one(item: QueueItem, *, executor, run_connectors: bool,
             connector_transport) -> dict[str, Any]:
    """Execute a single queue item's job with bounded retries. Never raises.

    Reuses ``asset_scheduler.execute_plan`` on a one-job plan so there is exactly
    one execution code path (no duplicated per-job logic).
    """
    single = asset_scheduler.EvidencePlan(jobs=[item.job])
    while item.attempts <= item.max_retries:
        item.attempts += 1
        try:
            results = asset_scheduler.execute_plan(
                single, executor=executor, requested_by="scheduler_execution",
                run_connectors=run_connectors, connector_transport=connector_transport,
            )
            receipt = results[0] if results else {}
            ok, reason = _receipt_ok(receipt)
            if ok:
                return {"item_id": item.item_id, "priority": item.priority,
                        "attempts": item.attempts, "status": "completed",
                        "receipt": receipt}
            item.last_error = reason
        except Exception as exc:  # noqa: BLE001 - captured, never propagated
            item.last_error = type(exc).__name__
    # Retries exhausted -> dead-letter.
    _to_dlq(item)
    return {"item_id": item.item_id, "priority": item.priority,
            "attempts": item.attempts, "status": "dead_letter",
            "last_error": item.last_error}


def execute_parallel(
    plan: "asset_scheduler.EvidencePlan",
    *,
    workers: int = DEFAULT_WORKERS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    executor: Optional[Callable] = None,
    run_connectors: bool = True,
    connector_transport=None,
    record_history: bool = True,
) -> dict[str, Any]:
    """Execute a plan with priority ordering, bounded workers, retries, and DLQ.

    * ``workers`` is clamped to ``[1, MAX_WORKERS]`` (default 1 = fully sequential
      and deterministic).
    * Jobs run highest-priority first. With >1 worker, items are submitted in
      priority order to the pool.
    * Failed jobs retry up to ``max_retries``; exhausted ones go to the DLQ.
    * An event is recorded to the existing scheduler history (best-effort).

    Backward compatible: does not touch ``asset_scheduler.execute_plan``; that
    remains the sequential default for existing callers.
    """
    n_workers = max(1, min(int(workers or 1), MAX_WORKERS))
    queue = build_queue(plan, max_retries=max_retries)

    results: list[dict[str, Any]]
    if n_workers == 1:
        results = [
            _run_one(it, executor=executor, run_connectors=run_connectors,
                     connector_transport=connector_transport)
            for it in queue
        ]
    else:
        results = [None] * len(queue)  # type: ignore[list-item]
        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures = {
                pool.submit(_run_one, it, executor=executor,
                            run_connectors=run_connectors,
                            connector_transport=connector_transport): idx
                for idx, it in enumerate(queue)
            }
            for fut, idx in futures.items():
                results[idx] = fut.result()

    completed = sum(1 for r in results if r.get("status") == "completed")
    dead = sum(1 for r in results if r.get("status") == "dead_letter")
    summary = {
        "queued": len(queue),
        "workers": n_workers,
        "completed": completed,
        "dead_letter": dead,
        "by_priority": {
            p: sum(1 for it in queue if it.priority == p)
            for p in (PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW)
        },
    }
    if record_history:
        try:
            from modules.audit_intelligence.services import persistence as _p

            _p.get_persistence().record_scheduler_event({
                "at": _now(), "mode": "parallel", **summary,
            })
        except Exception:  # noqa: BLE001 - history is best-effort
            pass
    return {"ok": True, "summary": summary, "results": results}


def requeue_dead_letter(
    item_id: str,
    *,
    executor: Optional[Callable] = None,
    run_connectors: bool = False,
    connector_transport=None,
) -> dict[str, Any]:
    """Requeue a single DLQ item and re-run it once (safe).

    Removes it from the DLQ, resets its attempt counter, and re-executes via the
    same single-job path. If it fails again it returns to the DLQ. Connector live
    execution stays OFF by default (``run_connectors=False``) so a requeue can
    never accidentally hit the network unless explicitly enabled.
    """
    item = get_dead_letter(item_id)
    if item is None:
        return {"ok": False, "error": "unknown_dead_letter", "item_id": item_id}
    remove_dead_letter(item_id)
    item.attempts = 0
    item.last_error = ""
    result = _run_one(item, executor=executor, run_connectors=run_connectors,
                      connector_transport=connector_transport)
    return {"ok": result.get("status") == "completed", "result": result}


# --------------------------------------------------------------------------- #
# Read-only queue preview (no execution)
# --------------------------------------------------------------------------- #
def preview_queue(config_path: str | None = None, *,
                  max_retries: int = DEFAULT_MAX_RETRIES) -> dict[str, Any]:
    """Build + return the prioritized queue for the configured assets (no run)."""
    assets = asset_scheduler.load_assets(config_path or None)
    plan = asset_scheduler.plan_evidence(assets)
    queue = build_queue(plan, max_retries=max_retries)
    return {
        "ok": True,
        "queue": [it.to_dict() for it in queue],
        "count": len(queue),
        "by_priority": {
            p: sum(1 for it in queue if it.priority == p)
            for p in (PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW)
        },
    }
