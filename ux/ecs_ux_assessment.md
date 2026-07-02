# ECS — UX Assessment

**Lens:** Principal UX Strategist
**Method:** Inspection of the actual UI layer — shared macros (`modules/shared/templates/partials/ecs_ux_macros.html`), the universal drilldown engine (`modules/shared/static/js/drilldown_engine.js`, `modules/shared/drilldowns/ecs_universal_drill_engine.py`), persona display (`persona_display.py`), navigation (`mvp_sidebar.html`, `ecs_nav_groups.html`), and the page/partial templates across all six modules.

---

## 1. UX Architecture (as built)

- **Pattern:** Server-rendered Jinja2 + Bootstrap, two-column layout (persistent left sidebar + main workspace). No SPA framework.
- **Composition system:** A disciplined macro library (`ecs_ux_macros.html`) provides `page_header`, `kpi_card`, `accordion_section`, `priority_card`, `zone_open`/`zone_close`, `persona_tab_nav`, `role_label`, `empty_state`, and action menus. This gives the platform strong visual consistency across 40+ pages.
- **Navigation:** Grouped sidebar (Executive Overview · Frameworks · Operations · Governance · Enterprise GRC · AI-SDLC) that collapses/expands by active module.
- **Interaction model:** A **universal drill-down engine** — virtually every KPI, counter, table row and chart cell is clickable and opens a detail modal that traces to supporting records. This is the platform's strongest UX asset.
- **Persona system:** Role-tailored dashboards (App Owner, Auditor, CIO, Vertical Head, Compliance Head, Functional Head) and persona tab navigation; the same data re-frames per role.
- **AI Copilot:** A floating assistant dock present across all pages.

---

## 2. UX Heuristic Evaluation (Nielsen)

| Heuristic | Score (1–5) | Findings |
|---|:--:|---|
| Visibility of system status | 4 | KPI strips, readiness bars, stage pills, connector health, sync status, "How Calculated" methodology on drills |
| Match to real world | 5 | Language is GRC-native (frameworks, controls, evidence, observations, exceptions, CAB); persona framing matches bank roles |
| User control & freedom | 3 | Strong drill-in; back-navigation relies on browser + URL state; limited breadcrumb affordance on deep drills |
| Consistency & standards | 4 | Macro library enforces consistent cards/headers/zones; some per-page inline styling diverges |
| Error prevention | 4 | RBAC guards block disallowed actions with toasts; resubmission gating prevents premature submit |
| Recognition over recall | 3 | Excellent within-page; cross-module recall is heavier because state lives in URL params, not saved views |
| Flexibility & efficiency | 3 | Power-user drill-downs are fast; no global command palette or saved filters yet |
| Aesthetic & minimalist design | 3 | Dense, information-rich screens; high signal but can overwhelm first-time users |
| Help users recover from errors | 3 | Toast/redirect denials are clear; deeper error states (failed sync, empty data) use `empty_state` but messaging varies |
| Help & documentation | 4 | In-context "How Calculated" methodology and grounded Copilot reduce reliance on external docs |

**Composite UX maturity: 3.6 / 5 — strong, consistent, information-dense enterprise UX with clear traceability; rough edges in navigation memory, responsiveness and first-run onboarding.**

---

## 3. What Works Exceptionally Well

1. **Traceability as a first-class UX principle.** The universal drilldown engine means no number is a dead-end — every metric explains itself and links to its records. For a compliance audience that must *defend* numbers, this is differentiating.
2. **"How Calculated" transparency.** Drill-downs expose the methodology (e.g. readiness = 50/30/20), which builds auditor trust directly in the UI.
3. **Consistent macro-driven layout.** `zone_open`/`kpi_card`/`accordion_section`/`persona_tab_nav` give a coherent system across a very large surface, reducing cognitive load page-to-page.
4. **Role-framed truth.** The same underlying data presented per persona avoids the "different teams quoting different numbers" problem.
5. **Grounded Copilot in-context.** A floating assistant that refuses to answer without evidence is a trustworthy, low-risk AI UX.

---

## 4. Friction & Risk Areas

1. **Information density.** Screens such as the framework command center, audit-prep cockpit and demo overview pack many widgets; first-time users need guided orientation.
2. **Desktop-first.** Layouts assume wide viewports; there is no dedicated mobile/responsive experience (e.g. an auditor approving from a phone). Bootstrap defaults provide minimal reflow only.
3. **Navigation memory.** Deep state lives in URL query params rather than persisted views; users cannot easily save or share a filtered context, and breadcrumbs on deep drills are thin.
4. **Heavy Jinja contexts.** Some templates take 20+ context variables, which is an authoring/maintainability risk (mitigated by `safe_get`/defaults but still fragile) and can cause inconsistent empty/error states.
5. **Onboarding/first-run.** No guided tour or progressive disclosure for a brand-new user landing on a dense dashboard.
6. **Accessibility.** An accessibility theme template exists, but there is no evidence of a completed WCAG 2.1 AA audit; dense tables and color-coded status need contrast/ARIA verification.

---

## 5. Prioritized UX Recommendations

| # | Recommendation | Grounded in | Priority |
|--:|---|---|:--:|
| 1 | First-run guided tour + progressive disclosure on dense dashboards | persona dashboards, `mvp_demo_overview.html` | P1 |
| 2 | Breadcrumbs + persistent "back to context" on universal drilldowns | `drilldown_engine.js`, `ecs_universal_drill_engine.py` | P1 |
| 3 | Saved/shareable filter views + global command palette | `global_filter_engine.py`, filter clients | P1 |
| 4 | Responsive auditor experience (approve/reject/review on mobile) | `evidence_review`, approval actions | P2 |
| 5 | WCAG 2.1 AA audit + remediation (contrast, ARIA, keyboard nav) | accessibility theme template, tables | P2 |
| 6 | Standardize empty/error/loading states via a single macro | `empty_state` macro | P2 |
| 7 | View-model assembly layer to thin out 20+ var Jinja contexts | dense templates | P2 |
| 8 | Notification inbox UX (in-app + email/Teams) | `audit_trail` notifications ring | P2 |
| 9 | Consolidate per-page inline CSS into shared stylesheets | inline `<style>` blocks | P3 |
| 10 | Density toggle (comfortable/compact) for power vs. new users | macro library | P3 |

---

## 6. Persona-Specific UX Notes

- **CIO / Vertical / Functional / Compliance Head:** Executive dashboards are strong on at-a-glance KPIs and drill-through; benefit most from saved views and scheduled/exportable snapshots.
- **Auditor:** Best served by the evidence-review and audit-prep flows; the biggest unlock is a mobile approval surface and one-click evidence packs.
- **App Owner:** Work-queue and upload flows are clear; resubmission gating is good error-prevention; would benefit from clearer "what's blocking me" guidance.
- **Security Officer / Control Owner (new RBAC roles):** Have permission scaffolding in `config/rbac.yaml` but lighter dedicated UI; opportunity to give them first-class landing pages.

---

## 7. Conclusion

ECS has a **mature, consistent, traceability-first enterprise UX** that is unusually trustworthy for a compliance product — every number explains and proves itself, and the AI assistant is grounded. The improvement agenda is not a redesign; it is **polish and reach**: guided onboarding, navigation memory, responsiveness, accessibility, and thinner template contexts. These are well-scoped against the existing macro and drilldown systems and are reflected as UX items in `product/ecs_enterprise_backlog.md`.
