"""Evidence approval / submission visual workflow engine — states, counters, timelines."""

from __future__ import annotations

from datetime import datetime, timezone

from app import ecs_state

OWNER_STATES = {
    "draft": "Draft",
    "uploaded": "Uploaded",
    "pending_app_owner": "Pending App Owner Approval",
    "pending_auditor": "Pending Auditor Approval",
    "submitted": "Pending Auditor Approval",
    "reupload": "Needs Rework",
    "rejected": "Rejected By Auditor",
    "rejected_owner": "Rejected By App Owner",
    "approved": "Closed",
    "clarification": "Needs Rework",
    "cancelled": "Draft Cancelled",
}

AUDITOR_STATES = {
    "pending": "Pending Auditor Approval",
    "submitted": "Pending Auditor Approval",
    "approved": "Closed",
    "rejected": "Rejected By Auditor",
    "reupload": "Needs Rework",
    "escalated": "Escalated",
    "exception": "Exception Raised",
    "clarification": "Pending Auditor Approval",
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
    from modules.shared.services.role_permissions import is_auditor, normalize_role

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
                {"label": "Pending Review", "value": pending, "tone": "warning", "metric": "pending_review"},
                {"label": "Approved", "value": approved, "tone": "success", "metric": "auditor_approved"},
                {"label": "Rejected", "value": rejected, "tone": "danger", "metric": "rejected"},
            ],
        }

    return {
        "role": r,
        "draft": drafts + missing_pending,
        "submitted": pending,
        "reupload_requested": reupload,
        "approved": approved,
        "counters": [
            {"label": "Draft", "value": drafts + missing_pending, "tone": "secondary", "metric": "draft"},
            {"label": "Submitted", "value": pending, "tone": "warning", "metric": "submitted"},
            {"label": "Re-upload Req", "value": reupload, "tone": "danger", "metric": "reupload"},
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
            {"label": "Approval Rate", "value": f"{approval_rate}%", "hint": "In-scope evidence", "tone": "success", "metric": "approval_rate"},
            {"label": "Avg Review Time", "value": "3.2d", "hint": "Auditor turnaround", "tone": "primary", "metric": "avg_review_time"},
            {"label": "Rejection Trend", "value": "↓ 12%", "hint": "Month over month", "tone": "warning", "metric": "rejection_trend"},
            {"label": "Pending Aging", "value": f"{pending} items", "hint": "Avg 8 days in queue", "tone": "info", "metric": "pending_aging"},
            {"label": "Auditor SLA", "value": "94.5%", "hint": "Within 5-day target", "tone": "teal", "metric": "auditor_sla"},
        ],
    }


def build_queues(role: str) -> dict:
    """Role-specific queue labels and counts."""
    from modules.shared.services.role_permissions import is_auditor

    s = build_summary(role)
    if is_auditor(role):
        return {
            "queues": [
                {"id": "pending", "label": "Pending Auditor Review", "count": s["pending_review"], "metric": "pending_review"},
                {"id": "approved", "label": "Recently Approved", "count": s["approved"], "metric": "auditor_approved"},
                {"id": "rejected", "label": "Rejected Evidence", "count": s["rejected"], "metric": "rejected"},
                {"id": "escalated", "label": "Escalated Evidence", "count": s.get("escalated", 0), "metric": "escalated"},
            ]
        }
    return {
        "queues": [
            {"id": "draft", "label": "Draft Evidence", "count": s["draft"], "metric": "draft"},
            {"id": "submitted", "label": "Submitted Evidence", "count": s["submitted"], "metric": "submitted"},
            {"id": "reupload", "label": "Re-upload Requested", "count": s["reupload_requested"], "metric": "reupload"},
            {"id": "approved", "label": "Auditor Approved", "count": s["approved"], "metric": "auditor_approved"},
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
    from modules.frameworks.engines.framework_catalog import resolve_framework_name
    from modules.governance.engines.governance_relational_model import build_relational_view

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
        # Phase 4 Step 3: mirror closure to the durable store (flag-gated, best-effort).
        try:
            from app.observations.store import persist_close

            persist_close(oid, closed_by=user, role=role, detail={
                "framework": fw, "control": control, "control_id": control_id})
        except Exception:  # noqa: BLE001 - durability must never break close
            pass
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
        from modules.shared.services.audit_trail import log_event
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


def record_transition(key: str, action: str, user: str, role: str, detail: str = "", *, previous_status: str = "", new_status: str = "") -> None:
    state = resolve_state(key)
    prev = previous_status or state.get("owner_label", "Draft")
    new = new_status or _action_to_status(action)
    trail = ecs_state.evidence_approval_trail.setdefault(key, [])
    entry = {
        "timestamp": _ts(),
        "action": action,
        "actor": user,
        "user": user,
        "role": role,
        "detail": detail,
        "comments": detail,
        "previous_status": prev,
        "new_status": new,
    }
    trail.append(entry)
    ecs_state.workflow_audit_history.setdefault(key, []).append(entry)


def _action_to_status(action: str) -> str:
    mapping = {
        "submitted": "Pending Auditor Approval",
        "approved": "Closed",
        "rejected": "Rejected By Auditor",
        "reupload": "Needs Rework",
        "owner_approved": "Pending Auditor Approval",
        "owner_rejected": "Rejected By App Owner",
    }
    return mapping.get(action, action.replace("_", " ").title())


def resolve_upload_workflow_target(control: dict) -> dict[str, str]:
    """Map a persisted control payload to generic workflow coordinates."""
    from modules.frameworks.engines.framework_catalog import resolve_framework_name

    frameworks = list(control.get("frameworks") or [])
    if not frameworks:
        coverage = str(control.get("framework_coverage") or "")
        if coverage:
            frameworks = [part.strip() for part in coverage.split(",") if part.strip()]
    framework = resolve_framework_name(frameworks[0] if frameworks else "DB Baselining")
    control_id = str(control.get("control_id") or control.get("query_id") or "")
    control_name = str(control.get("control_name") or control_id or "Governance Control")
    return {
        "framework": framework,
        "control_name": control_name,
        "control_id": control_id,
        "query_id": control_id,
    }


def enroll_persisted_evidence(
    upload: dict,
    *,
    control: dict,
    artifact: dict | None = None,
    source_connector: str = "PREDEFINED_QUERY",
) -> dict[str, str]:
    """Place a persisted upload into the generic App Owner workflow queue."""
    target = resolve_upload_workflow_target(control)
    key = ecs_state.control_key(target["framework"], target["control_name"])
    evidence_id = str(upload.get("evidence_id") or "")
    version = int(upload.get("version") or upload.get("evidence_version") or 1)
    object_key = str((upload.get("metadata") or {}).get("object_key") or upload.get("object_key") or "")
    sha256 = str(upload.get("sha256") or (upload.get("metadata") or {}).get("content_sha256") or "")
    custody_mode = str(upload.get("custody_mode") or "")
    now = _ts()
    upload.update({
        "workflow_status": "Pending App Owner Review",
        "validation_status": "Pending Review",
        "lifecycle": "Draft",
        "status": "Pending App Owner Review",
        "source_connector": source_connector,
        "query_id": target["query_id"],
        "evidence_version": version,
        "object_key": object_key,
        "environment": upload.get("environment") or str((artifact or {}).get("environment") or ""),
        "framework": target["framework"],
        "application": (upload.get("application_tags") or ["Net Banking"])[0]
        if upload.get("application_tags")
        else str((artifact or {}).get("application") or "Net Banking"),
    })
    enrollment = {
        "key": key,
        "framework": target["framework"],
        "control_name": target["control_name"],
        "control_id": target["control_id"],
        "query_id": target["query_id"],
        "evidence_id": evidence_id,
        "evidence_version": version,
        "application": upload["application"],
        "environment": upload.get("environment") or "",
        "source_connector": source_connector,
        "custody_mode": custody_mode,
        "object_key": object_key,
        "sha256": sha256,
        "status": "Pending App Owner Review",
        "uploaded_at": upload.get("uploaded_at") or now,
        "uploaded_by": upload.get("uploaded_by") or "",
        "artifact_preview": (artifact or {}).get("result") or [],
        "framework_tags": list(upload.get("framework_tags") or []),
    }
    for stale_id, stale in list(ecs_state.uploaded_evidence_enrollments.items()):
        if isinstance(stale, dict) and stale.get("key") == key and stale.get("evidence_id") not in ("", evidence_id):
            ecs_state.uploaded_evidence_enrollments.pop(stale.get("evidence_id"), None)
    ecs_state.uploaded_evidence_enrollments[evidence_id] = enrollment
    ecs_state.uploaded_evidence_enrollments[key] = enrollment
    return enrollment


def get_enrollment(*, evidence_id: str = "", key: str = "") -> dict | None:
    if evidence_id:
        row = ecs_state.uploaded_evidence_enrollments.get(evidence_id)
        if isinstance(row, dict) and row.get("evidence_id"):
            return row
    if key:
        row = ecs_state.uploaded_evidence_enrollments.get(key)
        if isinstance(row, dict) and row.get("evidence_id"):
            return row
    return None


def build_enrolled_owner_queue_items() -> list[dict]:
    """Dynamic owner-queue rows for persisted uploads outside the static catalog."""
    from modules.governance.engines.workflow_module import PRIORITY_ORDER, _enrich_queue_item

    items: list[dict] = []
    seen: set[str] = set()
    for row in ecs_state.uploaded_evidence_enrollments.values():
        if not isinstance(row, dict) or not row.get("key"):
            continue
        key = row["key"]
        if key in seen or key in ecs_state.approved_controls or key in ecs_state.submitted_controls:
            continue
        if key in ecs_state.cancelled_drafts:
            continue
        seen.add(key)
        wf_code = "rejected" if key in ecs_state.rejected_controls else "pending"
        wf_label = (
            "Rejected by Auditor"
            if wf_code == "rejected"
            else "Draft — Pending App Owner Review"
        )
        item = {
            "key": key,
            "framework": row["framework"],
            "application": row.get("application", "Net Banking"),
            "control": row["control_name"],
            "control_id": row.get("control_id") or row.get("query_id") or "",
            "evidence_name": f"Predefined Query {row.get('query_id', '')}".strip(),
            "evidence_id": row.get("evidence_id", ""),
            "mock_file": f"PREDEFINED_QUERY_{row.get('query_id', 'PQ')}.json",
            "evidence_status": "Current",
            "auditor_comments": ecs_state.rejected_controls.get(key, {}).get("reason", "—"),
            "due_date": "2026-09-30",
            "aging_days": 0,
            "priority": "High" if wf_code == "rejected" else "Medium",
            "submitted_timestamp": row.get("uploaded_at", _ts()),
            "expiry_date": "2026-09-30",
            "workflow_status": wf_label,
            "workflow_code": wf_code,
            "action_type": "Rejected evidence requires resubmission"
            if wf_code == "rejected"
            else "Evidence upload pending",
            "app_owner": row.get("uploaded_by") or "App Owner",
            "risk_rating": "High" if wf_code == "rejected" else "Medium",
            "evidence_health": "Valid",
            "expiry_risk": "None",
            "escalated": key in ecs_state.escalated_controls,
            "server_name": row.get("application", ""),
            "environment": row.get("environment", ""),
            "region": "Central",
            "owner_comments": ecs_state.owner_comments.get(key, []),
            "source_connector": row.get("source_connector", ""),
        }
        items.append(_enrich_queue_item(item))
    items.sort(key=lambda x: (PRIORITY_ORDER.get(x["priority"], 9), -x["aging_days"]))
    return items


def build_enrolled_auditor_queue_items() -> list[dict]:
    from modules.governance.engines.workflow_module import _enrich_queue_item

    items: list[dict] = []
    for key in ecs_state.submitted_controls:
        enrollment = get_enrollment(key=key)
        if not enrollment:
            continue
        item = {
            "key": key,
            "framework": enrollment["framework"],
            "application": enrollment.get("application", "Net Banking"),
            "control": enrollment["control_name"],
            "control_id": enrollment.get("control_id") or enrollment.get("query_id") or "",
            "evidence_name": f"Predefined Query {enrollment.get('query_id', '')}".strip(),
            "evidence_id": enrollment.get("evidence_id", ""),
            "mock_file": f"PREDEFINED_QUERY_{enrollment.get('query_id', 'PQ')}.json",
            "evidence_status": "Current",
            "auditor_comments": "Awaiting auditor review.",
            "due_date": "2026-09-30",
            "aging_days": 0,
            "priority": "Medium",
            "submitted_timestamp": ecs_state.submitted_meta.get(key, {}).get("submitted_at", _ts()),
            "expiry_date": "2026-09-30",
            "workflow_status": "Pending Auditor Review",
            "workflow_code": "submitted",
            "action_type": "Observation closure pending",
            "app_owner": enrollment.get("uploaded_by") or "App Owner",
            "risk_rating": "Medium",
            "evidence_health": "Valid",
            "expiry_risk": "None",
            "escalated": key in ecs_state.escalated_controls,
            "server_name": enrollment.get("application", ""),
            "environment": enrollment.get("environment", ""),
            "region": "Central",
            "owner_comments": ecs_state.owner_comments.get(key, []),
            "source_connector": enrollment.get("source_connector", ""),
        }
        items.append(_enrich_queue_item(item))
    return items


def open_observation_for_rejection(
    *,
    framework: str,
    control_name: str,
    control_id: str = "",
    reason: str,
    user: str,
    evidence_id: str = "",
) -> str:
    """Open or refresh a workflow observation when auditor rejects evidence."""
    from modules.frameworks.engines.framework_catalog import resolve_framework_name

    fw = resolve_framework_name(framework)
    obs_id = observation_id_for(fw, control_name, control_id)
    ts = _ts()
    rec = ecs_state.missing_evidence_registry.get(obs_id) or {
        "observation_id": obs_id,
        "framework": fw,
        "control_id": control_id or control_name,
        "control_name": control_name,
        "control": control_name,
        "application": "Net Banking",
        "missing_evidence": reason,
        "evidence_type": "Predefined Query JSON",
        "status": "Rejected",
        "observation_severity": "Major",
        "risk": "High",
        "owner": user,
        "history": [],
    }
    rec.update({
        "status": "Rejected",
        "missing_evidence": reason,
        "evidence_id": evidence_id or rec.get("evidence_id", ""),
        "rejected_by": user,
        "rejected_at": ts,
    })
    rec.setdefault("history", []).append(
        {"date": ts, "action": "Rejected By Auditor", "actor": user, "remarks": reason},
    )
    ecs_state.missing_evidence_registry[obs_id] = rec
    return obs_id


def drill_workflow_metric(role: str, metric: str, count: int = 0) -> dict:
    """Enterprise-wide evidence workflow drill — traceable to displayed counts."""
    from modules.shared.utils.demo_data_standards import ensure_drill_rows, generate_standard_drill_row, pick, seed, between
    from modules.shared.utils.demo_data_standards import BANKING_APPLICATIONS, BANKING_OWNERS

    metric = (metric or "submitted").strip().lower().replace("-", "_").replace(" ", "_")
    ctx = build_workflow_context(role)
    label = metric.replace("_", " ").title()
    for block in (
        ctx["summary"].get("counters", []),
        ctx["analytics"].get("cards", []),
        ctx["queues"].get("queues", []),
    ):
        for item in block:
            if item.get("metric") == metric:
                label = item.get("label", label)
                break

    status_map = {
        "draft": "Draft",
        "submitted": "Pending Auditor Approval",
        "pending_review": "Pending Auditor Approval",
        "reupload": "Needs Rework",
        "rejected": "Rejected By Auditor",
        "auditor_approved": "Closed",
        "approval_rate": "Closed",
        "avg_review_time": "Pending Auditor Approval",
        "rejection_trend": "Needs Rework",
        "pending_aging": "Pending App Owner Approval",
        "escalated": "Escalated",
    }
    status = status_map.get(metric, "Open")

    rows: list[dict] = []
    for i in range(12):
        s = seed("ewf", role, metric, i)
        app = pick(s, BANKING_APPLICATIONS)
        row = generate_standard_drill_row(i, metric=f"ewf:{metric}", application=app)
        row.update({
            "observation": f"OBS-EWF-{i + 1:04d}",
            "reviewer": pick(s >> 2, ["S. Nair (Auditor)", "Internal Audit"]),
            "status": status,
            "owner": pick(s >> 4, BANKING_OWNERS),
            "created_date": f"2026-04-{(i % 25) + 1:02d}",
            "updated_date": f"2026-05-{(i % 20) + 1:02d}",
            "review_days": f"{between(s >> 6, 1, 8)}d",
        })
        rows.append(row)

    from modules.shared.drilldowns.ecs_universal_drill_engine import _target_rows, UNIVERSAL_COLUMNS

    target = _target_rows(count or ctx["summary"].get("submitted", 0))
    rows = ensure_drill_rows(rows, target, metric=metric)
    for r in rows:
        for c in UNIVERSAL_COLUMNS:
            r.setdefault(c, "—")

    history: list[dict] = []
    for i, entry in enumerate(ecs_state.workflow_audit_history.get(f"ewf:{metric}", [])[:5]):
        history.append(entry)
    if not history:
        for i in range(8):
            history.append({
                "user": pick(seed(i, "u"), BANKING_OWNERS),
                "role": pick(seed(i, "r"), ["Application Owner", "Auditor", "Compliance Officer"]),
                "timestamp": f"2026-05-{(i % 20) + 1:02d} 10:{i:02d} UTC",
                "previous_status": pick(seed(i, "p"), list(OWNER_STATES.values())),
                "new_status": status,
                "comments": f"Workflow transition for {label}",
            })

    return {
        "ok": True,
        "title": f"{label} — Evidence Workflow",
        "rows": rows,
        "columns": UNIVERSAL_COLUMNS,
        "sections": {"audit_history": history, "approval_history": rows[:10]},
        "metric": metric,
        "role": role,
    }
