# ECS Demo Trustability Report

**Scope:** Predefined Queries, KPI drilldowns, execution status, framework coverage, unsupported technology, evidence rejection visibility.
**Lens:** fake data · placeholder records · synthetic rows · mock drilldowns · contradictory counts · misleading statuses · broken traceability chains.

## Issues found & dispositions

| # | Issue | Location | Impact | Severity | Recommendation | Status | Demo Risk (after) |
|---|---|---|---|---|---|---|---|
| 1 | "Ready" shown for non-executable controls (16 vs. 6 real) | Predefined Queries catalog/detail status badge | Misleading capability; running them fails | **High** | Make "Ready" require executable capability | ✅ FIXED (`assess_execution_capability`) | Low |
| 2 | Run button enabled for OS-001 (Unknown tech) | Catalog/detail Run action | Click → guaranteed failure; contradicts its own status | **High** | Gate Run on real capability | ✅ FIXED (`is_live_execution_enabled` tightened) | Low |
| 3 | KPI drilldowns returned unrelated/synthetic rows; 0-count KPIs showed ~25 fake rows | `/api/module-kpi/drill?module=predefined_queries` | Fabricated data in a governance demo | **High** | Authoritative per-KPI drill + bypass padding/fallback | ✅ FIXED (prior pass, re-verified) | Low |
| 4 | Unsupported Technology drilldown lacked a reason | Unsupported Tech KPI drilldown | Not explainable | **Medium** | Add reason + query excerpt columns | ✅ FIXED | Low |
| 5 | Evidence Rejections missing timestamp & workflow state | Dashboard → Evidence → Rejections | Incomplete rejection traceability | **Medium** | Add available fields (no fabrication) | ✅ FIXED | Low |
| 6 | `LIVE_CONTROL_IDS` contains non-existent APPSEC-001/002 | `predefined_queries_engine` constant | Dead references (no UI rows) | **Low** | Prune in a content pass | ⚠️ Documented (not changed) | None |
| 7 | Generic drill padding/fallback still fabricates rows for **other** modules | `module_kpi_drill_engine` / `api_module_kpi_drill` | Other modules' drilldowns may pad to demo minimums | **Medium** | Extend the authoritative pattern per module over time | ⚠️ Out of scope (PQ only) | Medium (non-PQ screens) |
| 8 | Live execution needs `psycopg2` + reachable targets | PostgreSQL controls | No live evidence if env lacks driver/DB | **Medium** | Pre-flight env; graceful error already in place | ⚠️ Documented; degrades gracefully | Medium (live-exec demo only) |

## Trustability validations (all pass)

| Requirement | Result |
|---|---|
| 1. KPI count equals drilldown count | ✅ Total 37 / Predefined 37 / Manual 0 / Frameworks 13→13 rows / Unsupported 21→21 rows |
| 2. Status equals runtime reality | ✅ Ready 6 = executable 6; Connector Missing / Configuration Required / Unsupported reflect actual connector + wiring |
| 3. Unsupported Technology KPI equals backend findings | ✅ 21 KPI = 21 `errors_found` = 21 drilldown rows |
| 4. Framework Coverage KPI equals actual framework coverage | ✅ 13 = 13 distinct frameworks = 13 drilldown rows |
| 5. Evidence rejection shows complete (available) context | ✅ Reason, User, Timestamp, Control, Framework, Workflow State |
| 6. No KPI displays unrelated records | ✅ PQ drilldowns return only KPI-specific data; empty-states are honest |
| 7. No "Ready" without executable capability | ✅ Verified — only the 6 genuinely executable controls are Ready |

## Residual gaps (documented, not defects)

- **Other-module drilldowns** still use the generic padding/fallback; only Predefined Queries is fully authoritative. Recommend rolling the same pattern out module-by-module (separate effort).
- **Remote/Oracle/Windows/NGINX connectors** are not implemented (shown truthfully as Connector Missing) — tracked in `docs/PRODUCTION/ECS_REMOTE_CONNECTOR_EXPANSION_PLAN.md`.
- **21 Unsupported controls** need query→technology mapping (content task).
- **APPSEC-001/002** dead references in `LIVE_CONTROL_IDS`.
- **Evidence/Observation ID** are not linked to dashboard rejection records.

## Overall Demo Risk Rating

**LOW** for the Phase-1 trustability story: every visible KPI reconciles to its drilldown, every status reflects runtime reality, no fabricated/placeholder/unrelated rows appear in Predefined Queries, and rejections carry full available context.

**MEDIUM** only for (a) live PostgreSQL execution in an environment lacking `psycopg2`/DB connectivity (degrades gracefully), and (b) drilldowns on **non-Predefined-Queries** modules, which still use the generic padding path. Both are documented above with mitigations.
