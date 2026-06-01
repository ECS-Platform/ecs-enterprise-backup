# ECS Dependency Report

**Status:** Analysis only — no code changes authorized  
**Date:** 2026-05-29  
**Purpose:** Map cross-module dependencies, shared kernel coupling, and refactor risk areas

---

## 1. Dependency Overview

ECS today is a **highly interconnected monolith**. No module is fully isolated. The shared kernel (`ecs_state`, `enterprise_context`, `demo_data_standards`, universal drill) creates **hub-and-spoke coupling** where most engines import from 3–5 shared modules and occasionally from peer engines.

```
                    ┌─────────────────┐
                    │   ecs_state     │
                    │  (global hub)   │
                    └────────┬────────┘
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │ Frameworks  │◄──►│ Governance  │◄──►│ Enterprise  │
    │   engines   │    │   engines   │    │     GRC     │
    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
           │                   │                   │
           └───────────────────┼───────────────────┘
                               ▼
                    ┌─────────────────┐
                    │     shared      │
                    │ demo_data_std   │
                    │ universal_drill │
                    │ enterprise_ctx  │
                    └─────────────────┘
```

---

## 2. Shared Kernel Dependencies (All Modules Depend On These)

| Shared asset | Imported by | Coupling severity |
|--------------|-------------|-------------------|
| `app/ecs_state.py` | 40+ files | **Critical** — global mutable workflow state |
| `app/demo_data_standards.py` | 25+ files | **High** — drill row generation standard |
| `app/enterprise_context.py` | All MVP pages via `_base_ctx` | **High** — injects widgets for every page |
| `app/role_permissions.py` | 15+ files | **Medium** — role gates |
| `app/framework_catalog.py` | 30+ files | **Critical** — frameworks team owns but all modules read |
| `app/demo_metrics.py` | 10+ files | **Medium** — executive KPIs used in shared context |
| `app/ecs_universal_drill_engine.py` | Route layer + 2 engines | **High** — delegates to all module drills |
| `app/module_capabilities.py` | Routes + drill engine | **High** — monolithic capability registry |
| `app/audit_trail.py` | Evidence review, workflow | **Medium** — cross-cutting audit log |

---

## 3. Module-to-Module Dependencies (Direct Imports — Problem Areas)

These are **forbidden in target architecture** but exist today:

| Source module | Target module | Files involved | Nature |
|---------------|---------------|----------------|--------|
| **Frameworks** | **Governance** | `framework_governance_data.py` → `governance_data_enrichment.py`, `governance_relational_model.py` | Framework pages render governance relational data |
| **Frameworks** | **Governance** | `evidence_review.py` ← called from framework templates | Review screen is governance-owned |
| **Governance** | **Frameworks** | `analytics_module.py` → `framework_catalog.py` | Completeness uses catalog stats |
| **Governance** | **Frameworks** | `audit_schedule_engine.py` → `framework_catalog.py` | Audit prep scopes by framework |
| **Enterprise GRC** | **Governance** | `grc_module_demo.py` → `governance_mock_data`, analytics | GRC drills reuse governance datasets |
| **Enterprise GRC** | **Executive** | `grc_module_demo.py` → `demo_metrics` patterns | Shared KPI builders |
| **Executive** | **Frameworks** | `demo_kpi_drill_engine.py` → `framework_catalog.py` | Demo overview shows framework heatmap |
| **Executive** | **Governance** | `analytics_module.py` used by enterprise dashboard | Enterprise page uses gov analytics |
| **Operations** | **Frameworks** | `scheduler_module.py` → framework names from catalog | Scan jobs scoped to frameworks |
| **Operations** | **Governance** | `evidence_repository.py` → evidence state | Uploads affect governance queues |
| **AI SDLC** | **Governance** | `ai_sdlc_workflow_engine.py` → governance table framework | SDLC tables use gov table injection |
| **AI SDLC** | **Shared/GRC** | `ecs_governance_drilldowns.py` overlap | AI and GRC share drill payload shapes |
| **Universal drill** | **All modules** | `ecs_universal_drill_engine.py` imports 6+ drill engines | Central router knows all modules |

---

## 4. Route Layer Dependencies

| Route file | Registers routes for | Lines (approx) | Modules touched |
|------------|---------------------|----------------|-----------------|
| `main.py` | Platform, dashboards, frameworks, evidence review | ~1,200 | 4 modules |
| `routes_mvp.py` | Executive, ops, gov, partial GRC | ~1,680 | 5 modules |
| `routes_grc_demo.py` | GRC APIs | ~25 | 1 module |
| `routes_ai_sdlc_governance.py` | AI SDLC | ~350 | 1 module |
| `evidence_routes.py` | Evidence API | ~200 | 2 modules |

**Risk:** `routes_mvp.py` is the single largest merge-conflict surface. Contains `_base_ctx()` which pulls `enterprise_widgets_context()` affecting all modules simultaneously.

---

## 5. Template Include Dependencies

### 5.1 Global include chain (every MVP page)

```
mvp_*.html
  └── mvp_styles.html
        └── enterprise_theme.html
              ├── ecs_executive_table_system.html    [shared/tables]
              ├── evidence_workflow_system.html      [shared/governance]
              ├── ecs_pagination.html                [shared/drilldowns]
              ├── ecs_module_kpi_drill.html          [shared/drilldowns]
              ├── grc_demo_drill_modal.html          [enterprise-grc]
              ├── ai_sdlc_drill_modal.html           [ai-sdlc]
              └── ecs_universal_drill.html           [shared/drilldowns]
```

**Impact:** Any module page load pulls **6 shared partials + 2 module drill modals**. Theme changes affect all teams.

### 5.2 Cross-module template includes

| Template | Includes from other module | Risk |
|----------|---------------------------|------|
| `framework.html` | `evidence_workflow_macros.html` (governance/shared) | Expected — workflow counters |
| `mvp_governance_analytics.html` | `governance_analytics_panel.html` (GRC) | GRC panel on gov-adjacent page |
| `mvp_audit_prep.html` | Inline audit drill JS (governance) | Self-contained but large |
| `mvp_trends.html` | `grc_demo_drill_modal.html` (GRC) | Executive page uses GRC modal |
| `mvp_heatmaps.html` | `grc_kpis.html` (GRC) | Executive heatmaps under GRC nav |

---

## 6. Data Flow Dependencies

### 6.1 Evidence workflow (highest cross-module coupling)

```
App Owner action (Governance: evidence_review.py)
    → mutates ecs_state.submitted_controls / approved_controls
    → updates evidence_workflow_engine counters
    → reflected on Framework pages (framework.html counters)
    → reflected on Dashboard (dashboard.html counters)
    → reflected on Governance pages (audit_prep, evidence_health)
    → audit_trail.log_event (shared)
    → close_observations_for_control (Governance → governance_relational_model)
```

**Refactor implication:** Evidence workflow MUST become a **shared service** with event hooks, not duplicated in Frameworks and Governance.

### 6.2 Framework catalog as read-only dependency

```
framework_catalog.py (Frameworks)
    → read by: demo_kpi_drill, analytics_module, module_capabilities,
               nav_counter_engine, grc_module_demo, scheduler_module,
               enterprise_context, 20+ others
```

**Refactor implication:** Publish `FrameworkCatalogReader` interface in `shared/contracts/`. Only Frameworks team writes; all others read through contract.

### 6.3 Drilldown delegation graph

```
ecs_universal_drill_engine (shared)
    ├── demo_kpi_drill_engine          [executive-overview]
    ├── framework_kpi_drill_engine       [frameworks]
    ├── framework_workflow_engine        [frameworks]
    ├── ecs_row_drill_engine             [frameworks]
    ├── module_kpi_drill_engine          [shared → module_capabilities]
    ├── grc_module_demo                  [enterprise-grc]
    ├── ai_sdlc_governance_mock          [ai-sdlc]
    ├── audit_schedule_engine            [governance]
    └── generate_standard_drill_row      [shared fallback]
```

**Refactor implication:** Replace central if/else with **drill adapter registry** — each module registers its metrics at startup.

---

## 7. State Coupling in `ecs_state.py`

| State slice | Primary writer | Primary readers |
|-------------|----------------|-----------------|
| `submitted_controls`, `approved_controls`, `rejected_controls` | Governance (evidence review POSTs) | Frameworks, Governance, Dashboard |
| `missing_evidence_registry` | Governance | Frameworks, Audit prep |
| `closed_observations` | Governance | Framework findings panels |
| `scheduler_data`, `scheduler_failures` | Operations | Scheduler page, nav counters |
| `framework_onboarding_registry` | Frameworks | Framework admin, loader |
| `exception_registry` | Governance/GRC | Exceptions pages |
| `workflow_audit_history` | Governance | Universal drill sections |
| `grc_action_log` | Enterprise GRC | GRC pages |

**Partition recommendation:**

```
shared/services/state/
├── workflow_state.py      ← Governance owns
├── framework_state.py     ← Frameworks owns
├── operations_state.py    ← Operations owns
├── grc_state.py           ← Enterprise GRC owns
├── ai_sdlc_state.py       ← AI SDLC owns
└── registry.py            ← Shared facade (read-only cross-module)
```

---

## 8. Circular Dependency Risks

| Cycle | Path | Severity |
|-------|------|----------|
| Framework ↔ Governance | `framework_governance_data` → `governance_relational_model` → `framework_catalog` | **High** |
| Universal drill ↔ All modules | Drill engine imports all module drills; modules use universal for fallback | **Medium** |
| Enterprise context ↔ All modules | Context builder imports module capabilities; capabilities import analytics/governance | **High** |
| Evidence workflow ↔ Review | `evidence_workflow_engine` ↔ `evidence_review` ↔ `ecs_state` | **Medium** |

**No hard Python circular imports detected** (lazy imports used in several places), but **logical cycles** exist and will worsen during split without contracts.

---

## 9. External / Root Dependencies

| Dependency | Used by | Notes |
|------------|---------|-------|
| FastAPI | Platform | Web framework |
| Jinja2 | All templates | Template engine |
| Bootstrap 5.3 CDN | All pages | UI framework |
| hashlib (seed) | demo_data_standards | Deterministic mock data |
| pytest | tests | Test runner |
| httpx (TestClient) | tests | API testing |

No database, no Redis, no external API calls in demo mode.

---

## 10. Test Dependency Map

| Test suite | Depends on modules | CI gate level |
|------------|-------------------|---------------|
| `test_ecs_demo_readiness.py` | All (route smoke) | **P0** — blocks release |
| `test_ecs_platform_governance.py` | Shared + Governance + Frameworks | **P0** |
| `test_framework_kpi_drilldowns.py` | Frameworks | **P1** |
| `test_enterprise_drilldown_validation.py` | Frameworks | **P1** |
| `test_ai_sdlc_*.py` | AI SDLC | **P1** |
| `test_demo_polish.py` | Executive + Shared | **P2** |
| `test_module_kpi_drill.py` | Shared + Operations | **P2** |

**Recommendation:** After modular split, each module runs its own test job in CI; shared runs `test_ecs_demo_readiness.py` as integration gate.

---

## 11. Dependency Metrics (Static Analysis)

| Metric | Count |
|--------|-------|
| Python files in `app/` | 104 |
| Template files | 149 |
| Route handlers (approx) | 120+ |
| Engines with `drill` in name or purpose | 14 |
| Files importing `ecs_state` | ~40 |
| Files importing `framework_catalog` | ~30 |
| Files importing `demo_data_standards` | ~25 |
| Shared partials included globally | 10+ |

---

## 12. Highest-Risk Refactor Targets (Priority Order)

1. **`routes_mvp.py` split** — affects every team; do first with re-export shim
2. **`ecs_state.py` partition** — blocks independent module testing
3. **`module_capabilities.py` split** — each module owns its `_view` builder
4. **`enterprise_context.py` provider registry** — modules register widgets instead of central list
5. **`ecs_universal_drill_engine.py` adapter registry** — remove central knowledge of all modules
6. **`framework_catalog.py` read contract** — formalize as shared read-only API
7. **`evidence_workflow_engine.py` elevation to shared service** — both Frameworks and Governance consume

---

## 13. Recommended Shared Contracts (Phase 0 Deliverables)

| Contract | Methods / shape | Owner |
|----------|-----------------|-------|
| `DrillAdapter` | `drill(metric, count, role) → DrillResponse` | Shared |
| `FrameworkCatalogReader` | `controls(fw)`, `stats()`, `evidence_count()` | Frameworks impl, Shared iface |
| `WorkflowStateReader` | `counters(role)`, `queues(role)` | Governance impl, Shared iface |
| `ModuleContextProvider` | `build_context(role, filters) → dict` | Each module |
| `NavCounterProvider` | `badges(role) → dict` | Each module registers |
| `AuditTrailWriter` | `log_event(action, user, ...)` | Shared |

---

## 14. Dependency Report Summary

| Category | Status | Action required |
|----------|--------|-----------------|
| Shared kernel coupling | **High** | Partition state + context first |
| Cross-module Python imports | **Medium-High** | Replace with contracts |
| Route monolith | **Critical** | Split `routes_mvp.py` early |
| Template global includes | **Medium** | Namespace module partials |
| Drill delegation | **Medium** | Adapter registry pattern |
| Test isolation | **Low** | Add per-module CI jobs after split |

---

**This report is analysis only. No code has been modified. Await approval before implementation.**
