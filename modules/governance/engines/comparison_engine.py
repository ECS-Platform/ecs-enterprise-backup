"""Framework-specific application comparison engine for Governance → App Comparison."""

from __future__ import annotations

import hashlib

from modules.frameworks.engines.framework_catalog import FRAMEWORK_CATALOG
from modules.operations.engines.operations_catalog import BANKING_APPLICATIONS, OWNERS

COMPARISON_APPS = [
    "Net Banking", "Mobile Banking", "Treasury", "Payments", "UPI",
    "Loan System", "Wealth Portal", "Loan Origination", "Core Banking",
]

ALL_FRAMEWORKS = list(FRAMEWORK_CATALOG.keys())

COMPARE_SCOPES = [
    "All Applications",
    "Tier-1 Only",
    "Internet Facing",
    "High Risk",
    "Critical Apps",
]

TIME_RANGES = [
    "Current Month",
    "Quarterly",
    "Yearly",
    "Last Audit Cycle",
]

_SCOPE_APPS: dict[str, list[str]] = {
    "All Applications": COMPARISON_APPS,
    "Tier-1 Only": ["Net Banking", "Mobile Banking", "Core Banking", "Payments"],
    "Internet Facing": ["Net Banking", "Mobile Banking", "UPI", "Merchant Portal", "Internet Banking"],
    "High Risk": ["Loan Origination", "Payments", "Treasury", "AML Engine", "Fraud Monitoring"],
    "Critical Apps": ["Core Banking", "Net Banking", "Payments Hub", "ATM Switch"],
}

_TRENDS = ["Improving", "Stable", "Declining", "Critical"]


def _seed(key: str) -> int:
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)


def _readiness(app: str, fw: str, time_range: str) -> dict:
    s = _seed(f"{app}|{fw}|{time_range}")
    base = 55 + (s % 38)
    if fw in ("PCI DSS", "AppSec") and app in ("Net Banking", "Mobile Banking"):
        base = max(base, 72)
    if fw == "DPSC" and app == "Mobile Banking":
        base = min(base, 35)
    readiness = min(98, base)
    failed = s % 8 if readiness < 70 else s % 4
    findings = 4 + (s % 22)
    stale = s % 6
    sla = s % 3 if readiness < 80 else 0
    drift = round((s % 15) / 10, 1)
    trend = _TRENDS[s % 4]
    if readiness < 50:
        trend = "Critical"
    elif readiness >= 85 and trend == "Declining":
        trend = "Stable"
    tone = "success" if readiness >= 80 else ("warning" if readiness >= 65 else "danger")
    return {
        "application": app,
        "framework": fw,
        "readiness_pct": readiness,
        "open_findings": findings,
        "failed_controls": failed,
        "stale_evidence": stale,
        "sla_breaches": sla,
        "audit_maturity": min(98, readiness + (s % 8) - 3),
        "framework_drift": drift,
        "trend": trend,
        "tone": tone,
        "owner": OWNERS[s % len(OWNERS)],
        "risk": "Critical" if readiness < 55 else ("High" if readiness < 70 else ("Medium" if readiness < 85 else "Low")),
    }


def _apps_in_scope(scope: str) -> list[str]:
    allowed = _SCOPE_APPS.get(scope, COMPARISON_APPS)
    return [a for a in COMPARISON_APPS if a in allowed]


def build_readiness_matrix(scope: str = "All Applications", time_range: str = "Current Month") -> list[dict]:
    apps = _apps_in_scope(scope)
    rows = []
    for app in apps:
        for fw in ALL_FRAMEWORKS:
            rows.append(_readiness(app, fw, time_range))
    return rows


def build_pair_comparisons(
    framework: str = "All Frameworks",
    scope: str = "All Applications",
    time_range: str = "Current Month",
) -> list[dict]:
    apps = _apps_in_scope(scope)
    frameworks = ALL_FRAMEWORKS if framework == "All Frameworks" else [framework]
    pairs = []
    for fw in frameworks:
        scores = {a: _readiness(a, fw, time_range) for a in apps}
        for i, a in enumerate(apps):
            for b in apps[i + 1:]:
                ra, rb = scores[a], scores[b]
                gap = abs(ra["readiness_pct"] - rb["readiness_pct"])
                pairs.append({
                    "pair_label": f"{a} vs {b}",
                    "app_a": a,
                    "app_b": b,
                    "framework": fw,
                    "readiness_a": ra["readiness_pct"],
                    "readiness_b": rb["readiness_pct"],
                    "gap": gap,
                    "open_findings_a": ra["open_findings"],
                    "open_findings_b": rb["open_findings"],
                    "failed_a": ra["failed_controls"],
                    "failed_b": rb["failed_controls"],
                    "trend": ra["trend"] if ra["readiness_pct"] >= rb["readiness_pct"] else rb["trend"],
                    "tone_a": ra["tone"],
                    "tone_b": rb["tone"],
                    "risk": "High" if gap > 12 or min(ra["readiness_pct"], rb["readiness_pct"]) < 60 else "Medium",
                })
    pairs.sort(key=lambda p: (-p["gap"], p["framework"], p["pair_label"]))
    return pairs


def build_heatmap_cards(
    framework: str = "All Frameworks",
    scope: str = "All Applications",
    time_range: str = "Current Month",
    limit: int = 12,
) -> list[dict]:
    matrix = build_readiness_matrix(scope, time_range)
    if framework != "All Frameworks":
        matrix = [r for r in matrix if r["framework"] == framework]
    matrix.sort(key=lambda r: (r["readiness_pct"], -r["open_findings"]))
    cards = []
    for r in matrix[:limit]:
        cards.append({
            **r,
            "title": r["application"],
            "subtitle": f"{r['framework']} Readiness",
            "metric_label": f"{r['framework']} Readiness",
        })
    return cards


def build_trend_series(
    framework: str = "All Frameworks",
    scope: str = "All Applications",
    time_range: str = "Current Month",
) -> dict:
    apps = _apps_in_scope(scope)[:4]
    fws = ALL_FRAMEWORKS if framework == "All Frameworks" else [framework]
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    readiness_evolution = []
    failed_trend = []
    closure_trend = []
    maturity_trend = []
    for m_idx, month in enumerate(months):
        s = _seed(f"trend-{month}-{framework}-{scope}-{time_range}")
        avg_ready = 0
        avg_failed = 0
        avg_closure = 0
        avg_maturity = 0
        count = 0
        for app in apps:
            for fw in fws[:3]:
                r = _readiness(app, fw, time_range)
                drift = (m_idx - 2.5) * (2 if r["trend"] == "Improving" else (-2 if r["trend"] == "Declining" else 0))
                avg_ready += max(40, min(98, r["readiness_pct"] + int(drift)))
                avg_failed += max(0, r["failed_controls"] + (2 - m_idx // 2))
                avg_closure += 3 + (s % 5) + m_idx
                avg_maturity += r["audit_maturity"] + int(drift / 2)
                count += 1
        if count:
            readiness_evolution.append({"month": month, "value": round(avg_ready / count, 1)})
            failed_trend.append({"month": month, "value": round(avg_failed / count, 1)})
            closure_trend.append({"month": month, "value": round(avg_closure / count, 1)})
            maturity_trend.append({"month": month, "value": round(avg_maturity / count, 1)})
    return {
        "readiness_evolution": readiness_evolution,
        "failed_controls_trend": failed_trend,
        "observation_closure_trend": closure_trend,
        "framework_maturity_trend": maturity_trend,
    }


def build_comparison_dashboard(
    framework: str = "All Frameworks",
    scope: str = "All Applications",
    time_range: str = "Current Month",
) -> dict:
    matrix = build_readiness_matrix(scope, time_range)
    if framework != "All Frameworks":
        matrix = [r for r in matrix if r["framework"] == framework]
    pairs = build_pair_comparisons(framework, scope, time_range)
    cards = build_heatmap_cards(framework, scope, time_range, limit=15)
    trends = build_trend_series(framework, scope, time_range)
    avg_ready = round(sum(r["readiness_pct"] for r in matrix) / max(len(matrix), 1), 1)
    critical = len([r for r in matrix if r["readiness_pct"] < 60])
    improving = len([r for r in matrix if r["trend"] == "Improving"])
    return {
        "framework": framework,
        "scope": scope,
        "time_range": time_range,
        "comparison_pairs": pairs,
        "heatmap_cards": cards,
        "readiness_matrix": matrix,
        "trends": trends,
        "kpis": [
            {"label": "Apps in Scope", "value": len(_apps_in_scope(scope)), "tone": "primary"},
            {"label": "Avg Readiness", "value": f"{avg_ready}%", "tone": "success" if avg_ready >= 75 else "warning"},
            {"label": "Critical Postures", "value": critical, "tone": "danger"},
            {"label": "Improving Trends", "value": improving, "tone": "info"},
        ],
    }


def build_comparison_dataset(role: str = "owner") -> dict:
    """Compact dataset — client derives pairs/cards from readiness matrices."""
    from modules.shared.services.role_filter_scope import apply_role_scope

    matrices = {}
    for scope in COMPARE_SCOPES:
        for tr in TIME_RANGES:
            matrices[f"{scope}|{tr}"] = apply_role_scope(build_readiness_matrix(scope, tr), role)
    return {
        "role": role,
        "scopes": COMPARE_SCOPES,
        "time_ranges": TIME_RANGES,
        "frameworks": ["All Frameworks"] + ALL_FRAMEWORKS,
        "matrices": matrices,
    }
