# ECS Low-Level Design (LLD)

> Sourced from `/Users/nikhil/Documents/ECS`. Each module section lists components, the
> controller (route) layer, services/engines, data models, APIs, UI flows, validation, and
> dependencies — as actually implemented. **[ASSUMPTION]**/**[RECOMMENDATION]** tag inferences.

---

## 0. Cross-cutting building blocks (`modules/shared`)

| Concern | Component | File |
|---|---|---|
| Runtime/business state | `ecs_state` | `modules/shared/services/ecs_state.py` |
| Evidence workflow engine | `evidence_workflow_engine` | `modules/shared/services/evidence_workflow_engine.py` |
| Universal drilldown (service) | `drill_metric()` | `modules/shared/services/drilldown_engine.py` |
| Universal drilldown (engine) | `drill_universal_kpi/row/chart`, `drill_enterprise_workflow` | `modules/shared/drilldowns/ecs_universal_drill_engine.py` |
| Module KPI drill | `drill_module_kpi` | `modules/shared/drilldowns/module_kpi_drill_engine.py` |
| RBAC helpers | `normalize_role`, permission checks | `modules/shared/services/role_permissions.py` |
| Role data scope | role→apps/frameworks | `modules/shared/services/role_filter_scope.py` |
| Persona metadata | `PERSONA_BY_ROLE`, `PERSONA_TABS` | `modules/shared/services/persona_display.py` |
| Module capabilities | view-model assembly | `modules/shared/services/module_capabilities.py` |
| Frontend drilldown | fetch + render modal | `modules/shared/static/js/drilldown_engine.js` |

**Universal drill response contract** (`drilldown_engine.py` / `ecs_universal_drill_engine.py`):
`{ ok, title, rows[], columns[], sections{approval_history, audit_history, related_controls,
related_evidence, related_findings}, metric_trace{}, detail{}, trace_count, row_count, metric, role }`.
A `_fallback_body()` guarantees non-empty rows with `UNIVERSAL_COLUMNS` when delegation fails.

**Validation:** `_safe_count()` (`routes_mvp.py`) coerces formatted `count` query values to int
(prevents HTTP 422); JS `safeCount()` mirrors it client-side; HTML escaped via `esc()` in
`drilldown_engine.js`.

---

## 1. executive_overview

- **Controllers:** dashboard routes (`/dashboard`, `/dashboard/cio` in `app/main.py`;
  `/dashboard/vertical-head|compliance-head|functional-head` in `routes_mvp.py`); MVP pages
  `/mvp/enterprise`, `/mvp/pan-india`, `/mvp/trends`, `/mvp/roi`, `/mvp/reports*`, `/mvp/demo-overview`;
  demo JSON feeds `/api/demo/*`.
- **Services/engines:** `executive_analytics_engine.py` (BU analytics, regulatory traceability,
  heatmaps), `reporting_module.py` (catalog + export), `reports_analytics_engine.py`,
  `reports_drill_engine.py`, `ecs_reports_engine.py`, `demo_metrics.py` (KPI profiles, framework
  maturity baselines), `demo_kpi_drill_engine.py`, `demo_seed.py`, `enterprise_mock_service.py`
  (pan-India, reuse mappings), `integration_hub_executive_engine.py`.
- **Models:** report catalog entries (`reporting_module._REPORT_DEFS`); ROI dataclasses
  (`app/roi/models.py`); pan-India region dict (`ecs_state.PAN_INDIA_REGIONS`).
- **APIs:** `/api/demo/*` (status, overview, banking-applications, frameworks, servicenow,
  ai-governance, prompt-audit, risk-heatmap, cio-executive, …); `/mvp/reports/view/{type}`,
  `/mvp/reports/download/{id}`.
- **UI flows:** role dashboard → KPI strip (drillable) → universal drill modal; ROI center;
  enterprise/pan-india heatmaps; report catalog → view/download.
- **Validation:** role normalization for KPI selection; export format whitelist (pdf/excel/csv).
- **Dependencies:** `ecs_state`, drilldown engines, `gap_export_engine` (export), persona services.

---

## 2. governance

- **Controllers:** `/mvp/evidence-health`, `/mvp/completeness`, `/mvp/lifecycle`, `/mvp/search`,
  `/mvp/audit-prep`, `/mvp/comparison` (+ `/export-gaps`), `/mvp/evidence-approval`,
  `/mvp/exception-governance`, workflow helpers `/mvp/workflow/*`; evidence review POSTs in
  `app/main.py` (`/evidence/review/*`).
- **Services/engines:** `evidence_approval_engine.py` (approval analytics + quality scores),
  `evidence_health_engine.py` (health records, audit trail), `evidence_review.py`, `workflow_module.py`
  (LIFECYCLE_STATES), `operational_workflows.py`, `governance_completeness_engine.py`,
  `governance_lifecycle_engine.py`, `search_module.py`, `analytics_module.py`
  (`enterprise_dashboard`, `compliance_trends`, `audit_preparation_checklist`),
  `governance_intelligence.py`, `comparison_engine.py`, `trends_analytics_engine.py`,
  `trends_drill_engine.py`, `missing_evidence_engine.py`, `exception_state_engine.py`,
  `gap_export_engine.py`, `governance_relational_model.py`.
- **Models:** approval record, health record, missing-evidence observation, relational
  control/evidence/finding (`governance_relational_model.py`).
- **APIs:** `/api/evidence-workflow/summary`; audit-prep drills `/api/audit-prep/*`.
- **UI flows:** evidence health dashboard → record drill; approval queue; completeness/lifecycle;
  application comparison → export gaps (PDF/Excel).
- **Validation:** workflow state transitions via `evidence_workflow_engine.resolve_state()`
  (can_approve/can_reject/can_submit/can_upload/is_locked).
- **Dependencies:** `ecs_state`, `evidence_workflow_engine`, `gap_export_engine`, drilldown engines.

---

## 3. operations

- **Controllers:** `/mvp/scheduler` (+ run/retry/pause/resume), `/mvp/upload` (+ `/bulk`),
  `/mvp/integrations` (+ `/sync`), `/mvp/onboarding`, `/mvp/predefined-queries` (+ prepare/run/detail),
  `/mvp/ai-ops-assistant`; platform ingestion routes `/mvp/platform/sync/*`, `/api/platform/*`
  (`routes_platform.py`).
- **Services/engines:** `scheduler_module.py`, `scheduler_intelligence.py`, `evidence_repository.py`
  (`refresh_repository_from_frameworks`, repository CRUD), `onboarding_engine.py`,
  `integrations_module.py`, `integration_health_engine.py`, `operations_catalog.py`,
  `operations_filter_engine.py`, `predefined_queries_engine.py` (`validate_startup`,
  `get_predefined_queries_dashboard`), `predefined_query_evidence.py`, `predefined_query_audit.py`,
  `ai_ops_assistant_engine.py`, `ai_ops_summary_engine.py`, `resubmission.py`.
- **Connectors:** `linux_connector.py`, `postgresql_connector.py`, `sonarqube_connector.py`,
  `trivy_connector.py`, `gitleaks_connector.py`, `query_connectors.py`, `connector_common.py`.
- **Models:** scheduler/upload/onboarding datasets (`operations_mock_data.py`); resubmission
  sub-states (`resubmission.py`: owner_review, team_resubmission, reevaluate, ready_resubmit).
- **APIs:** `/api/platform/health`, `/api/platform/sync/{connector}`, `/api/platform/evidence`;
  predefined-query prepare/run.
- **UI flows:** scheduler run → job results; bulk upload; integrations sync → health; onboarding wizard;
  predefined queries → evidence/audit.
- **Validation:** connector health checks; upload registration via `register_upload`.
- **Dependencies:** `ecs_platform` (ingestion/repository) optional; `ecs_state`; connectors.

---

## 4. frameworks

- **Controllers:** `/framework/{framework_name}` (`app/main.py`), `/mvp/framework-loader`,
  `/mvp/framework-admin` (+ export), framework drill APIs `/api/framework/kpi-drill`,
  `/workflow-drill`, `/row-drill`, `/tab-drill` (`app/main.py`); onboarding APIs
  `/api/framework-onboarding/*`, `/mvp/framework-loader/activate`.
- **Services/engines:** `framework_catalog.py` (single source of controls/evidence + aliases),
  `framework_dashboards.py`, `framework_intelligence.py`, `framework_governance_data.py`,
  `framework_governance_context.py`, `framework_workflow_engine.py` (`drill_framework_workflow`),
  `framework_kpi_drill_engine.py` (`drill_framework_kpi`), `ecs_row_drill_engine.py`
  (`drill_framework_row`), `framework_onboarding_engine.py`, `framework_loader_service.py`,
  `control_validation_engine.py`, `application_governance.py`, `framework_trends_engine.py`,
  `itpp_module.py`.
- **Models:** control dict (`_control`), catalog evidence (`_make_evidence`), framework graphs
  (`FRAMEWORK_GRAPHS`), legacy `frameworks` tuples (`ecs_state.build_legacy_frameworks`).
- **APIs:** framework kpi/workflow/row/tab drills; framework loader control-drill/application-scan.
- **UI flows:** framework dashboard → KPI/workflow/row/tab drill modals; ITPP command center; loader →
  activate; admin → export config.
- **Validation:** `resolve_framework_name()` (alias→canonical); control validation engine;
  required-evidence checks per control.
- **Dependencies:** `ecs_state` (dynamic catalog merge), drilldown engines.

---

## 5. enterprise_grc

- **Controllers:** `/mvp/risk-register`, `/mvp/cmdb`, `/mvp/exceptions` (+ raise),
  `/mvp/regulatory`, `/mvp/heatmaps`, `/mvp/correlation`, `/mvp/governance-analytics`,
  `/mvp/integrations-hub`; drill APIs `/api/grc-demo/risk/drill`, `/governance/drill`,
  `/governance/intel` (`routes_grc_demo.py`).
- **Services/engines:** `enterprise_grc.py`, `grc_demo_service.py`, `grc_module_demo.py`
  (`_generate_risk_rows`), `correlation_engine.py`, `ecs_governance_framework.py`,
  `ecs_governance_drilldowns.py`, `ecs_governance_qa_engine.py` (`self_heal_governance`),
  `ecs_demo_remediation.py`.
- **Models:** risk register row; exception registry (`ecs_state.exception_registry`); GRC reports
  (JSON under `modules/enterprise_grc/reports/`).
- **APIs:** risk/governance drills + governance intel KPIs.
- **UI flows:** risk register → risk drill; exceptions → raise exception; heatmaps; governance
  analytics → drill.
- **Validation:** exception raise form; governance QA self-heal at startup.
- **Dependencies:** `ecs_state`, drilldown engines, reports JSON.

---

## 6. ai_sdlc

- **Controllers:** `/mvp/ai-sdlc` (home, control-tower, onboarding), stage routes
  `/mvp/ai-sdlc/{requirements|design|development|testing|golive}`, `/mvp/ai-sdlc/evidence|findings|reports`,
  `/mvp/ai-governance`, `/mvp/ai-registry`, `/mvp/governance-quality`, `/mvp/sdlc-gates`; APIs
  `/api/ai-sdlc/*` (control-tower tabs/drills, onboarding, controlled-document, workflow review/action,
  posture/registry/sdlc data + drills, governance-quality scan) (`routes_ai_sdlc_governance.py`).
- **Services/engines:** `ai_sdlc_workflow_engine.py` (stage worklists, evidence queue, findings,
  reports hub; STAGE keys requirement/design/development/testing/go-live; STAGE_ARTIFACTS; STATUSES),
  `ai_sdlc_governance_mock.py` (SDLC_STAGES, AI_APPLICATIONS, drill builders),
  `ai_sdlc_control_tower_engine.py`, `ecs_sdlc_stage_dashboard.py`, `ai_sdlc_controlled_documents.py`,
  `ai_sdlc_document_artifacts.py`, `ai_sdlc_evidence_governance.py`, `ai_sdlc_governance_service.py`,
  `ai_sdlc_knowledge_repository.py`, `ai_sdlc_onboarding_engine.py`, `ai_sdlc_reports_engine.py`,
  `ecs_ai_governance_drilldowns.py`, `ai_sdlc_workflow_store.py`.
- **Models:** onboarded application dict, AI application registry (`AI_APPLICATIONS`), stage activity,
  evidence queue row, finding.
- **APIs:** control tower tab/drill, onboarding run/drill, controlled-document, workflow review/action,
  posture/registry/sdlc data+drills, governance-quality scan.
- **UI flows:** AI-SDLC home → stage gates (Req→Go-Live) → activity worklist → upload/review/approve;
  evidence collection workspace; findings & remediation; control tower; reports hub.
- **Validation:** stage activity status machine (Pending, In Review, Approved, Rejected, Needs Rework,
  Overdue, Awaiting Upload); workflow review/action endpoints.
- **Dependencies:** `ai_sdlc_workflow_store`, `ecs_state`, drilldown engines.

---

## 7. app/ subsystems (typed models & platform)

| Subsystem | Path | Purpose |
|---|---|---|
| auth | `app/auth/` | AuthN/AuthZ: providers, jwt_validator, middleware, guards, roles |
| evidence_intel | `app/evidence_intel/models.py` | EvidenceVersion, LineageGraph, SufficiencyAssessment, EvidenceStatus |
| evidence_analytics | `app/evidence_analytics/models.py` | EvidenceTimeline, EvidenceQualityReport, DSLQuery/Result, PortfolioView |
| roi | `app/roi/models.py` | RoiInputs/RoiResult, Projection, Waterfall, RolloutSimulator |
| connectivity | `app/connectivity/models.py` | ConnectivityProfile, readiness/risk assessments |
| observations | `app/observations/store.py` | Durable observation hydration (optional) |
| audit / sufficiency | `app/audit/`, `app/sufficiency/` | Audit + sufficiency logic |
| ecs_platform | `ecs_platform/` | config loader, ingestion, repository, vectorstore, rag, governance |

---

## 8. Key UI-to-API flows (representative)

| UI action | JS function (`drilldown_engine.js`) | Endpoint | Engine |
|---|---|---|---|
| KPI card (workflow) | `ecsOpenEnterpriseWorkflowDrill` | `/api/ecs/workflow-drill` | `drill_workflow` → `evidence_workflow_engine.drill_workflow_metric` |
| KPI card (universal) | `ecsOpenUniversalKpiDrill` | `/api/ecs/universal-drill?scope=kpi` | `drill_universal_kpi` |
| Chart element | `ecsOpenUniversalChartDrill` | `/api/ecs/universal-drill?scope=chart` | `drill_universal_chart` |
| Table row | `ecsOpenUniversalRowDrill` | `/api/ecs/universal-drill?scope=row` | `drill_universal_row` |
| Heatmap cell | `ecsOpenHeatmapDrill` | `/api/ecs/universal-drill?scope=heatmap` | `drill_heatmap_cell` |
| Module KPI | `ecsOpenModuleKpiDrill` | `/api/module-kpi/drill` | `drill_module_kpi` |
| Framework KPI | (framework drill modal) | `/api/framework/kpi-drill` | `drill_framework_kpi` |

All drill responses share the universal contract and render via `renderResponse()` with empty/error
failsafes (`emptyStateHtml`/`errorStateHtml`) and a timeout guard.
