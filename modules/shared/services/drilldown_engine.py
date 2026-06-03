"""Global ECS drilldown engine — wraps universal drill with metric trace explainability."""

from __future__ import annotations

from typing import Any

from modules.shared.drilldowns.ecs_universal_drill_engine import (
    drill_enterprise_workflow,
    drill_universal_chart,
    drill_universal_kpi,
    drill_universal_row,
    parse_display_count,
)
from modules.shared.services.metric_trace_service import build_metric_trace


def _attach_trace(body: dict[str, Any], *, metric: str, page: str, label: str, count: int, framework: str, role: str) -> dict[str, Any]:
    trace = build_metric_trace(
        metric=metric,
        page=page,
        label=label or body.get("title", metric),
        count=count or body.get("trace_count") or len(body.get("rows", [])),
        framework=framework,
        role=role,
        display_value=str(body.get("trace_count", count)) if count else "",
    )
    body["metric_trace"] = trace
    body.setdefault("detail", {})
    if isinstance(body["detail"], dict):
        body["detail"].update({
            "metric_name": trace["metric_name"],
            "formula": trace["calculation_formula"]["formula_text"],
            "result": trace["calculation_formula"]["result"],
        })
    return body


def drill_kpi(
    page: str,
    metric: str,
    *,
    count: int = 0,
    role: str = "cio",
    framework: str = "",
    label: str = "",
) -> dict[str, Any]:
    body = drill_universal_kpi(page, metric, count=count, role=role, framework=framework, label=label)
    return _attach_trace(body, metric=metric, page=page, label=label, count=count, framework=framework, role=role)


def drill_row(
    page: str,
    row_type: str,
    row_id: str,
    *,
    role: str = "cio",
    framework: str = "",
) -> dict[str, Any]:
    body = drill_universal_row(page, row_type, row_id, role=role, framework=framework)
    return _attach_trace(body, metric=row_type, page=page, label=row_id, count=len(body.get("rows", [])), framework=framework, role=role)


def drill_chart(
    page: str,
    chart: str,
    element: str,
    *,
    count: int = 0,
    role: str = "cio",
    framework: str = "",
) -> dict[str, Any]:
    body = drill_universal_chart(page, chart, element, count=count, role=role)
    metric = f"{chart}_{element}".lower().replace(" ", "_")
    return _attach_trace(body, metric=metric, page=page, label=f"{chart} — {element}", count=count, framework=framework, role=role)


def drill_workflow(role: str, metric: str, count: int = 0) -> dict[str, Any]:
    body = drill_enterprise_workflow(role, metric, count)
    return _attach_trace(body, metric=metric, page="enterprise", label=metric, count=count, framework="", role=role)


def drill_heatmap_cell(
    application: str,
    framework: str,
    readiness_pct: str | float,
    *,
    role: str = "cio",
) -> dict[str, Any]:
    """Framework readiness heatmap cell — controls, observations, evidence, gaps."""
    count = parse_display_count(readiness_pct)
    page = "framework"
    metric = f"heatmap_{application}_{framework}".lower().replace(" ", "_")
    body = drill_universal_kpi(page, metric, count=count, role=role, framework=framework, label=f"{application} · {framework}")
    trace = build_metric_trace(
        metric=metric,
        page=page,
        label=f"{application} — {framework} Readiness",
        count=count,
        framework=framework,
        role=role,
        display_value=f"{readiness_pct}%" if "%" not in str(readiness_pct) else str(readiness_pct),
    )
    trace["contributing_applications"] = [application]
    body["metric_trace"] = trace
    body["title"] = f"{application} · {framework} · {readiness_pct}% Readiness"
    body["heatmap_context"] = {
        "application": application,
        "framework": framework,
        "readiness_pct": readiness_pct,
        "controls": trace["contributing_controls"],
        "observations": trace["related_observations"],
        "evidence": trace["contributing_evidence"],
        "gaps": trace["gaps"],
    }
    return body


def drill_metric(
    scope: str,
    *,
    page: str = "",
    metric: str = "",
    chart: str = "",
    element: str = "",
    row_type: str = "",
    row_id: str = "",
    count: int = 0,
    role: str = "cio",
    framework: str = "",
    label: str = "",
    application: str = "",
    readiness_pct: str = "",
) -> dict[str, Any]:
    """Single entry point for all drill scopes."""
    scope = (scope or "kpi").lower()
    if scope == "heatmap":
        return drill_heatmap_cell(application or element, framework, readiness_pct or count, role=role)
    if scope == "row":
        return drill_row(page, row_type or "record", row_id, role=role, framework=framework)
    if scope == "chart":
        return drill_chart(page, chart or "chart", element or metric, count=count, role=role, framework=framework)
    if scope == "workflow":
        return drill_workflow(role, metric, count)
    if not metric and not label:
        return {"ok": False, "error": "metric required"}
    return drill_kpi(page, metric or label, count=count, role=role, framework=framework, label=label)
