# Predefined Queries — KPI Drilldown Audit

**Page:** `/mvp/predefined-queries`
**Drilldown endpoint:** `GET /api/module-kpi/drill?module=predefined_queries&metric=<metric>&count=<value>`
**Routing:** `routes_mvp.api_module_kpi_drill` → `module_kpi_drill_engine.drill_module_kpi` → `predefined_queries_engine.drill_predefined_query_kpi`

## Why the audit was needed (before state)

Before this hardening pass, the Predefined Queries KPI cards drilled through the **generic** module‑KPI path:

1. `drill_module_kpi("predefined_queries", metric)` called `get_module_capability()` (a generic workspace view, **not** the control library) and `_pick_rows()` (heuristic status matching). The predefined‑query KPIs have no matching keys there, so it fell through to **unrelated rows**.
2. When the heuristic produced no rows, the engine **fabricated 25 synthetic rows** (`generate_standard_drill_row`) and then `ensure_drill_rows(..., 25)` padded to a demo minimum.
3. The route additionally padded to the KPI `count` (`ensure_drill_rows`) and, on any empty result, substituted `_fallback_body()` synthetic data.

**Net effect (reported problems #1, #2, #4, #5, #6):** clicking a KPI opened unrelated datasets; `Manual Controls = 0` still showed ~25 fabricated records; `Frameworks Covered` did not show framework coverage; `Unsupported Tech` did not show unsupported technologies.

## Fix applied (after state)

- Added `drill_predefined_query_kpi()` as the **single source of truth** for these drilldowns. Each metric returns only rows directly related to that KPI, sourced from the same control set as the KPI cards.
- `drill_module_kpi()` now early‑returns to that function for `module == "predefined_queries"` (mirrors the existing `trends`/`reports` early‑returns).
- `api_module_kpi_drill` **bypasses count‑padding and the synthetic fallback** for `predefined_queries`, so results are never fabricated, padded, or unrelated.
- Zero‑count KPIs return an **honest empty‑state** (explanatory `note`, `rows: []`) rendered by `drilldown_engine.js` (`No supporting records.` + note), never placeholder rows.

## Per‑KPI validation

| KPI (click) | metric slug | Drilldown returns | Count = 0 behaviour | Related‑only? | Verified |
|---|---|---|---|---|---|
| Total Controls | `total_controls` | All 37 controls (`control, control_name, framework, technology, status`) | n/a (37) | Yes | ✅ 37 rows |
| Predefined Queries | `predefined_queries` | The 37 controls that have a query | Empty‑state: “No predefined queries are loaded…” | Yes | ✅ 37 rows |
| Manual Controls | `manual_controls` | Controls with no query | **Empty‑state** (note: “No manual controls — every loaded control has a predefined query.”) — **no fabricated rows** | Yes | ✅ 0 rows + note |
| Frameworks Covered | `frameworks_covered` | Per‑framework breakdown (`framework, controls, predefined, manual`) — 13 frameworks | Empty‑state: “No frameworks are mapped…” | Yes | ✅ 13 rows |
| Unsupported Tech | `unsupported_tech` | Predefined controls with `technology == Unknown` | Empty‑state: “No unsupported technologies…” | Yes | ✅ 21 rows |

All rows verified via the application test client against `/api/module-kpi/drill`. `count` padding confirmed **not applied** (e.g. `frameworks_covered&count=13` returns the 13 real framework rows; `manual_controls&count=0` returns 0 rows + note).

## Empty‑state contract

For any predefined‑query KPI with no matching records, the drill payload is:

```json
{ "ok": true, "title": "<KPI> — Predefined Queries", "columns": [...], "rows": [], "row_count": 0, "note": "<reason it is empty>" }
```

`drilldown_engine.js` renders the `note` as an info banner and the table body as “No supporting records.” — **no fake data, no placeholder records, no unrelated tables.**

## Residual notes

- Drilldowns for **other** modules are unchanged; the generic padding/fallback path remains intact for them. Only `module=predefined_queries` is rerouted.
- If the Excel library changes, all five KPIs and their drilldowns recompute from the same `load_predefined_queries()` result, so card values and drill datasets always reconcile.
