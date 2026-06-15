# Phase 1 — Global Color / Theme Audit

Scanned `modules/**/templates/**/*.html` for light-theme utility classes and
Bootstrap defaults that break on the dark executive page (`DEMO_MODE`, bg #0B1220).

## Class usage (occurrences across templates)
| Class / pattern | Occurrences | Risk on dark page |
|---|---|---|
| `text-muted` | 782 | Bootstrap muted = #6c757d → low contrast on dark |
| `text-secondary` | 4 | similar muted gray |
| `text-light` | 0 | n/a |
| `bg-light` | ~110 (mostly `<body class="bg-light">`) | light page/surface island |
| `bg-white` | ~90 | white card/island on dark page |
| `table-light` | present in several | light thead on dark page |
| Bootstrap default `.table` | ~600 across ~95 templates | default colors inherit page; rows can become dark-on-dark or light-on-light |

## Hotspot pages (named in the request)
- `mvp_enterprise.html` — Enterprise Overview + Open Gaps tab + Analytics (`table` ×8, `bg-light`).
- `mvp_governance_analytics.html` — Governance Analytics timeline/event table (`table` ×10).
- `mvp_integrations.html` / `mvp_integrations_hub.html` / `platform_integration_health.html` — connector charts + dependency matrix.
- `mvp_audit_prep.html` — `table` ×29 (heavy).
- `mvp_demo_overview.html`, `mvp_roi_center.html` — already themed in prior passes.

## Strategy
A single global helper stylesheet (`accessibility_theme.html`), included last in
`mvp_styles.html` under `DEMO_MODE`, enforces:
- Phase 2 universal contrast law (light text on dark surfaces, dark text on light surfaces).
- Phase 3 table standard (dark header / white rows / dark text / striped / hover).
- Phase 4 chart label standard (≥14px, opaque, panel-aware color).
- Phase 5 KPI standard (auto light/dark by card background).
This avoids editing 95 templates and touches no logic/routes/data.
