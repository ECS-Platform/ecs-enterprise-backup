# Phase 3 — ROI Scenario Validation

Scenario values use the **approved EXACT figures** (not derived):
Conservative = Expected −20%, Aggressive = Expected +20%, applied to BOTH
applications and net benefit. ECS OPEX is identical across scenarios. Verified
live against `/mvp/roi?scenario=…` and the embedded bar-chart series.

## Applications (per year)
| Scenario | Y1 | Y2 | Y3 | Y4 | Y5 |
|---|---|---|---|---|---|
| Conservative | 40 | 80 | 160 | 240 | 320 |
| Expected | 50 | 100 | 200 | 300 | 400 |
| Aggressive | 60 | 120 | 240 | 360 | 480 |

## Net Benefit ₹ Cr (per year)
| Scenario | Y1 | Y2 | Y3 | Y4 | Y5 |
|---|---|---|---|---|---|
| Conservative | 4.0 | 16.8 | 43.8 | 78.1 | 119.5 |
| Expected | 5.0 | 21.0 | 54.8 | 97.6 | 149.4 |
| Aggressive | 6.0 | 25.2 | 65.8 | 117.1 | 179.3 |

## Required summary
| Scenario | Applications (Y5) | Net Benefit (Y5) | Payback |
|---|---|---|---|
| Conservative | 320 | ₹119.5 Cr | Year 1 |
| Expected | 400 | ₹149.4 Cr | Year 1 |
| Aggressive | 480 | ₹179.3 Cr | Year 1 |

## Assertions
- Conservative ≠ Expected ≠ Aggressive on apps AND net benefit — TRUE.
- No slide shows identical application counts across all scenarios — TRUE.
- Bar chart (slide 4) values per scenario live:
  - Conservative ₹4 / 16.8 / 43.8 / 78.1 / 119.5 Cr
  - Expected ₹5 / 21 / 54.8 / 97.6 / 149.4 Cr
  - Aggressive ₹6 / 25.2 / 65.8 / 117.1 / 179.3 Cr
- Expected matches the approved board model exactly — TRUE.
- Each scenario tab re-renders apps, net benefit, scale-up story, bar chart,
  executive summary, approval slide and appendix table (via
  `window.ECS_ROI.scenarios[*].deck`) — TRUE.
