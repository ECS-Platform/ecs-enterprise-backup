# Framework Reference — OS Baselining

**Grounding:** `framework_catalog._os_catalog()`, route `/framework/OS Baselining`, Linux predefined queries. **Status:** Catalog framework. Part of [Frameworks Library](README.md).

## Purpose
Harden operating systems (Linux/AIX, container hosts) to CIS baselines across banking workloads.

## Objectives
CIS L2 hardening, SSH restrictions, AV/EDR coverage, patch compliance, privileged command logging, CMDB accuracy, container/kernel hardening, NTP, FIM, service minimization, access recertification.

## Controls (catalog, sample)
Linux Server Hardening — CIS L2 · SSH Access Restrictions · Endpoint AV Coverage · Patch Compliance — Critical · Privileged Command Logging · OS Inventory & CMDB Accuracy · Container Host Baseline · Time Synchronization (NTP) · File Integrity Monitoring · Unused Service Disablement · OS Access Recertification · Security Kernel Parameters · API Gateway OS Hardening · SOC Collector Host Baseline · Container Runtime Security · Middleware Patch Cadence · Production Jump Host Hardening · AIX Legacy Server Baseline.

## Checklist (sample)
- [ ] CIS benchmark scan + remediation closure
- [ ] sshd_config root login disabled
- [ ] Patch report (critical) + emergency closure
- [ ] sudoers audit log + allow-list review
- [ ] sysctl baseline + drift detection

## Evidence Requirements
Benchmark scans, config exports, patch reports, audit logs, port scans. **Query-driven** via Linux connector (objective pass/fail).

## Control & Evidence Reuse
Hardening/patch/access reuse with **PCI DSS, RBI Cyber, DB/Nginx/Middleware Baselining**. CMDB evidence shared with onboarding.

## Reporting
- **Executive:** OS baseline maturity %.
- **Audit:** CIS compliance pack.
- **Risk:** drift/unpatched criticals to Risk Register.

## Sample Assessment / Findings / Closure
- **Assessment:** CIS 85% compliant; 2 drift items.
- **Finding:** drift report week 19.
- **Closure:** auto-remediated via Ansible → Approved.
