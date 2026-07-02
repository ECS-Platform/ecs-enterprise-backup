# Pass 2 — Focused Verification

Scope: targeted re-verification of the Pass 1 remediation only. No platform-wide
crawl, no full persona sweep, no large validation jobs. All checks run live
against `http://127.0.0.1:8000`.

**Overall result: ALL CHECKS PASS.**

---

## 1. Evidence Explorer — all personas

Route: `/mvp/evidence-explorer` · checked for HTTP 200, non-empty grid, and
absence of "Repository unavailable".

| Persona | HTTP | Rows shown | Repository unavailable | Result |
|---|---|---|---|---|
| cio | 200 | 200 of 1,200 | No | PASS |
| vertical_head | 200 | 200 of 1,200 | No | PASS |
| functional_head | 200 | 200 of 1,200 | No | PASS |
| owner | 200 | 200 of 1,200 | No | PASS |
| auditor | 200 | 200 of 1,200 | No | PASS |
| compliance | 200 | 200 of 1,200 | No | PASS |
| security | 200 | 200 of 1,200 | No | PASS |
| it_ops | 200 | 200 of 1,200 | No | PASS |
| platform_ops | 200 | 200 of 1,200 | No | PASS |
| risk | 200 | 200 of 1,200 | No | PASS |
| governance | 200 | 200 of 1,200 | No | PASS |
| ai_governance | 200 | 200 of 1,200 | No | PASS |

- No "Repository unavailable" / psycopg2 for any persona.
- No empty grids — 200 records rendered (of 1,200 deterministic total).
- Mock evidence visible across 10 connectors (GitHub, Jira, Confluence, Figma,
  Teams, SharePoint, SonarQube, Jenkins, GitLab, ServiceNow).

**Evidence Explorer: PASS**

---

## 2. Enterprise Dashboard

Drilldown endpoint: `/api/ecs/universal-drill?scope=kpi&page=enterprise&metric=…`
Page body: `/mvp/enterprise`.

| Metric / check | HTTP | ok | Rows | Result |
|---|---|---|---|---|
| `national_score` drilldown | 200 | true | 25 | PASS |
| `enterprise_compliance` drilldown | 200 | true | 25 | PASS |
| `open_observations` drilldown | 200 | true | 25 | PASS |
| `frameworks_at_risk` drilldown | 200 | true | 25 | PASS |
| Enterprise page body shows "Demo data unavailable" | — | — | — | No (PASS) |

- National Score drilldown populated (25 rows).
- Enterprise Compliance drilldown populated (25 rows).
- No "Demo data unavailable" in the rendered Enterprise page body.

**Enterprise Dashboard: PASS**

---

## 3. Demo Overview — Top Risk Applications readability

Route: `/mvp/demo-overview`.

- 40 Top Risk application rows render with names (e.g. *Customer Onboarding
  Platform, Mobile Banking Edge, Enterprise Payments Hub, Digital Lending
  Platform, Core Banking Platform*).
- Contrast rule confirmed in served CSS:
  - `.ecs-top-risk-applications .col-app strong` → present
  - `table.demo-table .col-app strong` → present
  - `table.demo-table .col-app` → present
- Application-name ink colour resolves to `--ax-ink = #0F172A` (near-black) on the
  light table surface → **no white-on-white**.
- Screenshot: `nav_audit/pass2_demo_overview_toprisk.png` (application column legible).

**Demo Overview Top Risk Applications: PASS**

---

## 4. KPI Drilldowns

| Endpoint | Metric | HTTP | ok | Rows | Result |
|---|---|---|---|---|---|
| `/api/module-kpi/drill` (audit_prep) | `rejection_trend` | 200 | true | 122 | PASS |
| `/api/module-kpi/drill` (audit_prep) | `pending_aging` | 200 | true | 25 | PASS |
| `/api/ecs/universal-drill` (framework PCI-DSS) | `controls_passed` | 200 | true | 25 | PASS |
| `/api/ecs/universal-drill` (framework PCI-DSS) | `open_observations` | 200 | true | 25 | PASS |
| `/api/ecs/workflow-drill` | `auditor_sla` | 200 | true | 25 | PASS |

- Framework KPI drilldowns populated.
- Module KPI drilldowns populated (including the previously-failing
  `rejection_trend` / `pending_aging` audit_prep metrics).
- Auditor SLA workflow drilldown populated.
- No modal returns only "Failed" — every probe returned `ok:true` with rows.

**KPI Drilldowns: PASS**

---

## Summary

| Area | Result |
|---|---|
| 1. Evidence Explorer (12 personas) | PASS |
| 2. Enterprise Dashboard drilldowns | PASS |
| 3. Demo Overview Top Risk readability | PASS |
| 4. Framework + Module + Workflow KPI drilldowns | PASS |

No "Repository unavailable", no "Demo data unavailable", no empty grids, no
white-on-white text, and no "Failed"-only modals were observed in the verified
scope.

**Status: PASS — not committed, not pushed.**
