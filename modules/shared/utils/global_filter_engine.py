"""Centralized ECS dynamic filter engine — options, apply, KPI refresh, state preservation."""

from __future__ import annotations

from app import ecs_state
from modules.frameworks.engines.framework_catalog import get_merged_framework_catalog
from modules.shared.utils.standard_filter_engine import aggregate_kpis, build_standard_dataset, filter_rows

APPLICATIONS = [
    "Net Banking", "Mobile Banking", "Payments", "Treasury", "UPI",
    "Loan System", "Card Platform", "Wealth Portal",
]

FRAMEWORKS = list(get_merged_framework_catalog().keys()) + [
    "RBI Cyber", "ISO 27001", "SWIFT CSP",
]

REGIONS = ["All Regions", "North", "South", "East", "West", "Central"]
RISKS = ["All Risk Levels", "Critical", "High", "Medium", "Low"]
STATUSES = ["All Statuses", "Open", "Closed", "Approved", "Rejected", "Pending Review", "Submitted", "Expired", "Escalated"]
OWNERS = [
    "All Owners", "R. Mehta (App Owner)", "A. Sharma (App Owner)", "K. Reddy (App Owner)",
    "S. Banerjee (App Owner)", "P. Iyer (App Owner)", "M. Joshi (App Owner)", "V. Rao (App Owner)",
]
AUDIT_CYCLES = ["All Cycles", "Q1 2026", "Q2 2026 Audit Cycle", "Q3 2026", "FY 2026"]
SEVERITIES = ["All Severities", "Critical", "High", "Medium", "Low"]
DATE_RANGES = ["Last 7 days", "Last 30 days", "Last 90 days", "Quarterly", "Yearly"]
GRANULARITIES = ["Daily", "Weekly", "Monthly", "Quarterly"]


def filter_options(role: str = "owner") -> dict:
    from modules.shared.services.role_filter_scope import apply_role_scope

    scoped_apps = apply_role_scope([{"application": a} for a in APPLICATIONS], role)
    app_names = ["All Applications"] + [a["application"] for a in scoped_apps]
    return {
        "frameworks": ["All Frameworks"] + sorted(set(FRAMEWORKS)),
        "applications": app_names,
        "regions": REGIONS,
        "risks": RISKS,
        "statuses": STATUSES,
        "owners": OWNERS,
        "audit_cycles": AUDIT_CYCLES,
        "severities": SEVERITIES,
        "date_ranges": DATE_RANGES,
        "granularities": GRANULARITIES,
    }


def normalize_filters(raw: dict | None) -> dict:
    raw = raw or {}
    return {
        "framework": raw.get("framework") or raw.get("fw") or "All Frameworks",
        "application": raw.get("application") or raw.get("app") or "All Applications",
        "region": raw.get("region") or "All Regions",
        "risk": raw.get("risk") or raw.get("risk_level") or "All Risk Levels",
        "status": raw.get("status") or "All Statuses",
        "owner": raw.get("owner") or "All Owners",
        "audit_cycle": raw.get("audit_cycle") or "All Cycles",
        "severity": raw.get("severity") or "All Severities",
        "date_range": raw.get("date_range") or "Last 30 days",
        "granularity": raw.get("granularity") or "Monthly",
    }


def apply_filters(module: str, role: str, filters: dict | None = None) -> dict:
    """Return filtered dataset + KPIs for a module."""
    v = normalize_filters(filters)
    dataset = build_standard_dataset(module, role, v if module == "audit_prep" else None)
    records = dataset.get("records", {})
    filtered: dict = {}
    for key, rows in records.items():
        if isinstance(rows, list):
            filtered[key] = filter_rows(rows, v)
        else:
            filtered[key] = rows
    kpis = aggregate_kpis(module, filtered, v)
    status_counts = _status_counts(module, filtered)
    return {
        "module": module,
        "role": role,
        "filters": v,
        "records": filtered,
        "kpis": kpis,
        "status_counts": status_counts,
        "total_rows": sum(len(r) for r in filtered.values() if isinstance(r, list)),
    }


def _status_counts(module: str, records: dict) -> dict:
    counts: dict[str, int] = {}
    for rows in records.values():
        if not isinstance(rows, list):
            continue
        for r in rows:
            st = r.get("status") or r.get("health") or "Unknown"
            counts[st] = counts.get(st, 0) + 1
    return counts
