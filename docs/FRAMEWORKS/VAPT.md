# Framework Reference — VAPT

**Grounding:** `framework_catalog._vapt_catalog()`, route `/framework/VAPT`, Trivy connector, CIO "Open VAPT" KPI. **Status:** Catalog framework. Part of [Frameworks Library](README.md).

## Purpose
Vulnerability Assessment & Penetration Testing assurance across applications and infrastructure.

## Objectives
Scheduled internal/external scans, penetration testing, finding triage, remediation validation, retest closure.

## Controls (catalog, sample)
Annual ASV/external scan · Internal VA scan (quarterly) · Penetration test execution · VA remediation tracking · Remediation validation/retest.

## Checklist (sample)
- [ ] Annual external scan, 0 critical
- [ ] Quarterly internal VA scan
- [ ] Pentest report + risk ratings
- [ ] Remediation tracker on-SLA
- [ ] Retest validation letter

## Evidence Requirements
Scan reports, pentest summaries, remediation trackers, validation letters. Partly **query-driven** (Trivy) + manual pentest uploads.

## Control & Evidence Reuse
Scan/remediation evidence reuse with **PCI DSS (ASV), AppSec, Cloud Security**.

## Reporting
- **Executive:** Open VAPT count (CIO dashboard).
- **Audit:** VAPT remediation pack.
- **Risk:** open criticals/mediums to Risk Register, correlation chains.

## Sample Assessment / Findings / Closure
- **Assessment:** ASV scan — no critical; 2 medium in remediation.
- **Finding:** medium findings open.
- **Closure:** retest passed; remediation validation letter → Approved.
