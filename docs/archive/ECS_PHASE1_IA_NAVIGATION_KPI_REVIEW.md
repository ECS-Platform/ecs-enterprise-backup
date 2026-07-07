# ECS Phase 1 — Information Architecture, Navigation & KPI Rationalization Review

**Status:** REVIEW / PROPOSAL ONLY — **not implemented.** Awaiting approval before any UI/template/route change.
**Mode:** Documentation only. No backend service, API, repository, service-class, DB-entity, or route deletions proposed. No code generated.
**Grounding (verified by source inspection):**
- Navigation: `modules/shared/templates/partials/ecs_nav_groups.html`, `ecs_nav_ai_sdlc.html`, `ecs_sidebar.html`, `mvp_sidebar.html`; module groups/labels in `modules/shared/services/ecs_nav_framework.py`.
- Routes: `/mvp/*`, `/framework/<name>`, `/dashboard*` (FastAPI routes in `modules/shared/routes/routes_mvp.py` + dashboard routers).
- KPIs: [KPI Validation Report](../testing/ECS_KPI_VALIDATION_REPORT.md), [Master KPI Dictionary](../product/ECS_MASTER_KPI_DICTIONARY.md).

---

> ## ⚠ Critical accuracy note: ECS is **not** a React app
> The brief specifies "React/UI Layer Restructuring" and a "React Route Refactoring Plan." **ECS has no React/JSX/TSX and no `package.json`** (verified: 0 `.jsx`/`.tsx` files, no `package.json`). The frontend is **server-rendered FastAPI + Jinja2 templates with Bootstrap + vanilla JavaScript**. Routes are **Python FastAPI routes**, navigation is a **Jinja2 partial** (`ecs_nav_groups.html`) driven by a `frameworks` list + `nav_counters` context, and "components" are **Jinja2 partials/templates**, not React components.
>
> **All deliverables below are therefore reframed to the actual stack** (Jinja2 partials, route grouping, template includes). The *intent* of every requested deliverable is fully preserved; only the technology framing is corrected. Where the brief says "React component," read "Jinja2 template/partial." This reframing is the single most important finding for planning effort and risk.

---

## 1. Information Architecture Review

### 1.1 Current state (verified)
The left navigation (`ecs_nav_groups.html` + included `ecs_nav_ai_sdlc.html`) currently renders **7 collapsible groups** containing **~70 leaf links**, plus a dynamic **Frameworks** list of ~10–15 framework entries:

| # | Group (current) | Leaf items (verified) | Count |
|---|---|---|---|
| 1 | **Executive Overview** | ROI & Value Realization, Main/Role Dashboard, Demo Overview, Enterprise, Pan India, Reports, Trends | 7 |
| 2 | **Frameworks** | one link per framework (PCI DSS, DPSC, OS/DB/Nginx Baseline, AppSec, VAPT, C-SITE, ITPP, ITDRM, …) + Framework Loader + Framework Administration + Add New Framework | ~12–15 |
| 3 | **Operations** | Scheduler, Predefined Queries, Integration Health, Evidence Explorer, AI Ops Assistant, Bulk Upload, Integrations, Onboarding | 8 |
| 4 | **Governance** | Audit Prep, Evidence Health, Evidence Reuse, Lifecycle, Completeness, App Comparison, Search, Evidence Approval Analytics | 8 |
| 5 | **Evidence Governance** | Role Scorecard, Executive Summary, Audit Readiness, Application Onboarding, Application Inventory, Control Coverage, Framework Coverage, Evidence Reuse, Evidence Lifecycle, Collection Scheduler, AI Assistant, AI Assistant (Chat) | 12 |
| 6 | **Enterprise GRC** | Risk Register, Exceptions/TD, Exception Governance, CMDB/Assets, Regulatory Mapping, Executive Heatmaps, Integrations Hub, Cross-Tool Correlation, Governance Analytics | 9 |
| 7 | **AI SDLC Governance** | Control Tower, Onboarding, Requirements, Design, Development, Testing, Go-Live, Evidence, Findings, Reports, AI Governance, SDLC Gates, Model/Prompt Registry, Governance Quality | ~14 |

**Total: ~70 leaf links across 7 groups** (+ framework list). This is the root cause of the "excessive complexity" perception.

### 1.2 Key IA problems (evidence-based)
1. **Duplicate concepts across groups** (verified):
   - *Evidence Reuse* appears **twice** — Governance (`/mvp/reuse`) and Evidence Governance (`/mvp/platform/evidence-reuse`).
   - *Lifecycle* appears **twice** — Governance (`/mvp/lifecycle`) and Evidence Governance (`/mvp/platform/evidence-lifecycle`).
   - *Scheduler* appears **twice** — Operations (`/mvp/scheduler`) and Evidence Governance "Collection Scheduler" (`/mvp/platform/scheduler`).
   - *Audit Readiness* (Evidence Governance) overlaps *Audit Prep* (Governance).
   - *AI Assistant* appears **three times** — Operations "AI Ops Assistant", Evidence Governance "AI Assistant", "AI Assistant (Chat)".
   - *Application Onboarding* appears **twice** — Operations "Onboarding" and Evidence Governance "Application Onboarding".
   - *Executive Summary / Framework Coverage / Control Coverage* (Evidence Governance) overlap Executive + Governance analytics.
2. **Frameworks consume left-nav space** as a navigation tree (one link per framework) — they are *context*, not destinations.
3. **Analytics screens are top-level destinations** (Completeness, Lifecycle, Reuse, Search, Coverage, Inventory) rather than tabs within a parent.
4. **AI SDLC Governance** is a large parallel module (~14 items) that is **out of scope for the Phase-1 demo story** and inflates perceived complexity.
5. **Two sidebars exist** (`ecs_sidebar.html`, `mvp_sidebar.html`) — a maintenance/duplication smell to consolidate.

### 1.3 Target IA (per brief) — 4 groups, ~9 leaf items
Dashboard · Operations (Predefined Queries, Evidence Explorer, Integrations) · Governance (Findings, Audit Readiness) · Insights (Evidence Intelligence). Everything else becomes **in-page tabs**, **context filters**, or **hidden (retained, not deleted)**.

---

## 2. Current vs Proposed Navigation Tree

### 2.1 Current (verified, abbreviated)
```
Executive Overview ▾  (7)        Frameworks ▾  (~12)        Operations ▾  (8)
  ROI & Value                      PCI DSS                     Scheduler
  Main/Role Dashboard              DPSC                        Predefined Queries
  Demo Overview                    OS/DB/Nginx Baseline        Integration Health
  Enterprise                       AppSec / VAPT               Evidence Explorer
  Pan India                        C-SITE / ITPP / ITDRM       AI Ops Assistant
  Reports                          Framework Loader            Bulk Upload
  Trends                           Framework Admin / +Add      Integrations / Onboarding
Governance ▾ (8)                 Evidence Governance ▾ (12)  Enterprise GRC ▾ (9)
  Audit Prep                       Role Scorecard              Risk Register
  Evidence Health                  Executive Summary           Exceptions / TD
  Evidence Reuse  ⟸ dup            Audit Readiness  ⟸ overlap  Exception Governance
  Lifecycle       ⟸ dup            Application Onboarding ⟸dup  CMDB / Assets
  Completeness                     Application Inventory       Regulatory Mapping
  App Comparison                   Control / Framework Cov.    Executive Heatmaps
  Search                           Evidence Reuse  ⟸ dup       Integrations Hub
  Evidence Approval Analytics      Evidence Lifecycle ⟸ dup    Cross-Tool Correlation
                                   Collection Scheduler ⟸ dup  Governance Analytics
                                   AI Assistant ×2 ⟸ dup
AI SDLC Governance ▾ (~14)  [out of Phase-1 demo scope]
```

### 2.2 Proposed (4 groups, ~9 leaf links)
```
Dashboard                         (single landing; 5 tabs)
Operations ▾
  Predefined Queries              (4 tabs)
  Evidence Explorer               (5 tabs)
  Integrations                    (4 tabs)
Governance ▾
  Findings                        (4 tabs)
  Audit Readiness                 (4 tabs)
Insights ▾
  Evidence Intelligence           (5 tabs)
```
**Result: 7 groups → 4 groups; ~70 leaf links → ~9.** Framework links → in-page context filter. AI SDLC, GRC sub-screens, Executive sub-screens → **hidden but retained** (routes intact) or folded into tabs (see §6, §9).

---

## 3. Menu Reduction Report

| Metric | Current | Proposed | Reduction |
|---|---|---:|---:|
| Top-level groups | 7 | 4 | **43%** |
| Leaf nav links (excl. frameworks) | ~70 | ~9 | **~87%** |
| Framework nav links | ~10–15 | 0 (→ context filter) | **100%** |
| Duplicate nav concepts | ≥7 | 0 | **100%** |
| Sidebars (templates) | 2 | 1 | **50%** |

**Disposition of every current group:**
| Current group | Disposition |
|---|---|
| Executive Overview | Fold into **Dashboard** (Overview tab) + **Insights**; ROI/Enterprise/Pan India/Reports/Trends → Audit Readiness/Insights tabs or hidden-retained |
| Frameworks | **Eliminate as nav** → in-page framework filter (§5) |
| Operations | **Keep** (trim to Predefined Queries, Evidence Explorer, Integrations; Scheduler/Bulk Upload/Health → Integrations tabs; AI Ops Assistant → Insights or hidden) |
| Governance | Fold into **Governance → Findings + Audit Readiness**; analytics → Insights tabs |
| Evidence Governance | **Merge** into Dashboard/Insights/Audit Readiness tabs (eliminates the biggest duplicate cluster) |
| Enterprise GRC | **Hidden-retained** for Phase 1 (Findings covers observations/exceptions); routes intact |
| AI SDLC Governance | **Hidden-retained** for Phase 1 (out of demo story); routes intact |

---

## 4. KPI Reduction Report

### 4.1 Principle
Every KPI must answer *"what decision does this enable?"* Target: **≤4 primary KPI cards + ≤1 secondary row** per page; **≥70% reduction** in visible KPI density. (Current dashboards present large KPI walls — see [KPI Validation Report](../testing/ECS_KPI_VALIDATION_REPORT.md) for the full inventory.)

### 4.2 Proposed per-page KPI sets (decision-mapped)
| Page | Primary KPI cards (≤4) | Decision enabled |
|---|---|---|
| **Dashboard** | Open Findings · Evidence Pending Review · Audit Readiness % · Evidence Reuse % | Where to act today; am I audit-ready? |
| **Predefined Queries** | Total Queries · Ready Queries · Evidence Generated · Unsupported Technologies | What can I run; what produced evidence; what's blocked |
| **Evidence Explorer** | Pending · Submitted · Approved · Rejected | Review queue triage |
| **Audit Readiness** | Readiness % · Open Findings · Critical Gaps · Reusable Evidence % | Go/no-go for audit; biggest gaps |
| **Findings** | Open · In Progress · Submitted · Closed | Workflow throughput / bottlenecks |

**Secondary row:** ≤1 row of supporting metrics per page (e.g., trend sparkline or last-refresh), not a wall.

### 4.3 KPI disposition rule
- **Retain** the 5×4 decision KPIs above.
- **Demote to secondary row / tab detail:** breakdowns, distributions, per-framework rollups.
- **Hide (retained in backend/API):** vanity counts that enable no action (no KPI calculation is deleted — only its prominence changes; see Backend Impact §11).

> **No KPI calculation logic is removed.** This is a *display rationalization*: cards are reduced in the template; the underlying KPI services/endpoints remain callable.

---

## 5. Framework Navigation Elimination Plan

**Current:** `ecs_nav_groups.html` lines 42–61 render a **Frameworks** group looping `{% for framework in frameworks %}` → `/framework/<name>` (one nav link each) + Framework Loader/Admin.

**Proposed (frameworks become context, not navigation):**
1. **Remove the Frameworks nav group** from the sidebar partial (template-only change; keep `/framework/<name>` routes intact).
2. Replace with an **in-page framework selector** on relevant pages (Dashboard, Predefined Queries, Audit Readiness, Insights): a **dropdown / horizontal tab strip / context filter** bound to the existing `frameworks` context list and `?framework=` query param the routes already accept.
3. **Framework Loader / Administration / Add New Framework** → move under an **admin-only** entry (hidden from the four primary groups; retained, RBAC-gated as today via `perm_can_manage_frameworks`).
4. Framework KPIs/coverage surface inside **Audit Readiness → Frameworks tab** and **Insights → Coverage tab** rather than as standalone destinations.

**Net effect:** frameworks consume **zero** left-nav space; selecting a framework re-scopes the current page (a filter), matching the brief's "frameworks are context filters."

---

## 6. Page-to-Tab Consolidation Plan

Convert standalone analytics destinations into **contextual tabs** (Bootstrap nav-tabs in the page template; each tab loads the existing route's content/partial).

| Page | Tabs (proposed) | Sourced from current screens |
|---|---|---|
| **Dashboard** | Overview · Controls · Evidence · Findings · Remediation | role dashboards, control coverage, evidence health, findings |
| **Operations → Predefined Queries** | Query Catalog · Query Execution · Evidence Generated · Evidence Reuse | `/mvp/predefined-queries` (+ reuse) |
| **Operations → Evidence Explorer** | All Evidence · Pending Review · Submitted · Approved · Rejected | `/mvp/evidence-explorer` (status filters) |
| **Operations → Integrations** | Connected Systems · Scheduler · Health · Bulk Upload | `/mvp/integrations`, `/mvp/scheduler`, `/mvp/integration-health`, `/mvp/upload` |
| **Governance → Findings** | Open · In Progress · Submitted · Closed | observations/exceptions status views |
| **Governance → Audit Readiness** | Enterprise · Frameworks · Applications · Trends | `/mvp/platform/audit-readiness`, `/mvp/audit-prep`, enterprise, trends |
| **Insights → Evidence Intelligence** | Reuse · Coverage · Completeness · Lifecycle · Search | `/mvp/reuse`, control/framework coverage, `/mvp/completeness`, `/mvp/lifecycle`, `/mvp/search` |

**Consolidation also collapses duplicates:** the two Evidence-Reuse, two Lifecycle, two Scheduler, and two Onboarding entries each merge into a **single tab**.

---

## 7. Route Organization Plan (was "React Route Refactoring")

> Reframed for FastAPI + Jinja2. **No routes are deleted or moved server-side** in Phase 1; this is a *presentation grouping* over existing routes.

1. **Keep all existing routes** (`/mvp/*`, `/framework/<name>`, `/dashboard*`) live and unchanged — they remain the data/content endpoints that tabs load.
2. Introduce a **nav-config map** (single source) that declares the 4 groups → leaf pages → tabs, and which existing route each tab renders. This can be a Python dict consumed by the nav partial (a new presentation helper, not a service change) **or** static structure in the template.
3. **Tab content strategy (lowest-risk):** each tab links to / lazy-loads the existing route (server-rendered partial via `hx-get`/fetch or a full-page route with `?tab=`), so no business logic moves.
4. **Deep links preserved:** hidden/retained pages keep working by URL (bookmarks, docs, tests) even when not in the primary nav.
5. **Redirect aliases (optional, additive):** add friendly group URLs (e.g., `/operations`, `/governance`, `/insights`) that render the new landing pages; old URLs continue to function.

**Effort (Jinja2/template, indicative [Inferred/Target]):** nav partial rebuild ~2–3d; 7 tabbed page shells ~5–8d; framework filter component ~2d; KPI card trim across 5 pages ~3–4d; consolidate two sidebars ~1–2d. **Total ~13–19 front-end/template eng-days.** (No React rewrite — far smaller than a SPA refactor.)

---

## 8. Components to Merge (Jinja2 partials/templates)

| Merge target | Sources to merge |
|---|---|
| Single sidebar partial | `ecs_sidebar.html` + `mvp_sidebar.html` → one canonical nav partial |
| Evidence Reuse (one tab) | `/mvp/reuse` + `/mvp/platform/evidence-reuse` |
| Lifecycle (one tab) | `/mvp/lifecycle` + `/mvp/platform/evidence-lifecycle` |
| Scheduler (one tab) | `/mvp/scheduler` + `/mvp/platform/scheduler` (Collection Scheduler) |
| Onboarding (one tab) | `/mvp/onboarding` + `/mvp/platform/onboarding` |
| Audit Readiness (one page) | `/mvp/platform/audit-readiness` + `/mvp/audit-prep` |
| AI Assistant (one entry) | `/mvp/ai-assistant` + `/mvp/platform/assistant` + `/mvp/ai-ops-assistant` (surface one; retain others) |
| Coverage (Insights tab) | `/mvp/platform/control-coverage` + `/mvp/platform/framework-coverage` |

## 9. Components to Hide (retained — routes/services intact, removed from primary nav)

- **AI SDLC Governance** group (all ~14 screens) — out of Phase-1 demo scope.
- **Enterprise GRC** sub-screens not in the demo story: CMDB/Assets, Regulatory Mapping, Executive Heatmaps, Integrations Hub, Cross-Tool Correlation, Governance Analytics. (Risk Register / Exceptions surface via **Findings**.)
- **Executive Overview** extras: ROI & Value Realization, Pan India, App Comparison, Reports, Trends (Trends resurfaces as a tab under Audit Readiness).
- **Evidence Governance** duplicates: Role Scorecard, Executive Summary, Application Inventory (Inventory may surface as an Insights/Operations sub-view).
- **Demo Overview** — see §10.

> "Hide" = remove from the four primary nav groups only. **Routes, services, repositories, APIs, and DB entities remain fully intact and reachable by URL / admin menu.**

## 10. Components to Retain (Phase-1 core — the demo story spine)

Mapped to the required flow **Predefined Query → Execution → Evidence Collection → Reuse → Observation → Owner Review → Auditor Review → Closure → Audit Readiness**:

| Demo step | Retained screen(s) | New location |
|---|---|---|
| Predefined Query + Execution | `/mvp/predefined-queries` | Operations → Predefined Queries (Catalog/Execution tabs) |
| Evidence Collection | query → evidence; `/mvp/evidence-explorer` | Predefined Queries → Evidence Generated; Operations → Evidence Explorer |
| Evidence Reuse | `/mvp/reuse` | Predefined Queries → Evidence Reuse; Insights → Reuse |
| Observation Creation | observations/findings | Governance → Findings (Open) |
| Application Owner Review | evidence review (owner) | Evidence Explorer (Pending/Submitted) |
| Auditor Review | evidence approval / audit | Evidence Explorer (Approved/Rejected); Governance → Findings |
| Closure | observation closure | Governance → Findings (Closed) |
| Audit Readiness Improvement | `/mvp/platform/audit-readiness` | Governance → Audit Readiness |
| Cross-cutting | Dashboard, Integrations, Scheduler, Bulk Upload | Dashboard; Operations → Integrations tabs |

**Demo Overview recommendation:** the current `/mvp/demo-overview` duplicates dashboard KPIs. **Recommendation: Option 2 — replace with a lightweight landing page** (or simply make **Dashboard → Overview** the landing). Do **not** keep a second KPI-heavy dashboard. Retain the route but point it at the new Dashboard (or a thin “start the demo here” page) to avoid duplicate dashboards/KPI displays.

---

## 11. Backend Impact Assessment (for future review — no changes proposed now)

| Area | Phase-1 impact | Notes |
|---|---|---|
| **Routes** (`/mvp/*`, `/framework/<name>`, `/dashboard*`) | **None** (retained) | Tabs render existing routes; hidden pages still reachable by URL |
| **Services / repositories / APIs / DB entities** | **None** (retained) | Strictly UI/template/IA changes |
| **KPI services** | **None** | Cards reduced in templates; calculations untouched and still callable |
| **Nav context** (`frameworks`, `nav_counters`, `nav_module`) | Light, presentation-only | New nav-config map consumes the same context; counters can shrink to the surfaced set |
| **Templates/partials** | **Primary work** | Rebuild nav partial, add tab shells + framework filter, trim KPI cards, merge two sidebars |
| **RBAC/page guards** | Reuse as-is | `perm_can_manage_frameworks`, role gates continue to apply to hidden/admin entries |
| **Tests / deep links / docs** | Verify | Keep URLs valid; update nav-related template tests + `nav_audit` artifacts |

**Future (post-Phase-1) backend items to consider — documented, not actioned:**
- Consolidate duplicate route pairs (reuse/lifecycle/scheduler/onboarding) into single canonical routes once UI no longer needs both (currently both retained).
- Optionally add `?tab=` / group landing routes as thin presentation routes.
- Reduce `nav_counter_engine` work to only surfaced counters (perf, optional).

---

## Recommendation & next step
Adopt the 4-group IA, framework-as-filter, page-to-tab consolidation, and the 5×4 decision-mapped KPI set. The work is **template/IA only (~13–19 eng-days)** on the **Jinja2** stack — **not** a React rewrite. **No backend deletions.** 

**This document is review-only. Please approve (or adjust) the proposed IA, tab structure, and KPI set before I make any template/route changes.** Open decisions for your sign-off:
1. Confirm **Demo Overview → lightweight landing** (Option 2) vs full removal.
2. Confirm **AI SDLC Governance** and **Enterprise GRC** are *hidden-retained* for Phase 1 (not in primary nav).
3. Confirm whether hidden screens should be reachable via an **“Advanced/Admin” menu** or **URL-only**.

## Cross-references
- [Screen Validation Report](../testing/ECS_SCREEN_VALIDATION_REPORT.md) · [Navigation Audit](ECS_NAVIGATION_AUDIT.md) · [KPI Validation Report](../testing/ECS_KPI_VALIDATION_REPORT.md) · [Master Product Manual](../product/ECS_MASTER_PRODUCT_MANUAL.md) · [Master Use Case Registry](../product/ECS_MASTER_USE_CASE_REGISTRY.md)
