# Predefined Queries — Demo Readiness Report

**Module:** Predefined Queries (`/mvp/predefined-queries`, `/mvp/predefined-queries/detail`)
**Scope of change:** Traceability, drilldowns, Run‑Query modal UX, error handling, demo readiness. **No navigation, routes, or business logic removed.**

## Current Issues (as reported)

1. KPI cards did not clearly map to the data shown when clicked.
2. KPI drilldowns returned unrelated datasets.
3. "Run Query" view was one long scroll mixing query, result, evidence and history.
4. Manual Controls KPI showed records even when count = 0.
5. Frameworks Covered KPI did not show framework coverage data.
6. Unsupported Technology KPI did not show unsupported technologies.
7. Query‑execution errors surfaced as 500 / `ModuleNotFoundError: psycopg2`.
8. KPIs were not explainable / traceable to backend logic.

## Issues Fixed

| # | Issue | Fix | Evidence |
|---|---|---|---|
| 1, 2 | KPI ↔ data mismatch / unrelated drilldowns | Added `drill_predefined_query_kpi()` as single source of truth; `drill_module_kpi` early‑returns for `predefined_queries`; route bypasses generic padding/fallback | `docs/01-product/product/PREDEFINED_QUERY_KPI_DRILLDOWN_AUDIT.md` |
| 3 | Monolithic Run‑Query view | Detail page refactored into 5 tabs: **Summary · Query · Result · Evidence · Audit Trail** (only one section visible at a time) | `modules/operations/templates/mvp_predefined_query_detail.html` |
| 4 | Manual Controls (0) showed fake rows | Zero‑count drilldowns now return an honest empty‑state (`rows: []` + explanatory `note`); padding/fallback disabled for this module | Verified: `manual_controls&count=0` → 0 rows + note |
| 5 | Frameworks Covered drilldown wrong | Returns per‑framework breakdown (`framework, controls, predefined, manual`) — 13 frameworks | Verified: 13 rows |
| 6 | Unsupported Tech drilldown wrong | Returns predefined controls with `technology == Unknown` — 21 rows | Verified: 21 rows |
| 7 | Ungraceful execution errors | `psycopg2` import guarded in `run_postgresql_query` and `connector_for_technology`; run route wrapped so it never 500s; user sees **“PostgreSQL connector unavailable — Reason … — Action: Install psycopg2‑binary…”** | `predefined_queries_engine.py`, `query_connectors.py`, `routes_mvp.py` |
| 8 | KPI explainability | Full KPI Dictionary with formulas, services, data sources, SQL/logic, drilldown datasets | `docs/01-product/product/PREDEFINED_QUERY_KPI_DICTIONARY.md` |

### Verified KPI values (current Excel library)

Total Controls **37** · Predefined Queries **37** · Manual Controls **0** · Frameworks Covered **13** · Unsupported Tech **21**.

### Files changed

- `modules/operations/engines/predefined_queries_engine.py` — added `drill_predefined_query_kpi()` + `_pq_drill_body()`; guarded psycopg2 import in `run_postgresql_query` (structured `connector_unavailable` error).
- `modules/operations/engines/query_connectors.py` — `connector_for_technology()` returns `None` instead of raising when the PostgreSQL driver is missing.
- `modules/shared/drilldowns/module_kpi_drill_engine.py` — early‑return to the authoritative PQ drill for `module == "predefined_queries"`.
- `modules/shared/routes/routes_mvp.py` — drill route bypasses padding/fallback for `predefined_queries`; `run` route wrapped to never surface a 500 and to format a graceful `Reason/Action` notice.
- `modules/operations/templates/mvp_predefined_query_detail.html` — 5‑tab Run‑Query experience.

## Remaining Gaps

- **Live PostgreSQL execution** still requires `psycopg2` installed and a reachable demo database; without it the UI now degrades gracefully but does not produce live evidence. (Tracked in `docs/01-product/use-cases/ECS_CONNECTOR_ACTIVATION_PLAN.md`.)
- **Unsupported Tech (21)** controls remain non‑executable until their queries are mapped to a connector/technology — a content (Excel) task, not a code defect.
- KPI cards on the **catalog** page are still rendered via the shared `workspace_exec_strip` strip; the drilldowns are now correct, but a future pass could reduce the catalog KPI count per the IA review.
- Evidence tab currently surfaces the most recent generated evidence record for the control; a full evidence‑history list per control is a future enhancement.

## Demo Risk Rating

**LOW** for the core Phase‑1 demo story (browse catalog → open a control → Summary/Query/Result/Evidence/Audit‑Trail tabs → click KPIs for traceable drilldowns). KPI drilldowns are accurate and empty‑states are honest; query‑execution failures degrade gracefully with no stack traces.

**MEDIUM** only if the demo intends to show a **live PostgreSQL execution producing new evidence** in an environment without `psycopg2`/DB connectivity — in that case the flow shows a graceful "connector unavailable" message rather than live evidence. Mitigation: pre‑install `psycopg2-binary` and confirm the demo DB before the session, or demo execution against a control whose connector is available.
