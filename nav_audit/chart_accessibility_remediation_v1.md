# ECS Chart Accessibility, Contrast & Readability Remediation

**Release tag:** `ecs-chart-accessibility-remediation-v1`

Platform-wide standardization of chart contrast, tabs, badges, legends, supporting
text, and self-describing chart chrome (titles/subtitles/axis labels/axis scale/
units/data labels/tooltips). Grounded in the **actual** ECS charting stack (vanilla
JS + CSS div/SVG bars — no Chart.js/canvas), so the fix standardizes the existing
shared renderers and classes rather than introducing a parallel system.

---

## 1. Root analysis (what was actually wrong)

ECS renders all charts via CSS bars driven by shared JS helpers in
`modules/shared/templates/partials/executive_charts_system.html`
(`ecsRenderCompactBarChart`, `ecsRenderHorizontalBars`, `ecsRenderSparkline`) plus
server-rendered Jinja bars. The systemic issues traced to:

| Issue | Root cause (file) |
|---|---|
| Light-gray text on white | `--ecs-chart-muted: #94a3b8` (2.56:1, **fails AA**) used for subtitles/labels/legends |
| Low-contrast legend/labels | `--ecs-chart-slate: #475569` + sub-12px fonts (0.48–0.66rem) |
| Light green/orange below AA | `--ecs-chart-green: #4a7c59`, `--ecs-chart-orange: #c27803` |
| Missing axis labels/scale/units | renderer had no axis frame, no Y-scale ticks, no units |
| Inconsistent tabs/badges | no standardized tab/badge token set |
| No validation | no contrast/config/accessibility utilities |

---

## 2. What changed

### New files
| File | Purpose |
|---|---|
| `modules/shared/templates/partials/ecs_chart_standard.html` | Canonical WCAG token set + standardized tab/badge/legend/supporting-text classes + self-describing axis chrome CSS |
| `modules/shared/static/js/ecs_chart_standards.js` | `validateContrast()`, `validateChartAccessibility()`, `validateChartConfiguration()`, `auditPage()` |
| `tests/test_chart_accessibility_standard.py` | 35 tests: palette AA, tokens/classes present, validator behavior (Node), platform delivery |

### Modified files
| File | Change |
|---|---|
| `modules/shared/templates/partials/executive_charts_system.html` | Renderer upgrade: `niceScale()` auto Y-axis, `richTip()` tooltips (metric/value/previous/period/%change/context), `yLabel`/`xLabel`/`units`/`subtitle` options → framed self-describing charts with visible Y-scale; horizontal-bar tooltips+units; **re-includes the standard last** so token overrides win |
| `modules/shared/templates/partials/enterprise_theme.html` | Includes the standard + loads validator JS (covers role dashboards/drilldowns that load the theme without the chart system) |

> **Load order:** the standard always loads **after** `executive_charts_system.html`,
> so its accessible `:root` tokens override the legacy low-contrast palette.

---

## 3. Part 1 — Accessibility standardization (WCAG AA, verified)

All standardized pairs computed/verified at ≥ 4.5:1 (most ≥ 7:1):

**Series palette on white:** navy 11.5, slate 10.35, blue 5.17, teal 5.47, green 5.02,
orange 5.18, red 6.47, muted 7.58, benchmark 7.9 — **all PASS**.

**Supporting text on white:** axis `#0F172A` 17.85, legend `#0F172A` 17.85,
subtitle `#334155` 10.35, helper `#475569` 7.58 — **all PASS**.

**Tabs (as specified):** inactive `#E2E8F0/#1E293B` 11.87, active `#FFFFFF/#2563EB` 5.17,
hover `#FFFFFF/#1D4ED8` 6.7 — **all PASS**.

**KPI badges** — reconciled to satisfy the brief's own non-negotiable rule
("never allow any combination below WCAG AA"):

| Badge | Brief | Reconciled | Ratio |
|---|---|---|---|
| Blue | white on #2563EB | unchanged | 5.17 ✓ |
| Green | white on #16A34A (**3.3 fail**) | white on **#15803D** | 5.02 ✓ |
| Red | white on #DC2626 | unchanged | 4.83 ✓ |
| Orange | white on #F97316 (**2.8 fail**) | **#111827** on #F97316 | 6.33 ✓ |
| Yellow | #111827 on #EAB308 | unchanged | 9.25 ✓ |

> **Deviation note (intentional):** the brief's white-on-green and white-on-orange
> fall below WCAG AA for normal text. Because the brief explicitly forbids sub-AA
> combinations, those two were reconciled to AA while preserving the requested hues
> (green slightly darkened; orange keeps its hue with dark ink, mirroring the
> yellow treatment). All other tab/badge colors are used exactly as specified.

Minimum legend/subtitle/helper font size raised to **≥ 12px** (0.75rem); data labels
bold dark; light-gray-on-white eliminated.

---

## 4. Part 2 — Chart readability standardization

`ecsRenderCompactBarChart` now supports (and, when supplied, auto-renders):
`title` (existing card title), `subtitle`, `yLabel`, `xLabel`, `units`, auto Y-axis
**scale** (`niceScale` ticks, always visible when axes requested), **data labels**
with units on every bar, **rich tooltips** (Metric · Value · Previous · Period ·
%Change · Context), and **self-describing legends**. Responsive rules prevent axis
clipping, hidden/overlapping labels, and legend/tooltip overflow.

Backward compatible: charts that don't pass axis options keep their existing layout
but still inherit the accessible palette, fonts, legend, and tooltip text.

---

## 5. Part 3 — Shared component refactor

The single shared renderer + the new standard partial are the common inheritance
point. Because every ECS dashboard pulls charts through
`executive_charts_system.html` (via `mvp_styles.html`) and/or `enterprise_theme.html`,
**no individual dashboard requires manual accessibility fixes** — they inherit:
accessible palette, ≥12px legend/label text, standardized tabs/badges, axis chrome,
data labels, tooltips, and responsive rules automatically.

---

## 6. Part 4 — Automated validation utilities

`modules/shared/static/js/ecs_chart_standards.js` (dependency-free, browser + Node):

- `validateContrast(fg, bg)` → `{ ratio, AA, AAA, AA_large, passes }` (WCAG 2.x luminance).
- `validateChartAccessibility(elOrDescriptor)` → fails on missing title/subtitle/
  X-axis/Y-axis/Y-scale/legend/tooltip, hidden labels, overlapping labels.
- `validateChartConfiguration(cfg)` → pre-render config gate for the same rules.
- `auditPage()` → console audit of every chart on the page.

Verified via Node: low-contrast `#94a3b8/#fff` → AA=false; `#475569/#fff` → AA=true;
incomplete config → fail; complete config → pass.

---

## 7. Part 5 — Platform-wide application (verified delivered)

Confirmed (tests + live render) that the standard tokens + validator are served on:
Trends, Reports, Enterprise, Pan India, role/Executive dashboards, AI Governance,
Evidence Governance — and via `enterprise_theme.html` reach Universal Drilldowns and
all future charts that use the shared renderers/classes.

---

## 8. Test evidence

`tests/test_chart_accessibility_standard.py` — **35 passed**:
- Full palette / supporting text / tabs / badges meet WCAG AA (Python-computed).
- Guard test ensures the old `#94a3b8` muted (2.56:1) can never pass.
- Standard partial defines all required tokens & classes; chart system includes it last.
- Renderer exposes axis/units/scale/tooltip support.
- Validator JS behavior verified under Node.
- Standard served on 5 representative pages across modules.

**Regression check:** existing chart suites
(`test_trends_analytics`, `test_reports_analytics`, `test_universal_drilldown_engine`,
`test_top_risk_application_rendering`) pass. Two failures in
`test_ecs_platform_governance.py` (`test_framework_metrics_unique_including_extensions`,
`test_dashboard_workflow_drillable`) were verified **pre-existing** (fail identically
with these changes reverted) and are unrelated to chart accessibility.

---

## 9. How to apply readability to a chart (developer note)

```js
ecsRenderCompactBarChart('ecsGranCompChart', items, {
  metricName: 'Compliance Coverage',
  subtitle: 'Monthly control implementation coverage percentage',
  yLabel: 'Compliance', units: '%',
  xLabel: 'Month',
  seriesLabel: 'Coverage',
  drill: { page: 'trends', chartId: 'compliance' }
});
// items: [{ label:'Mar', value:83, previous:79, period:'March 2026', tone:'blue' }, ...]
```
This yields title + subtitle + rotated Y-axis label + visible Y-scale + X-axis label +
on-bar data labels with units + rich tooltips + explained legend — all AA-compliant.
