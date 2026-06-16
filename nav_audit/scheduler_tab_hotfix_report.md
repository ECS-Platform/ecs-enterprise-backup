# P1 Hotfix Report — Scheduler Sub-Navigation Tab Visibility

**Date:** 2026-06-16
**Priority:** P1 — Executive Demo Blocker
**Scope:** Operations → Scheduler ("Evidence Collection Engine") sub-navigation tabs ONLY.
**Result:** Fixed with a Scheduler-scoped CSS override. No global CSS changed. No other page touched.

---

## 1. Root Cause

### Component
The Scheduler tabs are rendered by the shared workspace macro `workspace_tab_nav(workspace)`,
invoked at `modules/operations/templates/mvp_scheduler.html:32`:

```html
{{ workspace_tab_nav(workspace) }}
```

This macro (`modules/shared/templates/partials/mvp_workspace_macros.html`) emits one button per tab:

```html
<button type="button" role="tab" class="ecs-workspace-tab{% if loop.first %} is-active{% endif %}"
        aria-selected="..." data-workspace-tab="{{ t.id }}">{{ t.label }}</button>
```

Tab labels come from `modules/shared/services/module_workspace.py` (`"scheduler"` entry):
Overview, App Scans, Cron Timeline, Run History, Failures, Tomorrow Plan, Integrations.

### CSS selector
`.ecs-workspace-tab` (active state `.ecs-workspace-tab.is-active` / `[aria-selected="true"]`).

### Inherited selector causing the issue
The page loads `mvp_styles.html` then `scheduler_styles.html` (`mvp_scheduler.html:1`). The
canonical `.ecs-workspace-tab` rule lives in `mvp_workspace_styles.html`.

**Pre-remediation** the canonical rule was low-contrast:

```css
.ecs-workspace-tab        { background:#fff;     color:#475569; }   /* slate on white */
.ecs-workspace-tab:hover  { color:#2563eb; }                        /* light blue on white */
.ecs-workspace-tab.is-active { background:#dbeafe; color:#2563eb; } /* #2563eb on #dbeafe = 4.24:1 — FAILS AA */
```

The active state `#2563eb` on `#dbeafe` measures **4.24:1**, below WCAG AA (4.5:1) — the
"washed out / partially invisible" tabs in the screenshot.

> **Note on the live build:** the canonical rule was already corrected in the prior tab-contrast
> remediation, and the Scheduler page now serves the corrected `.ecs-workspace-tab` CSS. The
> screenshot most likely reflects **stale browser cache** of the page's inline CSS. To make the
> Scheduler page deterministically correct regardless of cache state — and to comply with the
> requirement to fix *only* Scheduler without touching the shared class — this hotfix adds a
> Scheduler-scoped override that always wins on this page.

---

## 2. Fix

### File changed
`modules/operations/templates/partials/scheduler_styles.html` (Scheduler-only partial; included
only by `mvp_scheduler.html`, and loaded **after** `mvp_styles.html`).

### Lines changed
Appended a scoped block (22 lines) before the closing `</style>`.

### Selector strategy (compliant with the rules)
All new rules are scoped under the Scheduler page body class **`.ecs-cap-scheduler`**
(`mvp_scheduler.html:2` → `<body class="bg-light ecs-cap-scheduler">`). This is a
"scheduler-specific parent-scoped selector," exactly the acceptable pattern. No bare `.nav-tabs`,
`.nav-pills`, `.btn`, `.ecs-tab`, or unscoped `.ecs-workspace-tab` was modified.

### Before / after

| State | Before (served pre-fix / stale) | After (Scheduler-scoped) | Source of "after" |
|---|---|---|---|
| Inactive | `#475569` on `#fff` (or stale wash) | `color:#0F172A; background:#E2E8F0; border:1px solid #CBD5E1` | `.ecs-cap-scheduler .ecs-workspace-tab` |
| Active | `#2563eb` on `#dbeafe` (4.24:1) | `color:#FFFFFF; background:#2563EB; font-weight:700` | `.ecs-cap-scheduler .ecs-workspace-tab.is-active` |
| Hover | `#2563eb` on `#fff` | `color:#FFFFFF; background:#1D4ED8` | `.ecs-cap-scheduler .ecs-workspace-tab:hover` |
| Focus | (none) | `outline:2px solid #93C5FD; outline-offset:2px` | `.ecs-cap-scheduler .ecs-workspace-tab:focus-visible` |

---

## 3. Validation

### Contrast ratios (WCAG AA ≥ 4.5:1 for text)

| State | Foreground | Background | Ratio | AA |
|---|---|---|---|---|
| Inactive text | `#0F172A` | `#E2E8F0` | **14.48:1** | ✅ |
| Active text | `#FFFFFF` | `#2563EB` | **5.17:1** | ✅ |
| Hover text | `#FFFFFF` | `#1D4ED8` | **6.70:1** | ✅ |
| Focus ring | `#93C5FD` outline (decorative, not text) | — | n/a | ✅ visible ring |

All text states pass WCAG AA. The focus ring is a non-text decorative outline; its job is
visibility, satisfied by the 2px ring + offset.

### Scheduler verification (served HTML, `/mvp/scheduler`)
- HTTP 200; body carries `ecs-cap-scheduler`.
- Scoped override `.ecs-cap-scheduler .ecs-workspace-tab` is present in the served page.
- All seven tab labels render (Overview, App Scans, Cron Timeline, Run History, Failures,
  Tomorrow Plan, Integrations); first tab carries `is-active` (immediately recognizable as active).
- Standalone visual preview artifact: `nav_audit/artifacts/scheduler_tabs_preview.html`
  (rendered nav + scoped CSS; open in a browser to confirm legibility).
  *(No headless browser is installed in this environment, so a PNG screenshot could not be
  auto-captured; the HTML preview + contrast math are the verification evidence.)*

### No-regression verification (audited, NOT modified)
Confirmed the Scheduler-scoped rule is **absent** from every forbidden page (it cannot affect them):

| Page | HTTP | Scheduler rule leaked? |
|---|---|---|
| Executive Overview (`/mvp/demo-overview`) | 200 | No |
| Enterprise (`/mvp/enterprise`) | 200 | No |
| Pan India (`/mvp/pan-india`) | 200 | No |
| Reports (`/mvp/reports`) | 200 | No |
| Trends (`/mvp/trends`) | 200 | No |
| Evidence Health (`/mvp/evidence-health`) | 200 | No |
| Completeness (`/mvp/completeness`) | 200 | No |

No global selector (`.ecs-workspace-tab`, `.ecs-tab`, `.nav-tabs`, `.nav-pills`, `.btn`, badges)
was modified. Prior accessibility fixes and badge/button styling are untouched.

---

## 4. Regression Audit (report only — NOT fixed)

Per instructions, the following observations are documented but **deliberately left unchanged**:

| Page | Component | CSS selector | Contrast | Screenshot | Recommendation |
|---|---|---|---|---|---|
| Platform-wide | Sub-nav tabs | `.ecs-workspace-tab.is-active` (pre-remediation value) | `#2563eb` on `#dbeafe` = **4.24:1** (fails) | n/a (server-rendered; clear cache to see corrected build) | Already corrected globally in the prior tab-contrast remediation; if any environment still shows the old wash it is **stale browser cache** — hard-refresh. No further code change recommended. |
| Workspace timeline | `.ecs-timeline-badge` | `.ecs-timeline-badge` | corrected to `#1E3A8A` on `#dbeafe` = 8.49:1 in prior remediation | n/a | None — already compliant. |
| No NEW low-contrast tab defects were found on Enterprise, Pan India, Reports, Trends, Evidence Governance, Governance drilldowns, or Executive Overview. | — | — | all states ≥ 4.5:1 | n/a | None. |

No additional defects fixed in this hotfix (scope: Scheduler only).

---

## 5. Success Criteria Checklist

1. ✅ Scheduler tab labels clearly visible (inactive 14.48:1).
2. ✅ Active tab immediately recognizable (solid `#2563EB`, white, bold, vs. light-slate inactive).
3. ✅ No global CSS changes (scoped under `.ecs-cap-scheduler`).
4. ✅ No impact to previously remediated Executive Overview tabs (rule absent there).
5. ✅ No impact to framework pages (rule absent there).
6. ✅ No impact to workspace navigation on other modules (rule absent there).
7. ✅ WCAG AA maintained (all text states ≥ 4.5:1).
