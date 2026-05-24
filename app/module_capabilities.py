"""Specialized business views for each ECS MVP module (not generic workflow queues)."""

from __future__ import annotations

from datetime import datetime, timezone

from app import ecs_state
from app.analytics_module import (
    application_comparison,
    audit_preparation_checklist,
    completeness_report,
    compliance_trends,
    enterprise_dashboard,
    lifecycle_timeline,
)
from app.demo_metrics import REUSE_METRICS, onboarding_progress, BUSINESS_UNITS
from app.evidence_repository import evidence_repository, get_health_dashboard, get_reuse_graph, upload_tracker
from app.framework_catalog import FRAMEWORK_CATALOG, get_all_evidence_records
from app.integrations_module import get_integration_dashboard
from app.reporting_module import list_reports
from app.scheduler_module import get_scheduler_dashboard
from app.search_module import build_search_discovery
from app.workflow_module import aging_days_from

MODULE_PURPOSES = {
    "scheduler": "Automated evidence collection scheduling across SharePoint, ServiceNow, SIEM, and CMDB source systems.",
    "upload": "Mass onboarding and batch import of evidence artefacts with validation, deduplication, and framework auto-mapping.",
    "evidence_health": "Risk and quality scoring — stale, expired, incomplete, and low-confidence evidence governance.",
    "search": "Enterprise evidence discovery with semantic filters, reuse mapping, and cross-framework search.",
    "completeness": "Coverage gap analysis — controls without evidence, partial compliance, and audit readiness.",
    "reuse": "Cross-framework evidence reuse engine — map once, satisfy multiple controls, reduce duplicate uploads.",
    "lifecycle": "Evidence lifecycle governance — draft through active, expiring, archived, and retired states.",
    "comparison": "Application compliance posture comparison — maturity variance, control gaps, and risk heatmaps.",
    "integrations": "External system connectors — SIEM, ticketing, GRC, and ingestion pipeline health.",
    "enterprise": "Organization-wide governance KPIs, framework maturity, business-unit risk, and compliance posture.",
    "pan_india": "Regional and branch-level compliance visibility with zone risk and SLA breach tracking.",
    "reports": "Audit-ready export center — regulator packs, scheduled reports, and export history.",
    "audit_prep": "Audit readiness cockpit — upcoming audits, missing controls, and mock-audit preparation.",
    "trends": "Historical compliance analytics — maturity, closure, rejection, SLA, and evidence aging trends.",
    "onboarding": "Application onboarding workflow — framework assignment, ownership, and registration stages.",
    "risk_register": "Enterprise risk governance — inherent/residual risk, treatment, regulatory impact, and risk aging.",
    "exceptions_td": "Technical debt and exception workflow — compensating controls, TD expiry, renewal, and approval.",
    "cmdb": "CMDB and asset inventory — applications, servers, cloud assets, ownership, and compliance mapping.",
    "regulatory_mapping": "Cross-framework regulatory normalization — shared controls, evidence reuse, and coverage matrix.",
    "executive_heatmaps": "CIO/MD executive visibility — framework, application, BU, regional, and SLA heatmaps.",
    "integrations_hub": "Enterprise integration orchestration — ServiceNow, Jira, Prisma, Tripwire, SonarQube, and more.",
    "correlation": "Cross-tool governance correlation — incident-to-remediation-to-control failure chains.",
    "governance_analytics": "AI-driven governance analytics — risk trends, exceptions, maturity, SLA, and repeat failures.",
}


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def get_module_capability(module: str, role: str = "owner") -> dict:
    builders = {
        "scheduler": _scheduler_view,
        "upload": _upload_view,
        "evidence_health": _health_view,
        "search": _search_view,
        "completeness": _completeness_view,
        "reuse": _reuse_view,
        "lifecycle": _lifecycle_view,
        "comparison": _comparison_view,
        "integrations": _integrations_view,
        "enterprise": _enterprise_view,
        "pan_india": _pan_india_view,
        "reports": _reports_view,
        "audit_prep": _audit_prep_view,
        "trends": _trends_view,
        "onboarding": _onboarding_view,
        "risk_register": _risk_register_view,
        "exceptions_td": _exceptions_view,
        "cmdb": _cmdb_view,
        "regulatory_mapping": _regulatory_view,
        "executive_heatmaps": _heatmaps_view,
        "integrations_hub": _integrations_hub_view,
        "correlation": _correlation_view,
        "governance_analytics": _governance_analytics_view,
    }
    fn = builders.get(module)
    if not fn:
        return {"purpose": "", "kpis": [], "rows": [], "role": role}
    view = fn(role)
    view["purpose"] = MODULE_PURPOSES.get(module, "")
    view["module"] = module
    view["role"] = role
    return view


def _scheduler_view(role: str) -> dict:
    dash = get_scheduler_dashboard()
    jobs = []
    for i, job in enumerate(dash["status"]["jobs"]):
        health = "Healthy" if job["status"] == "Synced" else "Attention"
        jobs.append({
            **job,
            "job_id": f"SCH-JOB-{i+1:03d}",
            "next_run": "2026-05-24 14:00 UTC" if job["status"] == "Synced" else "2026-05-24 08:00 UTC",
            "frequency": "Every 6 hours",
            "health": health,
            "failed_collections": 0 if job["status"] == "Synced" else 2,
            "retry_status": "—" if job["status"] == "Synced" else "Pending retry",
            "source_system": job["source"],
            "paused": False,
        })
    failed = [j for j in jobs if j["health"] != "Healthy"]
    healthy_pct = round((len(jobs) - len(failed)) / max(len(jobs), 1) * 100, 1)
    return {
        "kpis": [
            {"label": "Jobs Running", "value": len([j for j in jobs if not j.get("paused")]), "tone": "primary"},
            {"label": "Jobs Failed", "value": len(failed), "tone": "danger"},
            {"label": "Auto-Collected", "value": dash["status"]["records_last_pull"], "tone": "success"},
            {"label": "Scheduler Uptime", "value": f"{dash['status']['success_rate_pct']}%", "tone": "info"},
        ],
        "scheduler_health": {"status": "Operational" if healthy_pct >= 90 else "Degraded", "uptime_pct": dash["status"]["success_rate_pct"], "healthy_jobs": len(jobs) - len(failed), "total_jobs": len(jobs)},
        "rows": jobs,
        "failed_jobs": failed,
        "execution_history": dash["execution_history"][:8],
        "actions": _actions_for(role, scheduler=True),
    }


def _upload_view(role: str) -> dict:
    batches = {}
    for u in upload_tracker:
        batch_id = u.get("batch_id", "BATCH-001")
        batches.setdefault(batch_id, {"batch_id": batch_id, "files": [], "status": "Parsing", "errors": 0, "duplicates": 0})
        batches[batch_id]["files"].append(u)
    if not batches:
        batches["BATCH-DEMO-001"] = {
            "batch_id": "BATCH-DEMO-001",
            "uploaded_at": "2026-05-23 18:30 UTC",
            "file_count": 12,
            "status": "Validated",
            "framework_mapping": "PCI DSS, DPSC",
            "parsing_status": "Complete",
            "duplicate_count": 1,
            "error_count": 0,
            "uploaded_by": "R. Mehta (App Owner)",
        }
        batches["BATCH-DEMO-002"] = {
            "batch_id": "BATCH-DEMO-002",
            "uploaded_at": "2026-05-24 09:15 UTC",
            "file_count": 8,
            "status": "Pending Validation",
            "framework_mapping": "Auto-detect in progress",
            "parsing_status": "In Progress",
            "duplicate_count": 0,
            "error_count": 2,
            "uploaded_by": "A. Sharma (App Owner)",
        }
    batch_list = list(batches.values()) if batches else []
    if batch_list and "file_count" not in batch_list[0]:
        batch_list = [
            {
                "batch_id": "BATCH-DEMO-001",
                "uploaded_at": "2026-05-23 18:30 UTC",
                "file_count": len(evidence_repository) or 12,
                "status": "Validated",
                "framework_mapping": "PCI DSS, OS Baselining",
                "parsing_status": "Complete",
                "duplicate_count": 1,
                "error_count": 0,
                "uploaded_by": "R. Mehta (App Owner)",
                "progress_pct": 100,
            }
        ]
    for b in batch_list:
        if "progress_pct" not in b:
            b["progress_pct"] = 100 if b.get("status") == "Validated" else (65 if b.get("parsing_status") == "In Progress" else 85)
    return {
        "kpis": [
            {"label": "Active Batches", "value": len(batch_list), "tone": "primary"},
            {"label": "Files Ingested", "value": sum(b.get("file_count", 0) for b in batch_list), "tone": "success"},
            {"label": "Duplicates Flagged", "value": sum(b.get("duplicate_count", 0) for b in batch_list), "tone": "warning"},
            {"label": "Ingestion Errors", "value": sum(b.get("error_count", 0) for b in batch_list), "tone": "danger"},
        ],
        "rows": batch_list,
        "recent_uploads": list(reversed(evidence_repository[-10:])),
        "actions": _actions_for(role, upload=True),
    }


def _health_view(role: str) -> dict:
    health = get_health_dashboard()
    all_ev = get_all_evidence_records()
    rows = []
    for ev in all_ev:
        risk = "Low"
        issue = "Current"
        if ev.get("evidence_status") == "Expired":
            risk, issue = "Critical", "Expired"
        elif ev.get("evidence_status") == "Due for Refresh":
            risk, issue = "High", "Expiring Soon"
        elif ev.get("audit_status") in ("Pending", "Rejected"):
            risk, issue = "Medium", "Incomplete Metadata"
        elif not ev.get("comments"):
            risk, issue = "Medium", "Low Confidence"
        aging = aging_days_from(ev.get("upload_timestamp", ""), 10)
        if aging > 60 and risk == "Low":
            risk, issue = "Medium", "Stale"
        rows.append({
            "evidence_id": ev.get("evidence_id"),
            "evidence_name": ev.get("evidence_name"),
            "framework": ev.get("framework"),
            "application": ev.get("application_name"),
            "risk": risk,
            "issue": issue,
            "health_score": 95 if risk == "Low" else (72 if risk == "Medium" else (55 if risk == "High" else 30)),
            "expiry_date": ev.get("expiry_date"),
            "missing_metadata": not ev.get("reviewer"),
        })
    rows.sort(key=lambda x: {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}[x["risk"]])
    expired = sum(1 for r in rows if r["issue"] == "Expired")
    stale = sum(1 for r in rows if r["issue"] == "Stale")
    expiring = sum(1 for r in rows if r["issue"] == "Expiring Soon")
    incomplete = sum(1 for r in rows if r["issue"] == "Incomplete Metadata")
    risky = sum(1 for r in rows if r["risk"] in ("Critical", "High"))
    avg_score = round(sum(r["health_score"] for r in rows[:50]) / max(len(rows[:50]), 1), 1)
    return {
        "kpis": [
            {"label": "Health Score", "value": f"{avg_score}%", "tone": "success"},
            {"label": "Critical / High Risk", "value": risky, "tone": "danger"},
            {"label": "Stale Evidence", "value": stale, "tone": "warning"},
            {"label": "Expiring This Month", "value": expiring, "tone": "info"},
        ],
        "risk_distribution": [
            {"label": "Critical", "count": sum(1 for r in rows if r["risk"] == "Critical"), "class": "risk-critical"},
            {"label": "High", "count": sum(1 for r in rows if r["risk"] == "High"), "class": "risk-high"},
            {"label": "Medium", "count": sum(1 for r in rows if r["risk"] == "Medium"), "class": "risk-medium"},
            {"label": "Low", "count": sum(1 for r in rows if r["risk"] == "Low"), "class": "risk-low"},
        ],
        "categories": {
            "stale": [r for r in rows if r["issue"] == "Stale"][:8],
            "expired": [r for r in rows if r["issue"] == "Expired"][:8],
            "incomplete": [r for r in rows if r["issue"] == "Incomplete Metadata"][:8],
            "risky": [r for r in rows if r["risk"] in ("Critical", "High")][:8],
        },
        "rows": rows[:30],
        "integrity": health,
        "actions": _actions_for(role, health=True),
    }


def _search_view(role: str) -> dict:
    discovery = build_search_discovery()
    return {
        "kpis": [
            {"label": "Indexed Artefacts", "value": discovery["total_indexed"], "tone": "primary"},
            {"label": "Frameworks Mapped", "value": len(FRAMEWORK_CATALOG), "tone": "info"},
            {"label": "Reuse Suggestions", "value": len(discovery["reuse_suggestions"]), "tone": "success"},
            {"label": "Semantic Matches", "value": len(discovery["semantic_matches"]), "tone": "secondary"},
        ],
        "rows": [],
        "discovery": discovery,
        "framework_filters": discovery["framework_filters"],
        "actions": _actions_for(role, search=True),
    }


def _completeness_view(role: str) -> dict:
    comp = completeness_report()
    stats = ecs_state.build_evidence_analytics()
    fw_rows = []
    for fw in stats["framework_stats"]:
        pct = round((fw["approved"] / fw["total"]) * 100, 1) if fw["total"] else 0
        fw_rows.append({
            "framework": fw["name"],
            "completeness_pct": pct,
            "approved": fw["approved"],
            "total": fw["total"],
            "gaps": fw["pending"] + fw["rejected"],
        })
    app_rows = application_comparison()
    audit_readiness = round(100 - (comp["missing_count"] / max(sum(fw["total"] for fw in stats["framework_stats"]), 1) * 100), 1)
    return {
        "kpis": [
            {"label": "Framework Completeness", "value": f"{round(sum(r['completeness_pct'] for r in fw_rows)/len(fw_rows),1)}%", "tone": "primary"},
            {"label": "Missing Controls", "value": comp["missing_count"], "tone": "danger"},
            {"label": "Audit Readiness", "value": f"{audit_readiness}%", "tone": "success"},
            {"label": "Incomplete Apps", "value": len([a for a in app_rows if a["compliance_pct"] < 80]), "tone": "warning"},
        ],
        "rows": comp["missing"][:20],
        "incomplete": comp["incomplete"][:15],
        "framework_rows": fw_rows,
        "application_rows": app_rows,
        "actions": _actions_for(role, completeness=True),
    }


def _reuse_view(role: str) -> dict:
    reuse = get_reuse_graph()
    candidates = []
    for g in reuse.get("groups", []):
        candidates.append({
            "group_id": g["group_id"],
            "filename": g["filename"],
            "frameworks_mapped": len({l["framework"] for l in g["linked_controls"]}),
            "controls_linked": len(g["linked_controls"]),
            "duplicate_avoided": len(g["linked_controls"]) - 1,
            "status": "Approved" if len(g["linked_controls"]) > 2 else "Candidate",
            "linked_controls": g["linked_controls"],
        })
    return {
        "kpis": [
            {"label": "Reuse %", "value": "34.5%", "tone": "success"},
            {"label": "Reuse Groups", "value": REUSE_METRICS["total_reuse_groups"], "tone": "primary"},
            {"label": "Duplicates Avoided", "value": sum(c["duplicate_avoided"] for c in candidates), "tone": "info"},
            {"label": "Hours Saved", "value": REUSE_METRICS["top_saving_hours"], "tone": "secondary"},
        ],
        "rows": candidates,
        "actions": _actions_for(role, reuse=True),
    }


def _lifecycle_view(role: str) -> dict:
    timeline = lifecycle_timeline()
    buckets = {"Draft": [], "Active": [], "Expiring": [], "Archived": [], "Retired": []}
    for ev in get_all_evidence_records():
        st = ev.get("evidence_status", "Current")
        if st == "Expired":
            bucket = "Retired"
        elif st == "Due for Refresh":
            bucket = "Expiring"
        elif ev.get("audit_status") == "Approved":
            bucket = "Active"
        elif ev.get("audit_status") in ("Pending", "Submitted"):
            bucket = "Draft"
        else:
            bucket = "Active"
        buckets[bucket].append({
            "evidence_id": ev.get("evidence_id"),
            "name": ev.get("evidence_name"),
            "framework": ev.get("framework"),
            "upload_date": ev.get("upload_timestamp", "")[:10],
            "expiry_date": ev.get("expiry_date"),
            "state": bucket,
        })
    rows = []
    for state, items in buckets.items():
        for item in items[:8]:
            item["lifecycle_state"] = state
            rows.append(item)
    timeline_events = []
    for ev in rows[:6]:
        timeline_events.append({
            "evidence_id": ev.get("evidence_id"),
            "name": ev.get("name"),
            "upload_date": ev.get("upload_date"),
            "expiry_date": ev.get("expiry_date"),
            "state": ev.get("lifecycle_state"),
            "event": f"State: {ev.get('lifecycle_state')}",
        })
    return {
        "kpis": [
            {"label": "Active", "value": len(buckets["Active"]), "tone": "success"},
            {"label": "Expiring", "value": len(buckets["Expiring"]), "tone": "warning"},
            {"label": "Draft", "value": len(buckets["Draft"]), "tone": "info"},
            {"label": "Retired", "value": len(buckets["Retired"]), "tone": "secondary"},
        ],
        "rows": rows[:25],
        "timeline": timeline[:10],
        "timeline_events": timeline_events,
        "buckets": {k: len(v) for k, v in buckets.items()},
        "bucket_items": buckets,
        "actions": _actions_for(role, lifecycle=True),
    }


def _comparison_view(role: str) -> dict:
    apps = application_comparison()
    rows = []
    for i, a in enumerate(apps):
        for j, b in enumerate(apps):
            if i < j:
                variance = abs(a["compliance_pct"] - b["compliance_pct"])
                if variance >= 5:
                    rows.append({
                        "app_a": a["application"],
                        "app_b": b["application"],
                        "maturity_a": a["compliance_pct"],
                        "maturity_b": b["compliance_pct"],
                        "variance": round(variance, 1),
                        "risk": "High" if variance > 12 else "Medium",
                    })
    heatmap = []
    for a in apps:
        for fw, fw_data in a.get("frameworks", {}).items():
            pct = round((fw_data["approved"] / fw_data["total"]) * 100, 0) if fw_data["total"] else 0
            heatmap.append({"application": a["application"], "framework": fw, "pct": int(pct)})
    return {
        "kpis": [
            {"label": "Applications", "value": len(apps), "tone": "primary"},
            {"label": "High Variance Pairs", "value": len([r for r in rows if r["risk"] == "High"]), "tone": "danger"},
            {"label": "Avg Maturity", "value": f"{round(sum(a['compliance_pct'] for a in apps)/len(apps),1)}%", "tone": "success"},
            {"label": "Elevated Risk Apps", "value": len([a for a in apps if a.get("risk") in ("High", "Critical", "Elevated")]), "tone": "warning"},
        ],
        "rows": apps,
        "variance_rows": rows[:12],
        "heatmap": heatmap[:24],
        "actions": _actions_for(role, comparison=True),
    }


def _integrations_view(role: str) -> dict:
    dash = get_integration_dashboard()
    rows = []
    for c in dash["connectors"]:
        rows.append({
            **c,
            "pipeline": c.get("name", "Connector"),
            "last_sync": c.get("last_sync", "2026-05-24 06:00 UTC"),
            "records_ingested": c.get("records", 128),
            "api_health": "Healthy" if c.get("api_status", c["status"]) in ("Healthy", "Connected", "Synced") else "Degraded",
            "sync_status": c.get("sync_status", c["status"]),
        })
    return {
        "kpis": [
            {"label": "Connectors", "value": len(rows), "tone": "primary"},
            {"label": "Healthy APIs", "value": len([r for r in rows if r["api_health"] == "Healthy"]), "tone": "success"},
            {"label": "Degraded", "value": len([r for r in rows if r["api_health"] != "Healthy"]), "tone": "danger"},
            {"label": "Records Ingested", "value": sum(r.get("records_ingested", 0) for r in rows), "tone": "info"},
        ],
        "rows": rows,
        "grouped": dash.get("grouped", {}),
        "actions": _actions_for(role, integrations=True),
    }


def _enterprise_view(role: str) -> dict:
    ent = enterprise_dashboard()
    stats = ecs_state.build_evidence_analytics()
    rows = []
    for fw in stats["framework_stats"]:
        rows.append({
            "framework": fw["name"],
            "maturity_pct": fw["compliance_pct"],
            "approved": fw["approved"],
            "total": fw["total"],
            "risk": "High" if fw["compliance_pct"] < 70 else ("Medium" if fw["compliance_pct"] < 85 else "Low"),
            "open_items": fw["pending"] + fw["submitted"] + fw["rejected"],
        })
    return {
        "kpis": [
            {"label": "Enterprise Compliance", "value": f"{ent['kpis']['enterprise_compliance_pct']}%", "tone": "success"},
            {"label": "National Score", "value": f"{ent['national_score']}%", "tone": "primary"},
            {"label": "Open Observations", "value": ent["kpis"]["open_observations"], "tone": "warning"},
            {"label": "Frameworks at Risk", "value": len([r for r in rows if r["risk"] == "High"]), "tone": "danger"},
        ],
        "rows": rows,
        "business_units": BUSINESS_UNITS,
        "enterprise": ent,
        "maturity_heatmap": [{"framework": r["framework"], "pct": r["maturity_pct"]} for r in rows],
        "actions": _actions_for(role, enterprise=True),
    }


def _pan_india_view(role: str) -> dict:
    rows = []
    for r in ecs_state.PAN_INDIA_REGIONS:
        rows.append({
            **r,
            "zone": r["region"],
            "sla_breaches": max(1, r["observations_open"] // 8),
            "compliance_pct": r["score"],
            "risk_level": "High" if r["score"] < 85 else "Medium" if r["score"] < 90 else "Low",
        })
    return {
        "kpis": [
            {"label": "Regions", "value": len(rows), "tone": "primary"},
            {"label": "Branches", "value": sum(r["branches"] for r in rows), "tone": "info"},
            {"label": "Open Observations", "value": sum(r["observations_open"] for r in rows), "tone": "warning"},
            {"label": "SLA Breaches", "value": sum(r["sla_breaches"] for r in rows), "tone": "danger"},
        ],
        "rows": rows,
        "zone_heatmap": [{"zone": r["zone"], "score": r["compliance_pct"], "risk": r["risk_level"]} for r in rows],
        "actions": _actions_for(role, pan_india=True),
    }


def _reports_view(role: str) -> dict:
    reports = list_reports()
    rows = []
    for r in reports:
        rows.append({
            **r,
            "generated_at": r.get("generated_at", "2026-05-20 14:00 UTC"),
            "format": r.get("format", "PDF"),
            "schedule": r.get("schedule", "On-demand"),
        })
    return {
        "kpis": [
            {"label": "Available Reports", "value": len(rows), "tone": "primary"},
            {"label": "Generated", "value": len([r for r in rows if r.get("status") == "Generated"]), "tone": "success"},
            {"label": "Scheduled", "value": len([r for r in rows if r.get("schedule") != "On-demand"]), "tone": "info"},
            {"label": "Pending", "value": len([r for r in rows if r.get("status") != "Generated"]), "tone": "warning"},
        ],
        "rows": rows,
        "actions": _actions_for(role, reports=True),
    }


def _audit_prep_view(role: str) -> dict:
    prep = audit_preparation_checklist()
    rows = prep.get("checklist", [])[:20]
    return {
        "kpis": [
            {"label": "Readiness Score", "value": f"{prep['ready_pct']}%", "tone": "success"},
            {"label": "Missing Controls", "value": prep["missing_controls"], "tone": "danger"},
            {"label": "Upcoming Audits", "value": len(prep.get("upcoming_audits", [])), "tone": "primary"},
            {"label": "Auditor Requests", "value": len(prep.get("pending_auditor_requests", [])), "tone": "warning"},
        ],
        "rows": rows,
        "upcoming_audits": prep.get("upcoming_audits", []),
        "pending_auditor_requests": prep.get("pending_auditor_requests", []),
        "actions": _actions_for(role, audit_prep=True),
    }


def _trends_view(role: str) -> dict:
    trends = compliance_trends()
    monthly = trends.get("monthly", [])
    return {
        "kpis": [
            {"label": "Avg Closure Days", "value": trends.get("avg_days_to_close", 18), "tone": "primary"},
            {"label": "Latest Compliance", "value": f"{monthly[-1].get('compliance', 79)}%" if monthly else "—", "tone": "success"},
            {"label": "Rejection Rate", "value": f"{trends.get('rejection_trends', [{}])[-1].get('rate_pct', 4.2)}%", "tone": "warning"},
            {"label": "SLA On-Time", "value": f"{trends.get('sla_trends', [{}])[-1].get('on_time_pct', 91)}%", "tone": "info"},
        ],
        "rows": monthly,
        "trends": trends,
        "rejection_trends": trends.get("rejection_trends", []),
        "sla_trends": trends.get("sla_trends", []),
        "aging_buckets": trends.get("aging_buckets", []),
        "actions": _actions_for(role, trends=True),
    }


def _onboarding_view(role: str) -> dict:
    progress = onboarding_progress()
    rows = []
    for i, p in enumerate(progress):
        rows.append({
            **p,
            "stage": "Registration Complete" if p["progress_pct"] >= 90 else ("Framework Mapping" if p["progress_pct"] >= 70 else "Initial Setup"),
            "owner": ecs_state.BANKING_APPLICATIONS[i % len(ecs_state.BANKING_APPLICATIONS)] if i < len(ecs_state.BANKING_APPLICATIONS) else "TBD",
            "pending_tasks": max(0, 5 - p["frameworks_mapped"]),
        })
    return {
        "kpis": [
            {"label": "Applications", "value": len(rows), "tone": "primary"},
            {"label": "Production Ready", "value": len([r for r in rows if r["status"] == "Production"]), "tone": "success"},
            {"label": "In Progress", "value": len([r for r in rows if r["status"] != "Production"]), "tone": "warning"},
            {"label": "Pending Tasks", "value": sum(r["pending_tasks"] for r in rows), "tone": "info"},
        ],
        "rows": rows,
        "stages": ["Initial Setup", "Framework Mapping", "Owner Assignment", "Registration Complete"],
        "actions": _actions_for(role, onboarding=True),
    }


def _risk_register_view(role: str) -> dict:
    from app.enterprise_grc import build_risk_register
    data = build_risk_register(role)
    return {**data, "actions": _actions_for(role, risk=True)}


def _exceptions_view(role: str) -> dict:
    from app.enterprise_grc import build_exceptions_td
    data = build_exceptions_td(role)
    return {**data, "actions": _actions_for(role, exception=True)}


def _cmdb_view(role: str) -> dict:
    from app.enterprise_grc import build_cmdb_inventory
    data = build_cmdb_inventory(role)
    return {**data, "actions": _actions_for(role, cmdb=True)}


def _regulatory_view(role: str) -> dict:
    from app.enterprise_grc import build_regulatory_mapping
    data = build_regulatory_mapping(role)
    return {**data, "rows": data["mappings"], "actions": _actions_for(role, regulatory=True)}


def _heatmaps_view(role: str) -> dict:
    from app.enterprise_grc import build_executive_heatmaps
    return build_executive_heatmaps(role)


def _integrations_hub_view(role: str) -> dict:
    from app.integrations_module import get_integrations_hub_dashboard
    dash = get_integrations_hub_dashboard()
    rows = [{**c, "records_ingested": c.get("records_pulled", c.get("records", 0))} for c in dash["connectors"]]
    return {**dash, "rows": rows, "grouped": dash["grouped"], "actions": _actions_for(role, hub=True)}


def _correlation_view(role: str) -> dict:
    from app.correlation_engine import build_correlation_dashboard
    return build_correlation_dashboard(role)


def _governance_analytics_view(role: str) -> dict:
    from app.enterprise_grc import build_governance_analytics_module
    return build_governance_analytics_module(role)


def _actions_for(role: str, **flags) -> list[str]:
    """Return action keys allowed for role on this module type."""
    if flags.get("scheduler"):
        return ["run_now", "pause", "resume", "retry", "change_frequency"] if role in ("owner", "auditor", "cio", "compliance_head") else ["run_now"]
    if flags.get("upload"):
        return ["upload_batch", "validate", "reprocess", "approve_import", "reject_import"] if role == "owner" else ["validate", "approve_import", "reject_import"]
    if flags.get("health"):
        return ["replace", "extend", "escalate_risk", "request_upload"] if role == "owner" else ["escalate_risk", "request_upload"]
    if flags.get("search"):
        return ["open", "map_framework", "reuse", "compare"]
    if flags.get("completeness"):
        return ["assign_gap", "upload_missing", "request_owner"] if role in ("owner", "compliance_head") else ["assign_gap", "request_owner"]
    if flags.get("reuse"):
        return ["reuse_across", "link", "approve_reuse", "reject_reuse"]
    if flags.get("lifecycle"):
        return ["renew", "archive", "retire", "extend_retention"] if role == "owner" else ["archive", "extend_retention"]
    if flags.get("comparison"):
        return ["compare", "export_gap", "variance_report"]
    if flags.get("integrations"):
        return ["test_connection", "sync_now", "reconnect", "view_logs"]
    if flags.get("enterprise"):
        return ["drill_down", "view_gaps", "escalate_risk"] if role in ("cio", "vertical_head", "compliance_head") else ["drill_down"]
    if flags.get("pan_india"):
        return ["open_region", "escalate_zone", "export_regional"]
    if flags.get("reports"):
        return ["generate", "export_pdf", "export_excel", "schedule"]
    if flags.get("audit_prep"):
        return ["close_gap", "upload_missing", "assign_owner", "mock_audit"]
    if flags.get("trends"):
        return ["export_chart", "drill_down"]
    if flags.get("onboarding"):
        return ["start", "assign_framework", "assign_owner", "complete_registration"]
    if flags.get("risk"):
        return ["accept_risk", "escalate_risk", "mitigate_risk", "assign_owner", "request_exception", "link_control"]
    if flags.get("exception"):
        return ["approve_exception", "reject_exception", "extend_td", "escalate_expired_td", "renew_exception"]
    if flags.get("cmdb"):
        return ["open_asset", "view_controls", "view_risks", "view_evidence"]
    if flags.get("regulatory"):
        return ["reuse_evidence", "link_control", "map_framework", "export_mapping"]
    if flags.get("heatmaps"):
        return ["drill_down", "escalate_risk", "view_exception", "approve_closure"]
    if flags.get("hub"):
        return ["sync_now", "test_connection", "view_logs", "retry_failed_sync"]
    if flags.get("correlation"):
        return ["view_chain", "escalate", "link_control"]
    if flags.get("gov_analytics"):
        return ["export_chart", "drill_down", "view_trends"]
    return []


def module_counter_rows(module: str, role: str) -> int:
    """Live row count for nav badge — derived from module capability, not workflow queue."""
    view = get_module_capability(module, role)
    rows = view.get("rows", [])
    if module == "completeness":
        return len(rows) + len(view.get("incomplete", []))
    if module == "comparison":
        return len(view.get("variance_rows", [])) + len([r for r in rows if r.get("risk") in ("High", "Critical", "Elevated")])
    if module == "search":
        return len(get_all_evidence_records())
    if module == "risk_register":
        return len([r for r in view.get("rows", []) if r.get("status") in ("Open", "Escalated")])
    if module == "exceptions_td":
        return len(view.get("expired", [])) + len([r for r in view.get("rows", []) if r.get("residual_risk") in ("Critical", "High")])
    if module == "cmdb":
        return len([r for r in view.get("rows", []) if r.get("risk_rating") in ("Critical", "High") or not r.get("monitoring_enabled")])
    if module == "integrations_hub":
        return sum(1 for r in view.get("rows", []) if r.get("sync_health") != "Healthy" or r.get("failed_syncs", 0) > 0)
    if module == "correlation":
        return len([c for c in view.get("chains", []) if c.get("status") == "Open"])
    return len(rows)
