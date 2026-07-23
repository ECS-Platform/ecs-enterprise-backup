# Framework Reference — Application Security (AppSec)

**Grounding:** `framework_catalog._appsec_catalog()`, route `/framework/AppSec`, SonarQube/Gitleaks/Trivy predefined queries. **Status:** Catalog framework. Part of [Frameworks Library](README.md).

## Purpose
Secure the SDLC and application code/dependencies for banking applications.

## Objectives
SAST/secret/dependency scanning, secure coding, vulnerability remediation SLAs, code quality gates, supply-chain assurance.

## Controls (catalog, sample)
SAST coverage (SonarQube) · Secret scanning (Gitleaks) · Dependency/container scanning (Trivy) · Secure coding standards · Vulnerability remediation SLA · Quality gate enforcement.

## Checklist (sample)
- [ ] SonarQube quality gate passing
- [ ] Gitleaks: no committed secrets
- [ ] Trivy: 0 critical CVEs in images
- [ ] Remediation within SLA
- [ ] Branch protection / PR review enforced

## Evidence Requirements
Scan reports (Sonar/Gitleaks/Trivy), quality-gate exports, remediation trackers. **Query-driven** via SonarQube/Gitleaks/Trivy connectors.

## Control & Evidence Reuse
Vuln-mgmt/scan evidence reuse with **VAPT, PCI DSS, Cloud Security**.

## Reporting
- **Executive:** AppSec maturity %.
- **Audit:** secure-SDLC evidence pack.
- **Risk:** open critical CVEs/secrets to Risk Register.

## Sample Assessment / Findings / Closure
- **Assessment:** quality gate green; 4 medium CVEs.
- **Finding:** leaked secret pattern (Gitleaks).
- **Closure:** secret rotated + history scrubbed → Approved.
