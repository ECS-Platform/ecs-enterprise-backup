# Framework Reference — ITDRM

**Grounding:** `framework_catalog._itdrm_catalog()`, route `/framework/ITDRM`, DR/backup evidence (`INTERNET_BANKING_DR`). **Status:** Catalog framework. Part of [Frameworks Library](README.md).

## Purpose
IT Disaster Recovery Management — resilience, backup, and recovery assurance for critical banking systems.

## Objectives
Backup validation, restore testing, DR drills, RTO/RPO compliance, failover testing, DR site readiness.

## Controls (catalog, sample)
Backup & recovery validation · Restore test attestation · DR drill / switchover · RTO/RPO compliance · Failover testing · DR site segmentation.

## Checklist (sample)
- [ ] Backup success dashboard current
- [ ] Restore test attestation (Q1)
- [ ] DR switchover drill executed
- [ ] RTO/RPO targets met
- [ ] DR network segmentation diagram current

## Evidence Requirements
Backup dashboards, restore attestations, DR drill logs, switchover attestations, segmentation diagrams.

## Control & Evidence Reuse
Backup/restore/DR evidence reuse with **DB Baselining, ISO27001, PCI DSS (IR/segmentation)**.

## Reporting
- **Executive:** resilience/DR readiness.
- **Audit:** DR/backup evidence pack.
- **Risk:** failed restores / missed RTO to Risk Register.

## Sample Assessment / Findings / Closure
- **Assessment:** DR switchover drill documented.
- **Finding:** restore test pending for one cluster.
- **Closure:** restore attestation completed → Approved.
