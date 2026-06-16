# P1 HOTFIX — Align Scheduler Visuals with Operations Onboarding

**Page:** Operations → Scheduler (`/mvp/scheduler`)
**Source of truth:** Operations → Onboarding (`/mvp/onboarding`)
**Status:** Fixed and verified (Scheduler-only, no global changes)

---

## 1. Root Cause

The Scheduler summary tiles ("Successful Runs", "Failed Runs", "Avg Runtime",
"Records Processed", "Applications Affected", "Frameworks Affected") render from the
shared macro `execution_engine_panel.html`:

```html
<div class="ecs-sched-card"><strong>{{ ... }}</strong><span>Successful Runs</span></div>
```

- The **label** is a `<span>`.
- The **value** is a `<strong>`.
- The tile is `.ecs-sched-card` with a **light** `#f8fafc` background (a CSS rule, no `bg-white`/`bg-light` class).

In DEMO_MODE the dark theme (`demo_dark_theme.html`) applies, with `!important`:

```css
p, span, li, dd, dt, label, small, .text-muted, .text-secondary, .lead {
  color: var(--demo-text2) !important;   /* #CBD5E1 light gray */
}
```

Because the card label is a `<span>`, this rule **repaints the Scheduler label to `#CBD5E1`**.
Since `.ecs-sched-card` keeps its light `#f8fafc` surface (the dark theme only flips
elements carrying `.bg-white`/`.bg-light`, which this tile does **not** have), the result is:

| Element | Color | Background | Contrast | Result |
|---|---|---|---|---|
| Scheduler card label (`span`, demo-forced) | `#CBD5E1` | `#f8fafc` | **1.42:1** | FAIL — washed out |

### Why Onboarding does NOT have this problem (the difference)

The Onboarding KPI tile (the visual source of truth) labels its text with a **dedicated
class on a `<div>`**, not a `<span>` and not `.text-muted`:

```html
<div class="ecs-onboard-kpi-val">…</div>
<div class="ecs-onboard-kpi-lbl">…</div>
```

```css
/* mvp_capability_styles.html */
.ecs-onboard-kpi     { background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:0.65rem; }
.ecs-onboard-kpi-val { font-size:1.25rem; font-weight:700; line-height:1.1; }
.ecs-onboard-kpi-lbl { font-size:0.68rem; color:#64748b; text-transform:uppercase; letter-spacing:0.03em; }
```

The demo `span { color:#CBD5E1 !important }` rule **never matches** `.ecs-onboard-kpi-lbl`
(it is a `<div>`, not a `<span>`, and not `.text-muted`), so the Onboarding label keeps
`#64748b` → **4.55:1 (AA pass)** on the same `#f8fafc` tile.

**Conclusion:** Scheduler differs from Onboarding only because Scheduler labels are
`<span>` (caught by the global demo override) while Onboarding labels are dedicated
`.ecs-onboard-kpi-lbl` `<div>`s (not caught). Values (`<strong>` / `.ecs-onboard-kpi-val`)
were already readable on both.

---

## 2. Fix

Replicated the **exact Onboarding tile treatment** onto the Scheduler cards, scoped
strictly under the Scheduler page body class `.ecs-cap-scheduler`. No new design tokens
were invented — colors, weights, sizes, radius, and padding are copied from
`.ecs-onboard-kpi` / `-val` / `-lbl`.

**File changed:** `modules/operations/templates/partials/scheduler_styles.html`
(Scheduler-only partial; included **only** by `mvp_scheduler.html`).

**Lines added (after the existing Scheduler tab block):**

```css
.ecs-cap-scheduler .ecs-sched-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;            /* match .ecs-onboard-kpi */
  padding: 0.65rem;              /* match .ecs-onboard-kpi */
}
.ecs-cap-scheduler .ecs-sched-card strong {
  color: #1e293b !important;     /* match .ecs-onboard-kpi-val ink, bold value */
  font-weight: 700 !important;
}
.ecs-cap-scheduler .ecs-sched-card span {
  color: #64748b !important;     /* match .ecs-onboard-kpi-lbl label ink; overrides demo span light-gray */
}
```

### Selectors changed

| Selector | Property | Before (effective) | After |
|---|---|---|---|
| `.ecs-cap-scheduler .ecs-sched-card` | radius / padding | 6px / 0.35rem 0.45rem | 8px / 0.65rem (match Onboarding) |
| `.ecs-cap-scheduler .ecs-sched-card strong` | color / weight | `#1e293b` / default | `#1e293b` / 700 (match `ecs-onboard-kpi-val`) |
| `.ecs-cap-scheduler .ecs-sched-card span` | color | `#CBD5E1` (demo-forced) | `#64748b` (match `ecs-onboard-kpi-lbl`) |

### Why this wins the cascade

`.ecs-cap-scheduler .ecs-sched-card span` has specificity **(0,2,1)** and carries
`!important` and appears **later** in source than the demo rule `p, span, … {…!important}`
(specificity **(0,1,1)**, also `!important`). Higher specificity + later source → the
Scheduler-scoped rule wins deterministically.

---

## 3. Validation

### Live cascade (rendered HTML, load order)

```
[demo: p, span, li, dd, dt, label, small, .text…] -> color:var(--demo-text2)!important;   (loses)
[.ecs-sched-card span]                              -> font-size; text-transform; …          (no color)
[.ecs-cap-scheduler .ecs-sched-card span]          -> color:#64748b !important;  ✅ WINNER
```

### Real Chromium computed styles (`/mvp/scheduler`, DEMO_MODE)

| Element | Computed value |
|---|---|
| `.ecs-sched-card span` color | `rgb(100,116,139)` = **#64748b** |
| `.ecs-sched-card strong` color | `rgb(30,41,59)` = **#1e293b** |
| `.ecs-sched-card` background | `rgb(248,250,252)` = **#f8fafc** |
| `.ecs-sched-card span` opacity / filter | **1 / none** (no fade) |

### Contrast (WCAG AA, normal text ≥ 4.5:1)

| Element | Pair | Ratio | AA |
|---|---|---|---|
| Card label (after) | `#64748b` on `#f8fafc` | **4.55:1** | PASS |
| Card value (after) | `#1e293b` on `#f8fafc` | **13.98:1** | PASS |
| Card label (before) | `#CBD5E1` on `#f8fafc` | 1.42:1 | (was FAIL) |

### Section readability checklist (verified)

| Section | Source | State |
|---|---|---|
| Last Run | `execution_engine_panel` (`.text-muted` on flipped dark `bg-white` card) | Readable (11.95:1) |
| Run Status | same | Readable |
| Records Processed (panel row) | same | Readable |
| Execution Duration | same | Readable |
| Successful Runs card | `.ecs-sched-card` | **Fixed → 4.55:1 label / 13.98:1 value** |
| Failed Runs card | `.ecs-sched-card` | **Fixed** |
| Applications Affected card | `.ecs-sched-card` | **Fixed** |
| Frameworks Affected card | `.ecs-sched-card` | **Fixed** |

> Note: the "Last Run / Run Status / Records Processed / Execution Duration" metadata row
> (also from `execution_engine_panel`) was already readable in DEMO_MODE — that panel carries
> `bg-white`, which the dark theme flips to a dark card, so its `.text-muted` labels render as
> light-gray on dark (11.95:1). Only the `.ecs-sched-card` summary tiles were faded, and those
> are now fixed.

### Screenshots

- After (summary cards): `nav_audit/a11y_shots/scheduler_after_cards.png`
- After (page region): `nav_audit/a11y_shots/scheduler_after_full.png`

### Proof the change is Scheduler-only

The new rule is present on Scheduler and **absent** from every other audited page
(rendered HTML inspection):

| Page | HTTP | `.ecs-cap-scheduler .ecs-sched-card` present? |
|---|---|---|
| Scheduler | 200 | **Yes** |
| Onboarding | 200 | No |
| Enterprise | 200 | No |
| Trends | 200 | No |
| Reports | 200 | No |
| Integrations | 200 | No |

The edit lives only in `scheduler_styles.html`, which is included exclusively by
`mvp_scheduler.html`, and every selector is prefixed with the Scheduler body class
`.ecs-cap-scheduler`.

### Test suite

`tests/test_chart_accessibility_standard.py` → **51 passed**.

---

## 4. Regression Audit (other pages — reported, NOT modified)

The underlying mechanism (DEMO_MODE `span/.text-muted → #CBD5E1 !important` painting onto a
light `#f8fafc`/`#fff` surface that the dark theme does not flip) can recur on any module that
puts `<span>` / `.text-muted` labels on a custom light card **without** a `.bg-white`/`.bg-light`
class. Per instructions, these are **reported only, not fixed**:

- Any module using bespoke light stat tiles with `<span>` labels and no Bootstrap bg class is
  a candidate for the same fade in DEMO_MODE.
- Recommended durable fix (separate, scoped task): give such tiles a dedicated label class
  (mirroring `.ecs-onboard-kpi-lbl`) instead of a bare `<span>`, OR have the dark theme flip
  custom light surfaces. **Not actioned here** to honor the "Scheduler-only, no global change"
  constraint.

No other page was changed.

---

## 5. Success Criteria

| Criterion | Result |
|---|---|
| Scheduler matches Onboarding for metric cards/summary | ✅ same tokens/weights/sizes/spacing |
| No new design language | ✅ values copied from `.ecs-onboard-kpi*` |
| No global CSS modifications | ✅ only `scheduler_styles.html`, all `.ecs-cap-scheduler`-scoped |
| No changes outside Scheduler | ✅ verified absent on 5 other pages |
| No global theme change required | ✅ |
