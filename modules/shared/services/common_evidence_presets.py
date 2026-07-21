"""Preset common evidence queries — stable IDs, catalogue, structured execution."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app import ecs_state
from modules.governance.engines.missing_evidence_engine import get_all_missing_evidence
from modules.operations.engines import evidence_repository as ops_repo
from modules.shared.services.common_evidence_queries import (
    NO_EVIDENCE_MESSAGE,
    _application_allowed,
    _filter_rows,
    _scope_rows,
    _sort_latest,
    _to_citation,
    collect_persisted_evidence_rows,
    handle_approved_evidence,
    handle_duplicate_attempts,
    handle_latest_evidence,
    handle_missing_evidence,
    handle_pending_app_owner,
    handle_pending_auditor,
    handle_rejected_evidence,
    is_evidence_catalog_query,
    try_deterministic_evidence_query,
    try_rag_evidence_query,
)
from modules.shared.services.role_filter_scope import apps_for_role, normalize_role

EMPTY_SCOPE_MESSAGE = "No matching evidence was found for the selected scope."

APP_ALIASES = {
    "netbanking": "Net Banking",
    "mobilebanking": "Mobile Banking",
    "net banking": "Net Banking",
    "mobile banking": "Mobile Banking",
}


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _normalize_app(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    return APP_ALIASES.get(raw.lower().replace("_", " "), raw)


def _merge_filters(base: dict[str, Any], **ctx: Any) -> dict[str, Any]:
    out = dict(base or {})
    if ctx.get("application"):
        out["application"] = _normalize_app(str(ctx["application"]))
    if ctx.get("framework"):
        out["framework"] = str(ctx["framework"]).strip()
    if ctx.get("control_id"):
        out["control_id"] = str(ctx["control_id"]).strip()
    if ctx.get("run_id"):
        out["run_id"] = str(ctx["run_id"]).strip()
    if ctx.get("limit"):
        out["limit"] = int(ctx["limit"])
    return out


def _open_observations(role: str, filters: dict[str, Any]) -> list[dict]:
    rows = get_all_missing_evidence(role)
    open_statuses = {
        "pending upload", "awaiting app owner", "submitted for review", "open",
        "overdue", "rejected", "in progress", "escalated", "monitoring",
    }
    rows = [r for r in rows if str(r.get("status", "")).lower() in open_statuses or r.get("status") == "Overdue"]
    if filters.get("application"):
        rows = [r for r in rows if r.get("application") == filters["application"]]
    if filters.get("framework"):
        rows = [r for r in rows if r.get("framework") == filters["framework"]]
    if filters.get("severity"):
        sev = str(filters["severity"]).lower()
        rows = [
            r for r in rows
            if sev in str(r.get("observation_severity", "")).lower()
            or sev in str(r.get("risk", "")).lower()
        ]
    if filters.get("overdue_only"):
        rows = [r for r in rows if str(r.get("status", "")).lower() == "overdue" or _is_overdue(r)]
    return rows


def _is_overdue(row: dict) -> bool:
    due = str(row.get("due_date") or "")
    if len(due) < 10:
        return False
    try:
        return datetime.fromisoformat(due[:10]).date() < datetime.now(timezone.utc).date()
    except ValueError:
        return False


def _latest_scheduler_run_id() -> str:
    try:
        from modules.operations.engines.scheduler_module import _execution_history

        if _execution_history:
            return str(_execution_history[0].get("run_id") or "")
    except Exception:  # noqa: BLE001
        pass
    return ""


def _rows_by_run_id(run_id: str, role: str) -> list[dict]:
    rows = _scope_rows(collect_persisted_evidence_rows(), role)
    if not run_id:
        return rows
    filtered = []
    for row in rows:
        meta = row.get("metadata") or {}
        if str(meta.get("scheduler_run_id") or "") == run_id:
            filtered.append(row)
    return filtered


def _structured(
    *,
    title: str,
    rows: list[dict],
    filters: dict[str, Any],
    answer_source: str = "Deterministic",
    intent: str = "",
    citations: list[dict] | None = None,
    empty_message: str = EMPTY_SCOPE_MESSAGE,
) -> dict[str, Any]:
    return {
        "ok": True,
        "query_type": answer_source,
        "answer_source": answer_source,
        "title": title,
        "total_count": len(rows),
        "rows": rows,
        "applied_filters": {k: v for k, v in filters.items() if v not in (None, "", 0)},
        "generated_at": _ts(),
        "citations": citations or [],
        "intent": intent,
        "answer": _render_answer_text(title, rows, answer_source, empty_message=empty_message),
        "empty": not rows,
    }


def _render_answer_text(title: str, rows: list[dict], source: str, *, empty_message: str) -> str:
    if not rows:
        return empty_message
    lines = [f"Query type: {source}", f"Result: {title}", ""]
    for idx, row in enumerate(rows[:10], start=1):
        if row.get("observation_id"):
            lines.append(
                f"{idx}. {row.get('observation_id')} — {row.get('control_id') or row.get('control')}\n"
                f"   Application: {row.get('application', '—')}\n"
                f"   Framework: {row.get('framework', '—')}\n"
                f"   Status: {row.get('status', '—')}\n"
                f"   Severity: {row.get('observation_severity') or row.get('risk', '—')}"
            )
            continue
        eid = row.get("evidence_id") or row.get("filename") or "—"
        view_line = (
            f"   View Evidence: /mvp/scheduler/fetched-evidence/view?evidence_id={eid}"
            if str(eid).startswith("EVD-")
            else f"   Evidence ID: {eid}"
        )
        lines.append(
            f"{idx}. {row.get('filename') or row.get('evidence_name') or eid}\n"
            f"   Source: {row.get('source_type') or row.get('source_connector') or '—'}\n"
            f"   Application: {row.get('application', '—')}\n"
            f"   Framework: {row.get('framework', '—')}\n"
            f"   Control: {row.get('control_id') or row.get('control', '—')}\n"
            f"   Collected: {(row.get('uploaded_at') or row.get('collected_at') or '—')[:19]}\n"
            f"   Status: {row.get('workflow_status') or row.get('status', '—')}\n"
            f"{view_line}"
        )
    if len(rows) > 10:
        lines.append(f"... and {len(rows) - 10} more")
    return "\n".join(lines)


def handle_latest_n(filters: dict[str, Any], role: str) -> dict[str, Any]:
    limit = int(filters.get("limit") or 5)
    rows = _sort_latest(_filter_rows(_scope_rows(collect_persisted_evidence_rows(), role), filters))[:limit]
    cites = [_to_citation(r) for r in rows]
    return _structured(title=f"Last {limit} evidences collected", rows=rows, filters=filters, citations=cites, intent="latest_n")


def handle_evidence_by_framework(filters: dict[str, Any], role: str) -> dict[str, Any]:
    if not filters.get("framework"):
        return _needs_param("framework", ["PCI DSS", "DPSC", "ITPP", "CSITE", "VAPT", "OS Baselining", "DB Baselining"])
    rows = _sort_latest(_filter_rows(_scope_rows(collect_persisted_evidence_rows(), role), filters))
    return _structured(
        title=f"Evidence for {filters['framework']}",
        rows=rows[:20],
        filters=filters,
        citations=[_to_citation(r) for r in rows[:20]],
        intent="evidence_by_framework",
    )


def handle_evidence_by_scheduler_run(filters: dict[str, Any], role: str) -> dict[str, Any]:
    run_id = filters.get("run_id") or _latest_scheduler_run_id()
    filters = {**filters, "run_id": run_id}
    rows = _sort_latest(_rows_by_run_id(run_id, role))
    return _structured(
        title=f"Evidence collected in scheduler run {run_id or 'latest'}",
        rows=rows[:20],
        filters=filters,
        citations=[_to_citation(r) for r in rows[:20]],
        intent="evidence_by_scheduler_run",
    )


def handle_failed_collections(filters: dict[str, Any], role: str) -> dict[str, Any]:
    rows: list[dict] = []
    try:
        from modules.operations.engines.scheduler_intelligence import _seed_scheduler_failures

        for item in _seed_scheduler_failures()[:10]:
            rows.append(
                {
                    "failure_id": item.get("failure_id"),
                    "source": item.get("source"),
                    "application": item.get("application", "—"),
                    "framework": item.get("framework", "—"),
                    "status": item.get("retry_status") or item.get("status") or "Failed",
                    "description": item.get("description", ""),
                }
            )
    except Exception:  # noqa: BLE001
        pass
    try:
        from modules.operations.engines.scheduler_module import _execution_history

        for hist in _execution_history[:3]:
            for ev in hist.get("progress_events") or []:
                if ev.get("status") == "Failed":
                    rows.append({"step": ev.get("step"), "status": "Failed", "detail": ev.get("detail"), "run_id": hist.get("run_id")})
    except Exception:  # noqa: BLE001
        pass
    return _structured(title="Failed evidence collections", rows=rows, filters=filters, intent="failed_evidence_collection")


def handle_pending_review(filters: dict[str, Any], role: str) -> dict[str, Any]:
    owner = handle_pending_app_owner(filters, role)
    auditor = handle_pending_auditor(filters, role)
    rows = []
    for block in (owner, auditor):
        if block.get("answer") == NO_EVIDENCE_MESSAGE:
            continue
        for cite in block.get("citations") or []:
            rows.append({**cite, "queue": "owner" if block.get("intent") == "pending_app_owner" else "auditor"})
    return _structured(title="Evidence pending review", rows=rows, filters=filters, citations=rows, intent="evidence_pending_review")


def handle_recently_approved(filters: dict[str, Any], role: str) -> dict[str, Any]:
    result = handle_approved_evidence(filters, role)
    if result.get("answer") in (NO_EVIDENCE_MESSAGE, EMPTY_SCOPE_MESSAGE):
        return _structured(title="Recently approved evidence", rows=[], filters=filters, intent="recently_approved_evidence")
    rows = list(result.get("citations") or [])
    return _structured(title="Recently approved evidence", rows=rows, filters=filters, citations=rows, intent="recently_approved_evidence")


def handle_version_history(filters: dict[str, Any], role: str) -> dict[str, Any]:
    rows = _sort_latest(_filter_rows(_scope_rows(collect_persisted_evidence_rows(), role), filters))
    grouped: dict[str, dict] = {}
    for row in rows:
        key = f"{row.get('application')}::{row.get('control_id') or row.get('control')}"
        if key not in grouped:
            grouped[key] = row
    out = list(grouped.values())[:15]
    return _structured(title="Latest evidence versions by control", rows=out, filters=filters, citations=[_to_citation(r) for r in out], intent="evidence_version_history")


def handle_expiring_evidence(filters: dict[str, Any], role: str) -> dict[str, Any]:
    rows = []
    for rec in _scope_rows(collect_persisted_evidence_rows(), role):
        status = str(rec.get("evidence_status") or rec.get("audit_status") or rec.get("workflow_status") or "")
        if "expir" in status.lower() or "refresh" in status.lower() or "stale" in status.lower():
            rows.append(rec)
    return _structured(title="Evidence expiring or due for refresh", rows=rows[:15], filters=filters, citations=[_to_citation(r) for r in rows[:15]], intent="expiring_evidence")


def handle_latest_open_observations(filters: dict[str, Any], role: str) -> dict[str, Any]:
    rows = _open_observations(role, filters)[: int(filters.get("limit") or 5)]
    return _structured(title="Latest open observations", rows=rows, filters=filters, intent="latest_open_observations")


def handle_high_risk_observations(filters: dict[str, Any], role: str) -> dict[str, Any]:
    filters = {**filters, "severity": "high"}
    rows = _open_observations(role, filters)
    rows = [r for r in rows if str(r.get("risk", "")).lower() in {"critical", "high"}][:15]
    return _structured(title="High-risk open observations", rows=rows, filters=filters, intent="high_risk_open_observations")


def handle_overdue_observations(filters: dict[str, Any], role: str) -> dict[str, Any]:
    rows = _open_observations(role, {**filters, "overdue_only": True})[:15]
    return _structured(title="Overdue observations", rows=rows, filters=filters, intent="overdue_observations")


def handle_observations_by_application(filters: dict[str, Any], role: str) -> dict[str, Any]:
    if not filters.get("application"):
        allowed = apps_for_role(role) or list(APP_ALIASES.values())
        return _needs_param("application", list(allowed)[:6])
    rows = _open_observations(role, filters)[:20]
    return _structured(title=f"Open observations for {filters['application']}", rows=rows, filters=filters, intent="observations_by_application")


def handle_observations_by_framework(filters: dict[str, Any], role: str) -> dict[str, Any]:
    if not filters.get("framework"):
        return _needs_param("framework", ["PCI DSS", "DPSC", "ITPP", "CSITE"])
    rows = _open_observations(role, filters)[:20]
    return _structured(title=f"Open observations for {filters['framework']}", rows=rows, filters=filters, intent="observations_by_framework")


def handle_framework_summary(filters: dict[str, Any], role: str) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for row in _scope_rows(collect_persisted_evidence_rows(), role):
        fw = row.get("framework") or "Cross-Framework"
        counts[fw] = counts.get(fw, 0) + 1
    rows = [{"framework": fw, "evidence_count": cnt} for fw, cnt in sorted(counts.items(), key=lambda x: -x[1])]
    return _structured(title="Evidence count by framework", rows=rows, filters=filters, intent="framework_collection_summary")


def handle_application_summary(filters: dict[str, Any], role: str) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for row in _scope_rows(collect_persisted_evidence_rows(), role):
        app = row.get("application") or "Unknown"
        counts[app] = counts.get(app, 0) + 1
    rows = [{"application": app, "evidence_count": cnt} for app, cnt in sorted(counts.items(), key=lambda x: -x[1])]
    return _structured(title="Evidence count by application", rows=rows, filters=filters, intent="application_collection_summary")


def handle_controls_without_evidence(filters: dict[str, Any], role: str) -> dict[str, Any]:
    return handle_missing_evidence(filters, role)


def handle_common_control_reuse(filters: dict[str, Any], role: str) -> dict[str, Any]:
    rows = []
    for rec in _scope_rows(collect_persisted_evidence_rows(), role):
        meta = rec.get("metadata") or {}
        if meta.get("collection_source") == "CommonControls" or rec.get("source_connector") == "common_controls":
            rows.append({**_to_citation(rec), "reuse_note": "Common control evidence"})
        elif rec.get("reused"):
            rows.append({**_to_citation(rec), "reuse_note": f"Reuse group {rec.get('reuse_group', '')}"})
    try:
        from modules.operations.engines.evidence_repository import evidence_reuse_map

        for group in list(evidence_reuse_map.values())[:5]:
            rows.append({"reuse_group": group.get("group_id"), "filename": group.get("filename"), "linked_controls": len(group.get("linked_controls") or [])})
    except Exception:  # noqa: BLE001
        pass
    return _structured(title="Evidence reused across frameworks", rows=rows[:15], filters=filters, citations=[r for r in rows if r.get("evidence_id")][:10], intent="common_control_reuse")


def handle_pgvector_status(filters: dict[str, Any], role: str) -> dict[str, Any]:
    rows = []
    for rec in _scope_rows(collect_persisted_evidence_rows(), role):
        idx = rec.get("search_index") or {}
        meta = rec.get("metadata") or {}
        indexed = bool(idx.get("indexed") or meta.get("pgvector_indexed"))
        if not indexed:
            rows.append({**_to_citation(rec), "pgvector_status": "not_indexed", "index_reason": idx.get("reason") or meta.get("index_reason") or "not indexed"})
    return _structured(title="Evidence not indexed in PGVector", rows=rows[:20], filters=filters, citations=rows[:20], intent="pgvector_indexing_status")


def handle_duplicate_summary(filters: dict[str, Any], role: str) -> dict[str, Any]:
    filters = {**filters, "run_id": filters.get("run_id") or _latest_scheduler_run_id()}
    try:
        from modules.operations.engines.scheduler_module import get_run_progress

        summary = (get_run_progress(filters["run_id"]) or {}).get("summary") or {}
        if summary.get("duplicates_skipped"):
            rows = [{"run_id": filters["run_id"], "duplicates_skipped": summary["duplicates_skipped"]}]
            return _structured(title="Duplicate evidences skipped in latest run", rows=rows, filters=filters, intent="duplicate_evidence_summary")
    except Exception:  # noqa: BLE001
        pass
    return handle_duplicate_attempts(filters, role)


def _needs_param(name: str, options: list[str], *, query_key: str = "") -> dict[str, Any]:
    return {
        "ok": False,
        "needs_parameter": True,
        "parameter": name,
        "options": options,
        "query_key": query_key,
        "answer_source": "Deterministic",
        "query_type": "Deterministic",
        "answer": f"Select a {name} to run this query.",
        "title": "Parameter required",
        "rows": [],
        "total_count": 0,
        "citations": [],
    }


PRESET_HANDLERS: dict[str, Any] = {
    "latest_n": handle_latest_n,
    "latest_evidence": handle_latest_evidence,
    "evidence_by_framework": handle_evidence_by_framework,
    "evidence_by_scheduler_run": handle_evidence_by_scheduler_run,
    "duplicate_evidence_summary": handle_duplicate_summary,
    "failed_evidence_collection": handle_failed_collections,
    "evidence_pending_review": handle_pending_review,
    "recently_approved_evidence": handle_recently_approved,
    "evidence_version_history": handle_version_history,
    "expiring_evidence": handle_expiring_evidence,
    "latest_open_observations": handle_latest_open_observations,
    "high_risk_open_observations": handle_high_risk_observations,
    "overdue_observations": handle_overdue_observations,
    "observations_by_application": handle_observations_by_application,
    "observations_by_framework": handle_observations_by_framework,
    "rejected_evidence": handle_rejected_evidence,
    "framework_collection_summary": handle_framework_summary,
    "application_collection_summary": handle_application_summary,
    "control_without_evidence": handle_controls_without_evidence,
    "common_control_reuse": handle_common_control_reuse,
    "pgvector_indexing_status": handle_pgvector_status,
}


PRESET_QUERY_CATALOG: list[dict[str, Any]] = [
    {"id": "latest_5_evidences", "label": "Last 5 evidences", "question": "Show the last 5 evidences collected", "group": "Recent Evidence", "execution": "deterministic", "handler": "latest_n", "defaults": {"limit": 5}},
    {"id": "latest_evidence_by_application", "label": "Latest by application", "question": "Show the latest evidence for Net Banking", "group": "Recent Evidence", "execution": "deterministic", "handler": "latest_evidence", "requires": ["application"], "defaults": {"application": "Net Banking"}},
    {"id": "evidence_by_framework", "label": "Evidence by framework", "question": "Show evidence collected for PCI DSS", "group": "Recent Evidence", "execution": "deterministic", "handler": "evidence_by_framework", "requires": ["framework"], "defaults": {"framework": "PCI DSS"}},
    {"id": "evidence_by_scheduler_run", "label": "Latest scheduler run", "question": "Show evidence collected in the latest scheduler run", "group": "Scheduler Run", "execution": "deterministic", "handler": "evidence_by_scheduler_run"},
    {"id": "duplicate_evidence_summary", "label": "Duplicates skipped", "question": "Show duplicate evidences skipped in the latest run", "group": "Scheduler Run", "execution": "deterministic", "handler": "duplicate_evidence_summary"},
    {"id": "failed_evidence_collection", "label": "Failed collections", "question": "Show failed evidence collections", "group": "Scheduler Run", "execution": "deterministic", "handler": "failed_evidence_collection"},
    {"id": "evidence_pending_review", "label": "Pending review", "question": "Show evidences pending review", "group": "Review & Observations", "execution": "deterministic", "handler": "evidence_pending_review"},
    {"id": "recently_approved_evidence", "label": "Recently approved", "question": "Show recently approved evidences", "group": "Review & Observations", "execution": "deterministic", "handler": "recently_approved_evidence"},
    {"id": "evidence_version_history", "label": "Latest versions", "question": "Show latest evidence versions", "group": "Recent Evidence", "execution": "deterministic", "handler": "evidence_version_history"},
    {"id": "expiring_evidence", "label": "Expiring evidence", "question": "Show evidence expiring in the next 30 days", "group": "Recent Evidence", "execution": "deterministic", "handler": "expiring_evidence"},
    {"id": "latest_open_observations", "label": "Open observations", "question": "Show the latest 5 open observations", "group": "Review & Observations", "execution": "deterministic", "handler": "latest_open_observations", "defaults": {"limit": 5}},
    {"id": "high_risk_open_observations", "label": "High-risk observations", "question": "Show high-risk open observations", "group": "Review & Observations", "execution": "deterministic", "handler": "high_risk_open_observations"},
    {"id": "overdue_observations", "label": "Overdue observations", "question": "Show overdue observations", "group": "Review & Observations", "execution": "deterministic", "handler": "overdue_observations"},
    {"id": "observations_by_application", "label": "Observations by app", "question": "Show open observations for Net Banking", "group": "Review & Observations", "execution": "deterministic", "handler": "observations_by_application", "requires": ["application"], "defaults": {"application": "Net Banking"}},
    {"id": "observations_by_framework", "label": "Observations by framework", "question": "Show open PCI DSS observations", "group": "Review & Observations", "execution": "deterministic", "handler": "observations_by_framework", "requires": ["framework"], "defaults": {"framework": "PCI DSS"}},
    {"id": "rejected_evidence", "label": "Rejected evidence", "question": "Show rejected evidences requiring resubmission", "group": "Review & Observations", "execution": "deterministic", "handler": "rejected_evidence"},
    {"id": "framework_collection_summary", "label": "Count by framework", "question": "Show evidence count by framework", "group": "Coverage & Gaps", "execution": "deterministic", "handler": "framework_collection_summary"},
    {"id": "application_collection_summary", "label": "Count by application", "question": "Show evidence count by application", "group": "Coverage & Gaps", "execution": "deterministic", "handler": "application_collection_summary"},
    {"id": "control_without_evidence", "label": "Controls without evidence", "question": "Show controls without evidence", "group": "Coverage & Gaps", "execution": "deterministic", "handler": "control_without_evidence"},
    {"id": "common_control_reuse", "label": "Reused evidence", "question": "Show evidences reused across frameworks", "group": "Coverage & Gaps", "execution": "deterministic", "handler": "common_control_reuse"},
    {"id": "pgvector_indexing_status", "label": "Not indexed", "question": "Show evidences not indexed in PGVector", "group": "Coverage & Gaps", "execution": "deterministic", "handler": "pgvector_indexing_status"},
]

PRESET_BY_ID = {item["id"]: item for item in PRESET_QUERY_CATALOG}


def presets_for_role(role: str) -> list[dict[str, Any]]:
    role = normalize_role(role)
    out = []
    for preset in PRESET_QUERY_CATALOG:
        roles = preset.get("roles")
        if roles and role not in roles:
            continue
        out.append(preset)
    return out


def preset_groups_for_role(role: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict]] = {}
    for preset in presets_for_role(role):
        grouped.setdefault(preset["group"], []).append(preset)
    return [{"group": group, "presets": items} for group, items in grouped.items()]


def execute_preset_query(
    query_key: str,
    *,
    role: str = "owner",
    user: str = "User",
    application: str = "",
    framework: str = "",
    run_id: str = "",
    limit: int = 0,
) -> dict[str, Any]:
    preset = PRESET_BY_ID.get(query_key)
    if not preset:
        return {"ok": False, "error": f"Unknown query key: {query_key}", "answer": f"Unknown query key: {query_key}", "answer_source": "Deterministic"}
    filters = _merge_filters(dict(preset.get("defaults") or {}), application=application, framework=framework, run_id=run_id, limit=limit or preset.get("defaults", {}).get("limit"))
    for req in preset.get("requires") or []:
        if not filters.get(req):
            allowed = apps_for_role(role) if req == "application" else None
            options = list(allowed)[:6] if allowed else ["PCI DSS", "DPSC", "ITPP", "CSITE"]
            return _needs_param(req, options, query_key=query_key)
        app = filters.get("application")
        if req == "application" and app and not _application_allowed(role, app):
            return {"ok": False, "answer": f"You do not have access to evidence for {app}.", "answer_source": "Deterministic", "query_type": "Deterministic", "rows": [], "citations": []}
    handler = PRESET_HANDLERS[preset["handler"]]
    result = handler(filters, normalize_role(role))
    result["query_key"] = query_key
    result["question"] = preset["question"]
    result["label"] = preset["label"]
    result["execution"] = preset["execution"]
    return result


def execute_common_evidence_query(
    *,
    query_key: str = "",
    query: str = "",
    role: str = "owner",
    user: str = "User",
    application: str = "",
    framework: str = "",
    run_id: str = "",
    limit: int = 0,
) -> dict[str, Any]:
    if query_key:
        return execute_preset_query(
            query_key, role=role, user=user, application=application, framework=framework, run_id=run_id, limit=limit,
        )
    if query:
        det = try_deterministic_evidence_query(query, role=role, user=user)
        if det is not None:
            det["query_type"] = det.get("answer_source", "Deterministic")
            return det
        if is_evidence_catalog_query(query) and _is_semantic_only(query):
            rag = try_rag_evidence_query(query, role=role, user=user)
            if rag is not None:
                rag["query_type"] = "RAG"
                return rag
    return {"ok": False, "answer": EMPTY_SCOPE_MESSAGE, "answer_source": "Deterministic", "query_type": "Deterministic", "rows": [], "citations": []}


def _is_semantic_only(query: str) -> bool:
    q = (query or "").lower()
    semantic_markers = ("describe", "explain", "summarize", "what does", "content of", "document says")
    catalog_markers = ("show", "list", "latest", "pending", "approved", "rejected", "duplicate", "observation", "count")
    return any(m in q for m in semantic_markers) and not any(m in q for m in catalog_markers)


def render_common_query_html(result: dict[str, Any]) -> str:
    from html import escape

    if result.get("needs_parameter"):
        opts = "".join(
            f'<button type="button" class="btn btn-outline-secondary btn-sm ecs-ceq-preset me-1 mb-1" '
            f'data-query-key="{escape(result.get("query_key", ""))}" data-{escape(result.get("parameter", "application"))}="{escape(opt)}">{escape(opt)}</button>'
            for opt in (result.get("options") or [])
        )
        return f'<div class="alert alert-warning py-2 small mb-0">{escape(result.get("answer", ""))}{opts}</div>'
    if result.get("error"):
        return f'<div class="alert alert-danger py-2 small mb-0">{escape(str(result.get("error")))}</div>'
    body = escape(result.get("answer") or EMPTY_SCOPE_MESSAGE).replace("\n", "<br>")
    refs = []
    for cite in (result.get("citations") or [])[:8]:
        eid = cite.get("evidence_id")
        if eid:
            refs.append(f'<a class="btn btn-sm btn-outline-primary me-1 mb-1" href="/mvp/scheduler/fetched-evidence/view?evidence_id={escape(eid)}">View {escape(eid)}</a>')
    ref_html = "".join(refs)
    return f'<div class="ecs-ceq-response"><pre class="small mb-2" style="white-space:pre-wrap;">{body}</pre>{ref_html}</div>'
