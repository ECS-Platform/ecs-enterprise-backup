# ECS Modular Refactor Plan

**Status:** Analysis only — no code changes authorized  
**Repository:** `wkin_ecs_consolidated_demo_v13`  
**Date:** 2026-05-29  
**Scope:** Propose a modular architecture so multiple developers can work on separate ECS modules without collision

---

## 1. Executive Summary

ECS is a FastAPI + Jinja2 banking governance demo with **~104 Python modules**, **~149 HTML templates**, **3 route registration files**, and **36 test files**. Today the codebase is organized as a **flat `app/` monolith** with cross-cutting imports between engines, shared global state (`ecs_state.py`), and three large route files (`main.py`, `routes_mvp.py`, `routes_ai_sdlc_governance.py`).

The product navigation already defines **seven logical boundaries** (six product modules + shared components), mirrored in `ecs_nav_groups.html` and `module_capabilities.py`. This plan maps every file to one of those boundaries and proposes a **target folder layout under `src/modules/`** without moving, renaming, or changing any code in this phase.

### Design principles for the future refactor

1. **Module owns its pages, engines, templates, and API handlers** — no module imports another module's internals; only `shared` contracts.
2. **Shared kernel is thin** — state interfaces, drill standards, theme, nav shell, role permissions, mock data generators.
3. **Routes compose modules** — a single bootstrap (`main.py`) registers module routers; URLs remain stable during migration.
4. **Drilldown is a shared contract** — universal drill engine + per-module drill adapters.
5. **Evidence workflow spans Governance + Frameworks** — extract to `shared/services/evidence-workflow` with module-specific views.

---

## 2. Current Architecture (As-Is)

```
app/
├── main.py                    # Auth, dashboard, framework pages, evidence review POSTs
├── routes_mvp.py              # ~80 MVP routes (Executive, Ops, Gov, partial GRC)
├── routes_grc_demo.py         # GRC drill APIs
├── routes_ai_sdlc_governance.py  # AI SDLC pages + APIs
├── evidence_routes.py         # Bulk upload / evidence API
├── ecs_state.py               # Global in-memory state (all modules)
├── *_engine.py / *_module.py  # 60+ domain engines (flat)
└── templates/
    ├── *.html                 # Page templates (flat prefix: mvp_, dashboard, framework)
    └── partials/              # 90+ shared partials
```

### Pain points for multi-developer work

| Issue | Impact |
|-------|--------|
| `routes_mvp.py` is 1,600+ lines | Merge conflicts across all teams |
| `module_capabilities.py` is 800+ lines | All module KPI builders in one file |
| `enterprise_context.py` injects all widgets | Touching shared context affects every page |
| `ecs_state.py` is global mutable state | Framework change can break Governance queues |
| Drill engines split across 10+ files | No single module boundary for traceability |
| Templates in flat `partials/` | Hard to know ownership of a partial |

---

## 3. Proposed Target Structure

```
src/
├── platform/                          # Bootstrap only (future home of main.py)
│   ├── app.py
│   ├── router_registry.py
│   └── config.py
│
├── modules/
│   ├── executive-overview/
│   │   ├── routes/
│   │   ├── pages/                     # templates
│   │   ├── engines/
│   │   ├── components/                # partials scoped to exec
│   │   └── tests/
│   │
│   ├── frameworks/
│   │   ├── routes/
│   │   ├── pages/
│   │   ├── engines/
│   │   ├── components/
│   │   └── tests/
│   │
│   ├── operations/
│   │   ├── routes/
│   │   ├── pages/
│   │   ├── engines/
│   │   ├── components/
│   │   └── tests/
│   │
│   ├── governance/
│   │   ├── routes/
│   │   ├── pages/
│   │   ├── engines/
│   │   ├── components/
│   │   └── tests/
│   │
│   ├── enterprise-grc/
│   │   ├── routes/
│   │   ├── pages/
│   │   ├── engines/
│   │   ├── components/
│   │   └── tests/
│   │
│   └── ai-sdlc/
│       ├── routes/
│       ├── pages/
│       ├── engines/
│       ├── components/
│       └── tests/
│
└── shared/
    ├── components/                    # nav, sidebar, theme, layout macros
    ├── drilldowns/                    # universal drill, pagination, modal shells
    ├── tables/                        # executive table system, governance table framework
    ├── charts/                        # executive charts system, compact chart
    ├── modals/                        # upload, exception, workflow modals
    ├── services/                      # ecs_state, audit_trail, role_permissions
    ├── utils/                         # demo_data_standards, pagination, filters
    └── contracts/                     # Typed interfaces between modules
```

### URL stability

All existing routes (`/mvp/*`, `/framework/*`, `/dashboard/*`, `/api/*`) MUST remain unchanged during migration. Module routers mount at the same paths via `platform/router_registry.py`.

---

## 4. Module Boundary Definitions

| Module | Nav group | Owns |
|--------|-----------|------|
| **executive-overview** | Executive Overview | Dashboards, demo overview, enterprise, pan-india, reports, trends |
| **frameworks** | Frameworks | Framework pages, loader, admin, catalog, KPI/workflow drills |
| **operations** | Operations | Scheduler, bulk upload, integrations, onboarding, AI Ops Assistant |
| **governance** | Governance | Audit prep, evidence health/reuse/lifecycle, completeness, comparison, search, approval analytics, evidence review |
| **enterprise-grc** | Enterprise GRC | Risk register, exceptions, CMDB, regulatory, heatmaps, correlation, governance analytics |
| **ai-sdlc** | AI SDLC Governance | Control tower, SDLC gates, AI registry, posture, reports, onboarding |
| **shared** | Cross-cutting | Theme, nav, state, universal drill, chatbot, filters, role permissions |

---

## 5. Complete File Mapping

Legend: **Suggested Module** uses kebab-case folder names from the target structure.

### 5.1 Platform & Route Registration

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/main.py` | `platform` | Application bootstrap, login, global middleware |
| `app/routes_mvp.py` | `platform` (split target) | Monolithic MVP router — future split into module `routes/` |
| `app/routes_grc_demo.py` | `enterprise-grc` | GRC-only API routes |
| `app/routes_ai_sdlc_governance.py` | `ai-sdlc` | AI SDLC pages and APIs |
| `app/evidence_routes.py` | `shared` | Cross-module evidence upload/API |
| `app/__init__.py` | `platform` | Package init |

---

### 5.2 Python Engines & Services — Executive Overview

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/demo_kpi_drill_engine.py` | `executive-overview` | Demo overview KPI drilldowns |
| `app/demo_metrics.py` | `executive-overview` | Enterprise KPIs, BU metrics, onboarding progress |
| `app/demo_seed.py` | `executive-overview` | Demo data seeding |
| `app/executive_analytics_engine.py` | `executive-overview` | Executive analytics computations |
| `app/ecs_reports_engine.py` | `executive-overview` | Report view generation |
| `app/reporting_module.py` | `executive-overview` | Report catalog and exports |
| `app/enterprise_mock_service.py` | `executive-overview` | Enterprise dashboard mock service |
| `app/integration_hub_executive_engine.py` | `executive-overview` | Integrations hub executive strip (exec nav context) |

---

### 5.3 Python Engines & Services — Frameworks

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/framework_catalog.py` | `frameworks` | Framework control/evidence catalog (source of truth) |
| `app/framework_dashboards.py` | `frameworks` | Per-framework dashboard context |
| `app/framework_governance_context.py` | `frameworks` | Framework governance context builder |
| `app/framework_governance_data.py` | `frameworks` | Framework relational governance data |
| `app/framework_intelligence.py` | `frameworks` | Framework loader theme intelligence |
| `app/framework_kpi_drill_engine.py` | `frameworks` | Framework executive KPI drills |
| `app/framework_loader_service.py` | `frameworks` | Framework loader ingest/activate |
| `app/framework_onboarding_engine.py` | `frameworks` | Framework admin onboarding |
| `app/framework_trends_engine.py` | `frameworks` | Framework trend panels |
| `app/framework_workflow_engine.py` | `frameworks` | Framework-scoped workflow metrics/drills |
| `app/ecs_row_drill_engine.py` | `frameworks` | Framework table row/tab drilldowns |
| `app/itpp_module.py` | `frameworks` | ITPP command center (framework-specific) |
| `app/control_validation_engine.py` | `frameworks` | Control validation panels on framework pages |
| `app/application_governance.py` | `frameworks` | Application grid drilldown on framework pages |

---

### 5.4 Python Engines & Services — Operations

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/scheduler_module.py` | `operations` | Scheduler dashboard data |
| `app/scheduler_intelligence.py` | `operations` | Scheduler scan drill-down |
| `app/operations_intelligence.py` | `operations` | Operations intelligence context |
| `app/operations_catalog.py` | `operations` | Operations module catalog |
| `app/operations_filter_engine.py` | `operations` | Operations-specific filters |
| `app/operations_mock_data.py` | `operations` | Operations mock datasets |
| `app/onboarding_engine.py` | `operations` | Application onboarding workflow |
| `app/integrations_module.py` | `operations` | Integrations dashboard |
| `app/integration_health_engine.py` | `operations` | Connector health scoring |
| `app/ai_ops_assistant_engine.py` | `operations` | AI Ops Assistant copilot |
| `app/ai_ops_summary_engine.py` | `operations` | AI Ops summary pages |
| `app/evidence_repository.py` | `operations` | Upload tracker (bulk upload page) |
| `app/resubmission.py` | `operations` | Resubmission workflows tied to upload |

---

### 5.5 Python Engines & Services — Governance

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/audit_schedule_engine.py` | `governance` | Audit prep calendar, KPI drills |
| `app/audit_prep_data.py` | `governance` | Audit package/export previews |
| `app/analytics_module.py` | `governance` | Completeness, comparison, trends, enterprise analytics (gov-facing) |
| `app/evidence_workflow_engine.py` | `shared` → consumed by `governance` | Evidence lifecycle state machine (cross-module) |
| `app/evidence_review.py` | `governance` | Evidence review screen builder |
| `app/evidence_approval_engine.py` | `governance` | Evidence approval analytics |
| `app/evidence_health_engine.py` | `governance` | Evidence health scoring |
| `app/governance_completeness_engine.py` | `governance` | Completeness enrichment |
| `app/governance_data_enrichment.py` | `governance` | Relational evidence/findings enrichment |
| `app/governance_intelligence.py` | `governance` | Governance analytics intelligence |
| `app/governance_lifecycle_engine.py` | `governance` | Lifecycle timeline engine |
| `app/governance_relational_model.py` | `governance` | Relational governance model |
| `app/governance_mock_data.py` | `governance` | Governance mock enrichments |
| `app/missing_evidence_engine.py` | `governance` | Missing evidence registry |
| `app/search_module.py` | `governance` | Evidence search discovery |
| `app/comparison_engine.py` | `governance` | App comparison engine |
| `app/gap_export_engine.py` | `governance` | Gap export for comparison |
| `app/workflow_module.py` | `governance` | Leadership/work queues |
| `app/operational_workflows.py` | `governance` | Close-gap, assign-owner, mock-audit flows |
| `app/operational_mock_data.py` | `governance` | Operational workflow mock data |
| `app/exception_state_engine.py` | `governance` | Exception state (also surfaced in GRC) |

---

### 5.6 Python Engines & Services — Enterprise GRC

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/grc_module_demo.py` | `enterprise-grc` | Risk register + governance analytics drills |
| `app/grc_demo_service.py` | `enterprise-grc` | GRC demo service wrapper |
| `app/enterprise_grc.py` | `enterprise-grc` | Enterprise GRC data structures |
| `app/correlation_engine.py` | `enterprise-grc` | Cross-tool correlation graph |
| `app/ecs_governance_drilldowns.py` | `enterprise-grc` | Deep GRC drill payloads |
| `app/ecs_governance_qa_engine.py` | `enterprise-grc` | Governance QA scans |
| `app/ecs_governance_framework.py` | `enterprise-grc` | GRC governance table framework |
| `app/ecs_demo_remediation.py` | `enterprise-grc` | Demo remediation scenarios |

---

### 5.7 Python Engines & Services — AI SDLC

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/ai_sdlc_governance_service.py` | `ai-sdlc` | Control tower + onboarding service |
| `app/ai_sdlc_governance_mock.py` | `ai-sdlc` | Posture/registry/SDLC drill mocks |
| `app/ai_sdlc_control_tower_engine.py` | `ai-sdlc` | Control tower tab data |
| `app/ai_sdlc_onboarding_engine.py` | `ai-sdlc` | AI SDLC onboarding |
| `app/ai_sdlc_workflow_engine.py` | `ai-sdlc` | SDLC stage workflow |
| `app/ai_sdlc_workflow_store.py` | `ai-sdlc` | Workflow state store |
| `app/ai_sdlc_reports_engine.py` | `ai-sdlc` | AI SDLC reports |
| `app/ai_sdlc_knowledge_repository.py` | `ai-sdlc` | Knowledge repository |
| `app/ai_sdlc_document_artifacts.py` | `ai-sdlc` | Document artifacts |
| `app/ecs_ai_governance_drilldowns.py` | `ai-sdlc` | AI governance explainability |
| `app/ecs_sdlc_stage_dashboard.py` | `ai-sdlc` | SDLC gate stage dashboards |

---

### 5.8 Python Engines & Services — Shared

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/ecs_state.py` | `shared/services` | Global in-memory state |
| `app/demo_data_standards.py` | `shared/utils` | Standard drill row generators |
| `app/ecs_universal_drill_engine.py` | `shared/drilldowns` | Platform-wide drill router |
| `app/module_kpi_drill_engine.py` | `shared/drilldowns` | Module workspace KPI drills |
| `app/ecs_mock_engine.py` | `shared/services` | Mock engine facade |
| `app/enterprise_context.py` | `shared/services` | Shared template context builder |
| `app/module_capabilities.py` | `shared/services` | Module capability registry (split later) |
| `app/module_workspace.py` | `shared/components` | Workspace shell builder |
| `app/nav_counter_engine.py` | `shared/services` | Nav badge counters |
| `app/ecs_nav_framework.py` | `shared/components` | Framework nav helpers |
| `app/role_permissions.py` | `shared/services` | Role permission matrix |
| `app/role_filter_scope.py` | `shared/services` | Role-scoped filter defaults |
| `app/global_filter_engine.py` | `shared/utils` | Global filter engine |
| `app/standard_filter_engine.py` | `shared/utils` | Standard filter profiles |
| `app/audit_trail.py` | `shared/services` | Audit trail logging |
| `app/ecs_logging.py` | `shared/utils` | ECS logging helpers |
| `app/pagination.py` | `shared/utils` | Pagination helpers |
| `app/table_schemas.py` | `shared/tables` | Table column schemas |
| `app/chatbot_engine.py` | `shared/services` | Chatbot NLP engine |
| `app/chatbot_context_engine.py` | `shared/services` | Chatbot context builder |
| `app/chatbot_nav.py` | `shared/services` | Chatbot deep-link builder |
| `app/chatbot_enhanced.py` | `shared/services` | Enhanced chatbot features |
| `app/evidence_api.py` | `shared/services` | Evidence API helpers |

---

### 5.9 Page Templates — Executive Overview

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/templates/dashboard.html` | `executive-overview` | Main role dashboard |
| `app/templates/cio_dashboard.html` | `executive-overview` | CIO dashboard |
| `app/templates/dashboard_vertical_head.html` | `executive-overview` | Vertical head dashboard |
| `app/templates/dashboard_compliance_head.html` | `executive-overview` | Compliance head dashboard |
| `app/templates/dashboard_functional_head.html` | `executive-overview` | Functional head dashboard |
| `app/templates/mvp_demo_overview.html` | `executive-overview` | Demo overview page |
| `app/templates/mvp_enterprise.html` | `executive-overview` | Enterprise page |
| `app/templates/mvp_pan_india.html` | `executive-overview` | Pan India page |
| `app/templates/mvp_reports.html` | `executive-overview` | Reports catalog |
| `app/templates/mvp_ecs_report.html` | `executive-overview` | Report viewer |
| `app/templates/mvp_trends.html` | `executive-overview` | Trends page (also GRC analytics overlap) |

---

### 5.10 Page Templates — Frameworks

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/templates/framework.html` | `frameworks` | Framework landing page |
| `app/templates/framework_loader.html` | `frameworks` | Framework loader page |
| `app/templates/mvp_framework_admin.html` | `frameworks` | Framework administration |

---

### 5.11 Page Templates — Operations

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/templates/mvp_scheduler.html` | `operations` | Scheduler page |
| `app/templates/mvp_bulk_upload.html` | `operations` | Bulk upload page |
| `app/templates/mvp_integrations.html` | `operations` | Integrations page |
| `app/templates/mvp_integrations_hub.html` | `operations` | Integrations hub |
| `app/templates/mvp_onboarding.html` | `operations` | Onboarding page |
| `app/templates/mvp_ai_ops_assistant.html` | `operations` | AI Ops Assistant |
| `app/templates/mvp_ai_ops_summary.html` | `operations` | AI Ops summary drill pages |

---

### 5.12 Page Templates — Governance

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/templates/mvp_audit_prep.html` | `governance` | Audit prep cockpit |
| `app/templates/mvp_evidence_health.html` | `governance` | Evidence health |
| `app/templates/mvp_reuse.html` | `governance` | Evidence reuse |
| `app/templates/mvp_lifecycle.html` | `governance` | Lifecycle |
| `app/templates/mvp_completeness.html` | `governance` | Completeness |
| `app/templates/mvp_comparison.html` | `governance` | App comparison |
| `app/templates/mvp_search.html` | `governance` | Search |
| `app/templates/mvp_evidence_approval.html` | `governance` | Evidence approval analytics |
| `app/templates/evidence_review.html` | `governance` | Evidence review screen |
| `app/templates/mvp_workflow_close_gap.html` | `governance` | Close gap workflow |
| `app/templates/mvp_workflow_assign_owner.html` | `governance` | Assign owner workflow |
| `app/templates/mvp_workflow_upload_missing.html` | `governance` | Upload missing workflow |
| `app/templates/mvp_workflow_mock_audit.html` | `governance` | Mock audit workflow |

---

### 5.13 Page Templates — Enterprise GRC

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/templates/mvp_risk_register.html` | `enterprise-grc` | Risk register |
| `app/templates/mvp_exceptions.html` | `enterprise-grc` | Exceptions / TD |
| `app/templates/mvp_exception_governance.html` | `enterprise-grc` | Exception governance |
| `app/templates/mvp_cmdb.html` | `enterprise-grc` | CMDB |
| `app/templates/mvp_regulatory.html` | `enterprise-grc` | Regulatory mapping |
| `app/templates/mvp_heatmaps.html` | `enterprise-grc` | Executive heatmaps |
| `app/templates/mvp_correlation.html` | `enterprise-grc` | Correlation |
| `app/templates/mvp_governance_analytics.html` | `enterprise-grc` | Governance analytics |

---

### 5.14 Page Templates — AI SDLC

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/templates/mvp_ai_sdlc_home.html` | `ai-sdlc` | AI SDLC home |
| `app/templates/mvp_ai_sdlc_control_tower.html` | `ai-sdlc` | Control tower |
| `app/templates/mvp_ai_sdlc_onboarding.html` | `ai-sdlc` | AI SDLC onboarding |
| `app/templates/mvp_ai_sdlc_worklist.html` | `ai-sdlc` | SDLC worklist stages |
| `app/templates/mvp_sdlc_gates.html` | `ai-sdlc` | SDLC gates overview |
| `app/templates/mvp_sdlc_gate_stage.html` | `ai-sdlc` | SDLC gate stage |
| `app/templates/mvp_ai_governance_posture.html` | `ai-sdlc` | AI governance posture |
| `app/templates/mvp_ai_registry.html` | `ai-sdlc` | AI registry |
| `app/templates/mvp_governance_quality.html` | `ai-sdlc` | Governance quality |
| `app/templates/mvp_ai_sdlc_reports.html` | `ai-sdlc` | AI SDLC reports list |
| `app/templates/mvp_ai_sdlc_report.html` | `ai-sdlc` | AI SDLC report view |
| `app/templates/mvp_ai_sdlc_evidence_viewer.html` | `ai-sdlc` | Evidence viewer |

---

### 5.15 Page Templates — Shared / Platform

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/templates/login.html` | `platform` | Login page |

---

### 5.16 Partial Templates — Shared Components

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/templates/partials/enterprise_theme.html` | `shared/components` | Global theme + includes |
| `app/templates/partials/mvp_styles.html` | `shared/components` | MVP style bundle |
| `app/templates/partials/ecs_sidebar.html` | `shared/components` | Sidebar shell |
| `app/templates/partials/mvp_sidebar.html` | `shared/components` | MVP sidebar variant |
| `app/templates/partials/ecs_nav_groups.html` | `shared/components` | Nav group definitions |
| `app/templates/partials/ecs_nav_shell.js.html` | `shared/components` | Nav shell JS |
| `app/templates/partials/ecs_nav_ai_sdlc.html` | `shared/components` | AI SDLC nav section |
| `app/templates/partials/nav_badge.html` | `shared/components` | Nav badge macro |
| `app/templates/partials/ecs_ux_macros.html` | `shared/components` | KPI cards, page headers |
| `app/templates/partials/ecs_ux_system.html` | `shared/components` | UX system JS |
| `app/templates/partials/mvp_workspace_macros.html` | `shared/components` | Workspace exec strip, filters |
| `app/templates/partials/mvp_workspace_styles.html` | `shared/components` | Workspace styles |
| `app/templates/partials/mvp_capability_styles.html` | `shared/components` | Capability styles |
| `app/templates/partials/mvp_module_header.html` | `shared/components` | Module page header |
| `app/templates/partials/mvp_module_actions.html` | `shared/components` | Module action buttons |
| `app/templates/partials/mvp_quick_links.html` | `shared/components` | Quick links |
| `app/templates/partials/role_metrics_strip.html` | `shared/components` | Role metrics strip |
| `app/templates/partials/chatbot_global.html` | `shared/components` | Global chatbot |
| `app/templates/partials/ecs_floating_action_portal.html` | `shared/components` | FAB portal |
| `app/templates/partials/enterprise_widgets.html` | `shared/components` | Enterprise widget macros |
| `app/templates/partials/workflow_styles.html` | `shared/components` | Workflow styles |
| `app/templates/partials/workflow_guidance.html` | `shared/components` | Workflow guidance |

---

### 5.17 Partial Templates — Shared Drilldowns

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/templates/partials/ecs_universal_drill.html` | `shared/drilldowns` | Universal KPI/row/chart drill |
| `app/templates/partials/ecs_module_kpi_drill.html` | `shared/drilldowns` | Module KPI drill modal |
| `app/templates/partials/ecs_framework_kpi_drill.html` | `frameworks` | Framework KPI/workflow/row drill |
| `app/templates/partials/grc_demo_drill_modal.html` | `enterprise-grc` | GRC drill modal |
| `app/templates/partials/ai_sdlc_drill_modal.html` | `ai-sdlc` | AI SDLC drill modal |
| `app/templates/partials/ecs_pagination.html` | `shared/drilldowns` | Pagination system |
| `app/templates/partials/executive_dashboard_client.html` | `executive-overview` | Exec drill modal client |
| `app/templates/partials/analytics_filter_client.html` | `enterprise-grc` | GRC analytics drill injection |
| `app/templates/partials/grc_governance_analytics_client.html` | `enterprise-grc` | GRC trend bar drill attrs |

---

### 5.18 Partial Templates — Shared Tables

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/templates/partials/ecs_executive_table_system.html` | `shared/tables` | Executive table layout system |
| `app/templates/partials/ecs_top_risk_table_fix.html` | `shared/tables` | Top risk table column guard |
| `app/templates/partials/ecs_governance_table_framework.html` | `shared/tables` | Governance table injection |
| `app/templates/partials/ecs_governance_table_macros.html` | `shared/tables` | Governance table macros |
| `app/templates/partials/mvp_reuse_table.html` | `governance` | Reuse mapping table |

---

### 5.19 Partial Templates — Shared Charts

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/templates/partials/executive_charts_system.html` | `shared/charts` | Chart rendering system |
| `app/templates/partials/executive_chart_macros.html` | `shared/charts` | Chart macros |
| `app/templates/partials/executive_chart_card.html` | `shared/charts` | Chart card wrapper |
| `app/templates/partials/compact_chart.html` | `shared/charts` | Compact chart partial |
| `app/templates/partials/analytics_macros.html` | `shared/charts` | Analytics chart macros |

---

### 5.20 Partial Templates — Shared Modals

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/templates/partials/evidence_upload_modal.html` | `shared/modals` | Evidence upload modal |
| `app/templates/partials/raise_exception_modal.html` | `shared/modals` | Raise exception modal |
| `app/templates/partials/upload_modals.html` | `operations` | Bulk upload modals |
| `app/templates/partials/scheduler_modals.html` | `operations` | Scheduler drill modals |
| `app/templates/partials/onboarding_modals.html` | `operations` | Onboarding modals |
| `app/templates/partials/integrations_modals.html` | `operations` | Integrations modals |
| `app/templates/partials/audit_prep_modals.html` | `governance` | Audit prep modals |
| `app/templates/partials/gap_export_modal.html` | `governance` | Gap export modal |
| `app/templates/partials/ai_sdlc_workflow_modals.html` | `ai-sdlc` | AI SDLC workflow modals |

---

### 5.21 Partial Templates — Frameworks Components

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/templates/partials/framework_executive_strip.html` | `frameworks` | Framework exec KPI strip |
| `app/templates/partials/framework_executive_extras.html` | `frameworks` | Framework exec extras |
| `app/templates/partials/framework_drill_panels.html` | `frameworks` | Framework tab drill panels |
| `app/templates/partials/framework_relational_evidence.html` | `frameworks` | Evidence repository table |
| `app/templates/partials/framework_workflow_table.html` | `frameworks` | Workflow status table |
| `app/templates/partials/framework_governance_panel.html` | `frameworks` | Governance panel |
| `app/templates/partials/framework_application_grid.html` | `frameworks` | Application grid |
| `app/templates/partials/framework_trends_panel.html` | `frameworks` | Trends panel |
| `app/templates/partials/framework_insights.html` | `frameworks` | Framework insights |
| `app/templates/partials/itpp_command_center.html` | `frameworks` | ITPP command center |
| `app/templates/partials/itpp_operational_panel.html` | `frameworks` | ITPP operational panel |
| `app/templates/partials/control_validation_panel.html` | `frameworks` | Control validation panel |

---

### 5.22 Partial Templates — Governance Components

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/templates/partials/evidence_workflow_macros.html` | `shared` + `governance` | Workflow counter macros (used everywhere) |
| `app/templates/partials/evidence_workflow_system.html` | `shared` + `governance` | Workflow summary JSON bootstrap |
| `app/templates/partials/governance_analytics_panel.html` | `enterprise-grc` | Governance analytics panel |
| `app/templates/partials/grc_kpis.html` | `enterprise-grc` | GRC KPI tile macro |
| `app/templates/partials/owner_work_queue.html` | `governance` | Owner work queue |
| `app/templates/partials/auditor_review_queue.html` | `governance` | Auditor review queue |
| `app/templates/partials/leadership_work_queue.html` | `governance` | Leadership queue |
| `app/templates/partials/page_workflow_queue.html` | `governance` | Page workflow queue |
| `app/templates/partials/mvp_upload_missing_panel.html` | `governance` | Upload missing panel |
| `app/templates/partials/gap_export_client.html` | `governance` | Gap export client JS |
| `app/templates/partials/completeness_filter_client.html` | `governance` | Completeness filters |
| `app/templates/partials/comparison_filter_client.html` | `governance` | Comparison filters |
| `app/templates/partials/lifecycle_filter_client.html` | `governance` | Lifecycle filters |

---

### 5.23 Partial Templates — Operations Components

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/templates/partials/scheduler_styles.html` | `operations` | Scheduler styles |
| `app/templates/partials/operations_filter_client.html` | `operations` | Operations filter client |
| `app/templates/partials/integrations_health_panel.html` | `operations` | Integrations health |
| `app/templates/partials/integrations_hub_executive_client.html` | `operations` | Integrations hub client |
| `app/templates/partials/upload_simulation_client.html` | `operations` | Upload simulation JS |
| `app/templates/partials/onboarding_simulator.html` | `operations` | Onboarding simulator |
| `app/templates/partials/ai_ops_assistant_client.html` | `operations` | AI Ops client JS |

---

### 5.24 Partial Templates — AI SDLC Components

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/templates/partials/ai_sdlc_styles.html` | `ai-sdlc` | AI SDLC styles |
| `app/templates/partials/ai_sdlc_subnav.html` | `ai-sdlc` | AI SDLC subnav |
| `app/templates/partials/ai_sdlc_control_tower_client.html` | `ai-sdlc` | Control tower client |
| `app/templates/partials/ai_sdlc_onboarding_client.html` | `ai-sdlc` | Onboarding client |
| `app/templates/partials/ai_sdlc_worklist.html` | `ai-sdlc` | Worklist partial |
| `app/templates/partials/ai_sdlc_stage_workspace.html` | `ai-sdlc` | Stage workspace |
| `app/templates/partials/ai_sdlc_stage_artifact_dashboard.html` | `ai-sdlc` | Artifact dashboard |
| `app/templates/partials/ecs_governance_chrome.html` | `ai-sdlc` | SDLC governance chrome |
| `app/templates/partials/ecs_governance_shell.html` | `ai-sdlc` | SDLC governance shell |

---

### 5.25 Partial Templates — Shared Filters & Analytics

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `app/templates/partials/analytics_filter_bar.html` | `shared/utils` | Analytics filter bar |
| `app/templates/partials/standard_filter_include.html` | `shared/utils` | Standard filter include |
| `app/templates/partials/standard_filter_client.html` | `shared/utils` | Standard filter client |

---

### 5.26 Tests

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `tests/test_demo_polish.py` | `executive-overview` | Demo overview drills |
| `tests/test_ecs_demo_readiness.py` | `shared` | Cross-module readiness |
| `tests/test_framework_kpi_drilldowns.py` | `frameworks` | Framework KPI drills |
| `tests/test_framework_specific_kpis.py` | `frameworks` | Framework KPI uniqueness |
| `tests/test_enterprise_drilldown_validation.py` | `frameworks` | Framework workflow drills |
| `tests/test_top_risk_application_rendering.py` | `enterprise-grc` | Top risk table rendering |
| `tests/test_module_kpi_drill.py` | `shared/drilldowns` | Module KPI drill |
| `tests/test_ecs_platform_governance.py` | `shared` | Platform-wide governance validation |
| `tests/test_ecs_governance_workflow.py` | `governance` | Evidence workflow |
| `tests/test_ai_ops_assistant.py` | `operations` | AI Ops Assistant |
| `tests/test_ai_sdlc_*.py` (6 files) | `ai-sdlc` | AI SDLC module tests |
| `tests/test_registry_table_rendering.py` | `ai-sdlc` | AI registry table |

---

### 5.27 Scripts & Root Files

| Current File | Suggested Module | Reason |
|--------------|------------------|--------|
| `scripts/validate_demo_engine.py` | `executive-overview` | Demo engine validation |
| `scripts/validate_audit_prep.py` | `governance` | Audit prep validation |
| `scripts/validate_framework_loader.py` | `frameworks` | Framework loader validation |
| `scripts/validate_demo_readiness.py` | `shared` | Cross-module readiness |
| `scripts/validate_templates.py` | `shared` | Template validation |
| `scripts/run_ecs_validation.py` | `shared` | Full validation runner |
| `start_ecs.sh` | `platform` | Server startup |
| `requirements.txt` | `platform` | Dependencies |
| `ECS_ARCHITECTURE_BASELINE.md` | `docs` | Architecture reference |
| `.cursor/rules/ecs-demo-quality-standard.mdc` | `shared` | Demo quality standard |

---

## 6. API Route Ownership (Future Split)

| Route prefix | Owner module |
|--------------|--------------|
| `/dashboard/*` | `executive-overview` |
| `/mvp/demo-overview`, `/mvp/enterprise`, `/mvp/pan-india`, `/mvp/reports`, `/mvp/trends` | `executive-overview` |
| `/api/demo/*` | `executive-overview` |
| `/framework/*`, `/api/framework/*` | `frameworks` |
| `/mvp/framework-*`, `/api/framework-loader/*`, `/api/framework-onboarding/*` | `frameworks` |
| `/mvp/scheduler`, `/mvp/upload`, `/mvp/integrations*`, `/mvp/onboarding`, `/mvp/ai-ops-*` | `operations` |
| `/mvp/audit-prep`, `/mvp/evidence-*`, `/mvp/reuse`, `/mvp/lifecycle`, `/mvp/completeness`, `/mvp/comparison`, `/mvp/search`, `/mvp/workflow/*` | `governance` |
| `/evidence/review*`, `/api/audit-prep/*` | `governance` |
| `/api/ecs/workflow-drill` | `governance` (via shared adapter) |
| `/mvp/risk-register`, `/mvp/exceptions*`, `/mvp/cmdb`, `/mvp/regulatory`, `/mvp/heatmaps`, `/mvp/correlation`, `/mvp/governance-analytics` | `enterprise-grc` |
| `/api/grc-demo/*` | `enterprise-grc` |
| `/mvp/ai-sdlc/*`, `/mvp/sdlc-gates/*`, `/mvp/ai-governance`, `/mvp/ai-registry`, `/api/ai-sdlc/*` | `ai-sdlc` |
| `/api/ecs/universal-drill`, `/api/module-kpi/drill`, `/api/ecs/filters/*` | `shared/drilldowns` |
| `/login`, `/logout`, `/chat` | `platform` |

---

## 7. Recommended Migration Phases (Future — Requires Approval)

### Phase 0 — Contract definition (1 week)
- Define `shared/contracts/` interfaces: `DrillResponse`, `ModuleContext`, `WorkflowState`, `FilterContext`
- Document allowed import directions in `ECS_MODULE_OWNERSHIP.md`
- No file moves

### Phase 1 — Shared extraction (2 weeks)
- Move drilldowns, theme, nav, pagination to `src/shared/` (re-export from old paths)
- Split `demo_data_standards.py` consumers to use shared utils only
- Add module-level test directories mirroring ownership

### Phase 2 — Route decomposition (2 weeks)
- Extract `routes_grc_demo.py` → `enterprise-grc/routes/`
- Extract `routes_ai_sdlc_governance.py` → `ai-sdlc/routes/`
- Split `routes_mvp.py` by nav group into module route files
- `platform/router_registry.py` mounts all routers at existing paths

### Phase 3 — Engine & template colocation (3 weeks)
- Move engines and templates module-by-module starting with **ai-sdlc** (most isolated)
- Then **frameworks**, **operations**, **governance**, **enterprise-grc**, **executive-overview**
- Keep compatibility shims in `app/` until all imports updated

### Phase 4 — State partitioning (2 weeks)
- Partition `ecs_state.py` into module-owned state slices with shared registry
- Evidence workflow becomes shared service with module adapters

### Phase 5 — Cleanup (1 week)
- Remove `app/` compatibility shims
- Consolidate `module_capabilities.py` into per-module capability builders
- Final validation suite per module

**Total estimated effort:** 10–11 weeks with 6 developers (one per module + platform lead)

---

## 8. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking drilldown traceability during split | Keep `ecs_universal_drill_engine` in shared until all modules register adapters |
| `ecs_state` coupling | Introduce state facades per module; shared registry read-only across boundaries |
| Template include path churn | Use Jinja loader with multi-path search; module templates namespaced |
| Route regression | Contract tests asserting all 120+ routes return 200 for smoke roles |
| Duplicate KPI logic | Centralize `demo_data_standards.ensure_drill_rows` in shared; modules supply row builders only |

---

## 9. Approval Gate

**This document is analysis only.** No files have been moved, renamed, or modified.

Before implementation:
1. Review module boundaries with product owner
2. Assign module owners (see `ECS_MODULE_OWNERSHIP.md`)
3. Review dependency graph (see `ECS_DEPENDENCY_REPORT.md`)
4. Approve Phase 0 start

**Awaiting approval to proceed.**
