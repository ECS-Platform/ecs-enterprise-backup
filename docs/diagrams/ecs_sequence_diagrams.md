# ECS System Sequence Diagrams

> Flows reconstructed from actual routes, engines, and the frontend drilldown engine in
> `/Users/nikhil/Documents/ECS`. File/endpoint citations appear under each diagram.

---

## 1. User Login

Routes: `GET /` and `POST /login` (`app/main.py`); role normalization
(`modules/shared/services/role_permissions.py`); auth (`app/auth/middleware.py`).

```mermaid
sequenceDiagram
  actor User
  participant Browser
  participant App as FastAPI (app/main.py)
  participant Auth as AuthenticationMiddleware
  participant Norm as normalize_role()
  User->>Browser: Open /
  Browser->>App: GET / (login.html)
  App-->>Browser: Login page (role/user select)
  User->>Browser: Submit role + user
  Browser->>Auth: POST /login
  Auth->>Auth: auth.enabled? DEMO_MODE? JWT valid?
  Auth->>App: forward (or 401/403)
  App->>Norm: normalize_role(role)
  Norm-->>App: canonical role
  App-->>Browser: 302 redirect to /dashboard?role=...&user=...
  Browser->>App: GET /dashboard (role-scoped)
  App-->>Browser: Role dashboard HTML
```

**Note:** When `DEMO_MODE=true`, auth is bypassed (`app/auth/demo.py`).

---

## 2. Evidence Submission (owner → auditor)

Routes: `/evidence/upload`, `/evidence/submit` (`evidence_routes.py`), `/evidence/review/*`
(`app/main.py`); engine `evidence_workflow_engine.py`; state `ecs_state`.

```mermaid
sequenceDiagram
  actor Owner
  participant UI as Browser
  participant App as FastAPI
  participant Repo as evidence_repository
  participant WF as evidence_workflow_engine
  participant State as ecs_state
  Owner->>UI: Upload evidence file
  UI->>App: POST /evidence/upload
  App->>Repo: register_upload(...)
  Repo->>State: store evidence record
  App-->>UI: upload confirmed
  Owner->>UI: Submit to auditor
  UI->>App: POST /evidence/review/submit
  App->>WF: resolve_state() -> can_submit?
  WF->>State: add control to submitted_controls
  App-->>UI: status = Pending Auditor Review
  Note over App,State: Summary via GET /api/evidence-workflow/summary
```

---

## 3. Audit Lifecycle (review → decision → observation closure → packaging)

Routes: `/evidence/review/approve|reject|request-reupload` (`app/main.py`);
`/audit/package/generate`, `/audit/package/export` (`evidence_routes.py`);
engines `evidence_workflow_engine.py` (`close_observations_for_control`), `audit_schedule_engine.py`.

```mermaid
sequenceDiagram
  actor Auditor
  participant UI as Browser
  participant App as FastAPI
  participant WF as evidence_workflow_engine
  participant State as ecs_state
  Auditor->>UI: Open /evidence/review
  UI->>App: GET /evidence/review
  App-->>UI: pending queue (build_queues)
  alt Approve
    Auditor->>App: POST /evidence/review/approve
    App->>WF: mark approved (Closed)
    WF->>State: approved_controls += control
    WF->>State: close_observations_for_control()
    State-->>WF: closed_observations updated
  else Reject / Re-upload
    Auditor->>App: POST /evidence/review/reject (or request-reupload)
    App->>WF: mark rejected / reupload
    WF->>State: rejected_controls / reupload state
  end
  App-->>UI: updated workflow status
  Auditor->>App: POST /audit/package/generate
  App-->>UI: audit package (export via /audit/package/export)
```

---

## 4. AI SDLC Assessment (stage gate)

Routes: `/mvp/ai-sdlc/{stage}`, `/api/ai-sdlc/workflow/review`, `/api/ai-sdlc/workflow/action`
(`routes_ai_sdlc_governance.py`); engine `ai_sdlc_workflow_engine.py`; store `ai_sdlc_workflow_store.py`.

```mermaid
sequenceDiagram
  actor SDLCOwner as AI-SDLC Owner
  participant UI as Browser
  participant App as FastAPI (ai_sdlc routes)
  participant Eng as ai_sdlc_workflow_engine
  participant Store as ai_sdlc_workflow_store
  SDLCOwner->>UI: Open AI-SDLC stage (e.g. /mvp/ai-sdlc/testing)
  UI->>App: GET /mvp/ai-sdlc/testing
  App->>Eng: build_stage_worklist("testing")
  Eng-->>App: activities + required artifacts
  App-->>UI: stage worklist (Pending/In Review/...)
  SDLCOwner->>UI: Upload artifact / take action
  UI->>App: POST /api/ai-sdlc/workflow/action
  App->>Store: persist activity status
  App->>Eng: recompute worklist/readiness
  App-->>UI: updated stage status
  Note over App,Eng: Reports hub via build_reports_hub()
```

---

## 5. Framework Assessment

Routes: `/framework/{name}`, `/api/framework/kpi-drill`, `/workflow-drill`, `/row-drill`, `/tab-drill`
(`app/main.py`); engines `framework_catalog.py`, `framework_dashboards.py`,
`framework_kpi_drill_engine.py`, `framework_workflow_engine.py`, `ecs_row_drill_engine.py`.

```mermaid
sequenceDiagram
  actor User
  participant UI as Browser
  participant App as FastAPI
  participant Cat as framework_catalog
  participant Dash as framework_dashboards
  participant Drill as framework_*_drill_engine
  User->>App: GET /framework/{name}
  App->>Cat: resolve_framework_name(name)
  App->>Dash: build framework dashboard (controls, evidence, KPIs)
  Dash-->>App: dashboard view-model
  App-->>UI: framework dashboard HTML
  User->>UI: Click KPI / row / tab
  UI->>App: GET /api/framework/kpi-drill (or row/tab/workflow)
  App->>Drill: drill_framework_kpi/row/workflow(...)
  Drill-->>App: {ok, rows, columns, sections}
  App-->>UI: JSON -> modal renders records
```

---

## 6. Drilldown Workflow (universal)

Frontend `modules/shared/static/js/drilldown_engine.js`; routes `/api/ecs/universal-drill`,
`/api/ecs/workflow-drill`, `/api/module-kpi/drill` (`routes_mvp.py`); services
`drilldown_engine.py` (`drill_metric`) → `ecs_universal_drill_engine.py`.

```mermaid
sequenceDiagram
  actor User
  participant DOM as KPI/chart/row element
  participant JS as drilldown_engine.js
  participant App as FastAPI route
  participant Svc as drill_metric()
  participant Eng as ecs_universal_drill_engine
  User->>DOM: Click drillable element
  DOM->>JS: delegated click -> ecsOpenUniversalKpiDrill/Chart/Row
  JS->>JS: safeCount(count), build URL, show "Loading..."
  JS->>App: GET /api/ecs/universal-drill?scope=...
  App->>App: _safe_count(count)
  App->>Svc: drill_metric(scope, page, metric, role, ...)
  Svc->>Eng: drill_universal_kpi/row/chart (+ metric_trace)
  Eng-->>Svc: {ok, title, rows, columns, sections, metric_trace}
  Svc-->>App: response (or _fallback_body)
  App-->>JS: JSON
  alt ok && rows
    JS->>DOM: renderResponse() -> table + trace
  else empty
    JS->>DOM: emptyStateHtml("No records found")
  else error/timeout
    JS->>DOM: errorStateHtml("Unable to load records")
  end
```

---

## 7. Dashboard Analytics

Routes: `/dashboard*`, `/mvp/enterprise`, `/mvp/pan-india`, `/mvp/trends` (`routes_mvp.py`,
`app/main.py`); engines `demo_metrics.py`, `executive_analytics_engine.py`, `analytics_module.py`;
data scope `role_filter_scope.py`.

```mermaid
sequenceDiagram
  actor User
  participant UI as Browser
  participant App as FastAPI
  participant Metrics as demo_metrics
  participant Scope as role_filter_scope
  participant Ana as executive/analytics engines
  User->>App: GET /dashboard?role=...
  App->>Scope: role_filter_scope(role)
  App->>Metrics: role_dashboard_metrics(role)
  App->>Ana: enterprise_dashboard / BU analytics / heatmaps
  Ana-->>App: KPI + chart view-models
  App-->>UI: dashboard HTML (drillable KPIs/charts)
  User->>UI: Click KPI -> (see Drilldown Workflow)
```

---

## 8. Report Generation & Export

Routes: `/mvp/reports`, `/mvp/reports/view/{type}`, `/mvp/reports/download/{id}` (`routes_mvp.py`);
engines `reporting_module.py` (`list_reports`, `generate_report_content`, `generate_report_export`),
`gap_export_engine.py` (PDF/Excel builders); analytics via `analytics_module.enterprise_dashboard`.

```mermaid
sequenceDiagram
  actor User
  participant UI as Browser
  participant App as FastAPI
  participant Rep as reporting_module
  participant Ana as analytics_module
  participant Exp as gap_export_engine
  participant State as ecs_state
  User->>App: GET /mvp/reports
  App->>Rep: list_reports() + list_report_history()
  Rep->>State: include export_history
  Rep-->>App: report catalog
  App-->>UI: report catalog page
  User->>UI: View / Download report (id, fmt)
  UI->>App: GET /mvp/reports/download/{id}?fmt=pdf|excel|csv
  App->>Rep: generate_report_export(id, fmt, role, ...)
  Rep->>Ana: enterprise_dashboard() analytics
  Rep->>Exp: _build_pdf / _spreadsheet_xml
  Exp-->>Rep: file bytes
  Rep->>State: record export in export_history
  Rep-->>App: downloadable file
  App-->>UI: file download
```
