# P1 Demo Hotfix — Evidence Rejection Reason Visibility

**Location:** Main Dashboard → Evidence tab → Evidence Rejections table
**Route:** `/dashboard?role=owner` (also `role=auditor`)
**Status:** Fixed (dashboard-only, surgical). No shared component modified.

---

## Root Cause

The rejection reason **data is fully present** in the row payload — it is a complete sentence,
not a single character. The "E / v…" appearance was pure **CSS/layout truncation**, caused by
two compounding effects, neither of which is a data problem:

1. **Borrowed shared column widths.** The table reused the shared 7-column risk-table width
   classes from `modules/shared/templates/partials/ecs_platform_ui.html`:

   ```css
   .ecs-risk-table th, .ecs-risk-table td { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
   .ecs-risk-table .col-app { width: 18%; }   /* Reason borrowed this */
   .ecs-risk-table .col-control { width: 28%; }
   ```

   Applied to this **4-column** table (Framework / Control / Reason / Rejected By), the fixed
   `col-*` percentages did not balance and the Reason cell (`col-app`) was squeezed to
   **~21–24px wide** → the long sentence wrapped/clipped to roughly one character per line,
   reading as `E` / `v` …

2. **Shared executive-table enhancer added a truncation "View" button.** The shared script
   `modules/shared/templates/partials/ecs_executive_table_system.html` auto-enhances tables and,
   for any leaf cell with > 80 characters, adds `.ecs-cell-truncate` plus a "View" toggle,
   reinforcing the clipped look.

**Measured before (live DOM):** Reason cell `width = 24px`, full text present
(`"Evidence package incomplete for Biometric Data Minimization: reviewer requires updated
production artefact and signed attestation."`), `title` attribute absent.

### Does a "rejection detail modal" exist?

No. The Evidence Rejections table on this dashboard has **no detail modal and no row
expand** — rows are plain `<tr><td>…</td></tr>`. The only modal on the page is the unrelated
Evidence Upload modal. Because the full reason is already visible in the row once the column is
readable, no new modal was introduced (introducing one would exceed the surgical scope). The
"Modal displays rejection reason if available" criterion is therefore N/A — there is no detail
modal for this table.

### Where the data comes from (for reference)

- Context key: `rejected_controls` → `app/main.py` `dashboard()` (`ctx["rejected_controls"]`).
- Structure: `ecs_state.rejected_controls[key] = { "reason": <full sentence>, "rejected_by": …, "rejected_at": …, "internal": … }`.
- Seeded reason text:
  `modules/frameworks/engines/framework_catalog.py::seed_workflow_targets()` →
  `"Evidence package incomplete for <control>: reviewer requires updated production artefact and signed attestation."`
  (applied in `modules/executive_overview/engines/demo_seed.py`).

---

## Files Changed

**One file only:** `modules/executive_overview/templates/dashboard.html`

1. **Table markup** (Evidence Rejections table):
   - Added a feature-scoped class `ecs-rejections-table` to the `<table>`.
   - Replaced the borrowed shared width classes `col-fw / col-control / col-app / col-status`
     on the headers with feature-scoped `rej-col-fw / rej-col-control / rej-col-reason / rej-col-by`
     (so the shared `.ecs-risk-table .col-app{18%}` rule no longer squeezes the Reason column).
   - Wrapped the reason text in `<span class="rej-reason-text">…</span>` and added a
     `title="{{ info.reason }}"` tooltip on the cell. The `<span>` gives the cell a child
     element, which makes the shared exec-table enhancer **skip** it (it only enhances leaf
     cells with no children), removing the "View" truncation button without touching the
     shared script.

2. **Scoped `<style>` block** (added in `<head>`, after the theme include, so it wins):

   ```css
   .ecs-rejections-table { table-layout: fixed; width: 100%; }
   .ecs-rejections-table .rej-col-fw      { width: 16%; }
   .ecs-rejections-table .rej-col-control { width: 26%; }
   .ecs-rejections-table .rej-col-reason  { width: 42%; }
   .ecs-rejections-table .rej-col-by      { width: 16%; }
   .ecs-rejections-table td.rej-reason-cell {
     white-space: normal; overflow: visible; text-overflow: clip;
     word-break: break-word; overflow-wrap: anywhere; line-height: 1.35;
   }
   .ecs-rejections-table td, .ecs-rejections-table th { vertical-align: top; }
   ```

All selectors are prefixed with `.ecs-rejections-table`, a class used only by this one table on
this one page (verified: no other file references `ecs-rejections-table` / `rej-*`).

---

## Before

| Property | Value |
|---|---|
| Reason cell width | **~24px** |
| Rendering | one character per line (`E` / `v` …) — unreadable |
| Tooltip | none |
| Reason data | present (full sentence) — confirmed in payload |
| Shared "View" truncation button | present |

## After

| Property | Value |
|---|---|
| Reason cell width | **~238px** (42% of a 1137px table) |
| Rendering | full sentence, wrapped across ~3 lines, fully visible |
| Tooltip | `title` shows the complete reason on hover |
| Table columns | Framework / Control / Reason / Rejected By (layout preserved) |
| Shared "View" truncation button | gone (cell now has a child span → enhancer skips it) |

Screenshot: `nav_audit/a11y_shots/evidence_rejections_after.png`

---

## Validation

| Check | Result |
|---|---|
| Reason column readable | ✅ full text, wrapped, 238px wide |
| Tooltip shows full reason | ✅ `title` present |
| Table still paginates | ✅ pager subsystem intact (10 rejected rows → single page; page-size control present) |
| Sorting still works | ✅ unchanged — no sort markup was touched |
| Modal still opens | ✅ Evidence Upload modal still present/renders |
| Other dashboards unaffected | ✅ `/dashboard` owner/auditor/cio all return 200 |
| No shared component modified | ✅ only `dashboard.html` changed; `ecs_platform_ui.html`, exec-table enhancer, modal framework untouched |
| `ecs-rejections-table` / `rej-*` scope | ✅ exist only in `dashboard.html` |

---

## Risk Assessment

**Risk: Low. Surgical, dashboard-only.**

- Change is confined to a single feature template (`dashboard.html`) with selectors scoped to a
  class (`ecs-rejections-table`) that exists nowhere else.
- No shared CSS, no shared table renderer, no exec-table enhancer, no modal framework, no
  accessibility/chart/nav code was modified.
- The `<span>` wrapper is a no-op for data and only opts this cell out of the shared >80-char
  truncation enhancer via that enhancer's own existing rule (leaf-cell-only).
- `table-layout: fixed` is applied only to this table, so other tables' auto layout is unchanged.
- No regression to pagination, sorting, or modal behavior observed.

No shared-component impact and no medium/high regression risk was found, so the fix was applied
(rather than stopping to report).

---

## Success Criteria

| Criterion | Met |
|---|---|
| Reason column displays readable content | ✅ |
| Modal displays rejection reason if available | N/A — no detail modal exists for this table; full reason is visible inline + tooltip |
| No other dashboard behavior changes | ✅ |
