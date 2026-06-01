"""Governance context engine — delegates to relational governance graph."""

from __future__ import annotations

from typing import Any

from modules.frameworks.engines.control_validation_engine import build_control_validations, validation_summary
from modules.frameworks.engines.framework_catalog import get_framework_controls
from modules.frameworks.engines.framework_governance_data import get_framework_profile
from modules.frameworks.engines.framework_trends_engine import build_framework_trends_analytics
from modules.governance.engines.governance_relational_model import build_relational_view, get_framework_graph


DEFINITIONS = {
    "open_findings": "Individual observations or issues detected (e.g. SSRF, missing patch). Not the same as failed controls.",
    "failed_controls": "Governance controls whose implementation validation failed. One failed control may generate many findings.",
    "validation_checks": "Automated validation runs (config, evidence, policy, SLA). One control may produce PASS/WARN/FAIL across multiple checks.",
}


def _enrich_validation_summary(framework_name: str) -> dict[str, Any]:
    rows = build_control_validations(framework_name, limit=500)
    passed = sum(1 for r in rows if r["status"] == "PASS")
    failed = sum(1 for r in rows if r["status"] == "FAIL")
    warned = sum(1 for r in rows if r["status"] == "WARN")
    total = len(rows) or 1
    g = get_framework_graph(framework_name)
    controls = g["controls"] or get_framework_controls(framework_name)
    apps = g["applications"]
    return {
        "total_checks": total,
        "passed": passed,
        "warned": warned,
        "failed": failed,
        "effectiveness_pct": round((passed / total) * 100, 1),
        "failed_control_ids": list({c["control_id"] for c in g["controls"] if c.get("validation") == "FAIL"}),
        "scope_label": f"Across {len(controls)} {framework_name} controls and {len(apps)} applications",
        "aggregation_type": "validation_checks",
        "explanation": DEFINITIONS["validation_checks"],
        "control_count": len(controls),
        "application_count": len(apps),
    }


def build_governance_context(framework_name: str, catalog_controls: list[dict] | None = None) -> dict[str, Any]:
    """Full governance context — relational graph + validation semantics."""
    profile = get_framework_profile(framework_name)
    rel = build_relational_view(framework_name)
    val = _enrich_validation_summary(framework_name)
    trends = rel.get("trends", {})
    apps = rel["applications"]

    return {
        "definitions": DEFINITIONS,
        "scope": {
            "framework": framework_name,
            "context_label": profile.get("context_label", ""),
            "description": profile.get("framework_description", ""),
            "application_count": len(apps),
            "control_count": len(rel["controls"]),
            "aggregation_notes": {
                "open_findings": "Individual observations/issues — may map to one control",
                "failed_controls": "Governance controls that failed implementation validation",
                "validation_checks": "Automated validation runs — one control may produce multiple checks",
            },
        },
        "audit_readiness": rel["audit_readiness"],
        "control_effectiveness": {
            "label": f"Average effectiveness across {len(rel['controls'])} {framework_name} controls",
            "average_pct": val["effectiveness_pct"],
            "by_application": [{"application": a["name"], "pct": a["audit_readiness_pct"], "owner": a.get("owner")} for a in apps],
            "control_count": len(rel["controls"]),
        },
        "open_findings": rel["open_findings"],
        "open_findings_count": len(rel["open_findings"]),
        "failed_controls": rel["failed_controls"],
        "failed_controls_count": len(rel["failed_controls"]),
        "relational_controls": rel["controls"],
        "evidence_repository": rel["evidence"],
        "integrations_detailed": rel["integrations"],
        "framework_exceptions": rel["exceptions"],
        "validation_context": val,
        "risk_contributors": rel["risk_contributors"],
        "pending_actions": rel.get("pending_actions_and_gaps") or rel["pending_actions"],
        "pending_actions_and_gaps": rel.get("pending_actions_and_gaps") or rel["pending_actions"],
        "open_gaps": rel.get("open_gaps") or [],
        "reuse_mappings": rel["reuse_mappings"],
        "trends_context": {
            "label": trends.get("label", f"{framework_name} governance trend"),
            "date_scope": "Jan–Jun 2026",
            "framework": framework_name,
            "application_scope": ", ".join(a["name"] for a in apps),
            "series": trends.get("metrics", profile.get("trends", [])),
            "metric_labels": trends.get("metric_labels", []),
        },
        "trend_analytics": build_framework_trends_analytics(framework_name),
    }
