"""Large-scale realistic Operations mock datasets with framework/application continuity."""

from __future__ import annotations

import hashlib

from app.operations_catalog import (
    ALL_FRAMEWORKS,
    BANKING_APPLICATIONS,
    CONNECTORS_BY_FRAMEWORK,
    FRAMEWORK_CONTROLS,
    FRAMEWORK_EVIDENCE,
    MODULE_STATUSES,
    OWNERS,
    owner_for,
)

_SCHEDULER_SOURCES = [
    "SharePoint", "ServiceNow GRC", "Prisma Cloud", "Tripwire", "SonarQube",
    "Checkmarx", "Splunk SIEM", "Jira", "ServiceNow CMDB",
]


def _seed(s: str) -> int:
    return int(hashlib.sha256(s.encode()).hexdigest()[:8], 16)


def _pick(items: list, seed: str):
    return items[_seed(seed) % len(items)]


def generate_scheduler_jobs(count: int = 150) -> list[dict]:
    jobs = []
    statuses = MODULE_STATUSES["scheduler"]
    for i in range(count):
        fw = ALL_FRAMEWORKS[i % len(ALL_FRAMEWORKS)]
        app = BANKING_APPLICATIONS[i % len(BANKING_APPLICATIONS)]
        s = _seed(f"sched-{i}")
        st = statuses[s % len(statuses)]
        risk = ["Critical", "High", "Medium", "Low"][s % 4]
        if st in ("Failed", "Partial"):
            risk = "High" if risk == "Low" else risk
        jobs.append({
            "job_id": f"SCH-JOB-{i+1:04d}",
            "framework": fw,
            "application": app,
            "owner": owner_for(app),
            "risk": risk,
            "status": st,
            "health": "Healthy" if st in ("Completed", "Success", "Running") else "Attention",
            "source_system": _pick(_SCHEDULER_SOURCES, f"src-{i}"),
            "frequency": ["Every 6 hours", "Daily", "Every 12 hours", "Weekly"][s % 4],
            "last_run": f"2026-05-{(s % 20) + 1:02d} {(s % 12) + 2:02d}:{s % 60:02d} UTC",
            "next_run": f"2026-05-24 {(s % 12) + 8:02d}:00 UTC",
            "evidence_collected": 8 + (s % 45),
            "controls_validated": 2 + (s % 18),
            "failed_collections": 0 if st not in ("Failed", "Partial") else 1 + (s % 3),
            "retry_status": "—" if st not in ("Failed", "Partial", "Delayed") else "Pending retry",
            "name": f"{fw} evidence pull — {app}",
        })
    return jobs


def generate_application_scans(count: int = 120) -> list[dict]:
    scans = []
    for i in range(count):
        fw = ALL_FRAMEWORKS[i % len(ALL_FRAMEWORKS)]
        app = BANKING_APPLICATIONS[(i * 3) % len(BANKING_APPLICATIONS)]
        s = _seed(f"scan-{i}")
        risk = ["Critical", "High", "Medium", "Low"][s % 4]
        health = "Healthy" if risk in ("Low", "Medium") else ("Attention" if risk == "Medium" else "Critical")
        scans.append({
            "framework": fw,
            "application": app,
            "owner": owner_for(app),
            "risk": risk,
            "status": health,
            "health": health,
            "evidence_collected": 12 + (s % 80),
            "controls_passed": 5 + (s % 25),
            "controls_pending": s % 8,
            "missing_evidence": s % 5,
            "last_scan": f"2026-05-{(s % 22) + 1:02d} {(s % 12) + 6:02d}:00 UTC",
        })
    return scans


def generate_cron_runs(count: int = 40) -> list[dict]:
    runs = []
    for i in range(count):
        fw = ALL_FRAMEWORKS[i % len(ALL_FRAMEWORKS)]
        app = BANKING_APPLICATIONS[i % len(BANKING_APPLICATIONS)]
        s = _seed(f"cron-{i}")
        health = ["Success", "Partial", "Failed"][s % 3]
        runs.append({
            "run_id": f"CRON-202605{(20 + i % 5):02d}-{i:04d}",
            "label": f"Cron run {i+1} — {fw}",
            "framework": fw,
            "application": app,
            "owner": owner_for(app),
            "risk": "High" if health == "Failed" else "Medium",
            "status": health,
            "timestamp": f"2026-05-{(20 + i % 5):02d} {(i % 12) + 2:02d}:00 IST",
            "duration_sec": 25 + (s % 40),
            "applications_scanned": 10 + (s % 35),
            "evidence_collected": 50 + (s % 300),
            "controls_validated": 10 + (s % 70),
            "failures": 0 if health == "Success" else 1 + (s % 3),
            "health": health,
            "retry_count": 0 if health == "Success" else s % 2,
            "details": [f"{fw} scan for {app}", f"Evidence pull via {_pick(_SCHEDULER_SOURCES, str(i))}"],
        })
    return runs


def generate_upload_records(count: int = 120) -> list[dict]:
    rows = []
    statuses = MODULE_STATUSES["upload"]
    for i in range(count):
        fw = ALL_FRAMEWORKS[i % len(ALL_FRAMEWORKS)]
        app = BANKING_APPLICATIONS[(i * 2) % len(BANKING_APPLICATIONS)]
        s = _seed(f"upload-{i}")
        st = statuses[s % len(statuses)]
        ev_type = FRAMEWORK_EVIDENCE[fw][s % len(FRAMEWORK_EVIDENCE[fw])]
        ctrl = FRAMEWORK_CONTROLS[fw][s % len(FRAMEWORK_CONTROLS[fw])]
        risk = "High" if st == "Rejected" else (["Low", "Medium", "High"][s % 3])
        rows.append({
            "batch_id": f"BATCH-{(i // 5) + 1:04d}",
            "filename": f"{app.replace(' ', '')}_{fw.replace(' ', '')}_{ev_type.replace(' ', '_')}_{i+1}.pdf",
            "framework": fw,
            "application": app,
            "owner": owner_for(app),
            "risk": risk,
            "status": st,
            "evidence_type": ev_type,
            "control_id": ctrl,
            "uploaded_at": f"2026-05-{(s % 22) + 1:02d} {(s % 12) + 8:02d}:{s % 60:02d} UTC",
            "uploaded_by": owner_for(app),
            "mapped_controls": ctrl,
            "auditor_review": st if st != "Uploaded" else "Not Started",
            "file_count": 1 + (s % 8),
            "error_count": 1 if st == "Rejected" else 0,
            "progress_pct": 100 if st == "Approved" else (65 if st == "Validating" else 85),
        })
    return rows


def generate_upload_batches(upload_rows: list[dict]) -> list[dict]:
    batches: dict[str, dict] = {}
    for r in upload_rows:
        bid = r["batch_id"]
        if bid not in batches:
            batches[bid] = {
                "batch_id": bid,
                "framework": r["framework"],
                "application": r["application"],
                "owner": r["owner"],
                "risk": r["risk"],
                "status": r["status"],
                "framework_mapping": r["framework"],
                "uploaded_by": r["uploaded_by"],
                "uploaded_at": r["uploaded_at"],
                "file_count": 0,
                "error_count": 0,
                "progress_pct": r.get("progress_pct", 100),
            }
        batches[bid]["file_count"] += 1
        batches[bid]["error_count"] += r.get("error_count", 0)
    return list(batches.values())


def generate_onboarding_records(count: int = 80) -> list[dict]:
    rows = []
    statuses = MODULE_STATUSES["onboarding"]
    for i in range(count):
        fw = ALL_FRAMEWORKS[i % len(ALL_FRAMEWORKS)]
        app = BANKING_APPLICATIONS[i % len(BANKING_APPLICATIONS)]
        s = _seed(f"onb-{i}")
        st = statuses[s % len(statuses)]
        discovered = 10 + (s % 25)
        implemented = int(discovered * (0.55 + (s % 30) / 100))
        missing = max(0, discovered - implemented - (s % 3))
        risk = ["Critical", "High", "Medium", "Low"][s % 4]
        rows.append({
            "application": app,
            "framework": fw,
            "owner": owner_for(app),
            "risk": risk,
            "status": st,
            "stage": "Registration Complete" if st == "Completed" else ("Framework Mapping" if st == "In Progress" else st),
            "progress_pct": min(98, 40 + (s % 55)) if st != "Failed Discovery" else 25 + (s % 30),
            "frameworks_mapped": 3 + (s % 6),
            "controls_discovered": discovered,
            "controls_implemented": implemented,
            "controls_missing": missing,
            "readiness_pct": round(implemented / max(discovered, 1) * 100, 1),
            "pipeline_id": f"PIPE-{i+1:03d}",
        })
    return rows


def generate_integration_events(count: int = 120) -> list[dict]:
    from app.integration_health_engine import build_integration_health_rows

    base = build_integration_health_rows()
    events = []
    for i, r in enumerate(base):
        events.append({
            **r,
            "timestamp": r.get("timestamp", f"2026-05-24 06:00 UTC"),
            "level": "Error" if r["health"] == "Failed" else ("Warning" if r["health"] == "Partial" else "Info"),
            "message": r["issue"] if r["issue"] != "—" else f"{r['connector']} sync OK",
            "outcome": r["sync_status"],
            "connector": r["connector"],
        })
    idx = len(events)
    while idx < count:
        fw = ALL_FRAMEWORKS[idx % len(ALL_FRAMEWORKS)]
        app = BANKING_APPLICATIONS[idx % len(BANKING_APPLICATIONS)]
        conn = _pick(CONNECTORS_BY_FRAMEWORK.get(fw, ["SharePoint"]), f"ev-{idx}")
        s = _seed(f"integ-{idx}")
        health = ["Healthy", "Partial", "Failed"][s % 3]
        events.append({
            "timestamp": f"2026-05-{(s % 20) + 1:02d} {(s % 12) + 6:02d}:{s % 60:02d} UTC",
            "framework": fw,
            "application": app,
            "owner": owner_for(app),
            "risk": ["Low", "Medium", "High"][s % 3],
            "status": health,
            "health": health,
            "connector": conn,
            "issue": "—" if health == "Healthy" else f"{conn} sync issue on {app}",
            "impact": "No impact" if health == "Healthy" else f"{fw} evidence delayed",
            "sync_status": "Healthy" if health == "Healthy" else ("Retry Pending" if health == "Failed" else "Partial"),
            "purpose": FRAMEWORK_EVIDENCE[fw][0],
            "evidence_type": FRAMEWORK_EVIDENCE[fw][0],
            "recommended_action": "Monitor" if health == "Healthy" else "Investigate sync",
            "level": "Info" if health == "Healthy" else "Warning",
            "message": f"{conn} — {app}",
            "outcome": health,
        })
        idx += 1
    return events


def generate_scheduler_failures(jobs: list[dict]) -> list[dict]:
    failures = []
    for j in jobs:
        if j["status"] not in ("Failed", "Partial", "Delayed"):
            continue
        failures.append({
            "failure_id": f"FAIL-{j['job_id'][-4:]}",
            "source": j["source_system"],
            "type": j["framework"],
            "description": f"{j['name']} — {j['failed_collections']} collection(s) failed",
            "severity": "High" if j["risk"] in ("Critical", "High") else "Medium",
            "impact": f"{j['application']} evidence gap",
            "affected_applications": j["application"],
            "remediation": f"Retry {j['source_system']} connector for {j['framework']}",
            "retry_status": j.get("retry_status", "Pending retry"),
            "framework": j["framework"],
            "application": j["application"],
            "owner": j["owner"],
            "risk": j["risk"],
            "status": j["status"],
        })
    return failures


def build_operations_dataset(module: str, role: str = "owner") -> dict:
    from app.role_filter_scope import apply_role_scope

    def _scope(records: dict) -> dict:
        scoped = {}
        for key, rows in records.items():
            if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                scoped[key] = apply_role_scope(rows, role)
            else:
                scoped[key] = rows
        return scoped

    if module == "scheduler":
        jobs = generate_scheduler_jobs(150)
        for j in jobs:
            j.setdefault("records", j.get("evidence_collected", 0))
        scans = generate_application_scans(120)
        cron = generate_cron_runs(40)
        failures = generate_scheduler_failures(jobs)
        return {
            "module": "scheduler",
            "role": role,
            "records": _scope({
                "jobs": jobs,
                "application_scans": scans,
                "cron_runs": cron,
                "failures": failures,
            }),
        }
    if module == "upload":
        from app.enterprise_mock_service import session_upload_records

        uploads = generate_upload_records(120)
        session = session_upload_records()
        uploads = session + uploads
        batches = generate_upload_batches(uploads)
        if session:
            batches = generate_upload_batches(session) + [b for b in batches if b["batch_id"] not in {s["batch_id"] for s in session}]
        return {
            "module": "upload",
            "role": role,
            "records": _scope({"uploads": uploads, "batches": batches}),
        }
    if module == "onboarding":
        records = generate_onboarding_records(80)
        return {"module": "onboarding", "role": role, "records": _scope({"applications": records, "pipeline": records})}
    if module == "integrations":
        events = generate_integration_events(120)
        from app.integration_health_engine import build_integration_health_rows
        health = build_integration_health_rows()
        return {"module": "integrations", "role": role, "records": _scope({"health_rows": health, "events": events})}
    return {"module": module, "records": {}}
