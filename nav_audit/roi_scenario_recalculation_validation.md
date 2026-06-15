# ROI Scenario Recalculation — Validation Report

**Scope:** Scenario value-realization modelling for the ROI deck.
**Unchanged (as required):** application counts, framework counts, ECS Cost, OPEX,
slide structure, executive styling, chart types.
**Only value-realization metrics scale** by the scenario factor.

---

## 1. Scenario Model

| Scenario | Factor | Indicator |
|---|---|---|
| Conservative | × 0.80 (−20%) | Amber `#F59E0B` |
| Expected | × 1.00 (baseline) | Blue `#38BDF8` |
| Aggressive | × 1.20 (+20%) | Green `#22C55E` |

Scaled metrics: Annual Savings · Net Benefit · Hours Saved · Emails Saved ·
FTE Equivalent · per-framework savings · FY25-26 live value.
**Not scaled:** application counts, framework counts, observations, ECS Cost, OPEX.

An **active scenario badge** (dot + label + factor %) renders next to the toggle and
recolours amber / blue / green to match the selection.

---

## 2. Slide 1 — FY25-26 Actual Live Value Realization

| Metric | Conservative | Expected | Aggressive |
|---|---|---|---|
| Headline total | **₹13.82 Cr** | **₹17.27 Cr** | **₹20.72 Cr** |
| ASST (example) | ₹2.68 Cr | ₹3.35 Cr | ₹4.02 Cr |

All 17 framework values scale proportionally; the 5 highlighted frameworks remain highlighted.

## 3. Slide 2 — Framework Value Realization (25-app)

| Metric | Conservative | Expected | Aggressive |
|---|---|---|---|
| Hours Saved | **36.4K** (36,350) | **45.4K** (45,438) | **54.5K** (54,526) |
| Annual Saving | **₹3.63 Cr** | **₹4.54 Cr** | **₹5.45 Cr** |

Framework-level emails/hours/annual saving all scale; application counts and
observation counts stay constant.

## 4. Slide 3 — FTE Productivity Realization

| Metric | Conservative | Expected | Aggressive |
|---|---|---|---|
| FTE Equivalent | **18.2** | **22.7** | **27.3** |

KPI cards, the Without/With ECS comparison graphic, the comparison chart, and the
productivity banner all update. (Cost-per-hour and average-salary rate assumptions are
unchanged, as they are inputs, not value outputs.)

## 5. Slide 4 — Executive Value Dashboard (Net Benefit, ₹ Cr)

| Year | Conservative (0.8) | Expected | Aggressive (1.2) |
|---|---|---|---|
| FY26 | 0.43 | 0.54 | 0.65 |
| FY27 | 12.93 | 16.16 | 19.39 |
| FY28 | 27.30 | 34.12 | 40.94 |
| FY29 | 56.35 | 70.44 | 84.53 |
| FY30 | 70.88 | 88.60 | 106.32 |
| FY31 | 56.35 | 70.44 | 84.53 |
| FY32 | 114.46 | 143.08 | 171.70 |

(Displayed with the approved executive formatting: 2 dp under ₹100 Cr, 1 dp at/above
₹100 Cr — e.g. ₹114.5 Cr, ₹143.1 Cr, ₹171.7 Cr. The underlying chart bar heights use
the exact values.) **ECS Cost stays ₹4.00 / ₹2.00 / ₹2.20 Cr across every scenario.**

---

## 6. Scenario Switching

Selecting a scenario re-renders, client-side from the precomputed per-scenario deck
(`window.ECS_ROI.scenarios[name].deck`):

- Slide 1 — 3 KPI cards + highlighted horizontal chart.
- Slide 2 — framework table + bar chart + bottom callout.
- Slide 3 — KPI cards + Without-ECS figure + comparison chart + banner.
- Slide 4 — dashboard table + net-benefit chart + callout band.
- Scenario badge colour, label, and factor %.

All three scenario decks are present in the client payload and verified to carry the
correct scaled values.

---

## 7. Visual Indicators

| Scenario | Toggle active colour | Badge |
|---|---|---|
| Conservative | Amber | ● Conservative · 80% (amber) |
| Expected | Blue | ● Expected · 100% (blue) |
| Aggressive | Green | ● Aggressive · 120% (green) |

---

## 8. Validation Results (`/mvp/roi`)

| Check | Result |
|---|---|
| HTTP (all scenarios) | **200** |
| Conservative = 80% of Expected | **PASS** (₹13.82 = 17.27×0.8; 36,350 = 45,438×0.8; 18.2 = 22.72×0.8; FY32 114.46 = 143.08×0.8) |
| Aggressive = 120% of Expected | **PASS** (₹20.72; 54,526; 27.3; FY32 171.70 = 143.08×1.2) |
| Charts update correctly | **PASS** (live horizontal chart, framework chart, FTE chart, 7-bar net-benefit chart) |
| FTE values update correctly | **PASS** (18.2 / 22.7 / 27.3; comparison + banner) |
| Framework values update correctly | **PASS** (all 17 scale; highlights retained) |
| Dashboard values update correctly | **PASS** (Annual Savings + Net Benefit scale; ECS Cost constant) |
| App / framework counts unchanged | **PASS** |
| ECS Cost / OPEX unchanged | **PASS** (₹4.00/₹2.00/₹2.20 Cr; OPEX ₹2.20 Cr in callout) |
| Active scenario badge | **PASS** (amber / blue / green) |
| No slide layout breaks | **PASS** (screenshots) |
| No text overflow / no wrap | **PASS** (nowrap numeric cells; tables fit one screen) |
| JS syntax (`node --check`) | **PASS** |
| All JS re-render selectors exist in DOM | **PASS** (15/15) |
| Linter | **PASS** |

**Screenshots:** `nav_audit/roi_scn_expected_s1.png` · `roi_scn_aggressive_s1.png` ·
`roi_scn_conservative_s4.png`

---

## 9. Files Changed

| File | Change |
|---|---|
| `app/roi/workbook.py` | Added `_SCENARIO_FACTORS` (0.80/1.00/1.20), `_SCENARIO_COLORS`, `_SCENARIO_LABELS`. `build_board_deck(scenario)` now scales value metrics by factor (app/framework counts, ECS cost, OPEX untouched) and emits `scenario_label` / `scenario_color` / `scenario_factor`. `_build_live_block` / `_build_framework_block` / `_build_fte_block` take a `factor`. |
| `modules/executive_overview/templates/mvp_roi_center.html` | Added active scenario badge (colour + label + factor); moved `{% set deck %}` above the scenario bar. |
| `modules/shared/templates/partials/roi_storyboard.js` | `applyDeckScenario(name)` re-renders all 4 slides (KPIs, tables, charts, callouts, FTE, framework values) and the badge from `DATA.scenarios[name].deck`; bound to the scenario toggle. |
| `modules/shared/templates/partials/roi_center_styles.html` | Scenario badge styling (amber/blue/green via `--scn-color`). |

---

## 10. Summary

- Conservative / Expected / Aggressive now show **materially different** value realization
  (× 0.80 / × 1.00 / × 1.20) across every slide.
- Application counts, framework counts, ECS Cost and OPEX are unchanged.
- Switching the scenario updates KPIs, charts, tables, callout bands, framework values,
  FTE values, and the colour-coded active-scenario badge.
- No layout breaks, no text overflow; values verified against the supplied targets.

**Status: COMPLETE — awaiting approval. Not committed, tagged, or pushed.**
