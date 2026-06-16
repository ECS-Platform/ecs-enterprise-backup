# ECS Module Reference

Part of the **ECS Product Operations Manual**. This chapter documents every functional module ECS ships, grounded in the actual code under `modules/` and the canonical module registry `MODULE_PURPOSES` (`modules/shared/services/module_capabilities.py:34-63`).

ECS is organized as a **modular monolith**: one FastAPI app composing seven code packages under `modules/` plus the infrastructure layer `ecs_platform/`. The left navigation groups screens into **seven business areas**. This document maps each area and code module to its purpose, engines, screens, workflows, KPIs, reports, and relationships.

> Navigation source: `modules/shared/templates/partials/ecs_nav_groups.html` + `ecs_nav_ai_sdlc.html`. Module registry: `module_capabilities.py`. Badge counts: `nav_counter_engine.py`.

---

## Navigation map (left sidebar → modules)

| Nav group | Screens (modules) |
|---|---|
| **Executive Overview** | ROI & Value Realization, Role Dashboard, Demo Overview, Enterprise, Pan India, Reports, Trends |
| **Frameworks** | 15 framework pages, Framework Loader, Framework Administration |
| **Operations** | Scheduler, Predefined Queries, Integration Health, Evidence Explorer, AI Ops Assistant, Bulk Upload, Integrations, Onboarding |
| **Governance** | Audit Prep, Evidence Health, Evidence Reuse, Lifecycle, Completeness, App Comparison, Search, Evidence Approval Analytics |
| **Evidence Governance** (platform/DB-backed) | Role Scorecard, Executive Summary, Audit Readiness, Application Onboarding, Application Inventory, Control Coverage, Framework Coverage, Evidence Reuse, Evidence Lifecycle, Collection Scheduler, AI Assistant |
| **Enterprise GRC** | Risk Register, Exceptions / TD, Exception Governance, CMDB / Assets, Regulatory Mapping, Executive Heatmaps, Integrations Hub, Cross-Tool Correlation, Governance Analytics |
| **AI SDLC Governance** | Home, Control Tower, Application Onboarding, Requirements, Design, Development, Testing, Go-Live, Evidence Collection, Findings & Remediation, Reports (+ AI Governance Posture, Model & Prompt Registry, Governance Quality) |

---

## Canonical module registry (`MODULE_PURPOSES`, 28 entries)

These are the product's advertised modules with their official one-line descriptions, taken verbatim from `modules/shared/services/module_capabilities.py:34-63`. Each drives a nav badge counter (`module_counter_rows()`).

| Key | Label | Route | Description |
|---|---|---|---|
| `scheduler` | Scheduler | `/mvp/scheduler` | Evidence Collection Engine — collects and refreshes evidence from integrated enterprise platforms (ServiceNow, GitHub, Jenkins, SonarQube, and more). |
| `upload` | Bulk Upload | `/mvp/upload` | Mass onboarding and batch import of evidence artefacts with validation, deduplication, and framework auto-mapping. |
| `evidence_health` | Evidence Health | `/mvp/evidence-health` | Risk and quality scoring — stale, expired, incomplete, and low-confidence evidence governance. |
| `search` | Search | `/mvp/search` | Enterprise evidence discovery with semantic filters, reuse mapping, and cross-framework search. |
| `completeness` | Completeness | `/mvp/completeness` | Coverage gap analysis — controls without evidence, partial compliance, and audit readiness. |
| `reuse` | Evidence Reuse | `/mvp/reuse` | Cross-framework evidence reuse engine — map once, satisfy multiple controls, reduce duplicate uploads. |
| `lifecycle` | Lifecycle | `/mvp/lifecycle` | Evidence lifecycle governance — draft through active, expiring, archived, and retired states. |
| `comparison` | App Comparison | `/mvp/comparison` | Application compliance posture comparison — maturity variance, control gaps, and risk heatmaps. |
| `integrations` | Integrations | `/mvp/integrations` | External system connectors — SIEM, ticketing, GRC, and ingestion pipeline health. |
| `enterprise` | Enterprise | `/mvp/enterprise` | Organization-wide governance KPIs, framework maturity, business-unit risk, and compliance posture. |
| `pan_india` | Pan India | `/mvp/pan-india` | Regional and branch-level compliance visibility with zone risk and SLA breach tracking. |
| `reports` | Reports | `/mvp/reports` | Audit-ready export center — regulator packs, scheduled reports, and export history. |
| `audit_prep` | Audit Prep | `/mvp/audit-prep` | Audit readiness cockpit — upcoming audits, missing controls, and mock-audit preparation. |
| `trends` | Trends | `/mvp/trends` | Historical compliance analytics — control implementation coverage, observation closure, auditor rejection, remediation SLA, and evidence aging. |
| `onboarding` | Onboarding | `/mvp/onboarding` | Application onboarding workflow — framework assignment, ownership, and registration stages. |
| `framework_admin` | Framework Administration | `/mvp/framework-admin` | Framework administration — ingest new compliance frameworks, control normalization, reuse intelligence, and activation. |
| `risk_register` | Risk Register | `/mvp/risk-register` | Enterprise risk governance — inherent/residual risk, treatment, regulatory impact, and risk aging. |
| `exceptions_td` | Exceptions / TD | `/mvp/exceptions` | Technical debt and exception workflow — compensating controls, TD expiry, renewal, and approval. |
| `cmdb` | CMDB / Assets | `/mvp/cmdb` | CMDB and asset inventory — applications, servers, cloud assets, ownership, and compliance mapping. |
| `regulatory_mapping` | Regulatory Mapping | `/mvp/regulatory` | Cross-framework regulatory normalization — shared controls, evidence reuse, and coverage matrix. |
| `executive_heatmaps` | Executive Heatmaps | `/mvp/heatmaps` | CIO/MD executive visibility — framework, application, BU, regional, and SLA heatmaps. |
| `integrations_hub` | Integrations Hub | `/mvp/integrations-hub` | Enterprise integration orchestration — ServiceNow, Jira, Prisma, Tripwire, SonarQube, and more. |
| `correlation` | Cross-Tool Correlation | `/mvp/correlation` | Cross-tool governance correlation — incident-to-remediation-to-control failure chains. |
| `governance_analytics` | Governance Analytics | `/mvp/governance-analytics` | Enterprise governance intelligence — audit readiness, rejection patterns, remediation SLA, evidence freshness, and application risk posture. |
| `evidence_approval` | Evidence Approval Analytics | `/mvp/evidence-approval` | Evidence approval analytics — approved, rejected, pending validation, stale evidence, quality scorecards, and reviewer workload. |
| `exception_governance` | Exception Governance | `/mvp/exception-governance` | Exception governance dashboard — TD lifecycle, approval persistence, expiring exceptions, and CAB pending queue. |
| `ai_ops_assistant` | AI Ops Assistant | `/mvp/ai-ops-assistant` | ECS AI Ops Assistant — banking governance copilot for incidents, audit, compliance, frameworks, evidence, and operations drilldowns. |
| `predefined_queries` | Predefined Queries | `/mvp/predefined-queries` | Predefined Queries — centralized catalog of control queries from the ECS Query Driven Control Library across all frameworks. |

---

# Code-package chapters

The 28 modules above are implemented across seven Python packages. Each chapter below covers a package: purpose, key engines, screens, workflows, KPIs, reports, and relationships.

---

## 1. `executive_overview`

**Purpose.** C-level and role dashboards, enterprise KPIs, regional (Pan-India) posture, the reporting center, trend analytics, the ROI value center, and the deterministic demo seed used for leadership presentations.

**Primary users.** CIO, Vertical Head, Functional Head, Compliance Head, Auditor (reports), demo teams.

**Key engines** (`modules/executive_overview/engines/`):

| File | Role |
|---|---|
| `demo_metrics.py` | Banking demo metrics blended with live workflow state; per-role KPI strips; `enterprise_kpis()` |
| `demo_seed.py` | Idempotent seed of enterprise workflow state at startup (`seed_demo_workflow_state()`) |
| `executive_analytics_engine.py` | Business-unit analytics, regional heatmaps, audit-prep matrix, correlation graph |
| `ecs_reports_engine.py` | Interactive HTML report builders (adherence, readiness, compliance, coverage, findings) |
| `reporting_module.py` | Filter-aware audit-pack reporting center (30 downloadable report packs) |
| `reports_analytics_engine.py` | Reports catalog, export, history, overview metrics |
| `reports_drill_engine.py` | Reports module drilldowns |
| `enterprise_mock_service.py` | Interconnected mock data (regions, reuse, uploads) |
| `integration_hub_executive_engine.py` | Executive Integration Command Center data |
| `demo_kpi_drill_engine.py` | Unified `/mvp/demo-overview` KPI drill API |

**Screens.** `/dashboard`, `/dashboard/cio`, `/dashboard/vertical-head`, `/dashboard/compliance-head`, `/dashboard/functional-head`, `/mvp/enterprise`, `/mvp/pan-india`, `/mvp/reports`, `/mvp/reports/view/{report_type}`, `/mvp/trends`, `/mvp/demo-overview`, `/mvp/roi`.

**Key workflows.** Enterprise KPI aggregation; report generation/download; trend analytics with daily/weekly/monthly/quarterly granularity; Pan-India regional SLA tracking; report-generation workflow.

**KPIs displayed.** Enterprise Compliance %, Audit Readiness, National/Pan-India Score, Business-Unit Compliance/Risk, Implementation Coverage trend, Observations Net, Auditor Rejection Rate, Remediation SLA Compliance, ROI value/hours/FTE (see `ECS_KPI_DICTIONARY.md` sections A, B, D, E, F).

**Reports.** 30 executive audit packs + 5 interactive HTML report types (`ECS_FEATURE_REFERENCE.md` / persona guide for the full catalog).

**Relationships.** Depends on `frameworks` (catalog), `governance` (analytics/mock/intelligence), `operations` (integration hub data), `shared` (`ecs_state`, `ecs_mock_engine`, `demo_data_standards`).

---

## 2. `frameworks`

**Purpose.** The compliance-framework catalog and everything framework-scoped: per-framework control/evidence data, framework landing pages, the Framework Loader, Framework Administration (onboarding), control validation, and framework KPI drills.

**Primary users.** Compliance Head / Compliance Officer, Framework Owner, Auditor, Application Owner (within a framework).

**Key engines** (`modules/frameworks/engines/`):

| File | Role |
|---|---|
| `framework_catalog.py` | Single source of truth — **15 frameworks**, their controls and evidence records; `catalog_stats()` |
| `framework_dashboards.py` | Assembles the `/framework/{name}` landing dashboard |
| `framework_governance_data.py` | Framework-specific datasets (apps, KPIs, trends, drills) |
| `framework_workflow_engine.py` | Framework-scoped workflow metrics & drill datasets |
| `framework_kpi_drill_engine.py` | Per-framework KPI tile configs + drilldown datasets |
| `framework_trends_engine.py` | Framework-scoped time series |
| `framework_intelligence.py` | Control intelligence & evidence reuse |
| `framework_onboarding_engine.py` | Ingest / normalize / reuse-intelligence / activate new frameworks; framework RBAC predicates |
| `framework_loader_service.py` | Framework Loader executive presentation layer |
| `control_validation_engine.py` | Config / file / policy / reuse / SLA validation checks |
| `application_governance.py` | Application-centric views per framework |
| `itpp_module.py` | ITPP operational governance (DR, backup, change, incident) |

**The 15 frameworks** (catalog keys, `framework_catalog.py`): PCI DSS, DPSC, OS Baselining, DB Baselining, Nginx Baselining, AppSec, VAPT, CSITE, ITPP, ITDRM, SOC2, ISO27001, RBI Cyber Security, ISG, ASST. Catalog totals (from `catalog_stats()`): **305 controls / 702 evidence records**.

**Screens.** `/framework/{framework_name}` (with tabs: applications / controls / evidence, plus ITPP drill views), `/mvp/framework-loader`, `/mvp/framework-admin` (+ wizard), `/mvp/framework-admin/export/{framework_id}`.

**Key workflows.** Framework compliance review; control validation; framework onboarding wizard (import → normalize → reuse decision → lifecycle → activation); ITPP command center; framework KPI drilldown.

**KPIs displayed.** Per-framework tile sets (6 KPIs each), e.g. PCI Maturity, CDE Controls, Encryption Coverage, QSA Readiness; ISO27001 ISMS Maturity; SOC2 Trust Criteria Coverage; RBI Maturity Score; VAPT Open Vulnerabilities; etc. (full ranges in `ECS_KPI_DICTIONARY.md` section G).

**Relationships.** Depends on `governance` (relational model, workflow queues), `operations` (evidence repository for reuse map), `shared` (audit trail, demo data standards). Consumed by `executive_overview` and `enterprise_grc`.

---

## 3. `operations`

**Purpose.** Evidence-collection operations: the scheduler, bulk upload, integrations, application onboarding, the predefined-query catalog, the AI Ops copilot, integration health, and the evidence explorer. Also hosts the real `ecs_platform` source connectors' operational adapters.

**Primary users.** Operations Owner, Platform Admin, Application Owner (upload), Auditor (explorer).

**Key engines** (`modules/operations/engines/`):

| File | Role |
|---|---|
| `scheduler_module.py` / `scheduler_intelligence.py` | Scheduled evidence-pull simulation; cron timeline, scan results, failures, upcoming plan |
| `evidence_repository.py` | Bulk upload, metadata/hashes, lifecycle, reuse graph; startup refresh from frameworks |
| `integrations_module.py` / `integration_health_engine.py` | Integrations hub data; framework-aware connector health rows & analytics |
| `onboarding_engine.py` | AI-driven application onboarding simulator + text export |
| `operations_catalog.py` / `operations_mock_data.py` / `operations_filter_engine.py` | Apps/frameworks/owners catalog; mock datasets; filter+paginate |
| `operations_intelligence.py` | Outage summarization / ops intelligence |
| `predefined_queries_engine.py` | Catalog from the ECS Query-Driven Control Library; `validate_startup()` |
| `predefined_query_audit.py` / `predefined_query_evidence.py` | Query execution audit + evidence integration |
| `query_connectors.py`, `postgresql_connector.py`, `linux_connector.py`, `sonarqube_connector.py`, `gitleaks_connector.py`, `trivy_connector.py`, `connector_common.py` | Operations-layer connector interfaces |
| `ai_ops_assistant_engine.py` / `ai_ops_summary_engine.py` / `ai_ops_response_modes.py` | AI Ops copilot workspace, summary drills, eight perspective response modes |
| `resubmission.py` | Rejection / resubmission lifecycle helpers |

**Screens.** `/mvp/scheduler`, `/mvp/upload` (`/mvp/bulk-upload` alias), `/mvp/integrations`, `/mvp/onboarding`, `/mvp/predefined-queries` (+ `/detail`), `/mvp/ai-ops-assistant` (+ `/summary/{mode}`), `/mvp/integration-health`, `/mvp/evidence-explorer`.

**Key workflows.** Scheduled evidence collection; batch upload with validation/auto-mapping; connector sync (`/api/platform/sync/{connector}`); application onboarding pipeline; predefined-query catalog browse/run; AI incident investigation.

**KPIs displayed.** Scheduler success rate (99.2%), collection jobs/day, connector health %, evidence collected/day; predefined-queries catalog totals (Total Controls, Predefined Queries, Manual Controls, Frameworks Covered, Unsupported Tech). See `ECS_KPI_DICTIONARY.md` sections E, J.

**Relationships.** Uses `executive_overview` demo metrics (scheduler); `shared` (audit trail, chatbot, pagination). Feeds `governance` (search, evidence review). Operationally backed by `ecs_platform/connectors`.

---

## 4. `governance`

**Purpose.** The core GRC governance workflows: audit prep, evidence health, reuse, lifecycle, completeness, application comparison, search, evidence-approval analytics, exception state, and the operational workflow actions (gap closure, owner assignment, mock audit). This is where evidence is reviewed and observations are managed.

**Primary users.** Auditor, Application Owner, Compliance Head, Governance teams.

**Key engines** (`modules/governance/engines/`):

| File | Role |
|---|---|
| `workflow_module.py` | App Owner / Auditor / Leadership work queues |
| `operational_workflows.py` | Gap closure, owner assignment, upload-missing, mock audit, mock-audit report |
| `evidence_review.py` | Single-evidence review screen + audit trail |
| `evidence_health_engine.py` | Evidence health scoring with control/observation linkage |
| `evidence_approval_engine.py` | Approval analytics (success/rejection/validation time) |
| `governance_completeness_engine.py` | Framework coverage & readiness; dynamic completeness % |
| `missing_evidence_engine.py` | Missing-evidence / upload queue; completeness formula |
| `comparison_engine.py` | Cross-application comparison + trend bundle |
| `governance_lifecycle_engine.py` | Interconnected lifecycle mock data + charts |
| `governance_relational_model.py` | Relational governance graph (framework→app→control→evidence) |
| `governance_intelligence.py` | Context-aware analytics & filtered trends |
| `search_module.py` | Enterprise evidence discovery |
| `exception_state_engine.py` | Persistent exception / TD workflow state + KPIs |
| `audit_prep_data.py` | Bank-wide audit-readiness command center; package generation |
| `audit_schedule_engine.py` | Audit scheduling (rolling 12-month window) |
| `gap_export_engine.py` | Gap-analysis PDF / Excel / CSV export |
| `trends_analytics_engine.py` / `trends_drill_engine.py` | Executive trends series + drilldowns |
| `analytics_module.py` | Completeness, comparison, enterprise metrics |
| `governance_mock_data.py` / `operational_mock_data.py` / `governance_data_enrichment.py` | Banking mock data + runtime graph enrichment |

**Screens.** `/mvp/audit-prep`, `/mvp/evidence-health`, `/mvp/reuse`, `/mvp/lifecycle`, `/mvp/completeness`, `/mvp/comparison`, `/mvp/search`, `/mvp/evidence-approval`; workflow pages `/mvp/workflow/close-gap`, `/assign-owner`, `/upload-missing`, `/mock-audit`; and the core `/evidence/review` workspace (in `app/main.py`).

**Key workflows.** Owner/auditor evidence-review queues; submit → review → approve/reject/clarify/request-reupload; observation create/close; audit-prep gap closure; completeness gap assignment; reuse approval; lifecycle transitions; mock audit; gap export.

**KPIs displayed.** Evidence Health Score, Controls Missing Evidence, Open Observations, High-Risk Failures, Expiring/Rejected/Stale Evidence; Approval Success %, Rejection Rate %, Avg Validation Time; Completeness/Maturity/Audit-Readiness; Implementation Coverage; Observations Net/Closure Rate; Remediation SLA. See `ECS_KPI_DICTIONARY.md` sections A–D.

**Reports.** Gap analysis export (PDF/Excel/CSV), audit package, mock-audit report, evidence-approval summary CSV.

**Relationships.** Depends on `frameworks` (catalog/controls), `operations` (evidence repository), `executive_overview` (metrics/analytics), `shared` (audit trail, role-filter scope, filter engine). Consumed by `executive_overview`, `enterprise_grc`, `frameworks`.

---

## 5. `enterprise_grc`

**Purpose.** Enterprise GRC platform views beyond the evidence lifecycle: risk register, exceptions/technical-debt, CMDB/assets, regulatory mapping, executive heatmaps, cross-tool correlation, governance analytics, and the governance QA self-heal engine.

**Primary users.** Governance lead/teams, Risk teams, Compliance Head, CIO (heatmaps), Admin (CMDB/correlation).

**Key engines** (`modules/enterprise_grc/engines/`):

| File | Role |
|---|---|
| `enterprise_grc.py` | Risk Register, Exceptions, CMDB, Regulatory Mapping, Heatmaps |
| `grc_module_demo.py` / `grc_demo_service.py` | Enterprise-scale demo data + presentation layer for risk/governance analytics |
| `correlation_engine.py` | Cross-tool governance correlation chains (incident→remediation→control failure) |
| `ecs_governance_framework.py` | Reusable governance framework — nav enrichment, reuse, control-360, framework coverage recompute |
| `ecs_governance_drilldowns.py` | Deep drill payloads for governance workspaces |
| `ecs_governance_qa_engine.py` | Governance QA scan, self-heal (`self_heal_governance()`), validation reports |
| `ecs_demo_remediation.py` | Demo remediation, lineage, reuse-wizard data |

**Screens.** `/mvp/risk-register`, `/mvp/exceptions`, `/mvp/exception-governance`, `/mvp/cmdb`, `/mvp/regulatory`, `/mvp/heatmaps`, `/mvp/correlation`, `/mvp/governance-analytics`, `/mvp/governance-quality`.

**Key workflows.** Risk acceptance/mitigation/treatment; exception/TD raise → renewal → CAB approval; asset compliance mapping; regulatory crosswalk; incident-to-control correlation; governance QA self-heal.

**KPIs displayed.** Risk severity distribution, risk aging, open/high-critical risks; Active/Approved/Rejected/Expiring exceptions, High-Risk Open TDs, Pending Review; regulatory coverage by theme; framework/app/BU/regional heatmap readiness; governance data-completeness/readiness/validation %. See `ECS_KPI_DICTIONARY.md` sections C, K and chart guide.

**Relationships.** Depends on `frameworks`, `governance` (workflow queues), `executive_overview` (metrics/analytics), `ai_sdlc` (governance mock, stage dashboard for QA), `shared`.

---

## 6. `ai_sdlc`

**Purpose.** AI & SDLC Governance: SDLC stage worklists (Requirements → Go-Live), the Control Tower, application onboarding, evidence collection, findings & remediation, executable reports, AI governance posture, and the AI model/prompt registry.

**Primary users.** AI SDLC Owner, AI Governance Owner, Auditor (reviews), Application Owner (worklists).

**Key engines** (`modules/ai_sdlc/engines/`):

| File | Role |
|---|---|
| `ai_sdlc_governance_service.py` | Presentation service orchestrating all AI SDLC views |
| `ai_sdlc_governance_mock.py` | Deterministic mock data; stage/release readiness scoring |
| `ai_sdlc_workflow_engine.py` / `ai_sdlc_workflow_store.py` | Workflow execution (framework→control→evidence); in-memory state, transitions, audit trail |
| `ai_sdlc_control_tower_engine.py` | Control Tower orchestration & monitoring |
| `ai_sdlc_onboarding_engine.py` | Application onboarding execution workspace |
| `ai_sdlc_reports_engine.py` | Executable report data builders (6 reports) |
| `ai_sdlc_controlled_documents.py` / `ai_sdlc_document_artifacts.py` | Controlled SDLC document generator + rich artifacts |
| `ai_sdlc_evidence_governance.py` | Evidence viewer governance summary |
| `ai_sdlc_knowledge_repository.py` | Governance knowledge base |
| `ecs_sdlc_stage_dashboard.py` | SDLC stage workspace dashboards + slug routes |
| `ecs_ai_governance_drilldowns.py` | Explainable AI-governance drill payloads; AI Compliance Score |

**Screens.** `/mvp/ai-sdlc` (home), `/control-tower`, `/onboarding`, `/requirements`, `/design`, `/development`, `/testing`, `/golive`, `/evidence`, `/findings`, `/reports` (+ `/reports/{id}`, `/evidence/view/{id}`); `/mvp/ai-governance`, `/mvp/ai-registry`, `/mvp/governance-quality`.

**Key workflows.** SDLC gate stage worklists; control-tower readiness drills; controlled-document review/approve (`/api/ai-sdlc/workflow/action`); evidence collection; findings remediation; AI model/prompt registry governance.

**KPIs displayed.** SDLC Stage/Release Readiness; Framework/Control/Evidence Coverage %; AI Compliance Score (6 weighted dimensions: Data Privacy 18, Model Risk 20, Prompt Safety 18, Bias & Fairness 16, Audit Trail 14, Human-in-Loop 14); prompt audits, hallucination rate, AI risk score; report compliance %. See `ECS_KPI_DICTIONARY.md` sections A, H.

**Reports.** 6 AI SDLC reports — Application Compliance, Framework Compliance, Readiness, Control Implementation, Evidence Collection Status, Findings & Remediation.

**Relationships.** Depends on `enterprise_grc` (governance framework, drilldowns, QA), `shared` (nav, role permissions, demo data standards).

---

## 7. `shared`

**Purpose.** Cross-cutting infrastructure used by every page: navigation, badge counters, the module-capability/workspace registry, role permissions and scope, the evidence workflow engine, the chatbot/AI assistant, universal drilldowns, audit trail, the page templates/partials, and the `/mvp/*` route registrar.

**Primary users.** All (it is the integration layer; not a user-facing module by itself).

**Key services** (`modules/shared/services/`):

| File | Role |
|---|---|
| `ecs_state.py` | Shared application/workflow state (control statuses, totals) |
| `evidence_workflow_engine.py` | Evidence workflow context, transitions, observations, toasts |
| `role_permissions.py` | `can_*` capability predicates, `normalize_role`, action filtering |
| `role_filter_scope.py` | Role-scoped application/data filtering (demo scope) |
| `nav_counter_engine.py` | Left-nav badge counters from live state |
| `module_capabilities.py` | `MODULE_PURPOSES` registry + per-module capability views |
| `module_workspace.py` | Tab-driven workspace configuration per module |
| `enterprise_context.py` | Shared template context injected into every MVP page |
| `ecs_nav_framework.py` | Breadcrumbs, module labels, drill footer links |
| `drilldown_engine.py` + `drilldowns/ecs_universal_drill_engine.py`, `module_kpi_drill_engine.py` | Universal KPI/row/chart drilldown orchestration |
| `chatbot_engine.py`, `chatbot_context_engine.py`, `chatbot_enhanced.py`, `chatbot_nav.py` | Governance chatbot / AI assistant + deep-link builder |
| `audit_trail.py` | Audit event logging & history |
| `metric_trace_service.py` | KPI explainability (metric trace modal) |
| `ecs_mock_engine.py` | Shared mock data engine (demo overview, CIO strip) |
| `standard_filter_engine.py`, `global_filter_engine.py`, `pagination.py`, `table_schemas.py`, `demo_data_standards.py` | Filtering, pagination, schemas, demo data standards |
| `ecs_logging.py` | Structured logging + startup banner |

**Routes.** `modules/shared/routes/routes_mvp.py` (most `/mvp/*`), `evidence_routes.py`.

**Relationships.** Imports from all business modules to build context/counters; it is the platform's integration layer.

---

## Infrastructure layer: `ecs_platform/`

Not a nav module, but the real backend used by the Evidence Governance / platform screens and the connector sync:

| Component | Role |
|---|---|
| `ecs_platform/connectors/` | 12 source-system connectors (Gitea, GitHub, SonarQube, Jenkins, Jira, Confluence, Figma, ServiceNow, Teams, SharePoint, Prisma Cloud, Azure DevOps) + base/factory/http_client |
| `ecs_platform/repository/` | PostgreSQL evidence repository (system of record) |
| `ecs_platform/vectorstore/` | pgvector embedding store |
| `ecs_platform/rag.py`, `llm_engine/` | Citation-grounded LLM-RAG assistant (provider-pluggable) |
| `ecs_platform/ingestion.py` | `sync_connector`, `health_overview`, `list_evidence`, `init_repository` |
| `ecs_platform/governance.py` / `demo_governance.py` | DB-backed governance scorecards (with demo fallback) — audit readiness, coverage, reuse |
| `ecs_platform/config/loader.py` | YAML config loader with `${ENV}` resolution |

The Evidence Governance nav group (`/mvp/platform/*`) and Integration Health / Evidence Explorer screens are powered by this layer; they degrade gracefully to demo data when no PostgreSQL is available.

---

## Module relationship diagram

```
                shared  (nav, counters, state, workflow, drilldowns, RBAC)
                  │  imports from all modules for context/counters
   frameworks ────┤  (15-framework catalog = source of truth)
       │          │
   governance ◄── operations (evidence repository, connectors)
       │
   executive_overview ◄── governance analytics / demo metrics
       │
   enterprise_grc ◄── frameworks + governance + ai_sdlc
       │
   ai_sdlc ◄── enterprise_grc (governance framework, drills, QA)

   ecs_platform (connectors / repository / pgvector / RAG) ── powers /mvp/platform/* + sync
```

See `ECS_SCREEN_CATALOG.md` for every screen, `ECS_KPI_DICTIONARY.md` for every metric, and `ECS_PERSONA_GUIDE.md` for who uses what.
