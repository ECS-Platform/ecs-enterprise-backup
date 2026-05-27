"""Enterprise evidence review screen — metadata, preview, validation, workflow history."""

from __future__ import annotations

from datetime import datetime, timezone

from app import ecs_state
from app.audit_trail import get_audit_trail, get_approval_history, get_version_history
from app.evidence_repository import get_reuse_graph
from app.framework_catalog import FRAMEWORK_CATALOG, get_framework_controls, get_all_evidence_records, resolve_framework_name

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


def resolve_control_name(framework: str, control_id: str = "", control_hint: str = "") -> str:
    """Resolve full control title from catalog or relational graph."""
    fw = resolve_framework_name(framework)
    if control_hint:
        return control_hint
    for ctrl in get_framework_controls(fw):
        if ctrl.get("control_id") == control_id or ctrl.get("control") == control_id:
            return ctrl["control"]
    from app.governance_relational_model import get_framework_graph
    for c in get_framework_graph(fw).get("controls", []):
        if c.get("control_id") == control_id:
            return c.get("control_name", control_id)
    return control_id or ""


def _relational_evidence_lookup(framework: str, evidence_id: str) -> tuple[dict, dict] | tuple[None, None]:
    from app.governance_relational_model import build_relational_view

    fw = resolve_framework_name(framework)
    rel = build_relational_view(fw)
    for ev in rel.get("evidence", []):
        if ev.get("evidence_id") != evidence_id:
            continue
        control_id = ev.get("control_id", "")
        control_name = ev.get("control_name") or ev.get("control") or ""
        if not control_name:
            for c in rel.get("controls", []):
                if c.get("control_id") == control_id:
                    control_name = c.get("control_name", control_id)
                    break
        if not control_name:
            control_name = resolve_control_name(fw, control_id)
        ctrl = {
            "control": control_name or control_id or "Governance Control",
            "control_id": control_id,
            "control_description": f"Control {control_id} — {ev.get('name', 'Evidence attestation')}",
        }
        mock_ext = {"Policy": "pdf", "SAST Report": "pdf", "SIEM Export": "zip", "Firewall Export": "csv"}.get(
            ev.get("type", ""), "pdf"
        )
        catalog_ev = {
            "evidence_id": ev["evidence_id"],
            "evidence_name": ev.get("name", ev["evidence_id"]),
            "mock_file": f"{ev['evidence_id']}.{mock_ext}",
            "application_name": ev.get("application", "Net Banking"),
            "application": ev.get("application", "Net Banking"),
            "uploaded_by": ev.get("uploaded_by", "App Owner"),
            "upload_timestamp": ev.get("uploaded_at", "2026-05-20 10:00 UTC"),
            "evidence_status": "Current" if ev.get("lifecycle") != "Expired" else "Expired",
            "audit_status": ev.get("lifecycle", "Pending Review"),
            "reviewer": ev.get("reviewer", ""),
            "comments": ev.get("comments", f"Relational evidence — {ev.get('type', 'Document')}"),
            "expiry_date": ev.get("expiry", "2026-12-31"),
            "evidence_source": ev.get("source_integration", "Manual Upload"),
            "server_name": ev.get("application", "PROD"),
            "environment": "Production",
            "region": "Central",
            "evidence_version": "v1.0",
            "evidence_type": ev.get("type", "Document"),
            "observation_id": ev.get("observation_id", ""),
            "observation_status": ev.get("observation_status", "Open"),
            "audit_cycle": ev.get("audit_cycle", "Q2 2026"),
        }
        return ctrl, catalog_ev
    return None, None


def _find_evidence(framework: str, control: str, evidence_id: str) -> tuple[dict, dict] | tuple[None, None]:
    fw = resolve_framework_name(framework)
    control = (control or "").strip()

    if evidence_id:
        for rec in get_all_evidence_records():
            if rec.get("evidence_id") == evidence_id:
                use_fw = resolve_framework_name(rec.get("framework", fw))
                for ctrl in get_framework_controls(use_fw):
                    for ev in ctrl["evidences"]:
                        if ev["evidence_id"] == evidence_id:
                            return ctrl, ev
        rel_match = _relational_evidence_lookup(fw, evidence_id)
        if rel_match[0]:
            return rel_match
        for catalog_fw in FRAMEWORK_CATALOG:
            if catalog_fw == fw:
                continue
            rel_match = _relational_evidence_lookup(catalog_fw, evidence_id)
            if rel_match[0]:
                return rel_match

    if control:
        for ctrl in get_framework_controls(fw):
            if ctrl["control"] == control or ctrl.get("control_id") == control:
                for ev in ctrl["evidences"]:
                    if not evidence_id or ev["evidence_id"] == evidence_id:
                        return ctrl, ev
                if ctrl["evidences"]:
                    return ctrl, ctrl["evidences"][0]

    if evidence_id:
        resolved = resolve_control_name(fw, control)
        if resolved:
            for ctrl in get_framework_controls(fw):
                if ctrl["control"] == resolved or ctrl.get("control_id") == control:
                    for ev in ctrl["evidences"]:
                        if ev["evidence_id"] == evidence_id:
                            return ctrl, ev

    # Lookup by control reference in relational graph (evidence_id on control row)
    if control or evidence_id:
        from app.governance_relational_model import get_framework_graph
        for c in get_framework_graph(fw).get("controls", []):
            match = (
                (evidence_id and c.get("evidence_id") == evidence_id)
                or (control and (c.get("control_name") == control or c.get("control_id") == control))
            )
            if match and c.get("evidence_id"):
                eid = c.get("evidence_id")
                rel = _relational_evidence_lookup(fw, eid)
                if rel[0]:
                    return rel
                return _synthesize_from_control(fw, c, eid)

    if evidence_id or control:
        return _synthesize_evidence(fw, evidence_id, control)
    return None, None


def _synthesize_from_control(framework: str, ctrl_row: dict, evidence_id: str) -> tuple[dict, dict]:
    """Build review payload from relational control row."""
    control_name = ctrl_row.get("control_name", ctrl_row.get("control_id", "Governance Control"))
    ctrl = {
        "control": control_name,
        "control_id": ctrl_row.get("control_id", ""),
        "control_description": ctrl_row.get("auditor_comment", f"Control attestation for {control_name}"),
    }
    wf = ctrl_row.get("workflow", "Pending Review")
    val = ctrl_row.get("validation", "WARN")
    ev_name = ctrl_row.get("evidence_name") or f"{control_name} — Q2 2026 attestation"
    ext = "pdf"
    if "SIEM" in ev_name or "log" in ev_name.lower():
        ext = "zip"
    elif "scan" in ev_name.lower() or "xlsx" in ev_name.lower():
        ext = "xlsx"
    elif "export" in ev_name.lower() and "firewall" in ev_name.lower():
        ext = "csv"
    catalog_ev = {
        "evidence_id": evidence_id,
        "evidence_name": ev_name,
        "mock_file": f"{ev_name.replace(' ', '_')[:40]}.{ext}",
        "application_name": ctrl_row.get("application", "Net Banking"),
        "application": ctrl_row.get("application", "Net Banking"),
        "uploaded_by": ctrl_row.get("owner", "App Owner"),
        "upload_timestamp": "2026-05-20 10:00 UTC",
        "evidence_status": "Current",
        "audit_status": wf,
        "reviewer": "",
        "comments": ctrl_row.get("auditor_comment", f"Linked evidence for {control_name}"),
        "expiry_date": "2026-08-31",
        "evidence_source": "SharePoint",
        "server_name": ctrl_row.get("application", "PROD"),
        "environment": "Production",
        "region": "Central",
        "evidence_version": "v1.0",
        "evidence_type": "Policy",
        "observation_id": "",
        "observation_status": "Open" if wf != "Approved" else "Closed",
        "audit_cycle": "Q2 2026",
    }
    return ctrl, catalog_ev


def _synthesize_evidence(framework: str, evidence_id: str, control: str) -> tuple[dict, dict]:
    """Guaranteed fallback — ECS demo always has reviewable evidence."""
    fw = resolve_framework_name(framework)
    cid = ""
    if control:
        if control.startswith(("PCI", "DP", "OS", "VP", "AS", "CS", "IT", "NGX", "DB")) or "." in control:
            cid = control
    cname = control if control and not cid else resolve_control_name(fw, cid, control)
    if not cname:
        cname = control or "Governance Control Attestation"
    if not evidence_id:
        prefix = {"PCI DSS": "PCI", "DPSC": "DPSC", "AppSec": "AS", "VAPT": "VP", "CSITE": "CS", "ITPP": "IT"}.get(fw, "EVD")
        slug = (cid or cname[:10]).replace(" ", "-").replace(".", "")[:12]
        evidence_id = f"EV-{prefix}-{slug}"
    ctrl = {
        "control": cname,
        "control_id": cid or cname[:12],
        "control_description": f"Enterprise attestation package for {cname} — {fw} audit cycle.",
    }
    slug = cname.lower()
    if "siem" in slug or "log" in slug:
        fname, etype, ext = "SOC_log_export_May2026.zip", "SIEM Export", "zip"
    elif "mfa" in slug or "pam" in slug:
        fname, etype, ext = "MFA_enrollment_report_Q2.pdf", "MFA Report", "pdf"
    elif "firewall" in slug or "segmentation" in slug:
        fname, etype, ext = "Firewall_rule_export_Q2.csv", "Firewall Export", "csv"
    elif "scan" in slug or "va" in slug or "pentest" in slug:
        fname, etype, ext = "External_VA_report_Q2.pdf", "VA Report", "pdf"
    elif "hardening" in slug or "cis" in slug:
        fname, etype, ext = "Quarterly_hardening_validation.xlsx", "Hardening Report", "xlsx"
    else:
        fname, etype, ext = f"{cname.replace(' ', '_')[:32]}_Q2.pdf", "Policy", "pdf"
    from app.evidence_workflow_engine import observation_id_for
    obs = observation_id_for(fw, cname, cid)
    catalog_ev = {
        "evidence_id": evidence_id,
        "evidence_name": fname.rsplit(".", 1)[0].replace("_", " "),
        "mock_file": fname,
        "application_name": "Net Banking",
        "application": "Net Banking",
        "uploaded_by": "R. Mehta",
        "upload_timestamp": "2026-05-22 14:30 UTC",
        "evidence_status": "Current",
        "audit_status": "Pending Review",
        "reviewer": "",
        "comments": f"Mock evidence artefact linked to observation {obs}",
        "expiry_date": "2026-09-30",
        "evidence_source": "SharePoint Evidence Library",
        "server_name": "NETBANKING_PROD",
        "environment": "Production",
        "region": "Central",
        "evidence_version": "v1.0",
        "evidence_type": etype,
        "observation_id": obs,
        "observation_status": "Open",
        "audit_cycle": "Q2 2026",
    }
    return ctrl, catalog_ev


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
        rej = ecs_state.rejected_controls[key]
        if rej.get("internal"):
            return {"code": "rejected", "label": "Rejected Internally", "locked": False}
        from app.resubmission import stage_label
        return {"code": "rejected", "label": "Rejected by Auditor", "stage_label": stage_label(key), "locked": False}
    if key in ecs_state.clarification_controls:
        return {"code": "clarification", "label": "Clarification Required", "locked": False}
    if key in ecs_state.cancelled_drafts:
        return {"code": "cancelled", "label": "Draft Cancelled", "locked": True}
    if key in ecs_state.owner_drafts:
        return {"code": "draft", "label": "Draft Saved", "locked": False}
    return {"code": "pending", "label": "Draft — Pending App Owner Review", "locked": False}


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
        fw = resolve_framework_name(framework)
        ctrl, ev = _synthesize_evidence(fw, evidence_id, control or "")
    control = control or ctrl["control"]
    key = ecs_state.control_key(framework, control)
    if log_view:
        record_evidence_view(framework, control, ev["evidence_id"], user, role)

    control_desc = ctrl.get("control_description", ev.get("comments", ""))
    wf = _workflow_state(key)
    from app.resubmission import can_resubmit_to_auditor, get_stage, stage_label
    from app.evidence_workflow_engine import can_close_observation, observation_id_for, resolve_state

    wf_visual = resolve_state(key, framework=framework, control=control, control_id=ctrl.get("control_id", ""))
    obs_id = wf_visual.get("observation_id") or ev.get("observation_id") or observation_id_for(
        resolve_framework_name(framework), control, ctrl.get("control_id", "")
    )
    obs_closed = obs_id in ecs_state.closed_observations or ev.get("observation_status") == "Closed"

    return {
        "framework": framework,
        "control": control,
        "control_id": ctrl.get("control_id", ""),
        "control_description": control_desc,
        "evidence": ev,
        "evidence_id": ev["evidence_id"],
        "metadata": {
            "framework": resolve_framework_name(framework),
            "control_id": ctrl.get("control_id", ""),
            "control_description": control_desc,
            "evidence_name": ev.get("evidence_name", ""),
            "evidence_id": ev.get("evidence_id", ""),
            "application_name": ev.get("application_name", ev.get("application", "")),
            "upload_timestamp": ev.get("upload_timestamp", ev.get("uploaded_at", "")),
            "expiry_date": ev.get("expiry_date", ev.get("expiry", "")),
            "source_system": ev.get("evidence_source", "Manual Upload"),
            "submitted_by": ev.get("uploaded_by", ""),
            "evidence_version": ev.get("evidence_version", "v1.0"),
            "evidence_status": ev.get("evidence_status", "Current"),
            "evidence_type": ev.get("evidence_type", ev.get("type", "Document")),
            "observation_id": obs_id,
            "observation_status": "Closed" if obs_closed else ev.get("observation_status", "Open"),
            "audit_cycle": ev.get("audit_cycle", "Q2 2026"),
            "reviewer": ev.get("reviewer", ""),
            "review_timestamp": ev.get("review_timestamp", ""),
        },
        "preview": _build_preview(ev, ctrl, framework),
        "validation": _validation_scores(ev, key),
        "workflow": wf,
        "workflow_visual": wf_visual,
        "workflow_history": _workflow_history(framework, control, ev["evidence_id"]),
        "owner_comments": ecs_state.owner_comments.get(key, []),
        "reject_reason": ecs_state.rejected_controls.get(key, {}).get("reason", "") if key in ecs_state.rejected_controls else "",
        "lineage": get_version_history(ev["evidence_id"]),
        "reuse_mapping": _reuse_mapping(ev["evidence_id"]),
        "reject_presets": REJECT_REASON_PRESETS,
        "resubmission_stage": get_stage(key),
        "resubmission_stage_label": stage_label(key),
        "can_resubmit_to_auditor": can_resubmit_to_auditor(key),
        "can_close_observation": can_close_observation(key, obs_id) and not obs_closed,
        "observation_closed": obs_closed,
        "observation_id": obs_id,
        "role": role,
        "user": user,
        "key": key,
    }


def review_url(framework: str, control: str, evidence_id: str, role: str, user: str, control_id: str = "") -> str:
    from urllib.parse import quote

    fw = resolve_framework_name(framework)
    ctrl = (control or "").strip()
    if not ctrl and control_id:
        ctrl = resolve_control_name(fw, control_id) or control_id
    if not ctrl and evidence_id:
        _, ev = _find_evidence(fw, "", evidence_id)
        if ev:
            rel = _relational_evidence_lookup(fw, evidence_id)
            if rel[0]:
                ctrl = rel[0]["control"]
    return (
        f"/evidence/review?framework_name={quote(framework)}"
        f"&control_name={quote(ctrl)}&evidence_id={quote(evidence_id)}"
        f"&role={quote(role)}&user={quote(user)}"
    )


def review_url_for_ev(framework: str, ev: dict, role: str, user: str) -> str:
    control = ev.get("control") or ev.get("control_name") or ""
    eid = ev.get("evidence_id", "")
    if not eid and ev.get("control_id"):
        from app.governance_relational_model import get_framework_graph
        fw = resolve_framework_name(framework)
        for c in get_framework_graph(fw).get("controls", []):
            if c.get("control_id") == ev.get("control_id"):
                eid = c.get("evidence_id", eid)
                if not control:
                    control = c.get("control_name", control)
                break
    return review_url(
        framework,
        control,
        eid,
        role,
        user,
        control_id=ev.get("control_id", ""),
    )
