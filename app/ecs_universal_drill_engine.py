"""Platform-wide universal drill engine — traceable mock data for every KPI, row, and chart."""

from __future__ import annotations

import re
from typing import Any

from app.demo_data_standards import (
    AUDIT_ACTIONS,
    AUDIT_ACTORS,
    BANKING_APPLICATIONS,
    BANKING_OWNERS,
    DOMAINS,
    FRAMEWORKS,
    ensure_drill_rows,
    generate_audit_trail,
    generate_standard_drill_row,
    pick,
    seed,
    between,
)

UNIVERSAL_COLUMNS = [
    "application", "framework", "domain", "control", "evidence", "observation",
    "finding", "owner", "reviewer", "status", "risk", "created_date", "updated_date",
]

AUDIT_HISTORY_COLUMNS = [
    "user", "role", "timestamp", "previous_status", "new_status", "comments",
]

WORKFLOW_STATUSES = [
    "Draft",
    "Pending App Owner Approval",
    "Pending Auditor Approval",
    "Rejected By App Owner",
    "Rejected By Auditor",
    "Needs Rework",
    "Closed",
]

_ROLES = [
    "CIO", "Vertical Head", "Functional Head", "Application Owner",
    "Auditor", "Compliance Officer", "Security Officer", "Framework Owner",
]


def parse_display_count(value: Any) -> int:
    """Extract integer count from KPI display values like '79', '73.4%', '307'."""
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return max(int(value), 0)
    text = str(value).strip()
    m = re.search(r"(\d+)", text.replace(",", ""))
    return int(m.group(1)) if m else 0


def _target_rows(count: int, *, minimum: int = 25) -> int:
    """Traceability: match displayed count when >= minimum, else pad to minimum."""
    c = parse_display_count(count)
    if c >= minimum:
        return min(c, 50)
    return minimum


def _generate_universal_row(index: int, *, metric: str = "", page: str = "", application: str = "") -> dict[str, Any]:
    base = generate_standard_drill_row(index, metric=metric, application=application)
    s = seed("univ", page, metric, index)
    base.update({
        "observation": f"OBS-{pick(s, ['PCI', 'VAPT', 'APP', 'RBI'])[:3]}-{index + 1:04d}",
        "reviewer": pick(s >> 2, ["S. Nair (Auditor)", "Internal Audit", "Compliance Head"]),
        "created_date": f"2026-0{(index % 4) + 1}-{(index % 25) + 1:02d}",
        "updated_date": f"2026-05-{(index % 20) + 1:02d}",
        "finding": base.get("finding") or f"Finding — {base['application']}",
    })
    return base


def _audit_history_section(count: int = 12, *, prefix: str = "") -> list[dict[str, Any]]:
    from datetime import date

    rows: list[dict[str, Any]] = []
    for i, ev in enumerate(generate_audit_trail(count, date(2026, 5, 29))):
        prev = pick(seed(prefix, i, "prev"), WORKFLOW_STATUSES)
        new = pick(seed(prefix, i, "new"), WORKFLOW_STATUSES)
        rows.append({
            "user": ev["actor"],
            "role": pick(seed(i, "role"), _ROLES),
            "timestamp": ev["timestamp"],
            "previous_status": prev,
            "new_status": new,
            "comments": ev["detail"],
        })
    return rows


def _sections(rows: list[dict], metric: str) -> dict[str, list[dict]]:
    app = rows[0]["application"] if rows else pick(seed(metric), BANKING_APPLICATIONS)
    return {
        "approval_history": ensure_drill_rows(
            [_generate_universal_row(i, metric="approval", page=metric) for i in range(8)],
            10, metric="approval",
        ),
        "audit_history": _audit_history_section(10, prefix=metric),
        "related_controls": ensure_drill_rows(
            [_generate_universal_row(i, metric="ctrl", application=app) for i in range(6)],
            10, metric="ctrl",
        ),
        "related_evidence": ensure_drill_rows(
            [_generate_universal_row(i, metric="evd", application=app) for i in range(6)],
            10, metric="evd",
        ),
        "related_findings": ensure_drill_rows(
            [_generate_universal_row(i, metric="fnd", application=app) for i in range(6)],
            10, metric="fnd",
        ),
    }


def _normalize_columns(rows: list[dict]) -> None:
    for r in rows:
        for c in UNIVERSAL_COLUMNS:
            r.setdefault(c, "—")


def _delegate_kpi(page: str, metric: str, role: str, framework: str, count: int) -> dict[str, Any] | None:
    page_l = (page or "").lower().replace("-", "_")
    metric_l = (metric or "").lower().replace("-", "_").replace(" ", "_")

    if page_l in ("demo", "demo_overview", "executive") or metric_l in (
        "applications", "frameworks", "controls", "evidence", "findings", "vapt", "tickets", "incidents",
    ):
        from app.demo_kpi_drill_engine import drill_demo_kpi
        body = drill_demo_kpi(metric_l or metric)
        target = _target_rows(count)
        body["rows"] = ensure_drill_rows(body.get("rows", []), target, metric=metric_l)
        return body

    if framework:
        from app.framework_catalog import resolve_framework_name
        fw = resolve_framework_name(framework)
        if metric_l in ("draft", "submitted", "reupload", "auditor_approved", "approval_rate",
                        "avg_review_time", "rejection_trend", "pending_aging", "findings",
                        "controls", "applications_covered", "readiness_score"):
            from app.framework_workflow_engine import drill_framework_workflow
            body = drill_framework_workflow(fw, metric_l)
            target = _target_rows(count)
            body["rows"] = ensure_drill_rows(body.get("rows", []), target, metric=metric_l)
            return body
        from app.framework_kpi_drill_engine import drill_framework_kpi
        body = drill_framework_kpi(fw, metric_l or metric)
        target = _target_rows(count)
        body["rows"] = ensure_drill_rows(body.get("rows", []), target, metric=metric_l)
        return body

    if page_l.startswith("grc") or page_l in ("risk_register", "governance_analytics", "cmdb", "regulatory", "correlation", "heatmaps", "exceptions"):
        from app.grc_module_demo import drill_governance_analytics, drill_risk_register
        if "risk" in page_l or metric_l.startswith("risk"):
            body = drill_risk_register(metric_l or "open_risks")
        else:
            body = drill_governance_analytics(metric_l or metric)
        target = _target_rows(count)
        rows = body.get("rows") or []
        body = {
            "ok": True,
            "title": body.get("title") or metric.replace("_", " ").title(),
            "rows": ensure_drill_rows(rows, target, metric=metric_l),
            "columns": UNIVERSAL_COLUMNS,
        }
        return body

    if page_l.startswith("ai_sdlc") or page_l in ("control_tower", "sdlc_gates", "ai_governance", "ai_registry"):
        from app.ai_sdlc_governance_mock import drill_posture, drill_registry, drill_sdlc
        if "registry" in metric_l or "registry" in page_l:
            body = drill_registry(metric_l or "applications")
        elif "sdlc" in metric_l or "gate" in page_l:
            body = drill_sdlc(metric_l or "findings")
        else:
            body = drill_posture(metric_l or "readiness")
        target = _target_rows(count)
        body["rows"] = ensure_drill_rows(body.get("rows", []), target, metric=metric_l)
        body["ok"] = True
        return body

    if page_l in ("audit_prep", "audit-prep"):
        from app.audit_schedule_engine import build_kpi_drilldowns
        drills = build_kpi_drilldowns()
        block = drills.get(metric_l) or drills.get(metric) or {}
        rows = block.get("rows") or []
        target = _target_rows(count)
        return {
            "ok": True,
            "title": block.get("title") or metric.replace("_", " ").title(),
            "rows": ensure_drill_rows(rows, target, metric=metric_l),
            "columns": block.get("columns") or UNIVERSAL_COLUMNS,
        }

    if page_l and page_l not in ("dashboard", "enterprise", ""):
        from app.module_kpi_drill_engine import drill_module_kpi
        body = drill_module_kpi(page_l.replace("mvp_", ""), metric_l or metric, role)
        target = _target_rows(count)
        body["rows"] = ensure_drill_rows(body.get("rows", []), target, metric=metric_l)
        return body

    return None


def drill_universal_kpi(
    page: str,
    metric: str,
    *,
    count: int = 0,
    role: str = "cio",
    framework: str = "",
    label: str = "",
) -> dict[str, Any]:
    delegated = _delegate_kpi(page, metric, role, framework, count)
    if delegated:
        delegated.setdefault("columns", UNIVERSAL_COLUMNS)
        _normalize_columns(delegated.get("rows", []))
        delegated.setdefault("sections", _sections(delegated.get("rows", []), metric))
        delegated["trace_count"] = parse_display_count(count)
        delegated["row_count"] = len(delegated.get("rows", []))
        return delegated

    target = _target_rows(count)
    rows = ensure_drill_rows(
        [_generate_universal_row(i, metric=metric, page=page) for i in range(min(target, 12))],
        target, metric=metric,
    )
    _normalize_columns(rows)
    title = label or metric.replace("_", " ").title() or "Detail"
    return {
        "ok": True,
        "title": f"{title} — {page.replace('_', ' ').title() if page else 'ECS'}",
        "rows": rows,
        "columns": UNIVERSAL_COLUMNS,
        "sections": _sections(rows, metric),
        "trace_count": parse_display_count(count),
        "row_count": len(rows),
    }


def drill_universal_row(
    page: str,
    row_type: str,
    row_id: str,
    *,
    role: str = "cio",
    framework: str = "",
) -> dict[str, Any]:
    if framework:
        from app.ecs_row_drill_engine import drill_framework_row
        body = drill_framework_row(framework, row_type, row_id)
        body["sections"]["audit_history"] = _audit_history_section(10, prefix=row_id)
        body["sections"]["approval_history"] = body["sections"].get("related_audit_history", [])
        return body

    rows = ensure_drill_rows(
        [_generate_universal_row(i, metric=f"{page}:{row_type}", page=page) for i in range(12)],
        25, metric=row_type,
    )
    _normalize_columns(rows)
    detail = {
        "page": page,
        "row_type": row_type,
        "row_id": row_id or rows[0]["application"],
        "application": row_id or rows[0]["application"],
        "framework": pick(seed(row_id), FRAMEWORKS),
        "owner": pick(seed(row_id, "o"), BANKING_OWNERS),
        "reviewer": pick(seed(row_id, "r"), ["S. Nair (Auditor)", "Internal Audit"]),
        "status": pick(seed(row_id, "s"), WORKFLOW_STATUSES),
        "risk": pick(seed(row_id, "k"), ["Critical", "High", "Medium", "Low"]),
        "observation": f"OBS-{row_id[:8].upper().replace(' ', '') if row_id else 'GEN'}-001",
    }
    return {
        "ok": True,
        "title": f"{row_type.replace('_', ' ').title()}: {row_id or 'Record'}",
        "detail": detail,
        "rows": rows,
        "columns": UNIVERSAL_COLUMNS,
        "sections": _sections(rows, f"{page}:{row_type}"),
    }


def drill_universal_chart(
    page: str,
    chart: str,
    element: str,
    *,
    count: int = 0,
    role: str = "cio",
) -> dict[str, Any]:
    metric = f"{chart}_{element}".lower().replace(" ", "_").replace("-", "_")
    return drill_universal_kpi(page, metric, count=count, role=role, label=f"{chart} — {element}")


def drill_enterprise_workflow(role: str, metric: str, count: int = 0) -> dict[str, Any]:
    from app.evidence_workflow_engine import drill_workflow_metric

    body = drill_workflow_metric(role, metric, count)
    target = _target_rows(count)
    body["rows"] = ensure_drill_rows(body.get("rows", []), target, metric=metric)
    body["sections"] = _sections(body["rows"], metric)
    body["trace_count"] = parse_display_count(count)
    body["row_count"] = len(body["rows"])
    return body
