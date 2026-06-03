"""Metric trace — formula, contributors, and audit context for drilldown modals."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from modules.shared.utils.demo_data_standards import (
    BANKING_APPLICATIONS,
    BANKING_OWNERS,
    FRAMEWORKS,
    between,
    pick,
    seed,
)

ANCHOR = date(2026, 5, 29)

_BANKING_APPS = [
    "Net Banking", "Mobile Banking", "Payments", "UPI", "Treasury",
    "Loan Origination", "Customer Onboarding", "Card Platform",
    "Internet Banking", "Core Banking",
]


def _metric_seed(metric: str, page: str, framework: str, count: int) -> int:
    return seed("mtrace", page, metric, framework, count)


def _historical_trend(s: int, months: int = 6) -> list[dict[str, Any]]:
    rows = []
    for i in range(months):
        m = ANCHOR.replace(day=1) - timedelta(days=30 * (months - 1 - i))
        rows.append({
            "month": m.strftime("%b %Y"),
            "value_pct": between(s >> (i + 2), 45, 92),
            "controls_covered": between(s >> (i + 4), 80, 220),
            "evidence_approved": between(s >> (i + 6), 60, 180),
        })
    return rows


def build_metric_trace(
    *,
    metric: str = "",
    page: str = "",
    label: str = "",
    count: int = 0,
    framework: str = "",
    role: str = "cio",
    display_value: str = "",
) -> dict[str, Any]:
    """Build explainability block for a drilled metric."""
    s = _metric_seed(metric, page, framework, count)
    fw = framework or pick(s, FRAMEWORKS)
    implemented = between(s >> 2, max(count, 24), max(count + 80, 124))
    applicable = between(s >> 4, implemented + 20, implemented + 120)
    if count and count > 0:
        implemented = min(implemented, count)
        applicable = max(applicable, count)
    readiness = round(implemented * 100 / applicable, 1) if applicable else 0.0
    pct_display = display_value or f"{readiness}%"
    if count and not display_value and "%" not in str(count):
        pct_display = str(count)

    app_count = min(len(_BANKING_APPS), between(s >> 6, 3, 8))
    contributing_apps = [pick(seed(s, i, "app"), _BANKING_APPS) for i in range(app_count)]
    contributing_apps = list(dict.fromkeys(contributing_apps))

    ctrl_count = min(between(s >> 8, 8, 24), max(count, 12))
    contributing_controls = [
        f"CTRL-{pick(seed(s, i, 'c'), ['PCI', 'VAPT', 'DPSC', 'APP'])[:3]}-{i + 1:03d}"
        for i in range(ctrl_count)
    ]

    ev_count = min(between(s >> 10, 6, 20), max(count, 10))
    contributing_evidence = [
        {
            "evidence_id": f"EVD-{between(seed(s, i, 'e'), 1000, 9999)}",
            "owner": pick(seed(s, i, "o"), BANKING_OWNERS),
            "status": pick(seed(s, i, "st"), ["Approved", "In Review", "Pending", "Auditor Accepted"]),
            "upload_date": (ANCHOR - timedelta(days=between(seed(s, i, "d"), 1, 90))).strftime("%Y-%m-%d"),
            "framework": fw,
            "application": pick(seed(s, i, "a"), contributing_apps),
        }
        for i in range(ev_count)
    ]

    obs_count = min(between(s >> 12, 4, 15), max(count // 3, 6))
    related_observations = [
        {
            "observation_id": f"OBS-{pick(seed(s, i, 'obs'), ['PCI', 'VAPT', 'DPSC'])[:3]}-{i + 1:04d}",
            "severity": pick(seed(s, i, "sev"), ["Critical", "High", "Medium", "Low"]),
            "application": pick(seed(s, i, "app"), contributing_apps),
            "framework": fw,
            "status": pick(seed(s, i, "ost"), ["Open", "In Remediation", "Closed"]),
        }
        for i in range(obs_count)
    ]

    target_fw = pick(s >> 14, [f for f in FRAMEWORKS if f != fw] or FRAMEWORKS)
    framework_mapping = {
        "source_framework": fw,
        "target_framework": target_fw,
        "shared_controls": between(s >> 16, 12, 48),
        "mapping_coverage_pct": between(s >> 18, 62, 94),
    }

    audit_trail = [
        {
            "created_by": pick(seed(s, i, "cb"), BANKING_OWNERS),
            "updated_by": pick(seed(s, i, "ub"), BANKING_OWNERS),
            "last_reviewed": (ANCHOR - timedelta(days=between(seed(s, i, "lr"), 1, 45))).strftime("%Y-%m-%d"),
            "action": pick(seed(s, i, "act"), ["Reviewed", "Approved", "Updated", "Escalated"]),
            "role": pick(seed(s, i, "rl"), ["Auditor", "Application Owner", "Compliance Officer"]),
        }
        for i in range(8)
    ]

    metric_name = label or metric.replace("_", " ").title() or "Metric"
    if fw and fw not in metric_name:
        metric_name = f"{fw} {metric_name}"

    return {
        "metric_name": f"{metric_name} = {pct_display}",
        "display_value": pct_display,
        "calculation_formula": {
            "implemented_controls": implemented,
            "applicable_controls": applicable,
            "numerator_label": "Implemented Controls",
            "denominator_label": "Applicable Controls",
            "formula_text": f"Readiness = {implemented} / {applicable}",
            "result": f"{readiness}%",
            "narrative": (
                f"{metric_name}: {implemented} of {applicable} applicable controls implemented "
                f"across {len(contributing_apps)} banking applications under {fw}."
            ),
        },
        "contributing_applications": contributing_apps,
        "contributing_controls": contributing_controls,
        "contributing_evidence": contributing_evidence,
        "related_observations": related_observations,
        "framework_mapping": framework_mapping,
        "historical_trend": _historical_trend(s),
        "audit_trail": audit_trail,
        "gaps": [
            {
                "gap_id": f"GAP-{i + 1:04d}",
                "severity": pick(seed(s, i, "g"), ["Critical", "High", "Medium"]),
                "application": pick(seed(s, i, "ga"), contributing_apps),
                "framework": fw,
                "owner": pick(seed(s, i, "go"), BANKING_OWNERS),
                "description": f"Missing evidence or control closure for {contributing_controls[i % len(contributing_controls)]}",
            }
            for i in range(min(between(s >> 20, 3, 12), max(count // 5, 5)))
        ],
        "role": role,
        "page": page,
        "framework": fw,
    }
