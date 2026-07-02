# Framework Reference — ISG Assessment

**Grounding:** `framework_catalog._isg_catalog()` + `_asst_catalog()` (ASST-* controls e.g. "ASST-17 — Sensitive Data Inventory"), routes `/framework/ISG`, `/framework/ASST`. **Status:** Catalog frameworks (`ISG`, `ASST`). Part of [Frameworks Library](README.md).

## Purpose
Information Security Governance self-assessment — periodic attestation of security governance posture.

## Objectives
Governance attestations, sensitive-data inventory, policy adherence, ownership confirmation, gap identification across security domains.

## Controls (catalog, sample)
ASST-series owner-attested controls (e.g., **ASST-17 — Sensitive Data Inventory** via owner attestation) plus ISG governance items.

## Checklist (sample)
- [ ] Sensitive data inventory current (owner attested)
- [ ] Security policy adherence confirmed
- [ ] Ownership/accountability assigned
- [ ] Governance gaps logged as exceptions

## Evidence Requirements
Owner attestations, inventories, policy sign-offs. Predominantly attestation-based (manual upload / ServiceNow GRC).

## Control & Evidence Reuse
Governance attestations reuse with **ISO27001, RBI Cyber, SOC2**.

## Reporting
- **Executive:** governance self-assessment score.
- **Audit:** ISG attestation pack.
- **Risk:** governance gaps to Risk Register.

## Sample Assessment / Findings / Closure
- **Assessment:** sensitive data inventory attested.
- **Finding:** missing attestation for one domain.
- **Closure:** owner attestation uploaded → Approved.
