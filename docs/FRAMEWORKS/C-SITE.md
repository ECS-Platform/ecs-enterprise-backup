# Framework Reference — C-SITE

**Grounding:** `framework_catalog._csite_catalog()`, route `/framework/CSITE`, SOC/SIEM evidence (`SIEM_COLLECTOR_HQ`). **Status:** Catalog framework (key `CSITE`). Part of [Frameworks Library](README.md).

## Purpose
Cyber Security & IT Examination / SOC monitoring assurance (continuous security operations).

## Objectives
SOC monitoring, SIEM alert review, escalation/closure within TAT, log retention, use-case effectiveness, threat coverage.

## Controls (catalog, sample)
SIEM daily alert review · Escalation closure tracking (P1/P2 TAT) · Centralized/immutable logging · Log retention attestation · SOC use-case effectiveness · Collector host baseline.

## Checklist (sample)
- [ ] Daily SOC alert review sign-offs
- [ ] P1/P2 escalations closed within TAT
- [ ] Immutable log chain hash verified
- [ ] 365-day log retention attested
- [ ] SIEM collector CIS baseline

## Evidence Requirements
SOC review logs, escalation trackers, log exports, retention attestations. Sources: SIEM Export, Scheduler Pull, ServiceNow GRC.

## Control & Evidence Reuse
Logging/monitoring evidence reuse with **PCI DSS, RBI Cyber, ISO27001, DPSC**.

## Reporting
- **Executive:** SOC posture / monitoring coverage.
- **Audit:** SOC monitoring evidence pack.
- **Risk:** open escalations / SLA breaches to Risk Register & correlation.

## Sample Assessment / Findings / Closure
- **Assessment:** daily reviews complete; escalations within TAT.
- **Finding:** escalation closure tracker under review.
- **Closure:** P1/P2 closed within TAT → Approved.
