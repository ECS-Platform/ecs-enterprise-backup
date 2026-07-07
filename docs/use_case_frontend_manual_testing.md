# ECS Use-Case Frontend Manual Testing Guide

**Purpose:** Manual UAT steps for each of the 19 ECS use cases, from the UI. Each
entry gives the screen/URL, role/persona, prerequisites, test data, steps,
expected result, pass/fail criteria, and known limitations.

**Environment (local/demo):**
```bash
export DEMO_MODE=true ECS_AUTH_ENABLED=false ECS_VALIDATE_CONFIG=off
PYTHONPATH=. uvicorn app.main:app --port 8000
# then browse http://127.0.0.1:8000<route>?role=<role>&user=<name>
```
Most pages accept `?role=` and `?user=` query params. Roles seen in the app:
`owner`, `cio`, `compliance-head`, `vertical-head`, `functional-head`, `auditor`.

---

## Phase 1

### 1. Automated scheduled evidence pull
- **Screen/URL:** `GET /mvp/scheduler`
- **Role/persona:** Compliance owner / operator (`role=owner`)
- **Prerequisites:** App running in `DEMO_MODE`. For UAT dry-run, a populated
  `config/uat_assets.local.yaml` (copy from `config/uat_assets.template.yaml`).
- **Test data:** Default seeded schedules; UAT assets from the local YAML.
- **Frontend steps:** 1) Open `/mvp/scheduler`. 2) Review the schedule list,
  cron timeline, and last-run summary. 3) Click **Run** (or POST `/mvp/scheduler/run`).
  4) (CLI dry-run) run `python scripts/run_uat_asset_scheduler.py --dry-run`.
- **Expected result:** Manual run records a pull; the page shows an updated
  last-run status; the CLI prints a deterministic plan with classified assets and
  routes (no live calls).
- **Pass/fail:** PASS if the manual trigger returns without error and the run/plan
  is reflected; FAIL on 500 or empty/erroring plan.
- **Known limitation:** No always-on cron/worker process; scheduling is manual
  trigger + dry-run planner (`enqueue_scheduled_run` is a hook, not a daemon).

### 2. Bulk evidence upload
- **Screen/URL:** `GET /mvp/upload` (bulk form posts to `/mvp/upload/bulk`)
- **Role/persona:** Evidence uploader (`role=owner`)
- **Prerequisites:** App running.
- **Test data:** 2–3 small sample files (e.g. `.txt`/`.pdf`), a framework
  (e.g. `PCI DSS`), an application (e.g. `Net Banking`).
- **Frontend steps:** 1) Open `/mvp/upload`. 2) Select framework + application.
  3) Choose multiple files. 4) Submit.
- **Expected result:** Redirect with a success count; files registered in the
  evidence repository with the enforced naming convention.
- **Pass/fail:** PASS if all selected files are accepted and a success count is
  shown; FAIL if upload errors or no confirmation.
- **Known limitation:** Bulk path captures framework+application only and returns
  a count (no per-file error array); use `POST /evidence/upload` for richer
  per-file metadata + JSON error envelope.

### 3. Metadata tagging & naming convention
- **Screen/URL:** `GET /mvp/evidence-health` (view naming) + `GET /mvp/search`
  (search by metadata); API `GET /api/audit/evidence?tag=&framework=&technology=`
- **Role/persona:** Auditor / owner
- **Prerequisites:** At least one uploaded/collected evidence item (do UC #2 first).
- **Test data:** Framework `PCI DSS`, application `Net Banking`.
- **Frontend steps:** 1) Upload a file (UC #2). 2) Open `/mvp/evidence-health` and
  confirm the stored filename follows `{PREFIX}_{APP}_{YYYYMMDD}_{file}`. 3) Open
  `/mvp/search`, filter by framework/application/owner/status.
- **Expected result:** Filename is normalized; the item is findable by its tags.
- **Pass/fail:** PASS if naming is applied and search returns the item; FAIL if
  the name is unmodified or the item is not searchable.
- **Known limitation:** No dedicated tag-normalization UI or naming-validation API
  beyond `enforce_naming()` at ingest; `period`/`owner` are first-class only in the
  MVP upload layer.

### 4. Evidence dashboard & hash integrity check
- **Screen/URL:** `GET /mvp/evidence-health`
- **Role/persona:** Auditor / owner
- **Prerequisites:** ≥1 evidence item.
- **Test data:** Any uploaded evidence.
- **Frontend steps:** 1) Open `/mvp/evidence-health`. 2) Review per-item SHA-256
  hash + integrity status. 3) (Packs) build a pack via `/mvp/audit/packs` or
  `GET /api/audit/packs/framework/PCI DSS` and confirm `pack_hash`/`verify` is true.
- **Expected result:** Each item shows a SHA-256 hash and an integrity/tamper
  status; pack manifest verification returns true.
- **Pass/fail:** PASS if hashes render and integrity status is shown/verified;
  FAIL if hashes are missing or verification errors.
- **Known limitation:** No interactive "re-verify this file now" button/API
  (`integrity_check()` runs at ingest; pack verification is the exposed check).

### 5. Common evidence querying
- **Screen/URL:** `GET /mvp/predefined-queries` (+ `/mvp/search`)
- **Role/persona:** Auditor / owner
- **Prerequisites:** App running (catalog loads at startup).
- **Test data:** Technology filter `Aerospike` or `PostgreSQL`; framework `PCI DSS`.
- **Frontend steps:** 1) Open `/mvp/predefined-queries`. 2) Filter by
  technology/framework/status; search by control ID/name. 3) Open a control's
  **View**; optionally click **Run Query**.
- **Expected result:** The filtered control list updates; a runnable control
  executes and records evidence.
- **Pass/fail:** PASS if filtering works and a runnable control executes; FAIL on
  empty catalog or run error for a `Ready` control.
- **Known limitation:** Export of query *results* is via the gap/report export
  utilities, not a direct per-query CSV button.

## Phase 2

### 6. Evidence completeness detection
- **Screen/URL:** `GET /mvp/completeness`
- **Role/persona:** Compliance head (`role=compliance-head`)
- **Prerequisites:** App running (uses seeded/collected evidence).
- **Test data:** Framework `PCI DSS`, application `Net Banking`.
- **Frontend steps:** 1) Open `/mvp/completeness`. 2) Review expected-vs-available
  matrix, completeness %, and missing/gap list. 3) Optionally export gaps via
  `/mvp/comparison`.
- **Expected result:** A completeness percentage and a list of missing controls/
  evidence are shown.
- **Pass/fail:** PASS if a % and gap list render; FAIL on error/empty when data
  exists.
- **Known limitation:** The page route uses the simpler `completeness_report()`;
  the richer matrix (`build_completeness_dashboard`) is available via the
  module-view context. No standalone completeness REST API.

### 7. Evidence similarity & reuse
- **Screen/URL:** `GET /mvp/reuse` (+ `GET /mvp/evidence-reuse-story`)
- **Role/persona:** Owner / auditor
- **Prerequisites:** App running; for vector search, PGVector configured (else
  keyword fallback).
- **Test data:** Existing evidence set.
- **Frontend steps:** 1) Open `/mvp/reuse`. 2) Review reuse suggestions / reuse
  graph / duplicate groupings. 3) Open the reuse story page for the narrative.
- **Expected result:** Reuse candidates / groups are displayed.
- **Pass/fail:** PASS if suggestions/graph render without error; FAIL on crash.
- **Known limitation:** Evidence-artifact similarity via PGVector is used in the
  RAG path, not surfaced as a dedicated `/api/evidence/similar`; the reuse score
  (`score_reuse`) is rule-based (no embeddings) and flag-gated.

### 8. AI-generated evidence summaries
- **Screen/URL:** `GET /mvp/ai-ops-assistant/summary/{mode}` (modes: `business`,
  `technical`, `executive`, `audit`, `compliance`, `evidence`)
- **Role/persona:** Executive / auditor
- **Prerequisites:** App running; for live LLM, a provider configured via env
  (else offline fallback text).
- **Test data:** `mode=executive`.
- **Frontend steps:** 1) Open `/mvp/ai-ops-assistant/summary/executive`. 2) Read
  the generated summary. 3) Try the copilot chat on `/mvp/ai-ops-assistant`.
- **Expected result:** A coherent summary renders; with no LLM configured, a clear
  offline fallback message is shown (never a crash).
- **Pass/fail:** PASS if a summary or offline fallback renders; FAIL on error.
- **Known limitation:** Per-artifact "summarize this evidence" LLM action is not a
  dedicated endpoint; `evidence_repository.generate_summary()` is deterministic
  template text, not provider-backed.

### 9. Natural language audit queries
- **Screen/URL:** Copilot on `/mvp/ai-ops-assistant`; API `POST /chat`,
  `GET /api/platform/assistant?q=`
- **Role/persona:** Auditor / executive
- **Prerequisites:** App running; RAG index warm improves grounding (optional).
- **Test data:** Question e.g. *"Which PCI DSS controls are missing evidence for
  Net Banking?"*
- **Frontend steps:** 1) Open the copilot. 2) Ask the question. 3) Review the
  answer and its evidence citations/source references.
- **Expected result:** A relevant answer with citations (or a safe grounded
  fallback) — never a hallucinated, source-less claim.
- **Pass/fail:** PASS if an answer with citations/fallback returns; FAIL on error
  or an ungrounded claim without sources.
- **Known limitation:** Answer quality depends on RAG index state / provider
  availability; keyword fallback is used when RAG is not grounded.

### 10. Leadership compliance dashboards
- **Screen/URL:** `GET /mvp/audit/executive-readiness` (alias `/mvp/audit/dashboard`);
  `GET /dashboard/cio`
- **Role/persona:** CIO / compliance head (`role=cio`)
- **Prerequisites:** App running.
- **Test data:** —
- **Frontend steps:** 1) Open the executive readiness page. 2) Review compliance
  posture, missing-evidence count, open observations, closure aging, framework
  readiness. 3) Open `/dashboard/cio` for persona widgets.
- **Expected result:** Executive KPIs and framework-level readiness render.
- **Pass/fail:** PASS if all widgets render with numbers; FAIL on error/blank.
- **Known limitation:** Two dashboards coexist (audit-intelligence
  `executive_readiness` vs demo `enterprise_dashboard`); some persona widgets use
  seeded demo metrics.

## Phase 3

### 11. Multi-application onboarding
- **Screen/URL:** `GET/POST /mvp/onboarding` (demo); `GET/POST /mvp/platform/onboarding` (DB)
- **Role/persona:** Platform admin / owner
- **Prerequisites:** App running.
- **Test data:** App name `Retail Banking`, owner `owner@example`, business unit
  `Retail`, frameworks `PCI DSS, ISO 27001`, tech stack `PostgreSQL, NGINX`.
- **Frontend steps:** 1) Open `/mvp/onboarding`. 2) Fill app metadata + owner +
  framework scope + technology. 3) Submit / simulate. 4) Confirm in
  `/mvp/platform/inventory`.
- **Expected result:** The application is onboarded with its metadata, owner,
  framework scope, and technology mapping.
- **Pass/fail:** PASS if the app appears with correct metadata; FAIL if not
  persisted/listed.
- **Known limitation:** Two onboarding flows (demo simulator + platform DB) are
  separate; no single unified transactional onboarding API.

### 12. Evidence lifecycle management
- **Screen/URL:** `GET /mvp/lifecycle`; `GET/POST /mvp/platform/evidence-lifecycle`;
  observations transition via `/mvp/audit/observations` UI or API.
- **Role/persona:** Reviewer / approver
- **Prerequisites:** ≥1 evidence item or observation.
- **Test data:** An observation ID; a `to_status` of `Submitted`/`Approved`.
- **Frontend steps:** 1) Open `/mvp/lifecycle` to view the status timeline +
  audit trail. 2) In platform lifecycle, review an item and set retention
  (`valid_days`). 3) Transition an observation (Draft→Submitted→Approved).
- **Expected result:** Status transitions are recorded with an audit trail;
  retention metadata is captured.
- **Pass/fail:** PASS if transitions persist with history; FAIL if a transition
  errors or leaves no trail.
- **Known limitation:** Three lifecycle models coexist (observation `OBS_WORKFLOW`,
  platform `_REVIEW_STATES` incl. `Expired`, evidence-intel `EvidenceStatus`);
  `Reviewed`/`Archived` are not unified across all three.

### 13. Cross-application compliance comparison
- **Screen/URL:** `GET /mvp/comparison`
- **Role/persona:** Compliance head / vertical head
- **Prerequisites:** App running (multiple apps in demo data).
- **Test data:** Framework `PCI DSS`, compare scope = all applications.
- **Frontend steps:** 1) Open `/mvp/comparison`. 2) Review the readiness matrix /
  heatmap / pair comparison. 3) Export gaps (`export_format=excel|csv|pdf`) →
  download.
- **Expected result:** Apps are compared across framework/control/readiness; export
  produces a file.
- **Pass/fail:** PASS if the comparison renders and export downloads; FAIL on error.
- **Known limitation:** Comparison data is demo/mock-seeded.

### 14. SharePoint & ServiceNow integration
- **Screen/URL:** `GET /mvp/integrations`; API `GET /api/audit/integrations` and
  `/integrations/health`
- **Role/persona:** Platform admin
- **Prerequisites:** App running. For live checks, set `ECS_GRAPH_*` /
  `ECS_SERVICENOW_*` in `.env.uat` (never committed).
- **Test data:** Leave unset for config-only; or set placeholders for masked view.
- **Frontend steps:** 1) Open `/mvp/integrations`. 2) Review adapter health/status.
  3) API: `GET /api/audit/integrations/health` and `/sharepoint_graph/health`,
  `/servicenow_cmdb/health`. 4) CLI: `python scripts/run_uat_connector_health.py
  --adapter all --no-network`.
- **Expected result:** Adapters report `configured`/`not_configured` with masked
  config (SET/MISSING) — no secret values, no crash when unconfigured.
- **Pass/fail:** PASS if health returns for both adapters and no secret leaks;
  FAIL on error or a leaked secret.
- **Known limitation:** Adapters are config-driven skeletons; live tenant calls
  require real credentials + `--live`.

### 15. Enterprise compliance dashboards
- **Screen/URL:** `GET /mvp/enterprise`
- **Role/persona:** CIO / executive
- **Prerequisites:** App running.
- **Test data:** —
- **Frontend steps:** 1) Open `/mvp/enterprise`. 2) Review enterprise rollups
  (phase/app/framework aggregation, national score, regions). 3) Drill into a
  framework/app.
- **Expected result:** Enterprise-level rollups render with drilldown-ready detail.
- **Pass/fail:** PASS if rollups + drilldown render; FAIL on error/blank.
- **Known limitation:** Enterprise rollup and audit-intelligence dashboard are
  separate data sources (not one canonical API).

## Pan India

### 16. Automated regulatory reporting
- **Screen/URL:** `GET /mvp/reports`
- **Role/persona:** Compliance head
- **Prerequisites:** App running.
- **Test data:** Report = `Pan India Regional Compliance Report`; format `pdf`.
- **Frontend steps:** 1) Open `/mvp/reports`. 2) Pick a report, framework, app.
  3) Download in `pdf`/`excel`/`csv`. 4) Optionally view HTML via
  `/mvp/reports/view/{report_type}`.
- **Expected result:** A scoped report file downloads (or HTML view renders) with
  summary + exception stats.
- **Pass/fail:** PASS if the file downloads / view renders; FAIL on error.
- **Known limitation:** Markdown is not a first-class export format; reports use
  summary stats (not deep per-evidence references) in PDFs.

### 17. AI-assisted audit preparation
- **Screen/URL:** `GET /mvp/audit-prep`; evidence packs `GET /mvp/audit/packs`
- **Role/persona:** Auditor / compliance head
- **Prerequisites:** App running; provider configured for live AI notes (else
  offline).
- **Test data:** Upcoming audit context; framework `PCI DSS`.
- **Frontend steps:** 1) Open `/mvp/audit-prep`. 2) Review the preparation
  checklist + package preview + upcoming audits. 3) Build/verify an evidence pack
  on `/mvp/audit/packs`.
- **Expected result:** A prep checklist and evidence-pack readiness render; pack
  manifest verifies.
- **Pass/fail:** PASS if checklist + pack readiness render/verify; FAIL on error.
- **Known limitation:** No dedicated AI-prep-notes generator; AI assistance is via
  the general copilot/RAG; offline fallback applies when no provider is configured.

### 18. Compliance trend & closure
- **Screen/URL:** `GET /mvp/trends`
- **Role/persona:** Compliance head / CIO
- **Prerequisites:** App running.
- **Test data:** Framework `PCI DSS`, time period `last 90 days`, region filter.
- **Frontend steps:** 1) Open `/mvp/trends`. 2) Review closure rate, avg days to
  close, aging buckets, rejection/SLA trends, repeat observations. 3) Drill into a
  KPI (`/api/ecs/universal-drill?page=trends`).
- **Expected result:** Trend series + closure velocity + aging analysis render.
- **Pass/fail:** PASS if trends + closure/aging render; FAIL on error/blank.
- **Known limitation:** Trend/closure/aging live in governance engines (mock/
  seeded), not in `dashboard_service`.

### 19. National compliance dashboard
- **Screen/URL:** `GET /mvp/pan-india?role=cio&user=CIO`
- **Role/persona:** CIO / national leadership
- **Prerequisites:** App running.
- **Test data:** —
- **Frontend steps:** 1) Open `/mvp/pan-india`. 2) Review national KPIs, regional
  charts (North/South/East/West/Central), zone heatmap, framework matrix.
- **Expected result:** A pan-India rollup with regional/app/framework/status
  summaries and executive KPIs renders.
- **Pass/fail:** PASS if the national dashboard renders with regional breakdowns;
  FAIL on error/blank.
- **Known limitation:** No dedicated `/api/national` REST endpoint; data is
  server-rendered from seeded regional aggregation (not a live regional DB).

---

## General known limitations (apply broadly)

- Demo mode uses seeded/mock datasets for many dashboards; live UAT numbers differ.
- Auth is bypassed in `DEMO_MODE`; role is a query param. In UAT/prod, enable
  auth/RBAC.
- Connector live calls require real credentials via env/secret manager (never
  committed); unconfigured adapters degrade to `not_configured`.

Cross references: [use_case_implementation_matrix.md](use_case_implementation_matrix.md) ·
[use_case_backend_api_mapping.md](use_case_backend_api_mapping.md) ·
[use_case_uat_readiness_report.md](use_case_uat_readiness_report.md).
