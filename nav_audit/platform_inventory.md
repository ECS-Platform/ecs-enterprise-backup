# ECS Platform Inventory

Complete inventory of personas, navigation, pages, and interactive surfaces used
for the hardening and demo-readiness validation.

## Personas / Roles validated

| # | Persona | Role key |
|---|---|---|
| 1 | CIO | `cio` |
| 2 | CISO | `ciso` |
| 3 | CTO | `cto` |
| 4 | Application Owner | `owner` |
| 5 | Auditor | `auditor` |
| 6 | Compliance Officer | `compliance` |
| 7 | Security Officer | `security` |
| 8 | Platform Administrator | `platform_ops` |
| 9 | Operations Manager / IT Ops | `it_ops` |
| 10 | Governance Lead | `governance` |
| 11 | Risk Officer | `risk` |
| 12 | Vertical / Executive Head | `vertical_head` |

> In `DEMO_MODE` every role is admitted to every page (auth/RBAC/page-guards
> bypassed), so each persona can navigate the full platform token-free.

## Left navigation menus → pages (66 routes)

### Executive Overview
- `★ ROI & Value Realization` — `/mvp/roi`
- `Main Dashboard` — `/dashboard`
- `Evidence Analytics` — `/dashboard/cio`
- `Vertical Head Dashboard` — `/dashboard/vertical-head`
- `Compliance Dashboard` — `/dashboard/compliance-head`
- `Functional Head Dashboard` — `/dashboard/functional-head`
- `Demo Overview` — `/mvp/demo-overview`
- `Enterprise` — `/mvp/enterprise`
- `Pan India` — `/mvp/pan-india`
- `Reports` — `/mvp/reports`
- `Trends` — `/mvp/trends`

### Frameworks
- `PCI-DSS / ISO27001 / SOC2 / RBI-CSF / AI-SDLC` — `/framework/{code}`
- `Framework Loader` — `/mvp/framework-loader`
- `Framework Administration` — `/mvp/framework-admin`

### Operations
- `Scheduler` — `/mvp/scheduler`
- `Predefined Queries` — `/mvp/predefined-queries`
- `Integration Health` — `/mvp/integration-health`
- `Evidence Explorer` — `/mvp/evidence-explorer`
- `AI Ops Assistant` — `/mvp/ai-ops-assistant`
- `Bulk Upload` — `/mvp/upload`
- `Integrations` — `/mvp/integrations`
- `Onboarding` — `/mvp/onboarding`

### Governance
- `Audit Prep` — `/mvp/audit-prep`
- `Evidence Health` — `/mvp/evidence-health`
- `Evidence Reuse` — `/mvp/reuse`
- `Lifecycle` — `/mvp/lifecycle`
- `Completeness` — `/mvp/completeness`
- `App Comparison` — `/mvp/comparison`
- `Search` — `/mvp/search`
- `Evidence Approval Analytics` — `/mvp/evidence-approval`

### Evidence Governance (platform)
- `Role Scorecard` — `/mvp/platform/scorecard`
- `Executive Summary` — `/mvp/platform/executive-summary`
- `Audit Readiness` — `/mvp/platform/audit-readiness`
- `Application Onboarding` — `/mvp/platform/onboarding`
- `Application Inventory` — `/mvp/platform/inventory`
- `Control Coverage` — `/mvp/platform/control-coverage`
- `Framework Coverage` — `/mvp/platform/framework-coverage`
- `Evidence Reuse` — `/mvp/platform/evidence-reuse`
- `Evidence Lifecycle` — `/mvp/platform/evidence-lifecycle`
- `Collection Scheduler` — `/mvp/platform/scheduler`
- `AI Assistant` — `/mvp/platform/assistant`, `/mvp/ai-assistant`

### Enterprise GRC
- `Risk Register` — `/mvp/risk-register`
- `Exceptions / TD` — `/mvp/exceptions`
- `Exception Governance` — `/mvp/exception-governance`
- `CMDB / Assets` — `/mvp/cmdb`
- `Regulatory Mapping` — `/mvp/regulatory`
- `Executive Heatmaps` — `/mvp/heatmaps`
- `Integrations Hub` — `/mvp/integrations-hub`
- `Cross-Tool Correlation` — `/mvp/correlation`
- `Governance Analytics` — `/mvp/governance-analytics`

### AI SDLC Governance
- `Home / Control Tower / Onboarding / Requirements / Design / Development /
  Testing / Go-Live / Evidence Collection / Findings & Remediation / Reports`
  — `/mvp/ai-sdlc[/...]`

## Interactive surfaces (per page)

- **KPI cards** — universal drill via `/api/ecs/universal-drill` (page + metric).
- **Charts** (bar / pie / donut / heatmap / trend) — segment/bar drilldowns.
- **Tables** — row drilldowns + pagination (`ecs-paginated-table`).
- **Tabs** — Overview / Risk / Evidence / Compliance / Analytics (Demo Overview etc.).
- **Modals / drawers** — universal drill modal, module KPI modal, framework KPI modal,
  demo KPI modal, workflow drill.
- **Drill APIs**: `/api/ecs/universal-drill`, `/api/ecs/workflow-drill`,
  `/api/demo/kpi-drill`, `/api/module-kpi/drill`.

## Demo data providers

| Provider | Purpose |
|---|---|
| `ecs_platform/demo_evidence.py` | 1,200 evidence records · 10 connectors · correlations · connector health · sync/audit |
| `ecs_platform/demo_governance.py` | applications · controls · frameworks · reuse · lifecycle · schedules · readiness · scorecard · tickets · VAPT · observations · AI prompts · regions |
| `modules/executive_overview/engines/demo_metrics.py` + `framework_catalog` | live demo-overview / dashboard datasets (305 controls, etc.) |
| `modules/shared/drilldowns/ecs_universal_drill_engine.py` + `drilldown_engine.py` | deterministic drilldown rows + global never-fail fallback |

**Total: 12 personas × 66 pages, all interactive surfaces backed by deterministic demo data.**
