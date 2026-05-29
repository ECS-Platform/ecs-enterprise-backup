"""GRC module demo service — Risk Register & Governance Analytics presentation layer."""

from __future__ import annotations

from app.grc_module_demo import (
    build_governance_analytics_demo,
    build_risk_register_demo,
    drill_governance_analytics,
    drill_risk_register,
)


def build_risk_register_demo_view(role: str) -> dict:
    return build_risk_register_demo(role)


def build_governance_analytics_demo_view(role: str, filters: dict | None = None) -> dict:
    view = build_governance_analytics_demo(role, filters)
    view["monthly_trends"] = view["intel"]["observations"]["series"]
    view["rejection_trends"] = view["intel"]["rejection_rate"]["series"]
    view["sla_trends"] = view["intel"]["sla_compliance"]["series"]
    view["implementation_coverage"] = view["intel"]["implementation_coverage"]
    view["rejection_analytics"] = view["intel"]["rejection_rate"]
    view["sla_analytics"] = view["intel"]["sla_compliance"]
    return view


def risk_drill(metric: str, item_id: str = "", role: str = "owner") -> dict:
    return drill_risk_register(metric, item_id, role)


def governance_drill(metric: str, item_id: str = "", role: str = "cio") -> dict:
    return drill_governance_analytics(metric, item_id, role)
