"""Relational banking ECS governance graph — every object links framework → app → control → evidence → finding."""

from __future__ import annotations

from typing import Any

APP_OWNERS: dict[str, str] = {
    "Net Banking": "R. Mehta",
    "Mobile Banking": "A. Sharma",
    "UPI": "P. Nair",
    "Treasury": "S. Banerjee",
    "Loan System": "V. Rao",
    "Payments": "K. Iyer",
    "Wealth Portal": "V. Rao",
    "Internet Banking": "A. Sharma",
    "Card Platform": "R. Mehta",
    "CRM": "K. Iyer",
    "Card Payments": "R. Mehta",
    "Core Banking": "S. Banerjee",
    "Oracle Core DB": "S. Banerjee",
    "Payments DB": "K. Iyer",
    "Treasury DB": "S. Banerjee",
    "UPI Gateway": "P. Nair",
    "API Gateway": "P. Nair",
    "Mobile Banking Edge": "A. Sharma",
    "Retail Banking": "R. Mehta",
    "UPI Switch": "P. Nair",
    "CBS Oracle": "S. Banerjee",
}


def _owner(app: str) -> str:
    return APP_OWNERS.get(app, "R. Mehta")


# ─── Per-framework relational graphs ─────────────────────────────────────────

FRAMEWORK_GRAPHS: dict[str, dict[str, Any]] = {}


def _g(fw: str, apps: list, controls: list, findings: list, evidence: list,
       integrations: list, reuse: list, exceptions: list, trends: dict,
       pending: list, gaps: list | None = None):
    FRAMEWORK_GRAPHS[fw] = {
        "applications": apps,
        "controls": controls,
        "findings": findings,
        "evidence": evidence,
        "integrations": integrations,
        "reuse_mappings": reuse,
        "exceptions": exceptions,
        "trends": trends,
        "pending_actions": pending,
        "open_gaps": gaps or [],
    }


# ── AppSec ──
_g(
    "AppSec",
    apps=[
        {"name": "Mobile Banking", "owner": "A. Sharma", "controls_implemented": 14, "open_findings": 5, "failed_controls": 2, "stale_evidence": 2, "sla_breaches": 1, "audit_readiness_pct": 76.8, "focus": "SAST gate · secrets · SonarQube"},
        {"name": "Loan System", "owner": "V. Rao", "controls_implemented": 11, "open_findings": 8, "failed_controls": 3, "stale_evidence": 3, "sla_breaches": 2, "audit_readiness_pct": 71.2, "focus": "Checkmarx · 14 critical SAST"},
        {"name": "Wealth Portal", "owner": "V. Rao", "controls_implemented": 16, "open_findings": 3, "failed_controls": 1, "stale_evidence": 1, "sla_breaches": 0, "audit_readiness_pct": 83.5, "focus": "SCA · DAST · dependency risk"},
    ],
    controls=[
        {"control_id": "AS-C-01", "control_name": "Secure Coding Review", "application": "Mobile Banking", "owner": "A. Sharma", "implementation": "Implemented", "evidence_id": "EV-AS-001", "evidence_name": "Secure Coding SOP v4.2", "validation": "PASS", "workflow": "Approved", "sla": "OK", "sla_days": 0, "auditor_comment": "Peer review process documented", "pending_action": "—"},
        {"control_id": "AS-C-02", "control_name": "SAST Pipeline Validation", "application": "Mobile Banking", "owner": "A. Sharma", "implementation": "Partial", "evidence_id": "EV-AS-002", "evidence_name": "SonarQube Gate Report Q2-2026", "validation": "FAIL", "workflow": "Rejected", "sla": "Breached", "sla_days": 6, "auditor_comment": "Quality gate failed — 14 critical findings open", "pending_action": "Upload clean SAST report"},
        {"control_id": "AS-C-03", "control_name": "Third Party Dependency Approval", "application": "Wealth Portal", "owner": "V. Rao", "implementation": "Implemented", "evidence_id": "EV-AS-003", "evidence_name": "SCA Dependency Whitelist May2026", "validation": "WARN", "workflow": "Pending Review", "sla": "At Risk", "sla_days": 28, "auditor_comment": "22 libraries pending approval", "pending_action": "Submit dependency exceptions"},
        {"control_id": "AS-C-04", "control_name": "Secrets Detection", "application": "Mobile Banking", "owner": "A. Sharma", "implementation": "Failed", "evidence_id": "EV-AS-004", "evidence_name": "GitHub Secret Scan Export", "validation": "FAIL", "workflow": "Rejected", "sla": "Breached", "sla_days": 4, "auditor_comment": "Hardcoded API key not rotated", "pending_action": "Rotate key and upload proof"},
        {"control_id": "AS-C-05", "control_name": "DAST Pre-Production Gate", "application": "Loan System", "owner": "V. Rao", "implementation": "Partial", "evidence_id": "EV-AS-005", "evidence_name": "Burp Suite DAST Report Apr2026", "validation": "WARN", "workflow": "Pending Review", "sla": "At Risk", "sla_days": 18, "auditor_comment": "8 high findings — retest pending", "pending_action": "Close DAST findings"},
    ],
    findings=[
        {"finding_id": "AS-F-001", "application": "Mobile Banking", "observation": "Hardcoded API key in mobile-banking-config repo", "severity": "Critical", "source": "GitHub Advanced Security", "integration": "GitHub Advanced Security", "open_since": "2026-05-14", "linked_control": "AS-C-04", "linked_evidence": "EV-AS-004", "owner": "A. Sharma", "status": "Open", "aging_days": 10, "escalation": "App Owner", "auditor_notes": "Key must be rotated before release 4.2.1", "closure_dependency": "Secret rotation proof"},
        {"finding_id": "AS-F-002", "application": "Loan System", "observation": "14 critical SAST findings — SonarQube quality gate failed", "severity": "Critical", "source": "SonarQube Enterprise", "integration": "SonarQube Enterprise", "open_since": "2026-05-10", "linked_control": "AS-C-02", "linked_evidence": "EV-AS-002", "owner": "V. Rao", "status": "Open", "aging_days": 14, "escalation": "—", "auditor_notes": "Block release until gate passes", "closure_dependency": "Clean SAST scan"},
        {"finding_id": "AS-F-003", "application": "Wealth Portal", "observation": "Log4j variant CVE-2026-4421 in wealth-api module", "severity": "High", "source": "Checkmarx SCA", "integration": "Checkmarx SAST", "open_since": "2026-05-08", "linked_control": "AS-C-03", "linked_evidence": "EV-AS-003", "owner": "V. Rao", "status": "Remediation", "aging_days": 16, "escalation": "—", "auditor_notes": "Patch scheduled sprint 23", "closure_dependency": "Updated SCA report"},
    ],
    evidence=[
        {"evidence_id": "EV-AS-001", "name": "Secure Coding SOP v4.2", "application": "Mobile Banking", "control_id": "AS-C-01", "uploaded_by": "A. Sharma", "type": "Policy", "lifecycle": "Approved", "validation": "Validated", "expiry": "2026-12-31", "audit_cycle": "Q2 2026", "linked_findings": "—", "reuse_eligible": True, "source_integration": "SharePoint"},
        {"evidence_id": "EV-AS-002", "name": "SonarQube Gate Report Q2-2026", "application": "Mobile Banking", "control_id": "AS-C-02", "uploaded_by": "A. Sharma", "type": "SAST Report", "lifecycle": "Rejected", "validation": "Failed", "expiry": "2026-06-30", "audit_cycle": "Q2 2026", "linked_findings": "AS-F-002", "reuse_eligible": False, "source_integration": "SonarQube Enterprise"},
        {"evidence_id": "EV-AS-004", "name": "GitHub Secret Scan Export", "application": "Mobile Banking", "control_id": "AS-C-04", "uploaded_by": "A. Sharma", "type": "Secret Scan", "lifecycle": "Rejected", "validation": "Failed", "expiry": "2026-05-31", "audit_cycle": "Q2 2026", "linked_findings": "AS-F-001", "reuse_eligible": False, "source_integration": "GitHub Advanced Security"},
        {"evidence_id": "EV-AS-005", "name": "Burp Suite DAST Report Apr2026", "application": "Loan System", "control_id": "AS-C-05", "uploaded_by": "V. Rao", "type": "DAST Report", "lifecycle": "Pending Review", "validation": "Warning", "expiry": "2026-07-15", "audit_cycle": "Q2 2026", "linked_findings": "—", "reuse_eligible": True, "source_integration": "Burp Enterprise"},
    ],
    integrations=[
        {"name": "SonarQube Enterprise", "applications": ["Mobile Banking", "Internet Banking"], "frameworks_covered": ["AppSec"], "controls_populated": 12, "last_sync": "2026-05-24 06:02 UTC", "health": "Healthy", "failed_jobs": 0, "evidence_collected": 234, "sync_note": "SAST gates for 2 tier-1 repos"},
        {"name": "Checkmarx SAST", "applications": ["UPI", "Wealth Portal", "Loan System"], "frameworks_covered": ["AppSec"], "controls_populated": 9, "last_sync": "2026-05-24 05:52 UTC", "health": "Healthy", "failed_jobs": 0, "evidence_collected": 178, "sync_note": "SCA + SAST for loan portal"},
        {"name": "GitHub Advanced Security", "applications": ["Mobile Banking", "Wealth Portal"], "frameworks_covered": ["AppSec"], "controls_populated": 6, "last_sync": "2026-05-24 05:30 UTC", "health": "Degraded", "failed_jobs": 1, "evidence_collected": 45, "sync_note": "Secret scan — 1 repo auth failure"},
        {"name": "Jira Security Remediation", "applications": ["Mobile Banking", "Loan System"], "frameworks_covered": ["AppSec", "VAPT"], "controls_populated": 8, "last_sync": "2026-05-24 06:05 UTC", "health": "Healthy", "failed_jobs": 0, "evidence_collected": 0, "sync_note": "Remediation ticket sync"},
    ],
    reuse=[
        {"source_framework": "AppSec", "source_control": "AS-C-02 SAST Pipeline Validation", "target_framework": "PCI DSS", "target_control": "Req 6.3 — Secure Development", "shared_evidence": "SAST Pipeline Report Q2", "confidence_pct": 88, "applications": "Mobile Banking, Internet Banking"},
        {"source_framework": "AppSec", "source_control": "AS-C-04 Secrets Detection", "target_framework": "VAPT", "target_control": "VP-C-01 External Pentest Closure", "shared_evidence": "Secret scan remediation proof", "confidence_pct": 82, "applications": "Mobile Banking"},
    ],
    exceptions=[
        {"id": "TD-AS-011", "control_id": "AS-C-02", "application": "Loan System", "title": "SAST gate waiver — legacy COBOL module", "justification": "COBOL module scheduled for decommission Q4 2026", "compensating": "Manual code review by AppSec team", "approver": "CISO Office", "expires": "2026-12-31", "status": "Active"},
    ],
    trends={"label": "AppSec SDLC posture (Feb–May 2026)", "metrics": [
        {"month": "Feb", "sast_pass_pct": 72, "dependency_vulns": 48, "secrets_exposure": 6},
        {"month": "Mar", "sast_pass_pct": 76, "dependency_vulns": 42, "secrets_exposure": 5},
        {"month": "Apr", "sast_pass_pct": 79, "dependency_vulns": 35, "secrets_exposure": 3},
        {"month": "May", "sast_pass_pct": 81, "dependency_vulns": 28, "secrets_exposure": 2},
    ], "metric_labels": ["SAST Pass %", "Open Dependency CVEs", "Secrets Exposure"]},
    pending=[
        {"framework": "AppSec", "application": "Mobile Banking", "control_id": "AS-C-04", "control_name": "Secrets Detection", "finding_id": "AS-F-001", "owner": "A. Sharma", "action": "Rotate API key and upload GitHub secret scan clean report", "due_date": "2026-05-28", "sla_aging_days": 4, "risk": "Critical", "blocker": "DevOps key rotation pending"},
        {"framework": "AppSec", "application": "Loan System", "control_id": "AS-C-02", "control_name": "SAST Pipeline Validation", "finding_id": "AS-F-002", "owner": "V. Rao", "action": "Remediate 14 critical SonarQube findings and re-run gate", "due_date": "2026-05-30", "sla_aging_days": 6, "risk": "Critical", "blocker": "Sprint capacity"},
    ],
    gaps=[
        {"control_id": "AS-C-04", "application": "Mobile Banking", "gap_type": "Failed validation", "finding_id": "AS-F-001", "owner": "A. Sharma", "risk": "Critical", "description": "Secrets detection failed — hardcoded API key"},
        {"control_id": "AS-C-02", "application": "Loan System", "gap_type": "Missing evidence", "finding_id": "AS-F-002", "owner": "V. Rao", "risk": "Critical", "description": "Clean SAST report not uploaded"},
    ],
)

# ── VAPT ──
_g(
    "VAPT",
    apps=[
        {"name": "UPI", "owner": "P. Nair", "controls_implemented": 9, "open_findings": 6, "failed_controls": 2, "stale_evidence": 1, "sla_breaches": 2, "audit_readiness_pct": 74.5, "focus": "SSRF · retest pending · Qualys"},
        {"name": "Internet Banking", "owner": "A. Sharma", "controls_implemented": 11, "open_findings": 4, "failed_controls": 1, "stale_evidence": 2, "sla_breaches": 1, "audit_readiness_pct": 77.8, "focus": "Auth bypass · pen-test Mar 2026"},
        {"name": "Net Banking", "owner": "R. Mehta", "controls_implemented": 13, "open_findings": 3, "failed_controls": 1, "stale_evidence": 1, "sla_breaches": 1, "audit_readiness_pct": 80.2, "focus": "CVE-2026-1842 patch"},
    ],
    controls=[
        {"control_id": "VP-C-01", "control_name": "External Pentest Closure", "application": "Internet Banking", "owner": "A. Sharma", "implementation": "Partial", "evidence_id": "EV-VP-001", "evidence_name": "External Pen-Test Report Mar2026", "validation": "WARN", "workflow": "Pending Review", "sla": "At Risk", "sla_days": 22, "auditor_comment": "Auth bypass finding open", "pending_action": "Upload retest evidence"},
        {"control_id": "VP-C-02", "control_name": "WAF Validation", "application": "UPI", "owner": "P. Nair", "implementation": "Failed", "evidence_id": "EV-VP-002", "evidence_name": "WAF Rule Export May2026", "validation": "FAIL", "workflow": "Rejected", "sla": "Breached", "sla_days": 12, "auditor_comment": "SSRF bypass rule missing", "pending_action": "Update WAF rules"},
        {"control_id": "VP-C-03", "control_name": "Retest Evidence Review", "application": "UPI", "owner": "P. Nair", "implementation": "Failed", "evidence_id": "EV-VP-003", "evidence_name": "Retest Report SSRF-UPI", "validation": "FAIL", "workflow": "Rejected", "sla": "Breached", "sla_days": 8, "auditor_comment": "Retest not uploaded after patch", "pending_action": "Upload retest evidence for VP-C-03"},
        {"control_id": "VP-C-04", "control_name": "Critical CVE Remediation", "application": "Net Banking", "owner": "R. Mehta", "implementation": "Partial", "evidence_id": "EV-VP-004", "evidence_name": "Qualys VA Scan May2026", "validation": "WARN", "workflow": "Pending Review", "sla": "At Risk", "sla_days": 15, "auditor_comment": "CVE-2026-1842 patch scheduled", "pending_action": "Upload patch validation"},
    ],
    findings=[
        {"finding_id": "VP-F-001", "application": "UPI", "observation": "SSRF in payment callback endpoint — exploitable", "severity": "Critical", "source": "External Pen-Test", "integration": "Qualys VMDR", "open_since": "2026-04-12", "linked_control": "VP-C-03", "linked_evidence": "EV-VP-003", "owner": "P. Nair", "status": "Open", "aging_days": 42, "escalation": "CISO", "auditor_notes": "Patch deployed — retest evidence missing", "closure_dependency": "Retest report VP-C-03"},
        {"finding_id": "VP-F-002", "application": "Internet Banking", "observation": "Session fixation — auth bypass vector", "severity": "High", "source": "DAST", "integration": "Burp Enterprise", "open_since": "2026-03-28", "linked_control": "VP-C-01", "linked_evidence": "EV-VP-001", "owner": "A. Sharma", "status": "Retest Pending", "aging_days": 57, "escalation": "—", "auditor_notes": "Fix deployed in v3.8.2", "closure_dependency": "Retest sign-off"},
        {"finding_id": "VP-F-003", "application": "Net Banking", "observation": "CVE-2026-1842 OpenSSL — critical exposure", "severity": "High", "source": "Qualys VMDR", "integration": "Qualys VMDR", "open_since": "2026-05-01", "linked_control": "VP-C-04", "linked_evidence": "EV-VP-004", "owner": "R. Mehta", "status": "Patch Scheduled", "aging_days": 23, "escalation": "—", "auditor_notes": "Change window May 28", "closure_dependency": "Post-patch VA scan"},
    ],
    evidence=[
        {"evidence_id": "EV-VP-001", "name": "External Pen-Test Report Mar2026", "application": "Internet Banking", "control_id": "VP-C-01", "uploaded_by": "A. Sharma", "type": "Pen-Test Report", "lifecycle": "Pending Review", "validation": "Warning", "expiry": "2026-09-30", "audit_cycle": "H1 2026", "linked_findings": "VP-F-002", "reuse_eligible": False, "source_integration": "SharePoint"},
        {"evidence_id": "EV-VP-003", "name": "Retest Report SSRF-UPI", "application": "UPI", "control_id": "VP-C-03", "uploaded_by": "P. Nair", "type": "Retest Report", "lifecycle": "Rejected", "validation": "Failed", "expiry": "2026-06-15", "audit_cycle": "Q2 2026", "linked_findings": "VP-F-001", "reuse_eligible": False, "source_integration": "Manual Upload"},
    ],
    integrations=[
        {"name": "Qualys VMDR", "applications": ["UPI", "Net Banking", "Internet Banking"], "frameworks_covered": ["VAPT"], "controls_populated": 8, "last_sync": "2026-05-24 05:45 UTC", "health": "Healthy", "failed_jobs": 0, "evidence_collected": 156, "sync_note": "External VA scan — 3 apps"},
        {"name": "Jira Security Remediation", "applications": ["UPI", "Internet Banking"], "frameworks_covered": ["VAPT", "AppSec"], "controls_populated": 14, "last_sync": "2026-05-24 06:05 UTC", "health": "Healthy", "failed_jobs": 0, "evidence_collected": 0, "sync_note": "VAPT finding remediation sync"},
        {"name": "F5 WAF", "applications": ["UPI Gateway", "Internet Banking"], "frameworks_covered": ["VAPT", "Nginx Baselining"], "controls_populated": 5, "last_sync": "2026-05-24 04:00 UTC", "health": "Degraded", "failed_jobs": 1, "evidence_collected": 24, "sync_note": "WAF rule export — SSRF rule gap"},
    ],
    reuse=[
        {"source_framework": "VAPT", "source_control": "VP-C-01 External Pentest Closure", "target_framework": "PCI DSS", "target_control": "Req 11.3 — External VA", "shared_evidence": "External Pen-Test Report Mar2026", "confidence_pct": 91, "applications": "Internet Banking, Net Banking"},
        {"source_framework": "AppSec", "source_control": "AS-C-02 SAST Pipeline", "target_framework": "VAPT", "target_control": "VP-C-01 External Pentest Closure", "shared_evidence": "SAST remediation tracker", "confidence_pct": 85, "applications": "Mobile Banking"},
    ],
    exceptions=[{"id": "TD-VP-005", "control_id": "VP-C-04", "application": "Net Banking", "title": "Patch deferral — OpenSSL CVE staging", "justification": "CAB-approved maintenance window", "compensating": "WAF rule + enhanced monitoring", "approver": "Risk Committee", "expires": "2026-06-15", "status": "Review Due"}],
    trends={"label": "VAPT exploitability & retest closure (Feb–May 2026)", "metrics": [
        {"month": "Feb", "exploitable_vulns": 9, "retest_closure_pct": 62, "critical_open": 7},
        {"month": "Mar", "exploitable_vulns": 7, "retest_closure_pct": 68, "critical_open": 6},
        {"month": "Apr", "exploitable_vulns": 5, "retest_closure_pct": 74, "critical_open": 4},
        {"month": "May", "exploitable_vulns": 4, "retest_closure_pct": 79, "critical_open": 3},
    ], "metric_labels": ["Exploitable Vulns", "Retest Closure %", "Critical Open"]},
    pending=[
        {"framework": "VAPT", "application": "UPI", "control_id": "VP-C-03", "control_name": "Retest Evidence Review", "finding_id": "VP-F-001", "owner": "P. Nair", "action": "Upload retest evidence for SSRF patch on UPI callback endpoint", "due_date": "2026-05-26", "sla_aging_days": 8, "risk": "Critical", "blocker": "Pen-test vendor report delayed"},
    ],
    gaps=[
        {"control_id": "VP-C-03", "application": "UPI", "gap_type": "Missing evidence", "finding_id": "VP-F-001", "owner": "P. Nair", "risk": "Critical", "description": "Retest report not uploaded after SSRF patch"},
    ],
)

# ── PCI DSS ──
_g(
    "PCI DSS",
    apps=[
        {"name": "Net Banking", "owner": "R. Mehta", "controls_implemented": 18, "open_findings": 2, "failed_controls": 1, "stale_evidence": 1, "sla_breaches": 0, "audit_readiness_pct": 86.2, "focus": "MFA · PAM · SIEM"},
        {"name": "Card Platform", "owner": "R. Mehta", "controls_implemented": 15, "open_findings": 4, "failed_controls": 2, "stale_evidence": 2, "sla_breaches": 1, "audit_readiness_pct": 78.9, "focus": "CDE segmentation · firewall"},
        {"name": "UPI", "owner": "P. Nair", "controls_implemented": 20, "open_findings": 1, "failed_controls": 0, "stale_evidence": 0, "sla_breaches": 0, "audit_readiness_pct": 91.4, "focus": "Tokenization · HSM"},
        {"name": "Mobile Banking", "owner": "A. Sharma", "controls_implemented": 17, "open_findings": 1, "failed_controls": 0, "stale_evidence": 1, "sla_breaches": 0, "audit_readiness_pct": 84.1, "focus": "Secure channel · MFA"},
    ],
    controls=[
        {"control_id": "PCI-7.2", "control_name": "CDE Access Restriction", "application": "Card Platform", "owner": "R. Mehta", "implementation": "Failed", "evidence_id": "EV-PCI-001", "evidence_name": "Firewall Rule Export Q2-2026", "validation": "FAIL", "workflow": "Rejected", "sla": "Breached", "sla_days": 10, "auditor_comment": "Segmentation test failed — gateway VLAN", "pending_action": "Upload updated firewall export"},
        {"control_id": "PCI-8.3", "control_name": "MFA for Privileged Access", "application": "Net Banking", "owner": "R. Mehta", "implementation": "Partial", "evidence_id": "EV-PCI-002", "evidence_name": "PAM MFA Enrollment Report", "validation": "WARN", "workflow": "Pending Review", "sla": "At Risk", "sla_days": 20, "auditor_comment": "2 jump servers exempted (TD-PCI-014)", "pending_action": "Close MFA exceptions"},
        {"control_id": "PCI-10.6", "control_name": "Log Review & SIEM Monitoring", "application": "Net Banking", "owner": "R. Mehta", "implementation": "Implemented", "evidence_id": "EV-PCI-003", "evidence_name": "SIEM Use-Case Export May2026", "validation": "PASS", "workflow": "Approved", "sla": "OK", "sla_days": 0, "auditor_comment": "Daily log review automated", "pending_action": "—"},
        {"control_id": "PCI-11.3", "control_name": "External Vulnerability Scan", "application": "Mobile Banking", "owner": "A. Sharma", "implementation": "Partial", "evidence_id": "EV-PCI-004", "evidence_name": "External VA Report Q1-2026", "validation": "WARN", "workflow": "Pending Review", "sla": "At Risk", "sla_days": 45, "auditor_comment": "Report stale — 45 days", "pending_action": "Upload Q2 VA report"},
    ],
    findings=[
        {"finding_id": "PCI-F-001", "application": "Card Platform", "observation": "CDE segmentation gap — payment gateway VLAN allows cross-zone traffic", "severity": "Critical", "source": "QSA Review", "integration": "ServiceNow GRC", "open_since": "2026-04-05", "linked_control": "PCI-7.2", "linked_evidence": "EV-PCI-001", "owner": "R. Mehta", "status": "Open", "aging_days": 49, "escalation": "QSA", "auditor_notes": "Must fix before audit window Jun 15", "closure_dependency": "Segmentation re-test"},
        {"finding_id": "PCI-F-002", "application": "Net Banking", "observation": "MFA not enforced on 2 privileged jump servers", "severity": "High", "source": "Access Review", "integration": "CyberArk PAM", "open_since": "2026-05-02", "linked_control": "PCI-8.3", "linked_evidence": "EV-PCI-002", "owner": "R. Mehta", "status": "Remediation", "aging_days": 22, "escalation": "—", "auditor_notes": "TD-PCI-014 active waiver", "closure_dependency": "MFA enrollment 100%"},
    ],
    evidence=[
        {"evidence_id": "EV-PCI-001", "name": "Firewall Rule Export Q2-2026", "application": "Card Platform", "control_id": "PCI-7.2", "uploaded_by": "R. Mehta", "type": "Firewall Export", "lifecycle": "Rejected", "validation": "Failed", "expiry": "2026-06-30", "audit_cycle": "Q2 2026", "linked_findings": "PCI-F-001", "reuse_eligible": False, "source_integration": "SharePoint"},
        {"evidence_id": "EV-PCI-002", "name": "PAM MFA Enrollment Report", "application": "Net Banking", "control_id": "PCI-8.3", "uploaded_by": "R. Mehta", "type": "MFA Report", "lifecycle": "Pending Review", "validation": "Warning", "expiry": "2026-07-31", "audit_cycle": "Q2 2026", "linked_findings": "PCI-F-002", "reuse_eligible": False, "source_integration": "CyberArk PAM"},
        {"evidence_id": "EV-PCI-003", "name": "SIEM Use-Case Export May2026", "application": "Net Banking", "control_id": "PCI-10.6", "uploaded_by": "R. Mehta", "type": "SIEM Export", "lifecycle": "Approved", "validation": "Validated", "expiry": "2026-08-31", "audit_cycle": "Q2 2026", "linked_findings": "OBS-PCI-1021", "reuse_eligible": True, "source_integration": "Splunk SIEM"},
        {"evidence_id": "EV-PCI-004", "name": "External VA Report Q1-2026", "application": "Mobile Banking", "control_id": "PCI-11.3", "uploaded_by": "A. Sharma", "type": "VA Report", "lifecycle": "Pending Review", "validation": "Warning", "expiry": "2026-06-30", "audit_cycle": "Q2 2026", "linked_findings": "—", "reuse_eligible": False, "source_integration": "SharePoint"},
    ],
    integrations=[
        {"name": "CyberArk PAM", "applications": ["Net Banking", "Card Platform"], "frameworks_covered": ["PCI DSS"], "controls_populated": 6, "last_sync": "2026-05-24 06:00 UTC", "health": "Healthy", "failed_jobs": 0, "evidence_collected": 89, "sync_note": "MFA + privileged access evidence"},
        {"name": "Splunk SIEM", "applications": ["Net Banking", "UPI", "Card Platform"], "frameworks_covered": ["PCI DSS", "CSITE"], "controls_populated": 8, "last_sync": "2026-05-24 05:50 UTC", "health": "Healthy", "failed_jobs": 0, "evidence_collected": 520, "sync_note": "Log review use-cases"},
        {"name": "ServiceNow GRC", "applications": ["Net Banking", "Card Platform", "Mobile Banking"], "frameworks_covered": ["PCI DSS", "CSITE"], "controls_populated": 22, "last_sync": "2026-05-24 06:12 UTC", "health": "Healthy", "failed_jobs": 0, "evidence_collected": 142, "sync_note": "Control mapping + exceptions"},
    ],
    reuse=[
        {"source_framework": "PCI DSS", "source_control": "PCI-10.6 SIEM Monitoring", "target_framework": "CSITE", "target_control": "CS-C-05 Log Retention", "shared_evidence": "SIEM Use-Case Export May2026", "confidence_pct": 90, "applications": "Net Banking"},
        {"source_framework": "VAPT", "source_control": "VP-C-01 External Pentest", "target_framework": "PCI DSS", "target_control": "PCI-11.3 External VA", "shared_evidence": "External Pen-Test Report", "confidence_pct": 91, "applications": "Internet Banking"},
    ],
    exceptions=[{"id": "TD-PCI-014", "control_id": "PCI-8.3", "application": "Net Banking", "title": "MFA exception — legacy jump server batch", "justification": "Hardware token incompatible — replacement Q3", "compensating": "Network isolation + session recording", "approver": "QSA + CISO", "expires": "2026-09-30", "status": "Active"}],
    trends={"label": "PCI DSS MFA & privileged access compliance (Feb–May 2026)", "metrics": [
        {"month": "Feb", "mfa_compliance_pct": 88, "priv_access_review_pct": 82, "siem_coverage_pct": 94},
        {"month": "Mar", "mfa_compliance_pct": 90, "priv_access_review_pct": 85, "siem_coverage_pct": 95},
        {"month": "Apr", "mfa_compliance_pct": 92, "priv_access_review_pct": 88, "siem_coverage_pct": 96},
        {"month": "May", "mfa_compliance_pct": 94, "priv_access_review_pct": 91, "siem_coverage_pct": 97},
    ], "metric_labels": ["MFA Compliance %", "Priv Access Review %", "SIEM Coverage %"]},
    pending=[
        {"framework": "PCI DSS", "application": "Card Platform", "control_id": "PCI-7.2", "control_name": "CDE Access Restriction", "finding_id": "PCI-F-001", "owner": "R. Mehta", "action": "Upload updated firewall export and segmentation test results", "due_date": "2026-06-01", "sla_aging_days": 10, "risk": "Critical", "blocker": "Network team CAB approval"},
    ],
    gaps=[{"control_id": "PCI-7.2", "application": "Card Platform", "gap_type": "Failed validation", "finding_id": "PCI-F-001", "owner": "R. Mehta", "risk": "Critical", "description": "CDE segmentation test failed"}],
)

# Add remaining frameworks with unique data (condensed but distinct)
_g("OS Baselining",
    apps=[{"name": "Net Banking", "owner": "R. Mehta", "controls_implemented": 22, "open_findings": 4, "failed_controls": 2, "stale_evidence": 3, "sla_breaches": 1, "audit_readiness_pct": 88.5, "focus": "142 Linux hosts · Tripwire"},
          {"name": "Treasury", "owner": "S. Banerjee", "controls_implemented": 18, "open_findings": 6, "failed_controls": 2, "stale_evidence": 4, "sla_breaches": 2, "audit_readiness_pct": 82.3, "focus": "Windows patch drift"},
          {"name": "Core Banking", "owner": "S. Banerjee", "controls_implemented": 24, "open_findings": 2, "failed_controls": 0, "stale_evidence": 1, "sla_breaches": 0, "audit_readiness_pct": 91.0, "focus": "CIS L2 · CBS cluster"}],
    controls=[{"control_id": "OS-C-01", "control_name": "CIS Benchmark L2 Hardening", "application": "Net Banking", "owner": "R. Mehta", "implementation": "Partial", "evidence_id": "EV-OS-001", "evidence_name": "Tripwire CIS Scan May2026", "validation": "WARN", "workflow": "Pending Review", "sla": "At Risk", "sla_days": 12, "auditor_comment": "89% compliant — 18 hosts drifted", "pending_action": "Remediate drift"},
            {"control_id": "OS-C-02", "control_name": "Critical Patch Within SLA", "application": "Treasury", "owner": "S. Banerjee", "implementation": "Failed", "evidence_id": "EV-OS-002", "evidence_name": "WSUS Patch Report May2026", "validation": "FAIL", "workflow": "Rejected", "sla": "Breached", "sla_days": 14, "auditor_comment": "KB5034441 missing on 4 hosts", "pending_action": "Apply critical patches"}],
    findings=[{"finding_id": "OS-F-001", "application": "Net Banking", "observation": "SSH root login enabled — prod-app-03", "severity": "Critical", "source": "Tripwire Enterprise", "integration": "Tripwire Enterprise", "open_since": "2026-05-12", "linked_control": "OS-C-01", "linked_evidence": "EV-OS-001", "owner": "R. Mehta", "status": "Open", "aging_days": 12, "escalation": "—", "auditor_notes": "CIS 5.2 violation", "closure_dependency": "Hardening scan pass"}],
    evidence=[{"evidence_id": "EV-OS-001", "name": "Tripwire CIS Scan May2026", "application": "Net Banking", "control_id": "OS-C-01", "uploaded_by": "R. Mehta", "type": "Integrity Scan", "lifecycle": "Pending Review", "validation": "Warning", "expiry": "2026-06-30", "audit_cycle": "Q2 2026", "linked_findings": "OS-F-001", "reuse_eligible": False, "source_integration": "Tripwire Enterprise"}],
    integrations=[{"name": "Tripwire Enterprise", "applications": ["Net Banking", "Core Banking", "Treasury"], "frameworks_covered": ["OS Baselining"], "controls_populated": 18, "last_sync": "2026-05-24 05:58 UTC", "health": "Healthy", "failed_jobs": 0, "evidence_collected": 89, "sync_note": "CIS + integrity scans"},
                  {"name": "CrowdStrike Falcon", "applications": ["Net Banking", "Treasury"], "frameworks_covered": ["OS Baselining", "CSITE"], "controls_populated": 10, "last_sync": "2026-05-24 05:40 UTC", "health": "Healthy", "failed_jobs": 0, "evidence_collected": 210, "sync_note": "EDR endpoint evidence"}],
    reuse=[{"source_framework": "OS Baselining", "source_control": "OS-C-01 CIS Hardening", "target_framework": "ITPP", "target_control": "IT-C-05 Patch Governance", "shared_evidence": "Patch compliance matrix", "confidence_pct": 87, "applications": "Net Banking, Core Banking"}],
    exceptions=[{"id": "TD-OS-003", "control_id": "OS-C-01", "application": "Core Banking", "title": "Legacy RHEL 7 host — CBS batch", "justification": "Decommission Q4 2026", "compensating": "Network isolation", "approver": "IT Risk", "expires": "2026-12-31", "status": "Active"}],
    trends={"label": "OS hardening compliance trend (Feb–May 2026)", "metrics": [{"month": "Feb", "cis_compliance_pct": 84, "patch_sla_pct": 78, "drift_hosts": 28}, {"month": "May", "cis_compliance_pct": 89, "patch_sla_pct": 86, "drift_hosts": 18}], "metric_labels": ["CIS Compliance %", "Patch SLA %", "Drifted Hosts"]},
    pending=[{"framework": "OS Baselining", "application": "Treasury", "control_id": "OS-C-02", "control_name": "Critical Patch Within SLA", "finding_id": "—", "owner": "S. Banerjee", "action": "Apply KB5034441 to 4 Windows hosts in Treasury zone", "due_date": "2026-05-27", "sla_aging_days": 14, "risk": "High", "blocker": "Maintenance window approval"}],
    gaps=[{"control_id": "OS-C-02", "application": "Treasury", "gap_type": "Failed validation", "finding_id": "—", "owner": "S. Banerjee", "risk": "High", "description": "Critical patch KB5034441 missing"}],
)

_g("DB Baselining",
    apps=[{"name": "Oracle Core DB", "owner": "S. Banerjee", "controls_implemented": 12, "open_findings": 2, "failed_controls": 1, "stale_evidence": 1, "sla_breaches": 0, "audit_readiness_pct": 87.4, "focus": "TDE · unified audit"},
          {"name": "Payments DB", "owner": "K. Iyer", "controls_implemented": 10, "open_findings": 3, "failed_controls": 2, "stale_evidence": 2, "sla_breaches": 1, "audit_readiness_pct": 79.6, "focus": "Encryption gap · backup"}],
    controls=[{"control_id": "DB-C-01", "control_name": "TDE Encryption at Rest", "application": "Payments DB", "owner": "K. Iyer", "implementation": "Failed", "evidence_id": "EV-DB-001", "evidence_name": "TDE Attestation Payments DB", "validation": "FAIL", "workflow": "Rejected", "sla": "Breached", "sla_days": 18, "auditor_comment": "Legacy token column unencrypted", "pending_action": "Enable TDE on legacy schema"}],
    findings=[{"finding_id": "DB-F-001", "application": "Payments DB", "observation": "Unencrypted payment_token column in legacy schema", "severity": "Critical", "source": "DB Audit Tool", "integration": "Oracle Enterprise Manager", "open_since": "2026-04-18", "linked_control": "DB-C-01", "linked_evidence": "EV-DB-001", "owner": "K. Iyer", "status": "Open", "aging_days": 36, "escalation": "DBA Lead", "auditor_notes": "PCI scope impact", "closure_dependency": "TDE migration complete"}],
    evidence=[{"evidence_id": "EV-DB-001", "name": "TDE Attestation Payments DB", "application": "Payments DB", "control_id": "DB-C-01", "uploaded_by": "K. Iyer", "type": "TDE Report", "lifecycle": "Rejected", "validation": "Failed", "expiry": "2026-06-30", "audit_cycle": "Q2 2026", "linked_findings": "DB-F-001", "reuse_eligible": False, "source_integration": "Oracle Enterprise Manager"}],
    integrations=[{"name": "Oracle Enterprise Manager", "applications": ["Oracle Core DB", "Payments DB", "CBS Oracle"], "frameworks_covered": ["DB Baselining"], "controls_populated": 14, "last_sync": "2026-05-24 06:08 UTC", "health": "Healthy", "failed_jobs": 0, "evidence_collected": 67, "sync_note": "TDE + audit trail exports"}],
    reuse=[{"source_framework": "DB Baselining", "source_control": "DB-C-01 TDE Encryption", "target_framework": "PCI DSS", "target_control": "Req 3.4 Encryption at Rest", "shared_evidence": "TDE Attestation Report", "confidence_pct": 95, "applications": "Payments DB, Oracle Core DB"}],
    exceptions=[{"id": "TD-DB-007", "control_id": "DB-C-01", "application": "Payments DB", "title": "TDE migration deferral — UAT clone", "justification": "Migration window Jun 2026", "compensating": "Column-level masking in UAT", "approver": "CISO", "expires": "2026-06-30", "status": "Active"}],
    trends={"label": "DB encryption & audit logging trend (Feb–May 2026)", "metrics": [{"month": "Feb", "tde_coverage_pct": 82, "audit_logging_pct": 88}, {"month": "May", "tde_coverage_pct": 91, "audit_logging_pct": 94}], "metric_labels": ["TDE Coverage %", "Audit Logging %"]},
    pending=[{"framework": "DB Baselining", "application": "Payments DB", "control_id": "DB-C-01", "control_name": "TDE Encryption at Rest", "finding_id": "DB-F-001", "owner": "K. Iyer", "action": "Complete TDE migration for legacy payment_token schema", "due_date": "2026-06-15", "sla_aging_days": 18, "risk": "Critical", "blocker": "DBA migration window"}],
    gaps=[{"control_id": "DB-C-01", "application": "Payments DB", "gap_type": "Failed validation", "finding_id": "DB-F-001", "owner": "K. Iyer", "risk": "Critical", "description": "Unencrypted legacy column"}],
)

_g("Nginx Baselining",
    apps=[{"name": "UPI Gateway", "owner": "P. Nair", "controls_implemented": 8, "open_findings": 2, "failed_controls": 0, "stale_evidence": 0, "sla_breaches": 0, "audit_readiness_pct": 90.2, "focus": "TLS 1.3 · HSTS"},
          {"name": "Mobile Banking Edge", "owner": "A. Sharma", "controls_implemented": 7, "open_findings": 3, "failed_controls": 1, "stale_evidence": 1, "sla_breaches": 1, "audit_readiness_pct": 81.5, "focus": "Cert expiry · WAF gap"}],
    controls=[{"control_id": "NGX-C-01", "control_name": "TLS 1.2+ Enforcement", "application": "UPI Gateway", "owner": "P. Nair", "implementation": "Implemented", "evidence_id": "EV-NGX-001", "evidence_name": "Nginx TLS Config Export", "validation": "PASS", "workflow": "Approved", "sla": "OK", "sla_days": 0, "auditor_comment": "TLS 1.3 enforced", "pending_action": "—"},
            {"control_id": "NGX-C-04", "control_name": "Certificate Lifecycle", "application": "Mobile Banking Edge", "owner": "A. Sharma", "implementation": "Failed", "evidence_id": "EV-NGX-002", "evidence_name": "Cert Inventory May2026", "validation": "FAIL", "workflow": "Rejected", "sla": "Breached", "sla_days": 5, "auditor_comment": "mobile.api.bank.in expires in 12 days", "pending_action": "Renew certificate"}],
    findings=[{"finding_id": "NGX-F-001", "application": "Mobile Banking Edge", "observation": "SSL cert expires in 12 days — mobile.api.bank.in", "severity": "High", "source": "Cert Monitor", "integration": "Venafi", "open_since": "2026-05-18", "linked_control": "NGX-C-04", "linked_evidence": "EV-NGX-002", "owner": "A. Sharma", "status": "Renewal Scheduled", "aging_days": 6, "escalation": "—", "auditor_notes": "Auto-renewal failed", "closure_dependency": "New cert deployed"}],
    evidence=[{"evidence_id": "EV-NGX-002", "name": "Cert Inventory May2026", "application": "Mobile Banking Edge", "control_id": "NGX-C-04", "uploaded_by": "A. Sharma", "type": "Certificate Report", "lifecycle": "Rejected", "validation": "Failed", "expiry": "2026-06-05", "audit_cycle": "Q2 2026", "linked_findings": "NGX-F-001", "reuse_eligible": False, "source_integration": "Venafi"}],
    integrations=[{"name": "Venafi", "applications": ["UPI Gateway", "Mobile Banking Edge", "API Gateway"], "frameworks_covered": ["Nginx Baselining"], "controls_populated": 6, "last_sync": "2026-05-24 05:35 UTC", "health": "Healthy", "failed_jobs": 0, "evidence_collected": 34, "sync_note": "Certificate lifecycle management"},
                  {"name": "F5 WAF", "applications": ["UPI Gateway", "Mobile Banking Edge"], "frameworks_covered": ["Nginx Baselining", "VAPT"], "controls_populated": 5, "last_sync": "2026-05-24 04:00 UTC", "health": "Degraded", "failed_jobs": 1, "evidence_collected": 24, "sync_note": "Edge WAF rules"}],
    reuse=[{"source_framework": "Nginx Baselining", "source_control": "NGX-C-01 TLS Enforcement", "target_framework": "PCI DSS", "target_control": "Req 4.1 Encryption in Transit", "shared_evidence": "TLS cipher suite inventory", "confidence_pct": 93, "applications": "UPI Gateway"}],
    exceptions=[], trends={"label": "TLS posture & cert expiry trend (Feb–May 2026)", "metrics": [{"month": "Feb", "tls_compliance_pct": 86, "expired_certs": 3}, {"month": "May", "tls_compliance_pct": 92, "expired_certs": 1}], "metric_labels": ["TLS Compliance %", "Expiring Certs"]},
    pending=[{"framework": "Nginx Baselining", "application": "Mobile Banking Edge", "control_id": "NGX-C-04", "control_name": "Certificate Lifecycle", "finding_id": "NGX-F-001", "owner": "A. Sharma", "action": "Renew mobile.api.bank.in certificate before Jun 5 expiry", "due_date": "2026-06-03", "sla_aging_days": 5, "risk": "High", "blocker": "Venafi auto-renew failed"}],
    gaps=[{"control_id": "NGX-C-04", "application": "Mobile Banking Edge", "gap_type": "Failed validation", "finding_id": "NGX-F-001", "owner": "A. Sharma", "risk": "High", "description": "Certificate expiring in 12 days"}],
)

_g("CSITE",
    apps=[{"name": "Retail Banking", "owner": "R. Mehta", "controls_implemented": 14, "open_findings": 4, "failed_controls": 1, "stale_evidence": 1, "sla_breaches": 1, "audit_readiness_pct": 88.0, "focus": "Access review · audit aging"},
          {"name": "Payments", "owner": "K. Iyer", "controls_implemented": 12, "open_findings": 5, "failed_controls": 2, "stale_evidence": 2, "sla_breaches": 2, "audit_readiness_pct": 82.1, "focus": "Repeat observation · log retention"}],
    controls=[{"control_id": "CS-C-03", "control_name": "Access Review Certification", "application": "Retail Banking", "owner": "R. Mehta", "implementation": "Failed", "evidence_id": "EV-CS-001", "evidence_name": "Q1 Access Review Sign-off", "validation": "FAIL", "workflow": "Rejected", "sla": "Breached", "sla_days": 32, "auditor_comment": "32 days overdue", "pending_action": "Complete access review"}],
    findings=[{"finding_id": "CS-F-001", "application": "Retail Banking", "observation": "Quarterly access review incomplete — 32 days overdue", "severity": "High", "source": "Internal Audit", "integration": "ServiceNow GRC", "open_since": "2026-04-22", "linked_control": "CS-C-03", "linked_evidence": "EV-CS-001", "owner": "R. Mehta", "status": "Open", "aging_days": 32, "escalation": "Audit Committee", "auditor_notes": "Repeat from Q4 2025", "closure_dependency": "Signed certification"}],
    evidence=[{"evidence_id": "EV-CS-001", "name": "Q1 Access Review Sign-off", "application": "Retail Banking", "control_id": "CS-C-03", "uploaded_by": "R. Mehta", "type": "Access Review", "lifecycle": "Rejected", "validation": "Failed", "expiry": "2026-03-31", "audit_cycle": "Q1 2026", "linked_findings": "CS-F-001", "reuse_eligible": False, "source_integration": "ServiceNow GRC"}],
    integrations=[{"name": "ServiceNow GRC", "applications": ["Retail Banking", "Payments", "Treasury"], "frameworks_covered": ["CSITE", "PCI DSS"], "controls_populated": 18, "last_sync": "2026-05-24 06:12 UTC", "health": "Healthy", "failed_jobs": 0, "evidence_collected": 98, "sync_note": "Observation tracking + closure workflow"}],
    reuse=[{"source_framework": "CSITE", "source_control": "CS-C-03 Access Review", "target_framework": "PCI DSS", "target_control": "PCI-8.3 MFA/Privileged Access", "shared_evidence": "Access review certification", "confidence_pct": 88, "applications": "Retail Banking"}],
    exceptions=[{"id": "TD-CS-008", "control_id": "CS-C-03", "application": "Payments", "title": "Observation closure extension", "justification": "Resource constraint — audit window", "compensating": "Interim manager attestation", "approver": "Audit Head", "expires": "2026-06-30", "status": "Active"}],
    trends={"label": "CSITE observation closure trend (Feb–May 2026)", "metrics": [{"month": "Feb", "closure_pct": 72, "open_observations": 28}, {"month": "May", "closure_pct": 84, "open_observations": 18}], "metric_labels": ["Closure %", "Open Observations"]},
    pending=[{"framework": "CSITE", "application": "Retail Banking", "control_id": "CS-C-03", "control_name": "Access Review Certification", "finding_id": "CS-F-001", "owner": "R. Mehta", "action": "Complete Q1 access review and upload signed certification", "due_date": "2026-05-30", "sla_aging_days": 32, "risk": "High", "blocker": "Manager sign-offs pending"}],
    gaps=[{"control_id": "CS-C-03", "application": "Retail Banking", "gap_type": "Failed validation", "finding_id": "CS-F-001", "owner": "R. Mehta", "risk": "High", "description": "Access review 32 days overdue"}],
)

_g("DPSC",
    apps=[{"name": "Mobile Banking", "owner": "A. Sharma", "controls_implemented": 11, "open_findings": 2, "failed_controls": 1, "stale_evidence": 1, "sla_breaches": 0, "audit_readiness_pct": 86.5, "focus": "Consent logs · PII masking"},
          {"name": "Payments", "owner": "K. Iyer", "controls_implemented": 13, "open_findings": 3, "failed_controls": 1, "stale_evidence": 2, "sla_breaches": 1, "audit_readiness_pct": 83.8, "focus": "Retention violation · archive"}],
    controls=[{"control_id": "DP-C-04", "control_name": "Consent Management", "application": "Mobile Banking", "owner": "A. Sharma", "implementation": "Partial", "evidence_id": "EV-DP-001", "evidence_name": "Consent Log Export v3.2", "validation": "WARN", "workflow": "Pending Review", "sla": "At Risk", "sla_days": 21, "auditor_comment": "Onboarding flow gap", "pending_action": "Fix consent capture"}],
    findings=[{"finding_id": "DP-F-001", "application": "Mobile Banking", "observation": "Consent log gap — onboarding flow v3.2", "severity": "High", "source": "Privacy Audit", "integration": "OneTrust", "open_since": "2026-05-01", "linked_control": "DP-C-04", "linked_evidence": "EV-DP-001", "owner": "A. Sharma", "status": "Open", "aging_days": 23, "escalation": "DPO", "auditor_notes": "RBI DPSC alignment", "closure_dependency": "Consent API fix deployed"}],
    evidence=[{"evidence_id": "EV-DP-001", "name": "Consent Log Export v3.2", "application": "Mobile Banking", "control_id": "DP-C-04", "uploaded_by": "A. Sharma", "type": "Consent Log", "lifecycle": "Pending Review", "validation": "Warning", "expiry": "2026-07-31", "audit_cycle": "Q2 2026", "linked_findings": "DP-F-001", "reuse_eligible": False, "source_integration": "OneTrust"}],
    integrations=[{"name": "OneTrust", "applications": ["Mobile Banking", "Payments", "CRM"], "frameworks_covered": ["DPSC"], "controls_populated": 10, "last_sync": "2026-05-24 05:55 UTC", "health": "Healthy", "failed_jobs": 0, "evidence_collected": 56, "sync_note": "Consent + retention tracking"}],
    reuse=[{"source_framework": "DPSC", "source_control": "DP-C-04 Consent Management", "target_framework": "PCI DSS", "target_control": "Req 3.1 Data Retention", "shared_evidence": "Data retention policy attestation", "confidence_pct": 86, "applications": "Mobile Banking"}],
    exceptions=[{"id": "TD-DP-006", "control_id": "DP-C-04", "application": "Mobile Banking", "title": "Consent refresh deferral", "justification": "App release blocked — API change", "compensating": "Manual consent capture interim", "approver": "DPO", "expires": "2026-07-31", "status": "Active"}],
    trends={"label": "DPSC privacy compliance trend (Feb–May 2026)", "metrics": [{"month": "Feb", "consent_compliance_pct": 84, "retention_violations": 5}, {"month": "May", "consent_compliance_pct": 91, "retention_violations": 2}], "metric_labels": ["Consent Compliance %", "Retention Violations"]},
    pending=[{"framework": "DPSC", "application": "Mobile Banking", "control_id": "DP-C-04", "control_name": "Consent Management", "finding_id": "DP-F-001", "owner": "A. Sharma", "action": "Deploy consent API fix for onboarding v3.2 and upload new consent logs", "due_date": "2026-06-05", "sla_aging_days": 21, "risk": "High", "blocker": "Mobile release pipeline"}],
    gaps=[{"control_id": "DP-C-04", "application": "Mobile Banking", "gap_type": "Missing evidence", "finding_id": "DP-F-001", "owner": "A. Sharma", "risk": "High", "description": "Consent log gap in onboarding v3.2"}],
)

_g("ITPP",
    apps=[{"name": "Net Banking", "owner": "R. Mehta", "controls_implemented": 16, "open_findings": 2, "failed_controls": 1, "stale_evidence": 1, "sla_breaches": 1, "audit_readiness_pct": 92.5, "focus": "DR drill · CAB"},
          {"name": "CBS Oracle", "owner": "S. Banerjee", "controls_implemented": 14, "open_findings": 2, "failed_controls": 1, "stale_evidence": 1, "sla_breaches": 1, "audit_readiness_pct": 88.7, "focus": "Backup validation · restore test"}],
    controls=[{"control_id": "IT-C-03", "control_name": "Restore Test Validated", "application": "CBS Oracle", "owner": "S. Banerjee", "implementation": "Failed", "evidence_id": "EV-IT-001", "evidence_name": "Q1 Restore Test Report", "validation": "FAIL", "workflow": "Rejected", "sla": "Breached", "sla_days": 45, "auditor_comment": "Quarterly restore test overdue", "pending_action": "Execute restore test"},
            {"control_id": "IT-C-08", "control_name": "CAB Approval for Prod Changes", "application": "Net Banking", "owner": "R. Mehta", "implementation": "Partial", "evidence_id": "EV-IT-002", "evidence_name": "Emergency Change PIR CHG-8842", "validation": "WARN", "workflow": "Pending Review", "sla": "At Risk", "sla_days": 5, "auditor_comment": "PIR pending 5 days", "pending_action": "Submit PIR"}],
    findings=[{"finding_id": "IT-F-001", "application": "Net Banking", "observation": "Emergency change PIR pending 5 days — CHG-8842", "severity": "High", "source": "Change Audit", "integration": "ServiceNow ITSM", "open_since": "2026-05-19", "linked_control": "IT-C-08", "linked_evidence": "EV-IT-002", "owner": "R. Mehta", "status": "Open", "aging_days": 5, "escalation": "—", "auditor_notes": "ITPP change management", "closure_dependency": "PIR approved"}],
    evidence=[{"evidence_id": "EV-IT-002", "name": "Emergency Change PIR CHG-8842", "application": "Net Banking", "control_id": "IT-C-08", "uploaded_by": "R. Mehta", "type": "Change Record", "lifecycle": "Pending Review", "validation": "Warning", "expiry": "2026-06-30", "audit_cycle": "Q2 2026", "linked_findings": "IT-F-001", "reuse_eligible": False, "source_integration": "ServiceNow ITSM"}],
    integrations=[{"name": "ServiceNow ITSM", "applications": ["Net Banking", "CBS Oracle", "UPI Switch"], "frameworks_covered": ["ITPP"], "controls_populated": 20, "last_sync": "2026-05-24 06:15 UTC", "health": "Healthy", "failed_jobs": 0, "evidence_collected": 112, "sync_note": "Change · incident · DR evidence"},
                  {"name": "Veeam Backup", "applications": ["CBS Oracle", "Net Banking"], "frameworks_covered": ["ITPP"], "controls_populated": 8, "last_sync": "2026-05-24 04:30 UTC", "health": "Healthy", "failed_jobs": 0, "evidence_collected": 45, "sync_note": "Backup + restore validation"}],
    reuse=[{"source_framework": "ITPP", "source_control": "IT-C-03 Restore Test", "target_framework": "DB Baselining", "target_control": "DB-C-02 Backup Validation", "shared_evidence": "Restore test report", "confidence_pct": 90, "applications": "CBS Oracle"}],
    exceptions=[{"id": "TD-IT-004", "control_id": "IT-C-08", "application": "Net Banking", "title": "Emergency change PIR extension", "justification": "Incident response priority", "compensating": "Verbal CAB approval documented", "approver": "IT Director", "expires": "2026-06-15", "status": "Active"}],
    trends={"label": "ITPP DR & change success trend (Feb–May 2026)", "metrics": [{"month": "Feb", "dr_success_pct": 92, "change_success_pct": 96}, {"month": "May", "dr_success_pct": 96, "change_success_pct": 98}], "metric_labels": ["DR Success %", "Change Success %"]},
    pending=[{"framework": "ITPP", "application": "CBS Oracle", "control_id": "IT-C-03", "control_name": "Restore Test Validated", "finding_id": "—", "owner": "S. Banerjee", "action": "Execute and document quarterly restore test for CBS Oracle", "due_date": "2026-06-10", "sla_aging_days": 45, "risk": "High", "blocker": "DBA availability"}],
    gaps=[{"control_id": "IT-C-03", "application": "CBS Oracle", "gap_type": "Stale evidence", "finding_id": "—", "owner": "S. Banerjee", "risk": "High", "description": "Restore test overdue 45 days"}],
)


def get_framework_graph(framework_name: str) -> dict[str, Any]:
    from modules.frameworks.engines.framework_catalog import resolve_framework_name
    fw = resolve_framework_name(framework_name)
    return FRAMEWORK_GRAPHS.get(fw, {
        "applications": [], "controls": [], "findings": [], "evidence": [],
        "integrations": [], "reuse_mappings": [], "exceptions": [],
        "trends": {"label": framework_name, "metrics": [], "metric_labels": []},
        "pending_actions": [], "open_gaps": [],
    })


def build_relational_view(framework_name: str) -> dict[str, Any]:
    """Full relational view for framework drill-down tabs."""
    from modules.governance.engines.governance_data_enrichment import enrich_framework_graph

    g = enrich_framework_graph(framework_name, get_framework_graph(framework_name))
    apps = g["applications"]
    findings = g["findings"]
    failed = [
        {
            "control_id": c["control_id"],
            "control_name": c["control_name"],
            "framework": framework_name,
            "application": c["application"],
            "failure_reason": c.get("auditor_comment", c.get("pending_action", "Validation failed")),
            "evidence_missing": c.get("evidence_name", "—"),
            "sla_status": c.get("sla", "At Risk"),
            "last_validation": "2026-05-22",
            "risk_severity": "Critical" if c.get("validation") == "FAIL" else "High",
            "owner": c.get("owner", _owner(c["application"])),
        }
        for c in g["controls"] if c.get("validation") == "FAIL"
    ]
    weighted = round(sum(a.get("audit_readiness_pct", 0) for a in apps) / max(len(apps), 1), 1)
    return {
        **g,
        "failed_controls": failed,
        "open_findings": findings,
        "audit_readiness": {
            "label": f"{framework_name} audit readiness across {len(apps)} applications",
            "weighted_pct": weighted,
            "by_application": [{"application": a["name"], "pct": a["audit_readiness_pct"], "owner": a.get("owner", _owner(a["name"]))} for a in apps],
        },
        "risk_contributors": [
            {"application": a["name"], "owner": a.get("owner"), "findings": a["open_findings"], "failed_controls": a["failed_controls"],
             "sla_breaches": a["sla_breaches"], "stale_evidence": a["stale_evidence"], "compliance_pct": a["audit_readiness_pct"],
             "controls_implemented": a["controls_implemented"]}
            for a in apps
        ],
    }
