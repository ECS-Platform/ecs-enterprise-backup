"""Context-aware enterprise governance analytics — explainable KPIs and filtered trends."""

from __future__ import annotations

import hashlib
from typing import Any

from app import ecs_state
from modules.executive_overview.engines.demo_metrics import (
    APPLICATION_COMPLIANCE_BASELINE,
    AUDIT_AGING_BUCKETS,
    BUSINESS_UNITS,
    ENTERPRISE_MONTHLY_TRENDS,
    FRAMEWORK_MATURITY_BASELINE,
    REJECTION_TRENDS,
    SLA_TRENDS,
    display_application_rows,
    display_framework_maturity,
)
from modules.frameworks.engines.framework_catalog import FRAMEWORK_CATALOG, get_all_evidence_records
from modules.governance.engines.workflow_module import build_owner_work_queue, work_queue_summary

FILTER_FRAMEWORKS = ["Enterprise-wide"] + sorted(FRAMEWORK_MATURITY_BASELINE.keys())
FILTER_APPLICATIONS = ["All Applications"] + list(APPLICATION_COMPLIANCE_BASELINE.keys())
FILTER_RISKS = ["All", "Critical", "High", "Medium", "Low"]
FILTER_PERIODS = ["Last 6 months", "Last 12 months", "YTD 2026", "Q2 2026 Audit Cycle"]
FILTER_AUDIT_CYCLES = ["Q1 2026 Audit Cycle", "Q2 2026 Audit Cycle", "H1 2026 External Audit", "FY 2025-26 Annual Audit"]
FILTER_REGIONS = ["All Regions"] + [r["region"] for r in ecs_state.PAN_INDIA_REGIONS]
FILTER_BUSINESS_UNITS = ["All Units"] + [u["unit"] for u in BUSINESS_UNITS]

REJECTION_REASONS = [
    {"reason": "Expired evidence", "pct": 32, "tooltip": "Submitted artifact past validity / TD window"},
    {"reason": "Insufficient proof", "pct": 24, "tooltip": "Evidence does not substantiate control requirement"},
    {"reason": "Incorrect scope", "pct": 18, "tooltip": "Application or environment scope mismatch"},
    {"reason": "Outdated screenshots", "pct": 14, "tooltip": "Visual evidence not from current production state"},
    {"reason": "Failed validations", "pct": 12, "tooltip": "Automated integrity, hash, or mapping validation failed"},
]

SCOPE_TOOLTIPS = {
    "implementation_coverage": (
        "Percentage of required controls with valid evidence, active App Owner, "
        "no expired submissions, and approved audit status."
    ),
    "observations": (
        "Audit observations opened vs closed — includes control observations, evidence gaps, "
        "audit findings, and remediation tickets."
    ),
    "rejection_rate": (
        "Percentage of auditor-submitted evidences rejected in the selected period "
        "due to quality, scope, expiry, or validation failures."
    ),
    "sla_compliance": (
        "Percentage of audit remediation tasks closed within agreed SLA "
        "(typically 5–15 business days by risk tier)."
    ),
    "evidence_aging": (
        "Distribution of active audit evidences by last refresh/update age "
        "across onboarded applications in scope."
    ),
}


def get_filter_options() -> dict:
    return {
        "frameworks": FILTER_FRAMEWORKS,
        "applications": FILTER_APPLICATIONS,
        "risk_levels": FILTER_RISKS,
        "periods": FILTER_PERIODS,
        "audit_cycles": FILTER_AUDIT_CYCLES,
        "regions": FILTER_REGIONS,
        "business_units": FILTER_BUSINESS_UNITS,
    }


def parse_analytics_filters(
    framework: str = "Enterprise-wide",
    application: str = "All Applications",
    risk_level: str = "All",
    audit_cycle: str = "Q2 2026 Audit Cycle",
    time_period: str = "Last 6 months",
    region: str = "All Regions",
    business_unit: str = "All Units",
) -> dict:
    return {
        "framework": framework or "Enterprise-wide",
        "application": application or "All Applications",
        "risk_level": risk_level or "All",
        "audit_cycle": audit_cycle or "Q2 2026 Audit Cycle",
        "time_period": time_period or "Last 6 months",
        "region": region or "All Regions",
        "business_unit": business_unit or "All Units",
    }


def _seed(key: str, lo: int, hi: int) -> int:
    h = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)
    return lo + (h % (hi - lo + 1))


def _scope_label(filters: dict) -> str:
    fw = filters["framework"]
    app = filters["application"]
    period = filters["time_period"]
    parts = []
    if fw != "Enterprise-wide":
        parts.append(fw)
    else:
        parts.append("Enterprise-wide")
    if app != "All Applications":
        parts.append(app)
    else:
        parts.append("onboarded applications")
    parts.append(period.lower())
    return " · ".join([parts[0], parts[1], parts[2]])


def _framework_multiplier(filters: dict) -> float:
    fw = filters["framework"]
    if fw == "Enterprise-wide":
        return 1.0
    return 0.92 + (_seed(fw, 0, 8) / 100)


def _risk_multiplier(filters: dict) -> float:
    risk = filters.get("risk_level", "All")
    if risk == "Critical":
        return 0.88
    if risk == "High":
        return 0.93
    if risk == "Medium":
        return 0.97
    if risk == "Low":
        return 1.04
    return 1.0


def _combined_multiplier(filters: dict) -> float:
    return _framework_multiplier(filters) * _risk_multiplier(filters)


def build_extended_trends(filters: dict, tab_payload: dict | None = None) -> dict:
    """Additional trend series — control growth, evidence collection, remediation velocity."""
    from modules.governance.engines.trends_analytics_engine import build_trends_tab_payload

    mult = _combined_multiplier(filters)
    fw = filters.get("framework", "Enterprise-wide")
    app = filters.get("application", "All Applications")
    tab = tab_payload or build_trends_tab_payload(filters)
    from modules.executive_overview.engines.executive_analytics_engine import timeline_labels_weekly

    weeks = timeline_labels_weekly(6)
    months = [r["label"] for r in tab["coverage_series"]] or ["Jan", "Feb", "Mar", "Apr", "May"]
    quarters = [r["quarter"].split()[0] for r in tab["quarterly_coverage"]]
    return {
        "weekly_control_growth": [
            {"label": w, "value": max(2, int((_seed(f"{fw}-{app}-{w}-ctrl", 4, 18) * mult)))}
            for w in weeks
        ],
        "monthly_evidence_collection": [
            {"label": m, "value": max(8, int(tab["coverage_series"][i]["implemented"] / 180 * mult)) if i < len(tab["coverage_series"]) else 40}
            for i, m in enumerate(months)
        ],
        "quarterly_audit_readiness": [
            {"label": q, "value": tab["quarterly_coverage"][i]["coverage_pct"], "suffix": "%", "tone": "green"}
            for i, q in enumerate(quarters)
        ],
        "yearly_maturity_evolution": [
            {"label": str(2022 + i), "value": min(99, round((62 + i * 5 + _seed(fw + str(i), 0, 6)) * mult, 1))}
            for i in range(5)
        ],
        "remediation_closure_velocity": [
            {"label": s["label"], "value": s["closed"], "tone": "teal"}
            for s in tab["observations_series"]
        ],
        "evidence_rejection_trend": [
            {"label": s["label"], "value": s["rejected"], "tone": "orange"}
            for s in tab["rejections_series"]
        ],
        "stale_evidence_trend": [
            {"label": s["label"], "value": max(2, tab["evidence_aging"]["expired_count"] + _seed(fw + s["label"], 0, 8)), "tone": "slate"}
            for s in tab["observations_series"]
        ],
    }



def _application_list(filters: dict) -> list[str]:
    app = filters["application"]
    if app != "All Applications":
        return [app]
    return list(APPLICATION_COMPLIANCE_BASELINE.keys())[:5]


def control_implementation_coverage(filters: dict) -> dict:
    stats = ecs_state.build_evidence_analytics()
    fw_filter = filters["framework"]
    apps = _application_list(filters)
    mult = _combined_multiplier(filters)

    if fw_filter != "Enterprise-wide":
        baseline = FRAMEWORK_MATURITY_BASELINE.get(fw_filter, 75.0)
        live_rows = [f for f in stats["framework_stats"] if f["name"] == fw_filter]
        live = live_rows[0]["compliance_pct"] if live_rows else 0
        current = round(max(live, baseline * 0.35 + live * 0.65) if live else baseline, 1)
        current = round(current * mult, 1)
    else:
        baseline_avg = sum(FRAMEWORK_MATURITY_BASELINE.values()) / len(FRAMEWORK_MATURITY_BASELINE)
        live = stats.get("overall_compliance_pct", 0)
        current = round(max(live, baseline_avg * 0.35 + live * 0.65) if live else baseline_avg, 1)
        current = round(current * mult, 1)

    series = []
    for row in ENTERPRISE_MONTHLY_TRENDS:
        pct = round(row["compliance"] * mult + _seed(row["month"] + fw_filter, -2, 2), 1)
        series.append({
            "month": row["month"],
            "coverage_pct": min(99, pct),
            "compliance": min(99, pct),
            "controls_in_scope": _seed(fw_filter + row["month"], 120, 280),
            "evidences_valid": _seed(fw_filter + row["month"] + "e", 80, 240),
        })

    app_label = ", ".join(apps[:4]) + ("…" if len(apps) > 4 else "")
    definition = (
        f"Control implementation coverage for {fw_filter if fw_filter != 'Enterprise-wide' else 'all frameworks'} "
        f"across {app_label}."
    )
    return {
        "title": "Control Implementation Coverage",
        "definition": definition,
        "tooltip": SCOPE_TOOLTIPS["implementation_coverage"],
        "scope": _scope_label(filters),
        "current_pct": current,
        "series": series,
        "applications": apps,
        "framework": fw_filter,
        "criteria": [
            "Valid evidence attached",
            "Active App Owner assigned",
            "No expired submissions",
            "Approved audit status",
        ],
    }


def audit_observations_opened_closed(filters: dict) -> dict:
    mult = _combined_multiplier(filters)
    series = []
    for row in ENTERPRISE_MONTHLY_TRENDS:
        opened = max(1, int(row["opened"] * mult))
        closed = max(1, int(row["closed"] * mult))
        series.append({
            "month": row["month"],
            "opened": opened,
            "closed": closed,
            "net": closed - opened,
            "compliance": row["compliance"],
        })
    total_opened = sum(s["opened"] for s in series)
    total_closed = sum(s["closed"] for s in series)
    closure_rate = round((total_closed / max(total_opened, 1)) * 100, 1)
    from modules.governance.engines.trends_analytics_engine import (
        OBSERVATIONS_CLOSURE_LABEL,
        OBSERVATIONS_CLOSURE_TOOLTIP,
    )

    return {
        "title": "Audit Observations Opened vs Closed",
        "subtitle": "Monthly opened vs closed audit observations",
        "tooltip": SCOPE_TOOLTIPS["observations"],
        "scope": _scope_label(filters),
        "series": series,
        "closure_rate_pct": closure_rate,
        "closure_rate_label": OBSERVATIONS_CLOSURE_LABEL,
        "closure_rate_tooltip": OBSERVATIONS_CLOSURE_TOOLTIP,
        "avg_days_to_close": 18.6,
    }


def auditor_evidence_rejection_rate(filters: dict) -> dict:
    mult = _combined_multiplier(filters)
    series = []
    for row in REJECTION_TRENDS:
        rate = round(row["rate_pct"] * (1.1 - mult * 0.1), 1)
        series.append({
            "month": row["month"],
            "rate_pct": rate,
            "rejections": row["rejections"],
            "submitted": max(row["rejections"] * 12, 80),
        })

    apps_rejection = []
    for app, baseline in APPLICATION_COMPLIANCE_BASELINE.items():
        if filters["application"] != "All Applications" and app != filters["application"]:
            continue
        apps_rejection.append({
            "application": app,
            "rate_pct": round(max(2.0, (100 - baseline) / 8 + _seed(app, 0, 3)), 1),
            "rejections": _seed(app + "rej", 2, 14),
        })
    apps_rejection.sort(key=lambda x: -x["rate_pct"])

    fw_rejection = []
    for fw, baseline in FRAMEWORK_MATURITY_BASELINE.items():
        if filters["framework"] not in ("Enterprise-wide", fw):
            continue
        fw_rejection.append({
            "framework": fw,
            "rate_pct": round(max(2.5, (100 - baseline) / 7), 1),
        })

    return {
        "title": "Auditor Evidence Rejection Rate",
        "definition": "Percentage of submitted evidences rejected by auditors in scope.",
        "tooltip": SCOPE_TOOLTIPS["rejection_rate"],
        "scope": _scope_label(filters),
        "series": series,
        "top_reasons": REJECTION_REASONS,
        "top_applications": apps_rejection[:5],
        "framework_wise": fw_rejection[:8] if filters["framework"] == "Enterprise-wide" else fw_rejection,
        "latest_rate_pct": series[-1]["rate_pct"] if series else 4.2,
    }


def remediation_sla_compliance(filters: dict) -> dict:
    mult = _combined_multiplier(filters)
    wq = work_queue_summary()
    series = []
    for row in SLA_TRENDS:
        on_time = min(99, int(row["on_time_pct"] * mult + _seed(row["month"], -1, 2)))
        series.append({
            "month": row["month"],
            "on_time_pct": on_time,
            "breaches": row["breaches"],
            "overdue": max(1, int(row["breaches"] * 0.6)),
        })

    fw_sla = []
    for fw in (FILTER_FRAMEWORKS[1:] if filters["framework"] == "Enterprise-wide" else [filters["framework"]]):
        if fw == "Enterprise-wide":
            continue
        fw_sla.append({
            "framework": fw,
            "on_time_pct": min(99, _seed(fw + "sla", 82, 96)),
            "overdue": _seed(fw + "od", 1, 8),
        })

    app_sla = []
    for app in _application_list(filters):
        app_sla.append({
            "application": app,
            "on_time_pct": min(99, _seed(app + "sla", 84, 97)),
            "breaches": _seed(app + "br", 0, 5),
        })

    owner_q = build_owner_work_queue(50)
    overdue_tasks = [i for i in owner_q if i.get("sla") == "Breached" or i.get("aging_days", 0) > 14][:6]
    upcoming_breaches = [i for i in owner_q if 10 <= i.get("aging_days", 0) <= 14][:5]

    return {
        "title": "Audit Remediation SLA Compliance",
        "definition": "Percentage of remediation tasks closed within agreed SLA.",
        "tooltip": SCOPE_TOOLTIPS["sla_compliance"],
        "scope": _scope_label(filters),
        "series": series,
        "latest_on_time_pct": series[-1]["on_time_pct"] if series else 91,
        "overdue_tasks": overdue_tasks,
        "upcoming_breaches": upcoming_breaches,
        "framework_wise": sorted(fw_sla, key=lambda x: x["on_time_pct"])[:6],
        "application_wise": app_sla,
        "total_breaches": wq.get("sla_breach", 8),
    }


def active_evidence_age_distribution(filters: dict) -> dict:
    records = get_all_evidence_records()
    mult = _combined_multiplier(filters)
    buckets = []
    for b in AUDIT_AGING_BUCKETS:
        count = max(1, int(b["count"] * mult))
        buckets.append({**b, "count": count, "pct": b["pct"]})

    stale_frameworks = []
    for fw, baseline in FRAMEWORK_MATURITY_BASELINE.items():
        if filters["framework"] not in ("Enterprise-wide", fw):
            continue
        stale_frameworks.append({
            "framework": fw,
            "stale_count": _seed(fw + "stale", 3, 18),
            "expiring_soon": _seed(fw + "exp", 1, 9),
        })
    stale_frameworks.sort(key=lambda x: -x["stale_count"])

    stale_apps = []
    for app in _application_list(filters):
        stale_apps.append({
            "application": app,
            "stale_count": _seed(app + "stale", 2, 14),
            "oldest_days": _seed(app + "old", 45, 120),
        })
    stale_apps.sort(key=lambda x: -x["stale_count"])

    expired = sum(1 for r in records if r.get("evidence_status") == "Expired")
    due_refresh = sum(1 for r in records if r.get("evidence_status") == "Due for Refresh")

    return {
        "title": "Active Evidence Age Distribution",
        "definition": "Distribution of active audit evidences by last refresh/update age.",
        "tooltip": SCOPE_TOOLTIPS["evidence_aging"],
        "scope": _scope_label(filters),
        "buckets": buckets,
        "stale_frameworks": stale_frameworks[:6],
        "stale_applications": stale_apps[:5],
        "expiring_evidences": due_refresh or 17,
        "expired_count": expired or 6,
    }


def top_risk_applications(filters: dict) -> list[dict]:
    from modules.governance.engines.analytics_module import application_comparison

    rows = application_comparison()
    if filters["application"] != "All Applications":
        rows = [r for r in rows if r["application"] == filters["application"]]

    risk_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    enriched = []
    for r in rows:
        app = r["application"]
        enriched.append({
            "application": app,
            "compliance_pct": r["compliance_pct"],
            "open_observations": _seed(app + "obs", 2, 18),
            "high_risk_gaps": _seed(app + "gap", 1, 12),
            "stale_evidences": _seed(app + "st", 2, 15),
            "sla_breaches": _seed(app + "sla", 0, 6),
            "risk": r.get("risk", "Medium"),
        })
    enriched.sort(key=lambda x: (risk_order.get(x["risk"], 9), -x["high_risk_gaps"]))
    return enriched[:6]


def build_contextual_trends(filters: dict | None = None) -> dict:
    from modules.governance.engines.trends_analytics_engine import build_trends_tab_payload

    base = parse_analytics_filters()
    if filters:
        base.update({k: v for k, v in filters.items() if v})
    tab = build_trends_tab_payload(base)
    f = tab["filters"]

    impl = control_implementation_coverage(f)
    impl["current_pct"] = tab["control_totals"]["coverage_pct"]
    impl["implemented_controls"] = tab["control_totals"]["implemented_controls"]
    impl["total_controls"] = tab["control_totals"]["total_controls"]
    impl["missing_controls"] = tab["control_totals"]["missing_controls"]
    impl["pending_controls"] = tab["control_totals"]["pending_controls"]
    impl["series"] = [
        {
            **row,
            "coverage_pct": row["coverage_pct"],
            "implemented": row["implemented"],
            "missing": row["missing"],
            "pending": row["pending"],
        }
        for row in tab["coverage_series"]
    ]
    impl["framework_contributions"] = tab["framework_contributions"]
    impl["quarterly_history"] = tab["quarterly_coverage"]

    obs = audit_observations_opened_closed(f)
    obs["series"] = tab["observations_series"]
    obs["closure_rate_pct"] = tab["closure_rate_pct"]
    obs["closure_rate_label"] = tab.get("closure_rate_label")
    obs["closure_rate_tooltip"] = tab.get("closure_rate_tooltip")

    rej = auditor_evidence_rejection_rate(f)
    rej["series"] = tab["rejections_series"]
    rej["latest_rate_pct"] = tab["rejections_series"][-1]["rate_pct"] if tab["rejections_series"] else 4.2
    rej["top_reasons"] = tab["rejection_reasons"]

    sla = remediation_sla_compliance(f)
    sla["series"] = tab["sla_series"]
    sla["latest_on_time_pct"] = tab["sla_series"][-1]["on_time_pct"] if tab["sla_series"] else 91
    sla["application_wise"] = tab["sla_violators"]
    sla["total_breaches"] = tab["total_breaches"]

    aging = active_evidence_age_distribution(f)
    apps = top_risk_applications(f)

    risk = f.get("risk_level", "All")
    if risk != "All":
        risk_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        apps = [a for a in apps if a.get("risk") == risk or (risk == "High" and a.get("risk") in ("High", "Critical"))]

    extended = build_extended_trends(f, tab)

    return {
        "filters": f,
        "filter_options": get_filter_options(),
        "scope_summary": tab["scope_summary"],
        "implementation_coverage": impl,
        "observations": obs,
        "rejection_rate": rej,
        "sla_compliance": sla,
        "evidence_aging": aging,
        "top_risk_applications": apps,
        "extended_trends": extended,
        "executive_kpis": tab["executive_kpis"],
        "trends_payload": tab,
    }


def build_trends_module_view(role: str, filters: dict | None = None) -> dict:
    intel = build_contextual_trends(filters)
    impl = intel["implementation_coverage"]
    obs = intel["observations"]
    rej = intel["rejection_rate"]
    sla = intel["sla_compliance"]
    aging = intel["evidence_aging"]

    monthly = []
    for i, row in enumerate(impl["series"]):
        o = obs["series"][i] if i < len(obs["series"]) else {}
        monthly.append({
            **row,
            "opened": o.get("opened", 0),
            "closed": o.get("closed", 0),
        })

    return {
        "kpis": intel["executive_kpis"],
        "rows": monthly,
        "trends": {
            "avg_days_to_close": obs["avg_days_to_close"],
            "closure_rate_pct": obs["closure_rate_pct"],
            "intel": intel,
        },
        "rejection_trends": rej["series"],
        "sla_trends": sla["series"],
        "aging_buckets": aging["buckets"],
        "intel": intel,
        "role": role,
    }


def build_governance_intel_view(role: str, filters: dict | None = None) -> dict:
    from modules.frameworks.engines.control_validation_engine import build_governance_analytics

    intel = build_contextual_trends(filters)
    gov = build_governance_analytics()
    gov_enriched = enrich_governance_analytics(gov, intel)

    return {
        "kpis": [
            {
                "label": "Audit Readiness",
                "value": f"{gov_enriched['audit_readiness_pct']}%",
                "tone": "primary",
                "tooltip": "Approved controls with active evidence across in-scope applications.",
            },
            {
                "label": "Open Audit Findings",
                "value": gov_enriched.get("open_findings", 0),
                "tone": "danger",
                "tooltip": "Unresolved control observations and evidence gaps in workflow queue.",
            },
            {
                "label": "High-Risk Controls",
                "value": len(gov_enriched.get("top_risky_controls", [])),
                "tone": "warning",
                "tooltip": "Controls rated Critical/High with aging remediation.",
            },
            {
                "label": "Evidence Freshness",
                "value": f"{100 - gov_enriched['stale_evidence_pct']:.0f}%",
                "tone": "success",
                "tooltip": "Share of active evidences refreshed within 60 days.",
            },
        ],
        "monthly_trends": intel["observations"]["series"],
        "rejection_trends": intel["rejection_rate"]["series"],
        "sla_trends": intel["sla_compliance"]["series"],
        "framework_maturity": gov["framework_maturity"],
        "operational_maturity": gov.get("operational_maturity", {}),
        "control_effectiveness": gov["control_effectiveness"],
        "implementation_coverage": intel["implementation_coverage"],
        "rejection_analytics": intel["rejection_rate"],
        "sla_analytics": intel["sla_compliance"],
        "evidence_aging": intel["evidence_aging"],
        "top_risk_applications": intel["top_risk_applications"],
        "risk_trends": [{"month": t["month"], "opened": t["opened"], "closed": t["closed"]} for t in intel["observations"]["series"]],
        "exception_trends": [
            {"month": "Mar 2026", "active": 4, "expired": 1},
            {"month": "Apr 2026", "active": 5, "expired": 2},
            {"month": "May 2026", "active": 4, "expired": 2},
        ],
        "top_reused": gov.get("most_reused_evidence", []),
        "repeat_failures": gov["repeat_failures"],
        "intel": intel,
        "governance_extended": gov_enriched,
        "actions": ["export_chart", "drill_down"],
        "role": role,
    }


def enrich_governance_analytics(gov: dict, intel: dict | None = None) -> dict:
    intel = intel or build_contextual_trends()
    wq = work_queue_summary()
    return {
        **gov,
        "open_findings": wq.get("pending", 0) + len(ecs_state.rejected_controls),
        "overdue_remediation": wq.get("sla_breach", 0),
        "top_risk_applications": intel["top_risk_applications"],
        "implementation_coverage_pct": intel["implementation_coverage"]["current_pct"],
        "kpi_tooltips": {
            "audit_readiness": "Approved controls with valid evidence across onboarded applications.",
            "stale_evidence": "Evidences past refresh window or marked Due for Refresh / Expired.",
            "sla_breaches": "Remediation tasks past agreed SLA in App Owner and auditor queues.",
            "escalated": "Items escalated to Compliance Head or CIO executive queue.",
        },
        "framework_coverage_label": "Framework Implementation Coverage",
    }
