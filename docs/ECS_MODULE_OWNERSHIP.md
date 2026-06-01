# ECS Module Ownership

**Status:** Analysis only — no code changes authorized  
**Date:** 2026-05-29  
**Purpose:** Define team boundaries, ownership, and collaboration rules for the proposed modular ECS architecture

---

## 1. Module Owner Matrix

| Module | Suggested team | Primary owner role | Backup |
|--------|----------------|-------------------|--------|
| **executive-overview** | Executive Analytics | Lead: Dashboard / CIO experience dev | GRC analytics dev |
| **frameworks** | Framework Engineering | Lead: Framework catalog & drilldown dev | Governance dev |
| **operations** | Platform Operations | Lead: Scheduler / integrations dev | AI Ops dev |
| **governance** | Evidence & Audit | Lead: Audit prep / evidence workflow dev | Framework dev |
| **enterprise-grc** | GRC Analytics | Lead: Risk register / heatmaps dev | Executive analytics dev |
| **ai-sdlc** | AI Governance | Lead: AI SDLC / control tower dev | Governance dev |
| **shared** | Platform Core | Lead: Platform architect | All module leads (RFC review) |
| **platform** | Platform Core | Lead: FastAPI bootstrap / routing | Platform architect |

---

## 2. Ownership Scope by Module

### 2.1 Executive Overview

**Owns:**
- Role dashboards (`/dashboard`, `/dashboard/cio`, etc.)
- Demo Overview, Enterprise, Pan India, Reports, Trends pages
- Demo KPI drill engine and demo API suite (`/api/demo/*`)
- Report generation and export viewer
- Executive dashboard client (heatmap, BU drill modals)

**Does NOT own:**
- Framework-specific readiness (Frameworks team)
- GRC risk register (Enterprise GRC team)
- Evidence workflow state (Governance team — consumes via shared)

**Key files today:** `demo_kpi_drill_engine.py`, `demo_metrics.py`, `ecs_reports_engine.py`, `reporting_module.py`, `mvp_demo_overview.html`, `mvp_enterprise.html`, `dashboard*.html`

**Acceptance criteria for changes:**
- All executive KPIs remain drillable (≥25 rows)
- Demo overview heatmap cells trace to supporting records
- No regression on role-specific dashboard routing

---

### 2.2 Frameworks

**Owns:**
- All `/framework/{name}` pages and framework-specific KPI/workflow drills
- Framework Loader and Framework Administration
- Framework catalog, dashboards, governance context, trends
- Framework row/tab drill engine
- ITPP command center (framework-specific)

**Does NOT own:**
- Global evidence review POST handlers (Governance — but triggered from framework pages)
- Universal drill router (Shared)
- Nav framework list rendering (Shared — data from catalog)

**Key files today:** `framework_catalog.py`, `framework_kpi_drill_engine.py`, `framework_workflow_engine.py`, `ecs_row_drill_engine.py`, `framework.html`, `framework_drill_panels.html`

**Acceptance criteria:**
- 16 frameworks each have unique workflow metrics
- Every framework KPI, workflow counter, table row, and tab button drills down
- Framework catalog remains single source of truth for controls/evidence counts

---

### 2.3 Operations

**Owns:**
- Scheduler, Bulk Upload, Integrations, Integrations Hub, Onboarding
- AI Ops Assistant and summary pages
- Operations filter engine and operations mock data
- Scheduler/onboarding/upload modals

**Does NOT own:**
- Evidence repository core (Shared/Governance — upload lands in shared state)
- Executive integrations hub strip (Executive Overview — if split later)

**Key files today:** `scheduler_module.py`, `scheduler_intelligence.py`, `integrations_module.py`, `onboarding_engine.py`, `ai_ops_assistant_engine.py`, `mvp_scheduler.html`, `mvp_bulk_upload.html`

**Acceptance criteria:**
- Module KPI strip drills on every operations page
- Scheduler scan rows open drill modals with ≥25 records
- Integration connector health traceable to underlying sync records

---

### 2.4 Governance

**Owns:**
- Audit Prep, Evidence Health, Reuse, Lifecycle, Completeness, Comparison, Search, Evidence Approval Analytics
- Evidence review screen and all `/evidence/review/*` POST workflows
- Audit schedule engine and audit prep modals
- Operational workflows (close-gap, assign-owner, upload-missing, mock-audit)
- Missing evidence registry and search module

**Does NOT own:**
- Framework page layout (Frameworks)
- GRC risk register (Enterprise GRC)
- Global `ecs_state` schema (Shared — Governance owns workflow slices)

**Key files today:** `audit_schedule_engine.py`, `evidence_review.py`, `evidence_workflow_engine.py`, `analytics_module.py`, `mvp_audit_prep.html`, `evidence_review.html`

**Acceptance criteria:**
- Evidence lifecycle: Draft → Pending App Owner → Pending Auditor → Closed
- Approved items leave queues; closed items remain in history
- Every governance KPI and table row drills with audit history section

---

### 2.5 Enterprise GRC

**Owns:**
- Risk Register, Exceptions, Exception Governance, CMDB, Regulatory Mapping, Heatmaps, Correlation, Governance Analytics
- GRC drill APIs (`/api/grc-demo/*`)
- GRC KPI macros and governance analytics panel
- Correlation engine and GRC drilldown payloads

**Does NOT own:**
- Executive trends page (Executive Overview — shares analytics_module data)
- Framework catalog (Frameworks)
- Universal drill delegation for GRC metrics (Shared adapter)

**Key files today:** `grc_module_demo.py`, `grc_demo_service.py`, `correlation_engine.py`, `mvp_risk_register.html`, `mvp_governance_analytics.html`, `grc_demo_drill_modal.html`

**Acceptance criteria:**
- All `[data-grc-drill]` KPIs and chart bars open modal with ≥25 rows
- Risk register rows drill to treatment and control mapping records
- Heatmaps trace to application × framework readiness records

---

### 2.6 AI SDLC Governance

**Owns:**
- AI SDLC home, Control Tower, Onboarding, SDLC Gates, Worklist stages
- AI Governance Posture, AI Registry, Governance Quality, Reports, Evidence Viewer
- All `/api/ai-sdlc/*` routes
- AI SDLC workflow store, document artifacts, knowledge repository

**Does NOT own:**
- Global chatbot (Shared)
- Framework readiness on non-AI frameworks (Frameworks)
- Main ECS nav (Shared — AI SDLC has own subnav)

**Key files today:** `routes_ai_sdlc_governance.py`, `ai_sdlc_*` engines, `mvp_ai_sdlc_*.html`, `ai_sdlc_drill_modal.html`

**Acceptance criteria:**
- Control tower tabs and readiness drills functional
- SDLC gate stages expose workflow review API
- `[data-aisdlc-drill]` and `[data-ct-drill]` elements open supporting records

---

### 2.7 Shared Components

**Owns:**
- Global theme, sidebar, nav groups, UX system
- Universal drill engine and module KPI drill
- Pagination, table systems, chart systems
- `ecs_state` registry, `demo_data_standards`, role permissions
- Global filters, audit trail, chatbot
- Cross-module modals (upload, exception raise)

**Governance model:**
- Changes require **RFC from any module owner**
- Shared team approves breaking changes to contracts
- Version shared contracts when drill response shape changes

**Key files today:** `ecs_universal_drill_engine.py`, `enterprise_theme.html`, `ecs_state.py`, `demo_data_standards.py`, `enterprise_context.py`

---

### 2.8 Platform

**Owns:**
- `main.py` bootstrap
- Login/logout
- Route registration orchestration
- `requirements.txt`, `start_ecs.sh`
- CI/CD and validation runner scripts

---

## 3. Collaboration Rules

### 3.1 Allowed dependencies

```
Module → Shared          ✅ Always allowed
Module → Platform        ✅ Via router registration only
Shared → Module          ❌ Never
Module A → Module B      ❌ Never direct; use Shared contracts or events
Platform → All modules   ✅ Router mounting only
```

### 3.2 Shared change process

1. Module owner opens RFC describing needed shared contract change
2. Shared/platform lead reviews impact on all 6 modules
3. If approved, shared team implements with backward-compatible shim
4. Module teams migrate within one sprint
5. Shim removed after all modules migrated

### 3.3 File conflict hotspots (coordinate before editing)

| File | Teams affected | Coordination |
|------|----------------|--------------|
| `routes_mvp.py` | All | Split is top priority; until then, module owners own their route sections |
| `module_capabilities.py` | All MVP modules | Each team owns their `_xxx_view` builder function |
| `enterprise_context.py` | All | Shared team gatekeeps; modules register context providers |
| `ecs_state.py` | All | Shared team gatekeeps; modules own named slices |
| `enterprise_theme.html` | All | Shared team gatekeeps |
| `ecs_nav_groups.html` | All | Shared team gatekeeps nav structure |

---

## 4. Per-Module Test Ownership

| Test file | Owner |
|-----------|-------|
| `test_demo_polish.py` | executive-overview |
| `test_framework_kpi_drilldowns.py` | frameworks |
| `test_framework_specific_kpis.py` | frameworks |
| `test_enterprise_drilldown_validation.py` | frameworks |
| `test_top_risk_application_rendering.py` | enterprise-grc |
| `test_module_kpi_drill.py` | shared |
| `test_ecs_platform_governance.py` | shared |
| `test_ecs_governance_workflow.py` | governance |
| `test_ecs_demo_readiness.py` | shared (CI gate) |
| `test_ai_ops_assistant.py` | operations |
| `test_ai_sdlc_*.py` | ai-sdlc |
| `test_registry_table_rendering.py` | ai-sdlc |

---

## 5. Branch & PR Strategy (Recommended)

| Pattern | Usage |
|---------|-------|
| `module/frameworks/*` | Frameworks team feature branches |
| `module/governance/*` | Governance team feature branches |
| `shared/*` | Shared contract changes — requires 2 module owner approvals |
| `platform/*` | Platform bootstrap changes |

**PR size guideline:** ≤15 files per PR within a single module boundary.

---

## 6. Definition of Done (Per Module)

Before a module is considered "extracted" to `src/modules/{name}/`:

- [ ] All owned routes registered via module router
- [ ] All owned engines colocated under module
- [ ] All owned templates colocated under module `pages/` and `components/`
- [ ] Module test suite passes independently
- [ ] No direct imports from other modules (only shared)
- [ ] Module ownership section in this doc updated
- [ ] Dependency report updated for module

---

## 7. Open Questions for Product Owner

1. Should **ITPP** remain under Frameworks or become its own sub-module?
2. Should **Integrations Hub** move from Operations to Executive Overview (executive strip context)?
3. Should **Trends** page live under Executive Overview or Enterprise GRC (currently uses GRC analytics data)?
4. Is **Evidence Workflow Engine** shared service or Governance-owned with Framework adapters?
5. Target team size: 6 module devs + 2 platform/shared — confirm staffing?

---

**Awaiting approval before any implementation begins.**
