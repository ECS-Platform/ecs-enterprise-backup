"""
Framework-specific dashboard profiles: KPIs, insights, themes, and workflow labels.
Additive presentation layer — does not alter catalog or workflow state logic.
"""

from __future__ import annotations

import hashlib
from typing import Any


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
            "owner_submit": "Upload Incident RCA",
            "owner_resubmit": "Resubmit SOC Evidence",
            "auditor_approve": "Close Incident",
            "auditor_reject": "Escalate Alert",
            "queue_title": "SOC & Incident Queue",
            "queue_subtitle": "SIEM alerts, threat detection, and incident response evidence",
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


def _framework_kpis(framework: str, controls: list[dict], stats: dict[str, int]) -> list[dict]:
    n_ctrl = len(controls)
    n_ev = stats["evidence_total"]
    fw = framework

    def pci():
        return [
            {"label": "PCI Maturity", "value": f"{_seed_int(fw+'maturity', 78, 92)}%", "hint": "CDE posture", "tone": "primary"},
            {"label": "Critical Gaps", "value": _seed_int(fw + "gaps", 2, 8), "hint": "Open audit obs.", "tone": "danger"},
            {"label": "Encryption Checks", "value": f"{_seed_int(fw+'enc', 88, 98)}%", "hint": "At-rest & in-transit", "tone": "success"},
            {"label": "MFA Exceptions", "value": _seed_int(fw + "mfa", 0, 4), "hint": "CDE access", "tone": "warning"},
            {"label": "Controls", "value": n_ctrl, "hint": f"{n_ev} evidences", "tone": "navy"},
            {"label": "Evidence Aging", "value": stats["stale"] + stats["expired"], "hint": "Stale / expired", "tone": "teal"},
        ]

    builders = {
        "PCI DSS": pci,
        "DPSC": lambda: [
            {"label": "Privacy Compliance", "value": f"{_seed_int(fw+'priv', 82, 94)}%", "hint": "DPSC assessment", "tone": "teal"},
            {"label": "Privacy Exceptions", "value": _seed_int(fw + "exc", 3, 11), "hint": "Active waivers", "tone": "warning"},
            {"label": "Retention Violations", "value": _seed_int(fw + "ret", 1, 6), "hint": "Expired retention", "tone": "danger"},
            {"label": "Masking Compliance", "value": f"{_seed_int(fw+'mask', 90, 99)}%", "hint": "Non-prod data", "tone": "success"},
            {"label": "Controls", "value": n_ctrl, "hint": f"{stats['applications']} apps", "tone": "primary"},
            {"label": "Sensitive Exposure", "value": _seed_int(fw + "exp", 0, 3), "hint": "Apps flagged", "tone": "danger"},
        ],
        "OS Baselining": lambda: [
            {"label": "Hardened Servers", "value": f"{_seed_int(fw+'hard', 84, 96)}%", "hint": "CIS L2 compliant", "tone": "success"},
            {"label": "Patch Gaps", "value": _seed_int(fw + "patch", 8, 24), "hint": "Critical missing", "tone": "danger"},
            {"label": "Unsupported OS", "value": _seed_int(fw + "os", 2, 9), "hint": "End-of-life hosts", "tone": "warning"},
            {"label": "Failed Checks", "value": _seed_int(fw + "fail", 12, 38), "hint": "Hardening drift", "tone": "warning"},
            {"label": "Controls", "value": n_ctrl, "hint": f"{n_ev} scan artefacts", "tone": "primary"},
            {"label": "Platform Split", "value": f"{_seed_int(fw+'lin', 58, 72)}% Linux", "hint": "Rest Windows", "tone": "navy"},
        ],
        "DB Baselining": lambda: [
            {"label": "DB Drift Items", "value": _seed_int(fw + "drift", 5, 18), "hint": "Config deviations", "tone": "warning"},
            {"label": "Weak Passwords", "value": _seed_int(fw + "pwd", 2, 9), "hint": "Rotation gaps", "tone": "danger"},
            {"label": "Audit Logging Off", "value": _seed_int(fw + "audit", 1, 5), "hint": "DB instances", "tone": "danger"},
            {"label": "Backup Failures", "value": _seed_int(fw + "bk", 0, 4), "hint": "Last 30 days", "tone": "warning"},
            {"label": "Controls", "value": n_ctrl, "hint": "Oracle/MSSQL/MySQL", "tone": "primary"},
            {"label": "TDE Coverage", "value": f"{_seed_int(fw+'tde', 91, 99)}%", "hint": "Production DBs", "tone": "success"},
        ],
        "Nginx Baselining": lambda: [
            {"label": "TLS Posture", "value": f"{_seed_int(fw+'tls', 86, 97)}%", "hint": "TLS 1.2+ enforced", "tone": "success"},
            {"label": "Weak TLS Configs", "value": _seed_int(fw + "weak", 2, 8), "hint": "Cipher issues", "tone": "danger"},
            {"label": "Expired Certs", "value": _seed_int(fw + "cert", 1, 6), "hint": "Edge / DMZ", "tone": "warning"},
            {"label": "Insecure Headers", "value": _seed_int(fw + "hdr", 3, 12), "hint": "Missing CSP/HSTS", "tone": "warning"},
            {"label": "Controls", "value": n_ctrl, "hint": f"{n_ev} edge configs", "tone": "primary"},
            {"label": "Internet Exposure", "value": _seed_int(fw + "iexp", 4, 14), "hint": "Public apps", "tone": "danger"},
        ],
        "AppSec": lambda: [
            {"label": "Critical Vulns", "value": _seed_int(fw + "crit", 3, 14), "hint": "Open findings", "tone": "danger"},
            {"label": "Open AppSec Items", "value": _seed_int(fw + "open", 18, 45), "hint": "All severities", "tone": "warning"},
            {"label": "Vulnerable Apps", "value": _seed_int(fw + "apps", 4, 9), "hint": "Tier-1 systems", "tone": "danger"},
            {"label": "Remediation SLA", "value": f"{_seed_int(fw+'sla', 72, 89)}%", "hint": "Within TAT", "tone": "success"},
            {"label": "Controls", "value": n_ctrl, "hint": "SAST/DAST/SCA", "tone": "primary"},
            {"label": "Release Risk", "value": _seed_int(fw + "rel", 22, 58), "hint": "Avg. this sprint", "tone": "warning"},
        ],
        "VAPT": lambda: [
            {"label": "Exploitable Vulns", "value": _seed_int(fw + "exploit", 2, 11), "hint": "Confirmed", "tone": "danger"},
            {"label": "Internet Findings", "value": _seed_int(fw + "inet", 6, 19), "hint": "External scope", "tone": "warning"},
            {"label": "Overdue Remediation", "value": _seed_int(fw + "od", 4, 13), "hint": "Past SLA", "tone": "danger"},
            {"label": "Critical CVEs", "value": _seed_int(fw + "cve", 1, 7), "hint": "CVSS >= 9.0", "tone": "danger"},
            {"label": "Controls", "value": n_ctrl, "hint": f"{n_ev} test artefacts", "tone": "primary"},
            {"label": "Retest Pass Rate", "value": f"{_seed_int(fw+'ret', 78, 94)}%", "hint": "Closure validation", "tone": "success"},
        ],
        "CSITE": lambda: [
            {"label": "Active Incidents", "value": _seed_int(fw + "inc", 2, 9), "hint": "Open P1/P2", "tone": "danger"},
            {"label": "Unresolved Alerts", "value": _seed_int(fw + "alert", 14, 38), "hint": "SIEM backlog", "tone": "warning"},
            {"label": "MTTR (hours)", "value": _seed_int(fw + "mttr", 3, 11), "hint": "P1 average", "tone": "teal"},
            {"label": "Critical Incidents", "value": _seed_int(fw + "critinc", 0, 3), "hint": "Last 30 days", "tone": "danger"},
            {"label": "Controls", "value": n_ctrl, "hint": "SOC operations", "tone": "primary"},
            {"label": "Cases Closed", "value": f"{_seed_int(fw+'closed', 82, 96)}%", "hint": "Within SLA", "tone": "success"},
        ],
        "ITPP": lambda: [
            {"label": "DR Test Compliance", "value": f"{_seed_int(fw+'dr', 88, 98)}%", "hint": "Semi-annual drills", "tone": "success"},
            {"label": "Failed Backups", "value": _seed_int(fw + "fbk", 1, 6), "hint": "Last 7 days", "tone": "danger"},
            {"label": "Overdue Changes", "value": _seed_int(fw + "chg", 3, 12), "hint": "CAB pending", "tone": "warning"},
            {"label": "Capacity Risks", "value": _seed_int(fw + "cap", 2, 8), "hint": "Saturation alerts", "tone": "warning"},
            {"label": "Controls", "value": n_ctrl, "hint": "7 ITPP domains", "tone": "navy"},
            {"label": "Policy Adherence", "value": f"{_seed_int(fw+'pol', 85, 96)}%", "hint": "Governance score", "tone": "primary"},
        ],
    }
    fn = builders.get(framework)
    return fn() if fn else [
        {"label": "Controls", "value": n_ctrl, "hint": "In scope", "tone": "primary"},
        {"label": "Evidence", "value": n_ev, "hint": "Linked artefacts", "tone": "teal"},
    ]


def _insight_sections(framework: str) -> list[dict]:
    fw = framework
    return {
        "PCI DSS": [
            {"type": "bars", "title": "Encryption Health by Application", "items": [
                {"name": "Net Banking", "score": _seed_int(fw + "nb", 88, 96)},
                {"name": "Payments", "score": _seed_int(fw + "pay", 82, 94)},
                {"name": "UPI Switch", "score": _seed_int(fw + "upi", 85, 97)},
                {"name": "Mobile Banking", "score": _seed_int(fw + "mob", 79, 91)},
            ]},
            {"type": "list", "title": "Top Risky PCI Applications", "items": [
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
            {"type": "heatmap", "title": "Server Compliance Heatmap", "items": [
                {"name": "NETBANKING_PROD", "score": _seed_int(fw + "s1", 88, 97), "risk": "Low"},
                {"name": "UPI_SWITCH_CLUSTER", "score": _seed_int(fw + "s2", 76, 89), "risk": "Medium"},
                {"name": "MOBILE_BANKING_API", "score": _seed_int(fw + "s4", 71, 85), "risk": "High"},
            ]},
            {"type": "list", "title": "Failed Baseline Drift", "items": [
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
            {"type": "heatmap", "title": "Code Security Posture", "items": [
                {"name": "Net Banking", "score": _seed_int(fw + "a1", 72, 88), "risk": "High"},
                {"name": "Mobile Banking", "score": _seed_int(fw + "a2", 78, 92), "risk": "Medium"},
                {"name": "Loan System", "score": _seed_int(fw + "a4", 68, 82), "risk": "High"},
            ]},
            {"type": "list", "title": "Top Vulnerable Applications", "items": [
                {"label": "Loan Origination — 14 critical SAST", "meta": "SonarQube gate failed", "severity": "Critical"},
                {"label": "Net Banking — 8 DAST findings", "meta": "SQLi retest pending", "severity": "High"},
            ]},
        ],
        "VAPT": [
            {"type": "metrics", "title": "Vulnerability Severity", "items": [
                {"label": "Critical", "value": _seed_int(fw + "c", 2, 7), "tone": "danger"},
                {"label": "High", "value": _seed_int(fw + "h", 8, 18), "tone": "warning"},
                {"label": "Medium", "value": _seed_int(fw + "m", 22, 45), "tone": "primary"},
            ]},
            {"type": "list", "title": "Critical Exposure Summary", "items": [
                {"label": "Internet Banking — auth bypass", "meta": "Pen test Mar 2026", "severity": "Critical"},
                {"label": "Payment Gateway — SSRF vector", "meta": "Patch scheduled", "severity": "High"},
            ]},
        ],
        "CSITE": [
            {"type": "timeline", "title": "Incident Timeline (Recent)", "items": [
                {"label": "INC-2026-0412 — Net Banking latency", "meta": "P2 · Closed · 4h MTTR", "severity": "Medium"},
                {"label": "INC-2026-0398 — UPI timeout spike", "meta": "P1 · Active · SOC engaged", "severity": "Critical"},
                {"label": "INC-2026-0371 — Phishing campaign", "meta": "P3 · Closed", "severity": "Low"},
            ]},
            {"type": "bars", "title": "Alert Trend (Weekly)", "items": [
                {"name": "Week 18", "score": 82}, {"name": "Week 19", "score": 76},
                {"name": "Week 20", "score": 68}, {"name": "Week 21", "score": 71},
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
    taglines = {
        "PCI DSS": "Cardholder data environment security and QSA audit readiness",
        "DPSC": "Digital payment security and customer data privacy governance",
        "OS Baselining": "Infrastructure hardening, CIS benchmarks, and patch compliance",
        "DB Baselining": "Database security, audit logging, and backup validation",
        "Nginx Baselining": "Edge TLS hardening, certificate lifecycle, and WAF posture",
        "AppSec": "Secure SDLC, SAST/DAST, and application vulnerability management",
        "VAPT": "Penetration testing, exploitable vulnerabilities, and remediation tracking",
        "CSITE": "Cyber security operations, SIEM alerts, and incident response",
        "ITPP": "IT policies, DR readiness, backup, change, and incident governance",
    }
    return {
        "theme": theme,
        "tagline": taglines.get(framework_name, "Framework controls and evidence workflow"),
        "kpis": _framework_kpis(framework_name, catalog_controls, stats),
        "insights": _insight_sections(framework_name),
        "workflow_labels": _workflow_labels(framework_name),
        "stats": stats,
        "show_itpp_panel": framework_name == "ITPP",
        "show_validation": framework_name not in ("CSITE",),
        "show_governance_strip": framework_name in ("PCI DSS", "ITPP", "CSITE", "VAPT"),
        "middle_label": {
            "PCI DSS": "Compliance & Encryption Insights",
            "DPSC": "Privacy Risk Summary",
            "OS Baselining": "Infrastructure Posture",
            "DB Baselining": "Database Security Posture",
            "Nginx Baselining": "TLS & Edge Security",
            "AppSec": "Secure SDLC Insights",
            "VAPT": "Vulnerability Intelligence",
            "CSITE": "SOC Operations Dashboard",
            "ITPP": "Operational Governance",
        }.get(framework_name, "Framework Insights"),
    }
