# Framework Reference — Database Baselining

**Grounding:** `framework_catalog._db_catalog()`, route `/framework/DB Baselining`, PostgreSQL/Oracle/MySQL/SQL Server predefined queries. **Status:** Catalog framework. Part of [Frameworks Library](README.md).

## Purpose
Harden and assure database platforms (Oracle CBS, PostgreSQL, MySQL, SQL Server).

## Objectives
Password rotation, audit logging, backup/recovery validation, TDE, least-privilege DB accounts, integrity assurance.

## Controls (catalog, sample)
Oracle Password Rotation — 90 day · Database Audit Logging · Backup & Recovery Validation · Transparent Data Encryption · Least Privilege — DB Accounts (and related DB controls).

## Checklist (sample)
- [ ] Password rotation compliance + break-glass review
- [ ] Unified DB audit trail + integrity hash proof
- [ ] Backup success dashboard + restore test attestation
- [ ] TDE status across production DBs + key escrow
- [ ] DB role entitlement review + excess privilege remediation

## Evidence Requirements
Rotation reports, audit-trail exports, backup dashboards, restore attestations, TDE status, entitlement reviews. **Query-driven** via DB connectors.

## Control & Evidence Reuse
TDE/encryption, audit logging, backup reuse with **PCI DSS, ISO27001, ITDRM, RBI Cyber**.

## Reporting
- **Executive:** DB baseline maturity.
- **Audit:** DB hardening + backup pack.
- **Risk:** missed rotations / failed restores to Risk Register.

## Sample Assessment / Findings / Closure
- **Assessment:** TDE enabled on production DBs; key escrow verified.
- **Finding:** restore test pending for one cluster.
- **Closure:** restore attestation Q1 → Approved.
