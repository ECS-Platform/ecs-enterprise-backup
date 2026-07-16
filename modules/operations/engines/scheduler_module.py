"""Automated scheduled evidence pull simulation."""

import time
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

_execution_history: list[dict] = []
_collection_seq = 0


def _scheduler_fetched_evidence(limit: int = 200) -> list[dict]:
    """Latest persisted evidence collected by scheduler connector runs only."""
    artifacts = []
    try:
        from modules.audit_intelligence.services.persistence import get_persistence

        artifacts = get_persistence().list_all_evidence_versions()
    except Exception:  # noqa: BLE001
        artifacts = []
    if not artifacts:
        try:
            from modules.audit_intelligence.engines import evidence_repository as ai_repo

            artifacts = ai_repo.all_artifacts()
        except Exception:  # noqa: BLE001
            artifacts = []

    rows: list[dict] = []
    for art in artifacts:
        source = str(getattr(art, "source", "") or "")
        source_connector = str(getattr(art, "source_connector", "") or "")
        if source == "llm_usecase_demo":
            continue
        if str(getattr(art, "evidence_id", "")).startswith("EV-DEMO-") or str(getattr(art, "evidence_id", "")) == "EV-LLM-ENC-001":
            continue
        meta = dict(getattr(art, "metadata", ()) or ())
        if str(meta.get("demo", "")).strip().lower() == "llm_usecase":
            continue
        # Scheduler connector ingestion persists artifacts as source=manual_upload
        # and may carry connector identity in either source_connector or metadata.source.
        if source not in ("manual_upload", "connector_executor", "asset_scheduler"):
            continue
        connector_name = source_connector or str(meta.get("source", "") or "")
        if not connector_name:
            continue
        framework = ", ".join(getattr(art, "frameworks", ()) or ())
        control = str(getattr(art, "control_id", "") or "")
        rows.append({
            "evidence_id": str(getattr(art, "evidence_id", "") or ""),
            "collected_at": str(getattr(art, "collected_at", "") or ""),
            "source": connector_name,
            "evidence_name": str(getattr(art, "filename", "") or getattr(art, "evidence_id", "")),
            "application": str(getattr(art, "asset_id", "") or ""),
            "framework_control": " / ".join([x for x in (framework, control) if x]),
            "custody_mode": str(getattr(art, "custody_mode", "") or ""),
            "view_url": str(getattr(art, "object_uri", "") or getattr(art, "source_url", "")),
            "download_url": str(getattr(art, "object_uri", "") or getattr(art, "source_url", "")),
        })
    rows.sort(key=lambda r: r.get("collected_at", ""), reverse=True)
    return rows[: max(0, int(limit or 0))]


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
        "fetched_evidence": _scheduler_fetched_evidence(),
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


def _norm_scheduler_key(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


# UI / scheduler-intelligence application labels -> canonical asset keys
# (``application`` field + ``asset_id`` from the asset config). Exact match only.
SCHEDULER_APPLICATION_MAP: dict[str, frozenset[str]] = {
    "net banking": frozenset({"evidence library (mock)", "local-sharepoint-evidence"}),
    "mobile banking": frozenset({"ecs appsec demo", "local-sonarqube"}),
    "payments": frozenset({"change management (mock)", "local-jira-project"}),
    "loan origination": frozenset({"change management (mock)", "local-jira-project"}),
    "internet banking": frozenset({"evidence library (mock)", "local-sharepoint-evidence"}),
    # Pass-through for asset-config application labels (local/UAT YAML).
    "ecs demo": frozenset({
        "ecs demo",
        "local-postgres",
        "local-nginx",
        "local-redis",
        "local-linux-host",
    }),
    "ecs appsec demo": frozenset({"ecs appsec demo", "local-sonarqube"}),
    "evidence library (mock)": frozenset({
        "evidence library (mock)",
        "local-sharepoint-evidence",
    }),
    "change management (mock)": frozenset({
        "change management (mock)",
        "local-jira-project",
    }),
    "cmdb (mock)": frozenset({"cmdb (mock)", "local-servicenow-cmdb"}),
}

# UI framework labels -> canonical framework names on planned jobs (exact, lowercased).
SCHEDULER_FRAMEWORK_ALIASES: dict[str, frozenset[str]] = {
    "pci dss": frozenset({"pci dss"}),
    "pci-dss": frozenset({"pci dss"}),
    "dpsc": frozenset({"dpsc"}),
    "itpp": frozenset({"itpp"}),
    "appsec": frozenset({"appsec"}),
    "csite": frozenset({"csite"}),
    "c-site": frozenset({"csite"}),
    "c site": frozenset({"csite"}),
    "vapt": frozenset({"vapt"}),
    "os baselining": frozenset({"os baselining"}),
    "db baselining": frozenset({"db baselining"}),
}


def _job_canonical_keys(job) -> frozenset[str]:
    keys: set[str] = set()
    for field in ("application", "asset_id"):
        val = _norm_scheduler_key(getattr(job, field, "") or "")
        if val:
            keys.add(val)
    return frozenset(keys)


def normalize_scheduler_applications(applications) -> frozenset[str] | None:
    """Map UI application labels to canonical asset keys.

    Returns ``None`` when the selection is empty (= all jobs). Returns an empty
    set when every selected label is unknown (= zero jobs).
    """
    selected = [_norm_scheduler_key(a) for a in (applications or []) if _norm_scheduler_key(a)]
    if not selected:
        return None
    canonical: set[str] = set()
    unknown_count = 0
    for label in selected:
        mapped = SCHEDULER_APPLICATION_MAP.get(label)
        if mapped is not None:
            canonical.update(mapped)
        else:
            unknown_count += 1
    # Mixed known+unknown UI labels (e.g. enterprise app scans + mapped demo apps)
    # should not over-restrict planning to only the mapped subset.
    if canonical and unknown_count:
        return None
    return frozenset(canonical)


def normalize_scheduler_frameworks(frameworks) -> frozenset[str] | None:
    """Map UI framework labels to canonical framework names on planned jobs."""
    selected = [_norm_scheduler_key(f) for f in (frameworks or []) if _norm_scheduler_key(f)]
    if not selected:
        return None
    canonical: set[str] = set()
    for label in selected:
        mapped = SCHEDULER_FRAMEWORK_ALIASES.get(label)
        if mapped is not None:
            canonical.update(mapped)
    return frozenset(canonical)


def _job_matches_selection(job, applications, frameworks) -> bool:
    """True when a planned job is in scope of the selected apps/frameworks.

    Empty selections mean "all" (no filtering). Unknown labels yield zero jobs.
    Matching is exact on canonical application/asset keys and framework names.
    """
    app_keys = normalize_scheduler_applications(applications)
    if app_keys is not None:
        if not app_keys or not (_job_canonical_keys(job) & app_keys):
            return False
    fw_keys = normalize_scheduler_frameworks(frameworks)
    if fw_keys is not None:
        if not fw_keys:
            return False
        job_fws = {
            _norm_scheduler_key(f)
            for f in (getattr(job, "frameworks", ()) or ())
            if _norm_scheduler_key(f)
        }
        # Connector jobs (e.g. SharePoint/Jira/ServiceNow) carry no predefined
        # framework tags — only baseline/technology jobs do. Don't let framework
        # selection zero out an otherwise-matched connector job for that reason.
        if job_fws and not (job_fws & fw_keys):
            return False
    return True


def run_scheduler_collection(
    *,
    user: str = "System",
    applications=None,
    frameworks=None,
    connector_transport=None,
) -> dict:
    started_perf = time.perf_counter()
    started_utc = datetime.now(timezone.utc)
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
    connector_plan_summary = {
        "planned_jobs": plan_summary.get("planned_jobs", 0),
        "by_route": plan_summary.get("by_route", {}),
    }

    results: list[dict] = []
    ingested = 0
    if live:
        # Execute only connector jobs here; baseline jobs are planned/visible but
        # collected by the predefined-query flow with its own executor path.
        connector_plan = asset_scheduler.EvidencePlan(
            jobs=[j for j in plan.jobs if getattr(j, "connector", "")],
            unsupported=[],
        )
        connector_plan_summary = connector_plan.to_dict()["summary"]
        results = asset_scheduler.execute_plan(
            connector_plan, run_connectors=True, connector_transport=connector_transport,
            requested_by=user or "scheduler",
        )
        ingested = sum(int(r.get("ingested", 0) or 0) for r in results if isinstance(r, dict))

    duration_sec = max(0, int(round(time.perf_counter() - started_perf)))
    completed_utc = datetime.now(timezone.utc)
    job_results = [r for r in results if isinstance(r, dict)]
    zero_or_failed = [
        r for r in job_results
        if (int(r.get("ingested", 0) or 0) == 0) or (r.get("ok") is False)
    ]
    status = "Success"
    if job_results and zero_or_failed:
        status = "Partial"
    if live and connector_plan_summary.get("planned_jobs", 0) and not job_results:
        status = "Failed"
    global _collection_seq
    _collection_seq += 1
    run_id = f"COLL-{started_utc.strftime('%Y%m%d-%H%M%S')}-{_collection_seq:03d}"
    log_preview = [
        f"[{started_utc.strftime('%H:%M:%S')} UTC] Collection started",
        f"planned_jobs={connector_plan_summary.get('planned_jobs', 0)} connectors={','.join(sorted({j.connector for j in plan.jobs if j.connector})) or '-'}",
        f"[{completed_utc.strftime('%H:%M:%S')} UTC] completed status={status} ingested={ingested}",
    ]
    _execution_history.insert(0, {
        "run_id": run_id,
        "trigger_type": "Manual",
        "started": started_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "completed": completed_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "duration_sec": duration_sec,
        "apps_covered": len(apps),
        "evidence_count": ingested,
        "status": status,
        "initiated_by": user or "System",
        "log_preview": log_preview,
        "job_results": job_results,
    })

    try:
        from modules.shared.services.ecs_logging import log_scheduler
        log_scheduler(
            f"Evidence collection {mode}",
            f"planned_jobs={connector_plan_summary.get('planned_jobs', 0)}; ingested={ingested}",
            user=user,
        )
    except Exception:  # noqa: BLE001 - logging must never break the run
        pass

    return {
        "ok": True,
        "run_id": run_id,
        "status": status,
        "duration_sec": duration_sec,
        "mode": mode,
        "timestamp": now,
        "applications": apps,
        "frameworks": fws,
        "planned_jobs": connector_plan_summary.get("planned_jobs", 0),
        "by_route": connector_plan_summary.get("by_route", {}),
        "connectors": sorted({j.connector for j in plan.jobs if j.connector}),
        "ingested": ingested,
        "results": results,
    }
