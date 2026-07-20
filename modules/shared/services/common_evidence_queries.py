"""Deterministic + RAG hybrid common evidence querying for the ECS chatbot."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Callable

from app import ecs_state
from modules.governance.engines.missing_evidence_engine import get_all_missing_evidence
from modules.governance.engines.workflow_module import build_auditor_review_queue, build_owner_work_queue
from modules.operations.engines import evidence_repository as ops_repo
from modules.shared.services.audit_trail import get_audit_trail
from modules.shared.services.evidence_workflow_engine import get_enrollment
from modules.shared.services.role_filter_scope import apply_role_scope, apps_for_role, normalize_role

NO_EVIDENCE_MESSAGE = "No supporting evidence was found in ECS."

_BANKING_APPS = (
    "Net Banking",
    "Mobile Banking",
    "Payments",
    "Treasury",
    "Loan System",
    "UPI",
)


def _parse_iso_date(value: str) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        if len(raw) >= 10:
            try:
                return datetime.fromisoformat(raw[:10])
            except ValueError:
                return None
    return None


def _record_application(record: dict) -> str:
    tags = record.get("application_tags") or []
    if tags:
        return str(tags[0])
    meta = record.get("metadata") or {}
    return str(meta.get("application") or record.get("application") or "")


def _record_framework(record: dict) -> str:
    tags = record.get("framework_tags") or []
    return str(tags[0] if tags else record.get("framework") or "")


def _record_control_id(record: dict) -> str:
    meta = record.get("metadata") or {}
    return str(record.get("control") or meta.get("query_id") or meta.get("control_id") or "")


def _record_object_key(record: dict) -> str:
    meta = record.get("metadata") or {}
    return str(meta.get("object_key") or record.get("object_key") or record.get("object_uri") or "")


def _workflow_status(record: dict) -> str:
    evidence_id = str(record.get("evidence_id") or "")
    enrollment = get_enrollment(evidence_id=evidence_id) or {}
    if enrollment.get("status"):
        return str(enrollment["status"])
    key = str(record.get("workflow_key") or (record.get("metadata") or {}).get("workflow_key") or "")
    if key:
        if key in ecs_state.approved_controls:
            return "Approved"
        if key in ecs_state.rejected_controls:
            return "Rejected"
        if key in ecs_state.submitted_controls:
            return "Pending Auditor Approval"
    for wf_key, info in ecs_state.approved_controls.items():
        enrolled = get_enrollment(key=wf_key) or {}
        if enrolled.get("evidence_id") == evidence_id:
            return "Approved"
    for wf_key in ecs_state.rejected_controls:
        enrolled = get_enrollment(key=wf_key) or {}
        if enrolled.get("evidence_id") == evidence_id:
            return "Rejected"
    for wf_key in ecs_state.submitted_controls:
        submitted = ecs_state.submitted_controls[wf_key]
        if submitted.get("evidence_id") == evidence_id:
            return "Pending Auditor Approval"
    return str(record.get("workflow_status") or record.get("status") or "Uploaded")


def _to_citation(record: dict) -> dict[str, Any]:
    return {
        "evidence_id": record.get("evidence_id", ""),
        "version": int(record.get("version") or record.get("evidence_version") or 1),
        "control_id": _record_control_id(record),
        "application": _record_application(record),
        "source_connector": record.get("source_connector") or "",
        "object_key": _record_object_key(record),
        "object_reference": _record_object_key(record),
        "sha256": record.get("sha256") or "",
        "status": _workflow_status(record),
        "framework": _record_framework(record),
    }


def collect_persisted_evidence_rows() -> list[dict]:
    """Normalize ops-repository uploads (including predefined-query JSON)."""
    rows: list[dict] = []
    for rec in ops_repo.evidence_repository:
        row = dict(rec)
        row["application"] = _record_application(rec)
        row["framework"] = _record_framework(rec)
        row["control_id"] = _record_control_id(rec)
        row["workflow_status"] = _workflow_status(rec)
        rows.append(row)
    return rows


def _extract_application(query: str) -> str | None:
    q = (query or "").lower()
    for app in _BANKING_APPS:
        if app.lower() in q:
            return app
    return None


def _extract_control_id(query: str) -> str | None:
    match = re.search(r"\b([A-Z]{2,5}-\d{2,4})\b", query or "")
    if match:
        return match.group(1)
    return None


def _extract_framework(query: str) -> str | None:
    q = (query or "").lower()
    for fw in ecs_state.frameworks:
        if fw.lower() in q:
            return fw
    if "db baselining" in q or "database baselining" in q:
        return "DB Baselining"
    return None


def _extract_evidence_id(query: str) -> str | None:
    match = re.search(r"\b(EVD-\d{5})\b", query or "", re.I)
    if match:
        return match.group(1).upper()
    return None


def _extract_date_range(query: str) -> tuple[str | None, str | None]:
    q = query or ""
    iso_dates = re.findall(r"\b(20\d{2}-\d{2}-\d{2})\b", q)
    if len(iso_dates) >= 2:
        return iso_dates[0], iso_dates[1]
    if len(iso_dates) == 1:
        return iso_dates[0], iso_dates[0]
    return None, None


def parse_query_filters(query: str) -> dict[str, Any]:
    return {
        "application": _extract_application(query),
        "framework": _extract_framework(query),
        "control_id": _extract_control_id(query),
        "evidence_id": _extract_evidence_id(query),
        "date_from": _extract_date_range(query)[0],
        "date_to": _extract_date_range(query)[1],
    }


def _application_allowed(role: str, application: str | None) -> bool:
    if not application:
        return True
    allowed = apps_for_role(role)
    if allowed is None:
        return True
    return application in allowed


def _scope_rows(rows: list[dict], role: str) -> list[dict]:
    return apply_role_scope(rows, role, app_key="application")


def _filter_rows(rows: list[dict], filters: dict[str, Any]) -> list[dict]:
    out = list(rows)
    if filters.get("application"):
        out = [r for r in out if r.get("application") == filters["application"]]
    if filters.get("framework"):
        out = [r for r in out if r.get("framework") == filters["framework"]]
    if filters.get("control_id"):
        cid = filters["control_id"]
        out = [r for r in out if r.get("control_id") == cid or r.get("control") == cid]
    if filters.get("evidence_id"):
        eid = filters["evidence_id"]
        out = [r for r in out if r.get("evidence_id") == eid]
    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    if date_from or date_to:
        start = _parse_iso_date(date_from or "") if date_from else None
        end = _parse_iso_date(date_to or "") if date_to else None
        filtered: list[dict] = []
        for row in out:
            uploaded = _parse_iso_date(str(row.get("uploaded_at") or ""))
            if uploaded is None:
                continue
            if start and uploaded.date() < start.date():
                continue
            if end and uploaded.date() > end.date():
                continue
            filtered.append(row)
        out = filtered
    return out


def _result(answer: str, *, citations: list[dict] | None = None, intent: str = "") -> dict[str, Any]:
    return {
        "answer": answer,
        "answer_source": "DETERMINISTIC",
        "citations": citations or [],
        "intent": intent,
    }


def _no_evidence(intent: str = "") -> dict[str, Any]:
    return _result(NO_EVIDENCE_MESSAGE, intent=intent)


def _access_denied(application: str, intent: str = "") -> dict[str, Any]:
    return _result(
        f"You do not have access to evidence for {application}.",
        intent=intent,
    )


def _guard_access(role: str, filters: dict[str, Any], intent: str) -> dict[str, Any] | None:
    app = filters.get("application")
    if app and not _application_allowed(role, app):
        return _access_denied(app, intent=intent)
    return None


def _sort_latest(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: str(r.get("uploaded_at") or ""), reverse=True)


def handle_latest_evidence(filters: dict[str, Any], role: str) -> dict[str, Any]:
    denied = _guard_access(role, filters, "latest_evidence")
    if denied:
        return denied
    rows = _filter_rows(_scope_rows(collect_persisted_evidence_rows(), role), filters)
    if not rows:
        return _no_evidence("latest_evidence")
    latest = _sort_latest(rows)[0]
    cite = _to_citation(latest)
    answer = (
        f"Latest evidence: {cite['evidence_id']} (v{cite['version']}) for control "
        f"{cite['control_id']} in {cite['application']} — status {cite['status']}."
    )
    return _result(answer, citations=[cite], intent="latest_evidence")


def handle_pending_app_owner(filters: dict[str, Any], role: str) -> dict[str, Any]:
    denied = _guard_access(role, filters, "pending_app_owner")
    if denied:
        return denied
    queue = build_owner_work_queue(limit=200)
    rows = []
    for item in queue:
        if item.get("workflow_code") not in ("draft", "uploaded", "pending_app_owner", "clarification", "reupload"):
            continue
        if filters.get("application") and item.get("application") != filters["application"]:
            continue
        if filters.get("control_id") and item.get("control_id") != filters["control_id"]:
            continue
        rows.append(item)
    rows = _scope_rows(
        [{"application": r.get("application", ""), **r} for r in rows],
        role,
    )
    if not rows:
        return _no_evidence("pending_app_owner")
    lines = [
        f"{r.get('evidence_id', 'n/a')} — {r.get('control_id') or r.get('control')} "
        f"({r.get('application', 'n/a')}) pending App Owner review"
        for r in rows[:10]
    ]
    citations = [
        {
            "evidence_id": r.get("evidence_id", ""),
            "version": int(r.get("evidence_version") or r.get("version") or 1),
            "control_id": r.get("control_id") or r.get("control") or "",
            "application": r.get("application", ""),
            "source_connector": r.get("source_connector") or "",
            "object_key": r.get("object_key") or "",
            "object_reference": r.get("object_key") or "",
            "status": r.get("workflow_status") or "Pending App Owner Review",
        }
        for r in rows[:10]
    ]
    return _result("Pending App Owner evidence:\n" + "\n".join(lines), citations=citations, intent="pending_app_owner")


def handle_pending_auditor(filters: dict[str, Any], role: str) -> dict[str, Any]:
    denied = _guard_access(role, filters, "pending_auditor")
    if denied:
        return denied
    queue = build_auditor_review_queue(limit=200)
    rows = []
    for item in queue:
        if filters.get("application") and item.get("application") != filters["application"]:
            continue
        if filters.get("control_id") and item.get("control_id") != filters["control_id"]:
            continue
        rows.append(item)
    rows = _scope_rows(
        [{"application": r.get("application", ""), **r} for r in rows],
        role,
    )
    if not rows:
        return _no_evidence("pending_auditor")
    lines = [
        f"{r.get('evidence_id', 'n/a')} — {r.get('control_id') or r.get('control')} "
        f"({r.get('application', 'n/a')}) pending Auditor review"
        for r in rows[:10]
    ]
    citations = [
        {
            "evidence_id": r.get("evidence_id", ""),
            "version": int(r.get("evidence_version") or r.get("version") or 1),
            "control_id": r.get("control_id") or r.get("control") or "",
            "application": r.get("application", ""),
            "source_connector": r.get("source_connector") or "",
            "object_key": r.get("object_key") or "",
            "object_reference": r.get("object_key") or "",
            "status": "Pending Auditor Approval",
        }
        for r in rows[:10]
    ]
    return _result("Evidence pending Auditor review:\n" + "\n".join(lines), citations=citations, intent="pending_auditor")


def handle_approved_evidence(filters: dict[str, Any], role: str) -> dict[str, Any]:
    denied = _guard_access(role, filters, "approved_evidence")
    if denied:
        return denied
    citations: list[dict] = []
    lines: list[str] = []
    for key, info in ecs_state.approved_controls.items():
        framework, control = key.split("::", 1)
        if filters.get("framework") and framework != filters["framework"]:
            continue
        enrollment = get_enrollment(key=key) or ecs_state.uploaded_evidence_enrollments.get(
            str(info.get("evidence_id") or "")
        ) or {}
        application = enrollment.get("application") or info.get("application") or ""
        control_id = enrollment.get("control_id") or info.get("control_id") or control
        if filters.get("application") and application != filters["application"]:
            continue
        if filters.get("control_id") and control_id != filters["control_id"]:
            continue
        evidence_id = enrollment.get("evidence_id") or info.get("evidence_id") or ""
        row = {
            "application": application,
            "evidence_id": evidence_id,
            "version": int(info.get("evidence_version") or enrollment.get("evidence_version") or 1),
            "control_id": control_id,
            "source_connector": enrollment.get("source_connector") or info.get("source_connector") or "",
            "object_key": enrollment.get("object_key") or info.get("object_key") or "",
            "status": "Approved",
        }
        if not _application_allowed(role, application):
            continue
        citations.append({**row, "object_reference": row["object_key"]})
        lines.append(f"{row['evidence_id']} — {control_id} ({application}) approved by Auditor")
    if not lines:
        persisted = _filter_rows(
            [r for r in collect_persisted_evidence_rows() if _workflow_status(r) == "Approved"],
            filters,
        )
        persisted = _scope_rows(persisted, role)
        for row in persisted[:10]:
            cite = _to_citation(row)
            citations.append(cite)
            lines.append(f"{cite['evidence_id']} — {cite['control_id']} ({cite['application']}) approved")
    if not lines:
        return _no_evidence("approved_evidence")
    return _result("Approved evidence:\n" + "\n".join(lines[:10]), citations=citations[:10], intent="approved_evidence")


def handle_rejected_evidence(filters: dict[str, Any], role: str) -> dict[str, Any]:
    denied = _guard_access(role, filters, "rejected_evidence")
    if denied:
        return denied
    lines: list[str] = []
    citations: list[dict] = []
    for key, info in ecs_state.rejected_controls.items():
        framework, control = key.split("::", 1)
        if filters.get("framework") and framework != filters["framework"]:
            continue
        enrollment = get_enrollment(key=key) or {}
        application = enrollment.get("application") or info.get("application") or ""
        control_id = enrollment.get("control_id") or info.get("control_id") or control
        evidence_id = enrollment.get("evidence_id") or info.get("evidence_id") or ""
        if filters.get("application") and application != filters["application"]:
            continue
        if filters.get("control_id") and control_id != filters["control_id"]:
            continue
        if not _application_allowed(role, application):
            continue
        reason = info.get("reason") or "No rejection reason recorded."
        lines.append(f"{evidence_id or 'n/a'} — {control_id} ({application}) rejected: {reason}")
        citations.append(
            {
                "evidence_id": evidence_id,
                "version": int(info.get("evidence_version") or enrollment.get("evidence_version") or 1),
                "control_id": control_id,
                "application": application,
                "source_connector": enrollment.get("source_connector") or "",
                "object_key": enrollment.get("object_key") or "",
                "object_reference": enrollment.get("object_key") or "",
                "status": "Rejected",
                "rejection_reason": reason,
            }
        )
    if not lines:
        return _no_evidence("rejected_evidence")
    return _result("Rejected evidence:\n" + "\n".join(lines[:10]), citations=citations[:10], intent="rejected_evidence")


def handle_missing_evidence(filters: dict[str, Any], role: str) -> dict[str, Any]:
    denied = _guard_access(role, filters, "missing_evidence")
    if denied:
        return denied
    rows = get_all_missing_evidence(role)
    if filters.get("application"):
        rows = [r for r in rows if r.get("application") == filters["application"]]
    if filters.get("framework"):
        rows = [r for r in rows if r.get("framework") == filters["framework"]]
    if filters.get("control_id"):
        cid = filters["control_id"]
        rows = [
            r for r in rows
            if r.get("control_id") == cid or r.get("control") == cid or cid in str(r.get("control_description", ""))
        ]
    if not rows:
        return _no_evidence("missing_evidence")
    lines = [
        f"{r.get('observation_id', 'n/a')} — {r.get('control_id') or r.get('control')} "
        f"({r.get('application', 'n/a')}): {r.get('missing_evidence', 'missing')}"
        for r in rows[:10]
    ]
    return _result("Missing evidence gaps:\n" + "\n".join(lines), intent="missing_evidence")


def handle_duplicate_attempts(filters: dict[str, Any], role: str) -> dict[str, Any]:
    denied = _guard_access(role, filters, "duplicate_attempts")
    if denied:
        return denied
    events = [
        e for e in get_audit_trail(200)
        if e.get("action") == "Predefined Query Evidence Duplicate"
    ]
    lines: list[str] = []
    citations: list[dict] = []
    for event in events:
        detail = str(event.get("detail") or "")
        evidence_id = str(event.get("evidence_id") or "")
        rec = next((r for r in ops_repo.evidence_repository if r.get("evidence_id") == evidence_id), None)
        if rec is None:
            continue
        app = _record_application(rec)
        if filters.get("application") and app != filters["application"]:
            continue
        if filters.get("control_id") and _record_control_id(rec) != filters["control_id"]:
            continue
        if not _application_allowed(role, app):
            continue
        cite = _to_citation(rec)
        cite["status"] = "DUPLICATE"
        citations.append(cite)
        lines.append(f"Duplicate attempt for {cite['evidence_id']} ({cite['control_id']}, {app}): {detail}")
    if not lines:
        return _no_evidence("duplicate_attempts")
    return _result(
        "Duplicate evidence attempts (not counted as new evidence):\n" + "\n".join(lines[:10]),
        citations=citations[:10],
        intent="duplicate_attempts",
    )


def handle_date_range(filters: dict[str, Any], role: str) -> dict[str, Any]:
    denied = _guard_access(role, filters, "date_range")
    if denied:
        return denied
    rows = _filter_rows(_scope_rows(collect_persisted_evidence_rows(), role), filters)
    if not rows:
        return _no_evidence("date_range")
    lines = [
        f"{r.get('evidence_id')} — {_record_control_id(r)} collected {r.get('uploaded_at', '')[:10]}"
        for r in _sort_latest(rows)[:10]
    ]
    return _result(
        "Evidence collected in requested date range:\n" + "\n".join(lines),
        citations=[_to_citation(r) for r in rows[:10]],
        intent="date_range",
    )


def handle_evidence_details(filters: dict[str, Any], role: str) -> dict[str, Any]:
    denied = _guard_access(role, filters, "evidence_details")
    if denied:
        return denied
    rows = _filter_rows(_scope_rows(collect_persisted_evidence_rows(), role), filters)
    if not rows:
        return _no_evidence("evidence_details")
    target = _sort_latest(rows)[0]
    cite = _to_citation(target)
    answer = (
        f"Evidence {cite['evidence_id']} v{cite['version']} — control {cite['control_id']}, "
        f"application {cite['application']}, source {cite['source_connector'] or 'n/a'}, "
        f"SHA-256 {cite['sha256']}, status {cite['status']}, object {_record_object_key(target)}."
    )
    return _result(answer, citations=[cite], intent="evidence_details")


def handle_control_approved(filters: dict[str, Any], role: str) -> dict[str, Any]:
    denied = _guard_access(role, filters, "control_approved")
    if denied:
        return denied
    control_id = filters.get("control_id")
    if not control_id:
        return _no_evidence("control_approved")
    for key, info in ecs_state.approved_controls.items():
        enrollment = get_enrollment(key=key) or {}
        mapped_control = enrollment.get("control_id") or info.get("control_id") or key.split("::", 1)[-1]
        application = enrollment.get("application") or info.get("application") or ""
        if mapped_control != control_id:
            continue
        if filters.get("application") and application != filters["application"]:
            continue
        if not _application_allowed(role, application):
            return _access_denied(application, intent="control_approved")
        evidence_id = enrollment.get("evidence_id") or info.get("evidence_id") or ""
        answer = (
            f"Control {control_id} is Approved with current evidence {evidence_id} "
            f"(v{int(info.get('evidence_version') or enrollment.get('evidence_version') or 1)})."
        )
        cite = {
            "evidence_id": evidence_id,
            "version": int(info.get("evidence_version") or enrollment.get("evidence_version") or 1),
            "control_id": control_id,
            "application": application,
            "source_connector": enrollment.get("source_connector") or "",
            "object_key": enrollment.get("object_key") or "",
            "object_reference": enrollment.get("object_key") or "",
            "status": "Approved",
        }
        return _result(answer, citations=[cite], intent="control_approved")
    return _no_evidence("control_approved")


Handler = Callable[[dict[str, Any], str], dict[str, Any]]

COMMON_QUERY_CATALOG: list[dict[str, Any]] = [
    {
        "intent": "latest_evidence",
        "description": "Show latest evidence for application/control",
        "required_filters": [],
        "optional_filters": ["application", "framework", "control_id"],
        "patterns": (
            r"\blatest evidence\b",
            r"\bmost recent evidence\b",
            r"\bshow (?:me )?(?:the )?latest\b.*\bevidence\b",
            r"\blatest\b.*\bfor\b.*\b(?:pgx|control)\b",
        ),
        "handler": handle_latest_evidence,
    },
    {
        "intent": "pending_app_owner",
        "description": "Show pending App Owner evidence",
        "required_filters": [],
        "optional_filters": ["application", "control_id"],
        "patterns": (
            r"\bpending app owner\b",
            r"\bapp owner\b.*\bpending\b",
            r"\bevidence\b.*\bpending\b.*\bowner\b",
            r"\bawaiting app owner\b",
        ),
        "handler": handle_pending_app_owner,
    },
    {
        "intent": "pending_auditor",
        "description": "Show evidence pending Auditor review",
        "required_filters": [],
        "optional_filters": ["application", "control_id"],
        "patterns": (
            r"\bpending auditor\b",
            r"\bauditor review\b",
            r"\bawaiting auditor\b",
            r"\bevidence\b.*\bpending\b.*\bauditor\b",
        ),
        "handler": handle_pending_auditor,
    },
    {
        "intent": "approved_evidence",
        "description": "Show approved evidence",
        "required_filters": [],
        "optional_filters": ["application", "framework", "control_id"],
        "patterns": (
            r"\bapproved evidence\b",
            r"\bshow approved\b.*\bevidence\b",
            r"\blist approved\b.*\bevidence\b",
        ),
        "handler": handle_approved_evidence,
    },
    {
        "intent": "rejected_evidence",
        "description": "Show rejected evidence and rejection reason",
        "required_filters": [],
        "optional_filters": ["application", "framework", "control_id"],
        "patterns": (
            r"\brejected evidence\b",
            r"\brejection reason\b",
            r"\bwhy\b.*\brejected\b",
            r"\bevidence\b.*\brejected\b",
        ),
        "handler": handle_rejected_evidence,
    },
    {
        "intent": "missing_evidence",
        "description": "Show missing evidence by application/framework/control",
        "required_filters": [],
        "optional_filters": ["application", "framework", "control_id"],
        "patterns": (
            r"\bmissing evidence\b",
            r"\bevidence gap\b",
            r"\bno evidence\b.*\bfor\b",
            r"\bshow missing\b",
        ),
        "handler": handle_missing_evidence,
    },
    {
        "intent": "duplicate_attempts",
        "description": "Show duplicate evidence attempts",
        "required_filters": [],
        "optional_filters": ["application", "control_id"],
        "patterns": (
            r"\bduplicate evidence\b",
            r"\bduplicate attempt\b",
            r"\bduplicate upload\b",
        ),
        "handler": handle_duplicate_attempts,
    },
    {
        "intent": "date_range",
        "description": "Show evidence collected in a date range",
        "required_filters": ["date_from"],
        "optional_filters": ["application", "framework", "control_id", "date_to"],
        "patterns": (
            r"\bevidence collected\b",
            r"\bcollected between\b",
            r"\bdate range\b.*\bevidence\b",
            r"\bevidence from\b.*\b20\d{2}-\d{2}-\d{2}\b",
        ),
        "handler": handle_date_range,
    },
    {
        "intent": "evidence_details",
        "description": "Show evidence source, version, SHA-256 and status",
        "required_filters": [],
        "optional_filters": ["evidence_id", "control_id", "application"],
        "patterns": (
            r"\bsha-?256\b",
            r"\bsource connector\b",
            r"\bevidence version\b",
            r"\bevidence details\b",
            r"\bobject key\b",
        ),
        "handler": handle_evidence_details,
    },
    {
        "intent": "control_approved",
        "description": "Confirm whether a control has approved current evidence",
        "required_filters": ["control_id"],
        "optional_filters": ["application"],
        "patterns": (
            r"\bcontrol\b.*\bimplemented\b",
            r"\bapproved current evidence\b",
            r"\bdoes\b.*\bhave approved\b",
            r"\bis\b.*\bcontrol\b.*\bapproved\b",
            r"\bimplementation status\b.*\bcontrol\b",
        ),
        "handler": handle_control_approved,
    },
]


def match_common_intent(query: str) -> dict[str, Any] | None:
    q = (query or "").lower()
    filters = parse_query_filters(query)
    for entry in COMMON_QUERY_CATALOG:
        if any(re.search(pattern, q) for pattern in entry["patterns"]):
            missing = [f for f in entry.get("required_filters", []) if not filters.get(f)]
            if missing and entry["intent"] != "date_range":
                continue
            if entry["intent"] == "date_range" and not (filters.get("date_from") or filters.get("date_to")):
                continue
            return {"intent": entry["intent"], "filters": filters, "handler": entry["handler"]}
    if filters.get("control_id") and re.search(r"\blatest\b", q):
        return {"intent": "latest_evidence", "filters": filters, "handler": handle_latest_evidence}
    if filters.get("evidence_id"):
        return {"intent": "evidence_details", "filters": filters, "handler": handle_evidence_details}
    return None


def is_evidence_catalog_query(query: str) -> bool:
    q = (query or "").lower()
    if match_common_intent(query):
        return True
    markers = (
        "evidence",
        "sha-256",
        "sha256",
        "control",
        "pgx-",
        "predefined query",
        "object key",
        "source connector",
        "auditor review",
        "app owner",
        "approved",
        "rejected",
        "missing evidence",
        "duplicate",
    )
    return any(marker in q for marker in markers)


def try_deterministic_evidence_query(query: str, *, role: str = "owner", user: str = "User") -> dict[str, Any] | None:
    _ = user
    matched = match_common_intent(query)
    if not matched:
        return None
    handler: Handler = matched["handler"]
    return handler(matched["filters"], normalize_role(role))


def _citations_from_rag(rag_result: dict[str, Any]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    for raw in rag_result.get("citations") or []:
        uid = raw.get("evidence_uid") or raw.get("evidence_id") or ""
        matched = None
        for rec in ops_repo.evidence_repository:
            meta = rec.get("metadata") or {}
            if rec.get("evidence_id") == uid:
                matched = rec
                break
            if uid and uid in str(meta.get("object_key") or ""):
                matched = rec
                break
            tag_hit = any(uid in str(tag) for tag in (rec.get("tags") or meta.get("tags") or ()))
            if tag_hit:
                matched = rec
                break
        if matched is None and uid.startswith("EVD-"):
            matched = next((r for r in ops_repo.evidence_repository if r.get("evidence_id") == uid), None)
        if matched is None:
            citations.append(
                {
                    "evidence_id": uid,
                    "version": raw.get("version") or 1,
                    "control_id": ", ".join(raw.get("controls") or []) or "",
                    "application": raw.get("application") or "",
                    "source_connector": raw.get("source_system") or "",
                    "object_key": raw.get("url") or "",
                    "object_reference": raw.get("url") or "",
                }
            )
            continue
        cite = _to_citation(matched)
        if raw.get("application"):
            cite["application"] = raw["application"]
        citations.append(cite)
    return citations


def try_rag_evidence_query(
    query: str,
    *,
    role: str = "owner",
    user: str = "User",
    framework: str = "",
) -> dict[str, Any] | None:
    from ecs_platform.rag import answer as rag_answer

    rag = rag_answer(
        query,
        role=role,
        user=user,
        framework=framework,
    )
    if rag.get("mode") == "denied":
        return {
            "answer": rag.get("answer") or NO_EVIDENCE_MESSAGE,
            "answer_source": "RAG",
            "citations": [],
            "intent": "free_text",
        }
    citations = _citations_from_rag(rag)
    if rag.get("mode") == "no_evidence" or (not citations and not rag.get("facts")):
        return {
            "answer": NO_EVIDENCE_MESSAGE,
            "answer_source": "RAG",
            "citations": [],
            "intent": "free_text",
        }
    answer = rag.get("answer") or ""
    if rag.get("mode") == "fallback" and citations:
        lines = [
            f"{c['evidence_id']} v{c['version']} — {c['control_id']} ({c['application']}) "
            f"via {c['source_connector'] or 'ECS'}"
            for c in citations[:5]
        ]
        answer = "Retrieved ECS evidence (LLM unavailable):\n" + "\n".join(lines)
    if not answer.strip():
        answer = NO_EVIDENCE_MESSAGE
    return {
        "answer": answer,
        "answer_source": "RAG",
        "citations": citations,
        "intent": "free_text",
        "rag_mode": rag.get("mode"),
    }


def format_evidence_chat_response(result: dict[str, Any], framework_hint: str = "") -> str:
    from modules.shared.services.chatbot_enhanced import format_chatbot_response

    body = result.get("answer") or NO_EVIDENCE_MESSAGE
    citations = result.get("citations") or []
    if citations:
        cite_lines = []
        for cite in citations[:8]:
            cite_lines.append(
                f"- {cite.get('evidence_id')} v{cite.get('version')} | {cite.get('control_id')} | "
                f"{cite.get('application')} | {cite.get('source_connector')} | "
                f"{cite.get('object_key') or cite.get('object_reference')}"
            )
        body += "\n\nCitations:\n" + "\n".join(cite_lines)
    source = result.get("answer_source") or "DETERMINISTIC"
    body += f"\n\n[Source: {source}]"
    return format_chatbot_response(body, framework_hint)


def evidence_search_status() -> dict[str, Any]:
    from ecs_platform.rag import rag_status

    status = rag_status()
    status["common_query_intents"] = [
        {
            "intent": entry["intent"],
            "description": entry["description"],
            "required_filters": entry.get("required_filters") or [],
            "optional_filters": entry.get("optional_filters") or [],
        }
        for entry in COMMON_QUERY_CATALOG
    ]
    status["ops_persisted_evidence"] = len(ops_repo.evidence_repository)
    status["indexed_documents"] = status.get("evidence_count", 0)
    status["indexed_chunks"] = status.get("vector_count", 0)
    return status
