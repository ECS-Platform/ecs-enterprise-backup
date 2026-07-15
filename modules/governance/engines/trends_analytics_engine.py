"""Executive Trends analytics — enterprise-scale control, observation, rejection, and SLA series."""

from __future__ import annotations

from typing import Any

from app import ecs_state
from modules.executive_overview.engines.demo_metrics import (
    APPLICATION_COMPLIANCE_BASELINE,
    ENTERPRISE_MONTHLY_TRENDS,
    FRAMEWORK_MATURITY_BASELINE,
    REJECTION_TRENDS,
    SLA_TRENDS,
)
from modules.frameworks.engines.framework_catalog import catalog_stats, get_all_evidence_records
from modules.governance.engines.governance_intelligence import (
    REJECTION_REASONS,
    _combined_multiplier,
    _scope_label,
    _seed,
    parse_analytics_filters,
)
from modules.governance.engines.workflow_module import build_owner_work_queue, work_queue_summary

# Enterprise banking scale — aligned with catalog × application × environment matrix
ENTERPRISE_CONTROL_TOTAL = 58_563
ENTERPRISE_IMPLEMENTED_BASE = 24_714
PRIMARY_FRAMEWORKS = ["PCI DSS", "AppSec", "VAPT", "CSITE"]
QUARTERS = ["Q1 2026", "Q2 2026", "Q3 2026", "Q4 2026"]
OBSERVATIONS_CLOSURE_LABEL = "Closed vs Newly Opened Rate"
OBSERVATIONS_CLOSURE_TOOLTIP = (
    "Percentage of observations closed relative to newly opened observations during the selected period. "
    "Values above 100% indicate backlog reduction."
)


def _catalog_scale() -> float:
    live = catalog_stats()["control_count"]
    return ENTERPRISE_CONTROL_TOTAL / max(live, 1)


def enterprise_control_totals(filters: dict | None = None) -> dict[str, Any]:
    """Implemented / missing / pending controls at enterprise or framework scope."""
    f = filters or parse_analytics_filters()
    mult = _combined_multiplier(f)
    fw = f.get("framework", "Enterprise-wide")
    stats = ecs_state.build_evidence_analytics()

    if fw != "Enterprise-wide":
        live_rows = [x for x in stats["framework_stats"] if x["name"] == fw]
        live = live_rows[0]["compliance_pct"] if live_rows else FRAMEWORK_MATURITY_BASELINE.get(fw, 75.0)
        baseline = FRAMEWORK_MATURITY_BASELINE.get(fw, 75.0)
        coverage_pct = round(max(live, baseline * 0.35 + live * 0.65) * mult, 1)
        fw_catalog = len(ecs_state.frameworks.get(fw, [])) if fw in ecs_state.frameworks else 0
        total = max(int(fw_catalog * _catalog_scale() * mult), 1200)
    else:
        baseline_avg = sum(FRAMEWORK_MATURITY_BASELINE.values()) / len(FRAMEWORK_MATURITY_BASELINE)
        live = stats.get("overall_compliance_pct", 0)
        if live < 5:
            coverage_pct = round(ENTERPRISE_IMPLEMENTED_BASE * 100 / ENTERPRISE_CONTROL_TOTAL * mult, 1)
        else:
            coverage_pct = round(max(live, baseline_avg * 0.35 + live * 0.65) * mult, 1)
        total = int(ENTERPRISE_CONTROL_TOTAL * mult)

    implemented = int(round(total * coverage_pct / 100))
    pending = max(int(total * 0.09 * mult), _seed(fw + "pend", 800, 6200))
    missing = max(0, total - implemented - pending)

    return {
        "total_controls": total,
        "implemented_controls": implemented,
        "missing_controls": missing,
        "pending_controls": pending,
        "coverage_pct": round(implemented * 100 / total, 1) if total else coverage_pct,
        "formula": f"Coverage = {implemented:,} / {total:,} × 100",
        "framework": fw,
        "scope": _scope_label(f),
    }


def framework_implementation_contributions(filters: dict | None = None) -> list[dict[str, Any]]:
    f = filters or parse_analytics_filters()
    fw_filter = f.get("framework", "Enterprise-wide")
    totals = enterprise_control_totals(f)
    rows = []
    frameworks = [fw_filter] if fw_filter != "Enterprise-wide" else PRIMARY_FRAMEWORKS + [
        x for x in FRAMEWORK_MATURITY_BASELINE if x not in PRIMARY_FRAMEWORKS
    ][:4]
    share_base = totals["implemented_controls"]
    for i, fw in enumerate(frameworks):
        weight = FRAMEWORK_MATURITY_BASELINE.get(fw, 75) / sum(
            FRAMEWORK_MATURITY_BASELINE.get(x, 75) for x in frameworks
        )
        impl = int(share_base * weight) if fw_filter == "Enterprise-wide" else totals["implemented_controls"]
        fw_total = int(totals["total_controls"] * weight) if fw_filter == "Enterprise-wide" else totals["total_controls"]
        rows.append({
            "framework": fw,
            "implemented_controls": impl,
            "total_controls": fw_total,
            "coverage_pct": round(impl * 100 / fw_total, 1) if fw_total else 0,
        })
    rows.sort(key=lambda x: -x["implemented_controls"])
    return rows


def coverage_monthly_series(filters: dict | None = None) -> list[dict[str, Any]]:
    f = filters or parse_analytics_filters()
    mult = _combined_multiplier(f)
    base = enterprise_control_totals(f)
    total = base["total_controls"]
    series = []
    for i, row in enumerate(ENTERPRISE_MONTHLY_TRENDS):
        pct = round(row["compliance"] * mult + _seed(row["month"] + f.get("framework", ""), -2, 2), 1)
        pct = min(99, max(38, pct))
        implemented = int(round(total * pct / 100))
        pending = max(int(total * (0.11 - i * 0.008) * mult), 400)
        missing = max(0, total - implemented - pending)
        series.append({
            "month": row["month"],
            "label": row["month"].split()[0][:3],
            "implemented": implemented,
            "missing": missing,
            "pending": pending,
            "coverage_pct": pct,
            "pct_implemented": round(implemented * 100 / total, 1),
            "pct_missing": round(missing * 100 / total, 1),
            "pct_pending": round(pending * 100 / total, 1),
        })
    return series


def quarterly_coverage_history(filters: dict | None = None) -> list[dict[str, Any]]:
    f = filters or parse_analytics_filters()
    base = enterprise_control_totals(f)
    total = base["total_controls"]
    pcts = [38.4, 39.8, 41.1, base["coverage_pct"]]
    rows = []
    for q, pct in zip(QUARTERS, pcts):
        implemented = int(round(total * pct / 100))
        rows.append({"quarter": q, "coverage_pct": pct, "implemented_controls": implemented})
    return rows


def observations_period_series(filters: dict | None = None) -> list[dict[str, Any]]:
    f = filters or parse_analytics_filters()
    mult = _combined_multiplier(f)
    series = []
    for row in ENTERPRISE_MONTHLY_TRENDS:
        opened = max(1, int(row["opened"] * mult))
        closed = max(1, int(row["closed"] * mult))
        net = closed - opened
        closure_rate = round(closed * 100 / max(opened, 1), 1)
        series.append({
            "month": row["month"],
            "label": row["month"].split()[0][:3],
            "opened": opened,
            "closed": closed,
            "net": net,
            "closure_rate_pct": closure_rate,
        })
    return series


def rejections_period_series(filters: dict | None = None) -> list[dict[str, Any]]:
    f = filters or parse_analytics_filters()
    mult = _combined_multiplier(f)
    series = []
    for row in REJECTION_TRENDS:
        rate = round(row["rate_pct"] * (1.1 - mult * 0.1), 1)
        rejected = row["rejections"]
        submitted = max(rejected * 12, int(rejected / max(rate, 0.1) * 100))
        series.append({
            "month": row["month"],
            "label": row["month"].split()[0][:3],
            "submitted": submitted,
            "rejected": rejected,
            "rate_pct": rate,
        })
    return series


def sla_period_series(filters: dict | None = None) -> list[dict[str, Any]]:
    f = filters or parse_analytics_filters()
    mult = _combined_multiplier(f)
    series = []
    for row in SLA_TRENDS:
        on_time = min(99, int(row["on_time_pct"] * mult + _seed(row["month"], -1, 2)))
        breaches = row["breaches"]
        near = max(1, int(breaches * 0.45))
        within = max(0, 100 - on_time - int(breaches * 0.15))
        series.append({
            "month": row["month"],
            "label": row["month"].split()[0][:3],
            "within_sla_pct": on_time,
            "near_breach": near,
            "breached": breaches,
            "on_time_pct": on_time,
        })
    return series


def top_sla_violating_applications(filters: dict | None = None) -> list[dict[str, Any]]:
    f = filters or parse_analytics_filters()
    apps = []
    for app, baseline in APPLICATION_COMPLIANCE_BASELINE.items():
        if f.get("application", "All Applications") != "All Applications" and app != f["application"]:
            continue
        breaches = _seed(app + "sla-br", 0, 8)
        apps.append({
            "application": app,
            "breaches": breaches,
            "on_time_pct": min(99, _seed(app + "sla", 84, 97)),
            "near_breach": _seed(app + "near", 0, 4),
        })
    apps.sort(key=lambda x: (-x["breaches"], -x["near_breach"]))
    return apps[:6]


def build_executive_trends_kpis(filters: dict | None = None) -> list[dict[str, Any]]:
    f = filters or parse_analytics_filters()
    totals = enterprise_control_totals(f)
    obs = observations_period_series(f)
    rej = rejections_period_series(f)
    sla = sla_period_series(f)
    latest_obs = obs[-1] if obs else {}
    latest_rej = rej[-1] if rej else {}
    latest_sla = sla[-1] if sla else {}

    return [
        {
            "label": "Implementation Coverage",
            "value": f"{totals['coverage_pct']}%",
            "tone": "success",
            "drill": "implementation_coverage",
            "tooltip": "Controls with valid evidence, active owner, and approved audit status.",
            "context": f"{totals['implemented_controls']:,} of {totals['total_controls']:,} controls",
        },
        {
            "label": "Observations Net",
            "value": latest_obs.get("net", 0),
            "tone": "primary",
            "drill": "observations_net",
            "tooltip": "Closed minus opened observations in the latest period.",
            "context": f"Closed {latest_obs.get('closed', 0)} vs opened {latest_obs.get('opened', 0)}",
        },
        {
            "label": "Auditor Rejection Rate",
            "value": f"{latest_rej.get('rate_pct', 4.2)}%",
            "tone": "warning",
            "drill": "auditor_rejection_rate",
            "tooltip": "Rejected evidences divided by submitted evidences in period.",
            "context": f"{latest_rej.get('rejected', 0)} rejected of {latest_rej.get('submitted', 0)} submitted",
        },
        {
            "label": "Remediation SLA Compliance",
            "value": f"{latest_sla.get('on_time_pct', 91)}%",
            "tone": "info",
            "drill": "remediation_sla_compliance",
            "tooltip": "Remediation tasks closed within agreed SLA by risk tier.",
            "context": f"{latest_sla.get('breached', 0)} breached · {latest_sla.get('near_breach', 0)} near breach",
        },
    ]


def build_trends_tab_payload(filters: dict | None = None) -> dict[str, Any]:
    """Full trends dataset for templates, filters, and drilldown APIs."""
    f = filters or parse_analytics_filters()
    totals = enterprise_control_totals(f)
    cov_series = coverage_monthly_series(f)
    obs_series = observations_period_series(f)
    rej_series = rejections_period_series(f)
    sla_series = sla_period_series(f)
    wq = work_queue_summary()
    owner_q = build_owner_work_queue(50)

    total_opened = sum(s["opened"] for s in obs_series)
    total_closed = sum(s["closed"] for s in obs_series)
    closure_rate = round(total_closed * 100 / max(total_opened, 1), 1)

    records = get_all_evidence_records()
    expired = sum(1 for r in records if r.get("evidence_status") == "Expired")

    from modules.shared.utils.data_source_marker import trends_analytics_data_source

    return {
        "filters": f,
        "scope_summary": _scope_label(f),
        "control_totals": totals,
        "framework_contributions": framework_implementation_contributions(f),
        "quarterly_coverage": quarterly_coverage_history(f),
        "coverage_series": cov_series,
        "observations_series": obs_series,
        "rejections_series": rej_series,
        "rejection_reasons": REJECTION_REASONS,
        "sla_series": sla_series,
        "sla_violators": top_sla_violating_applications(f),
        "closure_rate_pct": closure_rate,
        "closure_rate_label": OBSERVATIONS_CLOSURE_LABEL,
        "closure_rate_tooltip": OBSERVATIONS_CLOSURE_TOOLTIP,
        "avg_days_to_close": 18.6,
        "total_breaches": wq.get("sla_breach", 8),
        "overdue_tasks": [i for i in owner_q if i.get("sla") == "Breached" or i.get("aging_days", 0) > 14][:6],
        "evidence_aging": {
            "expired_count": expired,
            "due_refresh": sum(1 for r in records if r.get("evidence_status") == "Due for Refresh"),
        },
        "executive_kpis": build_executive_trends_kpis(f),
        "data_source": trends_analytics_data_source(),
    }
