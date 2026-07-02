# Predefined Queries — KPI Dictionary

**Scope:** KPI cards on the Predefined Queries page (`/mvp/predefined-queries`)
**Source of truth (code):** `modules/operations/engines/predefined_queries_engine.py` → `get_predefined_queries_dashboard()` (KPI strip) and `drill_predefined_query_kpi()` (drilldowns)
**Rendered by:** `modules/operations/templates/mvp_predefined_queries.html` via the `workspace_exec_strip()` macro (`modules/shared/templates/partials/mvp_workspace_macros.html`)
**Data source:** `ECS_Query_Driven_Control_Library_Consolidated.xlsx` (loaded with `openpyxl`, parsed in `_load_from_excel()` / `load_predefined_queries()`)
**Drilldown endpoint:** `GET /api/module-kpi/drill?module=predefined_queries&metric=<metric>&count=<value>` → `module_kpi_drill_engine.drill_module_kpi()` → `predefined_queries_engine.drill_predefined_query_kpi()`

> **Displayed values below** are the deterministic values produced from the current Excel control library (verified at audit time). They will track the source file if it changes.

| KPI Name | Displayed Value | Calculation Formula | API Endpoint | Backend Service | Data Source | Query / Logic | Expected Drilldown Dataset | Phase‑1 Feasible |
|---|---|---|---|---|---|---|---|---|
| **Total Controls** | 37 | `len(controls)` — `report["controls_loaded"]` | `/mvp/predefined-queries` (page) · drill via `/api/module-kpi/drill?module=predefined_queries&metric=total_controls` | `PredefinedQueriesEngine` (`get_predefined_queries_dashboard`, `drill_predefined_query_kpi`) | Excel control library (`ECS_Query_Driven_Control_Library_Consolidated.xlsx`) | `COUNT(all rows parsed from Excel)` | All controls — columns: `control, control_name, framework, technology, status` | **Y** |
| **Predefined Queries** | 37 | `sum(1 for c in controls if c["predefined"])` — `report["predefined_controls"]`; `predefined = bool(query)` | drill via `metric=predefined_queries` | `PredefinedQueriesEngine` | Excel control library | `COUNT(controls WHERE query IS NOT NULL)` | Controls that have a query defined — same control columns | **Y** |
| **Manual Controls** | 0 | `controls_loaded − predefined_controls` — `report["manual_controls"]` | drill via `metric=manual_controls` | `PredefinedQueriesEngine` | Excel control library | `COUNT(controls WHERE query IS NULL)` | Controls without a predefined query (empty‑state when 0) | **Y** |
| **Frameworks Covered** | 13 | `len(report["frameworks_covered"])`; `frameworks_covered = sorted(distinct frameworks across all controls)` | drill via `metric=frameworks_covered` | `PredefinedQueriesEngine` | Excel `Framework Coverage` column → `_parse_frameworks()` | `COUNT(DISTINCT framework)` over parsed framework lists | Per‑framework breakdown — columns: `framework, controls, predefined, manual` | **Y** |
| **Unsupported Tech** | 21 | `len([c for c in predefined if c["technology"] == "Unknown"])` | drill via `metric=unsupported_tech` | `PredefinedQueriesEngine` | Excel query text → `detect_technology()` (deterministic rule match) | `COUNT(predefined controls WHERE detect_technology(query) == 'Unknown')` | Predefined controls whose query did not match a known connector — control columns (empty‑state when 0) | **Y** |

## Definitions & interpretation

- **Total Controls** — Every row loaded from the Excel control library. The denominator for all other counts. Decision: *“How large is the control catalog in scope?”*
- **Predefined Queries** — Controls with a non‑empty `query` cell (`predefined = bool(query)`). These are candidates for automated execution. Decision: *“How much of the catalog is automatable today?”*
- **Manual Controls** — Controls with no query (`predefined = False`); evidence must be collected manually. Decision: *“What still needs human evidence collection?”* (Currently **0** — the loaded library is fully query‑backed.)
- **Frameworks Covered** — Distinct frameworks referenced by any control’s `Framework Coverage` field, parsed by `_parse_frameworks()` (splits on `, ; | /` and newlines). Decision: *“Which regulatory frameworks does this catalog touch?”*
- **Unsupported Tech** — Predefined controls whose query text did **not** match any `TECHNOLOGY_RULES` pattern, so `detect_technology()` returned `"Unknown"`. These cannot be auto‑executed yet. Decision: *“Which automated controls need a connector / technology mapping before they can run?”*

## Technology detection (for Predefined Queries / Unsupported Tech)

`detect_technology(query)` is deterministic (no AI): it lowercases the query and matches against `TECHNOLOGY_RULES` patterns. A match returns the technology (e.g. `PostgreSQL`, `Linux`, `SonarQube`, `Trivy`, `GitLeaks`); no match returns `"Unknown"`. This is why **Unsupported Tech** is a precise, reproducible figure rather than an estimate.

## Status derivation (shown in drilldown `status` column)

`_derive_status(control)`:
- `Manual` — control has no query.
- `Unsupported Technology` — predefined but `technology == "Unknown"`.
- `Ready` — predefined and a known technology was detected.

## Traceability notes

- The KPI strip emits each card with `data-ecs-module-kpi-module="predefined_queries"` and `data-ecs-module-kpi-metric="<label lowercased, spaces→underscores>"`, so the metric slugs are exactly: `total_controls`, `predefined_queries`, `manual_controls`, `frameworks_covered`, `unsupported_tech`.
- All five KPIs are computed from the same in‑memory control set returned by `load_predefined_queries()`, guaranteeing the cards and their drilldowns reconcile to the identical dataset.
