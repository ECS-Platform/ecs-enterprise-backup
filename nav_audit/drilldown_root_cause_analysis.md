# Drilldown Root Cause Analysis

## Executive Summary

Users repeatedly saw **"Unable to load records. Please try again."** when clicking drilldowns
(Main Dashboard KPI cards, Enterprise National Score / Compliance, Reports, Trends), while
fresh-browser validation kept passing. The discrepancy itself was the clue.

Two compounding root causes were found through **real browser execution** (Playwright + network +
console capture), not static review:

1. **HTTP 422 on `count` parameter (the actual error trigger).** KPI cards bind their `count`
   attribute to the *displayed* value (e.g. `94.5%`, `12 days`). The drill endpoints declared the
   query param as `int`, so FastAPI rejected those requests with **HTTP 422 before the route body
   ran** — the route's own try/except fallback never got a chance. The frontend `.catch` then
   showed "Unable to load records." Captured live:
   `GET /api/ecs/workflow-drill?metric=auditor_sla&count=94.5%25&role=cio → 422`.

2. **Stale browser cache (why the fix "didn't take" and why it varied by browser/session).**
   `drilldown_engine.js` was served at an **unversioned URL with no `Cache-Control` header**.
   Browsers cached the old, buggy script indefinitely. So users kept running pre-fix code and kept
   hitting the 422, even after server-side fixes — exactly the "previous validation PASS but user
   still fails" symptom.

## Root Cause

| # | Layer | Defect | Class |
|---|---|---|---|
| 1 | API route | `count: int` query param 422s on formatted values, before fallback runs | D. Schema mismatch |
| 2 | Asset delivery | Unversioned, uncached JS → browsers run stale buggy engine | Caching / delivery |
| (2b) | Frontend | `count` attr carried formatted display value; `window.__ecsRole` never set | E/F. Frontend |

## Failure Trace Table (live capture)

| Module | Drill | JS Function | Endpoint | Status (before) | Error (before) |
|---|---|---|---|---|---|
| Main Dashboard | Closure Rate / Avg Review Time / Auditor SLA | `ecsOpenEnterpriseWorkflowDrill` → `fetchJson` | `/api/ecs/workflow-drill` | **422** | `int_parsing` on `count=94.5%` → "Unable to load" |
| Enterprise | National Score / Compliance / KPIs | `ecsOpenUniversalKpiDrill` / `ecsOpenModuleKpiDrill` | `/api/ecs/universal-drill`, `/api/module-kpi/drill` | **422** when count formatted | same |
| Reports | Coverage / Observations / charts | `ecsOpenUniversalChartDrill` / `ecsOpenUniversalKpiDrill` | `/api/ecs/universal-drill` | **422** when count formatted | same |
| Trends | KPI / chart drills | `ecsOpenUniversalKpiDrill` / `ecsOpenUniversalChartDrill` | `/api/ecs/universal-drill` | **422** when count formatted | same |

After fix, every one of the above returns **200 with rendered rows** (see After).

## Files Changed

| File | Change |
|---|---|
| `modules/shared/routes/routes_mvp.py` | `count` query param `int → str` on `/api/module-kpi/drill`, `/api/ecs/universal-drill`, `/api/ecs/workflow-drill`; added `_safe_count()` to parse leading digits. Eliminates 422 at the parsing layer. |
| `app/main.py` | Added `asset_ver()` Jinja global (file-mtime cache-busting token). |
| `modules/shared/templates/shared/drilldown_modal.html` | Script tag now `drilldown_engine.js?v={{ asset_ver(...) }}`; sets `window.__ecsRole` from page role. |
| `modules/shared/static/js/drilldown_engine.js` | `safeCount()` sanitizes count before request; distinct empty vs error states; render guarded with try/catch; 12s timeout failsafe. |
| `modules/shared/templates/partials/ecs_module_kpi_drill.html` | Same failsafe + count sanitize. |
| `modules/frameworks/templates/partials/ecs_framework_kpi_drill.html` | Same failsafe pattern. |

## Before

```
GET /api/ecs/workflow-drill?metric=auditor_sla&count=94.5%25&role=cio
→ HTTP 422 {"detail":[{"type":"int_parsing","loc":["query","count"]...}]}
Modal: "Unable to load records. Please try again."
window.__ecsRole = undefined  (all drills ran as cio)
Script served: /static/ecs/js/drilldown_engine.js   (no version, no Cache-Control → cached stale)
```

## After

```
GET /api/ecs/workflow-drill?metric=auditor_sla&count=143&role=owner → HTTP 200, 25 rows
Modal renders 143 visible table rows. No console errors.
window.__ecsRole = "owner"
Script served: /static/ecs/js/drilldown_engine.js?v=1781545178  (changes on every edit)
```

## Validation Matrix (real browser, visible rendered rows)

5 required roles × executive modules, clicked in a real browser, counting rows inside the modal:

| Role | Drills clicked | Rendered (rows>0) | Error / Loading | Empty |
|---|---|---|---|---|
| owner | 13 | 13 (106–147 rows) | 0 | 0 |
| auditor | 13 | 13 (49–147 rows) | 0 | 0 |
| cio | 8 present | 8 (49–147 rows) | 0 | 0 |
| security_officer | 8 present | 8 | 0 | 0 |
| operations_owner | 8 present | 8 | 0 | 0 |

**Total: 65 checks — RENDERED 50 — EMPTY 0 — FAIL 0 — ABSENT 15.**
ABSENT = Main-Dashboard workflow KPI cards not present on cio/security/ops dashboard variants
(expected layout, not a defect; those cards render and pass for owner & auditor).

## Remaining Risks

- Other unversioned static JS/CSS could still be cached stale on a deploy. Only the drilldown
  engine was cache-busted here; a global asset-versioning pass is recommended as follow-up.
- `_safe_count` + `safeCount` are belt-and-suspenders; any new drill endpoint should accept
  `count: str` (not `int`) to stay 422-proof.
- Headless `.click()` on SVG/canvas chart segments is unreliable; validated via real DOM
  `MouseEvent` dispatch, which matches genuine user clicks.

## FINAL STATUS = PASS

- Personas tested: 5 (owner, auditor, cio, security_officer, operations_owner)
- Modules tested: 4 (Main Dashboard, Enterprise, Reports, Trends)
- Drills tested: 65
- Passed (visible rendered records): 50
- Failed: 0
- Not applicable (card absent for persona): 15
