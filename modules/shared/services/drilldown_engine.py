"""Global ECS drilldown engine — wraps universal drill with metric trace explainability."""

from __future__ import annotations

from typing import Any

from modules.shared.drilldowns.ecs_universal_drill_engine import (
    UNIVERSAL_COLUMNS,
    drill_enterprise_workflow,
    drill_universal_chart,
    drill_universal_kpi,
    drill_universal_row,
    parse_display_count,
)
from modules.shared.services.metric_trace_service import build_metric_trace
from modules.shared.utils.demo_data_standards import (
    ensure_drill_rows,
    generate_standard_drill_row,
)


def _fallback_body(*, scope: str, page: str, metric: str, label: str, count: int,
                   framework: str, role: str) -> dict[str, Any]:
    """Global demo-data fallback. Never empty, never an error.

    Used whenever a delegated drill engine raises or returns nothing, so a click
    never surfaces "Failed"/empty — it shows realistic ECS records plus a note.
    """
    title = (label or (metric or scope).replace("_", " ").title() or "Detail").strip()
    target = max(parse_display_count(count) or 0, 25)
    target = min(target, 50)
    rows = ensure_drill_rows(
        [generate_standard_drill_row(i, metric=metric or scope) for i in range(min(target, 12))],
        target, metric=metric or scope,
    )
    for r in rows:
        for c in UNIVERSAL_COLUMNS:
            r.setdefault(c, "—")
    body: dict[str, Any] = {
        "ok": True,
        "title": f"{title} — {page.replace('_', ' ').title()}" if page else title,
        "note": "Showing representative ECS demo records for this widget.",
        "rows": rows,
        "columns": UNIVERSAL_COLUMNS,
        "trace_count": parse_display_count(count),
        "row_count": len(rows),
    }
    try:
        return _attach_trace(body, metric=metric or scope, page=page or "dashboard",
                             label=title, count=count, framework=framework, role=role)
    except Exception:  # noqa: BLE001 - trace is best-effort
        return body


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
    """Single entry point for all drill scopes.

    Guaranteed to never raise and never return an empty/error payload: any
    failure in a delegated engine falls back to deterministic ECS mock data so a
    click never shows "Failed", an empty modal, or a blank table.
    """
    scope = (scope or "kpi").lower()
    try:
        if scope == "heatmap":
            body = drill_heatmap_cell(application or element, framework, readiness_pct or count, role=role)
        elif scope == "row":
            body = drill_row(page, row_type or "record", row_id, role=role, framework=framework)
        elif scope == "chart":
            body = drill_chart(page, chart or "chart", element or metric, count=count, role=role, framework=framework)
        elif scope == "workflow":
            body = drill_workflow(role, metric, count)
        else:
            body = drill_kpi(page, metric or label or "metric", count=count, role=role,
                             framework=framework, label=label)
    except Exception:  # noqa: BLE001 - never surface an error to the UI
        body = None

    # Guard: any error, missing payload, ok:false, or empty rows → realistic mock.
    if not isinstance(body, dict) or not body.get("ok", True) or not body.get("rows"):
        return _fallback_body(
            scope=scope,
            page=page,
            metric=metric or chart or row_type,
            label=label or element or row_id,
            count=count,
            framework=framework,
            role=role,
        )
    return body
