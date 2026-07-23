# ECS Functional Manual (Knowledge Transfer)

**Audience:** product managers, auditors, governance teams, application owners. **Goal:** know *how to perform every core workflow* in ECS. Deep step detail: `docs/01-product/product/ECS_USER_JOURNEYS.md`.

---

## 1. Core object model

| Object | Meaning |
|---|---|
| **Application** | A system under governance (e.g. a banking app) |
| **Framework** | A regulation/standard (15: PCI DSS, RBI Cyber Security, ISO 27001, SOC 2, AI-SDLC, …) |
| **Control** | A requirement within a framework (305 total) |
| **Evidence** | An artifact proving a control is met (702 records) |
| **Validation** | Auditor approve/reject of evidence |
| **Observation / Finding** | An audit gap to remediate |
| **Exception / TD** | An approved deviation (compensating control) |

## 2. The 12 functional workflows

| # | Workflow | Trigger | Actor | Where (screen) | Output |
|---|---|---|---|---|---|
| 1 | Application onboarding | New app | Ops Owner | `/mvp/onboarding`, `/mvp/platform/onboarding` | Registered app |
| 2 | Framework onboarding | New regulation | FW Owner/Compliance | `/mvp/framework-loader`, `/mvp/framework-admin` | Active framework + control library |
| 3 | Evidence collection | Schedule/upload/connector | Ops/Owner | `/mvp/scheduler`, `/mvp/upload`, `/mvp/integrations` | Evidence records |
| 4 | Evidence approval | Submitted evidence | Auditor | `/evidence/review`, `/mvp/evidence-approval` | Approved/Rejected + audit trail |
| 5 | Audit preparation | Upcoming audit | Auditor/Compliance | `/mvp/audit-prep` | Readiness + audit pack |
| 6 | Control validation | Control review | Compliance | `/mvp/completeness`, framework page | Coverage/maturity |
| 7 | Exception / TD handling | Cannot meet control | Compliance/Owner | `/mvp/exceptions`, `/mvp/exception-governance` | Governed exception |
| 8 | Risk management | New risk | Governance/Risk | `/mvp/risk-register` | Tracked risk |
| 9 | Issue / findings remediation | Audit finding | Owner | `/mvp/workflow/close-gap` | Closed observation |
| 10 | Report generation | Stakeholder request | Auditor/CIO | `/mvp/reports` | Audit pack / HTML report |
| 11 | AI SDLC review | AI delivery gate | AI SDLC Owner | `/mvp/ai-sdlc/*` | Stage readiness/go-live |
| 12 | ROI / value measurement | Exec review | CIO | `/mvp/roi` | ROI, payback, hours saved |

## 3. Evidence lifecycle (state machine)

`Not Submitted → Submitted → Under Review → Approved` (or `→ Rejected → Resubmitted`). Approved evidence becomes **reusable** across frameworks via the reuse engine, and ages through **Evidence Health/Lifecycle** (fresh → expiring → stale → refresh).

## 4. How a control gets satisfied (worked example)

1. App owner uploads encryption config to control `PCI-3.4` (`/mvp/upload`).
2. Auditor reviews and approves (`/evidence/review`).
3. Reuse engine maps the same evidence to ISO 27001 `A.10.1` and SOC 2 `CC6.1` (`/mvp/reuse`).
4. Coverage rises on three framework pages; Audit Readiness Score updates.
5. Reports pack includes the artifact with lineage (`/mvp/reports`).

## 5. Audit preparation (how to walk in ready)

- Open `/mvp/audit-prep` → readiness heatmap by framework/app.
- Close red cells via `close-gap` / `upload-missing` actions.
- Run **mock audit** → generate the **audit package**.
- Confirm Audit Readiness Score ≥ 80 (Ready band).

## 6. Functional success criteria per workflow

Every workflow defines success/failure conditions (e.g. approval requires reviewer + audit-trail entry; framework onboarding requires control library load + coverage scan). Full criteria: `docs/01-product/product/ECS_USER_JOURNEYS.md`.

## 7. What auditors specifically use

`/mvp/audit-prep` · `/evidence/review` · `/mvp/evidence-approval` · `/mvp/search` · framework pages · `/mvp/reports` (audit packs). All evidence carries lineage to source.
