#!/usr/bin/env python3
"""Generate Phase-1 Framework Control Master YAML catalogue (one-time bootstrap)."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "config" / "framework_control_master"
FW_DIR = OUT / "frameworks"

FRAMEWORKS: list[dict] = [
    {
        "id": "itpp",
        "code": "ITPP",
        "name": "ITPP",
        "display_name": "Information Technology Policies & Procedures",
        "category": "Internal Governance",
        "regulator": "ECS Internal",
        "version": "2026.1",
        "description": "Operational IT governance covering DR, backup, change, incident, and availability management.",
        "domains": ["Disaster Recovery", "Backup Management", "Change Management", "Incident Management", "Availability"],
        "control_templates": [
            ("DR Plan Exists", "Disaster Recovery", "Enterprise DR plan approved and published annually."),
            ("DR Drill Conducted", "Disaster Recovery", "Semi-annual failover drill executed with sign-off."),
            ("Backup Enabled", "Backup Management", "Production workloads covered by scheduled backup jobs."),
            ("Restore Testing Conducted", "Backup Management", "Quarterly restore validation with evidence."),
            ("CAB Approval", "Change Management", "Production changes approved via Change Advisory Board."),
            ("Incident SLA Defined", "Incident Management", "P1/P2 response and resolution SLAs documented."),
            ("Availability SLA Defined", "Availability", "Tier-1 application uptime targets published."),
        ],
    },
    {
        "id": "asst",
        "code": "ASST",
        "name": "ASST",
        "display_name": "Application Security Self-Assessment",
        "category": "Pre-Assessment",
        "regulator": "AppSec CoE",
        "version": "2026.1",
        "description": "Pre-audit application security posture questionnaire for banking channels.",
        "domains": ["Encryption", "Authentication", "Logging", "Vulnerability", "Third Party"],
        "control_templates": [
            ("Encryption Posture", "Encryption", "Data-at-rest and in-transit encryption self-attestation."),
            ("Authentication Strength", "Authentication", "MFA and session management coverage matrix."),
            ("Logging & Monitoring Coverage", "Logging", "Application logs integrated with enterprise SIEM."),
            ("Patch & Vulnerability Posture", "Vulnerability", "Critical patch SLA and VA scan attestation."),
            ("DR & Business Continuity", "Availability", "Application RPO/RTO declaration and DR test proof."),
            ("Third-Party Dependencies", "Third Party", "Vendor security review for integrated APIs."),
        ],
    },
    {
        "id": "mbss",
        "code": "MBSS",
        "name": "MBSS",
        "display_name": "Minimum Baseline Security Standard",
        "category": "Security Baseline",
        "regulator": "Information Security",
        "version": "2026.1",
        "description": "Enterprise minimum security baseline for production banking systems.",
        "domains": ["Identity", "Network", "Logging", "Patch", "Configuration"],
        "control_templates": [
            ("Privileged Access Review", "Identity", "Quarterly recertification of privileged accounts."),
            ("Network Segmentation", "Network", "Production/DMZ segmentation validated."),
            ("Centralized Audit Logging", "Logging", "Security events forwarded to SOC SIEM."),
            ("Critical Patch Compliance", "Patch", "Critical OS and middleware patches within SLA."),
            ("Secure Configuration Baseline", "Configuration", "CIS-aligned hardening for production hosts."),
            ("MFA for Administrative Access", "Identity", "100% MFA on admin and jump-host access."),
        ],
    },
    {
        "id": "pci_dss",
        "code": "PCI",
        "name": "PCI DSS",
        "display_name": "Payment Card Industry Data Security Standard",
        "category": "Regulatory",
        "regulator": "PCI SSC",
        "version": "4.0.1",
        "description": "Cardholder data environment controls for payment processing channels.",
        "domains": ["Network", "Access Control", "Cryptography", "Monitoring", "Vulnerability"],
        "control_templates": [
            ("Req 1.2 — Network Segmentation", "Network", "CDE segmented from untrusted networks."),
            ("Req 3.4 — Encryption at Rest", "Cryptography", "PAN storage encrypted with approved algorithms."),
            ("Req 4.1 — Encryption in Transit", "Cryptography", "TLS 1.2+ for cardholder data transmission."),
            ("Req 7.2 — Access Control Review", "Access Control", "Quarterly CDE access recertification."),
            ("Req 10.2 — Audit Trail Integrity", "Monitoring", "Centralized immutable audit logs for CDE."),
            ("Req 11.3 — External VAPT", "Vulnerability", "Annual ASV scan with remediation validation."),
        ],
    },
    {
        "id": "dpsc",
        "code": "DPSC",
        "name": "DPSC",
        "display_name": "Digital Payment Security Controls",
        "category": "Regulatory",
        "regulator": "RBI",
        "version": "2026.1",
        "description": "Digital payment channel security controls aligned to RBI DPSC expectations.",
        "domains": ["API Security", "Encryption", "Fraud", "Settlement", "Reporting"],
        "control_templates": [
            ("API Security Gateway Hardening", "API Security", "WAF and OAuth validation on payment APIs."),
            ("UPI Channel Encryption", "Encryption", "NPCI-aligned TLS and payload protection."),
            ("Fraud Monitoring Coverage", "Fraud", "Real-time transaction screening effectiveness."),
            ("Settlement Reconciliation", "Settlement", "Automated reconciliation with exception tracking."),
            ("Regulatory Reporting — RBI DPSC", "Reporting", "Self-assessment workbook and gap tracker."),
            ("Cryptographic Key Lifecycle — Payments", "Encryption", "HSM key rotation and dual-control ceremony."),
        ],
    },
    {
        "id": "csite",
        "code": "CSI",
        "name": "C-SITE",
        "display_name": "Cyber Security Incident Tracking & Evaluation",
        "category": "Audit Assessment",
        "regulator": "Internal Audit",
        "version": "2026.1",
        "description": "SOC monitoring, threat detection, and incident response assurance framework.",
        "domains": ["SOC Operations", "Threat Detection", "Incident Response", "Awareness"],
        "control_templates": [
            ("SIEM Alert Monitoring & Triage", "SOC Operations", "24x7 alert triage within defined SLA."),
            ("EDR Threat Detection Coverage", "Threat Detection", "Endpoint detection deployed on critical assets."),
            ("Incident Response SLA", "Incident Response", "P1 MTTR tracked with postmortem closure."),
            ("Threat Intelligence Integration", "Threat Detection", "TI feeds correlated with SIEM use-cases."),
            ("Phishing Simulation Program", "Awareness", "Employee click-rate and coaching programme."),
            ("Vulnerability Management SLA", "Threat Detection", "Critical vulnerability aging within tolerance."),
        ],
    },
    {
        "id": "vapt",
        "code": "VAP",
        "name": "VAPT",
        "display_name": "Vulnerability Assessment & Penetration Testing",
        "category": "Audit Assessment",
        "regulator": "AppSec CoE",
        "version": "2026.1",
        "description": "Internal/external VA and penetration testing programme for banking assets.",
        "domains": ["Internal VA", "External VA", "Penetration Testing", "Remediation"],
        "control_templates": [
            ("Internal Vulnerability Assessment", "Internal VA", "Quarterly authenticated scan of CDE assets."),
            ("External Vulnerability Assessment", "External VA", "Internet-facing asset scope and scan report."),
            ("Penetration Testing — Internet Banking", "Penetration Testing", "Annual pen test with executive summary."),
            ("Remediation Evidence — Critical Findings", "Remediation", "Critical finding closure within SLA."),
            ("Closure Validation — Pen Test", "Remediation", "Retest validation and auditor sign-off."),
            ("VAPT Scope & Methodology", "Penetration Testing", "Approved rules of engagement document."),
        ],
    },
    {
        "id": "os_baseline",
        "code": "OSB",
        "name": "OS Baseline",
        "display_name": "Operating System Baseline",
        "category": "Security Baseline",
        "regulator": "Infrastructure Operations",
        "version": "2026.1",
        "description": "CIS-aligned operating system hardening for Linux and Windows production servers.",
        "domains": ["Hardening", "Patch", "Access", "Monitoring", "Integrity"],
        "control_templates": [
            ("Linux Server Hardening — CIS L2", "Hardening", "CIS benchmark scan with remediation tracker."),
            ("SSH Access Restrictions", "Access", "Root login disabled; key-based access enforced."),
            ("Patch Compliance — Critical", "Patch", "Critical OS patches applied within 30 days."),
            ("Privileged Command Logging", "Monitoring", "sudo/privileged command audit trail retained."),
            ("File Integrity Monitoring", "Integrity", "Critical system files monitored for unauthorized change."),
            ("Time Synchronization (NTP)", "Monitoring", "NTP stratum configuration and drift monitoring."),
        ],
    },
    {
        "id": "middleware_baseline",
        "code": "MWB",
        "name": "Middleware Baseline",
        "display_name": "Middleware Baseline",
        "category": "Security Baseline",
        "regulator": "Platform Engineering",
        "version": "2026.1",
        "description": "Security baseline for application servers, reverse proxies, and message middleware.",
        "domains": ["TLS", "Headers", "WAF", "Patch", "Logging"],
        "control_templates": [
            ("TLS 1.2+ on Internet Banking Edge", "TLS", "Edge proxy enforces approved cipher suites."),
            ("Security Headers — CSP/HSTS", "Headers", "Response headers validated on production endpoints."),
            ("WAF Rule Effectiveness", "WAF", "Blocked attack statistics and false-positive tuning."),
            ("Certificate Lifecycle Management", "TLS", "Certificate inventory with automated renewal."),
            ("ModSecurity CRS Version", "WAF", "CRS version attestation and change approval."),
            ("Access Log Retention", "Logging", "Middleware access logs retained per policy."),
        ],
    },
    {
        "id": "database_baseline",
        "code": "DBB",
        "name": "Database Baseline",
        "display_name": "Database Baseline",
        "category": "Security Baseline",
        "regulator": "Database Operations",
        "version": "2026.1",
        "description": "Oracle, PostgreSQL, and CBS database security baseline controls.",
        "domains": ["Encryption", "Access", "Audit", "Backup", "Patch"],
        "control_templates": [
            ("Transparent Data Encryption", "Encryption", "TDE enabled on production databases storing sensitive data."),
            ("Database Audit Logging", "Audit", "Unified audit trail with integrity verification."),
            ("Least Privilege — DB Accounts", "Access", "Role entitlement review and excess privilege remediation."),
            ("Backup & Recovery Validation", "Backup", "Backup success monitoring and restore test attestation."),
            ("Database Vulnerability Scan", "Patch", "Quarterly DB VA scan with patch application proof."),
            ("DB Activity Monitoring", "Audit", "DAM alerts for privileged SQL and anomalous access."),
        ],
    },
]


def _policy_id(fw_code: str, domain: str, idx: int) -> str:
    slug = domain.upper().replace(" ", "_").replace("&", "AND")[:12]
    return f"{fw_code}-POL-{slug}-{idx:02d}"


def _control_id(fw_code: str, idx: int) -> str:
    return f"{fw_code}-C-{idx:02d}"


def _proc_id(fw_code: str, idx: int) -> str:
    return f"{fw_code}-PROC-{idx:02d}"


def _evr_id(fw_code: str, idx: int, ev: int) -> str:
    return f"{fw_code}-EVR-{idx:02d}{ev}"


def build_framework_doc(spec: dict) -> dict:
    fw_code = spec["code"]
    policies: list[dict] = []
    controls: list[dict] = []
    seen_domains: dict[str, int] = {}

    for idx, (title, domain, description) in enumerate(spec["control_templates"], start=1):
        dom_idx = seen_domains.get(domain, 0) + 1
        seen_domains[domain] = dom_idx
        pol_id = _policy_id(fw_code, domain, dom_idx)
        if not any(p["id"] == pol_id for p in policies):
            policies.append(
                {
                    "id": pol_id,
                    "title": f"{domain} Policy",
                    "description": f"Governing policy for {domain.lower()} requirements within {spec['display_name']}.",
                    "owner": "Compliance & Controls",
                    "status": "Active",
                    "review_frequency": "Annual",
                }
            )
        proc_id = _proc_id(fw_code, idx)
        controls.append(
            {
                "id": _control_id(fw_code, idx),
                "title": title,
                "domain": domain,
                "criticality": "High" if idx <= 3 else "Medium",
                "description": description,
                "policy_refs": [pol_id],
                "procedures": [
                    {
                        "id": proc_id,
                        "title": f"Execute — {title}",
                        "owner": "Control Owner",
                        "frequency": "Quarterly" if idx % 2 else "Semi-Annual",
                        "steps": [
                            f"Identify in-scope applications and environments for {title}.",
                            "Collect configuration or attestation artefacts from system owners.",
                            "Validate evidence against policy baseline and record exceptions.",
                            "Submit evidence package for auditor review and track remediation.",
                        ],
                    }
                ],
                "evidence_requirements": [
                    {
                        "id": _evr_id(fw_code, idx, 1),
                        "title": f"{title} — primary attestation",
                        "artefact_type": "Attestation / Configuration Export",
                        "frequency": "Quarterly",
                        "collection_method": "Manual Upload",
                        "retention_period": "12 months",
                    },
                    {
                        "id": _evr_id(fw_code, idx, 2),
                        "title": f"{title} — supporting review log",
                        "artefact_type": "Review Log / Scan Report",
                        "frequency": "Quarterly",
                        "collection_method": "Scheduler Pull",
                        "retention_period": "12 months",
                    },
                ],
            }
        )

    return {
        "framework": {
            "id": spec["id"],
            "code": fw_code,
            "name": spec["name"],
            "display_name": spec["display_name"],
            "category": spec["category"],
            "regulator": spec["regulator"],
            "version": spec["version"],
            "description": spec["description"],
            "source": "file_catalog",
            "phase": 1,
        },
        "policies": policies,
        "controls": controls,
    }


def main() -> None:
    FW_DIR.mkdir(parents=True, exist_ok=True)
    catalog_entries = []
    for spec in FRAMEWORKS:
        doc = build_framework_doc(spec)
        path = FW_DIR / f"{spec['id']}.yaml"
        path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
        catalog_entries.append(
            {
                "id": spec["id"],
                "code": spec["code"],
                "name": spec["name"],
                "display_name": spec["display_name"],
                "category": spec["category"],
                "file": f"frameworks/{spec['id']}.yaml",
                "control_count": len(doc["controls"]),
                "policy_count": len(doc["policies"]),
            }
        )

    catalog = {
        "catalog_version": "2026.1",
        "source_type": "file",
        "description": "Phase-1 Framework Control Master — hardcoded catalogue replaceable by DB/Excel/SharePoint/upload.",
        "frameworks": catalog_entries,
        "aliases": {
            "PCI": "pci_dss",
            "PCI DSS": "pci_dss",
            "C-SITE": "csite",
            "CSITE": "csite",
            "OS Baseline": "os_baseline",
            "OS Baselining": "os_baseline",
            "Middleware Baseline": "middleware_baseline",
            "Middleware Baselining": "middleware_baseline",
            "Database Baseline": "database_baseline",
            "DB Baseline": "database_baseline",
            "DB Baselining": "database_baseline",
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "catalog.yaml").write_text(
        yaml.safe_dump(catalog, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(f"Wrote {len(catalog_entries)} frameworks to {OUT}")


if __name__ == "__main__":
    main()
