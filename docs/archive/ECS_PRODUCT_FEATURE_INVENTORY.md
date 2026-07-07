# ECS Product Feature Inventory (Phase 2)

**Audit date:** 2026-06-17. Every ECS feature/page with **Purpose · Persona · Inputs · Outputs · KPIs · Drilldowns · Reports · Data source · Business value**. Grounded in the route registrars and engines. For deep per-screen detail see `docs/product/PRODUCT_MANUAL_ECS_SCREEN_CATALOG.md`; for KPI formulas see `docs/product/PRODUCT_MANUAL_ECS_KPI_DICTIONARY.md`.

**Data-source legend:** `catalog` = static framework library (`framework_catalog.py`); `demo` = deterministic demo metrics/mocks (`demo_metrics.py`, `*_mock*.py`); `repo` = PostgreSQL evidence repository (`ecs_platform`, with demo fallback); `state` = live workflow state (`ecs_state.py`, `evidence_workflow_engine.py`).

---

## Group 1 — Executive Overview

| Feature (URL) | Purpose | Persona | Inputs | Outputs / KPIs | Drilldowns | Reports | Data | Business value |
|---|---|---|---|---|---|---|---|---|
| Main Dashboard (`/dashboard`) | Personal work queue | Owner / Auditor | role, user | pending/resubmit/observation KPIs; queues | `/framework/{n}`, `/evidence/review` | — | state | Each user knows their next action |
| CIO Dashboard (`/dashboard/cio`) | Enterprise posture | CIO | role | enterprise compliance, audit completion, readiness, VAPT, AI alerts; exec charts | `/api/ecs/universal-drill` | CIO Enterprise Pack | demo+state | Board-level visibility in one screen |
| Vertical/Functional/Compliance Head dashboards | Scoped posture | Heads | role | scoped readiness, gaps, comparison | comparison, enterprise | scoped exports | demo+state | Mid-tier accountability views |
| ROI Center (`/mvp/roi`) | Quantify value | CIO/Exec | scenario | annual value, hours saved, FTE, payback, ROI readiness | ROI storyboard | — | `config/roi.yaml` (`roi/workbook.py`) | Justifies investment |
| Demo Overview (`/mvp/demo-overview`) | Demo cockpit | Demo/CIO | framework, app, owner | apps, frameworks, controls, evidence, SN tickets, AI prompts, VAPT, drift tiles | `/api/demo/*` | — | demo | One-screen story for prospects |
| Enterprise (`/mvp/enterprise`) | Org KPIs | CIO/Heads | filters | BU compliance/risk/gaps bars; framework maturity | std filter drills | — | demo (`BUSINESS_UNITS`) | BU accountability + maturity |
| Pan India (`/mvp/pan-india`) | Regional posture | CIO/Vertical | region | zone readiness, SLA breaches, critical obs | region drills | Pan India report (CSV/PDF) | demo (`PAN_INDIA_REGIONS`) | Branch/zone compliance visibility |
| Reports (`/mvp/reports`) | Export center | Auditor/CIO/Compliance | filters, format | export distribution + generation trend | `/mvp/reports/view/{t}` | **30 audit packs** + 5 HTML reports | demo+repo | Regulator-ready packs on demand |
| Trends (`/mvp/trends`) | Historical analytics | CIO/Compliance | framework/app/period filters | coverage, observation net, rejection rate, SLA, aging | `/mvp/api/analytics-intel` | — | demo (`trends_analytics_engine`) | Trajectory & early warning |

## Group 2 — Frameworks

| Feature | Purpose | Persona | Inputs | Outputs / KPIs | Drilldowns | Reports | Data | Business value |
|---|---|---|---|---|---|---|---|---|
| Framework page (`/framework/{name}`) | Per-framework compliance | Compliance/Auditor/FW Owner/Owner | fw_tab, fw_app, itpp_* | 6 KPI tiles (e.g. PCI Maturity, QSA Readiness), app grid, control/evidence tables | `/api/framework/{kpi,workflow,row,tab}-drill` | framework validation pack | catalog+demo | Single pane per regulation (15 frameworks) |
| Framework Loader (`/mvp/framework-loader`) | Upload/activate control library | Compliance/FW Owner | framework_id, file | coverage scan, control drill | `/api/framework-loader/*` | onboarding analysis | catalog | Add frameworks without code |
| Framework Admin (`/mvp/framework-admin`) | Onboarding lifecycle | FW Owner/Compliance/CIO/Admin | wizard, framework_id | onboarded/active/pending/imported KPIs | `/api/framework-onboarding/{id}` | onboarding export (PDF/Excel/CSV) | catalog | Governed framework intake + reuse |

## Group 3 — Operations

| Feature | Purpose | Persona | Inputs | Outputs / KPIs | Drilldowns | Reports | Data | Business value |
|---|---|---|---|---|---|---|---|---|
| Scheduler (`/mvp/scheduler`) | Automated collection | Ops Owner/Admin | run/retry/pause/resume | success rate, jobs, failures; collection bars | module/universal drill | — | demo (`scheduler_intelligence`) | Continuous evidence freshness |
| Predefined Queries (`/mvp/predefined-queries`) | Query-driven control catalog | Ops Owner | q, framework, sort | Total Controls, Queries, Manual, FW Covered, Unsupported | `/predefined-queries/detail` | — | `predefined_queries_engine` | Library of automated control checks |
| Integration Health (`/mvp/integration-health`) | Connector health | Admin/Ops | — | connector status, collection counts | `/api/platform/health` | health export | repo (`ecs_platform/ingestion`) | Trust in automated collection |
| Evidence Explorer (`/mvp/evidence-explorer`) | Browse repo evidence | Admin/Auditor | application, source, type | evidence rows + correlations | `/api/platform/evidence` | — | repo | Trace any artifact to source |
| AI Ops Assistant (`/mvp/ai-ops-assistant`) | Governance copilot | Ops Owner | chat query | investigation, response modes | `/summary/{mode}` | — | `ai_ops_assistant_engine` | Faster incident/audit answers |
| Bulk Upload (`/mvp/upload`) | Mass evidence import | Owner | files, fw, app, control | validation/dedup/auto-map | completeness | — | state | Onboard evidence at scale |
| Integrations (`/mvp/integrations`) | External connectors | Ops Owner | sync | connector list + sync | — | — | `integrations_module` | Source-system coverage |
| Onboarding (`/mvp/onboarding`) | App onboarding | Ops Owner | app metadata | simulate/register | `/api/onboarding/*` | onboarding summary (text) | `onboarding_engine` | Governed app intake |

## Group 4 — Governance

| Feature | Purpose | Persona | Inputs | Outputs / KPIs | Drilldowns | Reports | Data | Business value |
|---|---|---|---|---|---|---|---|---|
| Audit Prep (`/mvp/audit-prep`) | Audit readiness cockpit | Auditor/Compliance | fw/app/risk/status filters | readiness heatmap, upcoming audits | `/api/audit-prep/*` | **audit package** (JSON/text), mock-audit report | `audit_prep_data` | Walk into audits prepared |
| Evidence Health (`/mvp/evidence-health`) | Quality/freshness scoring | Owner/Governance | framework/app/status/issue | health score, missing, expiring, rejected, stale | module/universal drill | — | `evidence_health_engine` | Catch decay before audit |
| Evidence Reuse (`/mvp/reuse`) | Cross-framework reuse | Compliance | — | reuse %, controls covered, reuse factor | reuse graph | reuse-mapping report | `framework_intelligence` | Collect once, satisfy many |
| Lifecycle (`/mvp/lifecycle`) | Evidence lifecycle | Compliance | — | lifecycles, records, observations, remediations | charts | — | `governance_lifecycle_engine` | Govern evidence aging |
| Completeness (`/mvp/completeness`) | Gap analysis | Compliance/Owner | — | control maturity, audit readiness (dynamic) | `/mvp/workflow/*` | — | `governance_completeness_engine` | Find & close coverage gaps |
| App Comparison (`/mvp/comparison`) | Posture comparison | Vertical/Functional/Compliance | export_id | readiness/failed/closure trends | export-gaps | **gap export** (PDF/Excel/CSV) | `comparison_engine` | Benchmark apps, target worst |
| Search (`/mvp/search`) | Evidence discovery | Auditor/Compliance | q, fw, app, owner, status | search results, reuse links | reuse | — | `search_module` | Find any evidence fast |
| Evidence Approval Analytics (`/mvp/evidence-approval`) | Approval throughput | Auditor/Governance/FW Owner | — | approval success %, rejection rate, validation time, reviewer workload | charts | approval summary (CSV/PDF) | `evidence_approval_engine` | Manage reviewer SLAs |
| Evidence Review (`/evidence/review`) | Approve/reject workspace | Auditor/Owner | evidence_id, control | review actions + audit trail | — | — | state+`evidence_review` | Core audit decision point |

## Group 5 — Evidence Governance (platform, repo-backed)

| Feature | Purpose | Persona | Outputs / KPIs | Drilldowns | Data | Business value |
|---|---|---|---|---|---|---|
| Role Scorecard (`/mvp/platform/scorecard`) | Role-scoped scorecard | All | apps, evidence, reuse %, coverage, compliance score | `/api/platform/scorecard` | repo | Personalized governance posture |
| Executive Summary (`/mvp/platform/executive-summary`) | Platform exec summary | Exec | summary KPIs | `/api/platform/executive-summary` | repo | DB-backed exec view |
| Audit Readiness (`/mvp/platform/audit-readiness`) | Composite readiness | Auditor | readiness gauge (50/30/20) | `/api/platform/audit-readiness` | repo (`governance.py`) | Single readiness number |
| Application Onboarding/Inventory | Register/list apps | Admin/Ops | app records | `/application/{slug}` | repo | System of record for apps |
| Control / Framework Coverage | Coverage from evidence | Compliance | coverage % | `/api/platform/*coverage` | repo | True (not demo) coverage |
| Evidence Reuse / Lifecycle (platform) | DB reuse + lifecycle review | Compliance/Admin | reuse demos, lifecycle states | `/api/platform/*` | repo | Auditable reuse + freshness |
| Collection Scheduler (platform) | Connector schedules | Admin | schedule records | — | repo | Operationalize collection |
| AI Assistant (`/mvp/ai-assistant`) | Citation-grounded RAG | All (read) | q, app, framework | grounded answers + citations | `/api/platform/assistant` | repo+pgvector (`rag.py`) | Ask the evidence base in NL |

## Group 6 — Enterprise GRC

| Feature | Purpose | Persona | Outputs / KPIs | Drilldowns | Reports | Data | Business value |
|---|---|---|---|---|---|---|---|
| Risk Register (`/mvp/risk-register`) | Risk governance | Governance/Risk | severity dist, aging, open risks | `/api/grc-demo/risk/drill` | — | `grc_module_demo` | Enterprise risk visibility |
| Exceptions/TD (`/mvp/exceptions`) | TD workflow | Compliance/Owner | raise exception | — | TD register | `exception_state_engine` | Govern compensating controls |
| Exception Governance (`/mvp/exception-governance`) | TD lifecycle/CAB | Compliance | active/approved/expiring/high-risk | — | exception governance report | `exception_state_engine` | Control TD risk |
| CMDB/Assets (`/mvp/cmdb`) | Asset inventory | Admin | assets + compliance map | — | — | `enterprise_grc` | Asset-to-control mapping |
| Regulatory Mapping (`/mvp/regulatory`) | Crosswalk | Compliance | coverage by theme, overlap | — | — | `executive_analytics_engine` | Normalize across regulators |
| Executive Heatmaps (`/mvp/heatmaps`) | CIO heatmaps | CIO/MD | fw/app/BU/regional/SLA tiles | risk-register, completeness | — | `executive_analytics_engine` | Spot hotspots fast |
| Integrations Hub (`/mvp/integrations-hub`) | Integration orchestration | Admin | connector usage/health, exec bar | sync | — | `integration_health_engine` | Enterprise integration view |
| Cross-Tool Correlation (`/mvp/correlation`) | Incident→control chains | Admin | correlation chains | — | — | `correlation_engine` | Root-cause across tools |
| Governance Analytics (`/mvp/governance-analytics`) | Governance intel | CIO/Compliance | coverage, rejection, SLA intel | `/api/grc-demo/governance/*` | governance CSV | `governance_intelligence` | Enterprise governance trends |

## Group 7 — AI SDLC Governance

| Feature | Purpose | Persona | Outputs / KPIs | Drilldowns | Reports | Data | Business value |
|---|---|---|---|---|---|---|---|
| AI SDLC Home/Control Tower | SDLC governance entry + heatmap | AI SDLC Owner | readiness heatmap (fw×app) | `/api/ai-sdlc/control-tower/*` | — | `ai_sdlc_governance_mock` | Govern AI delivery gates |
| Stage worklists (Requirements→Go-Live) | Gate worklists | AI SDLC Owner/Auditor | stage activities, readiness | `/api/ai-sdlc/sdlc/*`, controlled-document | — | `ai_sdlc_workflow_engine` | Stage-gated assurance |
| Evidence Collection / Findings (AI SDLC) | Evidence + findings | AI SDLC Owner | coverage %, findings | evidence viewer, observation drill | — | `ai_sdlc_evidence_governance` | Evidence-backed gates |
| AI SDLC Reports | 6 executable reports | AI SDLC Owner | report tables | `/reports/{id}` | **6 AI SDLC reports** | `ai_sdlc_reports_engine` | AI delivery reporting |
| AI Governance Posture (`/mvp/ai-governance`) | AI compliance | AI Gov Owner | AI Compliance Score (6 dims), risk heatmap | `/api/ai-sdlc/posture/drill` | — | `ecs_ai_governance_drilldowns` | Govern AI risk posture |
| AI Registry (`/mvp/ai-registry`) | Model/prompt registry | AI Gov Owner | registry entries | `/registry/drill` | — | `ai_sdlc_knowledge_repository` | Inventory of AI assets |
| Governance Quality (`/mvp/governance-quality`) | Governance QA | Admin | data completeness, readiness, validation % | `/governance-scan` | — | `ecs_governance_qa_engine` | Self-heal governance data |

---

## Feature coverage summary

| Capability area | Pages | Status |
|---|---|---|
| Executive reporting | 9 | ✅ delivered |
| Frameworks (15) | 3 + per-framework | ✅ delivered |
| Operations / collection | 8 | ✅ delivered |
| Governance (evidence lifecycle) | 9 | ✅ delivered |
| Evidence Governance (repo-backed) | 12 | ✅ delivered (DB optional; demo fallback) |
| Enterprise GRC | 9 | ✅ delivered |
| AI SDLC + AI governance | 14 | ✅ delivered |
| Reports/exports | 30 packs + 5 HTML + 6 AI SDLC + gap/audit | ✅ delivered |

**Business-value thesis:** ECS's differentiating value is **"collect once, reuse everywhere"** — connectors + reuse intelligence + continuous readiness scoring, surfaced through persona-specific dashboards and one-click regulator packs. Every page above maps to that thesis.
