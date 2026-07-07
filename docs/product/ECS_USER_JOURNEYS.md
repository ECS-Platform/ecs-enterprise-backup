# ECS User Journeys & Workflow Guide

Part of the **ECS Product Operations Manual** (Section 7). End-to-end workflows, each with **Trigger · Actors · Inputs · Steps · Outputs · Success criteria · Failure conditions**, grounded in the actual routes and engines. Cross-reference `ECS_SCREEN_CATALOG.md` for screens and `ECS_FEATURE_REFERENCE.md` for the action endpoints.

> The unifying model: **Framework → Control → Evidence → Validation → Audit → Reporting.** Every workflow below is a slice of this chain.

---

## 1. Application Onboarding

- **Trigger:** A new banking application enters scope and needs governance coverage.
- **Actors:** Operations Owner / Application Owner (initiates); Compliance Head / Framework Owner (assigns frameworks); Admin.
- **Inputs:** application name, description, owner + email, business unit, criticality, environment, lifecycle status, tech stack, hosting, applicable frameworks.
- **Steps:**
  1. Open **Onboarding** (`/mvp/onboarding`) or platform **Application Onboarding** (`/mvp/platform/onboarding`).
  2. Enter application metadata and select frameworks.
  3. (Optional) **Simulate** the onboarding (`POST /api/onboarding/simulate`) to preview control assignment.
  4. Submit (`POST /mvp/platform/onboarding`) → redirected to **Application Inventory** (`/mvp/platform/inventory`).
  5. The app appears in inventory; controls are auto-assigned from the chosen frameworks.
- **Outputs:** Registered application in inventory; framework→control assignments; onboarding summary (exportable via `/api/onboarding/export`).
- **Success criteria:** Application visible in `/mvp/platform/inventory` with assigned frameworks and an owner.
- **Failure conditions:** Missing required metadata; no framework selected (no controls assigned → 0% coverage).

---

## 2. Framework Onboarding

- **Trigger:** A new compliance framework (or a custom control library) must be added.
- **Actors:** Framework Owner / Compliance Head / CIO (manage); Auditor (review). Gated by `can_manage_framework_onboarding`.
- **Inputs:** framework control library (uploaded file in Loader) or framework definition; reuse decisions.
- **Steps:**
  1. **Framework Administration** (`/mvp/framework-admin`) → start the wizard (`?wizard=1`).
  2. **Import** the framework (`POST /api/framework-onboarding/import`).
  3. ECS normalizes controls and proposes **reuse intelligence** against the 18 canonical control themes.
  4. Make **reuse decisions** (`POST /api/framework-onboarding/reuse-decision`) — accept/reject canonical reuse.
  5. Advance **lifecycle** (`POST /api/framework-onboarding/lifecycle`) → Pending Review.
  6. **Auditor / governance review** (`can_review_framework_onboarding`).
  7. **Activate** (Framework Loader `POST /mvp/framework-loader/activate`) → framework live in catalog/nav.
- **Outputs:** New framework in the catalog and left nav; controls mapped; reuse links created; onboarding analysis export (`/mvp/framework-admin/export/{id}`).
- **Success criteria:** Framework status = Active; controls imported; appears under Frameworks nav.
- **Failure conditions:** Unsupported/duplicate controls; reuse conflicts unresolved; review not approved (stays Pending).

---

## 3. Evidence Collection

- **Trigger:** Scheduled cron, connector sync, or manual upload for a control.
- **Actors:** Scheduler/Operations Owner (automated); Application Owner (manual); Admin (real connector sync).
- **Inputs:** connector config (`config/integrations.yaml`), framework/application/control context, evidence files.
- **Steps (automated):**
  1. **Scheduler** (`/mvp/scheduler`) runs collection jobs (`POST /mvp/scheduler/run`).
  2. **Connectors** pull artefacts (`POST /api/platform/sync/{connector}` — admin) from Gitea/GitHub/Jenkins/SonarQube/Jira/ServiceNow/etc.
  3. Artefacts land in the **evidence repository** with metadata + hashes.
  4. Evidence auto-maps to controls/frameworks; visible in **Evidence Explorer** (`/mvp/evidence-explorer`).
- **Steps (manual):**
  1. Owner opens **Bulk Upload** (`/mvp/upload`) or `/evidence/upload`.
  2. Selects framework/application/control, uploads files.
  3. ECS validates, deduplicates, and auto-maps.
- **Outputs:** Evidence records in repository; updated coverage; nav badge counts refresh.
- **Success criteria:** Evidence attached to control, status = Submitted/Collected; connector health green (`/api/platform/health`).
- **Failure conditions:** Connector unreachable / auth failure (red in Integration Health); validation rejects file; control mismatch.

---

## 4. Evidence Approval (review lifecycle)

- **Trigger:** Owner submits evidence to the auditor queue.
- **Actors:** Application Owner (submit, respond); Auditor / Admin (review).
- **Inputs:** submitted evidence, control context, reviewer notes.
- **Steps:**
  1. Owner **submits** (`POST /submit`) → appears in auditor queue on `/dashboard`.
  2. Auditor opens **Evidence Review** (`/evidence/review`).
  3. Auditor chooses: **Approve** / **Reject** / **Clarify** / **Request re-upload** / **Close observation**.
  4. On reject/clarify/re-upload, evidence returns to owner ("resubmits required").
  5. Owner **uploads revised** (`/evidence/review/upload-revised`) → re-enters queue.
  6. Auditor **re-evaluates** and approves.
  7. Throughput tracked on **Evidence Approval Analytics** (`/mvp/evidence-approval`).
- **Outputs:** Evidence approved (counts toward coverage/readiness) or rejected (counts toward rejection rate); full audit trail (`audit_trail.py`).
- **Success criteria:** Approval Success % up, Rejection Rate % down, Avg Validation Time within SLA.
- **Failure conditions:** Repeated rejections; SLA breach; observation left open.

---

## 5. Audit Preparation

- **Trigger:** Upcoming audit on the rolling 12-month schedule (`audit_schedule_engine.py`).
- **Actors:** Auditor, Compliance Head, Application Owners (close gaps).
- **Inputs:** framework/app/risk/status/owner filters; evidence inventory.
- **Steps:**
  1. Open **Audit Prep** (`/mvp/audit-prep`) → review upcoming audits and the framework×application readiness heatmap.
  2. Drill gaps (`/api/audit-prep/audit-detail`, `/upcoming`).
  3. Remediate via **Close Gap / Assign Owner / Upload Missing** workflow pages.
  4. (Optional) Run a **Mock Audit** (`/mvp/workflow/mock-audit`) → text report.
  5. **Generate audit package** (`POST /audit/package/generate`) and **export bundle** (`GET /audit/package/export`).
- **Outputs:** Audit package (manifest, included/excluded evidence, reuse mappings, checksum); readiness scorecard.
- **Success criteria:** Weighted readiness ≥ 75% (Audit Prep threshold); package generated with required evidence.
- **Failure conditions:** Critical gaps unclosed; readiness < threshold; missing/expired evidence blocks closure.

---

## 6. Control Validation

- **Trigger:** Evidence collected for a control; periodic re-validation.
- **Actors:** system (automated checks), Compliance Head (review).
- **Inputs:** control definition, collected evidence, validation rules (config/file/policy/reuse/SLA).
- **Steps:**
  1. `control_validation_engine.py` runs config/file/policy/reuse/SLA checks.
  2. Computes **effectiveness %** = `100 × passed / total_checks`.
  3. Flags stale evidence and failed checks.
  4. Results surface on framework pages and Governance Analytics.
- **Outputs:** Validation status per control; effectiveness %; stale-evidence list.
- **Success criteria:** Effectiveness % high; no failed critical checks; evidence fresh.
- **Failure conditions:** Failed checks; stale/expired evidence; policy mismatch.

---

## 7. Exception / Technical-Debt Handling

- **Trigger:** A control cannot be met now; a compensating control / TD is proposed.
- **Actors:** Owner / Compliance / CIO (raise); Auditor (approve/reject); CAB (governance).
- **Inputs:** exception rationale, compensating control, expiry date, risk level.
- **Steps:**
  1. **Raise exception** (`POST /mvp/exceptions/raise`) on `/mvp/exceptions`.
  2. Exception enters **Exception Governance** (`/mvp/exception-governance`) → Pending Review / CAB queue.
  3. Auditor **approves/rejects** (module action `approve_exception`/`reject_exception`).
  4. Approved TDs tracked with expiry; renewal before expiry.
- **Outputs:** Active TD register; CAB queue; expiry tracking.
- **Success criteria:** Exception approved with compensating control and expiry; no high-risk open TDs overdue.
- **Failure conditions:** TD expired without renewal; high-risk open TD; rejection without remediation.

---

## 8. Risk Management

- **Trigger:** New risk identified (from findings, observations, or assessment).
- **Actors:** Governance/Risk teams, Compliance Head, CIO.
- **Inputs:** inherent risk, likelihood/impact, treatment, regulatory impact.
- **Steps:**
  1. Review **Risk Register** (`/mvp/risk-register`) — severity distribution + aging.
  2. Drill a risk (`/api/grc-demo/risk/drill`).
  3. Decide treatment: accept / mitigate / transfer; assign owner; set residual risk.
  4. Monitor on **Executive Heatmaps** (`/mvp/heatmaps`) and **Governance Analytics**.
- **Outputs:** Updated risk register; residual risk; treatment plan.
- **Success criteria:** High/critical risks trending down; no aged untreated risks.
- **Failure conditions:** Aging open high/critical risks; no treatment/owner.

---

## 9. Issue / Findings Remediation

- **Trigger:** A finding (SAST/DAST/VAPT/observation) is opened.
- **Actors:** Application Owner (remediate), Auditor (verify), Security Officer (security findings).
- **Inputs:** finding severity, owner, due date, control linkage.
- **Steps:**
  1. View findings on framework pages, **Findings & Remediation** (`/mvp/ai-sdlc/findings`), or Governance Analytics.
  2. Assign owner + due date; remediate.
  3. Attach remediation evidence; re-validate.
  4. Auditor closes the observation (`/evidence/review/close-observation`).
- **Outputs:** Closed observation; remediation velocity metric; SLA compliance.
- **Success criteria:** Observations Net negative (closing faster than opening); SLA on-time %.
- **Failure conditions:** Overdue findings; SLA breach; reopened findings.

---

## 10. Report Generation

- **Trigger:** A regulator/audit/executive report is needed.
- **Actors:** Auditor, CIO, Compliance, owners (export-permitted).
- **Inputs:** report selection + filters; output format.
- **Steps:**
  1. Open **Reports** (`/mvp/reports`) — browse the 30-pack catalog.
  2. (Optional) **View** an interactive HTML report (`/mvp/reports/view/{report_type}`).
  3. **Download** (`/mvp/reports/download/{report_id}?format=pdf|excel|csv`).
- **Outputs:** PDF/Excel/CSV report; export logged in history.
- **Success criteria:** Report generated in the requested format with current data.
- **Failure conditions:** Role lacks `can_export_reports`; unsupported format (falls back to text).

---

## 11. AI SDLC Review

- **Trigger:** An AI-enabled application moves through SDLC gates.
- **Actors:** AI SDLC Owner, AI Governance Owner, Auditor.
- **Inputs:** application, release, framework controls, stage evidence.
- **Steps:**
  1. Onboard the app (`/mvp/ai-sdlc/onboarding`).
  2. Monitor the **Control Tower** (`/mvp/ai-sdlc/control-tower`) readiness heatmap.
  3. Step through stage worklists: **Requirements → Design → Development → Testing → Go-Live**.
  4. Collect/approve **Evidence** (`/mvp/ai-sdlc/evidence`); review **Controlled Documents** (`/api/ai-sdlc/workflow/action`).
  5. Remediate **Findings** (`/mvp/ai-sdlc/findings`).
  6. Check **AI Governance Posture** (`/mvp/ai-governance`) — AI Compliance Score by dimension.
  7. Pass the **Go-Live** gate when release readiness ≥ band.
- **Outputs:** Stage/release readiness; AI Compliance Score; AI SDLC reports.
- **Success criteria:** All stage gates passed; release readiness ≥80; AI Compliance Score near 90% target.
- **Failure conditions:** Gate readiness below threshold; open critical findings; low-scoring AI governance dimension.

---

## 12. ROI / Value Measurement

- **Trigger:** Leadership wants to quantify ECS value.
- **Actors:** CIO, executives.
- **Inputs:** `config/roi.yaml` parameters (frameworks, apps, rates), scenario.
- **Steps:**
  1. Open **ROI & Value Realization** (`/mvp/roi`).
  2. Select a scenario; review annual value, hours saved, FTE, payback, ROI Audit Readiness Score.
- **Outputs:** ROI storyboard and value charts.
- **Success criteria:** Payback and value figures rendered for the scenario.
- **Failure conditions:** `ROI_CENTER_ENABLED` off; missing `config/roi.yaml`.

> **Note on ROI figures:** headline financials are configuration-driven and depend on the rate basis in `config/roi.yaml`. Treat ROI outputs as illustrative pending finance sign-off (see `strategy/ecs_roi_model.md`).

---

## Common persona journeys (quick reference)

| Persona | Typical journey |
|---|---|
| **Application Owner** | `/dashboard` → upload evidence → `/submit` → fix rejections → `/mvp/evidence-health` |
| **Auditor** | `/dashboard` (queue) → `/evidence/review` (approve/reject) → `/mvp/audit-prep` → generate package |
| **CIO** | `/dashboard/cio` → `/mvp/heatmaps` → `/mvp/trends` → `/mvp/roi` → leadership review |
| **Compliance Head** | `/dashboard/compliance-head` → `/mvp/completeness` → `/mvp/framework-admin` → export packs |
| **Operations Owner** | `/mvp/onboarding` → `/mvp/scheduler` → `/mvp/integration-health` → `/mvp/ai-ops-assistant` |
| **AI SDLC Owner** | `/mvp/ai-sdlc` → `/control-tower` → stage worklists → `/findings` → `/reports` |
| **Framework Owner** | `/mvp/framework-admin` → import → reuse decisions → activate |

See `ECS_PRODUCT_MANUAL.md` Section 9 for the structured 7-day learning path that walks a new joiner through these journeys.
