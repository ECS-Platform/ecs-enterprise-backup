"""Realistic enterprise banking demo metrics (blended with live workflow state)."""

from app import ecs_state
from modules.frameworks.engines.framework_catalog import catalog_stats, get_all_evidence_records

_CAT = catalog_stats()

# Display maturity when live counts are still ramping (leadership demo baseline)
FRAMEWORK_MATURITY_BASELINE = {
    "PCI DSS": 78.5,
    "DPSC": 71.2,
    "OS Baselining": 82.4,
    "DB Baselining": 76.8,
    "Nginx Baselining": 84.1,
    "AppSec": 73.8,
    "VAPT": 77.2,
    "CSITE": 69.5,
    "ITPP": 74.3,
}

APPLICATION_COMPLIANCE_BASELINE = {
    "Net Banking": 81.3,
    "Mobile Banking": 74.6,
    "UPI": 77.9,
    "Payments": 79.2,
    "Treasury": 88.5,
    "Loan System": 72.1,
}

ENTERPRISE_MONTHLY_TRENDS = [
    {"month": "Nov 2025", "closed": 38, "opened": 22, "compliance": 71.2},
    {"month": "Dec 2025", "closed": 45, "opened": 19, "compliance": 74.8},
    {"month": "Jan 2026", "closed": 52, "opened": 24, "compliance": 76.5},
    {"month": "Feb 2026", "closed": 48, "opened": 18, "compliance": 78.1},
    {"month": "Mar 2026", "closed": 56, "opened": 15, "compliance": 79.4},
]

AUDIT_AGING_BUCKETS = [
    {"label": "0-30 days", "count": 94, "pct": 42},
    {"label": "31-60 days", "count": 67, "pct": 30},
    {"label": "61-90 days", "count": 38, "pct": 17},
    {"label": "90+ days (stale)", "count": 24, "pct": 11},
]

REJECTION_TRENDS = [
    {"month": "Nov 2025", "rejections": 14, "rate_pct": 8.2},
    {"month": "Dec 2025", "rejections": 11, "rate_pct": 6.8},
    {"month": "Jan 2026", "rejections": 9, "rate_pct": 5.4},
    {"month": "Feb 2026", "rejections": 12, "rate_pct": 6.1},
    {"month": "Mar 2026", "rejections": 7, "rate_pct": 4.2},
]

SLA_TRENDS = [
    {"month": "Nov 2025", "on_time_pct": 82, "breaches": 18},
    {"month": "Dec 2025", "on_time_pct": 85, "breaches": 14},
    {"month": "Jan 2026", "on_time_pct": 88, "breaches": 11},
    {"month": "Feb 2026", "on_time_pct": 86, "breaches": 13},
    {"month": "Mar 2026", "on_time_pct": 91, "breaches": 8},
]

BUSINESS_UNITS = [
    {"unit": "Retail Banking", "compliance_pct": 84.2, "risk": "Low", "open_gaps": 12},
    {"unit": "Corporate Banking", "compliance_pct": 79.6, "risk": "Medium", "open_gaps": 19},
    {"unit": "Wealth Management", "compliance_pct": 88.1, "risk": "Low", "open_gaps": 7},
    {"unit": "Digital Channels", "compliance_pct": 72.4, "risk": "High", "open_gaps": 28},
    {"unit": "Operations & IT", "compliance_pct": 81.0, "risk": "Medium", "open_gaps": 15},
]

REUSE_METRICS = {
    "total_reuse_groups": 42,
    "controls_covered_by_reuse": int(_CAT["control_count"] * 0.38),
    "avg_reuse_factor": 2.8,
    "top_saving_hours": 284,
    "evidences_reused": 186,
}

SCHEDULER_METRICS = {
    "pulls_completed": 1847,
    "last_pull_at": "2026-05-24 06:00:12 UTC",
    "last_pull_status": "Success",
    "records_last_pull": 412,
    "success_rate_pct": 99.2,
    "avg_duration_sec": 42,
}

HEALTH_METRICS = {
    "total_artifacts": _CAT["evidence_count"] + 412,
    "valid_integrity_pct": 98.4,
    "tamper_alerts": 3,
    "overdue_count": 17,
    "stale_count": 24,
    "expired_count": sum(1 for r in get_all_evidence_records() if r.get("evidence_status") == "Expired"),
}


def display_framework_maturity(framework_stats: list) -> list:
    enriched = []
    for fw in framework_stats:
        live = fw["compliance_pct"]
        baseline = FRAMEWORK_MATURITY_BASELINE.get(fw["name"], 75.0)
        display = round(max(live, baseline * 0.35 + live * 0.65), 1) if live else baseline
        enriched.append({**fw, "maturity_pct": display, "live_pct": live})
    return enriched


def display_application_rows(live_rows: list) -> list:
    enriched = []
    for row in live_rows:
        baseline = APPLICATION_COMPLIANCE_BASELINE.get(row["application"], 76.0)
        display = row["compliance_pct"]
        if display < 15 and row["total"] > 0:
            display = round(baseline * 0.4 + display * 0.6, 1)
        elif display == 0:
            display = baseline
        enriched.append({**row, "compliance_pct": display, "owner": _owner_for(row["application"])})
    return enriched


def _owner_for(application: str) -> str:
    owners = {
        "Net Banking": "R. Mehta",
        "Mobile Banking": "A. Sharma",
        "UPI": "P. Iyer",
        "Payments": "K. Reddy",
        "Treasury": "S. Banerjee",
        "Loan System": "M. Joshi",
    }
    return owners.get(application, "Enterprise Owner")


def role_dashboard_metrics(role: str) -> dict:
    from modules.governance.engines.workflow_module import build_auditor_review_queue, build_owner_work_queue, work_queue_summary

    stats = ecs_state.build_evidence_analytics()
    t = stats["totals"]
    wq = work_queue_summary()
    pending_approvals = t["submitted"]
    if role == "auditor":
        auditor_q = len(build_auditor_review_queue())
        return {
            "title": "Auditor Queue",
            "show_strip": True,
            "pending_tasks": auditor_q or pending_approvals,
            "approvals_today": 14,
            "summary": "",
        }
    if role == "owner":
        owner_q = len(build_owner_work_queue())
        try:
            apps_owned = len(ecs_state.onboarded_applications)
        except Exception:
            apps_owned = 6
        return {
            "title": "Application Owner Summary",
            "summary": "",
            "show_strip": True,
            "pending_tasks": owner_q or (t["pending"] + t["rejected"]),
            "resubmits_required": t["rejected"],
            "applications_owned": apps_owned,
            "owner_open_observations": t["pending"] + t["submitted"],
            "evidence_pending": t["pending"],
            "owner_sla_breaches": 9,
            "audit_readiness_pct": 83.5,
        }
    if role in ("compliance_head", "compliance_officer"):
        return {
            "title": "Compliance Overview",
            "show_strip": True,
            "pending_tasks": pending_approvals,
            "audit_readiness_pct": 86.2,
            "summary": "",
        }
    if role == "vertical_head":
        return {
            "title": "Vertical Head Summary",
            "show_strip": True,
            "pending_tasks": pending_approvals,
            "national_score": 88.1,
            "summary": "",
        }
    if role == "cio":
        return {
            "title": "CIO Summary",
            "show_strip": True,
            "pending_tasks": pending_approvals,
            "enterprise_compliance": enterprise_kpis()["enterprise_compliance_pct"],
            "evidence_artefacts": _CAT["evidence_count"],
            "audit_completion": "91.6%",
            "summary": "",
        }
    if role == "functional_head":
        return {
            "title": "Functional Head Summary",
            "show_strip": True,
            "pending_tasks": pending_approvals,
            "audit_readiness_pct": 82.4,
            "summary": "",
        }
    # ---- Part 5: dedicated persona metric profiles (distinct KPIs per role) ----
    if role in ("security_officer", "ciso"):
        return {
            "title": "Security Posture",
            "show_strip": True,
            "pending_tasks": pending_approvals,
            "critical_vulns": 12,
            "vapt_open": 38,
            "mttr_days": 6.4,
            "security_score": 79.5,
            "summary": "",
        }
    if role in ("operations_owner", "it_operations", "it_ops"):
        return {
            "title": "Operations Control Room",
            "show_strip": True,
            "pending_tasks": pending_approvals,
            "collection_jobs_today": 142,
            "failed_jobs": 7,
            "connector_health_pct": 96.1,
            "evidence_collected_today": 1840,
            "summary": "",
        }
    if role in ("platform_operations", "platform_ops"):
        return {
            "title": "Platform Operations",
            "show_strip": True,
            "pending_tasks": pending_approvals,
            "active_connectors": 12,
            "sync_runs_today": 53,
            "platform_uptime_pct": 99.7,
            "summary": "",
        }
    if role in ("governance_lead", "governance_team", "risk_team"):
        return {
            "title": "Governance & Risk Summary",
            "show_strip": True,
            "pending_tasks": pending_approvals,
            "open_risks": 46,
            "high_critical_risks": 11,
            "exceptions_active": 28,
            "governance_score": 84.0,
            "summary": "",
        }
    if role == "framework_owner":
        return {
            "title": "Framework Owner Summary",
            "show_strip": True,
            "pending_tasks": pending_approvals,
            "frameworks_owned": 4,
            "control_coverage_pct": 81.7,
            "open_gaps": 23,
            "summary": "",
        }
    if role in ("ai_governance_owner", "ai_governance_team"):
        return {
            "title": "AI Governance Summary",
            "show_strip": True,
            "pending_tasks": pending_approvals,
            "ai_systems_governed": 18,
            "prompt_audits": 100,
            "hallucination_rate_pct": 2.1,
            "ai_risk_score": 77.4,
            "summary": "",
        }
    if role == "ai_sdlc_owner":
        return {
            "title": "AI SDLC Governance",
            "show_strip": True,
            "pending_tasks": pending_approvals,
            "applications_in_sdlc": 26,
            "stage_gates_passed": 84,
            "sast_findings_open": 31,
            "release_readiness_pct": 88.0,
            "summary": "",
        }
    return {"title": "Executive Summary", "show_strip": True, "summary": "",
            "pending_tasks": pending_approvals, "audit_readiness_pct": 85.0}


def enterprise_kpis():
    stats = ecs_state.build_evidence_analytics()
    live = stats["overall_compliance_pct"]
    display_compliance = round(max(live, 84.6), 1) if live < 50 else max(live, 84.6)
    try:
        from modules.executive_overview.engines.enterprise_mock_service import build_pan_india_posture
        regions = build_pan_india_posture()["regions"]
        national = round(sum(r["score"] for r in regions) / max(len(regions), 1), 1)
    except Exception:
        national = round(
            sum(r["score"] for r in ecs_state.PAN_INDIA_REGIONS) / len(ecs_state.PAN_INDIA_REGIONS),
            1,
        )
    return {
        "enterprise_compliance_pct": display_compliance,
        "live_compliance_pct": live,
        "national_score": national,
        "open_observations": stats["totals"]["pending"] + stats["totals"]["submitted"],
        "closed_observations": stats["totals"]["approved"],
        "rejected_observations": stats["totals"]["rejected"],
        "total_controls": stats["totals"]["total"],
        "audit_readiness_pct": 86.2,
        "reuse_pct": 34.5,
    }


def onboarding_progress():
    progress = []
    targets = {
        "Net Banking": 100,
        "Mobile Banking": 92,
        "UPI": 88,
        "Payments": 95,
        "Treasury": 78,
        "Loan System": 65,
    }
    for app in ecs_state.onboarded_applications:
        progress.append(
            {
                "application": app,
                "progress_pct": targets.get(app, 80),
                "frameworks_mapped": 4 if app != "Treasury" else 3,
                "status": "Production" if targets.get(app, 0) >= 90 else "In Progress",
            }
        )
    return progress


def overdue_and_stale_alerts():
    alerts = []
    for fw, controls in ecs_state.frameworks.items():
        for control, evidence in controls[:2]:
            st = ecs_state.control_status(fw, control)
            if st == "pending":
                alerts.append(
                    {
                        "type": "Overdue",
                        "framework": fw,
                        "control": control,
                        "evidence": evidence,
                        "aging_days": 47,
                        "owner": _owner_for(_app_name(fw, control)),
                    }
                )
    for fw, controls in list(ecs_state.frameworks.items())[2:4]:
        for control, evidence in controls[:1]:
            alerts.append(
                {
                    "type": "Stale",
                    "framework": fw,
                    "control": control,
                    "evidence": evidence,
                    "aging_days": 92,
                    "owner": _owner_for(_app_name(fw, control)),
                }
            )
    return alerts[:12]


def _app_name(framework: str, control: str) -> str:
    for item in ecs_state.PCI_DSS_MOCK_EVIDENCES:
        if item["control"] == control:
            return item["application"]
    for row in ecs_state.scheduler_data:
        if len(row) >= 2 and row[1] == framework:
            return row[0]
    return "Net Banking"
