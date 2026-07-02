# Phase 1 — UI Contrast Audit

Audited the executive demo surfaces under `/dashboard*`, `/mvp/*`, `/framework/*`,
`/mvp/platform/*`, `/mvp/ai-sdlc/*` while running with `DEMO_MODE=true` (dark page
background `#0B1220`). The global dark theme themed Bootstrap `.card`/`.table`, but
several pages — most visibly `/mvp/demo-overview` — ship **hardcoded light-theme
styles** in their own `<style>` blocks that were never overridden.

## Issues found (before fix)

| # | Location | Class / element | Problem | Severity |
|---|---|---|---|---|
| 1 | demo-overview KPI strip | `.demo-kpi` (`background:#fff`) | White cards island on dark page; bright glare | High |
| 2 | demo-overview KPI label | `.demo-kpi .l` (`#475569`) | Dark-gray label, low contrast on intended dark | High |
| 3 | CIO Executive Snapshot | `.demo-card .border` + `.text-muted` 0.6rem | Labels "nearly invisible" (faded, tiny) | High |
| 4 | CIO Snapshot default metric | inline `#1e3a8a` | Dark navy number on light card → now dark-on-dark | High |
| 5 | Top Risk Applications | `.demo-table thead th` (`#475569` on `#f8fafc`) | Washed-out headers; rows default dark | High |
| 6 | Top Risk Applications | `.demo-table td` | App names not guaranteed light on dark | High |
| 7 | Risk heatmap label column | `.demo-heat-label` (`#f8fafc` bg) | Light label cells on dark grid | Medium |
| 8 | App registry cards | `.demo-app-card` (`#fff`) | White card island; `.meta` `#64748b` faded | Medium |
| 9 | Navigation tabs | `.nav-tabs .nav-link` | Inactive tabs low-contrast; active not accented | Medium |
| 10 | Role badges | `.ecs-user-chip` / `.ecs-role-chip` | Default chip styling low contrast on dark | Medium |
| 11 | Evidence lineage cards | `.lineage-card` (`#f8fafc`) | Light card; `.ev-name` dark text | Low |
| 12 | Section titles | `.demo-section-title` (`#475569`) | Faded headings | Medium |

## Root cause
Per-page `<style>` blocks define `.demo-*` component colors for a light theme.
These have higher specificity than the generic global theme rules, so they survived
the dark theme. Fix = scoped overrides for these exact classes using the approved
executive palette, loaded only under DEMO_MODE (`demo_dark_theme.html`).

All items above are addressed in Phase 2–7 (see `ui_readability_validation.md`).
