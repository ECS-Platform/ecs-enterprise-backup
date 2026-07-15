"""Truthful LIVE / DEMO / PARTIAL markers for executive and governance screens."""

from __future__ import annotations

from typing import Any

LIVE = "LIVE"
DEMO = "DEMO"
PARTIAL = "PARTIAL"

_STATUS_LABELS = {
    LIVE: "Live Data",
    DEMO: "Demo Data",
    PARTIAL: "Partial Data",
}


def marker_payload(
    status: str,
    provider: str,
    *,
    live_fields: list[str] | None = None,
    demo_fields: list[str] | None = None,
    note: str = "",
) -> dict[str, Any]:
    """Build a template-ready data-source descriptor."""
    live = live_fields or []
    demo = demo_fields or []
    if status == LIVE:
        tooltip = f"Primary KPIs are sourced from {provider}."
    elif status == DEMO:
        tooltip = f"Deterministic seeded dataset from {provider}."
    else:
        tooltip = (
            f"Mix of workflow/repository metrics and seeded baselines from {provider}."
        )
    if note:
        tooltip = f"{tooltip} {note}"
    return {
        "status": status,
        "label": _STATUS_LABELS[status],
        "tooltip": tooltip.strip(),
        "provider": provider,
        "live_fields": live,
        "demo_fields": demo,
    }


def enterprise_dashboard_data_source() -> dict[str, Any]:
    """Enterprise compliance dashboard — blended workflow + demo baselines."""
    return marker_payload(
        PARTIAL,
        "analytics_module.enterprise_dashboard",
        live_fields=[
            "framework_stats.approved",
            "framework_stats.pending",
            "completeness.missing",
            "applications.compliance_pct",
            "top_rejected",
            "open_observations",
        ],
        demo_fields=[
            "enterprise_compliance_pct",
            "national_score",
            "framework_maturity_display",
            "banking_bu_analytics",
            "audit_readiness_pct",
        ],
        note="National score and BU cards use seeded regional/baseline values.",
    )


def pan_india_posture_data_source() -> dict[str, Any]:
    """Pan-India and cross-region analytics — fully seeded regional posture."""
    return marker_payload(
        DEMO,
        "enterprise_mock_service.build_pan_india_posture",
        demo_fields=[
            "regions",
            "framework_matrix",
            "zone_heatmap",
            "pci_readiness",
            "sla_breaches",
            "critical_observations",
        ],
        note="Cross-region analytics tab shares this regional mock provider.",
    )


def trends_analytics_data_source() -> dict[str, Any]:
    """Compliance trend analysis — enterprise-scale series with live evidence hooks."""
    return marker_payload(
        PARTIAL,
        "trends_analytics_engine.build_trends_tab_payload",
        live_fields=[
            "evidence_aging.expired_count",
            "evidence_aging.due_refresh",
            "total_breaches",
            "control_totals.coverage_pct",
        ],
        demo_fields=[
            "coverage_series",
            "observations_series",
            "rejections_series",
            "sla_series",
            "executive_kpis",
            "granularity_trends",
            "avg_days_to_close",
        ],
        note="Monthly/quarterly trend series and KPI strip use seeded enterprise calendars.",
    )


def reports_overview_data_source() -> dict[str, Any]:
    """Regulatory report center overview — seeded catalog with live export/exception rows."""
    return marker_payload(
        PARTIAL,
        "reports_analytics_engine.build_reports_overview",
        live_fields=[
            "observation_rows.exceptions",
            "recent_activity.dynamic_export",
            "generated_records.dynamic_export",
        ],
        demo_fields=[
            "catalog",
            "reporting_health_kpis",
            "generation_trend",
            "top_downloaded",
            "failed_records",
        ],
        note="Catalog counts and generation trends are deterministic; exports may include live history.",
    )


def ecs_regulatory_report_data_source(report_type: str = "") -> dict[str, Any]:
    """Individual regulatory/audit report table — deterministic drill rows."""
    provider = "ecs_reports_engine.build_report"
    if report_type:
        provider = f"{provider}({report_type})"
    return marker_payload(
        DEMO,
        provider,
        demo_fields=["rows", "coverage_pct", "readiness_gates", "findings"],
        note="Report tables are seeded; export PDFs may blend live enterprise stats separately.",
    )
