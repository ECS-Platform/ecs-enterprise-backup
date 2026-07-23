# ECS Master Product Manual

**Type:** Master product documentation. **No code/UI/DB changes.** **Grounding:** route registrars, module engines, `docs/product_manual/*`, `docs/AUDIT/*`. This manual is the **single entry point** to every ECS screen; deep per-screen detail (inputs/actions/exports) lives in [`docs/01-product/product/PRODUCT_MANUAL_ECS_SCREEN_CATALOG.md`](../product/PRODUCT_MANUAL_ECS_SCREEN_CATALOG.md) and screenshots in [`docs/01-product/product/screenshots/`](screenshots) — cross-referenced here to avoid duplication.

> **Canonical facts:** 15 frameworks · 305 controls · 702 evidence · 12 connectors · 9 RBAC roles · ~79 screens / 66 screenshots across 7 nav groups. (Demo seeds larger rounded datasets.)

**Per-screen attributes** (Purpose · Navigation · Persona · Business Value · Inputs · Outputs · KPIs · Drilldowns · Reports · Dependencies · Data Sources · APIs · Workflow Participation · Audit/Compliance/Executive Relevance) are tabulated below; the cross-referenced [Feature Inventory](../../05-archive/archive/ECS_PRODUCT_FEATURE_INVENTORY.md) carries Inputs/Outputs/Data/Drilldowns and the [Screen Catalog](../../05-archive/archive/AUDIT_ECS_SCREEN_CATALOG.md) carries Route/Dependencies/Doc/Screenshot.

---

## How to read this manual

Each screen row: **Screen — Route — Persona — Business value — KPIs — Workflow role — A/C/E relevance** (A=Audit, C=Compliance, E=Executive). Full Inputs/Outputs/Drilldowns/Reports/Dependencies/Data/APIs are in the linked AUDIT + product_manual docs (same screen names), keeping this manual navigable and non-duplicative.

## Group 1 — Executive Overview

| Screen | Route | Persona | Business value | KPIs | Workflow role | A/C/E |
|---|---|---|---|---|---|---|
| Login | `/` | All | Persona entry | — | entry | –/–/– |
| Main Dashboard | `/dashboard` | Owner/Auditor | Personal work queue | pending, resubmit, observations | Evidence approval | A/C/– |
| CIO Dashboard | `/dashboard/cio` | CIO | Enterprise posture | compliance %, audit completion, readiness, VAPT | ROI/Reporting | A/C/E |
| Vertical/Functional/Compliance Head | `/dashboard/{...}-head` | Heads | Scoped posture | scoped readiness, gaps | Comparison | A/C/E |
| ROI Center | `/mvp/roi` | CIO/Exec | Quantify value | annual value, hours, FTE, payback | ROI measurement | –/–/E |
| Demo Overview | `/mvp/demo-overview` | Demo/CIO | One-screen story | apps, fw, controls, evidence, AI, VAPT | — | A/C/E |
| Enterprise | `/mvp/enterprise` | CIO/Heads | BU posture | BU compliance/risk/maturity | — | –/C/E |
| Pan India | `/mvp/pan-india` | Vertical/CIO | Regional posture | zone readiness, SLA, critical obs | — | –/C/E |
| Reports | `/mvp/reports` | Auditor/CIO/Compliance | Export center | export mix, generation trend | Report generation | A/C/E |
| Trends | `/mvp/trends` | CIO/Compliance | Historical analytics | coverage, obs net, rejection, SLA, aging | — | A/C/E |

## Group 2 — Frameworks

| Screen | Route | Persona | Business value | KPIs | Workflow role | A/C/E |
|---|---|---|---|---|---|---|
| Framework page (15) | `/framework/{name}` | Compliance/Auditor/FW Owner | Per-regulation compliance | 6 KPI tiles per fw | Control validation | A/C/E |
| Framework Loader | `/mvp/framework-loader` | Compliance/FW Owner | Add control library | coverage scan | Framework onboarding | –/C/– |
| Framework Admin | `/mvp/framework-admin` | FW Owner/Compliance/Admin | Onboarding lifecycle | onboarded/active/pending/imported | Framework onboarding | A/C/– |

## Group 3 — Operations

| Screen | Route | Persona | Business value | KPIs | Workflow role | A/C/E |
|---|---|---|---|---|---|---|
| Scheduler | `/mvp/scheduler` | Ops/Admin | Automated collection | success rate, jobs, failures | Evidence collection | –/C/– |
| Predefined Queries | `/mvp/predefined-queries` | Ops | Query-driven controls | controls, queries, manual, unsupported | Evidence collection | A/C/– |
| Integration Health | `/mvp/integration-health` | Admin/Ops | Connector trust | connector status, counts | Evidence collection | –/–/– |
| Evidence Explorer | `/mvp/evidence-explorer` | Admin/Auditor | Browse repo evidence | evidence rows + correlations | Evidence lifecycle | A/C/– |
| AI Ops Assistant | `/mvp/ai-ops-assistant` | Ops | Governance copilot | investigation modes | — | –/–/– |
| Bulk Upload | `/mvp/upload` | Owner | Mass import | validation/dedup/map | Evidence collection | A/C/– |
| Integrations | `/mvp/integrations` | Ops | Connectors | connector list/sync | Evidence collection | –/–/– |
| Onboarding | `/mvp/onboarding` | Ops | App onboarding | simulate/register | App onboarding | –/C/– |

## Group 4 — Governance

| Screen | Route | Persona | Business value | KPIs | Workflow role | A/C/E |
|---|---|---|---|---|---|---|
| Audit Prep | `/mvp/audit-prep` | Auditor/Compliance | Audit readiness | readiness heatmap, upcoming | Audit preparation | A/C/E |
| Evidence Health | `/mvp/evidence-health` | Owner/Governance | Quality/freshness | health score, missing, expiring | Evidence lifecycle | A/C/– |
| Evidence Reuse | `/mvp/reuse` | Compliance | Collect once reuse many | reuse %, factor | Control validation | –/C/– |
| Lifecycle | `/mvp/lifecycle` | Compliance | Evidence lifecycle | lifecycles, records | Evidence lifecycle | A/C/– |
| Completeness | `/mvp/completeness` | Compliance/Owner | Gap analysis | maturity, readiness | Control validation | A/C/– |
| App Comparison | `/mvp/comparison` | Heads/Compliance | Benchmark apps | readiness/closure trends | Reporting | –/C/E |
| Search | `/mvp/search` | Auditor/Compliance | Evidence discovery | results, reuse links | Search | A/C/– |
| Evidence Approval Analytics | `/mvp/evidence-approval` | Auditor/Governance | Approval throughput | success %, rejection, time | Evidence approval | A/C/– |
| Evidence Review | `/evidence/review` | Auditor/Owner | Approve/reject | review actions + trail | Evidence approval | A/C/– |

## Group 5 — Evidence Governance (repo-backed)

| Screen | Route | Persona | Business value | KPIs | Workflow role | A/C/E |
|---|---|---|---|---|---|---|
| Role Scorecard | `/mvp/platform/scorecard` | All | Personalized posture | apps, evidence, reuse, coverage | — | A/C/E |
| Executive Summary | `/mvp/platform/executive-summary` | Exec | DB-backed exec view | summary KPIs | — | –/–/E |
| Audit Readiness | `/mvp/platform/audit-readiness` | Auditor | Composite readiness | readiness gauge | Audit preparation | A/C/E |
| App Onboarding/Inventory | `/mvp/platform/onboarding`,`/inventory` | Admin/Ops | App system of record | app records | App onboarding | –/C/– |
| Control/Framework Coverage | `/mvp/platform/*-coverage` | Compliance | True coverage from evidence | coverage % | Control validation | A/C/– |
| Evidence Reuse/Lifecycle (platform) | `/mvp/platform/evidence-*` | Compliance/Admin | DB reuse + lifecycle | reuse, lifecycle | Evidence lifecycle | A/C/– |
| Collection Scheduler (platform) | `/mvp/platform/scheduler` | Admin | Connector schedules | schedules | Evidence collection | –/C/– |
| AI Assistant | `/mvp/ai-assistant` | All | Citation-grounded RAG | grounded answers | Knowledge | A/C/E |

## Group 6 — Enterprise GRC

| Screen | Route | Persona | Business value | KPIs | Workflow role | A/C/E |
|---|---|---|---|---|---|---|
| Risk Register | `/mvp/risk-register` | Governance/Risk | Risk governance | severity, aging, open | Risk management | –/C/E |
| Exceptions/TD | `/mvp/exceptions` | Compliance/Owner | TD workflow | raise exception | Exception handling | A/C/– |
| Exception Governance | `/mvp/exception-governance` | Compliance | TD lifecycle/CAB | active/approved/expiring | Exception handling | A/C/– |
| CMDB/Assets | `/mvp/cmdb` | Admin | Asset inventory | assets + compliance | App onboarding | –/C/– |
| Regulatory Mapping | `/mvp/regulatory` | Compliance | Crosswalk | coverage by theme | Control validation | A/C/– |
| Executive Heatmaps | `/mvp/heatmaps` | CIO/MD | Hotspots | fw/app/BU/regional tiles | — | –/C/E |
| Integrations Hub | `/mvp/integrations-hub` | Admin | Integration orchestration | usage/health | Evidence collection | –/–/– |
| Cross-Tool Correlation | `/mvp/correlation` | Admin | Incident→control chains | correlation chains | Risk management | A/C/– |
| Governance Analytics | `/mvp/governance-analytics` | CIO/Compliance | Governance intel | coverage, rejection, SLA | Reporting | –/C/E |

## Group 7 — AI SDLC Governance

| Screen | Route | Persona | Business value | KPIs | Workflow role | A/C/E |
|---|---|---|---|---|---|---|
| AI SDLC Home/Control Tower | `/mvp/ai-sdlc`, `/control-tower` | AI SDLC Owner | Govern AI delivery | readiness heatmap | AI SDLC review | A/C/E |
| Stage worklists (Req→Go-Live) | `/mvp/ai-sdlc/{stage}` | AI SDLC Owner | Stage gates | stage readiness | AI SDLC review | A/C/– |
| Evidence/Findings (AI SDLC) | `/mvp/ai-sdlc/{evidence,findings}` | AI SDLC Owner | Evidence-backed gates | coverage, findings | AI SDLC review | A/C/– |
| AI SDLC Reports | `/mvp/ai-sdlc/reports` | AI SDLC Owner | AI delivery reporting | 6 reports | Reporting | A/C/E |
| AI Governance Posture | `/mvp/ai-governance` | AI Gov Owner | Govern AI risk | AI compliance score (6 dims) | — | A/C/E |
| AI Registry | `/mvp/ai-registry` | AI Gov Owner | Model/prompt inventory | registry entries | — | A/C/– |
| Governance Quality | `/mvp/governance-quality` | Admin | Governance QA | completeness, validation | — | –/C/– |

---

## Screenshots

66 screens are captured under [`docs/01-product/product/screenshots/`](screenshots) and indexed in [`ECS_SCREENSHOTS_INDEX.md`](../product/ECS_SCREENSHOTS_INDEX.md). Forms, path-param, and redirect routes are documented but not separately imaged (see [Screen Catalog audit](../../05-archive/archive/AUDIT_ECS_SCREEN_CATALOG.md)).

## Related references

- KPIs → [ECS_MASTER_KPI_DICTIONARY.md](../product/ECS_MASTER_KPI_DICTIONARY.md)
- Workflows → [ECS_USER_JOURNEYS.md](../product/ECS_USER_JOURNEYS.md)
- Personas → [ECS_PERSONA_GUIDE.md](../product/ECS_PERSONA_GUIDE.md)
- Modules → [ECS_MODULE_REFERENCE.md](../product/ECS_MODULE_REFERENCE.md)
- Use cases → [ECS_MASTER_USE_CASE_CATALOG.md](../product/ECS_MASTER_USE_CASE_CATALOG.md)

### Connector & integration references (developer/technical)

- Enterprise connectors (11) → [../enterprise_connector_api_reference.md](../../03-development/developer-manual/connectors/enterprise_connector_api_reference.md)
- Microsoft Graph (SharePoint/Teams/Outlook) → [../microsoft_graph_connector_api_reference.md](../../03-development/developer-manual/connectors/microsoft_graph_connector_api_reference.md)
- Connector Test Workbench → [../connector_test_workbench_design.md](../../03-development/developer-manual/connectors/connector_test_workbench_design.md)
- Scheduler runtime flow → [../scheduler_runtime_flow.md](../../03-development/developer-manual/phase1/scheduler/scheduler_runtime_flow.md)
- Runtime call graph & sequence diagrams → [../runtime_call_graph.md](../../03-development/developer-manual/phase1/scheduler/runtime_call_graph.md)
