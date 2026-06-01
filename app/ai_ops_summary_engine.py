"""AI Ops Assistant summary drill pages — Business, Technical, Executive views."""

from __future__ import annotations

from app.demo_data_standards import DRILL_COLUMNS, ensure_drill_rows, generate_standard_drill_row
from app.operations_intelligence import OUTAGE_SCENARIOS

SUMMARY_PAGE_MODES = ("business", "technical", "executive", "audit", "compliance", "evidence", "incident", "root_cause")

RECOMMENDATIONS = {
    "business": [
        "Issue customer advisory on login delays and transaction confirmation times",
        "Escalate to business continuity coordinator for retail channel impact",
        "Prepare regulator notification draft if outage exceeds 4 hours",
    ],
    "technical": [
        "Validate DB replication and failover consistency on CBS cluster",
        "Close Tripwire baseline drift on authentication middleware",
        "Expedite ITPP DR validation and incident timeline evidence upload",
    ],
    "executive": [
        "Brief CIO steering on moderate customer impact with no data compromise",
        "Track PCI DSS and RBI Cyber incident reporting thresholds",
        "Monitor compensating controls for active TD exception on failover cluster",
    ],
}


def _scenario_rows(scenario: dict, scenario_key: str, mode: str) -> list[dict]:
    app = scenario["application"]
    base = []
    for i, sig in enumerate(scenario.get("correlated_signals", [])[:8]):
        base.append({
            "application": app,
            "framework": "ITPP" if "DR" in sig or "ITPP" in sig else pick_fw(sig),
            "domain": "Operations",
            "control": scenario.get("governance_observations", ["—"])[i % max(len(scenario.get("governance_observations", [1])), 1)],
            "owner": "Infrastructure Lead" if i % 2 else "App Owner",
            "status": scenario["status"],
            "risk": scenario["severity"],
            "evidence": f"INC-EVD-{scenario_key[:3].upper()}-{i:03d}",
            "finding": sig,
            "date": scenario.get("timeline", [["2026-05-24", ""]])[min(i, len(scenario.get("timeline", [])) - 1)][0],
        })
    for obs in scenario.get("governance_observations", []):
        base.append(generate_standard_drill_row(len(base), metric=mode, application=app))
        base[-1]["finding"] = obs
        base[-1]["control"] = obs[:60]
    for action in scenario.get("recommended_actions", []):
        base.append(generate_standard_drill_row(len(base), metric=mode, application=app))
        base[-1]["finding"] = f"Recommendation: {action}"
    return ensure_drill_rows(base, 25, metric=mode)


def pick_fw(text: str) -> str:
    for fw in ("PCI DSS", "DPSC", "VAPT", "DB Baselining", "ITPP", "AppSec"):
        if fw.lower() in text.lower():
            return fw
    return "Enterprise-wide"


def build_summary_page(mode: str, scenario_key: str = "net_banking", role: str = "cio") -> dict | None:
    if mode not in SUMMARY_PAGE_MODES:
        return None
    scenario = OUTAGE_SCENARIOS.get(scenario_key) or OUTAGE_SCENARIOS.get("net_banking")
    titles = {
        "business": "Business Summary",
        "technical": "Technical Summary",
        "executive": "Executive Summary",
        "audit": "Audit Summary",
        "compliance": "Compliance Summary",
        "evidence": "Evidence Summary",
        "incident": "Incident Summary",
        "root_cause": "Root Cause Analysis",
    }
    rows = _scenario_rows(scenario, scenario_key, mode)
    related_apps = list({r["application"] for r in rows}) + scenario.get("impacted_apps", [])
    related_fws = list({r["framework"] for r in rows if r["framework"] != "Enterprise-wide"})
    return {
        "title": f"{titles.get(mode, mode.title())} — {scenario['application']}",
        "subtitle": scenario.get("customer_impact", ""),
        "mode": mode,
        "scenario_key": scenario_key,
        "scenario": scenario,
        "columns": [{"key": c, "label": c.replace("_", " ").title(), "wrap": c in ("application", "control", "finding")} for c in DRILL_COLUMNS],
        "rows": rows,
        "recommendations": RECOMMENDATIONS.get(mode, scenario.get("recommended_actions", [])),
        "related_applications": related_apps[:8],
        "related_frameworks": related_fws[:8],
        "related_controls": [r["control"] for r in rows[:8]],
        "role": role,
    }
