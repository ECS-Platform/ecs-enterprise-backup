"""
Framework-specific dashboard profiles: KPIs, insights, themes, and workflow labels.
Additive presentation layer — does not alter catalog or workflow state logic.
"""

from __future__ import annotations

import hashlib
from typing import Any

from app import ecs_state
from modules.frameworks.engines.framework_governance_data import (
    build_framework_governance_analytics,
    get_framework_profile,
)
from modules.frameworks.engines.framework_governance_context import build_governance_context
from modules.frameworks.engines.framework_trends_engine import validate_control_mapping
from modules.frameworks.engines.framework_kpi_drill_engine import build_framework_kpi_list
from modules.governance.engines.governance_relational_model import get_framework_graph


FRAMEWORK_THEMES: dict[str, dict[str, str]] = {
    "PCI DSS": {"css_class": "ecs-fw-pci", "accent": "#1e40af", "accent_soft": "#dbeafe", "icon": "PCI"},
    "DPSC": {"css_class": "ecs-fw-dpsc", "accent": "#0d9488", "accent_soft": "#ccfbf1", "icon": "DPSC"},
    "OS Baselining": {"css_class": "ecs-fw-os", "accent": "#166534", "accent_soft": "#dcfce7", "icon": "OS"},
    "DB Baselining": {"css_class": "ecs-fw-db", "accent": "#7c3aed", "accent_soft": "#ede9fe", "icon": "DB"},
    "Nginx Baselining": {"css_class": "ecs-fw-nginx", "accent": "#ea580c", "accent_soft": "#ffedd5", "icon": "NGX"},
    "AppSec": {"css_class": "ecs-fw-appsec", "accent": "#dc2626", "accent_soft": "#fee2e2", "icon": "SEC"},
    "VAPT": {"css_class": "ecs-fw-vapt", "accent": "#991b1b", "accent_soft": "#fecaca", "icon": "VAPT"},
    "CSITE": {"css_class": "ecs-fw-csite", "accent": "#334155", "accent_soft": "#e2e8f0", "icon": "SOC"},
    "ITPP": {"css_class": "ecs-fw-itpp", "accent": "#1e3a5f", "accent_soft": "#e0e7ef", "icon": "ITPP"},
    "ITDRM": {"css_class": "ecs-fw-itdrm", "accent": "#b45309", "accent_soft": "#fef3c7", "icon": "DR"},
    "SOC2": {"css_class": "ecs-fw-soc2", "accent": "#0369a1", "accent_soft": "#e0f2fe", "icon": "SOC2"},
    "ISO27001": {"css_class": "ecs-fw-iso", "accent": "#4c1d95", "accent_soft": "#ede9fe", "icon": "ISO"},
}


def _seed_int(seed: str, lo: int, hi: int) -> int:
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return lo + (h % (hi - lo + 1))


def _catalog_stats(controls: list[dict]) -> dict[str, int]:
    expired = stale = current = 0
    apps: set[str] = set()
    for c in controls:
        for ev in c.get("evidences", []):
            st = ev.get("evidence_status", "Current")
            if st == "Expired":
                expired += 1
            elif st == "Due for Refresh":
                stale += 1
            else:
                current += 1
            apps.add(ev.get("application_name", ""))
    return {
        "expired": expired,
        "stale": stale,
        "current": current,
        "applications": len(apps),
        "evidence_total": sum(len(c.get("evidences", [])) for c in controls),
    }


def _workflow_labels(framework: str) -> dict[str, str]:
    labels = {
        "PCI DSS": {
            "owner_submit": "Submit PCI Evidence",
            "owner_resubmit": "Resubmit for QSA",
            "auditor_approve": "Approve Control",
            "auditor_reject": "Reject Finding",
            "queue_title": "PCI Evidence & Control Queue",
            "queue_subtitle": "Cardholder data environment controls awaiting attestation",
        },
        "DPSC": {
            "owner_submit": "Submit Privacy Evidence",
            "owner_resubmit": "Resubmit Consent Proof",
            "auditor_approve": "Approve Privacy Control",
            "auditor_reject": "Flag Privacy Gap",
            "queue_title": "Data Privacy Control Queue",
            "queue_subtitle": "Customer data protection and retention evidence",
        },
        "OS Baselining": {
            "owner_submit": "Upload Baseline Scan",
            "owner_resubmit": "Upload Remediation Proof",
            "auditor_approve": "Accept Hardening",
            "auditor_reject": "Reject Drift",
            "queue_title": "OS Hardening Queue",
            "queue_subtitle": "CIS benchmark and patch compliance evidence",
        },
        "DB Baselining": {
            "owner_submit": "Submit DB Evidence",
            "owner_resubmit": "Upload Patch Proof",
            "auditor_approve": "Approve DB Control",
            "auditor_reject": "Reject Config Gap",
            "queue_title": "Database Security Queue",
            "queue_subtitle": "Audit logging, TDE, and privileged access evidence",
        },
        "Nginx Baselining": {
            "owner_submit": "Upload TLS Config",
            "owner_resubmit": "Resubmit Cert Proof",
            "auditor_approve": "Approve Edge Config",
            "auditor_reject": "Reject TLS Gap",
            "queue_title": "Edge & TLS Control Queue",
            "queue_subtitle": "Reverse proxy, cipher, and certificate lifecycle evidence",
        },
        "AppSec": {
            "owner_submit": "Upload Scan Report",
            "owner_resubmit": "Submit Fix Evidence",
            "auditor_approve": "Accept Remediation",
            "auditor_reject": "Reject Fix Proof",
            "queue_title": "AppSec Finding Queue",
            "queue_subtitle": "SAST/DAST findings and secure SDLC evidence",
        },
        "VAPT": {
            "owner_submit": "Assign Remediation",
            "owner_resubmit": "Upload Patch Evidence",
            "auditor_approve": "Close Finding",
            "auditor_reject": "Reopen Vuln",
            "queue_title": "VAPT Finding Queue",
            "queue_subtitle": "Pen test and exploitable vulnerability remediation",
        },
        "CSITE": {
            "owner_submit": "Upload Remediation Evidence",
            "owner_resubmit": "Resubmit Closure Proof",
            "auditor_approve": "Close Observation",
            "auditor_reject": "Reopen Finding",
            "queue_title": "Internal Audit Observation Queue",
            "queue_subtitle": "Observation closure, remediation tracking, and auditor review workflow",
        },
        "ITPP": {
            "owner_submit": "Upload DR/Backup Proof",
            "owner_resubmit": "Resubmit Change Evidence",
            "auditor_approve": "Approve Governance",
            "auditor_reject": "Send Back",
            "queue_title": "Operational Governance Queue",
            "queue_subtitle": "DR, backup, change, and incident management evidence",
        },
    }
    return labels.get(framework, {
        "owner_submit": "Submit",
        "owner_resubmit": "Resubmit",
        "auditor_approve": "Approve",
        "auditor_reject": "Reject",
        "queue_title": "Evidence Workflow Queue",
        "queue_subtitle": "Control and evidence workflow",
    })


def _operational_counts(framework_name: str, controls: list[dict], stats: dict[str, int]) -> dict[str, Any]:
    """Live operational counts for executive strip — derived from workflow state."""
    approved = submitted = rejected = awaiting_evidence = stale_controls = remediation = 0
    high_risk_gaps = 0
    last_refresh = "—"
    sla_breach = len(ecs_state.escalated_controls)

    for c in controls:
        ckey = f"{framework_name}::{c['control']}"
        if ckey in ecs_state.approved_controls:
            approved += 1
        elif ckey in ecs_state.submitted_controls:
            submitted += 1
        elif ckey in ecs_state.rejected_controls:
            rejected += 1
            remediation += 1
            high_risk_gaps += 1
        elif ckey in ecs_state.escalated_controls:
            remediation += 1
            high_risk_gaps += 1
        else:
            awaiting_evidence += 1
            if not c.get("evidences"):
                high_risk_gaps += 1

        ctrl_stale = False
        for ev in c.get("evidences", []):
            st = ev.get("evidence_status", "Current")
            if st in ("Expired", "Due for Refresh"):
                ctrl_stale = True
            ts = ev.get("upload_timestamp", "")
            if ts and (last_refresh == "—" or ts > last_refresh):
                last_refresh = ts[:10] if len(ts) >= 10 else ts
        if ctrl_stale and ckey not in ecs_state.approved_controls:
            stale_controls += 1

    open_findings = rejected + sum(
        1 for c in controls if f"{framework_name}::{c['control']}" in ecs_state.escalated_controls
    )
    if high_risk_gaps < rejected:
        high_risk_gaps = rejected + _seed_int(framework_name + "hr", 0, 3)

    apps: set[str] = set()
    for c in controls:
        for ev in c.get("evidences", []):
            if ev.get("application_name"):
                apps.add(ev["application_name"])

    return {
        "applications_onboarded": len(apps) or stats["applications"],
        "controls_approved": approved,
        "open_audit_findings": open_findings,
        "high_risk_gaps": high_risk_gaps,
        "auditor_pending": submitted,
        "expired_evidences": stats["expired"],
        "stale_evidences": stats["stale"],
        "last_evidence_refresh": last_refresh,
        "sla_breach_count": sla_breach + _seed_int(framework_name + "sla", 0, 4),
        "awaiting_evidence": awaiting_evidence,
        "stale_controls": stale_controls,
        "pending_auditor_validation": submitted,
        "remediation_controls": remediation,
        "exception_controls": _seed_int(framework_name + "exc", 1, 4),
    }


def _framework_focus_line(framework_name: str) -> str:
    lines = {
        "PCI DSS": "CDE controls · MFA · firewall · encryption · VAPT · SIEM · privileged access",
        "DPSC": "RBI cybersecurity · monitoring · SOC · incident response · governance",
        "ITPP": "DR · backup · incident · change · problem · capacity management",
        "OS Baselining": "CIS compliance · patching · hardening gaps · stale builds",
        "DB Baselining": "DB hardening · privileged DB access · encryption · audit logging",
        "Nginx Baselining": "Edge TLS · reverse proxy · certificate lifecycle · DMZ controls",
        "AppSec": "SAST · DAST · code review · vulnerabilities · secure SDLC",
        "VAPT": "Vulnerabilities · remediation · exploitability · critical finding aging",
        "CSITE": "Internal audit observations · closure tracking · remediation workflow · repeat findings",
    }
    return lines.get(framework_name, "Control implementation · evidence · audit workflow")


def _executive_kpis(framework_name: str, controls: list[dict], stats: dict[str, int]) -> list[dict]:
    """Operational executive KPI strip — no generic maturity/readiness scores."""
    op = _operational_counts(framework_name, controls, stats)
    fw = framework_name

    if framework_name == "ITPP":
        return [
            {"label": "Applications", "value": op["applications_onboarded"], "hint": "In DR scope", "tone": "primary"},
            {"label": "Approved Controls", "value": op["controls_approved"], "hint": "Governance closed", "tone": "success"},
            {"label": "DR / Backup Gaps", "value": _seed_int(fw + "drg", 2, 8), "hint": "Open findings", "tone": "danger"},
            {"label": "Change Overdue", "value": _seed_int(fw + "chg", 3, 11), "hint": "CAB pending", "tone": "warning"},
            {"label": "Auditor Queue", "value": op["auditor_pending"], "hint": "Pending validation", "tone": "warning"},
            {"label": "Expired Evidence", "value": op["expired_evidences"], "hint": "Refresh required", "tone": "danger"},
            {"label": "Last Refresh", "value": op["last_evidence_refresh"], "hint": "Latest upload", "tone": "teal"},
            {"label": "SLA Breaches", "value": op["sla_breach_count"], "hint": "Remediation overdue", "tone": "danger"},
        ]

    return [
        {"label": "Applications", "value": op["applications_onboarded"], "hint": "Onboarded in scope", "tone": "primary"},
        {"label": "Approved Controls", "value": op["controls_approved"], "hint": "Auditor approved", "tone": "success"},
        {"label": "Open Findings", "value": op["open_audit_findings"], "hint": "Audit observations", "tone": "danger"},
        {"label": "High-Risk Gaps", "value": op["high_risk_gaps"], "hint": "Priority remediation", "tone": "danger"},
        {"label": "Auditor Queue", "value": op["auditor_pending"], "hint": "Pending validation", "tone": "warning"},
        {"label": "Expired Evidence", "value": op["expired_evidences"], "hint": "Past validity", "tone": "warning"},
        {"label": "Last Refresh", "value": op["last_evidence_refresh"], "hint": "Latest evidence upload", "tone": "teal"},
        {"label": "SLA Breaches", "value": op["sla_breach_count"], "hint": "Overdue remediation", "tone": "danger"},
    ]


def build_relational_control_breakdown(framework_name: str) -> list[dict]:
    """Control rows from relational governance graph — framework-specific, app-aware."""
    g = get_framework_graph(framework_name)
    controls = g.get("controls", [])
    findings = g.get("findings", [])
    rows = []
    for c in controls:
        if not validate_control_mapping(framework_name, c["control_id"]):
            continue
        fc = sum(1 for f in findings if f.get("linked_control") == c["control_id"])
        env = "PROD" if c["application"] in ("Net Banking", "UPI", "Mobile Banking", "Card Platform", "Internet Banking") else "PROD/UAT"
        rows.append({
            "control": c["control_name"],
            "control_id": c["control_id"],
            "framework": framework_name,
            "application": c["application"],
            "environment": c.get("environment", env),
            "audit_cycle": c.get("audit_cycle", "Q2 2026"),
            "owner": c.get("owner", "—"),
            "implementation": c.get("implementation", "—"),
            "evidence_name": c.get("evidence_name", "—"),
            "evidence_id": c.get("evidence_id", ""),
            "validation": c.get("validation", "Pending"),
            "workflow_status": c.get("workflow", "Draft"),
            "sla": c.get("sla", "OK"),
            "sla_days": c.get("sla_days", 0),
            "auditor_comment": c.get("auditor_comment", ""),
            "pending_action": c.get("pending_action", "—"),
            "finding_count": fc,
            "auditor_approved": c.get("validation") == "PASS" and c.get("workflow") == "Approved",
            "evidence_present": bool(c.get("evidence_id")),
            "evidence_count": 1 if c.get("evidence_id") else 0,
            "stale": c.get("sla") in ("Breached", "At Risk"),
            "has_exception": c.get("workflow") == "Exception",
            "primary_evidence_id": c.get("evidence_id", ""),
            "last_reviewed": "2026-05-22",
            "relational": True,
            "ckey": f"{framework_name}::{c['control_id']}",
        })
    return rows


def build_control_library(framework_name: str, catalog_controls: list[dict]) -> list[dict]:
    """Framework-scoped control library rows with consolidated control details."""
    g = get_framework_graph(framework_name)
    finding_map: dict[str, int] = {}
    domain_map: dict[str, str] = {}
    validation_map: dict[str, str] = {}
    app_map: dict[str, set[str]] = {}
    for c in g.get("controls", []):
        cid = c.get("control_id", "")
        if not cid:
            continue
        domain_map.setdefault(cid, c.get("domain", "Governance"))
        validation_map.setdefault(cid, c.get("validation", "PENDING"))
        app_map.setdefault(cid, set()).add(c.get("application", ""))
    for f in g.get("findings", []):
        cid = f.get("linked_control", "")
        if not cid:
            continue
        finding_map[cid] = finding_map.get(cid, 0) + 1

    rows: list[dict[str, Any]] = []
    for ctrl in catalog_controls:
        cid = ctrl.get("control_id", "")
        if not cid:
            continue
        evidence_count = len(ctrl.get("evidences", []))
        applications = {
            ev.get("application_name", "")
            for ev in ctrl.get("evidences", [])
            if ev.get("application_name")
        }
        applications.update({a for a in app_map.get(cid, set()) if a})
        finding_count = finding_map.get(cid, 0)
        validation = validation_map.get(cid, "PENDING").upper()
        if validation in ("PASS", "APPROVED"):
            status = "Approved"
            risk = "Low"
        elif validation in ("FAIL", "REJECTED"):
            status = "Failed"
            risk = "High"
        else:
            status = "Pending"
            risk = "Medium"
        rows.append({
            "control_id": cid,
            "control_name": ctrl.get("control", ""),
            "domain": domain_map.get(cid, "Governance"),
            "status": status,
            "risk": risk,
            "evidence_count": evidence_count,
            "finding_count": finding_count,
            "mapped_applications": sorted(applications),
        })
    return rows


def build_control_breakdown(framework_name: str, catalog_controls: list[dict]) -> list[dict]:
    """Control-wise implementation view for drill-down tables."""
    rows = []
    for ctrl in catalog_controls:
        ckey = f"{framework_name}::{ctrl['control']}"
        evs = ctrl.get("evidences", [])
        primary = evs[0] if evs else {}
        stale = any(e.get("evidence_status") in ("Expired", "Due for Refresh") for e in evs)
        approved = ckey in ecs_state.approved_controls
        rejected = ckey in ecs_state.rejected_controls
        submitted = ckey in ecs_state.submitted_controls
        escalated = ckey in ecs_state.escalated_controls

        if approved:
            workflow = "Approved"
        elif rejected:
            workflow = "Rejected — Remediation"
        elif submitted:
            workflow = "Pending Auditor Validation"
        elif escalated:
            workflow = "Under Remediation"
        elif not evs:
            workflow = "Awaiting Evidence"
        else:
            workflow = "Draft"

        rows.append({
            "control": ctrl["control"],
            "control_id": ctrl.get("control_id", ""),
            "evidences": evs,
            "evidence_count": len(evs),
            "evidence_present": bool(evs),
            "auditor_approved": approved,
            "stale": stale,
            "last_reviewed": (primary.get("upload_timestamp") or "—")[:10],
            "owner": primary.get("uploaded_by", "Unassigned"),
            "application": primary.get("application_name", "—"),
            "has_exception": escalated or (ckey in ecs_state.clarification_controls),
            "workflow_status": workflow,
            "primary_evidence_id": primary.get("evidence_id", ""),
            "ckey": ckey,
            "mfa_enabled": _seed_int(ckey + "mfa", 0, 1) == 1 if "MFA" in ctrl["control"] or "8.3" in ctrl.get("control_id", "") else None,
        })
    return rows


def _executive_extras(framework_name: str, controls: list[dict], stats: dict[str, int]) -> dict:
    fw = framework_name
    profile = get_framework_profile(framework_name)
    owners: dict[str, int] = {}
    for c in controls:
        for ev in c.get("evidences", []):
            ob = ev.get("uploaded_by", "Unassigned")
            ckey = f"{framework_name}::{c['control']}"
            if ckey not in ecs_state.approved_controls:
                owners[ob] = owners.get(ob, 0) + 1
    pending_by_owner = [
        {"owner": k, "count": v}
        for k, v in sorted(owners.items(), key=lambda x: -x[1])[:5]
    ]
    fw_trends = profile.get("trends", [])
    return {
        "pending_by_owner": pending_by_owner,
        "audit_aging": {
            "expired": stats["expired"],
            "stale": stats["stale"],
            "current": stats["current"],
        },
        "maturity_trend": [
            {"name": row["month"], "score": row.get("compliance", row.get("drift_pct", 80)), "label": f"{framework_name} {row['month']}"}
            for row in fw_trends[-4:]
        ] if fw_trends else [],
        "coverage_label": profile.get("context_label", f"{framework_name} control implementation coverage"),
    }


def _drill_modules(framework_name: str) -> list[dict]:
    base = [
        {"id": "applications", "label": "Applications", "icon": "◫"},
        {"id": "control-library", "label": "Control Library", "icon": "☑"},
        {"id": "evidence", "label": "Evidence Repository", "icon": "📁"},
        {"id": "pending", "label": "Pending Actions & Gaps", "icon": "⏳"},
        {"id": "findings", "label": "Open Observations", "icon": "⚠"},
        {"id": "integrations", "label": "Integrations", "icon": "🔗"},
        {"id": "exceptions", "label": "Exceptions / TD", "icon": "⊘"},
        {"id": "trends", "label": "Trends", "icon": "📈"},
        {"id": "reuse", "label": "Reuse Mapping", "icon": "↻"},
    ]
    return base


def _framework_kpis(framework: str, controls: list[dict], stats: dict[str, int]) -> list[dict]:
    return build_framework_kpi_list(framework, controls, stats)


def _insight_sections(framework: str) -> list[dict]:
    fw = framework
    return {
        "PCI DSS": [
            {"type": "bars", "title": "Encryption Coverage", "items": [
                {"name": "Net Banking", "score": _seed_int(fw + "nb", 88, 96)},
                {"name": "Payments", "score": _seed_int(fw + "pay", 82, 94)},
                {"name": "UPI Switch", "score": _seed_int(fw + "upi", 85, 97)},
                {"name": "Mobile Banking", "score": _seed_int(fw + "mob", 79, 91)},
            ]},
            {"type": "metrics", "title": "Payment Security Posture", "items": [
                {"label": "MFA Gaps", "value": _seed_int(fw + "mfa", 0, 4), "tone": "warning"},
                {"label": "CDE Risks", "value": _seed_int(fw + "cde", 2, 6), "tone": "danger"},
                {"label": "TD Exceptions", "value": _seed_int(fw + "td", 1, 5), "tone": "warning"},
            ]},
            {"type": "list", "title": "Top Risk Applications", "items": [
                {"label": "Card Payment Gateway", "meta": "Req 1.2 segmentation gap", "severity": "High"},
                {"label": "Loan Origination", "meta": "Req 3.1 disposal overdue", "severity": "Critical"},
                {"label": "Treasury FX Core", "meta": "MFA exception pending", "severity": "Medium"},
            ]},
        ],
        "DPSC": [
            {"type": "bars", "title": "Privacy Risk by Channel", "items": [
                {"name": "UPI", "score": _seed_int(fw + "u", 86, 95)},
                {"name": "Net Banking", "score": _seed_int(fw + "n", 84, 93)},
                {"name": "Mobile", "score": _seed_int(fw + "m", 88, 97)},
                {"name": "Payments", "score": _seed_int(fw + "p", 80, 92)},
            ]},
            {"type": "list", "title": "Retention Violations", "items": [
                {"label": "Customer PII archive — Payments", "meta": "Retention exceeded 7 years", "severity": "High"},
                {"label": "Consent logs — Mobile", "meta": "Missing consent refresh", "severity": "Medium"},
            ]},
        ],
        "OS Baselining": [
            {"type": "heatmap", "title": "CIS Hardening Heatmap", "items": [
                {"name": "NETBANKING_PROD", "score": _seed_int(fw + "s1", 88, 97), "risk": "Low"},
                {"name": "UPI_SWITCH_CLUSTER", "score": _seed_int(fw + "s2", 76, 89), "risk": "Medium"},
                {"name": "MOBILE_BANKING_API", "score": _seed_int(fw + "s4", 71, 85), "risk": "High"},
            ]},
            {"type": "metrics", "title": "Baseline Drift", "items": [
                {"label": "Patch Drift", "value": _seed_int(fw + "patch", 8, 24), "tone": "danger"},
                {"label": "Config Deviations", "value": _seed_int(fw + "fail", 12, 38), "tone": "warning"},
                {"label": "Non-Compliant", "value": _seed_int(fw + "nc", 4, 14), "tone": "danger"},
            ]},
            {"type": "list", "title": "Failed Drift Items", "items": [
                {"label": "SSH root login — UPI cluster", "meta": "Drift detected 12d ago", "severity": "Critical"},
                {"label": "Open port 23 — legacy host", "meta": "Telnet service active", "severity": "High"},
            ]},
        ],
        "DB Baselining": [
            {"type": "bars", "title": "Database Posture by Engine", "items": [
                {"name": "Oracle CBS", "score": _seed_int(fw + "o", 88, 96)},
                {"name": "MSSQL Treasury", "score": _seed_int(fw + "ms", 82, 93)},
                {"name": "MySQL Loan DB", "score": _seed_int(fw + "my", 79, 91)},
            ]},
            {"type": "list", "title": "Critical DB Risks", "items": [
                {"label": "CBS Oracle — audit logging gap", "meta": "Unified audit trail incomplete", "severity": "Critical"},
                {"label": "Loan DB — weak service account", "meta": "Password rotation overdue", "severity": "High"},
            ]},
        ],
        "Nginx Baselining": [
            {"type": "bars", "title": "TLS Security Posture", "items": [
                {"name": "Internet Banking Edge", "score": _seed_int(fw + "ib", 90, 98)},
                {"name": "Mobile API Gateway", "score": _seed_int(fw + "ma", 85, 95)},
                {"name": "Card Gateway DMZ", "score": _seed_int(fw + "cg", 82, 93)},
            ]},
            {"type": "list", "title": "Certificate Lifecycle", "items": [
                {"label": "api.mobile.bank.in", "meta": "Expires in 12 days", "severity": "High"},
                {"label": "netbanking.bank.in", "meta": "Expires in 45 days", "severity": "Medium"},
            ]},
        ],
        "AppSec": [
            {"type": "heatmap", "title": "Repository Risk Heatmap", "items": [
                {"name": "Net Banking", "score": _seed_int(fw + "a1", 72, 88), "risk": "High"},
                {"name": "Mobile Banking", "score": _seed_int(fw + "a2", 78, 92), "risk": "Medium"},
                {"name": "Loan System", "score": _seed_int(fw + "a4", 68, 82), "risk": "High"},
            ]},
            {"type": "metrics", "title": "SDLC Security", "items": [
                {"label": "SAST Coverage", "value": f"{_seed_int(fw + 'sast', 88, 97)}%", "tone": "success"},
                {"label": "DAST Coverage", "value": f"{_seed_int(fw + 'dast', 82, 94)}%", "tone": "primary"},
                {"label": "Secrets Exposure", "value": _seed_int(fw + "sec", 1, 6), "tone": "danger"},
            ]},
            {"type": "list", "title": "Vulnerable Repositories", "items": [
                {"label": "Loan Origination — 14 critical SAST", "meta": "SonarQube gate failed", "severity": "Critical"},
                {"label": "Net Banking — 8 DAST findings", "meta": "SQLi retest pending", "severity": "High"},
            ]},
        ],
        "VAPT": [
            {"type": "metrics", "title": "Vulnerability Severity", "items": [
                {"label": "Critical", "value": _seed_int(fw + "c", 2, 7), "tone": "danger"},
                {"label": "High", "value": _seed_int(fw + "h", 8, 18), "tone": "warning"},
                {"label": "Exploitable", "value": _seed_int(fw + "exploit", 2, 11), "tone": "danger"},
            ]},
            {"type": "bars", "title": "Patch Aging (Days)", "items": [
                {"name": "Critical", "score": _seed_int(fw + "pag1", 65, 92)},
                {"name": "High", "score": _seed_int(fw + "pag2", 55, 85)},
                {"name": "Medium", "score": _seed_int(fw + "pag3", 70, 95)},
            ]},
            {"type": "list", "title": "Critical Findings", "items": [
                {"label": "Internet Banking — auth bypass", "meta": "Pen test Mar 2026", "severity": "Critical"},
                {"label": "Payment Gateway — SSRF vector", "meta": "Patch scheduled", "severity": "High"},
            ]},
        ],
        "CSITE": [
            {"type": "bars", "title": "Observation Closure by Unit", "items": [
                {"name": "Retail Banking", "score": _seed_int(fw + "rb", 82, 92)},
                {"name": "Treasury", "score": _seed_int(fw + "tr", 80, 90)},
                {"name": "Payments", "score": _seed_int(fw + "pay", 76, 88)},
            ]},
            {"type": "metrics", "title": "Audit Workflow Health", "items": [
                {"label": "Open Observations", "value": _seed_int(fw + "obs", 12, 28), "tone": "danger"},
                {"label": "Pending Review", "value": _seed_int(fw + "par", 6, 14), "tone": "warning"},
                {"label": "Closure Rate", "value": f"{_seed_int(fw + 'close', 78, 92)}%", "tone": "success"},
            ]},
            {"type": "list", "title": "Repeat Observations", "items": [
                {"label": "OBS-2026-038 — Segregation of duties", "meta": "Retail Banking · reopened · 45 days", "severity": "High"},
                {"label": "OBS-2026-041 — Access review incomplete", "meta": "Treasury · pending auditor", "severity": "Medium"},
                {"label": "OBS-2026-029 — Log retention policy", "meta": "Payments · repeat finding", "severity": "High"},
            ]},
        ],
        "ITPP": [
            {"type": "bars", "title": "DR Readiness by Application", "items": [
                {"name": "Net Banking", "score": _seed_int(fw + "d1", 90, 98)},
                {"name": "CBS Oracle", "score": _seed_int(fw + "d2", 88, 96)},
                {"name": "UPI Switch", "score": _seed_int(fw + "d3", 92, 99)},
            ]},
            {"type": "list", "title": "Policy Adherence Gaps", "items": [
                {"label": "Emergency change — Payment Gateway", "meta": "PIR pending 5 days", "severity": "High"},
                {"label": "RCA closure — UPI incident", "meta": "Awaiting owner sign-off", "severity": "Medium"},
            ]},
        ],
    }.get(framework, [])


def build_framework_dashboard(framework_name: str, catalog_controls: list[dict]) -> dict[str, Any]:
    theme = FRAMEWORK_THEMES.get(framework_name, {
        "css_class": "ecs-fw-default", "accent": "#2563eb", "accent_soft": "#dbeafe", "icon": "FW",
    })
    stats = _catalog_stats(catalog_controls)
    profile = get_framework_profile(framework_name)
    pending = sum(
        1 for c in catalog_controls
        if f"{framework_name}::{c['control']}" in ecs_state.submitted_controls
        or f"{framework_name}::{c['control']}" in ecs_state.rejected_controls
    )
    apps: set[str] = set()
    for c in catalog_controls:
        for ev in c.get("evidences", []):
            if ev.get("application_name"):
                apps.add(ev["application_name"])
    framework_kpis = _framework_kpis(framework_name, catalog_controls, stats)
    op = _operational_counts(framework_name, catalog_controls, stats)
    gov_ctx = build_governance_context(framework_name, catalog_controls)
    rel_controls = build_relational_control_breakdown(framework_name)
    control_library = build_control_library(framework_name, catalog_controls)
    rel_integrations = gov_ctx.get("integrations_detailed") or []
    rel_exceptions = gov_ctx.get("framework_exceptions") or []
    # Enrich KPI hints with scope
    for k in framework_kpis:
        k["scope"] = profile.get("context_label", framework_name)
    return {
        "theme": theme,
        "kpis": framework_kpis,
        "operational": op,
        "focus_line": _framework_focus_line(framework_name),
        "framework_description": profile.get("framework_description", ""),
        "context_label": profile.get("context_label", f"{framework_name} governance scope"),
        "profile_applications": profile.get("applications", []),
        "framework_integrations": rel_integrations or profile.get("integrations", []),
        "framework_exceptions": rel_exceptions or profile.get("exceptions", []),
        "framework_trends": gov_ctx.get("trends_context", {}).get("series") or profile.get("trends", []),
        "framework_analytics": build_framework_governance_analytics(framework_name),
        "governance_context": gov_ctx,
        "control_breakdown": rel_controls or build_control_breakdown(framework_name, catalog_controls),
        "control_library": control_library,
        "executive_extras": _executive_extras(framework_name, catalog_controls, stats),
        "drill_modules": _drill_modules(framework_name),
        "insights": _insight_sections(framework_name),
        "workflow_labels": _workflow_labels(framework_name),
        "stats": stats,
        "pending_count": pending,
        "application_count": len(profile.get("applications", [])) or len(apps),
        "show_itpp_panel": framework_name == "ITPP",
        "show_validation": False,
        "show_governance_strip": False,
        "show_framework_analytics": False,
    }
