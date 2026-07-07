# ECS Screen Catalog

Part of the **ECS Product Operations Manual**. Every user-facing screen ECS renders, grounded in the route registrars (`app/main.py`, `routes_mvp.py`, `routes_platform.py`, `routes_governance.py`, `routes_ai_sdlc_governance.py`, `evidence_routes.py`) and their Jinja templates.

**Conventions.** Most screens accept `role` and `user` query params (and often `notice`/`response`). Browser routes return server-rendered HTML; `/api/*` return JSON (see `ECS_FEATURE_REFERENCE.md` for the API/drill catalog). Screenshot file names refer to `docs/product/screenshots/` (see `ECS_SCREENSHOTS_INDEX.md`).

Screen count: **~79 HTML screens** across 7 nav groups + core. Each entry below lists: URL · Nav path · Purpose · Users · Inputs/Filters · Actions · Outputs (tables/charts/KPIs) · Drilldowns · Exports · Dependencies.

---

## Core / authentication

### Login
- **URL:** `/` · **Template:** `login.html` (`app/main.py:325`) · **Screenshot:** `01-login.png`
- **Nav path:** entry point
- **Purpose:** Role picker / landing page; select a persona to enter ECS.
- **Users:** all
- **Inputs:** `role` (form) · **Actions:** `POST /login` → role-specific dashboard
- **Outputs:** persona cards · **Dependencies:** `POST /login` routing (`app/main.py:334`)

### Access Denied
- **URL:** `/access-denied` (`app/main.py:407`)
- **Purpose:** RBAC denial page (403) shown when page enforcement is on and a role lacks the page.
- **Inputs:** `page`, `role`, `user`, `home` · **Outputs:** denial notice + home link · **Dependencies:** `app/auth/page_guard.py`

---

## Group 1 — Executive Overview

### Main Dashboard (Owner / Auditor)
- **URL:** `/dashboard?role={owner|auditor}` · **Template:** `dashboard.html` (`app/main.py:422`) · **Screenshots:** `02-dashboard-owner.png`, `03-dashboard-auditor.png`
- **Nav path:** Executive Overview → Main Dashboard
- **Purpose:** Primary work-queue dashboard — owner's pending/resubmit queue or auditor's review queue.
- **Users:** Application Owner, Auditor
- **Inputs:** `role`, `user`, `response`, `notice`
- **Actions:** `POST /chat`, `/submit`, `/approve`, `/reject`, `/workflow/*`
- **Outputs/KPIs:** role KPI strip (pending tasks, resubmits, observations, SLA breaches, audit readiness %); work-queue tables
- **Drilldowns:** `/framework/{name}`, `/evidence/review`, `/api/evidence-workflow/summary`
- **Dependencies:** `governance/workflow_module.py`, `evidence_workflow_engine.py`, `nav_counter_engine.py`

### CIO Executive Dashboard
- **URL:** `/dashboard/cio` · **Template:** `cio_dashboard.html` (`app/main.py:456`) · **Screenshot:** `04-dashboard-cio.png`
- **Nav path:** Executive Overview → Evidence Analytics (CIO)
- **Purpose:** Enterprise-wide analytics & governance posture for the CIO. Page-guarded to `dashboard.cio`.
- **Users:** CIO, AI Governance Owner
- **Actions:** `POST /chat`, `/workflow/leadership/review`
- **Outputs/KPIs:** enterprise compliance, audit completion, readiness, open VAPT, AI hallucination alerts; executive charts (compliance, readiness, risk)
- **Drilldowns:** `/api/ecs/universal-drill`, framework pages, `/mvp/*` executive modules
- **Dependencies:** `demo_metrics.py`, `executive_analytics_engine.py`

### Vertical Head Dashboard
- **URL:** `/dashboard/vertical-head` · **Template:** `dashboard_vertical_head.html` (`routes_mvp.py:134`) · **Screenshot:** `05-dashboard-vertical-head.png`
- **Nav path:** Executive Overview → Vertical Head Dashboard
- **Purpose:** Aggregated posture across the owned vertical.
- **Users:** Vertical Head · **Drilldowns:** `/mvp/comparison`, `/mvp/enterprise`

### Compliance Head Dashboard
- **URL:** `/dashboard/compliance-head` · **Template:** `dashboard_compliance_head.html` (`routes_mvp.py:147`) · **Screenshot:** `06-dashboard-compliance-head.png`
- **Nav path:** Executive Overview → Compliance Dashboard
- **Purpose:** Framework/control compliance oversight. Shared by Security Officer login.
- **Users:** Compliance Head/Officer, Security Officer, Framework Owner

### Functional Head Dashboard
- **URL:** `/dashboard/functional-head` · **Template:** `dashboard_functional_head.html` (`routes_mvp.py:163`) · **Screenshot:** `07-dashboard-functional-head.png`
- **Purpose:** Aggregated posture across the owned function. · **Users:** Functional Head

### ROI & Value Realization Center
- **URL:** `/mvp/roi` · **Template:** `mvp_roi_center.html` (`routes_mvp.py:295`) · **Screenshot:** `08-roi-center.png`
- **Nav path:** Executive Overview → ★ ROI & Value Realization
- **Purpose:** Quantify ECS value — hours saved, FTE, annual value, payback. Deterministic, from `config/roi.yaml`.
- **Users:** CIO, executives · **Inputs:** `scenario`
- **Outputs/KPIs:** ROI bars (annual value, hours, FTE), ROI Audit Readiness Score; storyboard (`roi_storyboard.js`)
- **Dependencies:** `app/roi/workbook.py`; gated by `ROI_CENTER_ENABLED`

### Demo Overview
- **URL:** `/mvp/demo-overview` · **Template:** `mvp_demo_overview.html` (`routes_mvp.py:664`) · **Screenshot:** `09-demo-overview.png`
- **Nav path:** Executive Overview → Demo Overview
- **Purpose:** Executive demo cockpit — headline KPIs across banking apps, frameworks, AI governance.
- **Users:** demo teams, CIO · **Inputs:** `framework`, `application`, `owner`
- **Outputs/KPIs:** Banking Applications, Frameworks, Controls, Evidence Records, ServiceNow Tickets, AI Prompts Audited, Hallucination Alerts, Open VAPT, Critical Drift; risk heatmap; CIO executive strip
- **Drilldowns:** `/api/demo/*` (status, overview, banking-applications, frameworks, servicenow, ai-governance, prompt-audit, hallucinations, token-usage, audit-history, risk-heatmap, drift, evidence-lineage, vapt, cio-executive)
- **Dependencies:** `ecs_mock_engine.py`, `demo_kpi_drill_engine.py`

### Enterprise
- **URL:** `/mvp/enterprise` · **Template:** `mvp_enterprise.html` (`routes_mvp.py:1133`) · **Screenshot:** `10-enterprise.png`
- **Nav path:** Executive Overview → Enterprise
- **Purpose:** Org-wide governance KPIs, framework maturity, business-unit risk.
- **Outputs/Charts:** BU bars (Compliance %, Audit Readiness, Open Gaps, Observations, Risk Score), framework maturity bars, executive heatmap bars
- **Filters:** via `standard_filter_client.html` (framework, BU) · **Dependencies:** `executive_analytics_engine.py`, `demo_metrics.BUSINESS_UNITS`

### Pan India
- **URL:** `/mvp/pan-india` · **Template:** `mvp_pan_india.html` (`routes_mvp.py:1139`) · **Screenshot:** `11-pan-india.png`
- **Nav path:** Executive Overview → Pan India
- **Purpose:** Regional/zone-level compliance, SLA breaches, critical observations.
- **Charts:** PCI Readiness by Region, Audit Readiness Score, SLA Breaches, Critical Observations, Framework Posture (by zone)
- **Actions/Exports:** `POST /mvp/module/action` (`export_regional` → `PanIndia_{region}_2026_05.csv`)
- **Dependencies:** `executive_analytics_engine.enhance_pan_india_regions`

### Reports
- **URL:** `/mvp/reports` · **Template:** `mvp_reports.html` (`routes_mvp.py:1146`) · **Screenshot:** `12-reports.png`
- **Nav path:** Executive Overview → Reports
- **Purpose:** Audit-ready export center — 30 regulator/audit packs with history.
- **Users:** Auditor, CIO, Compliance, owners (export-permitted roles)
- **Charts:** Export Distribution, Report Generation Trend; Top Downloaded / Recent / Upcoming lists
- **Actions/Exports:** `GET /mvp/reports/download/{report_id}?format={pdf|excel|csv|xlsx}`; `POST /mvp/module/action` (export_pdf/excel/csv/generate)
- **Drilldowns:** `/mvp/reports/view/{report_type}` · **Dependencies:** `reporting_module.py`, `reports_analytics_engine.py`

### Report Viewer (interactive HTML report)
- **URL:** `/mvp/reports/view/{report_type}` · **Template:** `mvp_ecs_report.html` (`routes_mvp.py:284`)
- **Purpose:** Render one of 5 interactive HTML reports: `framework-adherence`, `framework-readiness`, `application-compliance`, `evidence-coverage`, `findings-remediation`.
- **Dependencies:** `ecs_reports_engine.py`

### Trends
- **URL:** `/mvp/trends` · **Template:** `mvp_trends.html` (`routes_mvp.py:1547`) · **Screenshot:** `13-trends.png`
- **Nav path:** Executive Overview → Trends
- **Purpose:** Historical compliance analytics across multiple series.
- **Filters:** framework, application, risk_level, audit_cycle, time_period, region, business_unit
- **Charts:** Compliance Trend (daily/weekly/monthly/quarterly), Observation Trend (opened/closed/net), Evidence Rejections, Risk Escalation, Framework Contribution, Historical coverage, Implementation Coverage, Rejection Rate, SLA Compliance, Evidence Aging, Remediation Velocity, Weekly Control Growth
- **Drilldowns:** `/mvp/api/analytics-intel`, `/api/ecs/filters/*`
- **Dependencies:** `trends_analytics_engine.py`

---

## Group 2 — Frameworks

### Framework Dashboard
- **URL:** `/framework/{framework_name}` · **Template:** `framework.html` (`app/main.py:548`) · **Screenshot (PCI DSS):** `14-framework-pci-dss.png`
- **Nav path:** Frameworks → {framework}
- **Purpose:** Per-framework compliance dashboard with KPI tiles, tabs (applications / controls / evidence), and (for ITPP) operational drill views.
- **Users:** Compliance, Auditor, Framework Owner, Application Owner
- **Inputs:** `role`, `user`, `fw_tab`, `fw_app`, `itpp_view`, `itpp_domain`, `itpp_app`
- **Actions:** `POST /itpp/action`, `/submit`, `/approve`, `/reject`, `/evidence/upload`, `/evidence/submit`
- **Outputs/KPIs:** 6 framework-specific KPI tiles (e.g. PCI Maturity, CDE Controls, Encryption Coverage, QSA Readiness); application grid; control/evidence tables
- **Drilldowns:** `/api/framework/kpi-drill`, `/workflow-drill`, `/row-drill`, `/tab-drill`; `/evidence/review`
- **Frameworks (15):** PCI DSS, DPSC, OS Baselining, DB Baselining, Nginx Baselining, AppSec, VAPT, CSITE, ITPP, ITDRM, SOC2, ISO27001, RBI Cyber Security, ISG, ASST
- **Dependencies:** `framework_catalog.py`, `framework_dashboards.py`, `framework_kpi_drill_engine.py`

### Framework Loader
- **URL:** `/mvp/framework-loader` · **Template:** `framework_loader.html` (`routes_mvp.py:606`) · **Screenshot:** `15-framework-loader.png`
- **Nav path:** Frameworks → Framework Loader
- **Purpose:** Upload & activate custom framework control libraries; scan applications for coverage.
- **Users:** Compliance Head, Framework Owner · **Inputs:** `framework_id`
- **Actions:** `POST /mvp/framework-loader/upload`, `/activate`
- **Drilldowns:** `/api/framework-loader/control-drill`, `/application-scan`
- **Dependencies:** `framework_loader_service.py`

### Framework Administration
- **URL:** `/mvp/framework-admin` · **Template:** `mvp_framework_admin.html` (`routes_mvp.py:883`) · **Screenshot:** `16-framework-admin.png`
- **Nav path:** Frameworks → Framework Administration (visible if `can_manage_frameworks`)
- **Purpose:** Framework onboarding — import, normalize, reuse decisions, lifecycle, activation.
- **Users:** Framework Owner, Compliance Head, CIO, Admin · **Inputs:** `wizard`, `framework_id`, `toast`
- **Actions:** `POST /api/framework-onboarding/import`, `/lifecycle`, `/reuse-decision`
- **Exports:** `GET /mvp/framework-admin/export/{framework_id}?format={pdf|excel|csv}`
- **Drilldowns:** `GET /api/framework-onboarding/{framework_id}`
- **Dependencies:** `framework_onboarding_engine.py`

---

## Group 3 — Operations

### Scheduler
- **URL:** `/mvp/scheduler` · **Template:** `mvp_scheduler.html` (`routes_mvp.py:177`) · **Screenshot:** `17-scheduler.png`
- **Nav path:** Operations → Scheduler
- **Purpose:** Automated evidence-collection scheduler — cron timeline, scan results, failures, upcoming plan.
- **Users:** Operations Owner, Admin
- **Actions:** `POST /mvp/scheduler/run|retry|pause|resume`, `/mvp/module/action`
- **Outputs/KPIs:** success rate %, evidence collected, failed jobs; collection bars
- **Drilldowns:** `/api/module-kpi/drill`, `/api/ecs/universal-drill`
- **Dependencies:** `scheduler_module.py`, `scheduler_intelligence.py`

### Predefined Queries
- **URL:** `/mvp/predefined-queries` · **Template:** `mvp_predefined_queries.html` (`routes_mvp.py:190`) · **Screenshot:** `18-predefined-queries.png`
- **Nav path:** Operations → Predefined Queries
- **Purpose:** Catalog of query-driven controls from the ECS Query-Driven Control Library across frameworks.
- **Inputs/Filters:** `q`, `framework`, `page`, `sort`, `dir`
- **Outputs/KPIs:** Total Controls, Predefined Queries, Manual Controls, Frameworks Covered, Unsupported Tech
- **Actions:** `POST /mvp/predefined-queries/run` · **Drilldowns:** `/mvp/predefined-queries/detail?control_id=…`
- **Dependencies:** `predefined_queries_engine.py`

### Predefined Query Detail
- **URL:** `/mvp/predefined-queries/detail` · **Template:** `mvp_predefined_query_detail.html` (`routes_mvp.py:219`)
- **Purpose:** Single query detail + execution prep. · **Actions:** `POST /mvp/predefined-queries/prepare`, `/run`

### Integration Health
- **URL:** `/mvp/integration-health` · **Template:** `platform_integration_health.html` (`routes_platform.py:34`) · **Screenshot:** `19-integration-health.png`
- **Nav path:** Operations → Integration Health
- **Purpose:** Connector health & evidence collection status (real `ecs_platform` connectors).
- **Users:** Admin, Operations Owner
- **Actions:** `POST /mvp/platform/sync/{connector}` (admin), `/mvp/platform/sync-all`
- **Drilldowns:** `/api/platform/health` · **Dependencies:** `ecs_platform/ingestion.py`

### Evidence Explorer
- **URL:** `/mvp/evidence-explorer` · **Template:** `platform_evidence_explorer.html` (`routes_platform.py:46`) · **Screenshot:** `20-evidence-explorer.png`
- **Nav path:** Operations → Evidence Explorer
- **Purpose:** Browse repository evidence with correlations (Commit→Build→Scan chains).
- **Filters:** `application`, `source_system`, `object_type` · **Drilldowns:** `/api/platform/evidence` (scope-filtered)

### AI Ops Assistant
- **URL:** `/mvp/ai-ops-assistant` · **Template:** `mvp_ai_ops_assistant.html` (`routes_mvp.py:183`) · **Screenshot:** `21-ai-ops-assistant.png`
- **Nav path:** Operations → AI Ops Assistant
- **Purpose:** Banking governance copilot for incidents/audit/compliance/evidence drilldowns.
- **Actions:** `POST /mvp/chat`, `/mvp/api/chat-investigation`, `/chat-action`, `/chat-response-mode`
- **Drilldowns:** `/mvp/ai-ops-assistant/summary/{mode}` (business/technical/executive)
- **Dependencies:** `ai_ops_assistant_engine.py`, `ai_ops_response_modes.py`

### Bulk Upload
- **URL:** `/mvp/upload` (alias `/mvp/bulk-upload`) · **Template:** `mvp_bulk_upload.html` (`routes_mvp.py:442`) · **Screenshot:** `22-bulk-upload.png`
- **Nav path:** Operations → Bulk Upload (visible if `can_upload` / owner)
- **Purpose:** Mass evidence import with validation, dedup, framework auto-mapping.
- **Users:** Application Owner · **Inputs:** `framework`, `application`, `control`
- **Actions:** `POST /mvp/upload/bulk`, `/evidence/upload` · **Drilldowns:** `/mvp/completeness`

### Integrations
- **URL:** `/mvp/integrations` · **Template:** `mvp_integrations.html` (`routes_mvp.py:1121`) · **Screenshot:** `23-integrations.png`
- **Nav path:** Operations → Integrations
- **Purpose:** External system connectors (SIEM, ticketing, GRC) + ingestion health.
- **Actions:** `POST /mvp/integrations/sync` (open in demo) · **Dependencies:** `integrations_module.py`

### Onboarding
- **URL:** `/mvp/onboarding` · **Template:** `mvp_onboarding.html` (`routes_mvp.py:553`) · **Screenshot:** `24-onboarding.png`
- **Nav path:** Operations → Onboarding
- **Purpose:** Application onboarding wizard — framework assignment, ownership, registration.
- **Users:** Operations Owner
- **Actions:** `POST /mvp/onboarding`, `/api/onboarding/simulate`, `/api/onboarding/export` (text)
- **Dependencies:** `onboarding_engine.py`

---

## Group 4 — Governance

### Audit Prep
- **URL:** `/mvp/audit-prep` · **Template:** `mvp_audit_prep.html` (`routes_mvp.py:1192`) · **Screenshot:** `25-audit-prep.png`
- **Nav path:** Governance → Audit Prep
- **Purpose:** Audit readiness cockpit — upcoming audits, missing controls, package preview, mock audit.
- **Users:** Auditor, Compliance
- **Filters:** `fw_filter`, `app_filter`, `risk_filter`, `status_filter`, `owner_filter`, `show_modal`
- **Charts:** framework×application readiness heatmap
- **Actions/Exports:** `POST /audit/package/generate`, `/mvp/module/action` (generate_package, export_pdf), `/mvp/workflow/*`
- **Drilldowns:** `/api/audit-prep/kpi-drill`, `/audit-detail`, `/upcoming`; `/mvp/workflow/mock-audit`
- **Dependencies:** `audit_prep_data.py`, `executive_analytics_engine.py`

### Evidence Health
- **URL:** `/mvp/evidence-health` · **Template:** `mvp_evidence_health.html` (`routes_mvp.py:485`) · **Screenshot:** `26-evidence-health.png`
- **Nav path:** Governance → Evidence Health
- **Purpose:** Risk/quality scoring — stale, expired, incomplete, low-confidence evidence.
- **Filters:** `framework`, `application`, `status`, `filter_issue`, `tab`
- **Outputs/KPIs:** Health Score, Controls Missing Evidence, Open Observations, High-Risk Failures, Expiring/Rejected/Stale/Revalidated counts
- **Charts:** Rejection Trend, Stale Evidence Aging
- **Drilldowns:** `/mvp/search`, `/api/module-kpi/drill`, `/api/ecs/universal-drill`
- **Dependencies:** `evidence_health_engine.py`

### Evidence Reuse
- **URL:** `/mvp/reuse` · **Template:** `mvp_reuse.html` (`routes_mvp.py:547`) · **Screenshot:** `27-evidence-reuse.png`
- **Nav path:** Governance → Evidence Reuse
- **Purpose:** Cross-framework reuse graph — map once, satisfy many controls.
- **Outputs/KPIs:** reuse %, controls covered by reuse, avg reuse factor · **Dependencies:** `framework_intelligence.py`, `evidence_repository.py`

### Lifecycle
- **URL:** `/mvp/lifecycle` · **Template:** `mvp_lifecycle.html` (`routes_mvp.py:1005`) · **Screenshot:** `28-lifecycle.png`
- **Nav path:** Governance → Lifecycle
- **Purpose:** Evidence lifecycle governance — draft → active → expiring → archived → retired.
- **Outputs/KPIs:** Control Lifecycles, Evidence Records, Open Observations, Active Remediations, Audit Cycles, Active Exceptions
- **Charts:** evidence aging, remediation velocity, stale trend, exception expiry timeline, audit closure timeline
- **Dependencies:** `governance_lifecycle_engine.py`

### Completeness
- **URL:** `/mvp/completeness` · **Template:** `mvp_completeness.html` (`routes_mvp.py:541`) · **Screenshot:** `29-completeness.png`
- **Nav path:** Governance → Completeness
- **Purpose:** Coverage gap analysis — controls without evidence, partial compliance, audit readiness.
- **Outputs/KPIs:** Overall Control Maturity, Audit Readiness (dynamic), per app×framework readiness
- **Actions:** `POST /mvp/module/action` (close_gap, assign_owner, upload_missing) · **Drilldowns:** `/mvp/workflow/*`
- **Dependencies:** `governance_completeness_engine.py`, `missing_evidence_engine.py`

### App Comparison
- **URL:** `/mvp/comparison` · **Template:** `mvp_comparison.html` (`routes_mvp.py:1013`) · **Screenshot:** `30-comparison.png`
- **Nav path:** Governance → App Comparison
- **Purpose:** Cross-application/framework gap comparison — maturity variance, control gaps.
- **Users:** Vertical/Functional Head, Compliance
- **Charts:** readiness evolution, failed controls trend, observation closure, framework maturity trend
- **Exports:** `POST /mvp/comparison/export-gaps` (pdf/excel/csv) → `/mvp/exports/download/{id}`, preview `/mvp/exports/preview/{id}`
- **Dependencies:** `comparison_engine.py`, `gap_export_engine.py`

### Search
- **URL:** `/mvp/search` · **Template:** `mvp_search.html` (`routes_mvp.py:515`) · **Screenshot:** `31-search.png`
- **Nav path:** Governance → Search
- **Purpose:** Enterprise evidence discovery with semantic filters & reuse mapping.
- **Filters:** `q`, `framework`, `application`, `owner`, `status` · **Drilldowns:** `/mvp/reuse`
- **Dependencies:** `search_module.py`

### Evidence Approval Analytics
- **URL:** `/mvp/evidence-approval` · **Template:** `mvp_evidence_approval.html` (`routes_mvp.py:1633`) · **Screenshot:** `32-evidence-approval.png`
- **Nav path:** Governance → Evidence Approval Analytics
- **Purpose:** Track approval efficiency and reviewer throughput.
- **Users:** Auditor, Governance teams, Framework Owners
- **Outputs/KPIs:** Approval Success %, Rejection Rate %, Avg Validation Time, framework approval %, application maturity, quality score
- **Charts:** Approval Trend, Rejection Trend, Framework Approval %, Reviewer Workload, Application Maturity, Stale Evidence Aging
- **Exports:** `POST /mvp/module/action` (`evidence_approval`/`export_summary` → CSV)
- **Dependencies:** `evidence_approval_engine.py`

### Evidence Review (workspace)
- **URL:** `/evidence/review` · **Template:** `evidence_review.html` (`app/main.py:682`)
- **Purpose:** Single-evidence review workspace — the heart of the approve/reject lifecycle.
- **Users:** Auditor (review actions), Owner (submit/upload-revised)
- **Inputs:** `framework_name`, `evidence_id`, `control_name`
- **Actions:** `POST /evidence/review/{submit|approve|reject|clarify|close-observation|request-reupload|reject-internal|save-draft|cancel|request-resubmission|upload-revised|reevaluate}`
- **Dependencies:** `evidence_review.py`, `evidence_workflow_engine.py`, `audit_trail.py`

### Workflow action pages
- `/mvp/workflow/close-gap` (`mvp_workflow_close_gap.html`), `/mvp/workflow/assign-owner` (`mvp_workflow_assign_owner.html`), `/mvp/workflow/upload-missing` (`mvp_workflow_upload_missing.html`), `/mvp/workflow/mock-audit` (`mvp_workflow_mock_audit.html`)
- **Purpose:** Guided remediation forms invoked from Completeness/Audit-Prep.
- **Actions:** corresponding `POST` handlers; mock-audit → `GET /mvp/workflow/mock-audit/report` (text)
- **Dependencies:** `operational_workflows.py`

---

## Group 5 — Evidence Governance (platform / DB-backed)

Routes in `app/routes_governance.py`. Powered by `ecs_platform` (PostgreSQL repository) with demo fallback.

### Role Scorecard
- **URL:** `/mvp/platform/scorecard` · **Template:** `gov_scorecard.html` (`routes_governance.py:97`) · **Screenshot:** `33-platform-scorecard.png`
- **Purpose:** Role-scoped governance scorecard (applications, evidence, reuse %, coverage, observations, compliance score).
- **Drilldowns:** `/api/platform/scorecard`

### Executive Summary
- **URL:** `/mvp/platform/executive-summary` · **Template:** `gov_executive_summary.html` (`routes_governance.py:175`) · **Screenshot:** `34-platform-executive-summary.png`
- **Purpose:** Platform-level executive governance summary. · **Drilldowns:** `/api/platform/executive-summary`

### Audit Readiness
- **URL:** `/mvp/platform/audit-readiness` · **Template:** `gov_audit_readiness.html` (`routes_governance.py:166`) · **Screenshot:** `35-platform-audit-readiness.png`
- **Purpose:** Composite audit-readiness gauge (50% coverage + 30% approved evidence + 20% freshness).
- **Drilldowns:** `/api/platform/audit-readiness` · **Dependencies:** `ecs_platform/governance.py:audit_readiness`

### Application Onboarding
- **URL:** `/mvp/platform/onboarding` · **Template:** `gov_app_onboarding.html` (`routes_governance.py:38`) · **Screenshot:** `36-platform-onboarding.png`
- **Purpose:** Register an application (owner, BU, criticality, environment, frameworks).
- **Actions:** `POST /mvp/platform/onboarding` → `/mvp/platform/inventory`

### Application Inventory
- **URL:** `/mvp/platform/inventory` · **Template:** `gov_app_inventory.html` (`routes_governance.py:68`) · **Screenshot:** `37-platform-inventory.png`
- **Purpose:** Catalog of onboarded applications. · **Drilldowns:** `/mvp/platform/application/{slug}` (`gov_app_detail.html`)

### Control Coverage
- **URL:** `/mvp/platform/control-coverage` · **Template:** `gov_control_coverage.html` (`routes_governance.py:106`) · **Screenshot:** `38-platform-control-coverage.png`
- **Purpose:** Controls with ≥1 evidence / total controls. · **Drilldowns:** `/api/platform/control-coverage`

### Framework Coverage
- **URL:** `/mvp/platform/framework-coverage` · **Template:** `gov_framework_coverage.html` (`routes_governance.py:115`) · **Screenshot:** `39-platform-framework-coverage.png`
- **Purpose:** Per-framework coverage via crosswalk. · **Drilldowns:** `/api/platform/framework-coverage`

### Evidence Reuse (platform)
- **URL:** `/mvp/platform/evidence-reuse` · **Template:** `gov_evidence_reuse.html` (`routes_governance.py:86`) · **Screenshot:** `40-platform-evidence-reuse.png`
- **Purpose:** DB-backed reuse demonstrations & crosswalk. · **Drilldowns:** `/api/platform/evidence-reuse`, `/reuse-demonstrations`, `/crosswalk`

### Evidence Lifecycle (platform)
- **URL:** `/mvp/platform/evidence-lifecycle` · **Template:** `gov_evidence_lifecycle.html` (`routes_governance.py:145`) · **Screenshot:** `41-platform-evidence-lifecycle.png`
- **Purpose:** Review/validate evidence by lifecycle status. · **Inputs:** `status` · **Actions:** `POST /mvp/platform/evidence-lifecycle/review`

### Collection Scheduler (platform)
- **URL:** `/mvp/platform/scheduler` · **Template:** `gov_scheduler.html` (`routes_governance.py:124`) · **Screenshot:** `42-platform-scheduler.png`
- **Purpose:** Create connector collection schedules. · **Actions:** `POST /mvp/platform/scheduler`

### AI Assistant (platform & chat)
- **URLs:** `/mvp/platform/assistant` (`gov_assistant.html`), `/mvp/ai-assistant` (`ai_assistant.html`, `routes_governance.py:240`) · **Screenshot:** `43-ai-assistant.png`
- **Nav path:** Evidence Governance → AI Assistant / AI Assistant (Chat)
- **Purpose:** Citation-grounded RAG assistant over the evidence repository.
- **Inputs:** `q`, `application`, `framework` · **Actions:** `POST /mvp/ai-assistant/reindex` (admin)
- **Drilldowns:** `/api/platform/assistant`, `/api/platform/rag/{status|gemini|llm}` · **Dependencies:** `ecs_platform/rag.py`

---

## Group 6 — Enterprise GRC

### Risk Register
- **URL:** `/mvp/risk-register` · **Template:** `mvp_risk_register.html` (`routes_mvp.py:1625`) · **Screenshot:** `44-risk-register.png`
- **Nav path:** Enterprise GRC → Risk Register
- **Purpose:** Enterprise risk governance — inherent/residual risk, treatment, aging.
- **Charts:** Risk Severity Distribution, Risk Aging · **Drilldowns:** `/api/grc-demo/risk/drill`
- **Dependencies:** `enterprise_grc.py`, `grc_demo_service.py`

### Exceptions / TD
- **URL:** `/mvp/exceptions` · **Template:** `mvp_exceptions.html` (`routes_mvp.py:1629`) · **Screenshot:** `45-exceptions.png`
- **Nav path:** Enterprise GRC → Exceptions / TD
- **Purpose:** Technical-debt & exception workflow — compensating controls, TD expiry, renewal.
- **Actions:** `POST /mvp/exceptions/raise`, `/api/exceptions/raise`
- **Dependencies:** `exception_state_engine.py`

### Exception Governance
- **URL:** `/mvp/exception-governance` · **Template:** `mvp_exception_governance.html` (`routes_mvp.py:1637`) · **Screenshot:** `46-exception-governance.png`
- **Purpose:** TD lifecycle, approval persistence, expiring exceptions, CAB queue.
- **Outputs/KPIs:** Active, Approved TDs, Rejected, Expiring This Month, High-Risk Open TDs, Pending Review
- **Charts:** Exceptions by Framework

### CMDB / Assets
- **URL:** `/mvp/cmdb` · **Template:** `mvp_cmdb.html` (`routes_mvp.py:1641`) · **Screenshot:** `47-cmdb.png`
- **Purpose:** Asset inventory — applications, servers, cloud assets, ownership, compliance mapping.

### Regulatory Mapping
- **URL:** `/mvp/regulatory` · **Template:** `mvp_regulatory.html` (`routes_mvp.py:1645`) · **Screenshot:** `48-regulatory.png`
- **Purpose:** Cross-framework regulatory normalization — shared controls, reuse, coverage matrix.
- **Charts:** Coverage by Control Theme, Framework Overlap · **Dependencies:** `executive_analytics_engine.build_regulatory_traceability`

### Executive Heatmaps
- **URL:** `/mvp/heatmaps` · **Template:** `mvp_heatmaps.html` (`routes_mvp.py:1649`) · **Screenshot:** `49-heatmaps.png`
- **Nav path:** Enterprise GRC → Executive Heatmaps
- **Purpose:** CIO/MD heatmaps — framework, application, BU, regional, SLA.
- **Inputs:** period (month/quarter/year) · **Drilldowns:** `/mvp/risk-register`, `/mvp/completeness`

### Integrations Hub
- **URL:** `/mvp/integrations-hub` · **Template:** `mvp_integrations_hub.html` (`routes_mvp.py:1653`) · **Screenshot:** `50-integrations-hub.png`
- **Purpose:** Enterprise integration orchestration (ServiceNow, Jira, Prisma, SonarQube…).
- **Actions:** `POST /mvp/integrations-hub/sync`, `/mvp/module/action`
- **Charts:** connector usage by application, health distribution, executive bar + sparkline

### Cross-Tool Correlation
- **URL:** `/mvp/correlation` · **Template:** `mvp_correlation.html` (`routes_mvp.py:1664`) · **Screenshot:** `51-correlation.png`
- **Purpose:** Incident → remediation → control-failure correlation chains.
- **Dependencies:** `correlation_engine.py`

### Governance Analytics
- **URL:** `/mvp/governance-analytics` · **Template:** `mvp_governance_analytics.html` (`routes_mvp.py:1668`) · **Screenshot:** `52-governance-analytics.png`
- **Purpose:** Enterprise governance intelligence — readiness, rejection patterns, SLA, freshness, app risk.
- **Charts:** Implementation Coverage, Observations, Rejection Rate (intel trend blocks)
- **Drilldowns:** `/api/grc-demo/governance/drill`, `/governance/intel`, `/mvp/api/analytics-intel`

---

## Group 7 — AI SDLC Governance

Routes in `modules/ai_sdlc/routes/routes_ai_sdlc_governance.py`.

### AI SDLC Home
- **URL:** `/mvp/ai-sdlc` · **Template:** `mvp_ai_sdlc_home.html` (`:92`) · **Screenshot:** `53-ai-sdlc-home.png`
- **Nav path:** AI SDLC Governance → Home
- **Purpose:** Landing for AI/SDLC governance; entry to all sub-pages.

### AI SDLC Control Tower
- **URL:** `/mvp/ai-sdlc/control-tower` · **Template:** `mvp_ai_sdlc_control_tower.html` (`:97`) · **Screenshot:** `54-ai-sdlc-control-tower.png`
- **Purpose:** Framework×application readiness heatmap and monitoring.
- **Drilldowns:** `/api/ai-sdlc/control-tower/{tab/{id}|drill/readiness|drill/framework|work-item/{id}}`

### AI SDLC Application Onboarding
- **URL:** `/mvp/ai-sdlc/onboarding` · **Template:** `mvp_ai_sdlc_onboarding.html` (`:128`) · **Screenshot:** `55-ai-sdlc-onboarding.png`
- **Purpose:** Onboard an application into AI SDLC governance.
- **Drilldowns:** `/api/ai-sdlc/onboarding/{run|drill/framework|drill/application}`

### SDLC Stage Worklists (5)
- **URLs:** `/mvp/ai-sdlc/requirements`, `/design`, `/development`, `/testing`, `/golive` · **Template:** `mvp_ai_sdlc_worklist.html` (`:159`) · **Screenshots:** `56-…requirements`, `57-…design`, `58-…development`, `59-…testing`, `60-…golive`
- **Purpose:** Stage-gated worklist of framework→control→evidence activities per SDLC stage.
- **Drilldowns:** `/api/ai-sdlc/sdlc/{drill|stage}`, `/controlled-document`, `/control-drill`, `/observation-drill`
- **Actions:** `POST /api/ai-sdlc/workflow/action`

### Evidence Collection (AI SDLC)
- **URL:** `/mvp/ai-sdlc/evidence` · **Template:** `mvp_ai_sdlc_worklist.html` (`:168`) · **Screenshot:** `61-ai-sdlc-evidence.png`
- **Purpose:** Evidence collection status by framework (collected/required, approved %).
- **Drilldowns:** `/mvp/ai-sdlc/evidence/view/{evidence_id}` (`mvp_ai_sdlc_evidence_viewer.html`)

### Findings & Remediation (AI SDLC)
- **URL:** `/mvp/ai-sdlc/findings` · **Template:** `mvp_ai_sdlc_worklist.html` (`:183`) · **Screenshot:** `62-ai-sdlc-findings.png`
- **Purpose:** Open findings by app/framework/owner/severity with remediation.

### AI SDLC Reports
- **URL:** `/mvp/ai-sdlc/reports` · **Template:** `mvp_ai_sdlc_reports.html` (`:188`) · **Screenshot:** `63-ai-sdlc-reports.png`
- **Purpose:** Index of 6 AI SDLC reports. · **Drilldowns:** `/mvp/ai-sdlc/reports/{report_id}` (`mvp_ai_sdlc_report.html`)

### AI Governance Posture
- **URL:** `/mvp/ai-governance` · **Template:** `mvp_ai_governance_posture.html` (`:330`) · **Screenshot:** `64-ai-governance-posture.png`
- **Nav path:** (AI SDLC area; landing for AI Governance Owner)
- **Purpose:** AI Compliance Score across 6 weighted dimensions; risk heatmap; evidence trend.
- **Drilldowns:** `/api/ai-sdlc/posture/drill`, `/mvp/ai-registry`
- **Dependencies:** `ecs_ai_governance_drilldowns.py`

### AI Model & Prompt Registry
- **URL:** `/mvp/ai-registry` · **Template:** `mvp_ai_registry.html` (`:336`) · **Screenshot:** `65-ai-registry.png`
- **Purpose:** Registry of AI models/prompts under governance. · **Drilldowns:** `/api/ai-sdlc/registry/drill`

### Governance Quality
- **URL:** `/mvp/governance-quality` · **Template:** `mvp_governance_quality.html` (`:393`) · **Screenshot:** `66-governance-quality.png`
- **Purpose:** Governance QA scan & validation (data completeness, readiness, validation %).
- **Drilldowns:** `/api/ai-sdlc/governance-quality`, `/governance-scan` · **Dependencies:** `ecs_governance_qa_engine.py`

---

## Probes & utility (non-screen)

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | Liveness → `{"status":"ok"}` |
| `GET /readyz` | Readiness (Postgres `SELECT 1`) → 200/503 |
| `GET /logout` | Clear session → `/` |
| `GET /evidence/repository`, `/evidence/{id}` | Evidence repository JSON |

See `ECS_FEATURE_REFERENCE.md` for the complete action/API/drill/export catalog, and `ECS_KPI_DICTIONARY.md` for every KPI and chart referenced here.
