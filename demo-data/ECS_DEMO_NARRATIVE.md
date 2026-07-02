# ECS End-to-End Demo Narrative

A complete audit-lifecycle walkthrough on live repository data. Every step maps
to a working screen/endpoint. Roles: **App Owner**, **Compliance Head**,
**Auditor**, **CIO**.

Flow: Application Onboarding → Scheduler Creation → Evidence Collection →
Evidence Review → Evidence Reuse Across Frameworks → Compliance Dashboard →
Audit Reporting.

---

## 1. Application Onboarding  *(App Owner)*
- **Screen:** `/mvp/platform/onboarding` → `/mvp/platform/inventory`
- **Do:** Register an application (name, owner, business unit, criticality,
  environment, frameworks in scope). Submit.
- **Say:** "The portfolio is the system of record. Onboarding declares ownership
  and which frameworks (SOC2, ISO27001, PCI-DSS, RBI-CSF, AI-SDLC) apply — this
  is the denominator for coverage and readiness."
- **Proof:** new row in Application Inventory; `audit_log` gets
  `application.onboard`. 10 applications onboarded.

## 2. Scheduler Creation  *(Compliance Head)*
- **Screen:** `/mvp/platform/scheduler`
- **Do:** Add a recurring schedule (connector + cadence). Submit.
- **Say:** "Evidence must stay fresh. Schedules define cadence per connector/app
  with next-run tracking so proof never goes stale before an audit."
- **Proof:** schedule row with `next_run`; `schedule.create` audit entry.

## 3. Evidence Collection  *(Compliance Head / Ops)*
- **Screen:** `/mvp/integration-health` → **Sync Now** (Gitea / Jenkins / SonarQube)
- **Say:** "Connectors collect real artifacts — commits, PRs, builds, quality
  gates, security hotspots — into PostgreSQL, then auto-build Commit → Build →
  Sonar correlation chains."
- **Proof:** 54 evidence records; 6 CI/CD correlation chains; `evidence.collect`
  audit entries; sync runs logged.

## 4. Evidence Review (Lifecycle)  *(Auditor)*
- **Screen:** `/mvp/platform/evidence-lifecycle`
- **Do:** Move an item Collected → Under Review → Approved (or Rejected). Set
  validity window.
- **Say:** "Only **Approved** evidence counts toward readiness. Expired evidence
  is flagged automatically — this is the auditor's quality gate."
- **Proof:** 37 Approved / 11 Under Review / 3 Rejected / 2 Expired;
  `evidence.review` audit entries.

## 5. Evidence Reuse Across Frameworks  *(Compliance Head)* — the differentiator
- **Screen:** `/mvp/platform/evidence-reuse`
- **Say:** "One artifact, many obligations. A single SonarQube quality gate
  satisfies SOC2 CC7.1, ISO27001 A.14.2.1, PCI-DSS 6.3, RBI-CSF BCSF-SDLC and
  AI-SDLC simultaneously via the control→framework crosswalk."
- **Proof:** **5.0× cross-framework reuse** — 48 evidence items satisfy 240
  framework obligations = **192 collection operations saved**. The
  "One Evidence → Multiple Frameworks" tabs and Control×Framework crosswalk
  matrix make it concrete.

## 6. Compliance Dashboards  *(CIO / Vertical Head / Auditor / App Owner)*
- **Screen:** `/mvp/platform/scorecard?role=…` (role switcher) and
  `/mvp/platform/framework-coverage`, `/mvp/platform/control-coverage`
- **Say:** "Each leader sees the same truth, framed for them: onboarded apps,
  evidence collected, evidence reuse, framework coverage, open observations,
  rejected evidence, and a composite compliance score."
- **Proof:** Framework coverage 66.7% overall (AI-SDLC 83.3%); control coverage
  35.7%; compliance score 57.7% (At Risk); 12 open observations; 3 rejected.

## 7. Audit Reporting / Readiness  *(Auditor / CIO)*
- **Screen:** `/mvp/platform/audit-readiness` and `/mvp/platform/executive-summary`
- **Say:** "Readiness = 50% control coverage + 30% approved evidence + 20%
  freshness, scored per application and overall. The audit log is the immutable
  trail of every onboard, sync, and review."
- **Proof:** per-app readiness bands; open gaps + expired counts; full audit log
  on Integration Health.

---

## One-paragraph pitch
> "ECS turns scattered tool output into audit-ready evidence. Onboard an app,
> schedule collection, and connectors pull real artifacts into a single
> repository with lineage. Auditors approve once; the control→framework
> crosswalk reuses that single artifact across SOC2, ISO27001, PCI-DSS, RBI-CSF
> and AI-SDLC — a measured **5× reuse, 192 collection operations saved**.
> Leaders get role-specific scorecards and a live readiness score, all backed by
> an immutable audit trail."

## Demo URLs (role presets baked in)
| Step | URL |
|------|-----|
| Onboarding | `/mvp/platform/onboarding?role=owner&user=AppOwner` |
| Inventory | `/mvp/platform/inventory?role=owner&user=AppOwner` |
| Scheduler | `/mvp/platform/scheduler?role=compliance_head&user=Compliance` |
| Integration Health | `/mvp/integration-health?role=admin&user=Admin` |
| Evidence Lifecycle | `/mvp/platform/evidence-lifecycle?role=auditor&user=Auditor` |
| Evidence Reuse | `/mvp/platform/evidence-reuse?role=compliance_head&user=Compliance` |
| Role Scorecard | `/mvp/platform/scorecard?role=cio&user=CIO` |
| Framework Coverage | `/mvp/platform/framework-coverage?role=compliance_head&user=Compliance` |
| Audit Readiness | `/mvp/platform/audit-readiness?role=auditor&user=Auditor` |
| Executive Summary | `/mvp/platform/executive-summary?role=cio&user=CIO` |
