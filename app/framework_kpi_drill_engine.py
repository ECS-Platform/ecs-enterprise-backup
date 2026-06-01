"""Framework-specific KPI configurations and drilldown datasets."""

from __future__ import annotations

import hashlib
from typing import Any

from app.demo_data_standards import ensure_drill_rows, generate_standard_drill_row, pick, seed, between

# Standard drill columns (where relevant)
STANDARD_DRILL_COLUMNS = [
    "application", "framework", "domain", "control", "finding",
    "evidence", "owner", "status", "risk", "last_updated",
]

# Metric-specific column layouts
METRIC_COLUMN_PROFILES: dict[str, list[str]] = {
    "sast_open_items": ["application", "framework", "control", "finding_id", "severity", "status", "owner", "due_date"],
    "sast_findings": ["application", "framework", "control", "finding_id", "severity", "status", "owner", "due_date"],
    "dast_critical": ["application", "url", "finding", "severity", "owner", "status"],
    "dast_findings": ["application", "url", "finding", "severity", "owner", "status"],
    "sca_vulnerabilities": ["application", "package", "version", "vulnerability", "cvss", "owner"],
    "release_blockers": ["application", "framework", "control", "finding", "severity", "owner", "status", "due_date"],
    "vulnerable_apps": ["application", "framework", "domain", "control", "finding", "risk", "owner", "status"],
    "open_vulnerabilities": ["application", "framework", "finding_id", "finding", "severity", "status", "owner", "due_date"],
    "critical_cves": ["application", "framework", "finding_id", "finding", "severity", "cvss", "owner", "status"],
    "pen_test_findings": ["application", "framework", "control", "finding", "severity", "owner", "status"],
    "remediation_backlog": ["application", "framework", "finding", "severity", "owner", "status", "due_date"],
    "payment_controls": ["application", "framework", "domain", "control", "status", "owner", "evidence", "last_updated"],
    "upi_security_controls": ["application", "framework", "control", "status", "owner", "evidence", "risk"],
    "card_security_controls": ["application", "framework", "control", "status", "owner", "evidence", "risk"],
    "encryption_compliance": ["application", "framework", "domain", "control", "status", "evidence", "owner", "last_updated"],
    "open_payment_findings": ["application", "framework", "finding", "severity", "owner", "status", "due_date"],
    "servers_assessed": ["application", "framework", "domain", "control", "status", "owner", "evidence", "last_updated"],
    "baseline_deviations": ["application", "framework", "control", "finding", "severity", "owner", "status", "last_updated"],
    "critical_deviations": ["application", "framework", "control", "finding", "severity", "owner", "status", "due_date"],
    "patch_compliance": ["application", "framework", "domain", "control", "status", "owner", "evidence", "last_updated"],
    "databases_assessed": ["application", "framework", "domain", "control", "status", "owner", "evidence", "last_updated"],
    "critical_db_findings": ["application", "framework", "control", "finding", "severity", "owner", "status", "due_date"],
    "privilege_violations": ["application", "framework", "control", "finding", "severity", "owner", "status"],
    "policies_reviewed": ["application", "framework", "domain", "control", "status", "owner", "evidence", "last_updated"],
    "process_controls": ["application", "framework", "domain", "control", "status", "owner", "evidence", "last_updated"],
    "open_actions": ["application", "framework", "control", "finding", "owner", "status", "due_date", "risk"],
}

SCA_PACKAGES = [
    ("log4j-core", "2.14.1", "CVE-2021-44228"),
    ("spring-core", "5.3.18", "CVE-2022-22965"),
    ("openssl", "1.1.1k", "CVE-2021-3711"),
    ("jackson-databind", "2.12.3", "CVE-2020-36518"),
    ("commons-text", "1.9", "CVE-2022-42889"),
    ("netty-codec", "4.1.68", "CVE-2021-37136"),
    ("tomcat-embed-core", "9.0.50", "CVE-2021-42340"),
    ("lodash", "4.17.20", "CVE-2021-23337"),
]

DAST_PATHS = [
    "/api/v1/login", "/payments/transfer", "/account/summary",
    "/admin/config", "/oauth/token", "/cards/activate",
]

# Each spec: metric slug, label, value builder key, hint, tone
# Values are computed deterministically per framework+metric so dashboards look unique.


def _seed_int(seed: str, lo: int, hi: int) -> int:
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return lo + (h % (hi - lo + 1))


def _pct(seed: str, lo: int, hi: int) -> str:
    return f"{_seed_int(seed, lo, hi)}%"


def _int(seed: str, lo: int, hi: int) -> str:
    return str(_seed_int(seed, lo, hi))


# metric -> row flavor for drill datasets
_METRIC_FLAVORS: dict[str, dict[str, Any]] = {
    "open_vulnerabilities": {"finding_prefix": "Vuln", "status": "Open", "risk": "High"},
    "critical_cves": {"finding_prefix": "CVE", "status": "Open", "risk": "Critical"},
    "pen_test_findings": {"finding_prefix": "Pen-Test", "status": "In Remediation", "risk": "High"},
    "remediation_backlog": {"finding_prefix": "Remediation", "status": "Pending Review", "risk": "Medium"},
    "retest_pass_rate": {"finding_prefix": "Retest", "status": "Closed", "risk": "Low"},
    "payment_controls": {"domain": "Payment Security", "control_prefix": "PAY"},
    "upi_security_controls": {"domain": "UPI Security", "control_prefix": "UPI"},
    "card_security_controls": {"domain": "Card Security", "control_prefix": "CRD"},
    "encryption_compliance": {"domain": "Cryptography", "control_prefix": "ENC"},
    "open_payment_findings": {"finding_prefix": "Payment Finding", "status": "Open", "risk": "High"},
    "servers_assessed": {"domain": "OS Hardening", "control_prefix": "OS"},
    "baseline_deviations": {"finding_prefix": "Baseline Drift", "status": "Open", "risk": "Medium"},
    "critical_deviations": {"finding_prefix": "Critical Drift", "status": "Escalated", "risk": "Critical"},
    "patch_compliance": {"domain": "Patch Management", "control_prefix": "PCH"},
    "hardening_score": {"domain": "Hardening", "control_prefix": "HRD"},
    "databases_assessed": {"domain": "Database Security", "control_prefix": "DB"},
    "critical_db_findings": {"finding_prefix": "DB Finding", "status": "Open", "risk": "Critical"},
    "privilege_violations": {"finding_prefix": "Privilege Violation", "status": "Open", "risk": "High"},
    "backup_compliance": {"domain": "Backup & Recovery", "control_prefix": "BKP"},
    "encryption_coverage": {"domain": "Encryption", "control_prefix": "TDE"},
    "policies_reviewed": {"domain": "Policy Management", "control_prefix": "POL"},
    "process_controls": {"domain": "Process Control", "control_prefix": "PRC"},
    "exceptions": {"finding_prefix": "Exception", "status": "Approved", "risk": "Medium"},
    "compliance_pct": {"domain": "Compliance", "control_prefix": "CMP"},
    "open_actions": {"finding_prefix": "Action Item", "status": "Open", "risk": "Medium"},
    "sast_findings": {"finding_prefix": "SAST", "status": "Open", "risk": "High"},
    "dast_findings": {"finding_prefix": "DAST", "status": "In Remediation", "risk": "High"},
    "code_review_coverage": {"domain": "Secure SDLC", "control_prefix": "CRV"},
    "secure_coding_controls": {"domain": "Secure Coding", "control_prefix": "SEC"},
    "remediation_progress": {"finding_prefix": "Remediation", "status": "In Remediation", "risk": "Medium"},
    "sast_open_items": {"finding_prefix": "SAST", "status": "Open", "risk": "High"},
    "dast_critical": {"finding_prefix": "DAST", "status": "Open", "risk": "Critical"},
    "sca_vulnerabilities": {"finding_prefix": "SCA", "status": "Open", "risk": "High"},
    "release_blockers": {"finding_prefix": "Release Blocker", "status": "Open", "risk": "Critical"},
    "secure_sdlc_score": {"domain": "Secure SDLC", "control_prefix": "SDLC"},
    "vulnerable_apps": {"finding_prefix": "AppSec Gap", "status": "Open", "risk": "High"},
    "internet_findings": {"finding_prefix": "Internet Exposure", "status": "Open", "risk": "High"},
    "retention_violations": {"finding_prefix": "Retention", "status": "Open", "risk": "Medium"},
    "unsupported_os": {"finding_prefix": "EOL OS", "status": "Open", "risk": "High"},
    "audit_logging_gaps": {"finding_prefix": "Audit Log Gap", "status": "Open", "risk": "Medium"},
    "tls_posture": {"domain": "TLS", "control_prefix": "TLS"},
    "expired_certs": {"finding_prefix": "Expired Cert", "status": "Open", "risk": "High"},
    "weak_cipher_suites": {"finding_prefix": "Weak Cipher", "status": "Open", "risk": "High"},
    "config_drifts": {"finding_prefix": "Config Drift", "status": "Open", "risk": "Medium"},
    "waf_coverage": {"domain": "WAF", "control_prefix": "WAF"},
    "pci_maturity": {"domain": "PCI CDE", "control_prefix": "PCI"},
    "cde_controls": {"domain": "CDE", "control_prefix": "CDE"},
    "open_audit_gaps": {"finding_prefix": "Audit Gap", "status": "Open", "risk": "High"},
    "qsa_readiness": {"domain": "QSA", "control_prefix": "QSA"},
    "mfa_exceptions": {"finding_prefix": "MFA Exception", "status": "Approved", "risk": "Medium"},
    "hardening_score": {"domain": "Hardening", "control_prefix": "HRD"},
    "dr_test_compliance": {"domain": "DR Testing", "control_prefix": "DR"},
    "it_risks_identified": {"finding_prefix": "IT Risk", "status": "Open", "risk": "High"},
    "dr_test_coverage": {"domain": "DR Coverage", "control_prefix": "DR"},
    "bcp_gaps": {"finding_prefix": "BCP Gap", "status": "Open", "risk": "Medium"},
    "critical_dependencies": {"finding_prefix": "Dependency", "status": "Open", "risk": "Critical"},
    "open_dr_actions": {"finding_prefix": "DR Action", "status": "Open", "risk": "Medium"},
    "rto_breaches": {"finding_prefix": "RTO Breach", "status": "Escalated", "risk": "Critical"},
    "trust_criteria_coverage": {"domain": "SOC2 TSC", "control_prefix": "TSC"},
    "access_control_tests": {"domain": "Access Control", "control_prefix": "CC6"},
    "change_mgmt_gaps": {"finding_prefix": "Change Gap", "status": "Open", "risk": "Medium"},
    "availability_slas": {"domain": "Availability", "control_prefix": "CC7"},
    "open_soc_observations": {"finding_prefix": "SOC Observation", "status": "Open", "risk": "High"},
    "evidence_gaps": {"finding_prefix": "Evidence Gap", "status": "Open", "risk": "Medium"},
    "annex_a_controls": {"domain": "Annex A", "control_prefix": "A"},
    "isms_maturity": {"domain": "ISMS", "control_prefix": "ISMS"},
    "risk_treatment_gaps": {"finding_prefix": "Risk Treatment", "status": "Open", "risk": "High"},
    "audit_nonconformities": {"finding_prefix": "NC", "status": "Open", "risk": "Critical"},
    "soa_coverage": {"domain": "SoA", "control_prefix": "SoA"},
    "corrective_actions": {"finding_prefix": "CAPA", "status": "Open", "risk": "Medium"},
    "reopened_findings": {"finding_prefix": "Reopened", "status": "Open", "risk": "High"},
    "code_review_coverage": {"domain": "Code Review", "control_prefix": "CRV"},
    "secure_coding_controls": {"domain": "Secure Coding", "control_prefix": "SEC"},
    "controls": {"domain": "Controls", "control_prefix": "CTL"},
    "evidence": {"domain": "Evidence", "control_prefix": "EVD"},
}


def _value_for_spec(framework: str, spec: dict, n_ctrl: int, stats: dict) -> str:
    sk = f"{framework}::{spec['metric']}"
    kind = spec.get("value_kind", "int")
    lo, hi = spec.get("lo", 1), spec.get("hi", 10)
    if kind == "pct":
        return _pct(sk, lo, hi)
    if kind == "ctrl":
        return str(n_ctrl)
    if kind == "evidence":
        return str(stats.get("evidence_total", 0))
    if kind == "stale":
        return str(stats.get("stale", 0) + stats.get("expired", 0))
    return _int(sk, lo, hi)


def _kpi(metric: str, label: str, hint: str, tone: str, **value_kw) -> dict:
    return {"metric": metric, "label": label, "hint": hint, "tone": tone, **value_kw}


FRAMEWORK_KPI_SPECS: dict[str, list[dict]] = {
    "PCI DSS": [
        _kpi("pci_maturity", "PCI Maturity", "CDE posture index", "primary", value_kind="pct", lo=78, hi=92),
        _kpi("cde_controls", "CDE Controls", "Cardholder scope", "navy", value_kind="ctrl"),
        _kpi("encryption_coverage", "Encryption Coverage", "At-rest & in-transit", "success", value_kind="pct", lo=88, hi=98),
        _kpi("mfa_exceptions", "MFA Exceptions", "CDE access waivers", "warning", lo=0, hi=4),
        _kpi("open_audit_gaps", "Open Audit Gaps", "QSA observations", "danger", lo=2, hi=9),
        _kpi("qsa_readiness", "QSA Readiness", "Attestation readiness", "teal", value_kind="pct", lo=82, hi=96),
    ],
    "DPSC": [
        _kpi("payment_controls", "Payment Controls", "Switch & gateway controls", "primary", lo=18, hi=42),
        _kpi("upi_security_controls", "UPI Security Controls", "UPI rail security", "teal", lo=12, hi=28),
        _kpi("card_security_controls", "Card Security Controls", "Issuing & acquiring", "navy", lo=10, hi=24),
        _kpi("encryption_compliance", "Encryption Compliance", "PAN/token protection", "success", value_kind="pct", lo=91, hi=99),
        _kpi("open_payment_findings", "Open Payment Findings", "Active payment gaps", "danger", lo=3, hi=14),
        _kpi("retention_violations", "Retention Violations", "Data retention SLA", "warning", lo=1, hi=6),
    ],
    "OS Baselining": [
        _kpi("servers_assessed", "Servers Assessed", "In-scope Linux/Windows", "primary", lo=840, hi=1240),
        _kpi("baseline_deviations", "Baseline Deviations", "CIS benchmark drift", "warning", lo=18, hi=56),
        _kpi("critical_deviations", "Critical Deviations", "Severity-1 hardening gaps", "danger", lo=4, hi=16),
        _kpi("patch_compliance", "Patch Compliance", "Critical patch SLA", "success", value_kind="pct", lo=84, hi=96),
        _kpi("hardening_score", "Hardening Score", "Weighted CIS score", "teal", value_kind="pct", lo=79, hi=93),
        _kpi("unsupported_os", "Unsupported OS", "End-of-life hosts", "danger", lo=2, hi=9),
    ],
    "DB Baselining": [
        _kpi("databases_assessed", "Databases Assessed", "Oracle/MSSQL/MySQL", "primary", lo=62, hi=118),
        _kpi("critical_db_findings", "Critical DB Findings", "Production DB gaps", "danger", lo=3, hi=12),
        _kpi("privilege_violations", "Privilege Violations", "Excess DBA/sysadmin", "danger", lo=2, hi=11),
        _kpi("backup_compliance", "Backup Compliance", "RPO/RTO validated", "success", value_kind="pct", lo=88, hi=98),
        _kpi("encryption_coverage", "Encryption Coverage", "TDE & key mgmt", "success", value_kind="pct", lo=91, hi=99),
        _kpi("audit_logging_gaps", "Audit Logging Gaps", "DB audit trail off", "warning", lo=1, hi=5),
    ],
    "Nginx Baselining": [
        _kpi("tls_posture", "TLS Posture", "TLS 1.2+ enforced", "success", value_kind="pct", lo=86, hi=97),
        _kpi("expired_certs", "Expired Certs", "Edge / DMZ certs", "warning", lo=1, hi=6),
        _kpi("weak_cipher_suites", "Weak Cipher Suites", "Deprecated ciphers", "danger", lo=2, hi=8),
        _kpi("internet_exposure", "Internet Exposure", "Public-facing apps", "danger", lo=4, hi=14),
        _kpi("config_drifts", "Config Drifts", "Baseline deviations", "warning", lo=6, hi=22),
        _kpi("waf_coverage", "WAF Coverage", "Protected endpoints", "teal", value_kind="pct", lo=78, hi=94),
    ],
    "AppSec": [
        _kpi("sast_open_items", "SAST Open Items", "Static analysis backlog", "danger", lo=14, hi=38),
        _kpi("dast_critical", "DAST Critical", "Dynamic scan criticals", "danger", lo=3, hi=12),
        _kpi("sca_vulnerabilities", "SCA Vulnerabilities", "Third-party libs", "warning", lo=8, hi=28),
        _kpi("release_blockers", "Release Blockers", "Go-live blockers", "danger", lo=1, hi=7),
        _kpi("secure_sdlc_score", "Secure SDLC Score", "Pipeline maturity", "success", value_kind="pct", lo=72, hi=89),
        _kpi("vulnerable_apps", "Vulnerable Apps", "Tier-1 systems", "warning", lo=4, hi=9),
    ],
    "VAPT": [
        _kpi("open_vulnerabilities", "Open Vulnerabilities", "All severities open", "danger", lo=18, hi=52),
        _kpi("critical_cves", "Critical CVEs", "CVSS >= 9.0", "danger", lo=2, hi=11),
        _kpi("pen_test_findings", "Pen-Test Findings", "Latest engagement", "warning", lo=6, hi=24),
        _kpi("remediation_backlog", "Remediation Backlog", "Past SLA items", "danger", lo=8, hi=28),
        _kpi("retest_pass_rate", "Retest Pass Rate", "Closure validation", "success", value_kind="pct", lo=78, hi=94),
        _kpi("internet_findings", "Internet Findings", "External scope", "warning", lo=5, hi=19),
    ],
    "CSITE": [
        _kpi("sast_findings", "SAST Findings", "Static code review", "danger", lo=10, hi=32),
        _kpi("dast_findings", "DAST Findings", "Dynamic app testing", "warning", lo=6, hi=22),
        _kpi("code_review_coverage", "Code Review Coverage", "Peer review complete", "success", value_kind="pct", lo=74, hi=92),
        _kpi("secure_coding_controls", "Secure Coding Controls", "Standards enforced", "primary", lo=24, hi=58),
        _kpi("remediation_progress", "Remediation Progress", "Findings closed MTD", "teal", value_kind="pct", lo=62, hi=88),
        _kpi("reopened_findings", "Reopened Findings", "Repeat observations", "danger", lo=1, hi=5),
    ],
    "ITPP": [
        _kpi("policies_reviewed", "Policies Reviewed", "Annual policy cycle", "primary", lo=28, hi=48),
        _kpi("process_controls", "Process Controls", "IT process controls", "navy", lo=42, hi=86),
        _kpi("exceptions", "Exceptions", "Active waivers", "warning", lo=3, hi=14),
        _kpi("compliance_pct", "Compliance %", "ITPP adherence", "success", value_kind="pct", lo=85, hi=96),
        _kpi("open_actions", "Open Actions", "Owner actions pending", "danger", lo=5, hi=22),
        _kpi("dr_test_compliance", "DR Test Compliance", "Semi-annual drills", "teal", value_kind="pct", lo=88, hi=98),
    ],
    "ITDRM": [
        _kpi("it_risks_identified", "IT Risks Identified", "Registered IT risks", "danger", lo=14, hi=38),
        _kpi("dr_test_coverage", "DR Test Coverage", "Apps with DR tested", "success", value_kind="pct", lo=82, hi=96),
        _kpi("bcp_gaps", "BCP Gaps", "Business continuity gaps", "warning", lo=3, hi=12),
        _kpi("critical_dependencies", "Critical IT Dependencies", "Single points of failure", "danger", lo=4, hi=15),
        _kpi("open_dr_actions", "Open DR Actions", "DR remediation backlog", "warning", lo=6, hi=20),
        _kpi("rto_breaches", "RTO Breaches", "Recovery SLA misses", "danger", lo=1, hi=5),
    ],
    "SOC2": [
        _kpi("trust_criteria_coverage", "Trust Criteria Coverage", "TSC mapped controls", "primary", value_kind="pct", lo=86, hi=97),
        _kpi("access_control_tests", "Access Control Tests", "CC6 test procedures", "navy", lo=32, hi=68),
        _kpi("change_mgmt_gaps", "Change Mgmt Gaps", "CC8 deviations", "warning", lo=2, hi=10),
        _kpi("availability_slas", "Availability SLAs", "CC7 uptime targets", "success", value_kind="pct", lo=99, hi=100),
        _kpi("open_soc_observations", "Open SOC Observations", "Auditor observations", "danger", lo=3, hi=14),
        _kpi("evidence_gaps", "Evidence Gaps", "Missing TSC evidence", "warning", lo=2, hi=9),
    ],
    "ISO27001": [
        _kpi("annex_a_controls", "Annex A Controls", "ISMS control set", "primary", lo=78, hi=114),
        _kpi("isms_maturity", "ISMS Maturity", "Certification readiness", "success", value_kind="pct", lo=80, hi=94),
        _kpi("risk_treatment_gaps", "Risk Treatment Gaps", "Open risk treatments", "danger", lo=4, hi=16),
        _kpi("audit_nonconformities", "Audit Non-Conformities", "Major/minor NCs", "danger", lo=1, hi=8),
        _kpi("soa_coverage", "SoA Coverage", "Statement of Applicability", "teal", value_kind="pct", lo=88, hi=99),
        _kpi("corrective_actions", "Corrective Actions", "CAPA backlog", "warning", lo=3, hi=12),
    ],
    "RBI Cyber Security": [
        _kpi("rbi_maturity_score", "RBI Maturity Score", "Cyber framework index", "primary", value_kind="pct", lo=74, hi=88),
        _kpi("incident_reporting_gaps", "Incident Reporting Gaps", "RBI notification SLA", "danger", lo=2, hi=9),
        _kpi("api_security_controls", "API Security Controls", "Open banking API scope", "warning", lo=8, hi=22),
        _kpi("cyber_resilience_score", "Cyber Resilience Score", "BC/DR cyber readiness", "success", value_kind="pct", lo=79, hi=93),
        _kpi("third_party_risk_gaps", "Third-Party Risk Gaps", "Vendor cyber exposure", "danger", lo=4, hi=14),
        _kpi("board_reporting_readiness", "Board Reporting Readiness", "Cyber board pack status", "teal", value_kind="pct", lo=82, hi=96),
    ],
}


def build_framework_kpi_list(framework: str, controls: list[dict], stats: dict[str, int]) -> list[dict]:
    """Return framework-specific KPI cards with computed values."""
    specs = FRAMEWORK_KPI_SPECS.get(framework)
    n_ctrl = len(controls)
    if not specs:
        return [
            {"metric": "controls", "label": "Controls", "value": str(n_ctrl), "hint": "In scope", "tone": "primary"},
            {"metric": "evidence", "label": "Evidence", "value": str(stats.get("evidence_total", 0)), "hint": "Linked artefacts", "tone": "teal"},
        ]
    out: list[dict] = []
    for spec in specs:
        out.append({
            "metric": spec["metric"],
            "label": spec["label"],
            "value": _value_for_spec(framework, spec, n_ctrl, stats),
            "hint": spec["hint"],
            "tone": spec["tone"],
        })
    return out


def _framework_apps(framework: str) -> list[str]:
    from app.demo_data_standards import BANKING_APPLICATIONS, pick, seed

    apps = list(BANKING_APPLICATIONS)
    s = seed("fw-apps", framework)
    # Framework-biased app ordering for visible uniqueness
    bias: dict[str, list[str]] = {
        "VAPT": ["Net Banking", "Mobile Banking", "Payments", "UPI Gateway", "API Gateway"],
        "DPSC": ["Payments", "UPI Gateway", "Cards", "Customer Onboarding", "Fraud Monitoring"],
        "OS Baselining": ["Core Banking", "Net Banking", "API Gateway", "Data Lake", "ATM Switch"],
        "DB Baselining": ["Core Banking", "CBS Oracle", "Data Lake", "Trade Finance", "CRM"],
        "CSITE": ["Net Banking", "Loan Origination", "Trade Finance", "Wealth Management", "CRM"],
        "ITPP": ["Core Banking", "Net Banking", "Payments", "Data Lake", "ATM Switch"],
        "ITDRM": ["Core Banking", "Net Banking", "Payments", "Data Lake", "Mobile Banking"],
        "SOC2": ["Net Banking", "CRM", "Wealth Management", "Customer Onboarding", "Data Lake"],
        "ISO27001": ["Core Banking", "Net Banking", "Trade Finance", "Fraud Monitoring", "CRM"],
    }
    preferred = bias.get(framework, apps[:5])
    return preferred + [a for a in apps if a not in preferred]


def _columns_for_metric(metric: str) -> list[str]:
    if metric in METRIC_COLUMN_PROFILES:
        return METRIC_COLUMN_PROFILES[metric]
    if "sast" in metric:
        return METRIC_COLUMN_PROFILES["sast_open_items"]
    if "dast" in metric:
        return METRIC_COLUMN_PROFILES["dast_critical"]
    if "sca" in metric:
        return METRIC_COLUMN_PROFILES["sca_vulnerabilities"]
    return STANDARD_DRILL_COLUMNS


def _enrich_row(row: dict[str, Any], index: int, framework: str, metric: str) -> dict[str, Any]:
    s = seed("fw-drill", framework, metric, index)
    row = dict(row)
    row["last_updated"] = row.get("last_updated") or row.get("date") or f"2026-05-{(index % 20) + 1:02d}"
    row["finding_id"] = row.get("finding_id") or f"FND-{framework[:3].upper().replace(' ', '')}-{index + 1:05d}"
    row["severity"] = row.get("severity") or row.get("risk") or pick(s, ["Critical", "High", "Medium", "Low"])
    row["due_date"] = f"2026-06-{(index % 25) + 1:02d}"
    row["cvss"] = f"{between(s, 42, 99) / 10:.1f}"

    if metric in ("dast_critical", "dast_findings") or "dast" in metric:
        path = pick(s, DAST_PATHS)
        app_slug = row["application"].lower().replace(" ", "-")
        row["url"] = f"https://{app_slug}.demo.bank{path}"
    if metric == "sca_vulnerabilities" or "sca" in metric:
        pkg, ver, vuln = SCA_PACKAGES[index % len(SCA_PACKAGES)]
        row["package"] = pkg
        row["version"] = ver
        row["vulnerability"] = vuln
    if "cve" in metric or metric == "critical_cves":
        row["finding"] = f"CVE-2023-{4000 + index} — {row['application']}"
        row["cvss"] = f"{between(s, 90, 99) / 10:.1f}"

    # Ensure all standard columns exist for mixed renders
    for col in STANDARD_DRILL_COLUMNS:
        row.setdefault(col, "—")
    return row


def _generate_framework_drill_row(
    index: int,
    *,
    framework: str,
    metric: str,
    flavor: dict[str, Any],
) -> dict[str, Any]:
    apps = _framework_apps(framework)
    row = generate_standard_drill_row(index, metric=f"{framework}:{metric}", application=apps[index % len(apps)])
    row["framework"] = framework
    if flavor.get("domain"):
        row["domain"] = flavor["domain"]
    prefix = flavor.get("control_prefix") or flavor.get("finding_prefix") or "CTL"
    row["control"] = f"{prefix}-{index + 1:03d} — {row['control'].split('—', 1)[-1].strip()}"
    if flavor.get("finding_prefix"):
        row["finding"] = f"{flavor['finding_prefix']} — {row['application']} / {framework}"
    if flavor.get("status"):
        row["status"] = flavor["status"]
    if flavor.get("risk"):
        row["risk"] = flavor["risk"]
    row["evidence"] = f"EVD-{framework[:3].upper().replace(' ', '')}-{index + 1:04d}"
    return _enrich_row(row, index, framework, metric)


def drill_framework_kpi(framework: str, metric: str) -> dict[str, Any]:
    """Return paginated drill dataset for a framework KPI."""
    metric = (metric or "").strip().lower().replace("-", "_").replace(" ", "_")
    fw = framework.strip()
    specs = FRAMEWORK_KPI_SPECS.get(fw, [])
    label = next((s["label"] for s in specs if s["metric"] == metric), metric.replace("_", " ").title())
    flavor = _METRIC_FLAVORS.get(metric, {})

    base: list[dict] = []
    for i in range(12):
        base.append(_generate_framework_drill_row(i, framework=fw, metric=metric, flavor=flavor))

    rows = ensure_drill_rows(base, 25, metric=f"{fw}:{metric}")
    rows = [_enrich_row(r, i, fw, metric) for i, r in enumerate(rows)]
    columns = _columns_for_metric(metric)
    # Pad missing column keys on each row
    for r in rows:
        for c in columns:
            r.setdefault(c, "—")
    return {
        "ok": True,
        "framework": fw,
        "metric": metric,
        "title": f"{label} — {fw}",
        "rows": rows,
        "columns": columns,
    }


def iter_framework_kpi_pairs() -> list[tuple[str, str, str]]:
    """All (framework, metric, label) tuples for test coverage."""
    pairs: list[tuple[str, str, str]] = []
    for fw, specs in FRAMEWORK_KPI_SPECS.items():
        for spec in specs:
            pairs.append((fw, spec["metric"], spec["label"]))
    return pairs


def framework_kpi_labels(framework: str) -> list[str]:
    specs = FRAMEWORK_KPI_SPECS.get(framework, [])
    return [s["label"] for s in specs]


def framework_kpi_values(framework: str, controls: list[dict], stats: dict[str, int]) -> list[str]:
    return [k["value"] for k in build_framework_kpi_list(framework, controls, stats)]
