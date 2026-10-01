# ECS Functional Test Automation Framework

Implements automation for the **331 functional tests (UC01–UC20)** in `ECS_Consolidated_Functional_Test_Pack_UC01_UC20.xlsx`.
Code lives in `tests/functional/`. **The framework has been implemented only — nothing has been executed or validated.**

## 1. Design in one picture

```
workbook (.xlsx) ──tools/build_registry.py──▶ registry/ecs_test_registry.json   (single source of test metadata)
                                                   │
                       tools/generate_tests.py ◀───┤  one pytest function per Functional Test ID  (usecases/ucNN/test_ucNN.py)
                                                   │
usecases/ucNN/orchestration.py  ◀── @case(...) bindings (UC-specific orchestration only) + register_crosscutting(PROFILE)
        │                                          │
        ▼                                          ▼
framework/scenarios.py (shared flows)     framework/crosscutting.py (14 generic "Validate <topic> …" scenarios)
        │
        ▼
framework helpers ─▶ real ECS: HTTP API / UI / PostgreSQL / object store / scheduler / audit_log
        │
tools/build_traceability.py ─▶ docs/functional-test-traceability.yaml
```

* **160 use-case-specific tests** (FT001–FT008 of each sheet) → explicit orchestration in `usecases/ucNN/orchestration.py`.
* **171 generated "Validate <topic> for <UC>" tests** → 14 topic scenarios implemented **once** in `framework/crosscutting.py`,
  parameterised by each UC's `UseCaseProfile` (its real ECS page / API / trigger). No per-UC duplication.
* IDs are preserved exactly (`test_uc01_ft001` ↔ `UC01-FT001`). Nothing renumbered, merged or dropped.

## 2. Layout (`tests/functional/`)

| Path | Purpose |
|---|---|
| `config/environments.yaml` | per-env base/API/UI URL, auth mode, DB, object store, UI, timeouts, polling, **feature flags**, hooks (`${VAR:-default}`; secrets only as env-var *names*) |
| `config/test_data.yaml` | deterministic seed, real ECS personas, RBAC expectation matrix (derived from `role_permissions.py`), catalogue values |
| `config/thresholds.yaml` | SLA placeholders (`null` – workbook defines none), concurrency + polling settings |
| `framework/api_client.py` | GET/POST/PUT/PATCH/DELETE, persona identity, `X-Request-ID` correlation, history capture, `http` or `inprocess` (TestClient) transport |
| `framework/assertions.py` | `assert_success/failure/status/denied/exists/not_exists/equal/not_equal/contains/not_contains/json_field/schema/record_exists/record_count/hash/metadata/audit_record/role_access/notification/dashboard_value/report_value/version/traceability/compliance_mapping/retention_state/reconciles` |
| `framework/wait.py` | `wait_until`, `poll_job_status`, `wait_for_evidence/scheduler_execution/ingestion/processing/notification` (timeout, interval, terminal states, `WaitTimeout`/`TerminalStateError`) |
| `framework/db.py` | read-only PostgreSQL helper restricted to the **real tables** of `ecs_platform/repository/*.sql` |
| `framework/storage.py` | reads ECS's real object store (`LocalObjectStore` layout / MinIO via boto3); key builder reused from `object_store.py` |
| `framework/evidence.py · scheduler.py · connectors.py · audit.py · notification.py` | domain helpers over the real ECS routes |
| `framework/dashboard.py` | dashboards, search/filter/drill-down, compliance, reporting helpers |
| `framework/ai.py` · `lifecycle.py` · `security.py` · `correlation.py` | AI query/grounding/no-answer/failure; version/retention/onboarding; RBAC/security/concurrency/performance; id correlation |
| `framework/ui/` | Playwright helper (login, nav, forms, dropdowns, upload, tables, search, filters, widgets, drill-down, modal, notifications, download, role visibility) + `selectors.py` (**only ids/names that exist in ECS templates**) |
| `framework/data_factory.py` | deterministic data for application/framework/control/evidence/metadata/file/connector/schedule/audit/user-role/report/notification/observation |
| `framework/evidence_capture.py` · `results.py` | failure-evidence hooks and result rows (Test ID, UC, name, priority, status, time, error, evidence, request/execution/evidence IDs) |
| `framework/context.py` | `FunctionalContext`: all helpers on one client; lazy connections; capability gating |
| `registry/ecs_test_registry.json` | generated registry (UC → tests; priority, type, topic, automation capability, dependencies, markers) |
| `usecases/uc01 … uc20/` | `orchestration.py` (UC-specific) + generated `test_ucNN.py` |
| `conftest.py` | markers, fixtures, collection guard, result/evidence hooks |

## 3. Safety defaults (why nothing runs by accident)

* `pytest tests/` does **not** run these tests: every functional test is skipped at collection unless `--run-functional` or `ECS_FT_ENABLE=1`.
* Data-changing cases need `ECS_FT_ALLOW_MUTATION=true`; destructive (tamper/retention) `ECS_FT_ALLOW_DESTRUCTIVE`; security probes
  `ECS_FT_ALLOW_SECURITY_PROBES`; concurrency `ECS_FT_ALLOW_CONCURRENCY`; performance `ECS_FT_ALLOW_PERFORMANCE`; live connectors
  `ECS_FT_LIVE_CONNECTORS`; DB validation `ECS_FT_DB_ENABLED`; UI `ECS_FT_UI_ENABLED`.
* Where ECS lacks a capability or a flag/config value is missing, the helper raises `CapabilityBlocked` → **skip with the reason** (never a pass).
* No ECS production code was modified. No fake API/DB/storage/scheduler/auth/AI was created; every path used was cross-checked against the ECS route decorators.

## 4. Unsupported / blocked automation points (found in the real ECS implementation)

| # | Gap | Effect |
|---|---|---|
| 1 | No schedule **update/delete** API, no cron field (only `POST /mvp/platform/scheduler` upsert by name) | schedule-update steps → `SchedulerHelper.update_schedule` blocked |
| 2 | No process **restart** API | UC01-FT008, UC03-FT008, UC05-FT008, UC07-FT008 need `ECS_FT_RESTART_CMD` (harness-owned command) |
| 3 | No **retention-policy** configuration or **archival** trigger (only `evidence_reviews.valid_until` via lifecycle review); object store is immutable | all 19 "Validate retention and archival" cases assert the lifecycle view then block at the archival step; UC14-FT005 asserts `valid_until` only |
| 4 | No evidence **delete/update** endpoint | UC14-FT006 asserts DELETE/PUT/PATCH are not offered |
| 5 | No **e-mail/SMS** provider; notifications = redirect `notice=` text, the in-app feed, a logged Teams action | notification cases assert the in-app notice; e-mail delivery is blocked by design |
| 6 | No **common-control create/edit** API (read-only `/api/common-controls*`) | UC07-FT001 (existence only) and UC07-FT005 blocked |
| 7 | No metadata **edit** endpoint; `validate-metadata` checks required-ness only | UC03-FT006 needs DB `audit_log`; UC03-FT005 blocks if values are unconstrained |
| 8 | `POST /workflow/upload-version` only logs an audit event; versions are created by re-upload | versioning cases use re-upload + `/api/audit/evidence/{key}/versions` |
| 9 | `/api/demo/audit-history` and `/api/demo/prompt-audit` return **generated demo rows**; the in-memory audit trail has no API | real audit proof = PostgreSQL `audit_log` (`request_id`); without DB the audit helper falls back to scheduler history + "Recent Activity" feed |
| 10 | `DEMO_MODE` / `ECS_LOCAL_AUTH_BYPASS` bypass authentication (and DEMO_MODE bypasses page/RBAC guards) | auth-enforcement cases require a bearer-auth environment + `ECS_FT_TOKEN_<PERSONA>`; route-level role checks (upload, scheduler execute) still work in demo mode |
| 11 | No login **session/logout** (identity is the `role`/`user` pair) | `UiSession.login_as` drives the login form; `logout` only discards identity |
| 12 | Only `run_id` exists (no separate job/execution id) | `execution_id`/`job_id` alias `run_id` in `CorrelationTracker` |
| 13 | AI/vector failure cannot be injected over HTTP | UC10-FT007, UC11-FT007, UC18-FT007 need ECS started with the provider disabled + `ECS_FT_AI_FAILURE_READY=true` |
| 14 | Workbook defines **no numeric SLA** | performance cases (10) skip until `config/thresholds.yaml` values are set |
| 15 | Templates have **no `data-testid`** | UI selectors use existing ids/names only (`ui/selectors.py`); no UI-driven case bindings were added |
| 16 | Tamper simulation | only against the local object store and only for suite-created objects (`ECS_FT_ALLOW_DESTRUCTIVE`) |
| 17 | Several dashboards are demo/seed-derived | reconciliation cases block when no authoritative total key matches (UC12-FT004, UC16-FT005, UC20-FT005) |
| 18 | Live SharePoint/ServiceNow need credentials | UC04-FT002/004/005/007 need `ECS_FT_LIVE_CONNECTORS=true` + connector secrets configured in ECS |

### Workbook alignment (please review with the workbook owner)
FT001–FT008 of several sheets do not match the sheet title; IDs/descriptions were **preserved verbatim and automated as written**:

| Sheet | Title | FT001–FT008 actually describe |
|---|---|---|
| UC04 | Evidence dashboard and hash integrity check | SharePoint / ServiceNow connector |
| UC05 | Common Evidence Querying (Chatbot) | dashboard + hash integrity |
| UC06 | Evidence completeness detection | predefined queries |
| UC07 | Evidence similarity and reuse | common controls |
| UC08 | AI-generated evidence summaries | completeness detection |
| UC09 | Natural language audit queries | similarity and reuse |
| UC10 | Leadership compliance dashboards | AI evidence summaries |
| UC11 | Multi-application onboarding | natural-language evidence Q&A |
| UC12 | Evidence lifecycle management | leadership dashboards |
| UC13 | Cross-application compliance comparison | application onboarding |
| UC14 | Automated control validation | versioning / retention / lifecycle |
| UC15 | SharePoint, SNOW integration | application comparison |

The generated cross-cutting rows (FT009+) use the sheet **title**, so each UC's `UseCaseProfile` follows the title.

## 5. Future execution (not run as part of this work)

```bash
pip install -r tests/functional/requirements-functional.txt
# optional UI: playwright install chromium
# regenerate (only if the workbook changes)
python tests/functional/tools/build_registry.py <path-to-workbook.xlsx>
python tests/functional/tools/generate_tests.py
python tests/functional/tools/build_traceability.py

# environment (examples; secrets only via env)
export ECS_FT_ENV=local ECS_FT_BASE_URL=http://localhost:8000 ECS_FT_ENABLE=1
export ECS_FT_ALLOW_MUTATION=true            # data-creating cases
export ECS_FT_DB_ENABLED=true ECS_REPO_PG_PASSWORD=...   # DB/audit validation

pytest tests/functional --run-functional --collect-only -q        # list the 331 mapped tests
pytest tests/functional --run-functional -m uc01                  # one use case
pytest tests/functional --run-functional -m "api and priority_high"
pytest tests/functional --run-functional -m "rbac or security"
pytest tests/functional --run-functional tests/functional/usecases/uc03/test_uc03.py::test_uc03_ft003
```

Results (only produced when tests run): `tests/functional/reports/functional_results.{json,csv}`; failure evidence under
`tests/functional/reports/evidence/<test-id>/`.
