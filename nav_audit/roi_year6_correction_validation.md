# ROI Year-6 Correction — Validation Evidence

**Task:** Fix the Executive Overview → ROI & Value Realization → Executive Value Dashboard (slide 4)
Year-6 values only. No other ROI logic, scenarios, storage savings, FTE savings, or Years 1–5/7 changed.

**Result:** ✅ Year-6 corrected. Only the Year-6 Applications, Annual Savings, and Net Benefit changed.
ECS Cost (2.2) was already correct and left untouched. Years 1–5 and Year 7 are byte-for-byte unchanged.

---

## 1. Root Cause

The Executive Value Dashboard (slide 4 of the ROI storyboard) renders from a **hardcoded Python
array**, `_BOARD_DASHBOARD`, in `app/roi/workbook.py` (consumed by `build_board_deck()`).

The 6th tuple (Year 6) was an **accidental duplicate of the Year-4 row** `(400, 72.64, 2.2, 70.44)`
instead of the correct Year-6 values. The authoritative `Executive_Dashboard` sheet inside `ROI.xlsx`
already holds the **correct** Year-6 figures (600 / 108.96 / 106.76); only the hardcoded board array
used by the rendered dashboard was wrong.

### Source-of-truth confirmation (read directly from `ROI.xlsx` → `Executive_Dashboard`)

```
Year 1   apps=  50 annual= 4.54  ecs_cost=4.0 net=  0.54
Year 2   apps= 100 annual= 9.08  ecs_cost=2.0 net= 16.16
Year 3   apps= 200 annual=13.62  ecs_cost=2.2 net= 34.12
Year 4   apps= 400 annual=72.64  ecs_cost=2.2 net= 70.44
Year 5   apps= 500 annual=90.80  ecs_cost=2.2 net= 88.60
Year 6   apps= 600 annual=108.96 ecs_cost=2.2 net=106.76   <-- correct in workbook
Year 7   apps= 800 annual=145.28 ecs_cost=2.2 net=143.08
```

The workbook's Year-6 row (`600 / 108.96 / 106.76`) matches the task's required values exactly,
confirming the fix target.

---

## 2. File Modified

`app/roi/workbook.py` — constant `_BOARD_DASHBOARD` (slide-4 Executive Value Dashboard, 7-year scale-up).

This is the **only** source for the rendered dashboard:
- `build_board_deck()` iterates `_BOARD_DASHBOARD` to produce `deck.rows` and `deck.chart`.
- The frontend `modules/shared/templates/partials/roi_storyboard.js` renders the slide-4 table,
  the 7-bar net-benefit chart, tooltips/labels, and callouts entirely from `deck.rows` / `deck.chart`
  / `deck.net_benefit_display` / `deck.steady_cost_display`. **No Year-6 value is hardcoded in the
  frontend** — so the single edit propagates to every tile, chart, trend line, legend, tooltip,
  waterfall bar, and executive summary card.

---

## 3. Exact Values Corrected (Year 6 only)

| Field | Old (wrong) | New (correct) | Source of truth |
|---|---|---|---|
| Applications | 400 | **600** | Executive_Dashboard |
| Annual Savings (Cr) | 72.64 | **108.96** | Executive_Dashboard |
| ECS Cost (Cr) | 2.2 | 2.2 (unchanged) | Executive_Dashboard |
| Net Benefit (Cr) | 70.44 | **106.76** | Executive_Dashboard |

### Diff (before → after)

```diff
 _BOARD_DASHBOARD = [
     (25,  4.54,   4.0, 0.54),
     (100, 18.16,  2.0, 16.16),
     (200, 36.32,  2.2, 34.12),
     (400, 72.64,  2.2, 70.44),
     (500, 90.80,  2.2, 88.60),
-    (400, 72.64,  2.2, 70.44),
+    (600, 108.96, 2.2, 106.76),
     (800, 145.28, 2.2, 143.08),
 ]
```

---

## 4. Dashboard / Chart Dataset — Before vs After

`build_board_deck('expected')` output:

### Before (Year 6 = duplicate of Year 4)
```
Y6 | apps=400 | annual=72.64 | ecs_cost=2.2 | net=70.44
chart.net  = [0.54, 16.16, 34.12, 70.44, 88.6, 70.44, 143.08]
chart.apps = [25, 100, 200, 400, 500, 400, 800]
```

### After (Year 6 corrected)
```
Year | Apps | AnnualSav(Cr) | ECScost(Cr) | NetBenefit(Cr) | displays
  Y1 |   25 |     4.54 |   4.0 |     0.54 | ann=₹4.54 Cr   net=₹0.54 Cr
  Y2 |  100 |    18.16 |   2.0 |    16.16 | ann=₹18.16 Cr  net=₹16.16 Cr
  Y3 |  200 |    36.32 |   2.2 |    34.12 | ann=₹36.32 Cr  net=₹34.12 Cr
  Y4 |  400 |    72.64 |   2.2 |    70.44 | ann=₹72.64 Cr  net=₹70.44 Cr
  Y5 |  500 |    90.80 |   2.2 |    88.60 | ann=₹90.80 Cr  net=₹88.60 Cr
  Y6 |  600 |   108.96 |   2.2 |   106.76 | ann=₹109.0 Cr  net=₹106.8 Cr
  Y7 |  800 |   145.28 |   2.2 |   143.08 | ann=₹145.3 Cr  net=₹143.1 Cr

chart.net         = [0.54, 16.16, 34.12, 70.44, 88.6, 106.76, 143.08]
chart.net_display = ['0.5', '16.2', '34.1', '70.4', '88.6', '106.8', '143.1']
chart.apps        = [25, 100, 200, 400, 500, 600, 800]
```

> Display note: the executive formatter (`fmt_cr_exec`) uses 1 decimal place for values ≥ 100,
> so 108.96 renders as “₹109.0 Cr” and 106.76 as “₹106.8 Cr” on tiles/labels. The underlying stored
> values are exactly 108.96 and 106.76 (visible in `chart.net` and the raw row values above).

---

## 5. Proof That ONLY Year-6 Changed

- The edit is a **single tuple** replacement at index 5 (Year 6) of `_BOARD_DASHBOARD`.
- Years 1–5 tuples and the Year-7 tuple are character-for-character identical pre/post (see diff §3).
- Post-fix `chart.net`/`chart.apps` differ from pre-fix **only** in position 6
  (`70.44 → 106.76`, `400 → 600`).
- ECS Cost row unchanged for every year (Year-6 ECS cost stayed 2.2).
- Scenarios, storage (`_BOARD_*` storage/FTE blocks, `Storage_Savings`), FTE
  (`_BOARD_FTE` / `FTE_Savings`), and the deterministic ROI engine (`app/roi/calculations.py`)
  were **not touched**.

## 6. Proof That Year-7 Remains Unchanged

```
Y7 | apps=800 | annual=145.28 | ecs_cost=2.2 | net=143.08
```

Identical to the required values (Applications 800, Annual Savings 145.28, Net Benefit 143.08). The
slide-4 callouts that read the *last* row (Year 7) — applications, net benefit, steady-state cost —
therefore also remain correct and unchanged.

---

## 7. Regression Checks

- `import app.roi.workbook` → **OK** (module compiles).
- `tests/test_roi_engine.py` contains **no** references to `_BOARD_DASHBOARD` / `build_board_deck`
  Year-6 values; its `600` assertions relate to VAPT applications and 5-point projections, unaffected
  by this change.
- Frontend (`roi_storyboard.js`) is fully data-driven from the deck payload; no hardcoded Year-6
  value exists in the template/JS layer.

**Dashboard screenshot:** not generated in this pass (data-layer correction verified via deck output
above). The rendered slide-4 table/chart/callouts derive 1:1 from the corrected `deck` payload.
