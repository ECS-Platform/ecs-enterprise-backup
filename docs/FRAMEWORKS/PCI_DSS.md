# Framework Reference — PCI DSS

**Grounding:** `framework_catalog._pci_catalog()`, route `/framework/PCI DSS`. **Status:** Catalog framework. Part of [Frameworks Library](README.md).

## Purpose
Protect cardholder data (CHD) across CDE systems (CBS Oracle, NetBanking, Card Payment Gateway, UPI switch).

## Objectives
Data-at-rest/in-transit encryption, access control & recertification, network segmentation, logging & monitoring, vulnerability management, secure change, third-party (TPSP) assurance, CHD retention/disposal.

## Controls (catalog)
Domains incl. Data Protection (TDE, KMS), TLS/cipher, CDE access recert & SoD, MFA/PAM, firewall/segmentation, centralized logging, ASV scans, HSM key lifecycle, IR, baseline/drift, AV/EDR, CAB change, POI device, internal VA, TPSP, CHD retention/disposal. ~Multiple controls; see catalog.

## Checklist (sample)
- [ ] DB TDE attestation current (CBS Oracle)
- [ ] TLS 1.2+ cipher export within scope
- [ ] Quarterly CDE access recertification
- [ ] IAM MFA enforcement for CDE jump hosts
- [ ] Annual ASV scan, 0 critical
- [ ] HSM key rotation certificate
- [ ] CHD retention policy + secure disposal certs

## Evidence Requirements
Config exports, attestations, recert sheets, scan reports, CAB minutes, certificates. Sources: SharePoint, ServiceNow GRC, Manual Upload, Scheduler Pull, SIEM Export, CMDB Agent.

## Control & Evidence Reuse
Encryption, access mgmt, logging, vuln mgmt reuse across **ISO27001, RBI Cyber, AppSec, OS/DB Baselining** via crosswalk. TLS/Nginx and VA/Trivy evidence shared with Nginx/VAPT.

## Reporting
- **Executive:** PCI compliance %, audit readiness on CIO dashboard.
- **Audit:** Audit Prep heatmap + Reports export (PCI pack).
- **Risk:** open VAPT/medium findings to Risk Register.

## Sample Assessment / Findings / Closure
- **Assessment:** CDE baseline CIS 85% compliant; gaps tracked.
- **Finding:** "CDE firewall rule export — missing Q1 CDE segment" (Rejected, Due for Refresh).
- **Closure:** remediation validation letter + retest passed → Approved; audit_log entry.
