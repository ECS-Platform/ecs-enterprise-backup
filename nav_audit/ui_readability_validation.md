# Phase 8 — Global Accessibility / Readability Validation

All readability fixes were applied in one scoped, DEMO_MODE-only stylesheet
(`modules/shared/templates/partials/demo_dark_theme.html`) using the approved
executive palette. No business logic, routes, ROI calculations, or navigation
changed.

## Executive color standard applied (Phase 2)
| Token | Value |
|---|---|
| Background | #0B1220 |
| Panels | #111827 |
| Cards | #1E293B |
| Primary text | #F8FAFC |
| Secondary text | #CBD5E1 |
| Muted text | #94A3B8 |
| Accent | #38BDF8 |
| Positive | #22C55E |
| Warning | #F59E0B |
| Critical | #EF4444 |

## WCAG AA contrast (computed)
| Combination | Ratio | AA |
|---|---|---|
| #F8FAFC on #0B1220 | 17.89 | PASS |
| #F8FAFC on #1E293B | 13.98 | PASS |
| #CBD5E1 on #0B1220 | 12.61 | PASS |
| #CBD5E1 on #1E293B | 9.85 | PASS |
| #94A3B8 (muted) on #1E293B | 5.71 | PASS |
| #38BDF8 (accent) on #0B1220 | 8.74 | PASS |
| #22C55E (positive) on #1E293B | 6.42 | PASS |
| #F59E0B (warning) on #1E293B | 6.81 | PASS |
| #EF4444 (critical) on #1E293B | 3.89 | PASS (large/UI) |
| #FFFFFF on #EF4444 badge | 3.76 | PASS (large/UI) |

All normal text ≥ 4.5; status colors are used on large/bold metrics and badges
(WCAG large-text / UI-component threshold ≥ 3.0).

## Validation checklist
- WCAG AA contrast — PASS (table above)
- No invisible text — PASS (KPI labels, snapshot labels, section titles now #CBD5E1/#F8FAFC)
- No faded headers — PASS (table headers #F8FAFC on #111827)
- No washed-out tables — PASS (grid lines rgba(255,255,255,0.15), rows #CBD5E1)
- No dark-on-dark — PASS (default navy metric #1e3a8a overridden to #F8FAFC)
- No light-on-light — PASS (white `.demo-*` card backgrounds overridden to #1E293B)

## Coverage
| Metric | Count |
|---|---|
| Pages checked (route families) | /dashboard*, /mvp/*, /framework/*, /mvp/platform/*, /mvp/ai-sdlc/* |
| Components checked | KPI cards, CIO snapshot, Top Risk table, all demo tables, heatmap, app cards, lineage cards, nav tabs, role badges, section titles |
| Issues found | 12 |
| Issues fixed | 12 |

## Components fixed (Phase 3–7)
- **Phase 3 KPI cards** — value `#F8FAFC` weight 700; label `#CBD5E1` weight 500.
- **Phase 4 CIO snapshot** — labels `#CBD5E1`; metrics `#F8FAFC`; success `#22C55E`,
  warning `#F59E0B`, critical `#EF4444`.
- **Phase 5 Top Risk table** — headers `#F8FAFC`, rows `#CBD5E1`, grid lines
  `rgba(255,255,255,0.15)`, app names bold `#F8FAFC`; risk badges retain colors.
- **Phase 6 nav tabs** — inactive `#CBD5E1`, active `#38BDF8` with `#38BDF8` underline.
- **Phase 7 role badges** — background `#1E293B`, text `#F8FAFC`, border
  `rgba(255,255,255,0.15)`.
