# Scheduler "Washed Out" — Proven Root Cause (Investigation Only)

**Date:** 2026-06-16
**Status:** Root cause **proven**. **No code modified.** Fix proposed at the end for approval.
**Environment when reproduced:** `DEMO_MODE=true`, `ECS_AUTH_ENABLED=false` (current shell).

---

## 0. Executive answer

The Scheduler tabs *themselves* are now correctly colored, but the **whole content region looks
faded** because of a **theme/container conflict that has nothing to do with tab color**:

> In **DEMO_MODE**, the executive **dark theme** repaints all supporting text to **light gray**
> (`#CBD5E1` / `#94A3B8`) on the assumption the content sits on a **dark** page. But the
> **workspace panes and tables explicitly force a WHITE background** via a CSS rule the dark theme
> cannot match. The result is **light-gray text on white** — section labels at **2.56:1** and body
> text at **1.48:1**, far below WCAG AA (4.5:1). That is the "everything faded" symptom (tab labels,
> section labels, table headers, supporting text).

This is **NOT** a tab-styling bug and **NOT** Scheduler-only. It is a **DEMO_MODE global
interaction** that affects every page using white workspace panes. Scheduler is simply where it was
reported.

---

## 1. Scheduler tab component & rendered HTML

- **Template:** `modules/operations/templates/mvp_scheduler.html:32` → `{{ workspace_tab_nav(workspace) }}`
- **Macro:** `modules/shared/templates/partials/mvp_workspace_macros.html` (`workspace_tab_nav`)
- **Rendered markup (per tab):**
  ```html
  <button type="button" role="tab"
          class="ecs-workspace-tab is-active" aria-selected="true"
          data-workspace-tab="overview">Overview</button>
  ```
- **Tab labels source:** `modules/shared/services/module_workspace.py:102` (`"scheduler"`):
  Overview, App Scans, Cron Timeline, Run History, Failures, Tomorrow Plan, Integrations.
- **Section labels / supporting text** (the *other* faded elements) are plain Bootstrap utility
  text on the page, e.g. `mvp_scheduler.html:35,47,64,73`:
  ```html
  <h6 class="small text-muted text-uppercase mb-1">Yesterday Scan Summary</h6>
  ```
  and table headers inside `<table class="table ... ecs-paginated-table">`.

---

## 2. Exact selector chain (the cascade that produces the fade)

### 2a. The white surface (container-level)
`modules/shared/templates/partials/mvp_workspace_styles.html:47`
```css
.ecs-workspace-pane.is-active {
  display: block; ...
  background: #fff;          /* ← active pane is WHITE (a CSS rule, not a .bg-white class) */
  ...
}
```
Tables are likewise forced white in DEMO_MODE by
`modules/shared/templates/partials/accessibility_theme.html:38-55`
(`table.table … { background:#FFFFFF; color:#0F172A }`).

### 2b. The light-gray text (theme-level, DEMO_MODE only)
Loaded only in demo mode via `modules/shared/templates/partials/mvp_styles.html:8-9`:
```jinja
{% if demo_mode|default(false) %}{% include "partials/demo_dark_theme.html" %}{% endif %}
{% if demo_mode|default(false) %}{% include "partials/accessibility_theme.html" %}{% endif %}
```

`modules/shared/templates/partials/demo_dark_theme.html:31-32`
```css
p, span, li, dd, dt, label, small, .text-muted, .text-secondary, .lead{
  color:var(--demo-text2)!important; }      /* --demo-text2 = #CBD5E1 */
```
`modules/shared/templates/partials/accessibility_theme.html:29-30`
```css
.text-muted, .text-secondary{ color:var(--ax-text2)!important; }     /* #CBD5E1 */
small.text-muted, .small.text-muted{ color:var(--ax-muted)!important; } /* #94A3B8 */
```

### 2c. Why the dark theme does NOT fix the pane background
`demo_dark_theme.html:20-21` only repaints surfaces that carry a **class**:
```css
.bg-light, .bg-white, .card.bg-white, .bg-body, .bg-body-tertiary{
  background:var(--demo-card)!important; ... }
```
`.ecs-workspace-pane.is-active` has **no** `.bg-white`/`.bg-light` class — its white comes from a
*CSS rule*. So the dark-flip selector never matches the pane, and the pane stays **white** while the
text becomes **light gray**.

**Net selector chain:**
`body.ecs-cap-scheduler` (DEMO_MODE) → `.ecs-workspace-main` → `.ecs-workspace-pane.is-active`
(**background:#fff**, unflipped) → `h6.small.text-muted` / table `thead th` / `.text-muted`
(**color:#CBD5E1 / #94A3B8** from demo themes) = **light-gray-on-white**.

---

## 3. Computed styles (served HTML + computed contrast)

| Element | Background (computed) | Text color (computed) | Contrast | WCAG AA |
|---|---|---|---|---|
| Active tab | `#2563EB` (scheduler scoped fix wins, loads last) | `#FFFFFF` | 5.17:1 | ✅ |
| Inactive tab | `#E2E8F0` (scoped fix) | `#0F172A` | 14.48:1 | ✅ |
| **Section label** `h6.small.text-muted` | **`#FFFFFF`** (white pane, unflipped) | **`#94A3B8`** (demo `small.text-muted`) | **2.56:1** | ❌ |
| **Supporting text** `.text-muted` | **`#FFFFFF`** | **`#CBD5E1`** (demo `.text-muted`) | **1.48:1** | ❌ |
| Table header `thead th` | `#1E293B` (accessibility_theme forces dark header) | `#F8FAFC` | high | ✅ (header ok) |
| Table body `td` | `#FFFFFF` (forced) | `#0F172A` (forced) | high | ✅ (covered by `.table` rules) |

> The **tabs and table cells are fine**; the failures are the **`text-muted` section labels and
> any `.text-muted`/`.text-secondary` supporting text** inside the white panes (and any `<small>`
> helper text). The earlier "tab" report was correct about tabs but the screenshot's broader fade
> is these `text-muted` elements on white.

### Stylesheet load order on the served Scheduler page (later = higher priority)
| Offset | Stylesheet |
|---|---|
| 287k | workspace tab standard (`mvp_workspace_styles.html`) |
| 296k | `demo_dark_theme.html` (DEMO_MODE) |
| 304k | `accessibility_theme.html` (DEMO_MODE) |
| 315k | scheduler scoped tab fix (prior hotfix) |

The scoped tab fix wins for tabs; nothing after `accessibility_theme` rescues `.text-muted` on white panes.

---

## 4. Inherited-value trace (requested checklist)

| Property | Value on faded elements | Source | Verdict |
|---|---|---|---|
| `color` | `#CBD5E1` / `#94A3B8` (light gray) | `demo_dark_theme.html:31-32`, `accessibility_theme.html:29-30` | **CAUSE** (light text intended for dark bg) |
| `opacity` | `1` | — | Not a factor (no opacity < 1 on these elements) |
| `filter` | `none` | — | Not a factor (no `filter`/`grayscale`) |
| `visibility` | `visible` | — | Not a factor |
| `pointer-events` | `auto` | — | Not a factor |
| disabled / `aria-disabled` | absent | — | Not a factor |
| Bootstrap disabled states | absent | — | Not a factor |
| rgba alpha colors | none on these elements | — | Not a factor |
| nav-pill / nav-tab overrides | present in `accessibility_theme.html:115-122` & `ecs_chart_standard.html` but Scheduler tabs are `.ecs-workspace-tab`, not `.nav-link` | — | Not the cause of the fade |
| workspace accessibility overrides | `.ecs-workspace-pane.is-active{background:#fff}` | `mvp_workspace_styles.html:47` | **CAUSE** (white surface under light text) |

**Confirmed:** there is **no** `opacity < 1`, no `filter`, no disabled state, no rgba-alpha dimming.
The fade is purely **light-gray foreground on a white background** created by the DEMO_MODE theme +
white pane interaction.

---

## 5. Scope determination

| Scope | Verdict |
|---|---|
| Scheduler-only | **No.** |
| Operations-wide | **No** (broader than operations). |
| **Global regression (DEMO_MODE)** | **Yes.** |

Reproduced the same light-gray-on-white-pane condition on **every** workspace-pane page in DEMO_MODE:

| Page | Dark theme loaded | White pane | `text-muted` faded on white |
|---|---|---|---|
| Scheduler | ✅ | ✅ | ✅ |
| Enterprise | ✅ | ✅ | ✅ |
| Pan India | ✅ | ✅ | ✅ |
| Reports | ✅ | ✅ | ✅ |
| Trends | ✅ | ✅ | ✅ |
| Evidence Health | ✅ | ✅ | ✅ |

**Responsible selectors (global):**
- `mvp_workspace_styles.html:47` `.ecs-workspace-pane.is-active{ background:#fff }`
- `demo_dark_theme.html:31-32` and `accessibility_theme.html:29-30` `.text-muted{ color:#CBD5E1 } / small.text-muted{ color:#94A3B8 }`

**Impacted modules:** executive_overview, operations, governance, enterprise_grc, frameworks — any
page rendering `workspace_pane` content in DEMO_MODE.
**Risk level of the defect:** **High** (P1, demo-blocking, platform-wide in demo mode).

---

## 6. Why the previous hotfix "passed" but the page still looks bad

The previous hotfix correctly fixed the **tab buttons** (and they verify green). It did **not**
touch the `text-muted` section labels / supporting text inside the white panes, which is the larger
fade the new screenshot shows. The prior fix's success criteria were tab-only and were genuinely
met — the regression is a **different (container/theme) defect** surfacing on the same page.

---

## 7. Proposed smallest safe fix (for approval — NOT applied)

**Goal:** make `.text-muted` / `.text-secondary` / `<small>` helper text and section labels readable
**on the white workspace panes in DEMO_MODE**, without disturbing the dark page chrome, the tabs,
tables (already handled), badges, or non-demo rendering.

**Option A (recommended — smallest, surgical, DEMO_MODE-scoped):**
Add ONE rescue block to `accessibility_theme.html` (already DEMO_MODE-only, loads last among themes)
that flips muted/secondary text to **dark ink** specifically when it sits inside the **white pane**:

```css
/* White workspace panes keep a light surface in demo mode -> force dark ink so
   muted/secondary/section text stays readable (>=4.5:1). Mirrors the existing
   white-table rule at lines 75-77. */
.ecs-workspace-pane .text-muted,
.ecs-workspace-pane .text-secondary,
.ecs-workspace-pane small.text-muted,
.ecs-workspace-pane h6.text-muted{
  color: var(--ax-ink-muted) !important;   /* #475569 → 7.0:1 on #fff */
}
.ecs-workspace-pane h6.text-uppercase{ color: var(--ax-ink2) !important; } /* #1E293B */
```
- **Why safe:** only matches inside `.ecs-workspace-pane`; only loads in DEMO_MODE; uses existing
  `--ax-ink*` tokens; does not touch tabs, dark chrome, tables, badges, or production (non-demo).
- **Scope of fix:** resolves the regression on **all** affected pages at once (correct, since the
  defect is global), with zero impact when DEMO_MODE is off.

**Option B (Scheduler-only, if the team insists on minimal blast radius):**
Same rules but prefixed with `.ecs-cap-scheduler` in `scheduler_styles.html`. Fixes only Scheduler;
leaves Enterprise/Pan India/Reports/Trends/Evidence still faded in demo mode (not recommended given
§5 proves the defect is global).

**Option C (root structural fix):** give the dark theme a real dark pane
(`.ecs-workspace-pane.is-active{ background:var(--demo-card) }` under DEMO_MODE) so the light text is
correct-by-construction. Larger blast radius (re-tests all pane content on dark); defer unless a
full demo-dark redesign is wanted.

**Recommendation:** **Option A.** It is the smallest change that is *correct for the proven scope*
(global DEMO_MODE), is fully DEMO_MODE-scoped, and reuses the existing contrast-engine tokens and
the same pattern already used for white tables.

---

## 8. Deliverable checklist

1. ✅ Why tabs/content are faded: light-gray demo-theme text (`#CBD5E1`/`#94A3B8`) on the unflipped
   white workspace pane (`#fff`) = 1.48:1 / 2.56:1.
2. ✅ Responsible selectors: `.ecs-workspace-pane.is-active{background:#fff}` +
   `.text-muted/small.text-muted{color:#CBD5E1/#94A3B8}` (DEMO_MODE themes).
3. ✅ Scope: **Global DEMO_MODE regression** (not Scheduler-only, not operations-only).
4. ✅ Smallest safe fix: **Option A** (DEMO_MODE-scoped white-pane muted-text rescue).
5. ✅ No code committed.
