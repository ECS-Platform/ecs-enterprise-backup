"""Realistic enterprise banking demo metrics (blended with live workflow state)."""

from app import ecs_state
from app.framework_catalog import catalog_stats, get_all_evidence_records

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
    from app.workflow_module import build_auditor_review_queue, build_owner_work_queue, work_queue_summary

    stats = ecs_state.build_evidence_analytics()
    t = stats["totals"]
    wq = work_queue_summary()
    pending_approvals = t["submitted"]
    if role == "auditor":
        auditor_q = len(build_auditor_review_queue())
        return {
            "title": "Auditor Work Queue",
            "pending_tasks": auditor_q or pending_approvals,
            "approvals_today": 14,
            "escalations": wq["escalated"] or 3,
            "observations_reviewed": t["approved"] + t["rejected"],
            "summary": f"{auditor_q or pending_approvals} submissions awaiting review across {_CAT['framework_count']} frameworks.",
        }
    if role == "owner":
        owner_q = len(build_owner_work_queue())
        return {
            "title": "App Owner Actions",
            "pending_tasks": owner_q or (t["pending"] + t["rejected"]),
            "resubmits_required": t["rejected"],
            "draft_controls": t["pending"],
            "closed_observations": t["approved"],
            "summary": f"{owner_q} items in your consolidated work queue across all frameworks.",
        }
    if role in ("compliance_head", "compliance_officer"):
        return {
            "title": "Compliance Officer Overview",
            "pending_tasks": pending_approvals,
            "open_gaps": t["pending"] + t["rejected"],
            "audit_readiness_pct": 86.2,
            "frameworks_at_risk": 2,
            "summary": "Enterprise audit readiness at 86.2% with DPSC and CSITE frameworks under watch.",
        }
    if role == "vertical_head":
        return {
            "title": "Vertical Head Summary",
            "pending_tasks": pending_approvals,
            "national_score": 88.1,
            "applications_at_risk": 2,
            "closure_velocity": "87.4%",
            "summary": "Pan-India compliance 88.1% with Mobile Banking and Loan System elevated risk.",
        }
    if role == "cio":
        return {
            "title": "CIO Executive Summary",
            "pending_tasks": pending_approvals,
            "enterprise_compliance": enterprise_kpis()["enterprise_compliance_pct"],
            "evidence_artefacts": _CAT["evidence_count"],
            "audit_completion": "91.6%",
            "summary": f"{_CAT['evidence_count']} governed artefacts across {_CAT['control_count']} controls enterprise-wide.",
        }
    return {"title": "Enterprise ECS", "summary": "Governance dashboard", "pending_tasks": 0}


def enterprise_kpis():
    stats = ecs_state.build_evidence_analytics()
    live = stats["overall_compliance_pct"]
    display_compliance = round(max(live, 84.6), 1) if live < 50 else max(live, 84.6)
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
