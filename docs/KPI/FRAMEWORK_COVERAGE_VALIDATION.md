# Framework Coverage KPI — Validation

**KPI:** "Frameworks Covered" on the Predefined Queries page.
**Backend:** `predefined_queries_engine.load_predefined_queries()` → `frameworks_covered = sorted({fw for c in controls for fw in c["frameworks"]})`; drilldown via `drill_predefined_query_kpi("frameworks_covered")`.
**Framework parsing:** `_parse_frameworks()` splits each control's `Framework Coverage` cell on `, ; | /` and newlines.

## Displayed vs. actual

| Check | Result |
|---|---|
| Displayed KPI count | **13** |
| Actual distinct frameworks (computed) | **13** |
| Drilldown row count | **13** |
| KPI = drilldown count | ✅ Equal |
| Drilldown shows framework data only | ✅ columns `framework, controls, predefined, manual` — no unrelated controls/evidence |
| Synthetic rows | ✅ None (route bypasses padding/fallback for `predefined_queries`) |

## Framework attribution (drilldown output)

| Framework | Controls | Predefined | Manual |
|---|---|---|---|
| AI SDLC | 3 | 3 | 0 |
| ASST | 4 | 4 | 0 |
| AppSec | 7 | 7 | 0 |
| CSITE | 4 | 4 | 0 |
| DB Baselining | 8 | 8 | 0 |
| DPSC | 15 | 15 | 0 |
| ITDRM | 2 | 2 | 0 |
| ITPP | 4 | 4 | 0 |
| MBSS | 1 | 1 | 0 |
| Middleware Baselining | 4 | 4 | 0 |
| OS Baselining | 7 | 7 | 0 |
| PCI DSS | 18 | 18 | 0 |
| VAPT | 5 | 5 | 0 |

## Why the per-framework control counts sum to more than 37 (not a contradiction)

Controls are **cross-mapped to multiple frameworks** (this is a core ECS value — one control/evidence satisfies several frameworks). The "Frameworks Covered" KPI counts **distinct frameworks (13)**, while the breakdown counts **control↔framework attributions** (which legitimately exceed the 37 unique controls). The figures are consistent:

- Unique controls = **37** (the Total Controls KPI).
- Distinct frameworks = **13** (the Frameworks Covered KPI).
- Sum of per-framework attributions > 37 because of intentional cross-framework reuse.

## Validation verdict

✅ **Framework Coverage KPI is trustable.** The count equals both the actual distinct-framework count and the drilldown row count; the drilldown returns framework-coverage data only, with no unrelated controls, no unrelated evidence, and no synthetic rows.
