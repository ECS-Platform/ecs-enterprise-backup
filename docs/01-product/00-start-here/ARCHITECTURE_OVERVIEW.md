# ECS — Architecture Overview

A concise, code-grounded tour of how ECS is built. Anchored to the actual tree: `app/`, `modules/`, `ecs_platform/`, `config/`. For deep design docs see `docs/02-architecture/architecture/`, `docs/hld/`, `docs/lld/`, and `docs/02-architecture/diagrams/`.

---

## 1. Mission

ECS (Evidence & Compliance System) automates **evidence collection, compliance assessment, audit readiness, and governance** for regulated (banking) software delivery. It connects to engineering source systems (Git, CI, code-quality, issue trackers, document stores), correlates their artifacts into per-application evidence chains, maps that evidence to control frameworks, and drives a reviewable evidence workflow with durable audit and AI-assisted (citation-grounded) querying.

---

## 2. Architecture style — modular monolith

One FastAPI ASGI app (`app.main:app`) composes domain packages. No microservices; modules are Python packages with `engines/` (logic) and `templates/` (Jinja UI), wired through route registrars.

```
                         ┌─────────────────────────────────────────┐
  Browser (Jinja UI) ───▶│            app/main.py (FastAPI)          │
                         │  env_bootstrap → auth mw → no-cache mw    │
                         │  route registrars (6) → Jinja ChoiceLoader│
                         └───────┬───────────────────────┬──────────┘
                                 │                        │
                   ┌─────────────▼──────────┐   ┌─────────▼───────────────┐
                   │  modules/* (6 domains  │   │  ecs_platform/          │
                   │  + shared core)        │   │  connectors / repository│
                   │  engines + templates   │   │  vectorstore / rag /    │
                   └─────────────┬──────────┘   │  ingestion / governance │
                                 │              └─────────┬───────────────┘
                                 │                        │
                   ┌─────────────▼────────────────────────▼───────────────┐
                   │ PostgreSQL (repository) · pgvector · MinIO · Redis ·  │
                   │ source systems: Gitea/Jenkins/SonarQube/Jira/...      │
                   └───────────────────────────────────────────────────────┘
```

---

## 3. Major modules (`modules/`)

| Module | Responsibility (representative engines) |
|---|---|
| `executive_overview` | Executive dashboards, demo metrics/KPIs, reports, ROI value center, demo seed (`engines/demo_seed.py`). |
| `frameworks` | Framework catalog (`engines/framework_catalog.py`), per-framework dashboards, control validation, framework onboarding/trends/intelligence, ITPP. |
| `operations` | Evidence repository refresh, scheduler, bulk upload, integration health, predefined-query validation, AI-ops assistant. |
| `governance` | Evidence health/approval/review, completeness, audit-prep, governance lifecycle, work queues. |
| `enterprise_grc` | Risk register, CMDB/application governance, exceptions, correlation, heatmaps, governance QA self-heal. |
| `ai_sdlc` | AI-SDLC gates, control tower, AI-governance posture, controlled documents, onboarding, reports. |
| `shared` | Cross-cutting state (`ecs_state`), RBAC/role permissions, evidence workflow engine, universal drilldown, persona UI, logging, chatbot. |

Infrastructure layer `ecs_platform/`: `connectors/`, `repository/` (Postgres evidence store), `vectorstore/` (pgvector), `rag.py` + `llm_engine/`, `ingestion.py` (sync/health), `governance.py`, `rbac/`, `config/loader.py`.

---

## 4. Evidence flow

1. **Collect** — `ecs_platform/connectors/*` pull artifacts from source systems (commits, PRs, branch protections, builds, test results, quality gates, vulnerabilities…). Triggered by `POST /api/platform/sync/{connector}` → `ecs_platform.ingestion.sync_connector`.
2. **Persist** — evidence rows land in the PostgreSQL evidence repository (`ecs_platform/repository/`); raw artifacts go to MinIO object storage.
3. **Correlate** — artifacts sharing an application slug are grouped into a Commit → Build → Scan chain per app (see `demo-data/seed_demo_environment.sh` and `/api/platform/evidence` correlations).
4. **Map** — evidence is mapped to framework controls (`modules/frameworks`), with cross-framework reuse intelligence.
5. **Assess** — deterministic engines (sufficiency, completeness, change detection, reuse — all flag-gated, non-LLM) score evidence.
6. **Review** — the evidence workflow engine (`modules/shared/services/evidence_workflow_engine.py`) drives submit → approve/reject/clarify/escalate/close with toasts and observations.
7. **Audit** — when `AUDIT_WORKFLOW_ENABLED`, durable, attributable audit records (before/after, actor, request_id) are written to Postgres.

In native demo mode steps 1–3 are replaced by deterministic in-memory seed data (`seed_demo_workflow_state()` at startup); the rest behave identically.

---

## 5. Framework & control mapping

- `modules/frameworks/engines/framework_catalog.py` holds the static framework catalog (15 frameworks, e.g. RBI Cyber Security, PCI DSS, ISO 27001, SOC 2, AI-SDLC) and exposes `catalog_stats()`, `get_framework_controls()`, `resolve_framework_name()`.
- Controls and their evidence requirements are mapped per framework; cross-framework reuse groups controls by canonical themes so one piece of evidence satisfies many frameworks.
- Framework dashboards (`framework_dashboards.py`) render KPI tiles, workflow state, and drillable rows per framework at `GET /framework/{framework_name}`.

---

## 6. Audit, reporting & governance workflows

- **Audit workflow:** submit/approve/reject/observation lifecycle/escalation endpoints in `app/main.py` (`/submit`, `/approve`, `/reject`, `/workflow/*`, `/evidence/review/*`), backed by the workflow engine and (optionally) durable audit.
- **Governance:** `modules/governance` provides evidence health, completeness, audit-prep, owner/auditor work queues; `register_governance_routes` mounts them.
- **Reporting:** `modules/executive_overview` reports engine + `openpyxl` for Excel exports (e.g. control library workbook mounted into the container).
- **GRC demo:** `register_grc_demo_routes` exposes the enterprise GRC demonstration surface.

---

## 7. AI-SDLC workflows

`modules/ai_sdlc` implements SDLC governance gates, a control tower, AI-governance posture (prompt audit, hallucination/unsafe-prompt signals, token usage), controlled documents, and reports. Routes are mounted by `register_ai_sdlc_routes`. Its workflow engine/state live alongside the module engines.

---

## 8. ROI workflows

`modules/executive_overview` ROI value center reads **all numbers from `config/roi.yaml`** (deterministic; no LLM). Nav availability is gated by `ROI_CENTER_ENABLED`. ROI logic is covered by `tests/test_roi_engine.py`.

---

## 9. Connector architecture (`ecs_platform/connectors/`)

- A common `base.py` + `factory.py` + shared `http_client.py` define a uniform connector contract; `config/integrations.yaml` declares each connector's `enabled`, `base_url`, `auth_type`, credential env vars, and the `collect:` object types.
- **12 connectors:** `gitea`, `sonarqube`, `jenkins` (live-by-default in dev), plus interface-complete `jira`, `github`, `confluence`, `figma`, `servicenow`, `teams`, `sharepoint`, `prisma_cloud`, `azure_devops` (disabled until onboarded). Microsoft connectors share `_msgraph.py`.
- Connectors fail fast (low timeout, single retry — `defaults` in `integrations.yaml`) so the Integration Health page never hangs on an unreachable source.
- Enable any connector at runtime by setting `ECS_<NAME>_ENABLED=true` and its credentials — no code change (env-resolved YAML).

---

## 10. RBAC architecture (`config/rbac.yaml`, `modules/shared`, `app/auth`)

- **Authentication** (`app/auth/`, `config/auth.yaml`): central middleware validates Azure AD / OIDC JWTs (pluggable provider registry), or passes through when `ECS_AUTH_ENABLED=false` / `DEMO_MODE=true`, or authenticates a static principal in `ECS_AUTH_DEV_MODE`.
- **Authorization** is phased and flag-gated (all default OFF): delegation → enforcement foundation → mutation enforcement → page enforcement → scope filtering (see `docs/03-development/developer-manual/ENVIRONMENT_CONFIGURATION.md` §3). Decisions run through a consolidated PolicyEngine; high-risk mutations and persona dashboards are the guarded surfaces; scope filtering restricts row/list/search data to the principal's assignments (derived from groups like `app:payments-api`).
- Roles/permissions are defined in `config/rbac.yaml` and resolved by `modules/shared/services/role_permissions.py`; mutation guards live in `app/auth/mutation_guard.py`, scope in `app/auth/scope.py`.

---

## 11. Database architecture

| Store | Image / config | Purpose | Host port |
|---|---|---|---|
| Evidence repository | `postgres:16` (`config/repository.yaml`) | System of record for evidence, observations, durable audit | 5433 |
| Vector store | `pgvector/pgvector:pg16` (`config/vectorstore.yaml`) | RAG embeddings (`evidence_embeddings`, dim 768) | 5434 |
| Object store | MinIO (`config/repository.yaml`) | Raw evidence artifacts (bucket `ecs-evidence`) | 9002 / console 9001 |
| Cache/queue | `redis:7-alpine` | Caching / queueing | 6379 |
| Demo-connectors DB | `postgres:16` (`ecs_demo`) | Backing store for demo-connector subsystem | 5432 |

Schema is initialized best-effort at startup (`init_repository()`, `init_governance_schema()`); the app runs without these for the showcase demo.

---

## 12. API architecture

FastAPI routes registered in `app/main.py` via six registrars. Notable endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /` , `POST /login`, `GET /logout` | Entry / role chooser / session |
| `GET /dashboard`, `GET /dashboard/cio` | Persona dashboards |
| `GET /framework/{name}` + `/api/framework/*-drill` | Framework dashboard + drilldowns |
| `POST /submit` `/approve` `/reject` `/workflow/*` `/evidence/review/*` | Evidence workflow lifecycle |
| `POST /chat` | Citation-grounded assistant |
| `GET /healthz` | Liveness (no I/O) → `{"status":"ok"}` |
| `GET /readyz` | Readiness (Postgres `SELECT 1`) → 200/503 |
| `GET /api/platform/health` | Evidence counts by source/type |
| `POST /api/platform/sync/{connector}` | Trigger connector collection (mutation-guarded) |
| `GET /api/platform/evidence` | List evidence (scope-filtered) |
| `GET /mvp/integration-health`, `/mvp/evidence-explorer` | Platform UI pages |

Browser routes return server-rendered HTML; `/api/*` return JSON. Auth failures map to proper 401/403 responses (`app/main.py` exception handler).

---

## 13. UI architecture

- **Server-rendered Jinja2.** No SPA, no Node build. Templates are resolved through a `ChoiceLoader` over eight directories (six module `templates/` dirs + `modules/shared/templates` + `app/templates`).
- **Static assets** served at `/static/ecs` from `modules/shared/static` (CSS + vanilla JS such as `drilldown_engine.js`). Cache-busted via `?v=<mtime>` (`asset_ver`); HTML is sent `no-cache` so template edits appear on refresh.
- **Personas:** dashboards for CIO, Auditor, Compliance, Security, Vertical, Functional, Admin — selected via the login/role chooser and (when enabled) gated by RBAC page enforcement.
- **Universal drilldown:** `modules/shared/services/drilldown_engine.py` + `modules/shared/drilldowns/ecs_universal_drill_engine.py` power consistent KPI → row → detail drilldowns across modules.

---

## 14. Configuration architecture

All runtime config is YAML under `config/`, env-resolved by `ecs_platform/config/loader.py` (`${VAR:-default}`), cached via `lru_cache`. Config files: `auth`, `rbac`, `llm`, `vectorstore`, `repository`, `integrations`, `roi`, `sufficiency`, `connectivity`, `evidence_intel`, `evidence_analytics`. Secrets never live in YAML — they resolve from the environment at load time, so tenants/credentials are onboarded by setting env vars with no code change.
