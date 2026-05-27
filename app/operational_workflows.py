"""Enterprise operational workflows — gap closure, owner assignment, evidence upload, mock audit."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote

from app import ecs_state
from app.analytics_module import _app_for, audit_preparation_checklist, completeness_report
from app.audit_trail import log_event

ASSIGNMENT_TEAMS = [
    "Application Owner",
    "Infra Team",
    "Security Team",
    "SOC Team",
    "DBA Team",
    "Middleware Team",
]

MOCK_FILE_SAMPLES = [
    {"name": "MFA_Config_Export.pdf", "type": "PDF", "size": "842 KB"},
    {"name": "Firewall_Rules_Q2_2026.xlsx", "type": "XLSX", "size": "1.2 MB"},
    {"name": "SIEM_Alert_Validation.csv", "type": "SIEM export", "size": "456 KB"},
    {"name": "VAPT_Summary_May2026.pdf", "type": "Vulnerability report", "size": "2.1 MB"},
    {"name": "Access_Review_Screenshot.png", "type": "Screenshot", "size": "312 KB"},
    {"name": "ISMS_Policy_v4.2.pdf", "type": "Policy document", "size": "678 KB"},
]

AUDIT_PREP_TASKS = {
    "PCI DSS": [
        {"task": "Evidence refresh pending", "owner": "R. Mehta", "due": "2026-05-28", "status": "In Progress", "sla_risk": "Medium"},
        {"task": "Firewall rule recertification", "owner": "K. Reddy", "due": "2026-05-30", "status": "Pending", "sla_risk": "High"},
        {"task": "MFA validation for CDE access", "owner": "Security Team", "due": "2026-06-02", "status": "In Progress", "sla_risk": "Medium"},
        {"task": "Quarterly access review", "owner": "A. Sharma", "due": "2026-06-05", "status": "Scheduled", "sla_risk": "Low"},
        {"task": "VAPT evidence collection", "owner": "SOC Team", "due": "2026-06-08", "status": "Pending", "sla_risk": "High"},
    ],
    "DPSC": [
        {"task": "Privileged access review", "owner": "A. Sharma", "due": "2026-05-29", "status": "In Progress", "sla_risk": "High"},
        {"task": "Password rotation validation", "owner": "DBA Team", "due": "2026-06-01", "status": "Pending", "sla_risk": "Medium"},
        {"task": "DB audit log verification", "owner": "S. Banerjee", "due": "2026-06-04", "status": "Scheduled", "sla_risk": "Low"},
        {"task": "Backup validation evidence", "owner": "Infra Team", "due": "2026-06-06", "status": "Pending", "sla_risk": "Medium"},
    ],
    "CSITE": [
        {"task": "SIEM alert validation", "owner": "SOC Team", "due": "2026-05-31", "status": "In Progress", "sla_risk": "Medium"},
        {"task": "SOC incident closure review", "owner": "M. Joshi", "due": "2026-06-03", "status": "Pending", "sla_risk": "High"},
        {"task": "EDR coverage validation", "owner": "Security Team", "due": "2026-06-07", "status": "Scheduled", "sla_risk": "Low"},
        {"task": "Threat detection evidence review", "owner": "SOC Team", "due": "2026-06-10", "status": "Pending", "sla_risk": "Medium"},
    ],
}

GAP_TEMPLATES = {
    "PCI DSS": {
        "gap_description": "MFA not enforced for privileged Linux jump servers.",
        "root_cause": "Legacy PAM configuration bypass for break-glass accounts.",
        "remediation_plan": "PAM integration completed. MFA rollout in progress across CDE jump hosts.",
        "evidence_required": [
            "MFA configuration screenshot",
            "PAM policy export",
            "SIEM validation logs",
        ],
        "assigned_team": "Security Team",
        "reviewer": "Compliance Head",
    },
    "DPSC": {
        "gap_description": "Privileged access review incomplete for production DB clusters.",
        "root_cause": "Quarterly review cycle delayed due to change freeze.",
        "remediation_plan": "Expedited PAM export and DBA sign-off scheduled.",
        "evidence_required": [
            "PAM privileged user export",
            "DBA attestation",
            "Access review sign-off",
        ],
        "assigned_team": "DBA Team",
        "reviewer": "Internal Audit",
    },
    "CSITE": {
        "gap_description": "SIEM use-case validation not documented for new EDR rollout.",
        "root_cause": "Detection rule tuning in progress post-EDR deployment.",
        "remediation_plan": "SOC to complete use-case mapping and attach validation logs.",
        "evidence_required": [
            "SIEM use-case matrix",
            "EDR coverage report",
            "Incident closure samples",
        ],
        "assigned_team": "SOC Team",
        "reviewer": "CISO Office",
    },
}


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def gap_key(framework: str, control: str) -> str:
    return ecs_state.control_key(framework, control)


def is_gap_closed(framework: str, control: str) -> bool:
    return gap_key(framework, control) in ecs_state.operational_closed_gaps


def _evidence_for(framework: str, control: str) -> str:
    for fw, controls in ecs_state.frameworks.items():
        if fw == framework:
            for c, ev in controls:
                if c == control:
                    return ev
    return "Supporting evidence artifact"


def _gap_template(framework: str) -> dict:
    return GAP_TEMPLATES.get(framework, GAP_TEMPLATES["PCI DSS"])


def workflow_guidance(
    *,
    status: str,
    owner: str,
    next_action: str,
    due_date: str,
    sla_risk: str,
    escalation_risk: str,
) -> dict:
    return {
        "status": status,
        "owner": owner,
        "next_action": next_action,
        "due_date": due_date,
        "sla_risk": sla_risk,
        "escalation_risk": escalation_risk,
    }


def adjusted_readiness_pct() -> int:
    base = ecs_state.build_evidence_analytics()["overall_compliance_pct"]
    boost = min(ecs_state.operational_readiness_boost, 12)
    return min(99, base + boost)


def adjusted_missing_count() -> int:
    base = completeness_report()["missing_count"]
    return max(0, base - len(ecs_state.operational_closed_gaps))


def workflow_url_for_action(action: str, role: str, user: str, item_id: str = "", framework: str = "") -> str | None:
    q = f"role={quote(role)}&user={quote(user)}"
    if item_id:
        q += f"&control={quote(item_id)}"
    if framework:
        q += f"&framework={quote(framework)}"
    routes = {
        "close_gap": f"/mvp/workflow/close-gap?{q}",
        "assign_owner": f"/mvp/workflow/assign-owner?{q}",
        "assign_gap": f"/mvp/workflow/assign-owner?{q}",
        "upload_missing": f"/mvp/workflow/upload-missing?{q}",
        "mock_audit": f"/mvp/workflow/mock-audit?{q}",
    }
    return routes.get(action)


def _resolve_control_context(framework: str, control: str) -> dict:
    if not framework or not control:
        comp = completeness_report()
        if comp["missing"]:
            m = comp["missing"][0]
            framework = m["framework"]
            control = m["control"]
        else:
            framework = framework or "PCI DSS"
            control = control or "Req 8.3 — MFA for CDE Access"
    application = _app_for(framework, control)
    return {"framework": framework, "control": control, "application": application}


def _return_url(role: str, user: str, return_module: str = "audit_prep", tab: str = "") -> str:
    paths = {
        "audit_prep": "/mvp/audit-prep",
        "completeness": "/mvp/completeness",
        "onboarding": "/mvp/onboarding",
    }
    base = paths.get(return_module, "/mvp/audit-prep")
    url = f"{base}?role={quote(role)}&user={quote(user)}"
    if return_module == "completeness" and not tab:
        tab = "uploads"
    if tab:
        url += f"&tab={quote(tab)}"
    return url


def build_close_gap_view(framework: str, control: str, role: str, user: str, return_module: str = "audit_prep") -> dict:
    ctx = _resolve_control_context(framework, control)
    tpl = _gap_template(ctx["framework"])
    key = gap_key(ctx["framework"], ctx["control"])
    closed = key in ecs_state.operational_closed_gaps
    return {
        "workflow_title": "Gap Closure Workflow",
        "control_name": ctx["control"],
        "framework": ctx["framework"],
        "application": ctx["application"],
        "gap_description": tpl["gap_description"],
        "root_cause": tpl["root_cause"],
        "remediation_plan": tpl["remediation_plan"],
        "target_closure_date": "2026-06-10",
        "evidence_required": tpl["evidence_required"],
        "assigned_team": tpl["assigned_team"],
        "reviewer": tpl["reviewer"],
        "closure_validation_status": "Remediated — Pending Validation" if closed else "Open — Remediation In Progress",
        "guidance": workflow_guidance(
            status="Draft" if not closed else "Submitted for Validation",
            owner=tpl["assigned_team"],
            next_action="Submit for Validation" if not closed else "Await reviewer sign-off",
            due_date="2026-06-10",
            sla_risk="Medium",
            escalation_risk="Low" if not closed else "None",
        ),
        "already_closed": closed,
        "return_url": _return_url(role, user, return_module),
    }


def process_close_gap(
    *,
    framework: str,
    control: str,
    user: str,
    role: str,
    submit_type: str,
    root_cause: str = "",
    remediation_plan: str = "",
    target_date: str = "",
) -> str:
    ctx = _resolve_control_context(framework, control)
    key = gap_key(ctx["framework"], ctx["control"])
    label = submit_type.replace("_", " ").title()
    if submit_type == "save_draft":
        log_event("Gap Closure Draft Saved", user, ctx["framework"], ctx["control"], "Draft saved in gap closure workflow", role=role)
        return f"Gap closure draft saved for {ctx['control']}."
    if submit_type == "escalate":
        ecs_state.escalated_controls[key] = {"reason": "Gap closure SLA at risk", "by": user}
        log_event("Gap Escalated", user, ctx["framework"], ctx["control"], "Escalated to Compliance Head — SLA breach risk", role=role)
        return f"Gap escalated for {ctx['control']} — leadership notified."
    if submit_type in ("submit_validation", "mark_remediated"):
        if key not in ecs_state.operational_closed_gaps:
            ecs_state.operational_closed_gaps.append(key)
            ecs_state.operational_readiness_boost = min(12, ecs_state.operational_readiness_boost + 2)
        detail = remediation_plan or _gap_template(ctx["framework"])["remediation_plan"]
        log_event(
            "Gap Closed" if submit_type == "mark_remediated" else "Gap Submitted for Validation",
            user,
            ctx["framework"],
            ctx["control"],
            f"{label}: {detail[:120]}",
            role=role,
        )
        return f"{label} — pending gap count reduced. Audit readiness improved for {ctx['framework']}."
    return f"{label} recorded for {ctx['control']}."


def build_assign_owner_view(framework: str, control: str, role: str, user: str, return_module: str = "audit_prep") -> dict:
    ctx = _resolve_control_context(framework, control)
    existing = next(
        (a for a in reversed(ecs_state.operational_assignments) if a["control"] == ctx["control"]),
        None,
    )
    return {
        "workflow_title": "Control Owner Assignment",
        "application": ctx["application"],
        "framework": ctx["framework"],
        "control": ctx["control"],
        "current_risk": "High" if ctx["framework"] == "PCI DSS" else "Medium",
        "pending_due_date": "2026-06-05",
        "teams": ASSIGNMENT_TEAMS,
        "selected_team": existing["team"] if existing else "Application Owner",
        "priority": existing.get("priority", "High") if existing else "High",
        "sla_days": existing.get("sla_days", "5") if existing else "5",
        "escalation_level": existing.get("escalation_level", "L1") if existing else "L1",
        "comments": existing.get("comments", "") if existing else "",
        "guidance": workflow_guidance(
            status=existing["status"] if existing else "Unassigned",
            owner=existing["team"] if existing else "—",
            next_action="Assign owner and notify team" if not existing else "Monitor SLA and follow up",
            due_date="2026-06-05",
            sla_risk="High" if not existing else "Medium",
            escalation_risk="Medium" if not existing else "Low",
        ),
        "return_url": _return_url(role, user, return_module),
    }


def process_assign_owner(
    *,
    framework: str,
    control: str,
    user: str,
    role: str,
    submit_type: str,
    team: str = "Application Owner",
    priority: str = "High",
    sla_days: str = "5",
    escalation_level: str = "L1",
    comments: str = "",
) -> str:
    ctx = _resolve_control_context(framework, control)
    record = {
        "timestamp": _ts(),
        "framework": ctx["framework"],
        "control": ctx["control"],
        "application": ctx["application"],
        "team": team,
        "priority": priority,
        "sla_days": sla_days,
        "escalation_level": escalation_level,
        "comments": comments,
        "assigned_by": user,
        "status": "Assigned",
    }
    ecs_state.operational_assignments.append(record)
    if submit_type == "escalate":
        record["status"] = "Escalated"
        log_event("Owner Assignment Escalated", user, ctx["framework"], ctx["control"], f"Escalated to {escalation_level}", role=role)
        return f"Assignment escalated ({escalation_level}) for {ctx['control']}."
    if submit_type == "notify_teams":
        log_event("Teams Notification Sent", user, ctx["framework"], ctx["control"], f"Notified {team} via Microsoft Teams", role=role)
        return f"Teams notification sent to {team} for {ctx['control']}."
    if submit_type == "send_reminder":
        log_event("Assignment Reminder", user, ctx["framework"], ctx["control"], f"Reminder sent to {team}", role=role)
        return f"Reminder sent to {team} — due in {sla_days} business days."
    log_event("Owner Assigned", user, ctx["framework"], ctx["control"], f"{team} · Priority {priority} · SLA {sla_days}d", role=role)
    return f"{team} assigned to {ctx['control']}. Owner queue and audit tracker updated."


def build_upload_missing_view(
    framework: str,
    control: str,
    role: str,
    user: str,
    return_module: str = "audit_prep",
    observation_id: str = "",
) -> dict:
    from app.missing_evidence_engine import get_missing_record

    obs = get_missing_record(observation_id) if observation_id else None
    if obs:
        ctx = {
            "framework": obs["framework"],
            "control": obs["control_id"],
            "application": obs["application"],
        }
        evidence_type = obs.get("evidence_type", obs.get("missing_evidence"))
        auditor_comments = obs.get("audit_comments", "")
        missing_label = obs.get("missing_evidence", evidence_type)
        last_version = (obs.get("prior_uploads") or ["—"])[0]
        expiry = obs.get("due_date", "2026-06-05")
    else:
        ctx = _resolve_control_context(framework, control)
        evidence_type = _evidence_for(ctx["framework"], ctx["control"])
        auditor_comments = "Please provide current-period artifact with control owner attestation."
        missing_label = evidence_type
        last_version = "v2.1 — 2026-02-14 (expired)"
        expiry = "2026-05-01"
    return {
        "workflow_title": "Evidence Upload Workflow",
        "observation_id": observation_id or (obs or {}).get("observation_id", ""),
        "missing_evidence_type": evidence_type,
        "missing_evidence_label": missing_label,
        "control_description": (obs or {}).get("control_description", ""),
        "observation_severity": (obs or {}).get("observation_severity", ""),
        "requested_by": (obs or {}).get("requested_by", ""),
        "audit_impact": (obs or {}).get("audit_impact", ""),
        "last_uploaded_version": last_version,
        "evidence_expiry": expiry,
        "required_format": "PDF, XLSX, or SIEM export (max 25 MB)",
        "linked_control": ctx["control"],
        "application": ctx["application"],
        "framework": ctx["framework"],
        "auditor_comments": auditor_comments,
        "remediation_owner": (obs or {}).get("remediation_owner", ctx["application"] + " App Owner"),
        "mock_files": MOCK_FILE_SAMPLES,
        "sharepoint_link": "https://bank.sharepoint.com/sites/GRC/Evidence/PCI",
        "servicenow_ticket": "INC0042187",
        "jira_remediation": "GRC-1842",
        "observation_record": obs,
        "guidance": workflow_guidance(
            status="Evidence Missing",
            owner=ctx["application"] + " App Owner",
            next_action="Upload and submit for App Owner review",
            due_date=expiry,
            sla_risk="High",
            escalation_risk="Medium",
        ),
        "return_url": _return_url(role, user, return_module),
    }


def process_upload_missing(
    *,
    framework: str,
    control: str,
    user: str,
    role: str,
    submit_type: str,
    evidence_comments: str = "",
    linked_source: str = "",
    filename: str = "",
    observation_id: str = "",
    evidence_category: str = "",
    remediation_owner: str = "",
    expected_closure: str = "",
) -> str:
    from app.role_permissions import can_upload_evidence, permission_denied_message

    if not can_upload_evidence(role):
        return permission_denied_message("upload or replace evidence")
    from app.missing_evidence_engine import apply_upload

    if observation_id:
        return apply_upload(
            observation_id,
            user,
            role,
            filename=filename or MOCK_FILE_SAMPLES[0]["name"],
            comments=evidence_comments,
            evidence_category=evidence_category,
            remediation_owner=remediation_owner,
            expected_closure=expected_closure,
            submit_type=submit_type,
        )
    ctx = _resolve_control_context(framework, control)
    fname = filename or MOCK_FILE_SAMPLES[0]["name"]
    record = {
        "timestamp": _ts(),
        "framework": ctx["framework"],
        "control": ctx["control"],
        "application": ctx["application"],
        "filename": fname,
        "comments": evidence_comments,
        "linked_source": linked_source,
        "uploaded_by": user,
        "status": "Draft" if submit_type == "upload_draft" else "Pending App Owner Review",
    }
    ecs_state.operational_uploads.append(record)
    if submit_type != "upload_draft":
        from app.evidence_repository import register_upload
        from app.framework_catalog import resolve_framework_name
        fw = resolve_framework_name(ctx["framework"])
        register_upload(fname, b"ECS operational upload", user, framework=fw, application=ctx["application"], control=ctx["control"])
        key = ecs_state.control_key(fw, ctx["control"])
        ts_full = _ts()
        ecs_state.submitted_controls[key] = {"submitted_by": user, "submitted_at": ts_full}
        ecs_state.submitted_meta[key] = {"submitted_at": ts_full}
        ecs_state.operational_readiness_boost = min(12, ecs_state.operational_readiness_boost + 1)
    if submit_type == "upload_draft":
        log_event("Evidence Draft Uploaded", user, ctx["framework"], ctx["control"], f"Draft: {fname}", role=role)
        return f"Evidence draft saved ({fname}) for {ctx['control']}."
    ecs_state.operational_readiness_boost = min(12, ecs_state.operational_readiness_boost + 1)
    log_event(
        "Evidence Submitted for Review",
        user,
        ctx["framework"],
        ctx["control"],
        f"{fname} submitted to App Owner review queue",
        role=role,
    )
    return f"Evidence submitted for App Owner review — activity feed and audit tracker updated."


def build_mock_audit_view(role: str, user: str, executed: bool = False, return_module: str = "audit_prep") -> dict:
    from app.audit_prep_data import BANKING_APPS, build_audit_prep_view
    from app.governance_relational_model import FRAMEWORK_GRAPHS

    prep = build_audit_prep_view(role)
    frameworks = list(FRAMEWORK_GRAPHS.keys()) or ["PCI DSS", "VAPT", "AppSec", "DPSC", "ITPP"]
    auditors = ["Deloitte", "EY", "KPMG", "Internal Audit", "PwC"]
    cycles = ["Q1 2026", "Q2 2026", "H1 2026", "FY 2026"]
    gaps = prep["actionable_gaps"]
    missing_ev_count = len(gaps)
    stale = prep["evidence_freshness"]["stale_count"]
    readiness = prep["weighted_readiness_pct"]

    stages = [
        {"id": 1, "name": "Scope selection", "desc": "Select framework, applications, auditor, and audit cycle"},
        {"id": 2, "name": "Control sampling", "desc": "Sample in-scope controls across selected applications"},
        {"id": 3, "name": "Evidence validation", "desc": "Verify evidence freshness, format, and control mapping"},
        {"id": 4, "name": "Gap identification", "desc": "Cross-check missing, stale, and rejected artifacts"},
        {"id": 5, "name": "Observation generation", "desc": "Draft audit observations and risk ratings"},
        {"id": 6, "name": "Mock audit summary", "desc": "Compile readiness score and predicted findings"},
    ]

    result = ecs_state.operational_mock_audits[-1] if executed and ecs_state.operational_mock_audits else None
    completed_stage = 6 if result else 0

    return {
        "workflow_title": "Simulated Audit Execution",
        "audit_scope": "Bank-wide audit readiness simulation — regulator-style assessment",
        "applications_in_scope": BANKING_APPS[:6],
        "framework_coverage": frameworks,
        "framework_options": frameworks,
        "application_options": BANKING_APPS,
        "auditor_options": auditors,
        "cycle_options": cycles,
        "controls_sampled": min(48, len(gaps) + 24),
        "evidences_available": max(0, 120 - missing_ev_count),
        "evidences_missing": missing_ev_count,
        "expired_evidences": stale,
        "failed_controls": len([g for g in gaps if g.get("status") == "Failed Validation"]),
        "open_observations": len(prep.get("auditor_requests", [])),
        "audit_readiness_pct": readiness,
        "stages": stages,
        "completed_stage": completed_stage,
        "executed": bool(result),
        "result": result,
        "guidance": workflow_guidance(
            status="Configure & Execute" if not result else "Mock Audit Complete",
            owner="Internal Audit / External Auditor (simulated)",
            next_action="Select scope and execute mock audit simulation" if not result else "Review summary report and assign CAPA",
            due_date="2026-06-15",
            sla_risk="Medium",
            escalation_risk="Low" if readiness >= 75 else "High",
        ),
        "return_url": _return_url(role, user, return_module),
    }


def execute_mock_audit(
    user: str,
    role: str,
    framework: str = "PCI DSS",
    applications: str = "",
    auditor: str = "Deloitte",
    audit_cycle: str = "Q2 2026",
) -> dict:
    from app.audit_prep_data import build_audit_prep_view
    from app.governance_relational_model import get_framework_graph

    prep = build_audit_prep_view(role, {"framework": framework} if framework else None)
    g = get_framework_graph(framework or "PCI DSS")
    app_list = [a.strip() for a in applications.split(",") if a.strip()] or [a["name"] for a in g.get("applications", [])[:3]]

    observations = []
    for i, finding in enumerate(g.get("findings", [])[:4]):
        observations.append({
            "id": finding.get("finding_id", f"OBS-{i+1:03d}"),
            "severity": finding.get("severity", "Medium"),
            "control": finding.get("linked_control", "—"),
            "application": finding.get("application", "—"),
            "text": finding.get("observation", "Audit observation"),
        })
    if not observations:
        observations = [
            {"id": "OBS-001", "severity": "High", "control": "PCI-8.3", "application": app_list[0] if app_list else "Net Banking", "text": "MFA not consistently enforced on privileged access."},
            {"id": "OBS-002", "severity": "Medium", "control": "VP-C-03", "application": app_list[1] if len(app_list) > 1 else "UPI", "text": "Retest evidence pending for SSRF remediation."},
        ]

    missing_evidence = [f"{g['control_id']} — {g['evidence_missing']}" for g in prep["actionable_gaps"][:6]]
    failed_controls = [c["control_id"] for c in g.get("controls", []) if c.get("validation") == "FAIL"]
    stale_evidence = [e.get("name", "Stale evidence") for e in prep["evidence_freshness"].get("stale", [])[:4]]
    readiness = prep["weighted_readiness_pct"]

    result = {
        "audit_id": f"MOCK-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}",
        "executed_at": _ts(),
        "executed_by": user,
        "framework": framework or "PCI DSS",
        "applications": app_list,
        "auditor": auditor,
        "audit_cycle": audit_cycle,
        "readiness_score": readiness,
        "observations": observations,
        "risk_findings": len(observations),
        "high_risk_controls": [o for o in observations if o["severity"] in ("Critical", "High")],
        "missing_evidences": missing_evidence,
        "failed_controls": failed_controls,
        "stale_evidences": stale_evidence,
        "auditor_requests": len(prep.get("auditor_requests", [])),
        "predicted_findings": observations,
        "remediation_recommendations": [
            f"Close {len(missing_evidence)} missing evidence gaps before {audit_cycle} audit.",
            f"Address {len(failed_controls)} failed control validations on {', '.join(app_list[:2])}.",
            f"Refresh {len(stale_evidence)} stale evidence items flagged by auditor simulation.",
        ],
        "stages_completed": 6,
    }
    ecs_state.operational_mock_audits.append(result)
    ecs_state.operational_readiness_boost = min(12, ecs_state.operational_readiness_boost + 1)
    log_event(
        "Mock Audit Complete",
        user,
        framework or "",
        "",
        f"{framework} · {auditor} · Readiness {readiness}% · {len(observations)} predicted findings",
        role=role,
    )
    return result


def generate_mock_audit_report(audit_id: str = "") -> str:
    audits = ecs_state.operational_mock_audits
    if not audits:
        return "No mock audit results available. Run Start Mock Audit first."
    result = next((a for a in reversed(audits) if a["audit_id"] == audit_id), audits[-1])
    lines = [
        "=" * 72,
        "ECS MOCK AUDIT SUMMARY REPORT — CONFIDENTIAL",
        f"Audit ID: {result['audit_id']}",
        f"Framework: {result.get('framework', 'Multi-framework')}",
        f"Applications: {', '.join(result.get('applications', []))}",
        f"Auditor: {result.get('auditor', 'Simulated')}",
        f"Audit Cycle: {result.get('audit_cycle', 'Q2 2026')}",
        f"Generated: {result['executed_at']}",
        f"Executed by: {result['executed_by']}",
        f"Readiness Score: {result['readiness_score']}%",
        "=" * 72,
        "",
        "PREDICTED AUDIT FINDINGS",
        "-" * 40,
    ]
    for o in result.get("predicted_findings", result.get("observations", [])):
        lines.append(f"[{o['severity']}] {o['id']} — {o.get('application', '—')} · {o['control']}")
        lines.append(f"  {o['text']}")
        lines.append("")
    lines.extend(["FAILED CONTROLS", "-" * 40])
    for fc in result.get("failed_controls", []):
        lines.append(f"  • {fc}")
    lines.extend(["", "MISSING EVIDENCE", "-" * 40])
    for m in result.get("missing_evidences", []):
        lines.append(f"  • {m}")
    lines.extend(["", "STALE EVIDENCE", "-" * 40])
    for s in result.get("stale_evidences", []):
        lines.append(f"  • {s}")
    lines.extend([
        "",
        "REMEDIATION RECOMMENDATIONS",
        "-" * 40,
    ])
    for r in result.get("remediation_recommendations", []):
        lines.append(f"  • {r}")
    lines.extend(["", "End of mock audit summary report.", ""])
    return "\n".join(lines)


def process_mock_audit_action(submit_type: str, user: str, role: str) -> str:
    if submit_type == "assign_findings":
        log_event("Mock Audit Findings Assigned", user, "", "", "Observations routed to App Owner queues", role=role)
        return "Findings assigned to control owners — pending tasks updated."
    if submit_type == "create_capa":
        log_event("CAPA Created", user, "", "", "Corrective action plan opened from mock audit", role=role)
        return "CAPA record created — linked to high-risk observations."
    if submit_type == "escalate_cio":
        log_event("Mock Audit Escalated", user, "", "", "Executive briefing pack sent to CIO", role=role)
        return "Mock audit escalated to CIO — executive dashboard updated."
    return "Action recorded."


def enrich_upcoming_audits(base_audits: list[dict]) -> list[dict]:
    enriched = []
    for a in base_audits:
        fw = a.get("framework", "")
        prep = AUDIT_PREP_TASKS.get(fw, [])
        closed_boost = len([g for g in ecs_state.operational_closed_gaps if g.startswith(f"{fw}::")])
        readiness = min(99, a.get("readiness", 70) + closed_boost * 2 + ecs_state.operational_readiness_boost // 2)
        enriched.append({**a, "readiness": readiness, "prep_tasks": prep})
    return enriched


def filter_open_gaps(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        fw = r.get("framework", "")
        ctrl = r.get("control", "")
        if ctrl and is_gap_closed(fw, ctrl):
            continue
        out.append(r)
    return out
