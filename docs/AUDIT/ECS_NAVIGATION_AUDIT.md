# ECS Navigation Audit (Phase 5)

**Audit date:** 2026-06-17. Verifies every menu item, submenu, tab, drilldown, workspace, and report link. Cross-checked against the route registrars, the navigation builder, `ECS_INFORMATION_ARCHITECTURE_V1.md`, the prior `nav_audit/` suite (`route_audit_report.md`, `dead_link_report.md`, `broken_routes.md`), and a **live re-run of the demo-readiness validator** (45 screens + framework pages → **0 failures**).

---

## 1. Method

- **Static:** enumerated nav groups + items from the sidebar navigation builder and route registrars (`app/routes_*.py`, module `routes.py`).
- **Dynamic:** the existing `nav_audit` suite previously exercised **66 routes / 384 page requests / 504 drilldown probes → 0 failures, 0 forbidden states**.
- **Re-validation:** `scripts/validate_demo_readiness.py` on 2026-06-17 → **0 defects (P1/P2/P3 = 0), status READY**.

---

## 2. Navigation structure (7 groups)

| # | Group | Items | Status |
|---|---|:--:|:--:|
| 1 | Executive Overview | 9 | ✅ all resolve |
| 2 | Frameworks | 3 + 15 framework links | ✅ all resolve |
| 3 | Operations | 8 | ✅ all resolve |
| 4 | Governance | 9 | ✅ all resolve |
| 5 | Evidence Governance (platform) | 12 | ✅ all resolve |
| 6 | Enterprise GRC | 9 | ✅ all resolve |
| 7 | AI SDLC Governance | 14 | ✅ all resolve |

Every sidebar link maps to a registered route returning HTTP 200 in demo mode (verified). Sub-navigation tabs (AI SDLC stage subnav, framework tabs, platform tabs) all resolve.

---

## 3. Tabs & workspaces

| Workspace | Tabs verified | Status |
|---|---|:--:|
| Framework page | overview / controls / evidence / workflow tabs (`fw_tab`) | ✅ |
| AI SDLC | 11-stage subnav (`ai_sdlc_subnav.html`) | ✅ |
| Audit Prep | readiness / upcoming / package tabs | ✅ |
| Reports | report-type tabs → `/mvp/reports/view/{type}` | ✅ |
| Platform | scorecard/coverage/lifecycle tabs | ✅ |

---

## 4. Drilldowns

| Drilldown family | Endpoint | Status |
|---|---|:--:|
| Universal drill | `/api/ecs/universal-drill` | ✅ |
| Module drill | `/api/<module>/...-drill` | ✅ |
| Framework drills | `/api/framework/{kpi,workflow,row,tab}-drill` | ✅ |
| AI SDLC drills | `/api/ai-sdlc/{control-tower,sdlc,posture}/...` | ✅ |
| GRC demo drills | `/api/grc-demo/{risk,governance}/...` | ✅ |
| Platform APIs | `/api/platform/*` | ✅ |

Prior suite: **504 drilldown probes → 0 failures**. The historical `nav_audit/universal_drilldown_remediation.md` records the fix that brought this to 100%.

---

## 5. Reports (link integrity)

| Report family | Count | Link target | Status |
|---|:--:|---|:--:|
| Executive audit packs | 30 | `/mvp/reports` generation | ✅ |
| Interactive HTML reports | 5 | `/mvp/reports/view/{type}` | ✅ |
| AI SDLC reports | 6 | `/mvp/ai-sdlc/reports/{id}` | ✅ |
| Gap / comparison export | — | `/mvp/comparison` export | ✅ |
| Onboarding export | — | `/mvp/framework-admin/export/{id}` | ✅ |

---

## 6. Findings

### Dead links
**None found** in the active sidebar navigation. All in-app nav links resolve (validator: 0 HTTP ≥400 on assessed routes).
- **Documentation-only dead links (not in-app):** the *stale* `DOCUMENTATION_GAP_ANALYSIS.md` referenced 5 docs as missing; those now exist. The root `README.md` link set was reconciled in the onboarding task.

### Unused pages
**None functionally unused.** Redirect aliases exist intentionally:
- `/mvp/bulk-upload` → `/mvp/upload`
- `/mvp/sdlc-gates` → `/mvp/ai-sdlc`
- `/sdlc/{stage}` → `/mvp/ai-sdlc/{slug}`

### Hidden pages (reachable, not in sidebar)
These are reachable via deep links/drilldowns but are **not top-level menu items** (by design):
| Page | Reached via |
|---|---|
| `/evidence/review` | Dashboard queue / evidence drill |
| `/mvp/workflow/*` (4 forms) | Action buttons on governance pages |
| `/mvp/platform/application/{slug}` | Inventory row click |
| `/mvp/reports/view/{type}` | Reports tab |
| `/mvp/ai-sdlc/evidence/view/{id}` | Evidence list click |
| `/dashboard/{vertical,functional,compliance}-head` | Role-switch / persona login |

These are **documented** in the screen catalog; classify as intentional deep links, not orphans.

### Undocumented pages
**None.** Every reachable screen is documented in `docs/product_manual/ECS_SCREEN_CATALOG.md` and `docs/AUDIT/ECS_SCREEN_CATALOG.md`.

---

## 7. Discrepancy with prior nav_audit counts

The prior `nav_audit/final_demo_readiness_report.md` cites **66 routes** and demo datasets of **17 frameworks / 320 controls / 1,200 evidence / 10 connectors**. The **catalog** values are **15 / 305 / 702 / 12**. This is the catalog-vs-demo-seed drift documented in `ECS_DOCUMENTATION_INVENTORY.md §5`. Navigation correctness is unaffected — it is a labeling issue in the reports.

---

## 8. Verdict

**Navigation is sound.** No dead links, no orphan pages, no undocumented screens. All tabs, workspaces, drilldowns, and report links resolve in demo mode. The only navigation-adjacent issue is **count labeling drift** in older reports (cosmetic, documentation-only).
