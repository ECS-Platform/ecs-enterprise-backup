# ECS Framework Reference

**Type:** Knowledge documentation. No code modified.
**Date:** 2026-06-17
**Grounding:** `modules/frameworks/engines/framework_catalog.py`
(`FRAMEWORK_CATALOG`, `catalog_stats`, `get_all_evidence_records`). Directive
frameworks not present as distinct catalog keys are mapped and marked
**(Inferred from implementation)**.

`catalog_stats()` reports the static catalog: **15 frameworks** (plus dynamically
onboarded frameworks via `ecs_state.dynamic_framework_catalog`), each with
controls and evidence templates.

---

## 1. Framework inventory

| # | Framework | Catalog key | Code prefix | Type |
|---|-----------|-------------|-------------|------|
| 1 | PCI DSS | `PCI DSS` | PCI | Card data security (regulatory) |
| 2 | DPSC | `DPSC` | DPSC | Data protection & security controls (regulatory) |
| 3 | OS Baselining | `OS Baselining` | OSB | Infrastructure hardening |
| 4 | DB Baselining | `DB Baselining` | DBB | Database hardening |
| 5 | Nginx / Web Server Baselining | `Nginx Baselining` | NGX | Web-server hardening |
| 6 | Application Security (AppSec) | `AppSec` | APS | App security controls |
| 7 | VAPT | `VAPT` | VAP | Vulnerability assessment & pen-test |
| 8 | C-SITE | `CSITE` | CSI | Cyber security incident & threat (RBI-aligned) |
| 9 | ITPP | `ITPP` | ITP | IT process & production controls |
| 10 | ITDRM | `ITDRM` | DRM | IT DR management |
| 11 | SOC2 | `SOC2` | SOC | Trust Services Criteria |
| 12 | ISO 27001 | `ISO27001` | ISO | ISMS |
| 13 | RBI Cyber Security | `RBI Cyber Security` | RBI | RBI cyber framework |
| 14 | ISG | `ISG` | ISG | Information security governance |
| 15 | ASST | `ASST` | ASS | Application security self-assessment |
| + | MBSS | **(Inferred)** → aligns to OS/DB/Nginx Baselining | — | Minimum Baseline Security Standard |
| + | Middleware Baselining | **(Inferred)** → `predefined_query_targets.middleware_servers` | — | Middleware hardening |
| + | Dynamic frameworks | `ecs_state.dynamic_framework_catalog` | — | Onboarded at runtime |

## 2. Per-framework profile

Each framework below documents: **Purpose · Controls · Checklists · Mappings ·
Evidence Requirements · Control Reuse · Evidence Reuse · Audit Relevance ·
Executive Relevance.** Control/evidence specifics derive from the catalog
builders in `framework_catalog.py`.

### 2.1 PCI DSS (`_pci_catalog`)
- **Purpose:** Protect cardholder data across the CDE (Net Banking, Payments, CBS).
- **Controls:** Req 3 (stored data/TDE/KMS), Req 4 (TLS in transit), Req 11.3 (VAPT/ASV), CAB change control, TPSP clauses, retention.
- **Checklists:** ASV scan, TLS cipher export, TDE attestation, CAB minutes.
- **Mappings:** shares encryption/logging/VAPT controls with C-SITE, DPSC, ISO27001, RBI.
- **Evidence Requirements:** ASV report, TDE attestation, KMS sign-off, TLS export, CAB minutes, retention policy.
- **Control Reuse:** encryption-at-rest, TLS, VAPT reused across DPSC/C-SITE/ISG/ITPP.
- **Evidence Reuse:** one ASV/TDE artifact tagged to PCI + adjacent frameworks.
- **Audit Relevance:** primary card-scheme audit; high regulator focus.
- **Executive Relevance:** card-business risk; breach/penalty exposure.

### 2.2 DPSC (`_dpsc_catalog`)
- **Purpose:** Data protection & security controls (UPI channel encryption, cross-border transfer, settlement reconciliation, RBI DPSC self-assessment).
- **Controls:** UPI TLS, cross-border data transfer log, settlement reconciliation, regulatory reporting.
- **Evidence:** NPCI encryption letter, DPA attestation, reconciliation logs, DPSC workbook.
- **Reuse:** encryption/logging controls shared with PCI/C-SITE; reconciliation evidence reused in SOC2 PI.
- **Audit/Exec Relevance:** RBI/NPCI regulatory; payments-business risk.

### 2.3 OS Baselining (`_os_catalog`)
- **Purpose:** Operating-system hardening across the server estate (`os_servers`).
- **Controls:** baseline scans (incl. AIX legacy), patch posture, extended-support risk.
- **Evidence:** baseline scan reports, risk registers (predefined-query OS checks: OS-001/002).
- **Reuse:** OS hardening evidence reused by C-SITE/ISO/RBI/MBSS.
- **Audit/Exec Relevance:** infra audit; estate risk posture.

### 2.4 DB Baselining (`_db_catalog`)
- **Purpose:** Database hardening (`db_servers`; PostgreSQL/Oracle).
- **Controls:** DB security baseline (DB-001/002/003 predefined queries — SSL, password encryption, replication).
- **Evidence:** PostgreSQL `SHOW ssl`/`password_encryption`/`pg_stat_replication` outputs.
- **Reuse:** DB controls reused by PCI (Req 3) / ISO / RBI.

### 2.5 Nginx / Web Server Baselining (`_nginx_catalog`)
- **Purpose:** Web-server configuration hardening (NGINX/Apache).
- **Controls:** `nginx -t`/`-T` config validation, TLS posture.
- **Evidence:** config test output, TLS settings.
- **Reuse:** shares TLS controls with PCI Req 4.

### 2.6 AppSec (`_appsec_catalog`)
- **Purpose:** Application security controls (SonarQube quality gates, secrets, dependency posture).
- **Controls:** APP-001/002 (Sonar projects/issues), APPSEC-001/002, DLP, red team, API gateway threat detection, threat hunting.
- **Evidence:** Sonar quality-gate exports, finding registers.
- **Reuse:** AppSec evidence reused by VAPT/ASST/ISO.

### 2.7 VAPT (`_vapt_catalog`)
- **Purpose:** Vulnerability assessment & penetration testing program.
- **Controls:** scope/methodology, payment-gateway pen test, annual program attestation, red-team follow-up.
- **Evidence:** pen-test reports, ASV alignment, remediation validation.
- **Reuse:** VAPT reports reused by PCI Req 11.3 / RBI / AppSec.

### 2.8 C-SITE (`_csite_catalog`)
- **Purpose:** Cyber security incident & threat (SOC operations, SIEM, escalation).
- **Controls:** SIEM alerts, escalation closure (TAT), DLP effectiveness, red team, threat hunt.
- **Evidence:** escalation trackers, SIEM exports, hunt findings.
- **Reuse:** logging/monitoring/encryption shared with PCI/DPSC/ISO/RBI.

### 2.9 ITPP (`_itpp_catalog`)
- **Purpose:** IT process & production controls (change, DR coverage, backup, emergency change, KEDB).
- **Evidence:** change registers, backup alert registers, PIR samples, KEDB exports.
- **Reuse:** change/backup controls shared with ITDRM/SOC2/ISO.

### 2.10 ITDRM (`_itdrm_catalog`)
- **Purpose:** IT DR management (restore SLA, vendor DR dependency, RBI BCM).
- **Evidence:** restore SLA dashboards, dependency registers, BCM self-assessment.
- **Reuse:** DR/backup reused by ITPP/SOC2 Availability/RBI.

### 2.11 SOC2 (`_soc2_catalog`)
- **Purpose:** Trust Services Criteria (Security, Availability, Confidentiality, Processing Integrity).
- **Controls:** CC-series risk assessment, PI reconciliation.
- **Reuse:** risk/availability/reconciliation reused with ISO/ITPP/DPSC.

### 2.12 ISO 27001 (`_iso27001_catalog`)
- **Purpose:** ISMS (Annex A controls incl. A.8.12 DLP).
- **Reuse:** broad reuse hub — most technical controls map to ISO Annex A.

### 2.13 RBI Cyber Security (`_rbi_cyber_catalog`)
- **Purpose:** RBI Cyber Security Framework for Indian banks (Annex 1.x).
- **Controls:** vulnerability management (1.14), removable media (1.11), DLP (1.13), incident reporting to RBI (1.23).
- **Reuse:** VAPT/DLP/incident controls reused from C-SITE/PCI/AppSec.
- **Audit/Exec Relevance:** top regulator priority; board-level reporting.

### 2.14 ISG (`_isg_catalog`)
- **Purpose:** Information security governance (charter, RACI, classification, risk framework, exceptions, SAR, audit cycle, regulator liaison, awareness).
- **Reuse:** governance controls underpin all frameworks.

### 2.15 ASST (`_asst_catalog`)
- **Purpose:** Application security self-assessment (internal pre-assessment, 17 items: posture, asset coverage, encryption, auth, DLP, IR, patch, DR, third-party, identity, cloud/container, mobile, privileged tools, sensitive data).
- **Reuse:** self-assessment answers reuse AppSec/VAPT/ISG evidence.

## 3. Cross-framework control reuse map (representative)

| Reusable control | Frameworks served |
|------------------|-------------------|
| Encryption at rest (TDE/KMS) | PCI, DPSC, C-SITE, ISG, ITPP, ISO, RBI |
| TLS in transit | PCI (Req4), Nginx Baselining, DPSC (UPI), ISO |
| Logging & monitoring / SIEM | C-SITE, PCI, DPSC, ISO, RBI |
| Vulnerability mgmt / VAPT | VAPT, PCI (11.3), RBI (1.14), AppSec |
| Backup & DR | ITDRM, ITPP, SOC2 (Availability), RBI |
| Access / identity lifecycle | ISG, ISO, SOC2, ASST |

## 4. Aggregate catalog stats

| Metric | Value (from `catalog_stats`) |
|--------|------------------------------|
| Frameworks (static) | 15 (+ dynamic onboarded) |
| Controls | sum across all framework catalogs |
| Evidence templates | sum across all controls |

> Demo deployments report ~17 frameworks / 320 controls / 1,200 evidence records
> (`nav_audit/final_demo_readiness_report.md`) once dynamic frameworks + demo seed
> are loaded.

## 5. Current vs inferred vs recommended

| Item | Current | Inferred | Recommended |
|------|---------|----------|-------------|
| MBSS | not a distinct catalog key | maps to OS/DB/Nginx baselining + middleware | Add explicit MBSS catalog if regulator requires distinct reporting |
| Middleware Baselining | targets exist (`middleware_servers`) | no distinct catalog builder | Add `_middleware_catalog` for first-class reporting |
| Dynamic frameworks | runtime onboarding supported | onboarding UI | Document onboarding workflow + approval gates |
