"""Completeness, comparison, trends, enterprise metrics."""

from app import ecs_state
from app.demo_metrics import (
    AUDIT_AGING_BUCKETS,
    BUSINESS_UNITS,
    ENTERPRISE_MONTHLY_TRENDS,
    REJECTION_TRENDS,
    SLA_TRENDS,
    display_application_rows,
    display_framework_maturity,
    enterprise_kpis,
)
from app.audit_trail import get_approval_history


def completeness_report():
    missing = []
    incomplete = []
    for fw, controls in ecs_state.frameworks.items():
        for control, evidence in controls:
            st = ecs_state.control_status(fw, control)
            entry = {
                "framework": fw,
                "control": control,
                "evidence": evidence,
                "status": st,
            }
            if st == "pending":
                missing.append(entry)
            elif st in ("submitted", "rejected"):
                incomplete.append(entry)
    return {
        "missing": missing,
        "incomplete": incomplete,
        "missing_count": len(missing),
        "incomplete_count": len(incomplete),
        "warnings": len(missing) + len(incomplete),
    }


def application_comparison():
    apps = {}
    for app in ecs_state.onboarded_applications:
        apps[app] = {"total": 0, "approved": 0, "frameworks": {}}

    for fw, controls in ecs_state.frameworks.items():
        for control, _ in controls:
            application = _app_for(fw, control)
            if application not in apps:
                apps[application] = {"total": 0, "approved": 0, "frameworks": {}}
            apps[application]["total"] += 1
            st = ecs_state.control_status(fw, control)
            if st == "approved":
                apps[application]["approved"] += 1
            fw_stats = apps[application]["frameworks"].setdefault(
                fw, {"total": 0, "approved": 0}
            )
            fw_stats["total"] += 1
            if st == "approved":
                fw_stats["approved"] += 1

    rows = []
    for app, data in apps.items():
        pct = round((data["approved"] / data["total"]) * 100, 1) if data["total"] else 0
        risk = "High" if pct < 50 else "Medium" if pct < 80 else "Low"
        rows.append(
            {
                "application": app,
                "total": data["total"],
                "approved": data["approved"],
                "compliance_pct": pct,
                "risk": risk,
                "frameworks": data["frameworks"],
            }
        )
    return display_application_rows(sorted(rows, key=lambda x: x["compliance_pct"]))


def compliance_trends():
    stats = ecs_state.build_evidence_analytics()
    live = stats["framework_stats"]
    return {
        "monthly": ENTERPRISE_MONTHLY_TRENDS,
        "aging_buckets": AUDIT_AGING_BUCKETS,
        "rejection_trends": REJECTION_TRENDS,
        "sla_trends": SLA_TRENDS,
        "maturity": display_framework_maturity(live),
        "closure_rate_pct": 87.4,
        "avg_days_to_close": 18.6,
    }


def enterprise_dashboard():
    stats = ecs_state.build_evidence_analytics()
    stats["framework_stats"] = display_framework_maturity(stats["framework_stats"])
    stats["overall_compliance_pct"] = enterprise_kpis()["enterprise_compliance_pct"]
    comp = completeness_report()
    apps = application_comparison()
    top_risk = sorted(stats["framework_stats"], key=lambda x: x.get("maturity_pct", x["compliance_pct"]))[:3]
    top_rejected = [
        {
            "key": k,
            "reason": v["reason"],
        }
        for k, v in list(ecs_state.rejected_controls.items())[:5]
    ]
    national = round(
        sum(r["score"] for r in ecs_state.PAN_INDIA_REGIONS)
        / len(ecs_state.PAN_INDIA_REGIONS),
        1,
    )
    return {
        "analytics": stats,
        "completeness": comp,
        "applications": apps,
        "top_risk_frameworks": top_risk,
        "top_rejected": top_rejected,
        "national_score": national,
        "regions": ecs_state.PAN_INDIA_REGIONS,
        "branch_total": ecs_state.PAN_INDIA_BRANCH_TOTAL,
        "kpis": enterprise_kpis(),
        "approval_history": get_approval_history(8),
    }


def lifecycle_timeline():
    from app.audit_trail import get_audit_trail

    events = []
    stamps = [
        "2026-05-24 09:12 UTC",
        "2026-05-23 16:40 UTC",
        "2026-05-22 11:05 UTC",
        "2026-05-21 14:22 UTC",
    ]
    i = 0
    for key in ecs_state.approved_controls:
        fw, ctrl = key.split("::", 1)
        events.append(
            {
                "at": stamps[i % len(stamps)],
                "framework": fw,
                "control": ctrl,
                "status": "Closed",
                "aging_days": 5 + (i % 4),
            }
        )
        i += 1
    for key in ecs_state.submitted_controls:
        fw, ctrl = key.split("::", 1)
        events.append(
            {
                "at": stamps[i % len(stamps)],
                "framework": fw,
                "control": ctrl,
                "status": "Under Review",
                "aging_days": 12 + (i % 3),
            }
        )
        i += 1
    for key, info in ecs_state.rejected_controls.items():
        fw, ctrl = key.split("::", 1)
        events.append(
            {
                "at": stamps[i % len(stamps)],
                "framework": fw,
                "control": ctrl,
                "status": "Rejected",
                "aging_days": 8,
                "reason": info["reason"],
            }
        )
        i += 1
    if not events:
        for row in get_audit_trail(8):
            events.append(
                {
                    "at": row["timestamp"],
                    "framework": row["framework"] or "Enterprise",
                    "control": row["control"] or row["action"],
                    "status": row["action"],
                    "aging_days": 10,
                    "reason": row.get("detail", ""),
                }
            )
    return events


def _app_for(framework: str, control: str) -> str:
    for item in ecs_state.PCI_DSS_MOCK_EVIDENCES:
        if item["control"] == control:
            return item["application"]
    for row in ecs_state.scheduler_data:
        if len(row) >= 2 and row[1] == framework:
            return row[0]
    return "Net Banking"


def audit_preparation_checklist():
    comp = completeness_report()
    recommended = []
    for m in comp["missing"][:10]:
        recommended.append(
            {
                "framework": m["framework"],
                "control": m["control"],
                "action": f"Collect evidence: {m['evidence']}",
                "priority": "High",
            }
        )
    return {
        "checklist": recommended,
        "missing_controls": comp["missing_count"],
        "ready_pct": ecs_state.build_evidence_analytics()["overall_compliance_pct"],
        "upcoming_audits": [
            {"framework": "PCI DSS", "date": "2026-06-15", "auditor": "Deloitte", "days_out": 22, "readiness": 78},
            {"framework": "DPSC", "date": "2026-07-08", "auditor": "KPMG", "days_out": 45, "readiness": 71},
            {"framework": "CSITE", "date": "2026-08-20", "auditor": "Internal Audit", "days_out": 88, "readiness": 69},
        ],
        "pending_auditor_requests": [
            {"request": "Firewall rule export — Net Banking", "framework": "PCI DSS", "due": "2026-05-28", "owner": "R. Mehta"},
            {"request": "Privileged access review Q2", "framework": "DPSC", "due": "2026-05-30", "owner": "A. Sharma"},
        ],
    }
