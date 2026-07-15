"""Automated scheduled evidence pull simulation."""

from datetime import datetime, timezone

from app import ecs_state
from modules.executive_overview.engines.demo_metrics import SCHEDULER_METRICS
from modules.shared.services.audit_trail import log_event

_scheduler_status = {
    "enabled": True,
    "paused": False,
    "last_pull_at": SCHEDULER_METRICS["last_pull_at"],
    "last_pull_status": SCHEDULER_METRICS["last_pull_status"],
    "pulls_completed": SCHEDULER_METRICS["pulls_completed"],
    "next_scheduled": "Every 6 hours (02:00 / 08:00 / 14:00 / 20:00 IST)",
    "records_last_pull": SCHEDULER_METRICS["records_last_pull"],
    "success_rate_pct": SCHEDULER_METRICS["success_rate_pct"],
    "avg_duration_sec": SCHEDULER_METRICS["avg_duration_sec"],
    "jobs": [
        {
            "source": "SharePoint Evidence Library",
            "framework": "PCI DSS",
            "status": "Synced",
            "last_run": "2026-05-24 06:00 UTC",
            "records": 128,
        },
        {
            "source": "ServiceNow GRC",
            "framework": "DPSC",
            "status": "Synced",
            "last_run": "2026-05-24 06:01 UTC",
            "records": 96,
        },
        {
            "source": "SIEM Export Pipeline",
            "framework": "CSITE",
            "status": "Synced",
            "last_run": "2026-05-24 06:02 UTC",
            "records": 188,
        },
        {
            "source": "CMDB Baselining Agent",
            "framework": "OS Baselining",
            "status": "Ready",
            "last_run": "2026-05-23 20:00 UTC",
            "records": 74,
        },
    ],
}

_execution_history = [
    {
        "timestamp": "2026-05-24 06:00:12 UTC",
        "status": "Success",
        "records": 412,
        "duration_sec": 38,
        "triggered_by": "Cron",
    },
    {
        "timestamp": "2026-05-24 00:00:09 UTC",
        "status": "Success",
        "records": 405,
        "duration_sec": 41,
        "triggered_by": "Cron",
    },
    {
        "timestamp": "2026-05-23 18:00:15 UTC",
        "status": "Success",
        "records": 398,
        "duration_sec": 44,
        "triggered_by": "Cron",
    },
    {
        "timestamp": "2026-05-23 12:00:11 UTC",
        "status": "Partial",
        "records": 360,
        "duration_sec": 52,
        "triggered_by": "Cron",
    },
    {
        "timestamp": "2026-05-23 06:00:08 UTC",
        "status": "Success",
        "records": 401,
        "duration_sec": 39,
        "triggered_by": "Manual (Compliance Officer)",
    },
]


def _repository_count():
    from modules.operations.engines.evidence_repository import evidence_repository

    return len(evidence_repository)


def get_scheduler_dashboard():
    rows = []
    for row in ecs_state.scheduler_data:
        rows.append(
            {
                "application": row[0],
                "framework": row[1],
                "status": row[2],
                "owner": row[3] if len(row) > 3 else "—",
                "last_sync": row[4] if len(row) > 4 else "—",
            }
        )
    return {
        "status": _scheduler_status.copy(),
        "scheduler_rows": rows,
        "scheduler_data": ecs_state.scheduler_data,
        "repository_count": max(_repository_count(), SCHEDULER_METRICS["records_last_pull"] // 3),
        "execution_history": _execution_history,
    }


def run_scheduled_pull(user: str = "System") -> dict:
    from modules.operations.engines.evidence_repository import refresh_repository_from_frameworks

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    added = refresh_repository_from_frameworks(source="scheduler")
    observations_scanned = 18 + (added % 6)
    new_findings = max(1, added // 3)
    _scheduler_status["last_pull_at"] = now
    _scheduler_status["last_pull_status"] = "Success"
    _scheduler_status["pulls_completed"] += 1
    _scheduler_status["records_last_pull"] = 412 + (added * 3)
    run_id = f"RUN-{now.replace(' ', '-').replace(':', '')[:15]}"
    _execution_history.insert(
        0,
        {
            "run_id": run_id,
            "timestamp": now,
            "status": "Success",
            "records": _scheduler_status["records_last_pull"],
            "duration_sec": 40,
            "triggered_by": f"Manual ({user})" if user != "System" else "Manual",
            "observations_scanned": observations_scanned,
            "new_findings": new_findings,
        },
    )
    for job in _scheduler_status["jobs"]:
        job["status"] = "Synced"
        job["last_run"] = now
    for i, row in enumerate(ecs_state.scheduler_data):
        app, fw, status, owner, _ = row[:5]
        ecs_state.scheduler_data[i] = (app, fw, "Implemented", owner, now)
    log_event(
        "Scheduled Pull",
        user or "ECS Scheduler",
        "",
        "",
        f"Scanned {observations_scanned} observations; {new_findings} new findings; {added} artefacts added",
    )
    try:
        from modules.shared.services.ecs_logging import log_scheduler
        log_scheduler("Evidence sync completed", f"{observations_scanned} observations; {new_findings} findings; {added} artefacts", user=user)
    except Exception:
        pass
    return {
        "timestamp": now,
        "added": added,
        "run_id": run_id,
        "observations_scanned": observations_scanned,
        "new_findings": new_findings,
        "records": _scheduler_status["records_last_pull"],
    }


def retry_failed_observation(failure_id: str, user: str = "System") -> dict:
    """Reprocess a failed scheduler observation — updates failure queue and logs."""
    from modules.operations.engines.scheduler_intelligence import _seed_scheduler_failures

    failures = _seed_scheduler_failures()
    target = next((f for f in failures if f.get("failure_id") == failure_id), None)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    if not target:
        return {"ok": False, "message": f"Failure {failure_id} not found.", "status": "Failed"}

    target["retry_status"] = "Retrying"
    target["last_retry_at"] = ts
    target["retry_count"] = target.get("retry_count", 0) + 1
    ecs_state.scheduler_retry_log.insert(0, {
        "failure_id": failure_id,
        "timestamp": ts,
        "actor": user,
        "status": "Retrying",
        "detail": f"Reprocessing {target.get('source', 'integration')} pull",
    })

    import random
    success = random.Random(failure_id + ts).random() > 0.15
    if success:
        target["retry_status"] = "Completed"
        target["resolved_at"] = ts
        if target in ecs_state.scheduler_failures:
            ecs_state.scheduler_failures.remove(target)
        ecs_state.scheduler_retry_log[0]["status"] = "Completed"
        msg = f"Observation reprocessed successfully — {failure_id} removed from failed queue."
        log_event("Scheduler Retry", user, "", failure_id, msg)
    else:
        target["retry_status"] = "Failed Again"
        ecs_state.scheduler_retry_log[0]["status"] = "Failed Again"
        msg = f"Retry failed for {failure_id} — queued for next scheduler window."
        log_event("Scheduler Retry Failed", user, "", failure_id, msg)

    return {"ok": success, "message": msg, "status": target["retry_status"], "failure_id": failure_id}


def pause_scheduler(user: str = "") -> str:
    _scheduler_status["paused"] = True
    log_event("Scheduler Paused", user or "System", "", "", "Non-critical collection jobs paused")
    try:
        from modules.shared.services.ecs_logging import log_scheduler
        log_scheduler("Scheduler paused", user=user)
    except Exception:
        pass
    return "Scheduler paused — non-critical evidence collection jobs suspended."


def resume_scheduler(user: str = "") -> str:
    _scheduler_status["paused"] = False
    log_event("Scheduler Resumed", user or "System", "", "", "Collection jobs resumed")
    try:
        from modules.shared.services.ecs_logging import log_scheduler
        log_scheduler("Scheduler resumed", user=user)
    except Exception:
        pass
    return "Scheduler resumed — all collection jobs active."


def is_scheduler_paused() -> bool:
    return bool(_scheduler_status.get("paused"))


def _job_matches_selection(job, applications, frameworks) -> bool:
    """True when a planned job is in scope of the selected apps/frameworks.

    Empty selections mean "all" (no filtering). Matching is case-insensitive and
    based on the job's ``scope_value`` (the application/asset scope) and its
    ``frameworks``. Reuses the planner's own job shape — no new scoping model.
    """
    apps = {a.strip().lower() for a in (applications or []) if str(a).strip()}
    fws = {f.strip().lower() for f in (frameworks or []) if str(f).strip()}
    if apps:
        scope = str(getattr(job, "scope_value", "") or "").lower()
        asset = str(getattr(job, "asset_id", "") or "").lower()
        if not (scope in apps or asset in apps or any(a in scope for a in apps)):
            return False
    if fws:
        job_fws = {str(f).strip().lower() for f in (getattr(job, "frameworks", ()) or ())}
        if not (job_fws & fws):
            return False
    return True


def run_scheduler_collection(
    *,
    user: str = "System",
    applications=None,
    frameworks=None,
    connector_transport=None,
) -> dict:
    """Run evidence collection via the REAL asset-scheduler / connector-executor.

    Reuses the existing services (no new orchestration, connectors, or
    persistence):
      * ``asset_scheduler`` loads the existing asset config, classifies + plans
        jobs, and (dry-run) reports what *would* run;
      * ``connector_executor`` performs live evidence ingestion into the EXISTING
        repository — but only when ``ECS_CONNECTOR_EXECUTION_ENABLED=true`` (or a
        ``connector_transport`` is injected for tests).

    Safe by default: with the flag off and no injected transport this is a
    **dry-run** — the planner runs, but no connector call and no network happen.
    Returns a JSON-safe result carrying the real plan/execution outcome (no
    fabricated counters or log lines).
    """
    from modules.audit_intelligence.services import asset_scheduler
    from modules.audit_intelligence.services import connector_executor

    apps = [a for a in (applications or []) if str(a).strip()]
    fws = [f for f in (frameworks or []) if str(f).strip()]

    # Build the plan from the existing asset configuration (reuse; never invents).
    assets = asset_scheduler.load_assets()
    plan = asset_scheduler.plan_evidence(assets)
    # Filter planned jobs to the operator's selection (empty selection = all).
    plan.jobs = [j for j in plan.jobs if _job_matches_selection(j, apps, fws)]

    live = connector_transport is not None or connector_executor.execution_enabled()
    mode = "live" if live else "dry-run"

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    plan_summary = plan.to_dict()["summary"]

    results: list[dict] = []
    ingested = 0
    if live:
        # Execute only the connector jobs here (baseline jobs need an executor and
        # live DB/driver targets; those are driven by the predefined-query flow).
        results = asset_scheduler.execute_plan(
            plan, run_connectors=True, connector_transport=connector_transport,
            requested_by=user or "scheduler",
        )
        ingested = sum(int(r.get("ingested", 0) or 0) for r in results if isinstance(r, dict))

    try:
        from modules.shared.services.ecs_logging import log_scheduler
        log_scheduler(
            f"Evidence collection {mode}",
            f"planned_jobs={plan_summary.get('planned_jobs', 0)}; ingested={ingested}",
            user=user,
        )
    except Exception:  # noqa: BLE001 - logging must never break the run
        pass

    return {
        "ok": True,
        "mode": mode,
        "timestamp": now,
        "applications": apps,
        "frameworks": fws,
        "planned_jobs": plan_summary.get("planned_jobs", 0),
        "by_route": plan_summary.get("by_route", {}),
        "connectors": sorted({j.connector for j in plan.jobs if j.connector}),
        "ingested": ingested,
        "results": results,
    }
