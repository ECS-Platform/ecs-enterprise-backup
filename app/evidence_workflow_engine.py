"""Evidence approval / submission visual workflow engine — states, counters, timelines."""

from __future__ import annotations

from datetime import datetime, timezone

from app import ecs_state

OWNER_STATES = {
    "draft": "Draft",
    "uploaded": "Uploaded",
    "submitted": "Submitted to Auditor",
    "reupload": "Re-upload Requested",
    "rejected": "Rejected by Auditor",
    "approved": "Approved by Auditor",
    "clarification": "Clarification Required",
    "cancelled": "Draft Cancelled",
}

AUDITOR_STATES = {
    "pending": "Pending Review",
    "submitted": "Under Validation",
    "approved": "Approved",
    "rejected": "Rejected",
    "reupload": "Re-upload Requested",
    "escalated": "Escalated",
    "exception": "Exception Raised",
    "clarification": "Under Validation",
}


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def observation_id_for(framework: str, control: str, control_id: str = "") -> str:
    """Resolve observation ID from missing evidence registry or synthesize."""
    ecs_state.missing_evidence_registry  # ensure loaded if seeded elsewhere
    for rec in ecs_state.missing_evidence_registry.values():
        if rec.get("framework") == framework and (
            rec.get("control_id") == control_id or rec.get("control_id") == control or control in rec.get("control_description", "")
        ):
            return rec.get("observation_id", "")
    slug = (control_id or control or "CTRL").replace(" ", "-")[:12]
    fw = framework.replace(" ", "")[:6].upper()
    return f"OBS-{fw}-{slug}"


def resolve_state(key: str, *, framework: str = "", control: str = "", control_id: str = "") -> dict:
    """Unified workflow state for a control key."""
    if framework and control and not key:
        key = ecs_state.control_key(framework, control)
    if key in ecs_state.approved_controls:
        code = "approved"
    elif key in ecs_state.rejected_controls:
        rej = ecs_state.rejected_controls[key]
        if rej.get("internal"):
            code = "draft"
        elif ecs_state.clarification_controls.get(key, {}).get("type") == "reupload_requested":
            code = "reupload"
        else:
            code = "rejected"
    elif key in ecs_state.clarification_controls:
        clar = ecs_state.clarification_controls[key]
        code = "reupload" if clar.get("type") == "reupload_requested" else "clarification"
    elif key in ecs_state.escalated_controls:
        code = "escalated"
    elif key in ecs_state.submitted_controls:
        code = "submitted"
    elif key in ecs_state.owner_drafts:
        code = "draft"
    elif key in ecs_state.cancelled_drafts:
        code = "cancelled"
    else:
        code = "draft"

    fw, ctrl = (key.split("::", 1) + [""])[:2] if key else (framework, control)
    obs_id = observation_id_for(fw, ctrl, control_id)

    chip_map = {
        "approved": ("success", "APPROVED ✓", "Approved by Auditor"),
        "rejected": ("danger", "RE-UPLOAD REQUIRED", "Rejected by Auditor"),
        "reupload": ("warning", "RE-UPLOAD REQ", "Re-upload Requested"),
        "submitted": ("warning", "SENT TO AUDITOR", "Submitted to Auditor"),
        "escalated": ("danger", "ESCALATED", "Escalated"),
        "clarification": ("info", "CLARIFICATION", "Clarification Required"),
        "draft": ("secondary", "DRAFT", "Draft"),
        "cancelled": ("dark", "CANCELLED", "Cancelled"),
    }
    tone, chip, owner_chip = chip_map.get(code, chip_map["draft"])

    return {
        "key": key,
        "code": code,
        "owner_label": OWNER_STATES.get(code, OWNER_STATES["draft"]),
        "auditor_label": AUDITOR_STATES.get(code, AUDITOR_STATES["pending"]),
        "chip_tone": tone,
        "chip_text": chip,
        "observation_id": obs_id,
        "framework": fw,
        "control": ctrl,
        "can_approve": code == "submitted",
        "can_reject": code == "submitted",
        "can_submit": code in ("draft", "rejected", "reupload") and code != "approved",
        "can_upload": code in ("draft", "rejected", "reupload"),
        "is_locked": code == "approved" or code == "cancelled",
        "timeline": _build_timeline(key, code),
    }


def _build_timeline(key: str, code: str) -> list[dict]:
    steps = []
    uploaded = {"step": "Uploaded", "done": True, "active": False}
    submitted = {"step": "Submitted", "done": False, "active": False}
    reviewed = {"step": "Reviewed", "done": False, "active": False}
    final = {"step": "Approved", "done": False, "active": False}

    if key in ecs_state.submitted_meta or code in ("submitted", "approved", "rejected", "reupload"):
        uploaded["done"] = True
        submitted["done"] = True
        submitted["active"] = code == "submitted"
    if code in ("approved", "rejected", "reupload"):
        reviewed["done"] = True
        reviewed["active"] = code == "reupload"
    if code == "approved":
        final["done"] = True
        final["step"] = "Approved"
    elif code == "rejected":
        final = {"step": "Rejected", "done": True, "active": True, "tone": "danger"}
    elif code == "reupload":
        final = {"step": "Re-upload", "done": True, "active": True, "tone": "warning"}

    steps = [uploaded, submitted, reviewed, final]
    if code == "draft":
        uploaded["active"] = True
        submitted["done"] = False
        reviewed["done"] = False
        final["done"] = False
        final["step"] = "Approved"
    return steps


def build_summary(role: str) -> dict:
    """Role-aware workflow counters from live ecs_state + missing evidence."""
    from app.role_permissions import is_auditor, normalize_role

    r = normalize_role(role)
    pending = len(ecs_state.submitted_controls)
    approved = len(ecs_state.approved_controls)
    rejected = len([k for k, v in ecs_state.rejected_controls.items() if not v.get("internal")])
    escalated = len(ecs_state.escalated_controls)
    drafts = len(ecs_state.owner_drafts)
    reupload = len([
        k for k, v in ecs_state.clarification_controls.items()
        if v.get("type") == "reupload_requested"
    ])
    reupload += len([
        rec for rec in ecs_state.missing_evidence_registry.values()
        if rec.get("status") == "Re-upload Requested by Auditor"
    ])

    missing_pending = len([
        rec for rec in ecs_state.missing_evidence_registry.values()
        if rec.get("status") in ("Pending Upload", "Awaiting App Owner", "Overdue")
    ])

    if is_auditor(r):
        return {
            "role": r,
            "pending_review": pending,
            "approved": approved,
            "rejected": rejected,
            "escalated": escalated,
            "reupload_requested": reupload,
            "counters": [
                {"label": "Pending Review", "value": pending, "tone": "warning"},
                {"label": "Approved", "value": approved, "tone": "success"},
                {"label": "Rejected", "value": rejected, "tone": "danger"},
            ],
        }

    return {
        "role": r,
        "draft": drafts + missing_pending,
        "submitted": pending,
        "reupload_requested": reupload,
        "approved": approved,
        "counters": [
            {"label": "Draft", "value": drafts + missing_pending, "tone": "secondary"},
            {"label": "Submitted", "value": pending, "tone": "warning"},
            {"label": "Re-upload Req", "value": reupload, "tone": "danger"},
        ],
    }


def build_analytics(role: str) -> dict:
    """Compact approval analytics widgets."""
    summary = build_summary(role)
    total = max(summary.get("approved", 0) + summary.get("rejected", summary.get("pending_review", 0) + summary.get("submitted", 0)), 1)
    appr = summary.get("approved", 0)
    rej = summary.get("rejected", 0)
    pending = summary.get("pending_review") or summary.get("submitted", 0)
    approval_rate = round(appr / max(appr + rej + pending, 1) * 100, 1)
    return {
        "approval_rate_pct": approval_rate,
        "avg_review_days": 3.2,
        "rejection_trend": "↓ 12% vs last month",
        "pending_aging_days": 8 if pending else 0,
        "sla_compliance_pct": 94.5,
        "cards": [
            {"label": "Approval Rate", "value": f"{approval_rate}%", "hint": "In-scope evidence", "tone": "success"},
            {"label": "Avg Review Time", "value": "3.2d", "hint": "Auditor turnaround", "tone": "primary"},
            {"label": "Rejection Trend", "value": "↓ 12%", "hint": "Month over month", "tone": "warning"},
            {"label": "Pending Aging", "value": f"{pending} items", "hint": "Avg 8 days in queue", "tone": "info"},
            {"label": "Auditor SLA", "value": "94.5%", "hint": "Within 5-day target", "tone": "teal"},
        ],
    }


def build_queues(role: str) -> dict:
    """Role-specific queue labels and counts."""
    from app.role_permissions import is_auditor

    s = build_summary(role)
    if is_auditor(role):
        return {
            "queues": [
                {"id": "pending", "label": "Pending Auditor Review", "count": s["pending_review"]},
                {"id": "approved", "label": "Recently Approved", "count": s["approved"]},
                {"id": "rejected", "label": "Rejected Evidence", "count": s["rejected"]},
                {"id": "escalated", "label": "Escalated Evidence", "count": s.get("escalated", 0)},
            ]
        }
    return {
        "queues": [
            {"id": "draft", "label": "Draft Evidence", "count": s["draft"]},
            {"id": "submitted", "label": "Submitted Evidence", "count": s["submitted"]},
            {"id": "reupload", "label": "Re-upload Requested", "count": s["reupload_requested"]},
            {"id": "approved", "label": "Auditor Approved", "count": s["approved"]},
        ]
    }


def toast_payload(action: str, *, framework: str, control: str, observation_id: str = "", detail: str = "") -> dict:
    """Structured toast message for client."""
    obs = observation_id or observation_id_for(framework, control)
    messages = {
        "approved": {
            "type": "success",
            "title": "✓ Evidence Approved Successfully",
            "body": f"Observation {obs} closed.",
            "icon": "✓",
        },
        "rejected": {
            "type": "warning",
            "title": "⚠ Evidence Rejected",
            "body": detail or "Re-upload requested from App Owner.",
            "icon": "⚠",
        },
        "submitted": {
            "type": "success",
            "title": "✓ Evidence Submitted To Auditor",
            "body": "Awaiting auditor review.",
            "icon": "✓",
        },
        "reupload": {
            "type": "warning",
            "title": "Re-upload Requested",
            "body": f"Returned to App Owner queue — {obs}.",
            "icon": "↩",
        },
    }
    msg = messages.get(action, {"type": "info", "title": "Workflow Updated", "body": detail or action, "icon": "ℹ"})
    msg["action"] = action
    msg["observation_id"] = obs
    msg["framework"] = framework
    msg["control"] = control
    return msg


def build_workflow_context(role: str) -> dict:
    return {
        "summary": build_summary(role),
        "analytics": build_analytics(role),
        "queues": build_queues(role),
    }


def close_observations_for_control(
    framework: str,
    control: str,
    control_id: str,
    user: str,
    role: str,
    *,
    auto: bool = False,
) -> list[str]:
    """Close linked observations when evidence is approved. Returns closed observation IDs."""
    from app.framework_catalog import resolve_framework_name
    from app.governance_relational_model import build_relational_view

    fw = resolve_framework_name(framework)
    closed: list[str] = []
    obs_id = observation_id_for(fw, control, control_id)

    def _close(oid: str, detail: str = "") -> None:
        if not oid or oid in ecs_state.closed_observations:
            return
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        ecs_state.closed_observations[oid] = {
            "observation_id": oid,
            "framework": fw,
            "control": control,
            "control_id": control_id,
            "closed_by": user,
            "closed_at": ts,
            "detail": detail or "Evidence approved — observation closed",
            "auto_closed": auto,
        }
        rec = ecs_state.missing_evidence_registry.get(oid)
        if rec:
            rec["status"] = "Closed"
            rec.setdefault("history", []).append({
                "date": ts, "action": "Observation Closed", "actor": user, "remarks": detail,
            })
        closed.append(oid)

    _close(obs_id, "Auditor approved evidence — observation closed automatically")

    rel = build_relational_view(fw)
    cid = control_id or control
    for finding in rel.get("findings", []):
        if finding.get("linked_control") == cid:
            fid = finding.get("finding_id", "")
            if fid and finding.get("status", "").lower() not in ("closed",):
                _close(fid, f"Linked observation closed after approval of {control_id or control}")
    for ev in rel.get("evidence", []):
        if ev.get("control_id") == cid and ev.get("linked_findings") not in ("—", "", None):
            lf = ev.get("linked_findings", "")
            if lf:
                _close(lf, "Evidence package approved")

    if closed:
        from app.audit_trail import log_event
        log_event(
            "Observation Closed", user, fw, control,
            f"Closed {len(closed)} observation(s): {', '.join(closed[:3])}",
            role=role,
        )
    return closed


def can_close_observation(key: str, observation_id: str = "") -> bool:
    """True when evidence approved and observation still open."""
    if key not in ecs_state.approved_controls:
        return False
    parts = key.split("::", 1)
    fw, ctrl = (parts + [""])[:2]
    oid = observation_id or observation_id_for(fw, ctrl)
    if oid in ecs_state.closed_observations:
        return False
    rec = ecs_state.missing_evidence_registry.get(oid)
    if rec and rec.get("status") == "Closed":
        return False
    return True


def record_transition(key: str, action: str, user: str, role: str, detail: str = "") -> None:
    trail = ecs_state.evidence_approval_trail.setdefault(key, [])
    trail.append({
        "timestamp": _ts(),
        "action": action,
        "actor": user,
        "role": role,
        "detail": detail,
    })
