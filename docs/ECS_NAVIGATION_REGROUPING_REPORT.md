# ECS Navigation Regrouping Report

**Branch:** `cursor/predefined-queries-module`
**Change type:** Additive UX/navigation consolidation. No routes/pages removed; no auth/RBAC/benchmark/business logic changed.
**Goal:** Make the left sidebar cleaner by limiting **Administration** and **AI SDLC Governance** to a maximum of 4 child items each, moving related sub-pages into parent "aggregator" pages that show the sub-pages as horizontal tabs.

---

## 1. Executive summary

Two sidebar groups were over-populated. They are now consolidated to 4 children each:

- **Administration:** Evidence · Application Management · Control Coverage · Framework Coverage
- **AI SDLC Governance:** Home · Control Tower · Phases · Reports

Three new **aggregator pages** group the moved sub-pages behind horizontal tabs. Each tab embeds the **existing** ECS page (via an iframe with `?embed=1`), so all underlying routes, templates, JavaScript, and behaviour are reused unchanged and every original direct URL still works. A small, global, presentational "embed mode" hides the sidebar inside those tab iframes so each sub-page fills the tab panel cleanly.

No page or route was deleted. Authentication, RBAC, benchmark scripts, and business logic were not modified.

---

## 2. Old vs new sidebar structure

### Administration

| Before (14+ items) | After (4 items) |
|---|---|
| Scheduler, Integration Health, Bulk Upload, Application Onboarding, Application Inventory, Evidence Reuse, Lifecycle, Completeness, App Comparison, Search, Control Coverage, Framework Coverage, AI Assistant, Framework Loader, Framework Administration | **Evidence** · **Application Management** · **Control Coverage** · **Framework Coverage** |

- **Evidence** (`/mvp/admin/evidence`) → tabs: Scheduler, Bulk Upload, Evidence Reuse, Completeness
- **Application Management** (`/mvp/admin/application-management`) → tabs: Application Onboarding, Application Inventory, App Comparison
- **Control Coverage** → existing page `/mvp/platform/control-coverage` (unchanged)
- **Framework Coverage** → existing page `/mvp/platform/framework-coverage` (unchanged)

### AI SDLC Governance

| Before (11 items) | After (4 items) |
|---|---|
| Home, AI SDLC Control Tower, Application Onboarding, Requirements, Design, Development, Testing, Go-Live, Evidence Collection, Findings & Remediation, Reports | **Home** · **Control Tower** · **Phases** · **Reports** |

- **Home** → `/mvp/ai-sdlc` (unchanged)
- **Control Tower** → `/mvp/ai-sdlc/control-tower` (unchanged)
- **Phases** (`/mvp/ai-sdlc/phases`) → tabs: Requirements, Design, Development, Testing, Go-Live (Requirements default)
- **Reports** → `/mvp/ai-sdlc/reports` (unchanged)

### ECS Benchmark
Unchanged (single item "Benchmark Simulation" → `/mvp/ecs-benchmark`).

---

## 3. Accessibility of moved items (nothing lost)

All items removed from the two sidebars remain reachable:

- **In the new aggregator tabs:** Scheduler, Bulk Upload, Evidence Reuse, Completeness, Application Onboarding, Application Inventory, App Comparison, and the 5 AI SDLC stages.
- **By original direct URL:** every route still resolves exactly as before (verified 200 — see §6).
- **AI SDLC Onboarding / Evidence Collection / Findings & Remediation:** remain reachable by their original URLs (`/mvp/ai-sdlc/onboarding`, `/mvp/ai-sdlc/evidence`, `/mvp/ai-sdlc/findings`) and from the AI SDLC **Home** page cards. They were kept out of the 4 visible sidebar children to honour the "max 4" requirement (Evidence Collection & Findings are grouped conceptually under Reports for active-state highlighting).
- **Administration extras** previously in the sidebar (Integration Health, Lifecycle, Search, AI Assistant, Framework Loader, Framework Administration) remain fully reachable by URL; they were removed from the Administration sidebar only to meet the strict 4-item limit. (If any of these should be surfaced again, add them as tabs on an existing aggregator or as a separate group — no route changes needed.)

---

## 4. Routes

### Added (aggregators — render-only, no business logic)
| Route | Purpose |
|---|---|
| `GET /mvp/admin/evidence` | Administration → Evidence (tabs) |
| `GET /mvp/admin/application-management` | Administration → Application Management (tabs) |
| `GET /mvp/ai-sdlc/phases` | AI SDLC Governance → Phases (tabs, Requirements default) |

### Preserved (unchanged, still reachable by direct URL)
`/mvp/scheduler`, `/mvp/upload`, `/mvp/reuse`, `/mvp/completeness`, `/mvp/onboarding`, `/mvp/platform/inventory`, `/mvp/comparison`, `/mvp/platform/control-coverage`, `/mvp/platform/framework-coverage`, `/mvp/ai-sdlc`, `/mvp/ai-sdlc/control-tower`, `/mvp/ai-sdlc/requirements`, `/mvp/ai-sdlc/design`, `/mvp/ai-sdlc/development`, `/mvp/ai-sdlc/testing`, `/mvp/ai-sdlc/golive`, `/mvp/ai-sdlc/evidence`, `/mvp/ai-sdlc/findings`, `/mvp/ai-sdlc/reports`, `/mvp/ecs-benchmark`, plus all `/mvp/*` Administration extras. No routes were renamed or removed.

---

## 5. Files changed

### Added
| File | Purpose |
|---|---|
| `app/routes_nav_aggregators.py` | Registers the 3 aggregator routes (render-only; reuses existing pages). |
| `modules/shared/templates/mvp_tab_aggregator.html` | Reusable horizontal-tab shell; each tab lazy-loads an existing page in an iframe (`?embed=1`); active tab highlighted; direct links listed; preserves `role`/`user`. |

### Modified
| File | Change |
|---|---|
| `app/main.py` | Two lines: import + `register_nav_aggregator_routes(app, templates)` after the other route registrations. |
| `modules/shared/templates/partials/ecs_nav_groups.html` | Administration group reduced to 4 children (Evidence, Application Management, Control Coverage, Framework Coverage); `admin_open` state extended to keep the group open on aggregator/sub-page routes. |
| `modules/shared/templates/partials/ecs_nav_ai_sdlc.html` | AI SDLC group reduced to 4 children (Home, Control Tower, Phases, Reports); active-state helpers for Phases/Reports. |
| `modules/shared/templates/partials/enterprise_theme.html` | Added global, presentational **embed mode**: `body.ecs-embed` CSS (hides sidebar, expands main) + a tiny script that adds `ecs-embed` when `?embed=1` is in the URL. No behavioural/route change. |

No changes to `scripts/`, `benchmarks/`, `docs/benchmarks/`, `app/auth/`, RBAC, or AI SDLC engines.

---

## 6. Validation

```bash
python -m compileall app modules scripts      # -> exit 0 (clean)
./start_ecs.sh                                 # or uvicorn app.main:app --reload
```

Live server run with `ECS_LOCAL_AUTH_BYPASS=true` (so demo pages load); every URL returned **200**:

**Required aggregator + phase URLs:**
`/mvp/admin/evidence` · `/mvp/admin/application-management` · `/mvp/ai-sdlc/phases` · `/mvp/ai-sdlc/requirements` · `/mvp/ai-sdlc/design` · `/mvp/ai-sdlc/development` · `/mvp/ai-sdlc/testing` · `/mvp/ai-sdlc/golive` — **all 200**.

**Regression:** `/dashboard`, `/dashboard/cio`, `/mvp/ai-sdlc`, `/mvp/ai-sdlc/control-tower`, `/mvp/ai-sdlc/reports`, `/mvp/ai-sdlc/evidence`, `/mvp/ai-sdlc/findings`, `/mvp/ecs-benchmark`, `/mvp/scheduler`, `/mvp/upload`, `/mvp/reuse`, `/mvp/completeness`, `/mvp/onboarding`, `/mvp/platform/inventory`, `/mvp/comparison`, `/mvp/platform/control-coverage`, `/mvp/platform/framework-coverage` — **all 200**.

**Structure checks (HTML):**
- Evidence aggregator tabs = Scheduler, Bulk Upload, Evidence Reuse, Completeness (iframe `src` carries `&embed=1`).
- Application Management aggregator tabs = Application Onboarding, Application Inventory, App Comparison.
- Phases aggregator tabs = Requirements, Design, Development, Testing, Go-Live.
- Administration sidebar renders exactly 4 children; AI SDLC sidebar renders exactly 4 children (screenshots captured).
- Embed mode active on sub-pages loaded with `?embed=1` (`ecs-embed` present).
- ECS Benchmark nav unchanged.

**Auth safety (regression, no bypass — `ECS_AUTH_ENABLED=true`, bypass flags off):**
`/healthz` → 200; `/dashboard` → **401**; `/mvp/admin/evidence` → **401**; `/mvp/ai-sdlc/phases` → **401**. The new routes go through the same middleware; authentication is unchanged.

> Validation used a throwaway `/tmp` virtualenv with the app's already-declared demo deps; no new repo dependency was added and the system Python was not modified.

---

## 7. Known limitations

- **Tab content is embedded via iframe.** This maximises reuse and safety (zero changes to the sub-pages), but the sub-page loads in an iframe with its own scroll region; deep-linking to a specific tab is by clicking (the aggregator loads Requirements/first tab by default). Direct URLs to each sub-page remain the canonical way to bookmark a specific view.
- **Embed mode is presentational.** It hides the sidebar for embedded sub-pages via CSS/JS keyed on `?embed=1`; it does not alter routing, data, or auth.
- **AI SDLC Onboarding / Evidence Collection / Findings** are reachable by URL and Home-page cards but are not top-level sidebar children (to honour the max-4 rule). They can be added as tabs on the Phases/Reports aggregator later if desired.
- **Administration extras** (Integration Health, Lifecycle, Search, AI Assistant, Framework Loader, Framework Administration) are URL-reachable but no longer in the Administration sidebar, for the same max-4 reason.
