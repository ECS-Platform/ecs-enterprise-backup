"""Framework-specific governance datasets — each framework has unique applications, KPIs, trends, and drill-downs."""

from __future__ import annotations

import hashlib
from typing import Any


def _seed(seed: str, lo: int, hi: int) -> int:
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return lo + (h % (hi - lo + 1))


FRAMEWORK_PROFILES: dict[str, dict[str, Any]] = {
    "PCI DSS": {
        "framework_name": "PCI DSS",
        "framework_description": "Payment Card Industry Data Security Standard — CDE segmentation, encryption, MFA, firewall, SIEM, and privileged access for cardholder data environments.",
        "context_label": "PCI DSS posture across 4 onboarded payment-channel applications",
        "applications": [
            {"name": "Net Banking", "compliance_pct": 86.2, "findings": 3, "stale_evidences": 2, "pending_approvals": 4, "auditor_queue": 2, "last_validation": "2026-05-22", "risk_rating": "Medium", "focus": "CDE firewall · MFA · encryption"},
            {"name": "UPI", "compliance_pct": 91.4, "findings": 1, "stale_evidences": 1, "pending_approvals": 2, "auditor_queue": 1, "last_validation": "2026-05-23", "risk_rating": "Low", "focus": "Tokenization · HSM"},
            {"name": "Card Payments", "compliance_pct": 78.9, "findings": 5, "stale_evidences": 3, "pending_approvals": 6, "auditor_queue": 4, "last_validation": "2026-05-20", "risk_rating": "High", "focus": "Segmentation gap · VAPT"},
            {"name": "Mobile Banking", "compliance_pct": 84.1, "findings": 2, "stale_evidences": 2, "pending_approvals": 3, "auditor_queue": 2, "last_validation": "2026-05-21", "risk_rating": "Medium", "focus": "MFA · secure channel"},
        ],
        "trends": [
            {"month": "Feb", "compliance": 79, "evidence_health": 82, "audit_queue": 14},
            {"month": "Mar", "compliance": 81, "evidence_health": 84, "audit_queue": 12},
            {"month": "Apr", "compliance": 83, "evidence_health": 86, "audit_queue": 10},
            {"month": "May", "compliance": 85, "evidence_health": 88, "audit_queue": 9},
        ],
        "integrations": ["SharePoint Evidence Library", "ServiceNow GRC", "Splunk SIEM", "Prisma Cloud"],
        "exceptions": [
            {"id": "TD-PCI-014", "title": "MFA exception — jump server batch", "expires": "Q3 2026", "status": "Active"},
            {"id": "TD-PCI-009", "title": "TLS 1.2 legacy terminal — Treasury link", "expires": "Q2 2026", "status": "Review Due"},
        ],
    },
    "OS Baselining": {
        "framework_name": "OS Baselining",
        "framework_description": "CIS benchmark hardening for Linux and Windows hosts — patch compliance, root access, password policy, and unauthorized package detection.",
        "context_label": "OS Baselining drift across Linux and Windows production hosts",
        "applications": [
            {"name": "Net Banking", "compliance_pct": 88.5, "findings": 6, "stale_evidences": 4, "pending_approvals": 5, "auditor_queue": 3, "last_validation": "2026-05-23", "risk_rating": "Medium", "focus": "142 Linux hosts · CIS L2"},
            {"name": "Treasury", "compliance_pct": 82.3, "findings": 9, "stale_evidences": 5, "pending_approvals": 7, "auditor_queue": 4, "last_validation": "2026-05-21", "risk_rating": "High", "focus": "Windows hardening · patch drift"},
            {"name": "Core Banking", "compliance_pct": 91.0, "findings": 3, "stale_evidences": 2, "pending_approvals": 2, "auditor_queue": 1, "last_validation": "2026-05-24", "risk_rating": "Low", "focus": "CBS cluster · Tripwire"},
        ],
        "trends": [
            {"month": "Feb", "compliance": 84, "drift_pct": 12, "non_compliant_hosts": 28},
            {"month": "Mar", "compliance": 86, "drift_pct": 10, "non_compliant_hosts": 24},
            {"month": "Apr", "compliance": 87, "drift_pct": 9, "non_compliant_hosts": 21},
            {"month": "May", "compliance": 89, "drift_pct": 7, "non_compliant_hosts": 18},
        ],
        "integrations": ["Tripwire Enterprise", "ServiceNow CMDB", "SharePoint"],
        "exceptions": [
            {"id": "TD-OS-003", "title": "Legacy RHEL 7 host — CBS batch node", "expires": "Q4 2026", "status": "Active"},
        ],
    },
    "DB Baselining": {
        "framework_name": "DB Baselining",
        "framework_description": "Database security baselining — TDE, audit logging, privileged access, backup validation, and configuration drift for Oracle, MSSQL, and MySQL.",
        "context_label": "DB Baselining posture across Oracle, Payments, and Treasury databases",
        "applications": [
            {"name": "Oracle Core DB", "compliance_pct": 87.4, "findings": 4, "stale_evidences": 2, "pending_approvals": 3, "auditor_queue": 2, "last_validation": "2026-05-22", "risk_rating": "Medium", "focus": "TDE · unified audit"},
            {"name": "Payments DB", "compliance_pct": 79.6, "findings": 6, "stale_evidences": 3, "pending_approvals": 5, "auditor_queue": 3, "last_validation": "2026-05-20", "risk_rating": "High", "focus": "Backup failure · weak service account"},
            {"name": "Treasury DB", "compliance_pct": 92.1, "findings": 1, "stale_evidences": 1, "pending_approvals": 1, "auditor_queue": 1, "last_validation": "2026-05-23", "risk_rating": "Low", "focus": "Archive retention · encryption"},
        ],
        "trends": [
            {"month": "Feb", "compliance": 80, "unencrypted": 3, "backup_failures": 2},
            {"month": "Mar", "compliance": 83, "unencrypted": 2, "backup_failures": 2},
            {"month": "Apr", "compliance": 85, "unencrypted": 2, "backup_failures": 1},
            {"month": "May", "compliance": 87, "unencrypted": 1, "backup_failures": 1},
        ],
        "integrations": ["Tripwire Enterprise", "ServiceNow CMDB", "Prisma Cloud"],
        "exceptions": [
            {"id": "TD-DB-007", "title": "Audit logging deferred — UAT Oracle clone", "expires": "Q2 2026", "status": "Active"},
        ],
    },
    "Nginx Baselining": {
        "framework_name": "Nginx Baselining",
        "framework_description": "Edge and reverse-proxy hardening — TLS compliance, certificate lifecycle, HTTP security headers, DMZ exposure, and WAF integration.",
        "context_label": "Nginx Baselining TLS and edge posture for internet-facing gateways",
        "applications": [
            {"name": "UPI Gateway", "compliance_pct": 90.2, "findings": 2, "stale_evidences": 1, "pending_approvals": 2, "auditor_queue": 1, "last_validation": "2026-05-23", "risk_rating": "Low", "focus": "TLS 1.3 · HSTS"},
            {"name": "API Gateway", "compliance_pct": 84.7, "findings": 4, "stale_evidences": 2, "pending_approvals": 3, "auditor_queue": 2, "last_validation": "2026-05-21", "risk_rating": "Medium", "focus": "Weak cipher · cert expiry"},
            {"name": "Mobile Banking Edge", "compliance_pct": 81.5, "findings": 5, "stale_evidences": 3, "pending_approvals": 4, "auditor_queue": 3, "last_validation": "2026-05-19", "risk_rating": "High", "focus": "DMZ exposure · WAF gap"},
        ],
        "trends": [
            {"month": "Feb", "compliance": 82, "expired_certs": 4, "weak_cipher": 6},
            {"month": "Mar", "compliance": 84, "expired_certs": 3, "weak_cipher": 5},
            {"month": "Apr", "compliance": 86, "expired_certs": 2, "weak_cipher": 4},
            {"month": "May", "compliance": 88, "expired_certs": 2, "weak_cipher": 3},
        ],
        "integrations": ["SharePoint", "Prisma Cloud", "Splunk SIEM"],
        "exceptions": [
            {"id": "TD-NGX-002", "title": "Legacy TLS 1.0 — partner API endpoint", "expires": "Q3 2026", "status": "Active"},
        ],
    },
    "AppSec": {
        "framework_name": "AppSec",
        "framework_description": "Application security — SAST, DAST, SCA, secrets exposure, secure SDLC gates, and build pipeline validation.",
        "context_label": "AppSec findings and SDLC posture across tier-1 application portfolios",
        "applications": [
            {"name": "Mobile Banking", "compliance_pct": 76.8, "findings": 14, "stale_evidences": 3, "pending_approvals": 8, "auditor_queue": 5, "last_validation": "2026-05-22", "risk_rating": "High", "focus": "SAST gate · 8 critical CVEs"},
            {"name": "Loan System", "compliance_pct": 71.2, "findings": 18, "stale_evidences": 4, "pending_approvals": 10, "auditor_queue": 6, "last_validation": "2026-05-20", "risk_rating": "High", "focus": "SonarQube · secrets exposure"},
            {"name": "Wealth Portal", "compliance_pct": 83.5, "findings": 7, "stale_evidences": 2, "pending_approvals": 4, "auditor_queue": 3, "last_validation": "2026-05-23", "risk_rating": "Medium", "focus": "DAST · dependency risk"},
        ],
        "trends": [
            {"month": "Feb", "compliance": 72, "critical_cves": 22, "secure_build_pct": 78},
            {"month": "Mar", "compliance": 74, "critical_cves": 19, "secure_build_pct": 80},
            {"month": "Apr", "compliance": 77, "critical_cves": 16, "secure_build_pct": 83},
            {"month": "May", "compliance": 79, "critical_cves": 14, "secure_build_pct": 86},
        ],
        "integrations": ["SonarQube Enterprise", "Checkmarx SAST", "Jira Security Remediation"],
        "exceptions": [
            {"id": "TD-AS-011", "title": "SAST gate waiver — legacy COBOL module", "expires": "Q4 2026", "status": "Active"},
        ],
    },
    "VAPT": {
        "framework_name": "VAPT",
        "framework_description": "Vulnerability assessment and penetration testing — exploitable findings, retest status, internet exposure, and patch remediation aging.",
        "context_label": "VAPT findings for internet-facing banking applications",
        "applications": [
            {"name": "UPI", "compliance_pct": 74.5, "findings": 11, "stale_evidences": 2, "pending_approvals": 6, "auditor_queue": 4, "last_validation": "2026-05-21", "risk_rating": "High", "focus": "3 exploitable · retest pending"},
            {"name": "Net Banking", "compliance_pct": 80.2, "findings": 8, "stale_evidences": 2, "pending_approvals": 5, "auditor_queue": 3, "last_validation": "2026-05-22", "risk_rating": "Medium", "focus": "Auth bypass closed · SSRF open"},
            {"name": "Internet Banking", "compliance_pct": 77.8, "findings": 10, "stale_evidences": 3, "pending_approvals": 6, "auditor_queue": 4, "last_validation": "2026-05-20", "risk_rating": "High", "focus": "External pen-test Mar 2026"},
        ],
        "trends": [
            {"month": "Feb", "compliance": 70, "critical_vulns": 9, "retest_pending": 6},
            {"month": "Mar", "compliance": 73, "critical_vulns": 8, "retest_pending": 5},
            {"month": "Apr", "compliance": 76, "critical_vulns": 6, "retest_pending": 4},
            {"month": "May", "compliance": 78, "critical_vulns": 5, "retest_pending": 3},
        ],
        "integrations": ["Jira Security Remediation", "SharePoint", "ServiceNow GRC"],
        "exceptions": [
            {"id": "TD-VAPT-005", "title": "Patch deferral — payment gateway SSRF", "expires": "Q2 2026", "status": "Review Due"},
        ],
    },
    "CSITE": {
        "framework_name": "CSITE",
        "framework_description": "Internal audit observations — closure workflow, remediation tracking, observation aging, auditor comments, and evidence closure status.",
        "context_label": "CSITE internal audit observations and closure workflow across business units",
        "applications": [
            {"name": "Retail Banking", "compliance_pct": 88.0, "findings": 6, "stale_evidences": 2, "pending_approvals": 4, "auditor_queue": 3, "last_validation": "2026-05-22", "risk_rating": "Medium", "focus": "12 open observations"},
            {"name": "Treasury", "compliance_pct": 85.4, "findings": 4, "stale_evidences": 1, "pending_approvals": 3, "auditor_queue": 2, "last_validation": "2026-05-23", "risk_rating": "Medium", "focus": "Repeat observation — access review"},
            {"name": "Payments", "compliance_pct": 82.1, "findings": 8, "stale_evidences": 3, "pending_approvals": 5, "auditor_queue": 4, "last_validation": "2026-05-21", "risk_rating": "High", "focus": "Audit aging > 45 days"},
        ],
        "trends": [
            {"month": "Feb", "compliance": 80, "open_observations": 28, "closure_pct": 72},
            {"month": "Mar", "compliance": 82, "open_observations": 24, "closure_pct": 76},
            {"month": "Apr", "compliance": 84, "open_observations": 20, "closure_pct": 80},
            {"month": "May", "compliance": 86, "open_observations": 18, "closure_pct": 84},
        ],
        "integrations": ["ServiceNow GRC", "SharePoint Evidence Library", "Microsoft Teams Governance"],
        "exceptions": [
            {"id": "TD-CSITE-008", "title": "Observation closure extension — Payments unit", "expires": "Q2 2026", "status": "Active"},
        ],
    },
    "DPSC": {
        "framework_name": "DPSC",
        "framework_description": "Data privacy and sensitive customer data protection — consent management, PII exposure, retention compliance, and regulatory breach tracking.",
        "context_label": "DPSC data privacy posture across customer-facing channels",
        "applications": [
            {"name": "Net Banking", "compliance_pct": 89.2, "findings": 2, "stale_evidences": 1, "pending_approvals": 2, "auditor_queue": 1, "last_validation": "2026-05-23", "risk_rating": "Low", "focus": "Consent logs · masking"},
            {"name": "Mobile Banking", "compliance_pct": 86.5, "findings": 3, "stale_evidences": 2, "pending_approvals": 3, "auditor_queue": 2, "last_validation": "2026-05-22", "risk_rating": "Medium", "focus": "PII retention gap"},
            {"name": "UPI", "compliance_pct": 91.0, "findings": 1, "stale_evidences": 0, "pending_approvals": 1, "auditor_queue": 1, "last_validation": "2026-05-24", "risk_rating": "Low", "focus": "Tokenization · consent refresh"},
            {"name": "Payments", "compliance_pct": 83.8, "findings": 4, "stale_evidences": 2, "pending_approvals": 3, "auditor_queue": 2, "last_validation": "2026-05-21", "risk_rating": "Medium", "focus": "Retention violation · archive"},
        ],
        "trends": [
            {"month": "Feb", "compliance": 84, "privacy_violations": 5, "pii_exposure": 2},
            {"month": "Mar", "compliance": 86, "privacy_violations": 4, "pii_exposure": 2},
            {"month": "Apr", "compliance": 87, "privacy_violations": 3, "pii_exposure": 1},
            {"month": "May", "compliance": 88, "privacy_violations": 2, "pii_exposure": 1},
        ],
        "integrations": ["ServiceNow GRC", "SharePoint", "Confluence Governance Wiki"],
        "exceptions": [
            {"id": "TD-DPSC-006", "title": "Consent refresh deferral — mobile onboarding", "expires": "Q3 2026", "status": "Active"},
        ],
    },
    "ITPP": {
        "framework_name": "ITPP",
        "framework_description": "IT Process and Policy governance — DR readiness, incident management, change management, capacity, availability, and SLA compliance.",
        "context_label": "ITPP operational governance across DR, incident, change, and availability domains",
        "applications": [
            {"name": "Net Banking", "compliance_pct": 92.5, "findings": 2, "stale_evidences": 1, "pending_approvals": 2, "auditor_queue": 1, "last_validation": "2026-05-23", "risk_rating": "Low", "focus": "DR drill · change CAB"},
            {"name": "UPI Switch", "compliance_pct": 94.0, "findings": 1, "stale_evidences": 0, "pending_approvals": 1, "auditor_queue": 1, "last_validation": "2026-05-24", "risk_rating": "Low", "focus": "Availability · incident SLA"},
            {"name": "CBS Oracle", "compliance_pct": 88.7, "findings": 3, "stale_evidences": 2, "pending_approvals": 3, "auditor_queue": 2, "last_validation": "2026-05-22", "risk_rating": "Medium", "focus": "Backup validation · capacity"},
        ],
        "trends": [
            {"month": "Feb", "compliance": 86, "dr_success_pct": 92, "incident_sla_pct": 88},
            {"month": "Mar", "compliance": 88, "dr_success_pct": 94, "incident_sla_pct": 90},
            {"month": "Apr", "compliance": 90, "dr_success_pct": 95, "incident_sla_pct": 91},
            {"month": "May", "compliance": 91, "dr_success_pct": 96, "incident_sla_pct": 93},
        ],
        "integrations": ["ServiceNow GRC", "SharePoint Evidence Library", "Microsoft Teams Governance"],
        "exceptions": [
            {"id": "TD-ITPP-004", "title": "Emergency change PIR extension — Payment Gateway", "expires": "Q2 2026", "status": "Active"},
        ],
    },
}


# Framework-specific application drill-down details (shown when clicking Open)
APPLICATION_DRILLDOWN: dict[str, dict[str, dict[str, Any]]] = {
    "PCI DSS": {
        "Net Banking": {
            "sections": [
                {"title": "MFA Posture", "items": ["Privileged access MFA — 98% enrolled", "Jump server batch — 2 exceptions (TD-PCI-014)", "CDE admin accounts — fully enrolled"]},
                {"title": "Firewall Review", "items": ["Q2 firewall rule export — approved", "Segmentation review — 1 gap (Treasury link)", "DMZ rule change pending CAB"]},
                {"title": "Encryption Controls", "items": ["TDE attestation — current", "TLS 1.2+ — verified", "Key rotation — due Jun 2026"]},
                {"title": "Open Gaps", "items": ["Req 11.3 external VAPT — stale 45 days", "Req 8.2 MFA report — pending auditor"]},
            ],
        },
        "Card Payments": {
            "sections": [
                {"title": "CDE Segmentation", "items": ["Segmentation test — 1 failure (gateway VLAN)", "Firewall ACL review overdue", "Compensating control documented"]},
                {"title": "SIEM Validation", "items": ["Log review use-case — active", "Alert correlation — 3 gaps", "PCI log retention — compliant"]},
            ],
        },
    },
    "OS Baselining": {
        "Net Banking": {
            "sections": [
                {"title": "Hardened Servers", "items": ["142 Linux hosts — 89% CIS L2 compliant", "18 hosts with patch drift > 30 days", "4 unauthorized packages detected"]},
                {"title": "Open Violations", "items": ["SSH root login — UPI cluster node 3", "Open port 23 — legacy batch server", "Password policy gap — 2 service accounts"]},
                {"title": "Drifted Configs", "items": ["Tripwire drift — NETBANKING_PROD-07", "CIS benchmark deviation — sudoers file"]},
            ],
        },
        "Treasury": {
            "sections": [
                {"title": "Windows Hardening", "items": ["28 Windows servers — 82% compliant", "Critical patch missing — KB5034441 (4 hosts)", "Local admin accounts — 3 unmanaged"]},
            ],
        },
    },
    "DB Baselining": {
        "Oracle Core DB": {
            "sections": [
                {"title": "DB Hardening", "items": ["Unified audit trail — partial (3 schemas missing)", "TDE enabled — production", "Privileged access — 2 shared accounts flagged"]},
                {"title": "Backup Validation", "items": ["Daily backup — success rate 98%", "Restore test — last run Apr 2026", "Archive retention — compliant"]},
            ],
        },
        "Payments DB": {
            "sections": [
                {"title": "Critical Exposures", "items": ["Unencrypted column — legacy payment token table", "Audit logging off — UAT clone", "Service account password rotation overdue"]},
            ],
        },
    },
    "Nginx Baselining": {
        "UPI Gateway": {
            "sections": [
                {"title": "TLS Compliance", "items": ["TLS 1.3 enforced — all endpoints", "Certificate expiry — 45 days (api.upi.bank.in)", "Weak cipher — none detected"]},
                {"title": "Reverse Proxy", "items": ["HTTP security headers — HSTS, CSP configured", "WAF integration — active", "Static content integrity — verified"]},
            ],
        },
        "Mobile Banking Edge": {
            "sections": [
                {"title": "Internet-Facing Risk", "items": ["DMZ exposure — 2 endpoints without WAF", "SSL cert expires in 12 days — mobile.api.bank.in", "Rate limiting — configured"]},
            ],
        },
    },
    "AppSec": {
        "Mobile Banking": {
            "sections": [
                {"title": "SAST Findings", "items": ["14 critical — SonarQube gate failed", "8 high — SQL injection vector (retest pending)", "Secrets exposure — 1 API key in config"]},
                {"title": "SDLC Posture", "items": ["Secure build pipeline — 86% pass rate", "Dependency scan — 22 vulnerable libraries", "Release gate — blocked for v4.2.1"]},
            ],
        },
        "Loan System": {
            "sections": [
                {"title": "Critical CVEs", "items": ["Log4j variant — patched", "Spring framework CVE-2026-xxxx — open", "Third-party library — 6 critical SCA findings"]},
            ],
        },
    },
    "VAPT": {
        "UPI": {
            "sections": [
                {"title": "Critical Vulnerabilities", "items": ["CVE-2026-1842 — auth bypass (retest pending)", "SSRF vector — payment callback endpoint", "Exploit path — documented in pen-test report"]},
                {"title": "Retest Status", "items": ["3 findings awaiting retest", "Patch evidence uploaded — 2 of 3", "False positive validation — 1 closed"]},
            ],
        },
        "Net Banking": {
            "sections": [
                {"title": "Pen-Test Observations", "items": ["Session fixation — closed Mar 2026", "IDOR on account summary — patch scheduled", "Internet exposure — 2 external APIs in scope"]},
            ],
        },
    },
    "CSITE": {
        "Retail Banking": {
            "sections": [
                {"title": "Open Observations", "items": ["OBS-2026-041 — access review incomplete (32 days)", "OBS-2026-038 — segregation of duties gap", "Repeat observation — log retention policy"]},
                {"title": "Auditor Queue", "items": ["4 pending auditor review", "2 reopened findings", "Closure effectiveness — 84%"]},
            ],
        },
    },
    "DPSC": {
        "Mobile Banking": {
            "sections": [
                {"title": "Privacy Violations", "items": ["Consent log gap — onboarding flow v3.2", "PII in analytics export — masked pending", "Retention exceeded — customer archive batch"]},
                {"title": "Data Retention", "items": ["7-year retention — 2 batches overdue", "Encryption posture — 94% compliant"]},
            ],
        },
    },
    "ITPP": {
        "Net Banking": {
            "sections": [
                {"title": "DR Readiness", "items": ["Semi-annual DR drill — passed Apr 2026", "RTO achieved — 4.2 hours (target 6h)", "Backup validation — daily success 99%"]},
                {"title": "Change Management", "items": ["CAB approval rate — 96%", "Emergency change — 1 PIR pending 5 days", "Problem management — 3 open RCAs"]},
            ],
        },
    },
}


def get_framework_profile(framework_name: str) -> dict[str, Any]:
    """Return framework-specific profile or a minimal fallback."""
    if framework_name in FRAMEWORK_PROFILES:
        return FRAMEWORK_PROFILES[framework_name]
    return {
        "framework_name": framework_name,
        "framework_description": f"{framework_name} control implementation and evidence governance.",
        "context_label": f"{framework_name} posture across onboarded applications",
        "applications": [],
        "trends": [],
        "integrations": ["SharePoint", "ServiceNow GRC"],
        "exceptions": [],
    }


def get_application_drilldown(framework_name: str, application: str) -> dict[str, Any] | None:
    fw = APPLICATION_DRILLDOWN.get(framework_name, {})
    if application in fw:
        return fw[application]
    seed = f"{framework_name}::{application}"
    return {
        "sections": [
            {"title": f"{framework_name} Control Posture", "items": [
                f"Application {application} — framework-scoped controls in review",
                f"Pending validations — {_seed(seed + 'p', 1, 6)}",
                f"Open findings — {_seed(seed + 'f', 0, 4)}",
            ]},
        ],
    }


def build_framework_trends(framework_name: str) -> list[dict]:
    profile = get_framework_profile(framework_name)
    return profile.get("trends", [])


def build_framework_governance_analytics(framework_name: str) -> dict[str, Any]:
    """Framework-scoped analytics for Trends tab — NOT enterprise-wide."""
    profile = get_framework_profile(framework_name)
    trends = profile.get("trends", [])
    latest = trends[-1] if trends else {}
    apps = profile.get("applications", [])
    return {
        "framework_name": framework_name,
        "context_label": profile.get("context_label", ""),
        "audit_readiness_pct": latest.get("compliance", _seed(framework_name + "ar", 78, 92)),
        "stale_evidence_pct": _seed(framework_name + "st", 4, 12),
        "sla_breaches": sum(a.get("findings", 0) for a in apps) // 2 + _seed(framework_name + "sla", 1, 5),
        "escalated": _seed(framework_name + "esc", 0, 4),
        "open_findings": sum(a.get("findings", 0) for a in apps),
        "implementation_coverage_pct": latest.get("compliance", 85),
        "control_effectiveness": {framework_name: latest.get("compliance", 85)},
        "top_risky_controls": [
            {"risk": "High", "framework": framework_name, "control": a["focus"], "aging_days": _seed(a["name"], 10, 45)}
            for a in sorted(apps, key=lambda x: -x.get("findings", 0))[:3]
        ],
        "top_risk_applications": [
            {"application": a["name"], "compliance_pct": a["compliance_pct"], "open_observations": a["findings"], "sla_breaches": _seed(a["name"], 0, 3)}
            for a in sorted(apps, key=lambda x: x.get("compliance_pct", 100))[:4]
        ],
        "trends": trends,
        "is_framework_scoped": True,
    }
