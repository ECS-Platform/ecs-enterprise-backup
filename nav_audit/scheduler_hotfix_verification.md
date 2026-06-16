# Scheduler Hotfix Verification — Is "Stale Browser Cache" a Valid Explanation?

**Date:** 2026-06-16
**Method:** Server-rendered HTML captured from `/mvp/scheduler?role=cio&user=cio@bank.com`
(`DEMO_MODE=true`), CSS cascade resolved by specificity + source order, contrast computed with the
repo's `ecs_chart_standards.js`. **No code changed.**

---

## Verdict (up front)

**Stale browser cache is NOT a valid explanation for the faded *content* in the screenshot, and is
only a *possible* explanation for the *tabs* — but the evidence shows the tab fix is already active
and winning.**

Two distinct things must not be conflated:

| Element | Is the fix present & winning? | Faded? | Cache a valid cause? |
|---|---|---|---|
| **Tab buttons** (active/inactive) | **Yes — scoped fix wins, WCAG AA** | No (when fresh CSS is loaded) | Only if the browser served pre-fix cached HTML; the *current* server output is correct. |
| **Section labels / table headers / supporting text** | n/a (fix never targeted them) | **Yes (proven 1.48:1 / 2.56:1)** | **No.** Reproduces on a fresh fetch; it's a live DEMO_MODE theme defect. |

So: cache is at best a partial story for the tabs and **definitely not** the explanation for the
broader "everything faded" symptom. The real, fresh-render defect is the DEMO_MODE dark-theme text
on white workspace panes (see `scheduler_tab_root_cause.md`).

---

## 1. Scheduler page source opened

Rendered via FastAPI TestClient (bypasses all browser caching → this is the **fresh server truth**):
- `GET /mvp/scheduler` → **HTTP 200**, 737,361 bytes.
- `<body class="bg-light ecs-cap-scheduler">` confirmed.

## 2. Is the scheduler-specific override actually in the rendered HTML?

**YES.** The scoped block is present in the served HTML:

```
[2] Scheduler scoped override present in rendered HTML: True
    body carries ecs-cap-scheduler: True
```

Rendered scoped rules (verbatim from the page, with byte offsets):

```
@315990  .ecs-cap-scheduler .ecs-workspace-tab { background:#E2E8F0; color:#0F172A; border:1px solid #CBD5E1; font-weight:600; }
@316122  .ecs-cap-scheduler .ecs-workspace-tab:hover { background:#1D4ED8; border-color:#1D4ED8; color:#FFFFFF; }
@316345  .ecs-cap-scheduler .ecs-workspace-tab.is-active,
         .ecs-cap-scheduler .ecs-workspace-tab[aria-selected="true"] { background:#2563EB; border-color:#2563EB; color:#FFFFFF; font-weight:700; }
@316544  .ecs-cap-scheduler .ecs-workspace-tab.is-active:hover { background:#1D4ED8; border-color:#1D4ED8; }
```

## 3. Computed styles for the tabs (resolved cascade)

All rules in the served page that can color `.ecs-workspace-tab`, in load order:

| Offset | Selector | Specificity (id,class,elem) | color / background |
|---|---|---|---|
| 287750 | `.ecs-workspace-tab` | (0,1,0) | `#0F172A` / `#E2E8F0` |
| 288201 | `.ecs-workspace-tab.is-active, [aria-selected="true"]` | (0,3,0) | `#FFFFFF` / `#2563EB` |
| **315990** | `.ecs-cap-scheduler .ecs-workspace-tab` | **(0,2,0)** | `#0F172A` / `#E2E8F0` |
| **316345** | `.ecs-cap-scheduler .ecs-workspace-tab.is-active, …[aria-selected="true"]` | **(0,3,0)** | `#FFFFFF` / `#2563EB` |

**Computed (winning) values:**

| Tab state | Effective color | Effective background |
|---|---|---|
| **Inactive** | `#0F172A` | `#E2E8F0` |
| **Active** | `#FFFFFF` | `#2563EB` |

## 4. The CSS rule that wins

- **Inactive tab → `@315990 .ecs-cap-scheduler .ecs-workspace-tab`.**
  Specificity (0,2,0) beats the global `.ecs-workspace-tab` (0,1,0). **Scheduler fix wins.**
- **Active tab → `@316345 .ecs-cap-scheduler .ecs-workspace-tab.is-active`.**
  Specificity (0,3,0) **ties** the global active rule (0,3,0); the tie is broken by **source order**
  — the scheduler rule appears later (offset 316345 > 288201), so it wins. **Scheduler fix wins.**

**Contrast of the winning rules (WCAG AA ≥ 4.5:1):**

| State | Pair | Ratio | AA |
|---|---|---|---|
| Inactive | `#0F172A` on `#E2E8F0` | **14.48:1** | ✅ |
| Active | `#FFFFFF` on `#2563EB` | **5.17:1** | ✅ |

The tabs, on a fresh server render, are **fully readable and standards-compliant**.

## 5. Parent container opacity / filter

Checked `.ecs-workspace-main`, `.ecs-workspace-pane`, `.ecs-workspace-tabs`, `.ecs-cap-scheduler`,
`.container-fluid` for `opacity`/`filter`:

```
.ecs-workspace-main : no opacity/filter rule
.ecs-workspace-tabs : no opacity/filter rule
.ecs-cap-scheduler  : no opacity/filter rule
.container-fluid    : no opacity/filter rule
.ecs-workspace-pane : (only a JavaScript querySelectorAll line — NOT a CSS rule)
```

Full-page scan (scripts stripped) found 18 `opacity<1`/`filter` rules — **all** on unrelated
elements (chart bars, badges, decorative ↗ arrows, drag-resize handles, hover `transform`/
`brightness` micro-interactions). **None** target tabs, panes, or workspace content ancestors. The
tab disabled rule explicitly sets `opacity: 1`.

**Conclusion:** there is **no opacity/filter dimming** on the tabs or their containers.

## 6. Why the screenshot can still show "faded" if the fix is active

Because the screenshot's fade is **two separate phenomena**, and only one is even cache-eligible:

1. **The tabs:** the fresh server output proves the scoped fix is present and wins (§2–§4). If a
   browser showed faded *tabs*, the only way that happens with this server output is the browser
   rendering an **older cached copy of the inline-CSS HTML** (pre-fix). That is *plausible* but is a
   **client cache artifact, not a current code defect** — and ECS already sends
   `Cache-Control: no-cache` on HTML (`app/main.py` `_no_cache_html`), so even that should clear on
   reload. A hard refresh (Cmd/Ctrl-Shift-R) resolves any such stale tab rendering.

2. **The surrounding content (section labels, table headers, supporting text):** this is **NOT
   cache** and reproduces on a brand-new fetch. In DEMO_MODE the dark theme repaints
   `.text-muted → #CBD5E1` and `small.text-muted → #94A3B8`, but the active workspace pane keeps a
   **white** background (`.ecs-workspace-pane.is-active { background:#fff }`, which the dark theme's
   `.bg-white`/`.bg-light` selectors cannot match). Result: **light-gray text on white** —
   `#CBD5E1` on `#fff` = **1.48:1**, `#94A3B8` on `#fff` = **2.56:1**. Faded, live, every load.

So the dominant, demo-blocking fade is a **live theme/container defect**, independent of cache.

---

## Whether browser cache is a valid explanation

| Claim | Verdict | Evidence |
|---|---|---|
| "Faded **tabs** are caused by stale cache" | **Possible but unproven, and not a current-code issue** | Fresh server render shows the scoped fix present and winning (14.48:1 / 5.17:1). Any faded tab would require the browser to render pre-fix cached HTML; `no-cache` headers + hard refresh resolve it. |
| "Faded **content** (labels/headers/text) is caused by stale cache" | **DISPROVEN** | Reproduces on a fresh, uncached server fetch. Caused by DEMO_MODE light-gray text on the white pane (1.48:1 / 2.56:1). |
| "Overall screenshot fade = stale cache" | **DISPROVEN as the root cause** | The largest, demo-blocking part of the fade is a live CSS interaction, not cache. |

**Bottom line:** Cache is *not* a valid explanation for the reported defect. The tab fix is active
and correct; the persistent fade is the **DEMO_MODE dark-theme × white-pane** conflict documented in
`nav_audit/scheduler_tab_root_cause.md`. Recommended fix remains **Option A** there (DEMO_MODE-scoped
white-pane muted-text rescue). No code changed in this verification.
