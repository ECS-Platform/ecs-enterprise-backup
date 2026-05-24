"""Enterprise evidence review screen — metadata, preview, validation, workflow history."""

from __future__ import annotations

from datetime import datetime, timezone

from app import ecs_state
from app.audit_trail import get_audit_trail, get_approval_history, get_version_history
from app.evidence_repository import get_reuse_graph
from app.framework_catalog import FRAMEWORK_CATALOG, get_framework_controls

REJECT_REASON_PRESETS = [
    "Expired evidence",
    "Incorrect screenshot",
    "Missing timestamps",
    "Incomplete configuration",
    "Wrong application",
    "Invalid evidence mapping",
    "Poor quality evidence",
]

PREVIEW_TEMPLATES = {
    "pdf": """┌─────────────────────────────────────────────────────────────┐
│ ENTERPRISE COMPLIANCE ARTEFACT — CONTROL ATTESTATION          │
│ Document: {filename}                                          │
│ Classification: Internal — Audit Restricted                   │
├─────────────────────────────────────────────────────────────┤
│ Framework     : {framework}                                   │
│ Control       : {control}                                     │
│ Application   : {application}                                 │
│ Collected     : {upload_ts}                                   │
│ Attestation   : Production configuration verified by App Owner│
│ Reviewer Note : {comments}                                    │
└─────────────────────────────────────────────────────────────┘""",
    "png": """╔══════════════════════════════════════╗
║  SCREENSHOT EVIDENCE — {evidence_id}   ║
╠══════════════════════════════════════╣
║ [Simulated IAM Console Capture]      ║
║ MFA Enforcement: ENABLED (100%)      ║
║ Privileged Users: 42 mapped          ║
║ Last Policy Sync: {upload_ts}        ║
║ Environment: {environment}           ║
╚══════════════════════════════════════╝""",
    "csv": """timestamp,event,user,source,severity
2026-05-24T06:00:01Z,PRIV_SESSION_START,admin_jump,PAM,INFO
2026-05-24T06:00:45Z,MFA_CHALLENGE_OK,r.mehta,IAM,INFO
2026-05-24T06:01:12Z,COMMAND_EXEC,sudo systemctl,HOST,WARN
2026-05-24T06:02:00Z,SESSION_END,r.mehta,PAM,INFO
# Sample log extract — {filename}""",
    "xlsx": """[Spreadsheet Preview — {filename}]
Sheet: Compliance_Matrix | Rows: 248 | Controls mapped: 17
Column A: Control ID | B: Evidence Ref | C: Status | D: Owner
Sample: {control_id} | {evidence_id} | Under Review | {owner}""",
    "zip": """[SIEM Export Archive — {filename}]
├── audit_log_chain_manifest.json
├── hash_verification.sha256
├── events_2026-05-01_to_2026-05-24.ndjson (412,804 events)
└── collector_attestation.pdf
Immutable log chain: VERIFIED""",
    "default": """[Configuration Snapshot — {filename}]
Server: {server}
Environment: {environment} | Region: {region}
Control: {control}
Baseline hash: a4f9c2e8b1d0… | Last scan: {upload_ts}
Status: {evidence_status}""",
}


def _find_evidence(framework: str, control: str, evidence_id: str) -> tuple[dict, dict] | tuple[None, None]:
    for ctrl in get_framework_controls(framework):
        if ctrl["control"] != control:
            continue
        for ev in ctrl["evidences"]:
            if ev["evidence_id"] == evidence_id:
                return ctrl, ev
        if ctrl["evidences"]:
            return ctrl, ctrl["evidences"][0]
    return None, None


def _preview_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "pdf":
        return "pdf"
    if ext in ("png", "jpg", "jpeg"):
        return "png"
    if ext == "csv":
        return "csv"
    if ext in ("xlsx", "xls"):
        return "xlsx"
    if ext == "zip":
        return "zip"
    return "default"


def _build_preview(ev: dict, ctrl: dict, framework: str) -> dict:
    ptype = _preview_type(ev.get("mock_file", ""))
    template = PREVIEW_TEMPLATES[ptype]
    content = template.format(
        filename=ev.get("mock_file", ""),
        framework=framework,
        control=ctrl["control"],
        application=ev.get("application_name", ""),
        upload_ts=ev.get("upload_timestamp", ""),
        comments=ev.get("comments", "")[:80],
        evidence_id=ev.get("evidence_id", ""),
        environment=ev.get("environment", ""),
        server=ev.get("server_name", ""),
        region=ev.get("region", ""),
        evidence_status=ev.get("evidence_status", ""),
        control_id=ctrl.get("control_id", ""),
        owner=ev.get("uploaded_by", ""),
    )
    labels = {
        "pdf": "PDF Attestation Preview",
        "png": "Screenshot Preview",
        "csv": "Log Extract Preview",
        "xlsx": "Compliance Matrix Preview",
        "zip": "SIEM Export Preview",
        "default": "Configuration Snapshot Preview",
    }
    return {"type": ptype, "label": labels[ptype], "content": content}


def _validation_scores(ev: dict, key: str) -> dict:
    ev_status = ev.get("evidence_status", "Current")
    completeness = 92 if ev.get("comments") else 74
    confidence = 88 if ev.get("audit_status") in ("Approved", "Under Review") else 76
    if ev_status == "Expired":
        expiry_health = "Expired"
        risk = "Critical"
        completeness -= 25
    elif ev_status == "Due for Refresh":
        expiry_health = "Expiring within 30 days"
        risk = "High"
        completeness -= 10
    else:
        expiry_health = "Valid"
        risk = "Low"
    if key in ecs_state.rejected_controls:
        risk = "High"
        confidence -= 15
    duplicate = "Possible duplicate — review reuse mapping" if ev.get("evidence_id", "").endswith("1") else "No duplicate detected"
    reuse = "Candidate for cross-framework reuse" if completeness >= 85 else "Single-use evidence"
    return {
        "completeness_score": max(30, min(completeness, 99)),
        "confidence_score": max(30, min(confidence, 99)),
        "expiry_health": expiry_health,
        "duplicate_detection": duplicate,
        "reuse_recommendation": reuse,
        "risk_level": risk,
    }


def _workflow_history(framework: str, control: str, evidence_id: str) -> list[dict]:
    history = []
    for ev in get_audit_trail(50):
        if ev.get("framework") == framework and (ev.get("control") == control or ev.get("evidence_id") == evidence_id):
            history.append(ev)
    for ev in get_approval_history(20):
        if ev.get("framework") == framework and ev.get("control") == control:
            history.append({
                "timestamp": ev["timestamp"],
                "action": ev.get("note", "Approval event"),
                "actor": ev.get("auditor", ""),
                "role": "Auditor",
                "detail": ev.get("reason", ev.get("note", "")),
            })
    key = ecs_state.control_key(framework, control)
    if key in ecs_state.submitted_meta:
        meta = ecs_state.submitted_meta[key]
        history.append({
            "timestamp": meta.get("submitted_at", ""),
            "action": "Submitted To Auditor",
            "actor": meta.get("submitted_by", ""),
            "role": "App Owner",
            "detail": "Evidence package submitted for auditor review",
        })
    if key in ecs_state.approved_controls:
        appr = ecs_state.approved_controls[key]
        if isinstance(appr, dict):
            history.append({
                "timestamp": appr.get("approved_at", ""),
                "action": "Auditor Approved",
                "actor": appr.get("approved_by", ""),
                "role": "Auditor",
                "detail": appr.get("note", "Observation closed"),
            })
    if key in ecs_state.rejected_controls:
        rej = ecs_state.rejected_controls[key]
        history.append({
            "timestamp": rej.get("rejected_at", ""),
            "action": "Rejected By Auditor" if not rej.get("internal") else "Rejected Internally",
            "actor": rej.get("rejected_by", ""),
            "role": "App Owner" if rej.get("internal") else "Auditor",
            "detail": rej.get("reason", ""),
        })
    for view in ecs_state.evidence_views.get(key, []):
        history.append({
            "timestamp": view["timestamp"],
            "action": "Viewed Evidence",
            "actor": view["actor"],
            "role": view.get("role", ""),
            "detail": f"Review opened for {evidence_id}",
        })
    history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return history[:15]


def _reuse_mapping(evidence_id: str) -> list[dict]:
    mappings = []
    for g in get_reuse_graph().get("groups", []):
        if g.get("filename", "").startswith(evidence_id[:8]) or evidence_id in g.get("group_id", ""):
            for link in g.get("linked_controls", []):
                mappings.append(link)
    return mappings[:6]


def _workflow_state(key: str) -> dict:
    if key in ecs_state.approved_controls:
        appr = ecs_state.approved_controls[key]
        return {
            "code": "approved",
            "label": "Observation Closed — Auditor Approved",
            "locked": True,
            "approved_by": appr.get("approved_by", "") if isinstance(appr, dict) else "",
            "approved_at": appr.get("approved_at", "") if isinstance(appr, dict) else "",
        }
    if key in ecs_state.submitted_controls:
        return {"code": "submitted", "label": "Pending Auditor Review", "locked": False}
    if key in ecs_state.rejected_controls:
        return {"code": "rejected", "label": "Rejected By Auditor", "locked": False}
    if key in ecs_state.clarification_controls:
        return {"code": "clarification", "label": "Clarification Required", "locked": False}
    if key in ecs_state.cancelled_drafts:
        return {"code": "cancelled", "label": "Draft Cancelled", "locked": True}
    if key in ecs_state.owner_drafts:
        return {"code": "draft", "label": "Draft Saved", "locked": False}
    return {"code": "pending", "label": "Draft — Pending Owner Review", "locked": False}


def record_evidence_view(framework: str, control: str, evidence_id: str, actor: str, role: str):
    key = ecs_state.control_key(framework, control)
    ecs_state.evidence_views.setdefault(key, []).insert(
        0,
        {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "actor": actor,
            "role": role,
            "evidence_id": evidence_id,
        },
    )
    from app.audit_trail import log_event

    log_event("Viewed Evidence", actor, framework, control, f"Opened review for {evidence_id}", evidence_id, role=role)


def build_evidence_review(
    framework: str,
    control: str,
    evidence_id: str,
    role: str,
    user: str,
    *,
    log_view: bool = True,
) -> dict | None:
    ctrl, ev = _find_evidence(framework, control, evidence_id)
    if not ctrl or not ev:
        return None
    key = ecs_state.control_key(framework, control)
    if log_view:
        record_evidence_view(framework, control, ev["evidence_id"], user, role)

    control_desc = ctrl.get("control_description", ev.get("comments", ""))
    wf = _workflow_state(key)

    return {
        "framework": framework,
        "control": control,
        "control_id": ctrl.get("control_id", ""),
        "control_description": control_desc,
        "evidence": ev,
        "evidence_id": ev["evidence_id"],
        "metadata": {
            "framework": framework,
            "control_id": ctrl.get("control_id", ""),
            "control_description": control_desc,
            "evidence_name": ev.get("evidence_name", ""),
            "evidence_id": ev.get("evidence_id", ""),
            "application_name": ev.get("application_name", ""),
            "upload_timestamp": ev.get("upload_timestamp", ""),
            "expiry_date": ev.get("expiry_date", ""),
            "source_system": ev.get("evidence_source", "Manual Upload"),
            "submitted_by": ev.get("uploaded_by", ""),
            "evidence_version": ev.get("evidence_version", "v1.0"),
            "evidence_status": ev.get("evidence_status", "Current"),
        },
        "preview": _build_preview(ev, ctrl, framework),
        "validation": _validation_scores(ev, key),
        "workflow": wf,
        "workflow_history": _workflow_history(framework, control, ev["evidence_id"]),
        "owner_comments": ecs_state.owner_comments.get(key, []),
        "reject_reason": ecs_state.rejected_controls.get(key, {}).get("reason", "") if key in ecs_state.rejected_controls else "",
        "lineage": get_version_history(ev["evidence_id"]),
        "reuse_mapping": _reuse_mapping(ev["evidence_id"]),
        "reject_presets": REJECT_REASON_PRESETS,
        "role": role,
        "user": user,
        "key": key,
    }


def review_url(framework: str, control: str, evidence_id: str, role: str, user: str) -> str:
    from urllib.parse import quote

    return (
        f"/evidence/review?framework_name={quote(framework)}"
        f"&control_name={quote(control)}&evidence_id={quote(evidence_id)}"
        f"&role={quote(role)}&user={quote(user)}"
    )
