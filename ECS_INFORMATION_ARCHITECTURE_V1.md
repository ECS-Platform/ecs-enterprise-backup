# ECS Information Architecture V1

**Document type:** Authoritative Information Architecture  
**Version:** 1.0  
**Status:** Approved target state  
**Supersedes:** Ad-hoc navigation in `app/templates/partials/ecs_nav_groups.html` (baseline §2)  
**Derived from:** `ECS_ARCHITECTURE_BASELINE.md` + Enterprise Architecture recommendation (May 2026)  
**Scope:** Production navigation, module ownership, workflow ownership, role routing, reuse/retirement decisions  

> This document defines **what ECS exposes in the left navigation**, **who owns each surface**, and **which baseline modules are reused, introduced, or retired**. It does not prescribe implementation code.

---

## Document Purpose

ECS (Enterprise Compliance System) is reorganizing from a **feature-silo layout** (Executive Overview / Frameworks / Operations / Governance / Enterprise GRC) into a **capability-based information architecture** organized around:

- **Continuous Audit**
- **Continuous Compliance**
- **Continuous Governance**
- **AI Governance**
- **Audit Driven Development (ADD)**
- **Checklist-to-Evidence Lifecycle** (core spine)

This document is the single source of truth for navigation design, module boundaries, and ownership assignments for all future ECS work.

---

## Architectural Principles

1. **One lifecycle, many lenses** — Audit, compliance, and governance are views over the same control → evidence → observation graph.
2. **Frameworks are catalogs; navigation exposes capabilities** — Framework pages are reached through the Framework Catalog, not a flat 15-item list.
3. **Shift-left before shift-right** — ADD and SDLC gates sit upstream; Continuous Audit sits downstream.
4. **Every nav item has one owner** — Business function, primary role, and baseline engine are explicit.
5. **Consolidate before create** — Reuse existing engines; add net-new surfaces only when composition is insufficient.

---

## Core Spine: Checklist-to-Evidence Lifecycle

All operational modules ultimately support this end-to-end flow:

```
Control Checklist → Evidence Request → Collection → Validation →
Internal Review → Auditor Approval → Reuse Mapping → Audit Pack Export
```

| Stage | Baseline engine(s) | Primary workflow owner |
| --- | --- | --- |
| 1. Checklist generation | `governance_completeness_engine`, `missing_evidence_engine` | Compliance Office |
| 2. Evidence request | `missing_evidence_registry`, upload-missing workflow | GRC Operations |
| 3. Collection | `scheduler_module`, `integrations_module`, `evidence_repository` | Platform Engineering / App Owner |
| 4. Validation | `control_validation_engine`, `evidence_health_engine` | GRC Operations |
| 5. Internal review | `evidence_workflow_engine`, `evidence_review` | App Owner |
| 6. Auditor approval | `main.py` approve/reject/clarify, `evidence_workflow_engine` | Internal Audit |
| 7. Reuse mapping | `framework_intelligence`, reuse APIs | Compliance Architecture |
| 8. Audit pack assembly | `reporting_module`, `gap_export_engine`, audit package APIs | Audit PMO |

---

## 1. Final Left Navigation Hierarchy

Production sidebar structure. Items marked *(role-gated)* appear only for eligible roles.

```
ECS Sidebar (Production)
│
├── 🏠 Home
│
├── 📋 Compliance & Controls
│
├── 📁 Evidence Operations
│
├── 🔍 Continuous Audit
│
├── ⚖️ Governance & Risk
│
├── 🤖 AI & SDLC Governance
│
├── 🏢 Enterprise Insights
│
└── ⚙️ Platform Administration
```

### Navigation routing rules

| Rule | Description |
| --- | --- |
| **Role-aware Home** | Login routes to the correct Home dashboard per role (see §6). |
| **Framework Catalog replaces flat framework list** | Individual framework pages (`/framework/{name}`) are reached from the catalog, not listed as 15 sidebar entries. |
| **Workflow sub-screens are not nav items** | Evidence Review, Close Gap, Assign Owner, Upload Missing, Mock Audit remain drill-down/workflow routes. |
| **Demo Overview is not in production nav** | Route `/mvp/demo-overview` retained for sales/demo; hidden from production sidebar. |
| **Global AI Copilot is not a nav item** | Floating dock (`chatbot_global.html`) remains cross-cutting on all pages. |
| **Integrations is a single hub** | `/mvp/integrations` retired; all connector surfaces live under Integrations Hub. |

---

## 2. All Menu Groups

| # | Group ID | Display name | Operating model | Primary audience |
| --- | --- | --- | --- | --- |
| G1 | `home` | Home | Role entry / work queue | All roles |
| G2 | `compliance_controls` | Compliance & Controls | Continuous Compliance | Compliance Head, Owner, Auditor |
| G3 | `evidence_operations` | Evidence Operations | Checklist-to-Evidence execution | Owner, Auditor, GRC Ops |
| G4 | `continuous_audit` | Continuous Audit | Continuous Audit | Auditor, Compliance Head, CIO |
| G5 | `governance_risk` | Governance & Risk | Continuous Governance | Compliance Head, CIO, Risk Office |
| G6 | `ai_sdlc_governance` | AI & SDLC Governance | AI Governance + ADD | CIO, AI CoE, AppSec CoE, Owner |
| G7 | `enterprise_insights` | Enterprise Insights | Executive intelligence | CIO, Vertical Head, board |
| G8 | `platform_admin` | Platform Administration | Platform & catalog management | Admin, Compliance Architecture, EA |

### Hidden / non-production group

| Group ID | Display name | Route | Audience |
| --- | --- | --- | --- |
| `demo` | Demo Overview *(hidden)* | `/mvp/demo-overview` | Sales, product demo, QA |

---

## 3. All Submenus

### G1 — Home

| Submenu | Route | Module key | Role gate | Baseline reference |
| --- | --- | --- | --- | --- |
| Work Queue Dashboard | `/dashboard` | `main_dashboard` | Owner, Auditor | `dashboard.html` |
| Executive Command Center | `/dashboard/cio` | `role_dashboard` | CIO | `cio_dashboard.html` |
| Vertical Command Center | `/dashboard/vertical-head` | `role_dashboard` | Vertical Head | `dashboard_vertical_head.html` |
| Compliance Posture Dashboard | `/dashboard/compliance-head` | `role_dashboard` | Compliance Head, Compliance Officer | `dashboard_compliance_head.html` |
| Domain Command Center | `/dashboard/functional-head` | `role_dashboard` | Functional Head | `dashboard_functional_head.html` |

**Note:** Only one Home item is visible per role at login. Others are reachable if the user holds multiple roles (future SSO) or via direct URL in demo mode.

---

### G2 — Compliance & Controls

| Submenu | Route | Module key | Role gate | Baseline reference |
| --- | --- | --- | --- | --- |
| Framework Catalog | `/mvp/framework-catalog` *(new route; composes existing)* | `framework_catalog_browser` | All roles (read); Admin (write) | `framework_catalog`, `search_module`, `global_filter_engine` |
| Control Completeness | `/mvp/completeness` | `completeness` | Compliance Head, Owner, Auditor | `mvp_completeness.html` |
| Regulatory Mapping | `/mvp/regulatory` | `regulatory_mapping` | Compliance Head | `mvp_regulatory.html` |
| Evidence Reuse | `/mvp/reuse` | `reuse` | Owner, Compliance Head, Auditor | `mvp_reuse.html` |
| Lifecycle Tracker | `/mvp/lifecycle` | `lifecycle` | All operational roles | `mvp_lifecycle.html` |
| Continuous Controls Monitoring | `/mvp/ccm` *(new route; composes existing)* | `ccm` | Compliance Head, Auditor | `control_validation_engine`, `scheduler_module` |

**Framework drill-down (not sidebar items):**

| Submenu | Route | Notes |
| --- | --- | --- |
| Framework Command Center | `/framework/{name}` | One page per framework (15+ frameworks including AI Governance) |
| ITPP Domain View | `/framework/ITPP?itpp_domain={domain}` | Special domain-rich framework pattern |
| ITPP App View | `/framework/ITPP?itpp_domain={domain}&itpp_app={app}` | ITPP drill-down |
| Application Drill | `/framework/{name}?fw_app={app}&fw_tab={tab}` | Per-app control/evidence view |

---

### G3 — Evidence Operations

| Submenu | Route | Module key | Role gate | Baseline reference |
| --- | --- | --- | --- | --- |
| My Work Queue | `/dashboard?tab=queue` *(promoted; same route, nav emphasis)* | `work_queue` | Owner, Auditor | `workflow_module` queues on `dashboard.html` |
| Evidence Collection | `/mvp/scheduler` | `scheduler` | Owner, Admin | `mvp_scheduler.html` |
| Upload & Ingestion | `/mvp/upload` | `upload` | Owner only | `mvp_bulk_upload.html` |
| Evidence Health | `/mvp/evidence-health` | `evidence_health` | Owner, Auditor | `mvp_evidence_health.html` |
| Evidence Discovery | `/mvp/search` | `search` | All roles | `mvp_search.html` |
| Approval Analytics | `/mvp/evidence-approval` | `evidence_approval` | Auditor, Compliance Head | `mvp_evidence_approval.html` |

**Workflow entry points (not sidebar items):**

| Workflow screen | Route |
| --- | --- |
| Evidence Review | `/evidence/review?framework_name=…&evidence_id=…` |
| Upload Missing Evidence | `/mvp/workflow/upload-missing` |
| Close Gap | `/mvp/workflow/close-gap` |
| Assign Owner | `/mvp/workflow/assign-owner` |

---

### G4 — Continuous Audit

| Submenu | Route | Module key | Role gate | Baseline reference |
| --- | --- | --- | --- | --- |
| Audit Command Center | `/mvp/audit-prep` | `audit_prep` | Auditor, Compliance Head, CIO | `mvp_audit_prep.html` |
| Mock Audit & Readiness | `/mvp/workflow/mock-audit` | `mock_audit` | Auditor | `mvp_workflow_mock_audit.html` |
| Audit History | `/mvp/audit-history` *(new route; composes existing)* | `audit_history` | Auditor, CIO | `ecs_mock_engine.generate_audit_history`, trends slice |
| Audit Packs & Reports | `/mvp/reports?category=audit` *(filtered view)* | `reports_audit` | Auditor, Compliance Head, CIO | `mvp_reports.html` |

**Sections within Audit Command Center (tabs/anchors, not separate nav items):**

| Section | Baseline source |
| --- | --- |
| Audit Calendar | `audit_schedule_engine.generate_audit_calendar` |
| Audit Preparation Pipeline | `audit_schedule_engine.generate_preparation_pipeline` |
| Upcoming Audits | `audit_schedule_engine.generate_upcoming_audits` |
| Baselining History | `audit_schedule_engine.generate_baselining_history` |
| KPI Drill-downs | `audit_schedule_engine.build_kpi_drilldowns` |

---

### G5 — Governance & Risk

| Submenu | Route | Module key | Role gate | Baseline reference |
| --- | --- | --- | --- | --- |
| Risk Register | `/mvp/risk-register` | `risk_register` | Compliance Head, CIO | `mvp_risk_register.html` |
| Exceptions & Technical Debt | `/mvp/exceptions` | `exceptions_td` | Owner, Compliance Head, Auditor | `mvp_exceptions.html` |
| Exception Governance | `/mvp/exception-governance` | `exception_governance` | Compliance Head, CIO | `mvp_exception_governance.html` |
| Governance Analytics | `/mvp/governance-analytics` | `governance_analytics` | CIO, Compliance Head | `mvp_governance_analytics.html` |
| Cross-Tool Correlation | `/mvp/correlation` | `correlation` | Auditor, CIO | `mvp_correlation.html` |

---

### G6 — AI & SDLC Governance

| Submenu | Route | Module key | Role gate | Baseline reference |
| --- | --- | --- | --- | --- |
| AI Governance Posture | `/mvp/ai-governance` *(new route; promoted from demo)* | `ai_governance` | CIO, Compliance Head, Security Officer | `ecs_mock_engine.generate_ai_governance` |
| SDLC Compliance Gates | `/mvp/sdlc-gates` *(new route; composes existing)* | `sdlc_gates` | Owner, Functional Head, AppSec CoE | AppSec framework + `control_validation_engine` + Integrations Hub |
| Model & Prompt Registry | `/mvp/ai-registry` *(new module)* | `ai_registry` | AI CoE, Compliance Head, Admin | New entity; UX pattern from Framework Admin |

**Framework drill-down:**

| Submenu | Route | Notes |
| --- | --- | --- |
| AI Governance Framework | `/framework/AI Governance` | New catalog entry (see §9) |

---

### G7 — Enterprise Insights

| Submenu | Route | Module key | Role gate | Baseline reference |
| --- | --- | --- | --- | --- |
| Enterprise Overview | `/mvp/enterprise` | `enterprise` | CIO, Vertical Head | `mvp_enterprise.html` |
| Executive Heatmaps | `/mvp/heatmaps` | `executive_heatmaps` | CIO | `mvp_heatmaps.html` |
| Application Comparison | `/mvp/comparison` | `comparison` | Compliance Head, Vertical Head | `mvp_comparison.html` |
| Pan-India Posture | `/mvp/pan-india` | `pan_india` | CIO, Vertical Head | `mvp_pan_india.html` |
| Trends & Analytics | `/mvp/trends` | `trends` | CIO, Compliance Head, Auditor | `mvp_trends.html` |

---

### G8 — Platform Administration

| Submenu | Route | Module key | Role gate | Baseline reference |
| --- | --- | --- | --- | --- |
| Application Onboarding | `/mvp/onboarding` | `onboarding` | CIO, Admin | `mvp_onboarding.html` |
| Framework Loader | `/mvp/framework-loader` | `framework_loader` | Compliance Head, Admin | `framework_loader.html` |
| Framework Administration | `/mvp/framework-admin` | `framework_admin` | Admin, Compliance Head | `mvp_framework_admin.html` |
| + Add New Framework | `/mvp/framework-admin?wizard=1` | `framework_admin_wizard` | Admin, Compliance Head | Wizard entry |
| Framework Onboarding Review | `/mvp/framework-admin?role=auditor` | `framework_admin_review` | Auditor | Auditor review mode |
| Integrations Hub | `/mvp/integrations-hub` | `integrations_hub` | Admin, Owner (read) | `mvp_integrations_hub.html` |
| CMDB & Asset Inventory | `/mvp/cmdb` | `cmdb` | Owner, Admin | `mvp_cmdb.html` |

---

## 4. Dashboard Ownership

Each dashboard has **one primary business owner**, **one primary audience**, and **one canonical route**.

| Dashboard | Primary business owner | Primary audience | Canonical route | Layer |
| --- | --- | --- | --- | --- |
| Work Queue Dashboard | GRC Operations | App Owner, Auditor | `/dashboard` | L0 — Home |
| Executive Command Center | CIO Office | CIO | `/dashboard/cio` | L0 — Home |
| Vertical Command Center | Business Vertical Leadership | Vertical Head | `/dashboard/vertical-head` | L0 — Home |
| Compliance Posture Dashboard | Compliance Office | Compliance Head / Officer | `/dashboard/compliance-head` | L0 — Home |
| Domain Command Center | Functional IT Leadership | Functional Head | `/dashboard/functional-head` | L0 — Home |
| Framework Command Center | Framework owner (per framework) | App Owner, Auditor | `/framework/{name}` | L1 — Operating |
| Framework Catalog Browser | Compliance Architecture | All roles | `/mvp/framework-catalog` | L1 — Operating |
| Control Completeness Dashboard | Compliance Office | Compliance Head, App Owner | `/mvp/completeness` | L1 — Operating |
| Lifecycle Tracker Dashboard | GRC Operations | All operational roles | `/mvp/lifecycle` | L1 — Operating |
| Evidence Health Dashboard | GRC Operations | App Owner, Auditor | `/mvp/evidence-health` | L1 — Operating |
| Evidence Reuse Dashboard | Compliance Architecture | Compliance Head | `/mvp/reuse` | L1 — Operating |
| Approval Analytics Dashboard | Internal Audit | Auditor | `/mvp/evidence-approval` | L1 — Operating |
| Audit Command Center | Audit PMO | Auditor, Compliance Head | `/mvp/audit-prep` | L1 — Operating |
| Continuous Controls Monitoring | Compliance Office / Internal Audit | Compliance Head, Auditor | `/mvp/ccm` | L1 — Operating |
| AI Governance Posture Dashboard | AI CoE / Model Risk | CIO, Compliance Head | `/mvp/ai-governance` | L1 — Operating |
| SDLC Compliance Gates Dashboard | AppSec CoE | App Owner, Functional Head | `/mvp/sdlc-gates` | L1 — Operating |
| Model & Prompt Registry | AI CoE | AI CoE, Compliance Head | `/mvp/ai-registry` | L1 — Operating |
| Governance Analytics Dashboard | GRC Analytics | CIO, Compliance Head | `/mvp/governance-analytics` | L2 — Analytical |
| Application Comparison Dashboard | Compliance / Enterprise Architecture | Compliance Head, Vertical Head | `/mvp/comparison` | L2 — Analytical |
| Executive Heatmaps | CIO Office | CIO | `/mvp/heatmaps` | L2 — Analytical |
| Trends & Analytics Dashboard | GRC Analytics | CIO, Compliance Head, Auditor | `/mvp/trends` | L2 — Analytical |
| Enterprise Overview Dashboard | CIO Office | CIO, board | `/mvp/enterprise` | L3 — Executive |
| Pan-India Posture Dashboard | Regional Compliance | CIO, Vertical Head | `/mvp/pan-india` | L3 — Executive |
| Audit Packs & Reports Center | Audit PMO | Auditor, Compliance Head | `/mvp/reports` | L3 — Executive |
| Regulatory Mapping Dashboard | Compliance Architecture | Compliance Head | `/mvp/regulatory` | L2 — Analytical |
| Risk Register Dashboard | Enterprise Risk | Compliance Head, CIO | `/mvp/risk-register` | L2 — Analytical |
| Exceptions & TD Dashboard | App Owners + Risk | App Owner, Compliance Head | `/mvp/exceptions` | L2 — Analytical |
| Exception Governance Dashboard | Risk / CAB | Compliance Head, CIO | `/mvp/exception-governance` | L2 — Analytical |
| Cross-Tool Correlation Dashboard | SOC / GRC Fusion | Auditor, CIO | `/mvp/correlation` | L2 — Analytical |
| Integrations Hub Dashboard | Platform Engineering | Admin | `/mvp/integrations-hub` | L4 — Platform |
| Framework Loader Dashboard | Compliance Architecture | Compliance Head | `/mvp/framework-loader` | L4 — Platform |
| Framework Administration Dashboard | Compliance Architecture | Admin, Auditor (review) | `/mvp/framework-admin` | L4 — Platform |
| Application Onboarding Dashboard | Enterprise Architecture | CIO, Admin | `/mvp/onboarding` | L4 — Platform |
| CMDB & Asset Inventory Dashboard | IT Operations | App Owner, Admin | `/mvp/cmdb` | L4 — Platform |
| Demo Overview Dashboard | Product / Sales *(non-production)* | Demo users only | `/mvp/demo-overview` | L5 — Demo |

### Dashboard layer model

```
L0 — Role Home           Daily entry (Work Queue, Executive Command, etc.)
L1 — Operating           Audit Command, Completeness, Evidence Health, SDLC Gates, AI Posture
L2 — Analytical          Governance Analytics, Heatmaps, Comparison, Trends, Risk
L3 — Executive           Enterprise Overview, Pan-India, Reports
L4 — Platform            Integrations Hub, Framework Admin, Onboarding
L5 — Demo (hidden)       Demo Overview
```

---

## 5. Workflow Ownership

Workflows are owned by **business process**, not by the page that renders them.

### 5.1 Checklist-to-Evidence Lifecycle

| Stage | Workflow name | Process owner | Actors | Baseline route / engine |
| --- | --- | --- | --- | --- |
| 1 | Checklist generation | Compliance Office | System, Compliance Head | `governance_completeness_engine` → `/mvp/completeness` |
| 2 | Evidence request | GRC Operations | Auditor, App Owner | `missing_evidence_registry` → `/mvp/workflow/upload-missing` |
| 3 | Evidence collection | Platform Engineering | App Owner, Scheduler | `scheduler_module`, `integrations_module` → `/mvp/scheduler`, `/mvp/upload` |
| 4 | Evidence validation | GRC Operations | System, App Owner | `control_validation_engine`, `evidence_repository` → `/evidence/revalidate` |
| 5 | Internal owner review | App Owner | App Owner | `evidence_workflow_engine` → `/evidence/review` |
| 6 | Auditor approval | Internal Audit | Auditor | `main.py` approve/reject/clarify → `/evidence/review` |
| 7 | Resubmission | App Owner | App Owner, Team | `resubmission.py` → `/evidence/review/*` resubmit stages |
| 8 | Reuse mapping | Compliance Architecture | Compliance Head, Auditor | `framework_intelligence` → `/mvp/reuse`, reuse-decision API |
| 9 | Audit pack export | Audit PMO | Auditor | `reporting_module`, audit package APIs → `/mvp/reports`, `/audit/package/*` |

### 5.2 Continuous Audit workflows

| Workflow name | Process owner | Actors | Baseline route / engine |
| --- | --- | --- | --- |
| Audit scheduling (quarterly/annual) | Audit PMO | System, Auditor | `audit_schedule_engine` |
| Readiness scoring | Audit PMO | Auditor, Compliance Head | `audit_schedule_engine._build_audit_record` |
| Audit calendar management | Audit PMO | Auditor | Section in `/mvp/audit-prep` |
| Preparation pipeline tracking | Audit PMO | Auditor, App Owner | Section in `/mvp/audit-prep` |
| Mock audit execution | Internal Audit | Auditor | `/mvp/workflow/mock-audit` |
| Observation closure | Internal Audit | Auditor | `/evidence/review/close-observation`, `close_observations_for_control` |
| Baselining history review | Infra Audit | Auditor | Section in `/mvp/audit-prep` |
| Audit KPI drill-down | Audit PMO | Auditor, Compliance Head | `/api/audit-prep/kpi-drill` |
| Leadership review / escalation | Compliance / CIO | CIO, Vertical Head, Compliance Head | `/workflow/leadership/review` |

### 5.3 Continuous Compliance workflows

| Workflow name | Process owner | Actors | Baseline route / engine |
| --- | --- | --- | --- |
| Framework catalog onboarding | Compliance Architecture | Compliance Head, Admin | `framework_onboarding_engine`, `/mvp/framework-loader` |
| Control normalization / theme mapping | Compliance Architecture | Compliance Head | `framework_intelligence` |
| Regulatory crosswalk | Compliance Office | Compliance Head | `/mvp/regulatory` |
| Completeness gap remediation | App Owner | App Owner, Auditor | `/mvp/workflow/close-gap`, `/mvp/workflow/assign-owner` |
| Evidence refresh (stale/expired) | App Owner | App Owner | Evidence Health → upload-missing |
| Continuous controls monitoring | Compliance Office | System, Auditor | `control_validation_engine` + scheduler → `/mvp/ccm` |
| Framework lifecycle (Draft→Active) | Compliance Architecture | Admin, Auditor | `framework_onboarding_engine` LIFECYCLE_STATES |

### 5.4 Continuous Governance workflows

| Workflow name | Process owner | Actors | Baseline route / engine |
| --- | --- | --- | --- |
| Risk registration & treatment | Enterprise Risk | Compliance Head, CIO | `enterprise_grc.build_risk_register` |
| Exception / TD raise | App Owner / Internal Audit | App Owner, Auditor | `/mvp/exceptions/raise`, `/api/exceptions/raise` |
| Exception CAB approval | Risk / Compliance | Compliance Head, CIO | `/mvp/exception-governance`, `/mvp/grc/action` |
| Observation escalation | Compliance / Leadership | App Owner, Auditor, CIO | `/workflow/escalate`, `/workflow/leadership/review` |
| Cross-tool remediation correlation | SOC / GRC | Auditor, CIO | `correlation_engine` → `/mvp/correlation` |
| Audit trail & notifications | GRC Platform | All roles | `audit_trail.log_event` |

### 5.5 Audit Driven Development (ADD) workflows

| Workflow name | Process owner | Actors | Baseline route / engine |
| --- | --- | --- | --- |
| Application onboarding → control scope | Enterprise Architecture | CIO, App Owner | `onboarding_engine` → `/mvp/onboarding` |
| Release gate evidence pull | AppSec CoE | App Owner, CI/CD | Integrations Hub → SonarQube/Checkmarx → AppSec controls |
| Pre-release control validation | AppSec CoE | App Owner | `control_validation_engine` (AppSec) → `/mvp/sdlc-gates` |
| Shift-left gap closure | App Owner | App Owner | Checklist-to-Evidence stages 2–6, scoped to AppSec |
| AI feature release gate | AI CoE | App Owner, Model Risk | AI Governance controls + Model Registry → `/mvp/ai-registry` |

### 5.6 AI Governance workflows

| Workflow name | Process owner | Actors | Baseline route / engine |
| --- | --- | --- | --- |
| Prompt audit logging | AI CoE | All copilot users | `generate_prompt_audit` → `/mvp/ai-governance` |
| Hallucination triage | Model Risk | AI CoE, Compliance Head | `generate_hallucination_alerts` |
| Unsafe prompt quarantine | Security / AI CoE | Security Officer | `generate_unsafe_prompts` |
| Token budget enforcement | FinOps / AI CoE | CIO | `generate_token_usage` |
| Copilot governance query | All roles | All roles | `chatbot_engine` (policy-aware) |
| Model registration & approval | AI CoE | Admin, Compliance Head | `/mvp/ai-registry` *(new)* |

---

## 6. Role Ownership

Roles defined in baseline §3. This section maps **each role to its Home dashboard, primary nav groups, and key workflows**.

### 6.1 Role catalog

| Role key | Display name | Login landing | Executive read-only |
| --- | --- | --- | --- |
| `owner` | App Owner | `/dashboard` (Work Queue) | No |
| `auditor` | Auditor | `/dashboard` (Work Queue) | No |
| `cio` | CIO | `/dashboard/cio` (Executive Command) | Yes |
| `vertical_head` | Vertical Head | `/dashboard/vertical-head` | Yes |
| `compliance_head` | Compliance Head | `/dashboard/compliance-head` | Yes |
| `compliance_officer` | Compliance Officer | `/dashboard/compliance-head` *(normalized to compliance_head)* | Yes |
| `functional_head` | Functional Head | `/dashboard/functional-head` | Yes |
| `enterprise_admin` | Enterprise Admin | `/mvp/framework-admin` *(internal)* | No |

### 6.2 Role → navigation access matrix

| Nav group | Owner | Auditor | CIO | Vertical Head | Compliance Head | Functional Head | Admin |
| --- | --- | --- | --- | --- | --- | --- | --- |
| G1 Home | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| G2 Compliance & Controls | ✓ | ✓ | R | R | ✓ | R | ✓ |
| G3 Evidence Operations | ✓ | ✓ | R | R | R | R | ✓ |
| G4 Continuous Audit | R | ✓ | R | R | ✓ | R | R |
| G5 Governance & Risk | ✓ | ✓ | ✓ | R | ✓ | R | R |
| G6 AI & SDLC Governance | ✓ | R | ✓ | R | ✓ | ✓ | ✓ |
| G7 Enterprise Insights | R | R | ✓ | ✓ | ✓ | R | R |
| G8 Platform Administration | — | R† | R | — | ✓ | — | ✓ |

**Legend:** ✓ = full access · R = read-only · — = no access · † = Auditor has Framework Onboarding Review only

### 6.3 Role → primary workflows

| Role | Primary workflows owned / executed |
| --- | --- |
| **App Owner** | Upload evidence · Submit to auditor · Internal review · Resubmission · Close gap · Raise exception · SDLC gate remediation |
| **Auditor** | Approve/reject/clarify evidence · Request re-upload · Mock audit · Observation closure · Framework onboarding review · Assign owner |
| **CIO** | Executive review · Leadership escalation · Risk acceptance · AI governance oversight · Enterprise reporting |
| **Vertical Head** | Vertical compliance oversight · Leadership review · Regional escalation |
| **Compliance Head** | Completeness oversight · Exception approval · Framework onboarding · Reuse decisions · Regulatory mapping · Governance analytics |
| **Compliance Officer** | Same as Compliance Head (normalized role) |
| **Functional Head** | Domain application oversight · SDLC gate monitoring · Onboarding progress |
| **Enterprise Admin** | Framework administration · Integrations configuration · Application onboarding |

### 6.4 Role → application data scope

From baseline `role_filter_scope.py` / `chatbot_context_engine.ROLE_APP_SCOPE`:

| Role | Scoped applications |
| --- | --- |
| App Owner | Net Banking, Mobile Banking, Payments *(subset)* |
| Vertical Head | Net Banking, Mobile Banking, UPI, Payments, Treasury |
| Functional Head | Treasury, Loan System, Payments |
| Auditor, CIO, Compliance Head | All 20 banking applications |

### 6.5 Role → permission summary

From baseline `role_permissions.py`:

| Capability | Owner | Auditor | Executive roles | Admin |
| --- | --- | --- | --- | --- |
| Upload evidence | ✓ | | | |
| Submit to auditor | ✓ | | | |
| Review / approve / reject | | ✓ | | ✓ |
| Request re-upload | | ✓ | | |
| Raise exception | ✓ | ✓ | ✓ | ✓ |
| Escalate | ✓ | ✓ | ✓ | ✓ |
| Assign owner | ✓ | ✓ | ✓ | ✓ |
| Manage frameworks | | | ✓* | ✓ |
| Export reports | ✓ | ✓ | ✓ | ✓ |

---

## 7. Module Ownership

**Module** = a navigable surface backed by one or more baseline engines, with a single business accountable party.

| Module | Module key | Business owner | Technical owner (engine) | Primary route |
| --- | --- | --- | --- | --- |
| Work Queue Dashboard | `main_dashboard` | GRC Operations | `workflow_module`, `evidence_workflow_engine` | `/dashboard` |
| Executive Command Center | `role_dashboard` | CIO Office | `enterprise_context`, `executive_analytics_engine` | `/dashboard/cio` |
| Vertical Command Center | `role_dashboard` | Business Vertical | `enterprise_context`, `analytics_module` | `/dashboard/vertical-head` |
| Compliance Posture Dashboard | `role_dashboard` | Compliance Office | `governance_completeness_engine` | `/dashboard/compliance-head` |
| Domain Command Center | `role_dashboard` | Functional IT | `enterprise_context`, `onboarding_engine` | `/dashboard/functional-head` |
| Framework Catalog Browser | `framework_catalog_browser` | Compliance Architecture | `framework_catalog`, `search_module`, `global_filter_engine` | `/mvp/framework-catalog` |
| Framework Command Center | `framework_page` | Framework owner | `framework_dashboards`, `framework_catalog` | `/framework/{name}` |
| Control Completeness | `completeness` | Compliance Office | `governance_completeness_engine`, `missing_evidence_engine` | `/mvp/completeness` |
| Regulatory Mapping | `regulatory_mapping` | Compliance Architecture | `framework_intelligence`, `mvp_regulatory` | `/mvp/regulatory` |
| Evidence Reuse | `reuse` | Compliance Architecture | `framework_intelligence`, `enterprise_mock_service` | `/mvp/reuse` |
| Lifecycle Tracker | `lifecycle` | GRC Operations | `governance_lifecycle_engine` | `/mvp/lifecycle` |
| Continuous Controls Monitoring | `ccm` | Compliance Office | `control_validation_engine`, `scheduler_module` | `/mvp/ccm` |
| My Work Queue | `work_queue` | GRC Operations | `workflow_module` | `/dashboard?tab=queue` |
| Evidence Collection | `scheduler` | Platform Engineering | `scheduler_module`, `scheduler_intelligence` | `/mvp/scheduler` |
| Upload & Ingestion | `upload` | App Owners | `evidence_repository`, `evidence_routes` | `/mvp/upload` |
| Evidence Health | `evidence_health` | GRC Operations | `evidence_health_engine` | `/mvp/evidence-health` |
| Evidence Discovery | `search` | GRC Platform | `search_module`, `global_filter_engine` | `/mvp/search` |
| Approval Analytics | `evidence_approval` | Internal Audit | `evidence_approval_engine` | `/mvp/evidence-approval` |
| Evidence Review *(workflow)* | `evidence_review` | Internal Audit / App Owner | `evidence_review`, `evidence_workflow_engine` | `/evidence/review` |
| Audit Command Center | `audit_prep` | Audit PMO | `audit_schedule_engine`, `audit_prep_data` | `/mvp/audit-prep` |
| Mock Audit | `mock_audit` | Internal Audit | `operational_workflows` | `/mvp/workflow/mock-audit` |
| Audit History | `audit_history` | Audit PMO | `ecs_mock_engine`, `analytics_module` | `/mvp/audit-history` |
| Audit Packs & Reports | `reports` | Audit PMO | `reporting_module`, `gap_export_engine` | `/mvp/reports` |
| Risk Register | `risk_register` | Enterprise Risk | `enterprise_grc` | `/mvp/risk-register` |
| Exceptions & TD | `exceptions_td` | App Owners + Risk | `exception_state_engine`, `enterprise_grc` | `/mvp/exceptions` |
| Exception Governance | `exception_governance` | Risk / CAB | `enterprise_grc`, `exception_state_engine` | `/mvp/exception-governance` |
| Governance Analytics | `governance_analytics` | GRC Analytics | `governance_intelligence`, `governance_data_enrichment` | `/mvp/governance-analytics` |
| Cross-Tool Correlation | `correlation` | SOC / GRC Fusion | `correlation_engine`, `integrations_module` | `/mvp/correlation` |
| AI Governance Posture | `ai_governance` | AI CoE / Model Risk | `ecs_mock_engine` (AI slice) | `/mvp/ai-governance` |
| SDLC Compliance Gates | `sdlc_gates` | AppSec CoE | `control_validation_engine`, AppSec framework | `/mvp/sdlc-gates` |
| Model & Prompt Registry | `ai_registry` | AI CoE | *(new entity model)* | `/mvp/ai-registry` |
| AI Governance Framework | `framework_ai_governance` | AI CoE / Compliance Architecture | `framework_catalog` *(new entry)* | `/framework/AI Governance` |
| Enterprise Overview | `enterprise` | CIO Office | `enterprise_grc`, `analytics_module` | `/mvp/enterprise` |
| Executive Heatmaps | `executive_heatmaps` | CIO Office | `enterprise_grc`, `executive_analytics_engine` | `/mvp/heatmaps` |
| Application Comparison | `comparison` | Compliance / EA | `comparison_engine`, `analytics_module` | `/mvp/comparison` |
| Pan-India Posture | `pan_india` | Regional Compliance | `ecs_state.PAN_INDIA_REGIONS`, `enterprise_grc` | `/mvp/pan-india` |
| Trends & Analytics | `trends` | GRC Analytics | `analytics_module`, `framework_trends_engine` | `/mvp/trends` |
| Application Onboarding | `onboarding` | Enterprise Architecture | `onboarding_engine`, `application_governance` | `/mvp/onboarding` |
| Framework Loader | `framework_loader` | Compliance Architecture | `framework_loader_service`, `framework_intelligence` | `/mvp/framework-loader` |
| Framework Administration | `framework_admin` | Compliance Architecture | `framework_onboarding_engine` | `/mvp/framework-admin` |
| Integrations Hub | `integrations_hub` | Platform Engineering | `integrations_module`, `integration_hub_executive_engine` | `/mvp/integrations-hub` |
| CMDB & Assets | `cmdb` | IT Operations | `enterprise_grc`, ServiceNow CMDB connector | `/mvp/cmdb` |
| AI Audit Copilot *(cross-cutting)* | `chatbot` | GRC Platform | `chatbot_engine`, `chatbot_enhanced`, `chatbot_context_engine` | Global dock |
| Demo Overview *(non-production)* | `demo_overview` | Product / Sales | `ecs_mock_engine.build_demo_overview` | `/mvp/demo-overview` |

---

## 8. Which Existing Modules Are Reused

These baseline modules (baseline §2, §4, §6) are **retained without new backend engines**. V1 changes grouping, naming, route composition, or nav promotion only.

| V1 module / surface | Reused baseline module(s) | Reuse type |
| --- | --- | --- |
| Work Queue Dashboard | `dashboard.html`, `workflow_module` | Retain route; promote queue emphasis |
| All role Home dashboards | `cio_dashboard`, `dashboard_vertical_head`, `dashboard_compliance_head`, `dashboard_functional_head` | Retain unchanged |
| Framework Command Center | `framework.html`, `framework_dashboards`, `framework_catalog` | Retain; access via catalog |
| Control Completeness | `mvp_completeness`, `governance_completeness_engine` | Retain |
| Regulatory Mapping | `mvp_regulatory`, `framework_intelligence` overlap matrix | Retain; matrix as widget |
| Evidence Reuse | `mvp_reuse`, `framework_intelligence` | Retain |
| Lifecycle Tracker | `mvp_lifecycle`, `governance_lifecycle_engine` | Retain |
| Evidence Collection | `mvp_scheduler`, `scheduler_module` | Retain |
| Upload & Ingestion | `mvp_upload` / `mvp_bulk_upload`, `evidence_repository` | Retain |
| Evidence Health | `mvp_evidence_health`, `evidence_health_engine` | Retain |
| Evidence Discovery | `mvp_search`, `search_module` | Retain; rename from "Search" |
| Approval Analytics | `mvp_evidence_approval`, `evidence_approval_engine` | Retain |
| Evidence Review workflow | `evidence_review.html`, `evidence_workflow_engine`, `resubmission.py` | Retain |
| Audit Command Center | `mvp_audit_prep`, `audit_schedule_engine` | Retain; rename in nav |
| Mock Audit | `mvp_workflow_mock_audit`, `operational_workflows` | Retain |
| Audit Packs & Reports | `mvp_reports`, `reporting_module`, audit package APIs | Retain |
| Risk Register | `mvp_risk_register`, `enterprise_grc` | Retain |
| Exceptions & TD | `mvp_exceptions`, `exception_state_engine` | Retain |
| Exception Governance | `mvp_exception_governance`, `enterprise_grc` | Retain |
| Governance Analytics | `mvp_governance_analytics`, `governance_intelligence` | Retain |
| Cross-Tool Correlation | `mvp_correlation`, `correlation_engine` | Retain |
| Enterprise Overview | `mvp_enterprise`, `enterprise_grc` | Retain |
| Executive Heatmaps | `mvp_heatmaps`, `executive_analytics_engine` | Retain |
| Application Comparison | `mvp_comparison`, `comparison_engine` | Retain |
| Pan-India Posture | `mvp_pan_india`, `PAN_INDIA_REGIONS` | Retain |
| Trends & Analytics | `mvp_trends`, `analytics_module` | Retain |
| Application Onboarding | `mvp_onboarding`, `onboarding_engine` | Retain |
| Framework Loader | `framework_loader.html`, `framework_loader_service` | Retain |
| Framework Administration | `mvp_framework_admin`, `framework_onboarding_engine` | Retain |
| Integrations Hub | `mvp_integrations_hub`, `integrations_module` | Retain; absorbs legacy Integrations |
| CMDB & Assets | `mvp_cmdb`, `enterprise_grc` | Retain |
| AI Audit Copilot | `chatbot_engine`, `chatbot_enhanced`, `chatbot_context_engine`, `chatbot_nav` | Retain; global dock |
| Workflow sub-screens | close-gap, assign-owner, upload-missing, mock-audit | Retain as drill-down routes |
| Global filter engine | `global_filter_engine`, `standard_filter_engine` | Retain; shared across all modules |
| ITPP domain experience | `itpp_module`, ITPP framework page | Retain as reference pattern |
| Demo Overview | `mvp_demo_overview`, `ecs_mock_engine` | Retain; demote from production nav |

### Reuse composition (new route, existing engines only)

| V1 composed surface | Engines composed | No new backend required |
| --- | --- | --- |
| Framework Catalog Browser | `framework_catalog` + `search_module` + `global_filter_engine` | Yes |
| Audit History | `ecs_mock_engine.generate_audit_history` + trends slice | Yes |
| SDLC Compliance Gates | AppSec framework + `control_validation_engine` + Integrations Hub feeds + `onboarding_engine` scope | Yes |
| AI Governance Posture | `ecs_mock_engine.generate_ai_governance` + related `/api/demo/*` APIs | Yes *(promote APIs to production namespace)* |
| Continuous Controls Monitoring | `control_validation_engine` + `scheduler_module` + `framework_trends_engine` | Yes |
| Audit Packs filtered view | `reporting_module` with audit/regulatory category filter | Yes |

---

## 9. Which New Modules Are Introduced

Net-new modules that **cannot** be achieved by recomposing existing baseline engines alone.

| # | Module | Module key | Route | Nav group | Why net-new | Builds on |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | **Framework Catalog Browser** | `framework_catalog_browser` | `/mvp/framework-catalog` | G2 Compliance & Controls | Replaces 15-item flat nav; needs searchable catalog UX | Existing engines; new presentation route |
| 2 | **AI Governance Posture** | `ai_governance` | `/mvp/ai-governance` | G6 AI & SDLC Governance | Currently demo-only (baseline §5.3); needs production page | `ecs_mock_engine` AI APIs → production route |
| 3 | **SDLC Compliance Gates** | `sdlc_gates` | `/mvp/sdlc-gates` | G6 AI & SDLC Governance | ADD requires single shift-left entry point | Composed from existing; new composed dashboard |
| 4 | **Model & Prompt Registry** | `ai_registry` | `/mvp/ai-registry` | G6 AI & SDLC Governance | Inventory of approved models/prompts for release gates | **New entity model**; UX pattern from Framework Admin |
| 5 | **Continuous Controls Monitoring** | `ccm` | `/mvp/ccm` | G2 Compliance & Controls | Baseline §11.7.33; scheduled validation + drift visualization | New presentation over `control_validation_engine` |
| 6 | **Audit History** | `audit_history` | `/mvp/audit-history` | G4 Continuous Audit | Multi-year audit trends deserve dedicated surface under Continuous Audit | Composed from `ecs_mock_engine` + trends |
| 7 | **AI Governance Framework** | `framework_ai_governance` | `/framework/AI Governance` | G2 via catalog | Baseline §11.7.32; AI Governance as first-class catalog entry | **New catalog entry** in `FRAMEWORK_CATALOG` |

### New modules that are NOT required (deferred to Phase 2)

| Proposed module | Reason deferred |
| --- | --- |
| Regulator read-only dashboard | Filtered view of Enterprise + Regulatory frameworks; not a new module |
| Vendor / Third-Party Risk module | Currently a control theme only (baseline §11.7.31); needs vendor entity model first |
| Audit response narrative generator | Copilot capability, not a nav destination (baseline §11.7.34) |
| Mobile auditor approval surface | UX variant of Evidence Review workflow, not a new module |

---

## 10. Which Duplicate Modules Should Be Retired

These surfaces **must not exist as separate nav items or modules** in V1. Functionality is absorbed into the target module listed.

| Retire | Absorbed into | Reason |
| --- | --- | --- |
| **Flat 15-framework sidebar list** | Framework Catalog Browser + Framework Command Center | Nav bloat; does not scale (baseline §2.3) |
| **Integrations** (`/mvp/integrations`) | Integrations Hub (`/mvp/integrations-hub`) | Duplicate connector surface (baseline §10.2) |
| **Demo Overview in production nav** | Hidden demo layer only | Sales/QA route retained; not an operating module |
| **Separate "Audit Calendar" nav item** | Audit Command Center → Calendar section | Already in `audit_schedule_engine.generate_audit_calendar` |
| **Separate "Audit Pipeline" nav item** | Audit Command Center → Pipeline section | Already in `generate_preparation_pipeline` |
| **Separate "Observation Management" module** | Lifecycle Tracker + My Work Queue | Observations flow through existing workflow engines |
| **Separate "Evidence Management System" module** | Evidence Operations group (G3) | Upload + Health + Search + Approval already cover this |
| **New "Compliance Dashboard" module** | Compliance Posture Dashboard + Completeness + Governance Analytics | Would duplicate compliance_head dashboard |
| **"CIO Executive Snapshot" module** | Executive Command Center + Enterprise Overview | Exists only as Demo Overview slice |
| **"Risk Heatmap" standalone module** | Executive Heatmaps + Enterprise Insights | `build_risk_heatmap()` is a widget, not a product |
| **"Evidence Lineage Explorer" module** | Evidence Reuse + Lifecycle Tracker | `generate_evidence_lineage()` + reuse traceability |
| **"Baselining Dashboard" module** | Audit Command Center (Baselining History) + OS/DB/Nginx framework pages | Already in audit prep + framework pages |
| **"VAPT Dashboard" standalone** | VAPT Framework Command Center + Governance Analytics | Framework page is canonical surface |
| **"ServiceNow Module"** | Integrations Hub + Cross-Tool Correlation | ServiceNow is a connector, not a module |
| **"Mock Data Dashboard" (production)** | Demo Overview (hidden) | Not for production users |
| **"Framework Comparison" module** | Regulatory Mapping + Framework Intelligence overlap matrix | One crosswalk surface |
| **"Approval Workflow" nav item** | Evidence Review workflow + Approval Analytics dashboard | Workflow is a process, not a destination |
| **"Upload Missing Evidence" nav item** | Trigger from Completeness gap row → workflow route | Workflow sub-screen, not nav item |
| **"Control Library" module** | Framework Catalog + Framework pages + Framework Loader | Catalog browser replaces this concept |
| **"AI Copilot Dashboard"** | Global chatbot dock | Cross-cutting; not a nav destination |
| **"Compliance Trends" separate module** | Trends & Analytics with compliance filter tab | `mvp/trends` already covers this |
| **Merged "Exception Management" (TD + Governance)** | Keep Exceptions & TD + Exception Governance separate | Different actors: operational vs CAB |
| **"Secure SDLC Platform" product module** | SDLC Compliance Gates + AppSec framework | Do not brand as separate product |
| **Legacy nav group: "Executive Overview"** | Split into Home (G1) + Enterprise Insights (G7) + hidden Demo | Replaced by capability groups |
| **Legacy nav group: "Operations"** | Split into Evidence Operations (G3) + Platform Admin (G8) | Replaced by capability groups |
| **Legacy nav group: "Governance"** | Split into Compliance & Controls (G2) + Evidence Operations (G3) + Continuous Audit (G4) | Replaced by capability groups |
| **Legacy nav group: "Enterprise GRC"** | Split into Governance & Risk (G5) + Enterprise Insights (G7) + Platform Admin (G8) | Replaced by capability groups |
| **Legacy nav group: "Frameworks" (flat list)** | Framework Catalog (G2) + Platform Admin (G8) | Replaced by catalog pattern |

### Retirement summary

| Category | Count |
| --- | --- |
| Nav items retired | 2 (`Integrations`, flat framework list) |
| Nav groups retired | 5 (Executive Overview, Frameworks flat, Operations, Governance, Enterprise GRC) |
| Nav groups introduced | 8 (Home, Compliance & Controls, Evidence Operations, Continuous Audit, Governance & Risk, AI & SDLC Governance, Enterprise Insights, Platform Administration) |
| Proposed modules blocked | 22 (see table above) |
| Net-new modules | 7 (see §9) |

---

## Appendix A — Current → V1 Navigation Mapping

| Baseline nav item (§2) | V1 destination | Action |
| --- | --- | --- |
| Main Dashboard | G1 Home → Work Queue Dashboard | Retain |
| Evidence Analytics (CIO) | G1 Home → Executive Command Center | Retain |
| Vertical Head Dashboard | G1 Home → Vertical Command Center | Retain |
| Compliance Dashboard | G1 Home → Compliance Posture Dashboard | Retain |
| Functional Head Dashboard | G1 Home → Domain Command Center | Retain |
| Demo Overview | Hidden demo layer | Demote from production nav |
| Enterprise | G7 Enterprise Insights → Enterprise Overview | Retain |
| Pan India | G7 Enterprise Insights → Pan-India Posture | Retain |
| Reports | G4 Continuous Audit → Audit Packs & Reports | Retain; add filter |
| Trends | G7 Enterprise Insights → Trends & Analytics | Retain |
| 15 framework sidebar links | G2 Framework Catalog Browser → `/framework/{name}` | Replace flat list |
| Framework Loader | G8 Platform Administration | Retain |
| Framework Administration | G8 Platform Administration | Retain |
| Scheduler | G3 Evidence Operations → Evidence Collection | Retain |
| Bulk Upload | G3 Evidence Operations → Upload & Ingestion | Retain |
| Integrations | **Retired** → Integrations Hub | Merge |
| Onboarding | G8 Platform Administration | Retain |
| Audit Prep | G4 Continuous Audit → Audit Command Center | Elevate + rename |
| Evidence Health | G3 Evidence Operations | Retain |
| Evidence Reuse | G2 Compliance & Controls | Move from Governance |
| Lifecycle | G2 Compliance & Controls | Move from Governance |
| Completeness | G2 Compliance & Controls → Control Completeness | Rename |
| App Comparison | G7 Enterprise Insights | Move from Governance |
| Search | G3 Evidence Operations → Evidence Discovery | Rename |
| Evidence Approval Analytics | G3 Evidence Operations → Approval Analytics | Rename |
| Risk Register | G5 Governance & Risk | Retain |
| Exceptions / TD | G5 Governance & Risk | Retain |
| Exception Governance | G5 Governance & Risk | Retain |
| CMDB / Assets | G8 Platform Administration | Move from GRC |
| Regulatory Mapping | G2 Compliance & Controls | Move from GRC |
| Executive Heatmaps | G7 Enterprise Insights | Move from GRC |
| Integrations Hub | G8 Platform Administration | Retain; absorbs Integrations |
| Cross-Tool Correlation | G5 Governance & Risk | Retain |
| Governance Analytics | G5 Governance & Risk | Retain |
| *(not in baseline nav)* | G6 AI Governance Posture | **New** |
| *(not in baseline nav)* | G6 SDLC Compliance Gates | **New** |
| *(not in baseline nav)* | G6 Model & Prompt Registry | **New** |
| *(not in baseline nav)* | G2 Framework Catalog Browser | **New** |
| *(not in baseline nav)* | G2 Continuous Controls Monitoring | **New** |
| *(not in baseline nav)* | G4 Audit History | **New** |

---

## Appendix B — AI & SDLC Governance Placement

AI SDLC Governance occupies **three layers** in V1:

```
Layer A — Framework Catalog
  └── AI Governance framework entry (/framework/AI Governance)
      Controls: model registry, prompt audit, bias review, training data lineage,
                retraining cadence, human-in-the-loop

Layer B — Nav Group G6 (AI & SDLC Governance)
  ├── AI Governance Posture      → runtime monitoring (prompts, hallucinations, tokens)
  ├── SDLC Compliance Gates      → Audit Driven Development / shift-left
  └── Model & Prompt Registry    → approved inventory for release gates

Layer C — Cross-cutting enforcement
  ├── AI Audit Copilot (global dock) — policy-aware queries
  ├── control_validation_engine — AI-specific checks
  ├── Integrations Hub — LLM provider / MLOps connectors
  └── Evidence Operations — AI audit artefacts enter checklist-to-evidence spine
```

| Concern | Owner surface |
| --- | --- |
| Traditional AppSec (SAST/DAST/SCA) | AppSec Framework + SDLC Compliance Gates |
| AI/ML model risk | AI Governance Framework + AI Governance Posture |
| Prompt / LLM runtime | AI Governance Posture |
| Release evidence for both | Evidence Operations → Audit Pack export |

---

## Appendix C — Document Governance

| Field | Value |
| --- | --- |
| **Authoritative for** | Left navigation, module boundaries, ownership, reuse/retirement decisions |
| **Does not supersede** | `ECS_ARCHITECTURE_BASELINE.md` for technical implementation detail |
| **Change control** | Any new nav item requires entry in §3, §7, and ownership in §4–§6 |
| **Next review trigger** | Addition of net-new framework, new role, or production persistence layer |
| **Version history** | V1.0 — Initial authoritative IA (May 2026) |

---

**End of ECS Information Architecture V1**
