# Live Root Cause — Scheduler "Washed Out" Text (Cache Excluded)

**Date:** 2026-06-16
**Evidence source:** the **live running ECS server** on `http://127.0.0.1:8000` — i.e. the exact bytes
Chrome receives (`GET /mvp/scheduler?role=cio&user=cio@bank.com`, `DEMO_MODE=true`, 739,561 bytes).
Cache is excluded by construction: this is a fresh server response, and the user already cleared
Chrome cache + cookies and reloaded.
**Constraint honored:** no code modified, no fix proposed, no cache theories.

---

## 0. What is actually faded (corrects the scope)

The faded elements in Chrome are the **section labels and supporting text inside the active tab
pane**, e.g. `<h6 class="small text-muted text-uppercase">`. The **tab buttons themselves are NOT
the faded elements** — they render dark-on-light / white-on-blue and pass AA (proven in §4 and in
`scheduler_hotfix_verification.md`). The "tabs look faded" impression is the *adjacent* muted text
washing out, exactly as the screenshot evidence (labels, headers, supporting text all faded) shows.

> **Build mismatch note (factual):** the live server renders the tab set
> **Overview · App Scans · Cron Timeline · Run History · Failures · Tomorrow Plan · Integrations**.
> The ticket lists "**Validation Failures**" instead of "Tomorrow Plan." That label does **not**
> exist anywhere in the live page (`grep` = 0 hits). This means the user's screenshot is from a
> **different build/branch** than this working tree. It does not change the root cause of the fade,
> but it is recorded as live evidence.

---

## 1. Exact DOM elements (live server render, scripts excluded)

### Tab buttons
```html
<nav class="ecs-workspace-tabs mb-2" role="tablist" aria-label="Module sections">
  <button type="button" role="tab" class="ecs-workspace-tab is-active" aria-selected="true"  data-workspace-tab="overview">Overview</button>
  <button type="button" role="tab" class="ecs-workspace-tab"           aria-selected="false" data-workspace-tab="applications">App Scans</button>
  <button type="button" role="tab" class="ecs-workspace-tab"           aria-selected="false" data-workspace-tab="cron">Cron Timeline</button>
  <button type="button" role="tab" class="ecs-workspace-tab"           aria-selected="false" data-workspace-tab="history">Run History</button>
  <button type="button" role="tab" class="ecs-workspace-tab"           aria-selected="false" data-workspace-tab="failures">Failures</button>
  <button type="button" role="tab" class="ecs-workspace-tab"           aria-selected="false" data-workspace-tab="upcoming">Tomorrow Plan</button>
  <button type="button" role="tab" class="ecs-workspace-tab"           aria-selected="false" data-workspace-tab="integrations">Integrations</button>
</nav>
```
- File: `modules/operations/templates/mvp_scheduler.html:32` → macro `workspace_tab_nav`
  (`modules/shared/templates/partials/mvp_workspace_macros.html`).

### The actually-faded text (section labels) — live DOM
```html
<div class="ecs-workspace-pane is-active" ...>
  <h6 class="small text-muted text-uppercase mb-1">Yesterday Scan Summary</h6>
  <h6 class="small text-muted text-uppercase mb-1 mt-2">Daily Cron Execution — Yesterday</h6>
  <h6 class="small text-muted text-uppercase mb-1 mt-2">Compliance Impact From Scheduler</h6>
  <h6 class="small text-muted text-uppercase mb-1">Application Scan Preview</h6>
  ...
```
- The pane element carries **`class="ecs-workspace-pane is-active"`** — **no `bg-white`/`bg-light`
  class** (this fact is decisive; see §4c).

---

## 2. Captured rendered HTML
- HTTP 200, 739,561 bytes from the live server.
- `EXECUTIVE DEMO DARK THEME` present: **yes** (DEMO_MODE active).
- `ECS UNIVERSAL CONTRAST ENGINE` (accessibility_theme) present: **yes**.
- Scheduler scoped tab fix present: **yes**.
- Old broken active-tab wash (`#dbeafe` in a tab rule): **none**.

---

## 3. Exact winning CSS for the faded text

### 3a. `color`
For `<h6 class="small text-muted">` the live page contains these competing rules (load order):

| File:line | Selector | Declaration | Token value |
|---|---|---|---|
| `demo_dark_theme.html:31-32` | `p, span, li, dd, dt, label, small, .text-muted, .text-secondary, .lead` | `color:var(--demo-text2)!important` | `#CBD5E1` |
| `accessibility_theme.html:29` | `.text-muted, .text-secondary` | `color:var(--ax-text2)!important` | `#CBD5E1` |
| **`accessibility_theme.html:30`** | **`small.text-muted, .small.text-muted`** | **`color:var(--ax-muted)!important`** | **`#94A3B8`** |
| `accessibility_theme.html:75-77` | `.table .text-muted, .table small.text-muted, …` | `color:var(--ax-ink-muted)!important` | `#475569` (dark) — **only inside `.table`** |

**WINNER for `h6.small.text-muted`:** `accessibility_theme.html:30`
`small.text-muted, .small.text-muted { color:var(--ax-muted)!important; }` → **`#94A3B8`**.
It wins because: (a) it carries `!important`, (b) it is more specific for `small.text-muted` than the
generic `.text-muted` rules, and (c) it is the last muted rule in source order. The dark-rescue rule
at lines 75-77 does **not** apply because it is scoped under `.table`, and these `<h6>` labels are
direct children of the pane, not inside a table.
(Non-`small` `.text-muted` text resolves to `#CBD5E1` via `:29` / demo `:31`.)

### 3b. `background-color` (the surface under that text)
| File:line | Selector | Declaration |
|---|---|---|
| **`mvp_workspace_styles.html:62-64`** | **`.ecs-workspace-pane.is-active`** | **`background: #fff;`** |

This is the surface the faded labels sit on: **white**.

### 3c. `opacity`
- No `opacity < 1` rule applies to the tabs, the pane, or the section labels.
- Page-wide scan (scripts stripped): 18 `opacity`/`filter` rules exist, **all** on unrelated elements
  (chart bars, badges, decorative `↗`, drag-resize handles, hover `transform`/`brightness`). None
  match `.ecs-workspace-tab`, `.ecs-workspace-pane`, `.ecs-workspace-main`, or the `h6` labels.
- The tab `:disabled` rule explicitly sets `opacity: 1`.
- **Computed opacity of the faded text and its ancestors = 1.**

### 3d. `filter` / `mix-blend-mode`
- No `filter` (other than `none`) applies to tabs/panes/labels.
- `mix-blend-mode`: **0 occurrences** anywhere in the page.

---

## 4. Is the scheduler CSS applied / what overrides it?

### 4a. Scheduler tab CSS — applied and winning (tabs are fine)
| Tab state | Winning rule (file:line) | Specificity | Computed | Contrast |
|---|---|---|---|---|
| Inactive | `scheduler_styles.html` `.ecs-cap-scheduler .ecs-workspace-tab` | (0,2,0) > global (0,1,0) | `#0F172A` on `#E2E8F0` | 14.48:1 ✅ |
| Active | `scheduler_styles.html` `.ecs-cap-scheduler .ecs-workspace-tab.is-active` | (0,3,0), later in source than global | `#FFFFFF` on `#2563EB` | 5.17:1 ✅ |

So **another selector does not override the tabs**; the scheduler fix wins for the buttons.

### 4b. What overrides the SECTION-LABEL text → DEMO_MODE
The fade is on the muted **text**, overridden by **DEMO_MODE-only** stylesheets:
- Gated at `mvp_styles.html:8-9`:
  ```jinja
  {% if demo_mode|default(false) %}{% include "partials/demo_dark_theme.html" %}{% endif %}
  {% if demo_mode|default(false) %}{% include "partials/accessibility_theme.html" %}{% endif %}
  ```
- These set muted text to light gray (`#94A3B8` / `#CBD5E1`) — values designed for a **dark** page.

### 4c. Why the parent container does NOT save it (the crux)
The DEMO_MODE dark theme only repaints surfaces that carry a **class**:
`demo_dark_theme.html:20` → `.bg-light, .bg-white, .card.bg-white, .bg-body, .bg-body-tertiary { background:var(--demo-card)!important; }`.
The pane element is `<div class="ecs-workspace-pane is-active">` — it has **no** `.bg-white`/`.bg-light`
class; its white comes from the **CSS rule** at `mvp_workspace_styles.html:62-64`. Therefore the
dark-theme background-flip **never matches the pane**, and the pane stays **white** while the text is
**light gray**.

### 4d. Bootstrap
Bootstrap's own `.text-muted` (`#6c757d`-ish) is **overridden** by the DEMO_MODE `!important` rules
above; Bootstrap is not the winner and not the cause.

---

## 5. Computed result (the proof)

| Element | Winning color (file:line) | Background (file:line) | Contrast | WCAG AA |
|---|---|---|---|---|
| `h6.small.text-muted` section label | `#94A3B8` (`accessibility_theme.html:30`) | `#fff` (`mvp_workspace_styles.html:62-64`) | **2.56:1** | ❌ |
| `.text-muted` supporting text | `#CBD5E1` (`accessibility_theme.html:29` / `demo_dark_theme.html:31-32`) | `#fff` | **1.48:1** | ❌ |
| (Same `#94A3B8` on the *intended* dark bg `#0B1220`) | — | `#0B1220` | 7.30:1 | ✅ (proves the colors assume a dark bg) |
| Active tab button | `#FFFFFF` (`scheduler_styles.html`) | `#2563EB` | 5.17:1 | ✅ |
| Inactive tab button | `#0F172A` | `#E2E8F0` | 14.48:1 | ✅ |

---

## 6. The exact selector causing the appearance in Chrome

**`small.text-muted, .small.text-muted { color: var(--ax-muted)!important; }`** —
file `modules/shared/templates/partials/accessibility_theme.html:30` (`--ax-muted = #94A3B8`,
line 18) — **rendering on the white pane** produced by
**`.ecs-workspace-pane.is-active { background:#fff }`** —
file `modules/shared/templates/partials/mvp_workspace_styles.html:62-64`.

(For non-`small` muted text the partner selector is `.text-muted, .text-secondary { color:var(--ax-text2 / --demo-text2)!important }` → `#CBD5E1`, `accessibility_theme.html:29` / `demo_dark_theme.html:31-32`.)

**Selector chain:**
`body.ecs-cap-scheduler` (DEMO_MODE → demo themes loaded) →
`.ecs-workspace-main` → `.ecs-workspace-pane.is-active` (**background:#fff**, unflipped because it has
no `.bg-white` class) → `h6.small.text-muted` (**color:#94A3B8 !important** from accessibility_theme).

---

## 7. Why Chrome still renders the issue after cache/cookie purge

Because it is **not a cache artifact** — it is the **live, deterministic CSS cascade** in the bytes
the server sends on every request:

1. DEMO_MODE is active, so `demo_dark_theme.html` + `accessibility_theme.html` are **included on
   every fresh response** (`mvp_styles.html:8-9`). A cache purge re-downloads them unchanged.
2. Those stylesheets set muted/secondary/`small` text to light gray (`#94A3B8` / `#CBD5E1`) with
   `!important` — values meant for a **dark** background.
3. The active workspace pane is **white** (`mvp_workspace_styles.html:62-64`) and **cannot be flipped
   dark** by the demo theme because the pane lacks a `.bg-white`/`.bg-light` class
   (`demo_dark_theme.html:20`).
4. Net: **light-gray text on white = 1.48:1 / 2.56:1**, recomputed identically by Chrome on every
   load. Clearing cache/cookies cannot change a live `!important` CSS rule.

There is **no** `opacity`, `filter`, `mix-blend-mode`, disabled state, or rgba-alpha involved — the
fade is purely the foreground/background color pairing produced by the DEMO_MODE theme over the
white pane.

---

## 8. Search results (requested tokens, live page)

| Token | Finding |
|---|---|
| `opacity:` | 18 rules, all on unrelated elements; none on tabs/panes/labels; tab `:disabled` = `opacity:1`. |
| `filter:` | only on chart hover/`brightness` micro-interactions; none on the faded elements. |
| `mix-blend-mode:` | **0 occurrences.** |
| `color:` (muted) | winners: `#94A3B8` (`accessibility_theme.html:30`), `#CBD5E1` (`:29` / `demo_dark_theme.html:31-32`). |
| `text-muted` | recolored light-gray by DEMO_MODE themes; white-pane labels not rescued (rescue is `.table`-scoped, `:75-77`). |
| `text-secondary` | same recolor as `.text-muted` (`accessibility_theme.html:29`). |

**Root cause proven. No code modified. No fix proposed (per instructions).**
