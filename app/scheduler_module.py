"""Automated scheduled evidence pull simulation."""

from datetime import datetime, timezone

from app import ecs_state
from app.demo_metrics import SCHEDULER_METRICS
from app.audit_trail import log_event

_scheduler_status = {
    "enabled": True,
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
    from app.evidence_repository import evidence_repository

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


def run_scheduled_pull():
    from app.evidence_repository import refresh_repository_from_frameworks

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    added = refresh_repository_from_frameworks(source="scheduler")
    _scheduler_status["last_pull_at"] = now
    _scheduler_status["last_pull_status"] = "Success"
    _scheduler_status["pulls_completed"] += 1
    _scheduler_status["records_last_pull"] = 412 + (added * 3)
    _execution_history.insert(
        0,
        {
            "timestamp": now,
            "status": "Success",
            "records": _scheduler_status["records_last_pull"],
            "duration_sec": 40,
            "triggered_by": "Manual",
        },
    )
    for job in _scheduler_status["jobs"]:
        job["status"] = "Synced"
        job["last_run"] = now
    log_event("Scheduled Pull", "ECS Scheduler", "", "", f"Added {added} artefacts; {_scheduler_status['records_last_pull']} records")
    return {"timestamp": now, "added": added}
