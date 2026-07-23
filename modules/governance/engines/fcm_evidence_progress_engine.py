"""Framework Control Master × Evidence Dashboard progress integration.

Combines FCM catalogue (via service/repository), application assignments,
required evidence, and persisted workflow/evidence state. Dashboard routes must
call :class:`FrameworkControlMasterService` only — not this module directly.
"""

from __future__ import annotations

from typing import Any

from app import ecs_state
from modules.frameworks.repositories.framework_control_repository import (
    FrameworkControlRepository,
)
from modules.shared.services.role_filter_scope import apps_for_role, normalize_role

# Display names used by legacy ecs_state / evidence_rows
FCM_FRAMEWORK_DISPLAY: dict[str, str] = {
    "itpp": "ITPP",
    "asst": "ASST",
    "mbss": "MBSS",
    "pci_dss": "PCI DSS",
    "dpsc": "DPSC",
    "csite": "C-SITE",
    "vapt": "VAPT",
    "os_baseline": "OS Baseline",
    "middleware_baseline": "Middleware Baseline",
    "database_baseline": "Database Baseline",
}

PROGRESS_LEGEND: list[dict[str, str]] = [
    {"key": "closed", "label": "Closed", "tone": "green"},
    {"key": "pending", "label": "Pending / Under Review", "tone": "orange"},
    {"key": "blocked", "label": "Rejected / Overdue / Missing", "tone": "red"},
    {"key": "not_started", "label": "Not Started", "tone": "grey"},
    {"key": "not_applicable", "label": "Not Applicable", "tone": "grey"},
]

_STATUS_ORDER = ("closed", "pending", "blocked", "not_started", "not_applicable")


def _empty_segments() -> dict[str, int]:
    return {k: 0 for k in _STATUS_ORDER}


def _fcm_enrollment_key(
    framework_id: str, control_id: str, evr_id: str, application: str
) -> str:
    return f"fcm:{framework_id}:{control_id}:{evr_id}:{application}"


def _legacy_framework_name(framework_id: str, framework_doc: dict | None = None) -> str:
    if framework_doc:
        fw = framework_doc.get("framework") or {}
        return str(fw.get("name") or fw.get("display_name") or framework_id)
    return FCM_FRAMEWORK_DISPLAY.get(framework_id, framework_id)


def _index_persisted_submissions() -> dict[str, dict[str, Any]]:
    """Map fcm enrollment keys and legacy rows to submission payloads."""
    out: dict[str, dict[str, Any]] = {}
    for key, row in ecs_state.uploaded_evidence_enrollments.items():
        if not isinstance(row, dict):
            continue
        fw_id = row.get("fcm_framework_id") or row.get("framework_id")
        ctrl_id = row.get("fcm_control_id") or row.get("control_id")
        evr_id = row.get("fcm_evr_id") or row.get("evidence_requirement_id")
        app = row.get("application") or ""
        if fw_id and ctrl_id and evr_id and app:
            out[_fcm_enrollment_key(str(fw_id), str(ctrl_id), str(evr_id), str(app))] = row
    analytics = ecs_state.build_evidence_analytics()
    for row in analytics.get("evidence_rows") or []:
        fw = str(row.get("framework") or "")
        app = str(row.get("application") or "")
        ctrl = str(row.get("control") or "")
        if not fw or not app:
            continue
        legacy_key = f"legacy:{fw}::{ctrl}::{app}::{row.get('evidence_id', '')}"
        out.setdefault(
            legacy_key,
            {
                "source": "catalog",
                "framework": fw,
                "control_name": ctrl,
                "application": app,
                "evidence_id": row.get("evidence_id"),
                "evidence_name": row.get("evidence"),
                "audit_status": row.get("audit_status") or row.get("status"),
                "evidence_status": row.get("evidence_status"),
                "workflow_status": row.get("lifecycle") or row.get("status"),
                "status": row.get("audit_status") or row.get("status"),
            },
        )
    return out


def _find_submission(
    framework_id: str,
    framework_name: str,
    control: dict[str, Any],
    evr: dict[str, Any],
    application: str,
    submissions: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    evr_id = str(evr.get("id") or "")
    ctrl_id = str(control.get("id") or "")
    direct = submissions.get(_fcm_enrollment_key(framework_id, ctrl_id, evr_id, application))
    if direct:
        return direct
    title = str(control.get("title") or "")
    ev_title = str(evr.get("title") or "")
    for row in submissions.values():
        if row.get("application") != application:
            continue
        if row.get("fcm_framework_id") == framework_id and row.get("fcm_evr_id") == evr_id:
            return row
        if row.get("framework") != framework_name:
            continue
        if title and title in str(row.get("control_name") or ""):
            if ev_title and ev_title.split("—")[0].strip() in str(
                row.get("evidence_name") or row.get("evidence_id") or ""
            ):
                return row
            if not row.get("fcm_evr_id"):
                return row
    return None


def _classify_requirement(sub: dict[str, Any] | None) -> str:
    if not sub:
        return "missing"
    audit = str(sub.get("audit_status") or sub.get("status") or "").lower()
    workflow = str(sub.get("workflow_status") or sub.get("lifecycle") or "").lower()
    ev_status = str(sub.get("evidence_status") or "").lower()
    if audit in ("approved", "accepted") and ev_status not in ("expired", "due for refresh"):
        return "accepted"
    if audit in ("rejected",) or workflow in ("rejected",):
        return "rejected"
    if ev_status in ("expired",) or "overdue" in workflow:
        return "expired"
    if audit in ("submitted", "under review", "pending") or workflow in (
        "submitted",
        "under review",
        "pending app owner review",
        "pending review",
    ):
        return "pending"
    if sub.get("source") == "catalog" and audit in ("approved",):
        return "accepted"
    return "missing"


def _classify_control(
    *,
    repo: FrameworkControlRepository,
    framework_id: str,
    framework_name: str,
    control: dict[str, Any],
    application: str,
    submissions: dict[str, dict[str, Any]],
) -> str:
    ctrl_id = str(control.get("id") or "")
    if not repo.is_control_applicable(application, framework_id, ctrl_id):
        return "not_applicable"
    requirements = control.get("evidence_requirements") or []
    if not requirements:
        return "not_started"
    req_states = [
        _classify_requirement(
            _find_submission(
                framework_id, framework_name, control, evr, application, submissions
            )
        )
        for evr in requirements
    ]
    if all(s == "accepted" for s in req_states):
        ckey = ecs_state.control_key(framework_name, str(control.get("title") or ""))
        if ckey in ecs_state.approved_controls:
            return "closed"
        if all(s == "accepted" for s in req_states):
            return "closed"
    if any(s in ("rejected", "expired", "missing") for s in req_states):
        if any(s == "missing" for s in req_states) and not any(
            s == "pending" for s in req_states
        ):
            return "blocked"
        if any(s in ("rejected", "expired") for s in req_states):
            return "blocked"
    if any(s == "pending" for s in req_states) or any(s == "missing" for s in req_states):
        return "pending"
    return "not_started"


def _applications_for_role(role: str, repo: FrameworkControlRepository) -> list[str]:
    role = normalize_role(role)
    allowed = apps_for_role(role)
    all_apps = sorted({a["application"] for a in repo.list_application_assignments()})
    if allowed is None:
        return all_apps
    return [a for a in all_apps if a in allowed]


def build_framework_progress(
    repo: FrameworkControlRepository,
    *,
    role: str = "owner",
    application: str = "",
    framework_id: str = "",
) -> dict[str, Any]:
    submissions = _index_persisted_submissions()
    apps = _applications_for_role(role, repo)
    selected_app = (application or "").strip()
    if selected_app and selected_app in apps:
        scoped_apps = [selected_app]
    elif apps:
        scoped_apps = [apps[0]]
        selected_app = apps[0]
    else:
        scoped_apps = []
        selected_app = ""

    summaries = repo.list_framework_summaries()
    if framework_id:
        resolved = repo.resolve_framework_id(framework_id)
        summaries = [s for s in summaries if s["id"] == resolved]

    chart_rows: list[dict[str, Any]] = []
    control_rows: list[dict[str, Any]] = []

    for summary in summaries:
        fw_id = summary["id"]
        doc = repo.get_framework(fw_id)
        if not doc:
            continue
        fw_name = _legacy_framework_name(fw_id, doc)
        segments = _empty_segments()
        for app in scoped_apps:
            if fw_id not in repo.frameworks_for_application(app):
                continue
            for control in doc.get("controls") or []:
                status = _classify_control(
                    repo=repo,
                    framework_id=fw_id,
                    framework_name=fw_name,
                    control=control,
                    application=app,
                    submissions=submissions,
                )
                segments[status] += 1
                control_rows.append(
                    {
                        "framework_id": fw_id,
                        "framework_name": summary.get("display_name") or fw_name,
                        "application": app,
                        "control_id": control.get("id"),
                        "control_title": control.get("title"),
                        "domain": control.get("domain"),
                        "status": status,
                        "policy_refs": control.get("policy_refs") or [],
                    }
                )
        if sum(segments.values()) == 0:
            continue
        chart_rows.append(
            {
                "framework_id": fw_id,
                "framework_name": summary.get("display_name") or fw_name,
                "application": selected_app,
                "segments": segments,
                "total": sum(segments.values()),
            }
        )

    return {
        "ok": True,
        "role": role,
        "applications": apps,
        "selected_application": selected_app,
        "legend": PROGRESS_LEGEND,
        "chart_rows": chart_rows,
        "control_rows": control_rows,
        "totals": {
            "controls": len(control_rows),
            "frameworks": len(chart_rows),
        },
    }


def build_evidence_drill(
    repo: FrameworkControlRepository,
    *,
    framework_id: str,
    control_id: str,
    application: str,
    role: str = "",
) -> dict[str, Any]:
    app = (application or "").strip()
    if role:
        allowed = _applications_for_role(role, repo)
        if app and app not in allowed:
            return {"ok": False, "message": f"Application '{app}' is not in role scope."}
    doc = repo.get_control(framework_id, control_id)
    if not doc:
        return {"ok": False, "message": "Control not found."}
    fw = doc["framework"]
    fw_id = str(fw.get("id") or framework_id)
    fw_name = _legacy_framework_name(fw_id, doc)
    control = doc["control"]
    submissions = _index_persisted_submissions()
    policies = doc.get("linked_policies") or []
    policy = policies[0] if policies else None
    if not policy and control.get("policy_refs"):
        pol_id = control["policy_refs"][0]
        fw_doc = repo.get_framework(fw_id) or {}
        policy = next(
            (p for p in (fw_doc.get("policies") or []) if p.get("id") == pol_id),
            {"id": pol_id, "title": pol_id},
        )

    requirement_rows: list[dict[str, Any]] = []
    for evr in control.get("evidence_requirements") or []:
        sub = _find_submission(fw_id, fw_name, control, evr, app, submissions)
        req_state = _classify_requirement(sub)
        requirement_rows.append(
            {
                "requirement": evr,
                "submitted_evidence": sub,
                "status": req_state,
            }
        )

    control_status = _classify_control(
        repo=repo,
        framework_id=fw_id,
        framework_name=fw_name,
        control=control,
        application=app,
        submissions=submissions,
    )

    return {
        "ok": True,
        "framework": fw,
        "policy": policy,
        "control": control,
        "procedures": control.get("procedures") or [],
        "evidence_requirements": requirement_rows,
        "control_status": control_status,
        "application": app,
        "drill_path": [
            fw.get("display_name") or fw_name,
            (policy or {}).get("title", "—"),
            control.get("title"),
            "Procedures",
            "Required Evidence",
            "Submitted Evidence",
            control_status.replace("_", " ").title(),
        ],
    }
