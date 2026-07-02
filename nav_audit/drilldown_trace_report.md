# Executive KPI Drilldown — Complete Flow Trace

Traces the full chain for the four reported KPIs. The KPI cards appear on the **Application
Owner dashboard** (`/dashboard?role=owner`) as workflow analytic cards.

## Shared chain (all four KPIs)

```
KPI card  (data-ecs-enterprise-wf-drill + data-ecs-enterprise-wf-metric="<metric>")
   |  rendered by: modules/shared/templates/partials/evidence_workflow_macros.html
   |              macro workflow_analytics_cards(..., enterprise_drill=true)  (lines 29-54)
   v
onclick (event delegation)
   |  file: modules/shared/static/js/drilldown_engine.js
   |  function bindExplicit() -> document click listener (line ~340)
   |  matches closest('[data-ecs-enterprise-wf-drill]') (line ~350)
   v
JS function: window.ecsOpenEnterpriseWorkflowDrill(metric, label, count)  (line ~329)
   v
fetch call: fetchJson(url, title)  (line ~300)
   |  url = /api/ecs/workflow-drill?metric=<metric>&count=<n>&role=<window.__ecsRole||'cio'>
   v
backend route: /api/ecs/workflow-drill   (registered via app routes)
   v
service / data provider: ecs_universal_drill_engine / workflow drill engine
   v
response object: { ok:true, title, rows:[...25], columns:[...], sections{}, metric_trace{}, detail{} }
   v
modal renderer: renderResponse(j, title)  (line ~278) -> showModal()
```

## Per-KPI metric mapping

| KPI label (UI) | data-ecs-enterprise-wf-metric | Endpoint |
|---|---|---|
| Closure Rate | `approval_rate` | `/api/ecs/workflow-drill?metric=approval_rate` |
| Avg Review Time | `avg_review_time` | `/api/ecs/workflow-drill?metric=avg_review_time` |
| Rejection Trend | `rejection_trend` | `/api/ecs/workflow-drill?metric=rejection_trend` |
| Auditor SLA | `auditor_sla` | `/api/ecs/workflow-drill?metric=auditor_sla` |
| Pending Aging | `pending_aging` | `/api/ecs/workflow-drill?metric=pending_aging` |

## Exact files & functions

| Layer | File | Symbol |
|---|---|---|
| KPI card markup | `modules/shared/templates/partials/evidence_workflow_macros.html` | `workflow_analytics_cards` |
| Click binding | `modules/shared/static/js/drilldown_engine.js` | `bindExplicit` → `[data-ecs-enterprise-wf-drill]` |
| Drill launcher | `modules/shared/static/js/drilldown_engine.js` | `ecsOpenEnterpriseWorkflowDrill` |
| Fetch + render orchestration | `modules/shared/static/js/drilldown_engine.js` | `fetchJson` → `renderResponse` |
| Empty/error/loader states | `modules/shared/static/js/drilldown_engine.js` | `emptyStateHtml`, `errorStateHtml`, `EMPTY_DEFAULT`, `ERROR_DEFAULT` |
| Backend endpoint | `app` route registration | `/api/ecs/workflow-drill` |
| Drill engine | `modules/shared/drilldowns/ecs_universal_drill_engine.py` + workflow drill engine | workflow-drill handler |

The two sibling drill modals share the same pattern and were hardened identically:
- `modules/shared/templates/partials/ecs_module_kpi_drill.html` (`ecsOpenModuleKpiDrill`)
- `modules/frameworks/templates/partials/ecs_framework_kpi_drill.html` (`fetchJson`)
