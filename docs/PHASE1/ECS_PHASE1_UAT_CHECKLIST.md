# ECS Phase 1 — UAT Readiness Checklist

**Type:** Documentation only. No code modified.
**Date:** 2026-06-17
**Companion:** `ECS_PHASE1_IMPLEMENTATION_BACKLOG.md` (item IDs),
`ECS_PHASE1_GAP_ANALYSIS.md`.

Work top-to-bottom. Every item is **configuration / data / provisioning /
testing** — no source code changes are required to reach UAT. Mark each ✅ before
promotion.

---

## A. Pre-requisites (provisioning)

- [ ] **B08** Evidence repository PostgreSQL provisioned for UAT; reachable from ECS.
- [ ] **B09** Object store (MinIO/S3) provisioned with bucket + credentials.
- [ ] **B11** `psycopg2` (+ any DB drivers) present in the UAT runtime image.
- [ ] **B16** (optional for AI) Ollama + pgvector reachable; embedding model pulled.

## B. Configuration (`config/environments/uat.yaml`)

- [ ] **B01** App hosts/`base_url` set for in-scope applications.
- [ ] **B05** Remaining application slots populated or explicitly disabled.
- [ ] **B01** `databases.postgres` points at the UAT evidence repository.
- [ ] **B01** `connectors.*` URLs set for in-scope source systems; others `enabled: false`.
- [ ] **B03** `predefined_query_targets.postgresql/.sonarqube/.linux` set to real UAT systems (not demo defaults).
- [ ] **B04** `predefined_query_targets.os_servers/db_servers/middleware_servers/appsec_targets` replaced with the real UAT inventory (no `10.10.x` placeholders).
- [ ] `reporting.export_path` set to a writable UAT location.

## C. Secrets (environment variables — never in YAML)

- [ ] **B06** `ECS_REPO_PG_PASSWORD` (evidence repo)
- [ ] **B06** `ECS_PG_PASSWORD` (predefined-query PG target)
- [ ] **B06** Connector secrets: `JIRA_TOKEN`, `CONFLUENCE_TOKEN`, `SNOW_USER`/`SNOW_PASSWORD`, `GITHUB_TOKEN`, `GITEA_TOKEN`, `SONAR_TOKEN`, `JENKINS_USER`/`JENKINS_TOKEN`, `AZDO_TOKEN`, `MS_*` as applicable.
- [ ] **B06** `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY`.

## D. Validation (must pass)

- [ ] **B12** `ECS_ENV=uat python -m config.config_validation` → **PASS** (0 errors).
- [ ] App starts cleanly: `ECS_ENV=uat python -m uvicorn app.main:app …` (startup logs show `Active environment: uat`, repository ready).
- [ ] `python -m config.config_validation --all` still PASS (no regressions to other envs).

## E. Functional smoke (per persona × page)

- [ ] **B13** All routes return HTTP 200/303 for every persona (target parity with demo: 66 routes, 12+ personas, 0 failures).
- [ ] Integration Health: enabled connectors reachable or fail gracefully (no 500s).
- [ ] Predefined Queries: live execution against a real target succeeds and records evidence.
- [ ] Evidence Explorer: records load from the UAT repository (not demo fallback) for at least one connector.
- [ ] Reports: a report pack exports to `reporting.export_path`.
- [ ] AI assistant (if enabled): grounded answer returns with citations.

## F. Quality gates

- [ ] **B14** Unit-test suite green (or the 2 pre-existing failures triaged/fixed and documented).
- [ ] **B15** Load test at expected UAT concurrency — no 5xx, acceptable latency.
- [ ] Linter clean on changed files (no changes expected for UAT config-only path).

## G. UAT sign-off

- [ ] Validation gate green in the UAT pipeline (**B12**).
- [ ] Smoke automation green (**B13**).
- [ ] UAT business owner sign-off recorded.

---

### UAT GO criteria
All of **A–E** complete and **D/E** green. F/G recommended before broad UAT.
At that point ECS is **READY AFTER CONFIGURATION → UAT**.
