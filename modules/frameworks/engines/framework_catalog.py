"""
Enterprise framework catalog: controls with 2+ evidences each.
Single source for realistic banking governance demo data.
"""

from __future__ import annotations

import hashlib

APPLICATIONS = [
    "Net Banking",
    "Mobile Banking",
    "UPI",
    "Payments",
    "Treasury",
    "Loan System",
]

SERVERS = [
    "NETBANKING_PROD",
    "UPI_SWITCH_CLUSTER",
    "MOBILE_BANKING_API",
    "CBS_ORACLE_CLUSTER",
    "INTERNET_BANKING_DR",
    "CARD_PAYMENT_GATEWAY",
    "NGINX_EDGE_DMZ_01",
    "SIEM_COLLECTOR_HQ",
    "TREASURY_FX_CORE",
    "LOAN_ORIGINATION_APP",
]

OWNERS = [
    "R. Mehta (App Owner)",
    "A. Sharma (App Owner)",
    "P. Iyer (App Owner)",
    "K. Reddy (App Owner)",
    "S. Banerjee (App Owner)",
    "M. Joshi (App Owner)",
]

REVIEWERS = [
    "S. Nair (Auditor)",
    "A. Verma (Auditor)",
    "V. Desai (Compliance Officer)",
    "N. Kapoor (Lead Auditor)",
]

SOURCES = [
    "Manual Upload",
    "SharePoint Library",
    "ServiceNow GRC",
    "Scheduler Pull",
    "SIEM Export",
    "CMDB Agent",
]

ENVIRONMENTS = ["Production", "DR", "UAT", "SOC Production"]

EVIDENCE_STATUSES = ["Current", "Current", "Current", "Due for Refresh", "Expired"]
AUDIT_STATUSES = ["Approved", "Under Review", "Submitted", "Pending", "Rejected"]


def _stable_pick(seed: str, options: list) -> str:
    idx = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(options)
    return options[idx]


def _make_evidence(
    fw_code: str,
    ctrl_idx: int,
    ev_idx: int,
    control: str,
    evidence_name: str,
    application: str,
    server: str,
    filename: str,
    comments: str,
    upload_ts: str,
    expiry: str,
    uploaded_by: str,
    reviewer: str,
    evidence_status: str,
    audit_status: str,
    source: str,
    environment: str,
) -> dict:
    eid = f"EVD-{fw_code}-{ctrl_idx:02d}{ev_idx:01d}"
    return {
        "evidence_id": eid,
        "evidence_name": evidence_name,
        "mock_file": filename,
        "application_name": application,
        "application": application,
        "uploaded_by": uploaded_by,
        "upload_timestamp": upload_ts,
        "evidence_status": evidence_status,
        "audit_status": audit_status,
        "reviewer": reviewer,
        "comments": comments,
        "expiry_date": expiry,
        "evidence_source": source,
        "server_name": server,
        "environment": environment,
        "region": _stable_pick(eid, ["North", "South", "West", "East", "Central"]),
        "evidence_version": f"v{1 + (ctrl_idx % 3)}.{ev_idx}",
    }


def _control(
    fw_code: str,
    ctrl_idx: int,
    title: str,
    evidence_specs: list[tuple],
) -> dict:
    evidences = []
    for ev_idx, spec in enumerate(evidence_specs, start=1):
        (
            ev_name,
            app,
            server,
            filename,
            comments,
            upload_ts,
            expiry,
            owner,
            reviewer,
            ev_status,
            audit_status,
            source,
            env,
        ) = spec
        evidences.append(
            _make_evidence(
                fw_code,
                ctrl_idx,
                ev_idx,
                title,
                ev_name,
                app,
                server,
                filename,
                comments,
                upload_ts,
                expiry,
                owner,
                reviewer,
                ev_status,
                audit_status,
                source,
                env,
            )
        )
    return {
        "control": title,
        "control_id": f"{fw_code}-C{ctrl_idx:02d}",
        "control_description": f"Enterprise control requirement: {title}. Evidence must demonstrate production compliance with banking governance baseline.",
        "evidences": evidences,
        "primary_evidence": evidences[0]["evidence_name"],
    }


def _pci_catalog() -> list[dict]:
    specs = [
        (
            "Req 3.4 — Encryption at Rest",
            [
                ("Database TDE attestation report", "Net Banking", "CBS_ORACLE_CLUSTER", "PCI_DB_TDE_ATTESTATION_2026.pdf", "CDE data-at-rest validated for CBS Oracle cluster.", "2026-04-10 11:20 UTC", "2026-10-10", OWNERS[0], REVIEWERS[0], "Current", "Approved", "SharePoint Library", "Production"),
                ("Key management procedure sign-off", "Net Banking", "CBS_ORACLE_CLUSTER", "PCI_KMS_PROCEDURE_SIGNOFF_Q1.pdf", "HSM key custodian dual-control attested.", "2026-04-11 14:05 UTC", "2026-09-30", OWNERS[0], REVIEWERS[1], "Current", "Approved", "ServiceNow GRC", "Production"),
            ],
        ),
        (
            "Req 4.1 — Encryption in Transit",
            [
                ("TLS 1.2+ cipher suite export", "Net Banking", "NETBANKING_PROD", "PCI_TLS_CERTIFICATE_2026.pdf", "Internet banking edge TLS configuration within PCI scope.", "2026-04-08 16:40 UTC", "2026-08-08", OWNERS[0], REVIEWERS[0], "Current", "Under Review", "Manual Upload", "Production"),
                ("Certificate inventory & expiry tracker", "Payments", "CARD_PAYMENT_GATEWAY", "PROD_TLS_INVENTORY_MAY2026.xlsx", "Payment gateway certificates mapped to owners.", "2026-04-09 10:00 UTC", "2026-07-15", OWNERS[3], REVIEWERS[2], "Current", "Submitted", "Scheduler Pull", "Production"),
            ],
        ),
        (
            "Req 7.2 — Access Control Review",
            [
                ("Quarterly CDE access recertification", "UPI", "UPI_SWITCH_CLUSTER", "CDE_ACCESS_RECERT_Q1_2026.xlsx", "All privileged IDs recertified; 2 exceptions remediated.", "2026-03-28 13:22 UTC", "2026-06-28", OWNERS[2], REVIEWERS[1], "Current", "Approved", "ServiceNow GRC", "Production"),
                ("SoD conflict remediation evidence", "Payments", "CARD_PAYMENT_GATEWAY", "SOD_CONFLICT_CLOSURE_MAR2026.pdf", "Segregation of duties violations closed within SLA.", "2026-03-30 09:45 UTC", "2026-09-30", OWNERS[3], REVIEWERS[0], "Current", "Approved", "SharePoint Library", "Production"),
            ],
        ),
        (
            "Req 8.3 — MFA for CDE Access",
            [
                ("IAM MFA enforcement screenshot pack", "Payments", "CARD_PAYMENT_GATEWAY", "IAM_MFA_ENFORCEMENT_PROD.png", "100% MFA for CDE jump hosts verified.", "2026-04-14 08:30 UTC", "2026-10-14", OWNERS[3], REVIEWERS[0], "Current", "Approved", "Manual Upload", "Production"),
                ("Privileged access session logs sample", "Net Banking", "NETBANKING_PROD", "PRIV_SESSION_LOG_SAMPLE_MAY.csv", "Sample PAM sessions for Q1 audit window.", "2026-04-15 17:00 UTC", "2026-08-01", OWNERS[0], REVIEWERS[3], "Current", "Under Review", "SIEM Export", "SOC Production"),
            ],
        ),
        (
            "Req 1.2 — Network Segmentation",
            [
                ("CDE firewall rule export", "Payments", "CARD_PAYMENT_GATEWAY", "PROD_FIREWALL_CONFIG_AUDIT.pdf", "Firewall policy review — missing Q1 CDE segment noted.", "2026-04-05 12:00 UTC", "2026-07-05", OWNERS[3], REVIEWERS[0], "Due for Refresh", "Rejected", "Manual Upload", "Production"),
                ("Network segmentation diagram v4.2", "Net Banking", "INTERNET_BANKING_DR", "NETWORK_SEG_DIAGRAM_V4_2.pdf", "Updated DMZ segmentation for DR site.", "2026-04-06 11:15 UTC", "2026-12-31", OWNERS[0], REVIEWERS[1], "Current", "Submitted", "SharePoint Library", "DR"),
            ],
        ),
        (
            "Req 10.2 — Audit Trail Integrity",
            [
                ("Centralized audit log export", "UPI", "UPI_SWITCH_CLUSTER", "CENTRAL_AUDIT_LOG_EXPORT_MAY.zip", "Immutable log chain hash verified for UPI switch.", "2026-04-16 06:50 UTC", "2026-09-16", OWNERS[2], REVIEWERS[1], "Current", "Approved", "SIEM Export", "Production"),
                ("Log retention policy attestation", "Mobile Banking", "MOBILE_BANKING_API", "LOG_RETENTION_ATTESTATION_2026.pdf", "365-day retention meets policy baseline.", "2026-04-17 15:30 UTC", "2026-11-17", OWNERS[1], REVIEWERS[2], "Current", "Approved", "ServiceNow GRC", "Production"),
            ],
        ),
        (
            "Req 10.6 — Log Review",
            [
                ("SIEM daily alert review log", "Mobile Banking", "MOBILE_BANKING_API", "SIEM_DAILY_REVIEW_LOG_APR.csv", "Daily SOC review sign-offs for mobile channel.", "2026-04-11 07:00 UTC", "2026-08-11", OWNERS[1], REVIEWERS[0], "Current", "Submitted", "SIEM Export", "SOC Production"),
                ("Escalation closure tracker", "CSITE", "SIEM_COLLECTOR_HQ", "SOC_ESCALATION_CLOSURE_Q1.xlsx", "P1/P2 escalations closed within TAT.", "2026-04-12 18:20 UTC", "2026-10-12", OWNERS[1], REVIEWERS[3], "Current", "Under Review", "Scheduler Pull", "SOC Production"),
            ],
        ),
        (
            "Req 11.3 — External VAPT",
            [
                ("Annual PCI ASV scan report", "Net Banking", "NETBANKING_PROD", "PCI_VAPT_REPORT_Q1_2026.pdf", "ASV scan — no critical findings; 2 medium in remediation.", "2026-03-20 10:00 UTC", "2026-09-20", OWNERS[0], REVIEWERS[0], "Current", "Approved", "Manual Upload", "Production"),
                ("Remediation validation letter", "Net Banking", "NETBANKING_PROD", "VAPT_REMEDIATION_VALIDATION_MAR.pdf", "Medium findings retest passed.", "2026-03-25 14:30 UTC", "2026-09-25", OWNERS[0], REVIEWERS[1], "Current", "Approved", "SharePoint Library", "Production"),
            ],
        ),
        (
            "Req 3.6 — Cryptographic Key Management",
            [
                ("HSM key rotation certificate", "Payments", "CARD_PAYMENT_GATEWAY", "HSM_KEY_ROTATION_CERT_2026.pdf", "Annual rotation completed on production HSM.", "2026-04-01 09:00 UTC", "2027-04-01", OWNERS[3], REVIEWERS[0], "Current", "Approved", "ServiceNow GRC", "Production"),
                ("Key ceremony attendance record", "Treasury", "TREASURY_FX_CORE", "KEY_CEREMONY_ATTENDANCE_FEB.pdf", "Dual control key ceremony documented.", "2026-02-18 11:00 UTC", "2027-02-18", OWNERS[4], REVIEWERS[2], "Current", "Approved", "Manual Upload", "Production"),
            ],
        ),
        (
            "Req 12.10 — Incident Response Test",
            [
                ("IR tabletop exercise attendance", "Net Banking", "INTERNET_BANKING_DR", "IR_TABLETOP_ATTENDANCE_Q1.pdf", "Cardholder data breach scenario exercised.", "2026-03-15 13:00 UTC", "2026-12-15", OWNERS[0], REVIEWERS[1], "Current", "Approved", "SharePoint Library", "DR"),
                ("Lessons learned action tracker", "Net Banking", "NETBANKING_PROD", "IR_LESSONS_LEARNED_TRACKER.xlsx", "3 actions closed; 1 pending patch window.", "2026-03-18 16:45 UTC", "2026-09-18", OWNERS[0], REVIEWERS[3], "Current", "Under Review", "ServiceNow GRC", "Production"),
            ],
        ),
        (
            "Req 2.2 — Secure Config Standards",
            [
                ("CDE baseline configuration benchmark", "Payments", "CARD_PAYMENT_GATEWAY", "CDE_BASELINE_BENCHMARK_MAY.pdf", "CIS benchmark 85% compliant; gaps tracked.", "2026-04-13 10:30 UTC", "2026-10-13", OWNERS[3], REVIEWERS[0], "Current", "Submitted", "CMDB Agent", "Production"),
                ("Configuration drift report", "UPI", "UPI_SWITCH_CLUSTER", "CONFIG_DRIFT_REPORT_WEEK19.pdf", "2 drift items auto-remediated via Ansible.", "2026-04-14 06:00 UTC", "2026-07-14", OWNERS[2], REVIEWERS[1], "Current", "Pending", "Scheduler Pull", "Production"),
            ],
        ),
        (
            "Req 5.2 — Malware Protection",
            [
                ("AV/EDR coverage report — CDE", "Mobile Banking", "MOBILE_BANKING_API", "EDR_COVERAGE_CDE_MAY2026.pdf", "99.2% agents reporting on CDE workloads.", "2026-04-10 08:00 UTC", "2026-08-10", OWNERS[1], REVIEWERS[0], "Current", "Approved", "SIEM Export", "Production"),
                ("Malware incident nil attestation", "Net Banking", "NETBANKING_PROD", "MALWARE_NIL_ATTESTATION_Q1.pdf", "No malware incidents in CDE for Q1.", "2026-04-11 09:30 UTC", "2026-10-11", OWNERS[0], REVIEWERS[2], "Current", "Approved", "Manual Upload", "Production"),
            ],
        ),
        (
            "Req 6.4 — Change Control Process",
            [
                ("Change advisory board minutes", "Net Banking", "NETBANKING_PROD", "PCI_CAB_MINUTES_MAY2026.pdf", "All CDE changes approved via CAB.", "2026-05-02 11:00 UTC", "2026-11-02", OWNERS[0], REVIEWERS[1], "Current", "Under Review", "ServiceNow GRC", "Production"),
                ("Emergency change post-implementation review", "Payments", "CARD_PAYMENT_GATEWAY", "EMERG_CHANGE_PIR_Q1.pdf", "3 emergency changes reviewed within 24h.", "2026-05-03 15:30 UTC", "2026-11-03", OWNERS[3], REVIEWERS[0], "Current", "Submitted", "SharePoint Library", "Production"),
            ],
        ),
        (
            "Req 9.9 — POI Device Security",
            [
                ("POI device inventory attestation", "Payments", "CARD_PAYMENT_GATEWAY", "POI_DEVICE_INVENTORY_2026.xlsx", "All POI devices tracked in CMDB.", "2026-05-05 09:00 UTC", "2026-11-05", OWNERS[3], REVIEWERS[0], "Current", "Approved", "CMDB Agent", "Production"),
                ("Device firmware compliance report", "UPI", "UPI_SWITCH_CLUSTER", "POI_FIRMWARE_COMPLIANCE_MAY.pdf", "Firmware versions within approved baseline.", "2026-05-06 10:15 UTC", "2026-11-06", OWNERS[2], REVIEWERS[1], "Current", "Pending", "Manual Upload", "Production"),
            ],
        ),
        (
            "Req 11.5 — Internal Vulnerability Scan",
            [
                ("Quarterly internal VA scan", "Mobile Banking", "MOBILE_BANKING_API", "INTERNAL_VA_SCAN_Q2_2026.pdf", "Internal scan — 0 critical, 4 medium findings.", "2026-05-08 14:00 UTC", "2026-11-08", OWNERS[1], REVIEWERS[0], "Current", "Under Review", "Scheduler Pull", "Production"),
                ("VA remediation tracker", "Net Banking", "NETBANKING_PROD", "VA_REMEDIATION_TRACKER_MAY.xlsx", "Medium findings on track for June closure.", "2026-05-09 16:45 UTC", "2026-11-09", OWNERS[0], REVIEWERS[3], "Due for Refresh", "Submitted", "ServiceNow GRC", "Production"),
            ],
        ),
        (
            "Req 12.8 — Third-Party Service Provider",
            [
                ("TPSP due diligence assessment", "Treasury", "TREASURY_FX_CORE", "TPSP_DUE_DILIGENCE_2026.pdf", "Annual TPSP assessment for payment processor.", "2026-05-10 11:30 UTC", "2026-11-10", OWNERS[4], REVIEWERS[2], "Current", "Approved", "SharePoint Library", "Production"),
                ("TPSP contract PCI compliance clause", "Payments", "CARD_PAYMENT_GATEWAY", "TPSP_CONTRACT_PCI_CLAUSE.pdf", "Contractual PCI obligations verified.", "2026-05-11 13:00 UTC", "2026-11-11", OWNERS[3], REVIEWERS[0], "Current", "Approved", "Manual Upload", "Production"),
            ],
        ),
        (
            "Req 3.1 — Data Retention & Disposal",
            [
                ("Cardholder data retention policy", "Net Banking", "CBS_ORACLE_CLUSTER", "CHD_RETENTION_POLICY_V3.pdf", "Retention schedule aligned with RBI guidelines.", "2026-05-12 08:45 UTC", "2026-11-12", OWNERS[0], REVIEWERS[1], "Current", "Approved", "ServiceNow GRC", "Production"),
                ("Secure disposal certificate", "Loan System", "LOAN_ORIGINATION_APP", "SECURE_DISPOSAL_CERT_MAY.pdf", "Media destruction for decommissioned drives.", "2026-05-13 10:00 UTC", "2026-11-13", OWNERS[5], REVIEWERS[2], "Expired", "Rejected", "Manual Upload", "Production"),
            ],
        ),
    ]
    return [_control("PCI", i + 1, s[0], s[1]) for i, s in enumerate(specs)]


def _generic_catalog(fw_code: str, fw_name: str, control_templates: list[tuple]) -> list[dict]:
    """Build controls from (title, ev1_name, ev2_name, app_idx, server_idx) templates."""
    controls = []
    for i, tpl in enumerate(control_templates, start=1):
        title, ev1, ev2, app_i, srv_i = tpl
        app = APPLICATIONS[app_i % len(APPLICATIONS)]
        app2 = APPLICATIONS[(app_i + 1) % len(APPLICATIONS)]
        srv = SERVERS[srv_i % len(SERVERS)]
        srv2 = SERVERS[(srv_i + 2) % len(SERVERS)]
        owner = OWNERS[app_i % len(OWNERS)]
        reviewer = REVIEWERS[i % len(REVIEWERS)]
        prefix = fw_code.replace(" ", "_").upper()
        month = "05" if i % 2 else "04"
        specs = [
            (
                ev1,
                app,
                srv,
                f"{prefix}_{ev1[:20].replace(' ', '_').upper()}_{month}2026.pdf",
                f"Primary artefact for {title} — production attestation complete.",
                f"2026-{month}-{10 + i:02d} 10:30 UTC",
                f"2026-{int(month)+6:02d}-15",
                owner,
                reviewer,
                "Current" if i % 5 else "Due for Refresh",
                AUDIT_STATUSES[i % len(AUDIT_STATUSES)],
                SOURCES[i % len(SOURCES)],
                ENVIRONMENTS[i % len(ENVIRONMENTS)],
            ),
            (
                ev2,
                app2,
                srv2,
                f"{prefix}_{ev2[:18].replace(' ', '_').upper()}_Q1.xlsx",
                f"Supporting evidence — cross-check with SOC monitoring.",
                f"2026-{month}-{12 + i:02d} 14:00 UTC",
                f"2026-11-30",
                OWNERS[(app_i + 1) % len(OWNERS)],
                REVIEWERS[(i + 1) % len(REVIEWERS)],
                "Expired" if i % 11 == 0 else "Current",
                "Pending" if i % 7 == 0 else "Under Review",
                SOURCES[(i + 2) % len(SOURCES)],
                ENVIRONMENTS[(i + 1) % len(ENVIRONMENTS)],
            ),
        ]
        if i % 3 == 0:
            specs.append(
                (
                    f"{ev2} — supplemental scan output",
                    app,
                    srv,
                    f"{prefix}_SUPPLEMENTAL_SCAN_{i:02d}.csv",
                    "Automated compliance scan output attached for auditor walkthrough.",
                    f"2026-05-{8 + (i % 20):02d} 08:15 UTC",
                    "2026-12-31",
                    owner,
                    reviewer,
                    "Current",
                    "Submitted",
                    "Scheduler Pull",
                    "Production",
                )
            )
        controls.append(_control(fw_code[:3].upper().replace(" ", ""), i, title, specs))
    return controls


def _dpsc_catalog() -> list[dict]:
    tpl = [
        ("API Security Gateway Hardening", "API gateway WAF rule export", "OAuth token validation test results", 3, 0),
        ("UPI Channel Encryption", "UPI TLS configuration evidence", "NPCI encryption compliance letter", 2, 1),
        ("Fraud Monitoring Coverage", "Fraud rules effectiveness dashboard", "False positive tuning report", 2, 4),
        ("Card Tokenization Controls", "Token vault architecture diagram", "Tokenization penetration test summary", 3, 5),
        ("Real-time Transaction Screening", "AML screening latency metrics", "Screening rule change log", 0, 3),
        ("Digital Payment API Rate Limiting", "Rate limit policy configuration", "DDoS simulation test report", 1, 0),
        ("Customer Device Binding", "Device fingerprint enrollment stats", "Binding failure analysis Q1", 1, 2),
        ("Settlement Reconciliation", "Settlement mismatch register", "Auto-reconciliation job logs", 4, 3),
        ("Third-party PSP Integration", "PSP security assessment summary", "API key rotation evidence", 3, 5),
        ("Regulatory Reporting — RBI DPSC", "RBI DPSC self-assessment workbook", "Gap remediation tracker", 0, 1),
        ("Payment Exception Handling", "Exception queue aging report", "Manual override approval log", 2, 4),
        ("Cryptographic Key Lifecycle — Payments", "Payment HSM inventory", "Key compromise drill record", 3, 5),
        ("API Gateway Rate Limiting — Treasury", "API gateway throttle config", "Burst load test results", 4, 8),
        ("SOC Monitoring Integration", "SOC alert correlation rules", "Use-case effectiveness report", 1, 7),
        ("Mobile Banking Session Security", "Session timeout configuration", "Concurrent session audit", 1, 2),
        ("Card Switch Failover Testing", "Switch failover drill log", "DR switchover attestation", 3, 5),
        ("Oracle DB Audit Trail Review", "DB audit log export", "Privileged SQL review sample", 0, 4),
        ("Cross-border Data Transfer Log", "Cross-border transfer register", "DPA compliance attestation", 1, 3),
        ("Biometric Data Minimization", "Biometric storage audit", "Consent withdrawal workflow proof", 2, 2),
    ]
    return _generic_catalog("DPSC", "DPSC", tpl)


def _os_catalog() -> list[dict]:
    tpl = [
        ("Linux Server Hardening — CIS L2", "CIS benchmark scan results", "Remediation closure evidence", 0, 0),
        ("SSH Access Restrictions", "SSHd_config production export", "Root login disable verification", 1, 1),
        ("Endpoint AV Coverage", "AV agent deployment report", "Signature update compliance", 1, 2),
        ("Patch Compliance — Critical", "WSUS/SCCM patch report", "Emergency patch bulletin closure", 0, 3),
        ("Privileged Command Logging", "sudoers audit log sample", "Command allow-list review", 2, 4),
        ("OS Inventory & CMDB Accuracy", "CMDB reconciliation report", "Unauthorized asset investigation", 4, 5),
        ("Container Host Baseline", "CIS Docker benchmark", "Image vulnerability scan", 1, 6),
        ("Time Synchronization (NTP)", "NTP stratum configuration", "Clock drift monitoring evidence", 3, 0),
        ("File Integrity Monitoring", "FIM alert summary", "Critical file change approvals", 0, 7),
        ("Unused Service Disablement", "Open port scan results", "Service decommission records", 2, 1),
        ("OS Access Recertification", "Quarterly OS access review", "Terminated user cleanup proof", 5, 2),
        ("Security Kernel Parameters", "sysctl production baseline", "Kernel param drift detection", 4, 3),
        ("API Gateway OS Hardening", "API gateway OS baseline scan", "Middleware patch compliance", 3, 8),
        ("SOC Collector Host Baseline", "SIEM collector CIS scan", "Log forwarder hardening proof", 0, 7),
        ("Container Runtime Security", "Runtime security policy export", "K8s pod security standards", 1, 6),
        ("Middleware Patch Cadence", "Middleware patch report", "Zero-day emergency patch log", 3, 1),
        ("Production Jump Host Hardening", "Jump host config export", "Session recording attestation", 2, 0),
        ("AIX Legacy Server Baseline", "AIX security baseline scan", "Extended support risk register", 4, 5),
    ]
    return _generic_catalog("OSB", "OS Baselining", tpl)


def _db_catalog() -> list[dict]:
    tpl = [
        ("Oracle Password Rotation — 90 day", "Password rotation compliance report", "Break-glass account review", 0, 4),
        ("Database Audit Logging", "Unified DB audit trail export", "Audit log integrity hash proof", 0, 4),
        ("Backup & Recovery Validation", "Backup success rate dashboard", "Restore test attestation — Q1", 5, 4),
        ("Transparent Data Encryption", "TDE status — production databases", "Key escrow verification", 0, 4),
        ("Least Privilege — DB Accounts", "DB role entitlement review", "Excess privilege remediation", 4, 4),
        ("High Availability Configuration", "RAC/DataGuard config export", "Failover drill results", 0, 9),
        ("Sensitive Data Masking — Non-Prod", "Masking rule catalog", "UAT data scan for PAN detection", 2, 4),
        ("Database Vulnerability Scan", "DB VA scan report", "Critical patch application proof", 5, 4),
        ("Connection Pool Security", "Connection string review", "TLS-in-transit for JDBC evidence", 3, 4),
        ("Schema Change Management", "DB change ticket sample set", "Emergency change post-review", 0, 4),
        ("Retention & Archival Policy", "Archive job completion log", "Legal hold procedure attestation", 5, 4),
        ("DB Activity Monitoring", "DAM alert correlation report", "Privileged session replay sample", 0, 4),
        ("CBS Oracle Cluster Hardening", "CBS hardening checklist", "Oracle security patch report", 0, 4),
        ("Treasury DB Encryption Review", "Treasury TDE status", "FX core DB access review", 4, 9),
        ("Loan System DB Audit", "Loan DB audit export", "Origination schema change log", 5, 9),
        ("API Gateway DB Connection Pool", "Connection pool security review", "Pool credential rotation proof", 3, 4),
        ("Middleware DB Link Security", "DB link inventory", "Cross-schema access review", 2, 4),
        ("PostgreSQL Analytics DB Hardening", "PG security config export", "Row-level security validation", 3, 4),
        ("MongoDB NoSQL Audit Trail", "NoSQL audit log sample", "Encryption-at-rest proof", 1, 4),
        ("DB Connection Encryption Review", "JDBC TLS enforcement report", "Certificate trust store audit", 0, 4),
    ]
    return _generic_catalog("DBB", "DB Baselining", tpl)


def _nginx_catalog() -> list[dict]:
    tpl = [
        ("TLS 1.2+ on Internet Banking Edge", "Nginx SSL configuration export", "SSL Labs scan grade evidence", 0, 6),
        ("HTTP to HTTPS Redirect", "Redirect rule configuration", "HSTS header validation", 0, 6),
        ("Security Headers — CSP/HSTS", "Response header capture", "CSP violation report summary", 1, 6),
        ("WAF Rule Effectiveness", "WAF blocked attack statistics", "False positive tuning log", 3, 6),
        ("Rate Limiting & DDoS Mitigation", "limit_req zone configuration", "Stress test results — edge", 0, 6),
        ("Certificate Lifecycle Management", "Cert expiry dashboard", "Automated renewal job logs", 3, 5),
        ("Upstream Connection Security", "Proxy SSL to origin config", "mTLS certificate exchange proof", 1, 6),
        ("Access Log Retention", "Nginx access log archive proof", "Log integrity checksum report", 0, 7),
        ("ModSecurity CRS Version", "CRS version attestation", "Custom rule change approval", 3, 6),
        ("Load Balancer Health Checks", "Health check configuration", "Failover event postmortem", 0, 6),
        ("Static Content Integrity", "SRI hash implementation proof", "Third-party script inventory", 1, 0),
        ("Error Page Information Leakage", "Custom error page review", "Pen test finding closure — verbose errors", 0, 6),
        ("Net Banking Edge WAF Rules", "Net banking WAF policy export", "Blocked attack trend report", 0, 6),
        ("Mobile API Gateway TLS", "Mobile API TLS config", "Certificate pinning validation", 1, 6),
        ("UPI Switch Proxy Config", "UPI proxy nginx config", "Upstream health check logs", 2, 6),
        ("Internet Banking DR Edge", "DR edge nginx baseline", "DR failover traffic test", 0, 6),
        ("Card Gateway DMZ Hardening", "DMZ nginx security headers", "Pen test remediation closure", 3, 5),
        ("OCSP Stapling Validation", "OCSP stapling test output", "Certificate chain verification log", 0, 6),
        ("HTTP/2 & HTTP/3 Security Review", "Protocol downgrade test results", "ALPN configuration export", 1, 6),
    ]
    return _generic_catalog("NGX", "Nginx Baselining", tpl)


def _csite_catalog() -> list[dict]:
    tpl = [
        ("SIEM Alert Monitoring & Triage", "SIEM alert volume dashboard", "Alert triage SLA report", 0, 7),
        ("EDR Threat Detection Coverage", "EDR agent deployment report", "Threat isolation drill results", 1, 2),
        ("SOC 24x7 Monitoring Coverage", "SOC shift handover log", "Coverage gap analysis — nil", 1, 7),
        ("Threat Intelligence Integration", "TI feed ingestion proof", "IOC match closure report", 0, 7),
        ("Incident Response SLA", "P1 incident MTTR dashboard", "Major incident postmortem Q1", 1, 7),
        ("Phishing Simulation Program", "Employee click-rate report", "Repeat offender coaching log", 1, 1),
        ("Privileged Access Monitoring", "PAM session recording sample", "High-risk command alert review", 3, 0),
        ("Cloud Workload Protection", "CWPP policy compliance", "Container runtime alert summary", 1, 6),
        ("DLP Policy Effectiveness", "DLP incident register", "False positive whitelist review", 0, 3),
        ("Security Awareness Training", "Training completion by department", "Role-based module attestation", 5, 1),
        ("Vulnerability Management SLA", "Critical vuln aging report", "Exception risk acceptance form", 0, 0),
        ("Red Team Exercise Outcomes", "Red team findings register", "Remediation validation evidence", 0, 7),
        ("Net Banking SOC Integration", "Net banking SIEM use-cases", "Alert triage SLA report", 0, 7),
        ("Treasury Monitoring Coverage", "Treasury SOC monitoring proof", "FX transaction anomaly review", 4, 7),
        ("API Gateway Threat Detection", "API threat detection rules", "API abuse incident register", 3, 8),
        ("Enterprise GRC Dashboard", "GRC KPI export", "Board risk committee pack", 0, 7),
        ("Third-Party Risk Assessment", "Vendor risk assessment summary", "Critical vendor remediation tracker", 5, 1),
        ("SOAR Playbook Execution Log", "SOAR automation run summary", "Playbook failure remediation", 0, 7),
        ("Threat Hunt Campaign Results", "Proactive hunt findings register", "Hunt hypothesis closure evidence", 1, 7),
    ]
    return _generic_catalog("CSI", "CSITE", tpl)


def _appsec_catalog() -> list[dict]:
    tpl = [
        ("SAST — Static Application Security Testing", "SAST scan report — critical apps", "SAST finding remediation tracker", 0, 0),
        ("DAST — Dynamic Application Security Testing", "DAST scan results Q2", "DAST retest validation letter", 1, 2),
        ("Software Dependency Scanning", "SCA dependency vulnerability report", "Critical CVE remediation proof", 1, 0),
        ("Secrets Scanning — Source Repositories", "Git secrets scan output", "Secret rotation attestation", 3, 8),
        ("API Security Testing", "API security assessment report", "OAuth scope validation evidence", 2, 1),
        ("Secure Code Review Evidence", "Peer review sign-off samples", "Secure coding checklist closure", 0, 0),
        ("Mobile App Security Testing", "Mobile SAST/DAST combined report", "Certificate pinning validation", 1, 2),
        ("Container Image Vulnerability Scan", "Image scan CI pipeline output", "Base image hardening proof", 1, 6),
        ("Web Application Firewall Rules", "WAF rule effectiveness report", "False positive tuning log", 3, 6),
        ("DevSecOps Pipeline Gates", "CI/CD security gate configuration", "Failed build remediation log", 0, 0),
        ("Third-Party Library Allow-list", "Approved library inventory", "Deprecated library removal proof", 4, 3),
        ("API Rate Limiting Security", "Rate limit abuse test results", "Burst load simulation report", 2, 1),
        ("Input Validation Testing", "Fuzz testing output summary", "Injection test closure evidence", 0, 0),
        ("Session Management Security", "Session fixation test results", "Token rotation configuration", 1, 2),
        ("Security Champions Program", "Champion training attendance", "Champion-led review samples", 5, 1),
        ("Threat Modeling Documentation", "STRIDE threat model pack", "Mitigation implementation proof", 3, 8),
        ("Production Release Security Sign-off", "Release security checklist", "Emergency release PIR samples", 0, 0),
        ("SBOM Generation & Verification", "SBOM artefact from CI pipeline", "SBOM drift detection report", 2, 8),
        ("API OAuth Scope Validation", "OAuth scope matrix review", "Excessive scope remediation log", 3, 1),
        ("Business Logic Flaw Testing", "Logic flaw test cases", "Transaction abuse test results", 0, 0),
        ("Secure Deserialization Review", "Deserialization scan output", "Library upgrade proof", 4, 3),
    ]
    return _generic_catalog("APS", "AppSec", tpl)


def _vapt_catalog() -> list[dict]:
    tpl = [
        ("Internal Vulnerability Assessment", "Quarterly internal VA scan", "VA remediation tracker", 0, 0),
        ("External Vulnerability Assessment", "External VA scan report", "Internet-facing asset scope proof", 0, 6),
        ("Penetration Testing — Internet Banking", "Pen test executive summary", "Critical finding remediation proof", 0, 0),
        ("Penetration Testing — Mobile Banking", "Mobile pen test report", "Retest validation letter", 1, 2),
        ("Penetration Testing — Payment Gateway", "Payment gateway pen test", "PCI ASV alignment attestation", 3, 5),
        ("Remediation Evidence — Critical Findings", "Critical vuln closure tracker", "Retest scan clean report", 0, 0),
        ("Remediation Evidence — High Findings", "High severity closure log", "Risk acceptance forms", 2, 4),
        ("Closure Validation — Pen Test", "Pen test closure validation", "Auditor sign-off letter", 0, 0),
        ("Red Team Exercise Follow-up", "Red team finding register", "Purple team validation session", 0, 7),
        ("Wireless Network VA", "Wireless VA scan output", "Guest network segmentation proof", 1, 1),
        ("Database Vulnerability Scan", "DB VA scan report", "DB patch application proof", 0, 4),
        ("API Penetration Testing", "API pen test findings", "API auth bypass remediation", 2, 1),
        ("Social Engineering Test Results", "Phishing simulation outcomes", "Repeat offender coaching", 1, 1),
        ("Cloud Infrastructure VA", "Cloud VA scan report", "Misconfiguration remediation", 1, 6),
        ("Third-Party VA Evidence", "Vendor VA attestation", "TPSP remediation tracker", 3, 5),
        ("VAPT Scope & Methodology", "VAPT scope document", "Rules of engagement sign-off", 0, 7),
        ("Annual VAPT Program Attestation", "Annual VAPT completion certificate", "Board risk committee briefing", 4, 9),
        ("Active Directory Pen Test", "AD pen test summary", "Kerberoasting remediation proof", 0, 0),
        ("Container Escape Testing", "Container breakout test report", "Runtime isolation validation", 1, 6),
        ("Business Logic Pen Test", "Logic abuse test findings", "Transaction manipulation closure", 2, 1),
    ]
    return _generic_catalog("VAP", "VAPT", tpl)


def _itdrm_catalog() -> list[dict]:
    """IT Disaster Recovery Management — resilience, recovery, and continuity controls."""
    tpl = [
        ("BCM Policy Approved", "Business continuity policy v2026", "Board BCM approval minutes", 0, 0),
        ("BIA Refreshed Annually", "Business Impact Analysis workbook", "Critical app criticality matrix", 4, 9),
        ("RTO/RPO Validation", "RTO/RPO compliance attestation", "Tier-1 application recovery metrics", 0, 0),
        ("Multi-Region DR Replication", "Cross-region replication monitoring", "Replication lag dashboard export", 0, 4),
        ("Recovery Runbook Library", "Production runbook catalog", "Runbook review attestation Q2", 1, 2),
        ("DR Drill — Full Failover", "Full failover drill execution report", "Failover validation signoff", 0, 4),
        ("DR Drill — Tabletop Walkthrough", "Tabletop exercise minutes", "Lessons learned action tracker", 1, 7),
        ("Backup Encryption Validation", "Backup encryption attestation", "Key custodian dual-control proof", 0, 4),
        ("Restore SLA Compliance", "Restore SLA dashboard", "Failed restore incident register", 2, 4),
        ("Critical Vendor Recovery Assessment", "TPSP DR capability questionnaire", "Vendor BCM evidence inventory", 3, 5),
        ("Crisis Communication Plan", "Crisis comm tree document", "War-room activation log", 0, 7),
        ("Disaster Recovery Site Hardening", "DR site security baseline", "DR site access control review", 0, 4),
        ("Cyber Resilience Playbook", "Ransomware recovery playbook", "Cyber drill execution report", 1, 7),
        ("DR Data Integrity Validation", "Post-failover data integrity hash", "Reconciliation completeness proof", 0, 4),
        ("Recovery Testing Automation", "Automated recovery test runs", "Continuous resilience dashboard", 0, 4),
        ("Third-Party DR Dependency Map", "Vendor dependency register", "Single-point-of-failure remediation", 3, 5),
        ("DR Incident Postmortem", "DR event postmortem catalog", "Improvement action closure tracker", 0, 7),
        ("Regulatory DR Reporting", "RBI BCM self-assessment", "Regulator status briefings", 4, 9),
    ]
    return _generic_catalog("DRM", "ITDRM", tpl)


def _itpp_catalog() -> list[dict]:
    """Information Technology Policies & Procedures — operational governance controls."""
    tpl = [
        # Disaster Recovery
        ("DR Plan Exists", "Enterprise DR plan document v2026", "DR plan board approval minutes", 0, 4),
        ("DR Drill Conducted", "Semi-annual DR drill report", "DR drill attendance & signoff sheet", 0, 4),
        ("RPO and RTO Defined", "RPO/RTO matrix — critical apps", "Business impact analysis summary", 4, 9),
        ("DR Failover Validation", "Failover test execution log", "Application recovery validation checklist", 1, 4),
        ("DR Critical Applications Coverage", "Critical app DR coverage register", "Gap remediation tracker — DR scope", 0, 0),
        # Backup Management
        ("Backup Enabled", "Backup job success dashboard", "Backup policy configuration export", 0, 4),
        ("Backup Retention Configured", "Retention policy attestation", "Offsite backup replication proof", 5, 4),
        ("Restore Testing Conducted", "Quarterly restore test report", "Restore validation signoff", 0, 4),
        ("Backup Failure Monitoring", "Failed backup alert register", "Backup escalation closure log", 2, 3),
        # Change Management
        ("CAB Approval", "CAB meeting minutes — Q2", "Change approval workflow sample", 0, 0),
        ("Emergency Change Approval", "Emergency change register", "Post-implementation review samples", 3, 1),
        ("Rollback Plan Exists", "Rollback procedure documentation", "Rollback test evidence", 1, 2),
        ("Change Testing Completed", "UAT signoff for production changes", "Change validation checklist", 0, 0),
        # Incident Management
        ("Incident SLA Defined", "P1/P2 SLA matrix document", "SLA breach tracking dashboard", 1, 7),
        ("P1/P2 Tracking Enabled", "Major incident tracker export", "Escalation matrix attestation", 0, 7),
        ("RCA Completed", "Root cause analysis samples", "RCA closure approval log", 1, 1),
        ("Major Incident Reporting", "Board incident summary pack", "Regulatory incident notification proof", 4, 9),
        # Problem Management
        ("Repeat Incident Detection", "Recurring incident trend report", "Problem record linkage evidence", 1, 7),
        ("Known Error Database Updated", "KEDB review export", "Permanent fix tracking register", 2, 1),
        # Capacity Management
        ("Capacity Plan Exists", "Annual capacity plan document", "Peak load forecast report", 0, 0),
        ("CPU Utilization Monitoring", "CPU threshold alert dashboard", "Saturation risk escalation log", 1, 6),
        ("Storage Forecasting", "Storage growth projection", "Capacity review meeting minutes", 5, 4),
        # Availability Management
        ("Availability SLA Defined", "Uptime SLA matrix — tier-1 apps", "HA architecture documentation", 0, 0),
        ("HA Validation", "HA failover test results", "Redundancy configuration export", 3, 6),
        ("Uptime Reporting", "Monthly uptime dashboard", "Downtime root cause summary", 1, 2),
    ]
    return _generic_catalog("ITP", "ITPP", tpl)


def _soc2_catalog() -> list[dict]:
    """SOC2 Trust Services Criteria (Security, Availability, Confidentiality, PI)."""
    tpl = [
        ("CC1.1 — Governance Tone at the Top", "Board governance attestation", "Code of conduct policy signoff", 0, 0),
        ("CC2.1 — Information & Communication", "Information flow diagram v3", "Comms policy attestation", 1, 7),
        ("CC3.1 — Risk Assessment", "Annual risk register", "Risk treatment plan signoff", 0, 9),
        ("CC4.1 — Monitoring Activities", "Continuous control monitoring dashboard", "Quarterly KCI review", 1, 7),
        ("CC5.1 — Control Activities", "Control matrix walkthrough", "Operating effectiveness sample", 0, 0),
        ("CC6.1 — Logical Access — MFA", "MFA enforcement evidence", "Privileged access recertification", 3, 0),
        ("CC6.2 — User Access Provisioning", "Access provisioning workflow proof", "New joiner SoD validation", 5, 2),
        ("CC6.3 — Access Removal", "Termination access removal log", "Quarterly orphan account scan", 0, 0),
        ("CC6.6 — Boundary Protection", "Firewall rule set audit", "WAF/Reverse-proxy rule review", 0, 6),
        ("CC6.7 — Data in Transit", "TLS configuration export", "Certificate inventory & expiry tracker", 0, 6),
        ("CC6.8 — Malware Protection", "Endpoint EDR coverage report", "Malware nil incident attestation", 1, 2),
        ("CC7.1 — Vulnerability Management", "Internal vuln scan report", "Critical vuln aging tracker", 0, 0),
        ("CC7.2 — Continuous Monitoring", "SIEM alert volume dashboard", "Use-case effectiveness review", 0, 7),
        ("CC7.3 — Incident Response", "P1/P2 incident playbook", "Major incident postmortem Q1", 1, 7),
        ("CC7.4 — Recovery from Incidents", "Recovery test execution log", "Lessons learned action tracker", 0, 4),
        ("CC8.1 — Change Management", "CAB minutes — quarterly", "Emergency change PIR samples", 0, 0),
        ("CC9.1 — Risk Mitigation", "Risk mitigation tracker", "Treatment progress report", 1, 7),
        ("CC9.2 — Vendor Management", "Vendor risk assessment summary", "TPSP remediation tracker", 3, 5),
        ("A1.1 — Availability Monitoring", "Uptime SLA dashboard", "Downtime root cause summary", 0, 0),
        ("A1.2 — Capacity Planning", "Capacity plan document", "Peak load forecast", 0, 0),
        ("A1.3 — Backup & Recovery", "Backup success rate dashboard", "Restore test attestation", 0, 4),
        ("C1.1 — Confidential Information Identification", "Data classification inventory", "PII scan results", 1, 3),
        ("C1.2 — Confidential Data Disposal", "Secure disposal certificate", "Media destruction log", 5, 1),
        ("PI1.1 — Processing Integrity", "Reconciliation report — settlement", "Mismatch closure register", 4, 3),
        ("PI1.2 — System Inputs Controls", "Input validation test results", "Reject queue review log", 2, 1),
    ]
    return _generic_catalog("SOC", "SOC2", tpl)


def _iso27001_catalog() -> list[dict]:
    """ISO/IEC 27001:2022 Annex A controls — information security management."""
    tpl = [
        ("A.5.1 — Information Security Policy", "ISMS policy v2026", "Top management policy signoff", 0, 0),
        ("A.5.7 — Threat Intelligence", "TI feed ingestion proof", "IOC match closure report", 0, 7),
        ("A.5.15 — Access Control Policy", "Access control policy attestation", "Recertification cycle evidence", 5, 2),
        ("A.5.23 — Cloud Services Security", "Cloud baseline audit", "Cloud service approval log", 1, 6),
        ("A.5.24 — Incident Management Planning", "Incident response plan v2026", "Plan walkthrough attendance", 1, 7),
        ("A.5.30 — ICT Readiness for BCM", "ICT BCM playbook", "DR drill execution report", 0, 4),
        ("A.6.3 — Information Security Awareness", "Training completion by department", "Phishing simulation results", 5, 1),
        ("A.8.2 — Privileged Access Rights", "PAM access list", "Quarterly privileged access review", 3, 0),
        ("A.8.5 — Secure Authentication", "MFA enforcement report", "Auth strength policy attestation", 0, 0),
        ("A.8.7 — Protection Against Malware", "EDR coverage report", "Malware drill results", 1, 2),
        ("A.8.8 — Management of Technical Vulnerabilities", "VA scan dashboard", "Patch SLA compliance", 0, 0),
        ("A.8.9 — Configuration Management", "Configuration baseline export", "Drift detection report", 0, 0),
        ("A.8.10 — Information Deletion", "Secure deletion attestation", "Storage decommission log", 5, 1),
        ("A.8.11 — Data Masking", "Masking rule catalog", "Non-prod scan for PII", 2, 4),
        ("A.8.12 — Data Leakage Prevention", "DLP incident register", "Policy effectiveness review", 0, 3),
        ("A.8.16 — Monitoring Activities", "SIEM use-case catalog", "Alert correlation dashboard", 0, 7),
        ("A.8.20 — Network Security", "Firewall rule audit", "Network segmentation diagram", 0, 6),
        ("A.8.23 — Web Filtering", "Web filter category report", "Block bypass investigation log", 1, 1),
        ("A.8.24 — Cryptography", "Cryptographic standard attestation", "Key management policy review", 0, 4),
        ("A.8.25 — Secure Development Lifecycle", "Secure SDLC policy", "Gate failure remediation log", 0, 0),
        ("A.8.28 — Secure Coding", "Secure coding training attendance", "Code review checklist sample", 0, 0),
        ("A.8.29 — Security Testing in Development", "SAST/DAST pipeline output", "Critical finding closure proof", 0, 0),
        ("A.8.30 — Outsourced Development Security", "Vendor security clauses", "Source code escrow attestation", 4, 3),
        ("A.8.32 — Change Management", "CAB minutes", "Emergency change tracker", 0, 0),
        ("A.8.33 — Test Information", "Test data masking proof", "Test data refresh log", 2, 4),
    ]
    return _generic_catalog("ISO", "ISO27001", tpl)


def _rbi_cyber_catalog() -> list[dict]:
    """RBI Cyber Security Framework for Indian banks."""
    tpl = [
        ("Annex 1.1 — Cyber Security Policy", "Board-approved cyber security policy", "Annual policy review minutes", 0, 0),
        ("Annex 1.2 — Cyber Crisis Management Plan", "CCMP document v2026", "Crisis drill execution report", 0, 7),
        ("Annex 1.3 — Inventory of Assets", "CMDB reconciliation report", "Critical asset classification", 4, 5),
        ("Annex 1.4 — Network Security", "Firewall rule audit", "Network segmentation diagram v4", 0, 6),
        ("Annex 1.5 — Secure Configuration", "OS baseline scan results", "Configuration drift report", 0, 0),
        ("Annex 1.6 — Application Security Lifecycle", "Secure SDLC walkthrough", "Pre-deployment security signoff", 0, 0),
        ("Annex 1.7 — Patch Management", "WSUS/SCCM patch report", "Emergency patch bulletin closure", 0, 3),
        ("Annex 1.8 — User Access Control", "Quarterly access recertification", "SoD conflict closure log", 5, 2),
        ("Annex 1.9 — Authentication Framework", "MFA enforcement screenshot", "Authentication policy review", 0, 0),
        ("Annex 1.10 — Secure Mail Gateway", "Mail gateway scan stats", "Phishing detection metrics", 1, 1),
        ("Annex 1.11 — Removable Media Policy", "USB blocking attestation", "Exception register review", 0, 0),
        ("Annex 1.12 — Anti-Phishing", "Phishing simulation outcomes", "Repeat offender coaching", 1, 1),
        ("Annex 1.13 — Data Leak Prevention", "DLP incident register", "Cross-border transfer log", 0, 3),
        ("Annex 1.14 — Vulnerability Management", "VA & VAPT report", "Critical vuln aging tracker", 0, 0),
        ("Annex 1.15 — Logs & Monitoring", "SIEM alert dashboard", "Log retention policy attestation", 0, 7),
        ("Annex 1.16 — IT Operations", "Operations runbook catalog", "Operational metrics dashboard", 0, 0),
        ("Annex 1.17 — Forensic Readiness", "Forensic capability assessment", "Chain of custody procedure", 1, 7),
        ("Annex 1.18 — Customer Awareness", "Customer awareness campaign metrics", "Channel-specific advisory log", 0, 0),
        ("Annex 1.19 — Risk Based Transaction Monitoring", "Transaction monitoring rules", "Anomaly investigation log", 2, 4),
        ("Annex 1.20 — Cyber Insurance", "Cyber insurance policy document", "Claim readiness checklist", 4, 9),
        ("Annex 1.21 — Cyber Drill Exercises", "Annual cyber drill report", "Drill scenario library", 0, 7),
        ("Annex 1.22 — Vendor Risk Management", "TPSP cyber assessment", "Critical vendor remediation tracker", 3, 5),
        ("Annex 1.23 — Incident Reporting to RBI", "RBI incident notification log", "Reportable incident matrix", 4, 9),
        ("Annex 1.24 — Continuous Surveillance", "24x7 SOC coverage proof", "SOC quality metrics", 1, 7),
    ]
    return _generic_catalog("RBI", "RBI Cyber Security", tpl)


def _isg_catalog() -> list[dict]:
    """Information Security Governance — internal enterprise policy framework."""
    tpl = [
        ("ISG-01 — ISG Charter", "ISG charter approval", "Annual review minutes", 0, 0),
        ("ISG-02 — Roles & Responsibilities", "RACI matrix v2026", "RACI walkthrough attendance", 5, 1),
        ("ISG-03 — Information Classification", "Classification policy attestation", "Application scope mapping", 1, 3),
        ("ISG-04 — Risk Management Framework", "Risk treatment plan", "Quarterly risk review minutes", 0, 9),
        ("ISG-05 — Policy Exception Workflow", "Exception register", "Exception expiry log", 0, 0),
        ("ISG-06 — Security Architecture Review", "SAR submission log", "Architecture board minutes", 0, 6),
        ("ISG-07 — Third-Party Onboarding Security", "Vendor onboarding security checklist", "TPSP escalation register", 3, 5),
        ("ISG-08 — Internal Audit Cycle", "Audit plan v2026", "Audit closure tracker", 0, 7),
        ("ISG-09 — Regulator Liaison", "Regulator engagement log", "Inspection follow-through tracker", 4, 9),
        ("ISG-10 — Internal Reporting Cadence", "ISG dashboard pack", "Compliance KPI tracker", 0, 7),
        ("ISG-11 — Security Awareness Programme", "Training schedule", "Department completion stats", 5, 1),
        ("ISG-12 — Cyber Defence Exercises", "Cyber drill scenarios", "Drill effectiveness report", 1, 7),
        ("ISG-13 — Continuous Improvement", "CI tracker", "Improvement implementation evidence", 0, 0),
        ("ISG-14 — Annual ISG Maturity Review", "Maturity assessment scorecard", "Maturity improvement plan", 0, 7),
        ("ISG-15 — KRI Dashboard", "Key risk indicator dashboard", "Trend analysis report", 0, 9),
        ("ISG-16 — Sensitive Data Inventory", "Sensitive data inventory log", "Discovery scan output", 1, 4),
        ("ISG-17 — Records Management", "Records retention policy", "Legal hold procedure", 4, 9),
        ("ISG-18 — ISG-SOC Liaison", "SOC monthly review minutes", "Joint use-case tuning log", 1, 7),
    ]
    return _generic_catalog("ISG", "ISG", tpl)


def _asst_catalog() -> list[dict]:
    """Application Security Self-assessment — internal pre-assessment framework."""
    tpl = [
        ("ASST-01 — Application Security Posture", "ASST checklist completion", "Sign-off by application owner", 0, 0),
        ("ASST-02 — Asset Coverage", "ASST asset coverage attestation", "CMDB cross-check", 0, 5),
        ("ASST-03 — Risk Rating Validation", "App risk rating worksheet", "Compliance team review log", 1, 7),
        ("ASST-04 — Encryption Posture", "Encryption status questionnaire", "Crypto algorithm inventory", 0, 4),
        ("ASST-05 — Authentication Strength", "Auth mechanism inventory", "MFA coverage matrix", 0, 0),
        ("ASST-06 — Data Protection Controls", "Data protection self-assessment", "DLP rule coverage", 0, 3),
        ("ASST-07 — Logging & Monitoring Coverage", "Logging coverage worksheet", "SIEM integration proof", 1, 7),
        ("ASST-08 — Incident Response Readiness", "IR readiness questionnaire", "Tabletop participation proof", 1, 7),
        ("ASST-09 — Patch & Vulnerability Posture", "Patch posture self-attestation", "VA scan attestation", 0, 0),
        ("ASST-10 — DR & Business Continuity", "DR posture worksheet", "RPO/RTO declaration", 0, 4),
        ("ASST-11 — Third-Party Dependencies", "Third-party inventory", "Vendor security review", 3, 5),
        ("ASST-12 — Change & Release Discipline", "Release process attestation", "Last 5 change reviews", 0, 0),
        ("ASST-13 — Identity Lifecycle", "Joiner/mover/leaver attestation", "Orphan account scan", 5, 2),
        ("ASST-14 — Container & Cloud Coverage", "Cloud asset registration", "Container security posture", 1, 6),
        ("ASST-15 — Mobile App Security", "Mobile app store presence audit", "Pen test attestation", 1, 2),
        ("ASST-16 — Privileged Tool Usage", "Privileged tool register", "Quarterly access proof", 3, 0),
        ("ASST-17 — Sensitive Data Inventory", "Sensitive data discovery", "Owner attestation", 0, 3),
    ]
    return _generic_catalog("ASS", "ASST", tpl)


FRAMEWORK_CATALOG: dict[str, list[dict]] = {
    "PCI DSS": _pci_catalog(),
    "DPSC": _dpsc_catalog(),
    "OS Baselining": _os_catalog(),
    "DB Baselining": _db_catalog(),
    "Nginx Baselining": _nginx_catalog(),
    "AppSec": _appsec_catalog(),
    "VAPT": _vapt_catalog(),
    "CSITE": _csite_catalog(),
    "ITPP": _itpp_catalog(),
    "ITDRM": _itdrm_catalog(),
    "SOC2": _soc2_catalog(),
    "ISO27001": _iso27001_catalog(),
    "RBI Cyber Security": _rbi_cyber_catalog(),
    "ISG": _isg_catalog(),
    "ASST": _asst_catalog(),
}


def build_legacy_frameworks() -> dict[str, list[tuple[str, str]]]:
    """Backward-compatible (control, primary_evidence) tuples for existing code."""
    out = {}
    for fw, controls in FRAMEWORK_CATALOG.items():
        out[fw] = [(c["control"], c["primary_evidence"]) for c in controls]
    return out


FRAMEWORK_ALIASES: dict[str, str] = {
    "PCI": "PCI DSS",
    "OSB": "OS Baselining",
    "OS Baseline": "OS Baselining",
    "NGX": "Nginx Baselining",
    "Nginx Baseline": "Nginx Baselining",
    "DBB": "DB Baselining",
    "ISO": "ISO27001",
    "ISO 27001": "ISO27001",
    "SOC": "SOC2",
    "RBI": "RBI Cyber Security",
    "RBI Cyber": "RBI Cyber Security",
}


def get_merged_framework_catalog() -> dict[str, list[dict]]:
    """Static + dynamically onboarded frameworks."""
    from app import ecs_state
    merged = dict(FRAMEWORK_CATALOG)
    merged.update(ecs_state.dynamic_framework_catalog)
    return merged


def resolve_framework_name(framework_name: str) -> str:
    """Map short route slugs (e.g. PCI) to catalog keys (PCI DSS)."""
    if not framework_name:
        return framework_name
    merged = get_merged_framework_catalog()
    if framework_name in merged:
        return framework_name
    return FRAMEWORK_ALIASES.get(framework_name, framework_name)


def get_framework_controls(framework_name: str) -> list[dict]:
    return get_merged_framework_catalog().get(resolve_framework_name(framework_name), [])


def get_evidence_lookup(framework_name: str) -> dict[str, dict]:
    """Map control name -> first evidence metadata (legacy pci_mock_by_control)."""
    return {c["control"]: {**c["evidences"][0], "control_id": c["control_id"]} for c in get_framework_controls(framework_name)}


def get_all_evidence_records() -> list[dict]:
    rows = []
    for fw, controls in FRAMEWORK_CATALOG.items():
        for ctrl in controls:
            for ev in ctrl["evidences"]:
                rows.append({**ev, "framework": fw, "control": ctrl["control"], "control_id": ctrl["control_id"]})
    return rows


def catalog_stats() -> dict:
    controls = sum(len(c) for c in FRAMEWORK_CATALOG.values())
    evidences = sum(len(c["evidences"]) for controls in FRAMEWORK_CATALOG.values() for c in controls)
    return {
        "framework_count": len(FRAMEWORK_CATALOG),
        "control_count": controls,
        "evidence_count": evidences,
    }


def seed_workflow_targets() -> dict:
    """Deterministic seed targets for demo_seed across all frameworks."""
    approved = []
    submitted = []
    rejected = []
    for fw, controls in FRAMEWORK_CATALOG.items():
        for i, ctrl in enumerate(controls):
            name = ctrl["control"]
            if i % 4 == 0:
                approved.append((fw, name, REVIEWERS[i % len(REVIEWERS)]))
            elif i % 4 == 1:
                submitted.append((fw, name))
            elif i % 9 == 0:
                rejected.append(
                    (
                        fw,
                        name,
                        f"Evidence package incomplete for {name.split('—')[0].strip()}: "
                        f"reviewer requires updated production artefact and signed attestation.",
                    )
                )
    return {"approved": approved, "submitted": submitted, "rejected": rejected}


# Backward compatibility alias
PCI_DSS_MOCK_EVIDENCES = [
    {**ev, "control": c["control"], "evidence": ev["evidence_name"], "application": ev["application_name"], "mock_file": ev["mock_file"]}
    for c in FRAMEWORK_CATALOG["PCI DSS"]
    for ev in c["evidences"]
]
