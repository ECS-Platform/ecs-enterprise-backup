# Framework Reference — DPSC (Digital Payment Security Controls)

**Grounding:** `framework_catalog._dpsc_catalog()`, route `/framework/DPSC`. **Status:** Catalog framework. Part of [Frameworks Library](README.md).

## Purpose
RBI Digital Payment Security Controls for net banking, mobile, UPI, and card payment channels.

## Objectives
API/gateway security, channel encryption, fraud monitoring, tokenization, transaction screening, rate limiting, device binding, settlement reconciliation, PSP integration assurance, RBI DPSC self-assessment.

## Controls (catalog, sample)
API Security Gateway Hardening · UPI Channel Encryption · Fraud Monitoring Coverage · Card Tokenization Controls · Real-time Transaction Screening · Digital Payment API Rate Limiting · Customer Device Binding · Settlement Reconciliation · Third-party PSP Integration · Regulatory Reporting — RBI DPSC · Payment Exception Handling · Cryptographic Key Lifecycle — Payments · Mobile Banking Session Security · Card Switch Failover Testing · Cross-border Data Transfer Log · Biometric Data Minimization.

## Checklist (sample)
- [ ] API gateway WAF rules + OAuth token validation
- [ ] UPI TLS config + NPCI encryption compliance letter
- [ ] Token vault architecture + tokenization pentest
- [ ] RBI DPSC self-assessment workbook + gap tracker
- [ ] Session timeout config + concurrent session audit

## Evidence Requirements
WAF/gateway exports, encryption letters, fraud dashboards, pentest summaries, self-assessment workbooks, reconciliation registers.

## Control & Evidence Reuse
Encryption, key lifecycle, API hardening reuse with **PCI DSS, AppSec, Mobile Banking Security**. SOC monitoring evidence shared with **CSITE**.

## Reporting
- **Executive:** payment-channel compliance posture.
- **Audit:** RBI DPSC self-assessment pack.
- **Risk:** fraud/false-positive and screening latency to Risk Register.

## Sample Assessment / Findings / Closure
- **Assessment:** UPI channel encryption verified vs NPCI baseline.
- **Finding:** settlement mismatch register exception aging.
- **Closure:** auto-reconciliation job logs + manual override approvals → Approved.
