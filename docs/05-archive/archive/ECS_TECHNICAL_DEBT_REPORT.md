# ECS Technical Debt Report (Phase 10)

**Audit date:** 2026-06-17. Identifies **unused modules · dead code · duplicate logic · hardcoded values · incomplete implementations · temporary fixes · demo-only logic**. Findings are observations + recommendations only — **no code was changed** (per audit constraints).

**Severity:** 🔴 High (risk/maintainability) · 🟡 Medium · 🟢 Low/by-design.

---

## 1. Summary

ECS's largest "debt" is **intentional demo scaffolding** and a **legacy RBAC system kept for compatibility** — both known and documented, not accidental. There is **no broken dead code**; the `NotImplementedError` stubs are deliberate interface placeholders. The highest-value cleanup is **retiring the legacy RBAC path** and **standardizing counts/docs**.

| Category | Severity | Items |
|---|:--:|:--:|
| Demo-only logic | 🟡 | ~16 mock/demo engines + demo seeds |
| Duplicate logic | 🟡 | 2 RBAC systems; duplicate docs |
| Incomplete implementations | 🟢 | Connector execution stubs (by design) |
| Hardcoded values | 🟡 | Demo seeds, KPI floors, rate constants |
| Temporary fixes | 🟢 | nav_audit hotfix history (already merged) |
| Unused/dead code | 🟢 | None confirmed broken |

---

## 2. Demo-only logic 🟡

~16 mock/demo engine modules (`*mock*.py`, `*demo*.py`) and `demo_metrics.py` drive the entire UI when `DEMO_MODE=true` (referenced in `app/main.py`, `app/auth/demo.py`, `app/auth/page_guard.py`, `enforcement.py`, `routes_mvp.py`, `ecs_mock_engine.py`).

- **Risk:** demo seeds (e.g. 17 fw / 320 ctrl / 1,200 ev) diverge from the catalog (15/305/702), causing count drift in docs (see `ECS_DOCUMENTATION_INVENTORY.md §5`).
- **By design:** demo mode is a product feature (self-contained demos with no external deps).
- **Recommendation:** keep, but (a) label demo data in-UI with a "demo" badge, (b) align demo seed counts with the catalog narrative, (c) keep demo engines clearly namespaced (already are).

## 3. Duplicate logic 🟡

| Duplicate | Files | Recommendation |
|---|---|---|
| **Two RBAC systems** | canonical `config/rbac.yaml` (`rbac_catalog`) **+** legacy `app/role_permissions.py` **and** `modules/shared/services/role_permissions.py` | Migrate fully to YAML catalog; retire both legacy modules (see `docs/03-development/developer-manual/ECS_RBAC_LEGACY_FLAWS.md`) |
| Two ROI models | `executive/ecs_roi_model.md` + `strategy/ecs_roi_model.md` | Consolidate (pending finance sign-off) |
| Two backlogs | `product/ecs_enterprise_backlog.md` + `product/enterprise_feature_backlog.md` | Pick canonical |
| Duplicate EA review | root `architecture/…` + `docs/02-architecture/architecture/…` | Retire root stray |

## 4. Incomplete implementations 🟢 (by design)

`modules/operations/engines/query_connectors.py` raises `NotImplementedError` in `DatabaseConnector`/`SSHConnector`/`APIConnector` `connect()`/`execute()` ("execution not yet enabled"), and `app/auth/providers.py` has an abstract base raising `NotImplementedError`.

- **Assessment:** these are **deliberate interface stubs** — the query-driven connector framework is wired but live execution is gated off for safety. Not dead code; not a bug.
- **Recommendation:** document them as "interface-complete, execution gated" (done here) and add tests asserting the guard.

## 5. Hardcoded values 🟡

| Value | Where | Note |
|---|---|---|
| Demo dataset seeds (apps, frameworks, controls, evidence) | `demo_metrics.py`, mock engines | Intentional for determinism |
| KPI floors (e.g. compliance ≥ 84.6%) | demo metrics | Cosmetic for demo |
| ROI rate constants | `config/roi.yaml` (`cost_per_hour`) | Note: `1500` in YAML vs ₹1,000/hr in ROI tables — flagged in `executive/documentation_audit.md`, pending finance |
| `BUSINESS_UNITS`, `PAN_INDIA_REGIONS` | demo constants | Static demo geography |

**Recommendation:** centralize demo constants (mostly already in `demo_metrics`); reconcile the ROI rate (finance decision, not code).

## 6. Temporary fixes 🟢

The `nav_audit/` folder documents ~15 hotfixes (scheduler tab, sidebar overflow, drilldown remediation, contrast, Safari sidebar). These are **already applied and validated** (0-defect demo run). The folder is historical QA evidence, not pending debt.

- **Recommendation:** archive `nav_audit/` under `docs/history/` to reduce root clutter (documentation hygiene only).

## 7. Unused / dead code 🟢

- No confirmed broken/unreachable code. All routes resolve (Phase 5).
- Redirect aliases (`/mvp/bulk-upload`, `/mvp/sdlc-gates`, `/sdlc/{stage}`) are intentional, not orphans.
- Empty `package-lock.json` confirms **no Node toolchain** — expected (server-rendered Jinja2). Not debt.

## 8. Prioritized remediation (no functional change required)

| Priority | Action | Type |
|---|---|---|
| 🔴 1 | Retire legacy RBAC (`role_permissions.py` ×2) → canonical YAML | Refactor (future) |
| 🟡 2 | Align demo-seed counts with catalog + add demo badge | UI/data |
| 🟡 3 | Reconcile ROI rate (`roi.yaml` vs tables) | Finance decision |
| 🟡 4 | Consolidate duplicate docs (ROI, backlog, EA review) | Docs |
| 🟢 5 | Add tests around connector execution guards | Test |
| 🟢 6 | Archive `nav_audit/` history | Docs hygiene |

**Conclusion:** ECS carries **low, well-understood technical debt** dominated by intentional demo scaffolding and a documented legacy RBAC path. None of it blocks Phase 1 completeness, demos, or onboarding. The single highest-value future cleanup is unifying RBAC on the YAML catalog.
