"""Module KPI drilldown API — supporting data for workspace executive KPI strips."""

from __future__ import annotations

from modules.shared.utils.demo_data_standards import DRILL_COLUMNS, ensure_drill_rows, generate_standard_drill_row
from modules.shared.services.module_capabilities import get_module_capability


def _normalize_row(row: dict | str | list, module: str) -> dict:
    if isinstance(row, str):
        out = {"application": row, "framework": "Enterprise-wide", "control": "—", "status": "Active"}
        src: dict = out
    elif isinstance(row, dict):
        out = dict(row)
        src = out
    else:
        out = {"application": str(row), "framework": "Enterprise-wide", "control": "—", "status": "Open"}
        src = out
    out.setdefault("application", src.get("application") or src.get("app") or src.get("name") or "—")
    out.setdefault("framework", src.get("framework") or src.get("framework_name") or "Enterprise-wide")
    out.setdefault("domain", src.get("domain") or "Governance")
    out.setdefault("control", src.get("control") or src.get("control_id") or src.get("control_name") or "—")
    out.setdefault("evidence", src.get("evidence") or src.get("evidence_name") or src.get("filename") or "—")
    out.setdefault("finding", src.get("finding") or src.get("finding_id") or src.get("summary") or "—")
    out.setdefault("owner", src.get("owner") or src.get("uploaded_by") or src.get("assigned_to") or "—")
    out.setdefault("status", src.get("status") or src.get("evidence_status") or src.get("job_status") or "Open")
    out.setdefault("risk", src.get("risk") or src.get("risk_rating") or src.get("severity") or "Medium")
    out.setdefault("date", src.get("date") or src.get("last_updated") or src.get("uploaded_at") or "2026-05-24")
    out["module"] = module
    return out


def _pick_rows(view: dict, metric: str) -> list[dict]:
    m = metric.lower().replace("-", "_").replace(" ", "_")
    rows = view.get("rows") or []

    keyed = {
        "failed": view.get("failed_jobs") or view.get("scheduler_failures") or [],
        "scan": view.get("application_scans") or [],
        "upload": view.get("tracker_rows") or view.get("upload_rows") or [],
        "pending": view.get("pending_rows") or view.get("stale_rows") or [],
        "risk": view.get("high_risk_controls") or view.get("open_findings") or [],
        "exception": view.get("expired") or view.get("pending_cab") or [],
        "integration": view.get("connector_rows") or [],
        "onboard": view.get("onboarding_apps") or [],
        "incident": view.get("incident_rows") or [],
    }
    for key, candidates in keyed.items():
        if key in m and candidates:
            return candidates

    if "fail" in m or "error" in m or "reject" in m:
        filtered = [r for r in rows if str(r.get("status", "")).lower() in ("failed", "rejected", "partial", "delayed", "error")]
        if filtered:
            return filtered
    if "approv" in m or "success" in m or "valid" in m:
        filtered = [r for r in rows if str(r.get("status", "")).lower() in ("approved", "completed", "healthy", "success")]
        if filtered:
            return filtered
    if "pending" in m or "open" in m or "await" in m or "finding" in m:
        filtered = [r for r in rows if str(r.get("status", "")).lower() in ("pending", "open", "submitted", "under review", "draft")]
        if filtered:
            return filtered

    extras = []
    for key in (
        "application_scans", "failed_jobs", "scheduler_failures", "tracker_rows",
        "pending_rows", "stale_rows", "high_risk_controls", "open_findings",
        "onboarding_apps", "chains", "variance_rows", "missing_evidence_rows", "incident_rows",
    ):
        extras.extend(view.get(key) or [])
    if extras:
        return extras
    return rows


def drill_module_kpi(module: str, metric: str, role: str = "cio") -> dict:
    if module == "predefined_queries":
        # Authoritative, traceable KPI drilldowns sourced directly from the
        # control library — never generic/padded/fabricated rows.
        from modules.operations.engines.predefined_queries_engine import drill_predefined_query_kpi

        return drill_predefined_query_kpi(metric or "total_controls", role)

    if module == "trends":
        from modules.governance.engines.trends_drill_engine import drill_trends_kpi
        from modules.shared.drilldowns.ecs_universal_drill_engine import parse_display_count

        body = drill_trends_kpi(metric or "implementation_coverage", role, count=25)
        body["columns"] = body.get("columns") or DRILL_COLUMNS
        body["trace_count"] = parse_display_count(body.get("detail", {}).get("coverage_pct", 25))
        return body

    if module == "reports":
        from modules.executive_overview.engines.reports_drill_engine import drill_reports_kpi

        body = drill_reports_kpi(metric or "available_reports", role, count=25)
        body["columns"] = body.get("columns") or DRILL_COLUMNS
        return body

    view = get_module_capability(module, role)
    raw = _pick_rows(view, metric or "summary")
    normalized = [_normalize_row(r, module) for r in raw]
    if not normalized:
        normalized = [_normalize_row(generate_standard_drill_row(i, metric=metric), module) for i in range(25)]
    rows = ensure_drill_rows(normalized, 25, metric=metric or module)
    title = metric.replace("_", " ").title() if metric else module.replace("_", " ").title()
    return {
        "ok": True,
        "title": f"{title} — {module.replace('_', ' ').title()}",
        "rows": rows,
        "columns": DRILL_COLUMNS,
    }
