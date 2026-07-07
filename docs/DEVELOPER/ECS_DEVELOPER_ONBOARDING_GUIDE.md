# ECS Developer Onboarding Guide

The **single authoritative onboarding guide** for a new developer joining the ECS
(Enterprise Evidence Collection System) project. It gives you the whole picture —
product, architecture, workflow, how to run/extend/debug ECS — in one place, and
**cross-references** the deep-dive guides rather than repeating them.

> **How this fits with the other developer docs (no duplication):**
> - [README_DEVELOPER.md](README_DEVELOPER.md) — the quick "start here" checklist (software, venv, Docker ports).
> - [../DEVELOPER_SETUP_GUIDE.md](../DEVELOPER_SETUP_GUIDE.md) — exhaustive per-OS setup (macOS/Linux/Windows-WSL2), native vs Docker.
> - **This guide** — the comprehensive narrative that ties overview → architecture → workflow → extend → troubleshoot together and points to the specialist guides.
> - [ECS_DEVELOPER_ONBOARDING_MANUAL.md](ECS_DEVELOPER_ONBOARDING_MANUAL.md) — a focused companion for the asset-driven scheduler subsystem.

**Grounding:** derived from the repository (`app/main.py`, `modules/`,
`ecs_platform/`, `config/`, `requirements.txt`, `docker-compose.yml`,
`Dockerfile`). No secrets, credentials, tenant IDs, IPs, or bank-specific values
appear anywhere in ECS docs.

---

## Table of contents

1. [Project overview & product vision](#1-project-overview--product-vision)
2. [High-level architecture](#2-high-level-architecture)
3. [Repository layout](#3-repository-layout)
4. [Technology stack](#4-technology-stack)
5. [Development, Git & branch workflow](#5-development-git--branch-workflow)
6. [Coding standards](#6-coding-standards)
7. [Module overview](#7-module-overview)
8. [Subsystem architectures](#8-subsystem-architectures) (connectors, scheduler, evidence, classification, diagnostics, REST API, DB, Docker)
9. [Environment setup](#9-environment-setup)
10. [Running ECS](#10-running-ecs)
11. [Extending ECS](#11-extending-ecs)
12. [Troubleshooting](#12-troubleshooting)
13. [The wider documentation set](#13-the-wider-documentation-set)

---

## 1. Project overview & product vision

**ECS is an enterprise Evidence Collection & Audit-Readiness platform — not a GRC
tool.** It automates the collection of compliance evidence from a technology
estate, maps that evidence to the frameworks regulators care about (RBI, PCI DSS,
ISO 27001, ITPP, …), validates it deterministically, raises observations for
gaps, and rolls everything up into an executive audit-readiness view.

**Vision:** turn a *manual, weeks-long, screenshot-driven* audit-evidence exercise
into a *repeatable, defensible, on-demand* one — with tamper-evident, hashed,
versioned evidence and a verifiable audit pack an auditor can trust.

The platform line, end to end:

```
Technology → Predefined Queries (Controls) → Frameworks → Evidence → Validation → Observations → Audit-Ready Packs → Executive Readiness
```

For the business framing and leadership walkthrough see
[LEADERSHIP_DEMO_SCRIPT.md](LEADERSHIP_DEMO_SCRIPT.md) and the executive
[Technology Dossier](../executive/ecs_technology_dossier.md).

---

## 2. High-level architecture

ECS is a **modular monolith**: one FastAPI application (`app/main.py`, entry
`app.main:app`) that composes domain packages under `modules/` on top of an
infrastructure package `ecs_platform/`.

```
                    ┌───────────────────────────────────────────────┐
   Browser  ──────► │  FastAPI app (app.main:app)                    │
   (Jinja2 +        │   middleware → route registrars → engines      │
    Bootstrap)      │   in-process state (ecs_state, demo seeds)     │
                    └───────────────┬───────────────────────────────┘
                                    │ (optional, docker-compose)
             ┌──────────────┬───────┴────────┬───────────────┬─────────────┐
        PostgreSQL x3     pgvector          MinIO           Redis        LLM/RAG
        (repository)   (embeddings)      (artifacts)      (cache)     (Ollama/…)
```

- **Web/UI:** FastAPI + server-rendered **Jinja2** (Bootstrap + vanilla JS).
- **Runtime:** `uvicorn app.main:app`, **Python 3.12** (`Dockerfile`).
- **State:** primarily **in-process Python state**
  (`modules/shared/services/ecs_state.py`) seeded with deterministic demo data;
  **optional** PostgreSQL / pgvector / MinIO / Redis backing services.
- **Config:** environment-driven via `ECS_ENV` +
  `config/environments/<env>.yaml` merged over `_base.yaml`.

Deep dives: [Enterprise Architecture Review](../architecture/ecs_enterprise_architecture_review.md),
[HLD](../hld/ecs_hld.md), [LLD](../lld/ecs_lld.md),
[Deployment Architecture](../architecture/ecs_deployment_architecture.md),
[ER diagrams](../diagrams/ecs_er_diagrams.md),
[Sequence diagrams](../diagrams/ecs_sequence_diagrams.md).

---

## 3. Repository layout

```
app/                     FastAPI entrypoint (app/main.py), routes, auth, templates
modules/                 Domain modules (module-oriented)
  audit_intelligence/    Asset discovery, tech mapping, evidence orchestration,
                         validation, observations, repository/packs, persistence,
                         asset-driven scheduler, /api/audit + /mvp/audit routes
  operations/            Predefined-query engine + DB connectors + integrations/
                         (11 enterprise connectors), scheduler module
  ai_sdlc/               AI-SDLC governance module
  enterprise_grc/        Enterprise GRC / CMDB
  executive_overview/    Executive dashboards & demo metrics
  frameworks/            Framework catalog
  governance/            Governance module
  shared/                Cross-cutting services, utils, routes, templates, static
ecs_platform/            Platform foundation (config loader, repository, RAG)
config/                  YAML config + environments/<env>.yaml + uat_assets.*.yaml
scripts/                 Operational + diagnostic + smoke scripts
tests/                   Pytest suite
docs/                    Documentation (DEVELOPER/, operations/, architecture/, …)
Dockerfile               App image (python:3.12-slim)
docker-compose.yml       Local services (app, DBs, demo connectors, MinIO, Redis)
requirements.txt         Runtime dependencies
.env.example             Environment template (copy to .env)
```

See [README_DEVELOPER.md §2](README_DEVELOPER.md) for the condensed version and
the [Data Architecture Reference](../architecture/ECS_DATA_ARCHITECTURE_REFERENCE.md)
for persistence layout.

---

## 4. Technology stack

| Layer | Choice |
|-------|--------|
| Language / runtime | Python 3.12 (3.11+ supported) |
| Web framework | FastAPI + `uvicorn` |
| UI | Jinja2 (server-rendered) + Bootstrap + vanilla JS |
| Config | YAML (`config/`) via `ecs_platform.config.loader`, `${VAR:-default}` substitution |
| DB drivers | `psycopg2-binary` (PostgreSQL/YugabyteDB), `PyMySQL` (Aurora/MySQL), `oracledb` (Oracle, thin), `pymongo` (MongoDB); `pyodbc` optional for SQL Server |
| Optional infra | PostgreSQL ×3, pgvector, MinIO, Redis, Ollama/LLM (via `docker-compose.yml`) |
| Auth | `pyjwt[crypto]`; `app/auth/`, `config/auth.yaml`, `config/rbac.yaml` |
| Docs/exports | `openpyxl` (Excel), Markdown |
| Testing | `pytest` (+ `httpx` for FastAPI `TestClient`) — in `requirements-dev.txt` |

Full dependency notes: `requirements.txt` (each optional driver documents its
graceful-degradation behaviour) and [DEVELOPER_SETUP_GUIDE.md](../DEVELOPER_SETUP_GUIDE.md).

---

## 5. Development, Git & branch workflow

**Active branch:** `cursor/predefined-queries-module`.

**Branch strategy**
- Feature/work branches are named `cursor/<topic>` and branch from the active line.
- Environment promotion is **config-only**: the *same image* moves
  `Local → DEV → SIT → UAT → PROD`; behaviour changes via env vars + `config/*.yaml`
  (see [Deployment Reference](../DEPLOYMENT/ECS_DEPLOYMENT_REFERENCE.md)).

**Development workflow (typical loop)**
1. Create/checkout a `cursor/<topic>` branch.
2. Make the change, preferring to **extend existing modules** over adding new ones.
3. Add/extend **mocked** tests (no live systems in tests).
4. `python -m compileall <changed paths>` and run **scoped** `pytest` (not the full suite unless needed).
5. Commit with a clear, conventional message (`feat:`, `fix:`, `test:`, `docs:`, `perf:`, `chore:`) — **only when asked**.
6. Push to the remote branch (only when asked).

**Git conventions**
- Small, logical commits; one concern per commit.
- Never commit secrets, `.env*`, `.DS_Store`, backups, or bank-specific values.
- Never commit real IPs/hostnames/tenant IDs.

---

## 6. Coding standards

Follow the patterns already established across `modules/`:

- **Module-oriented layout:** `modules/<domain>/engines/`, `.../services/`,
  `.../routes/`. Engines hold logic; services are thin serialization-friendly
  facades; routes are thin HTTP wrappers.
- **`from __future__ import annotations`** at the top of new modules; type-hint
  public functions.
- **Frozen dataclasses** with `to_dict()` for serializable models (see
  `modules/audit_intelligence/models.py`).
- **Determinism & offline-safety:** engine logic must be deterministic and must
  not open sockets in tests; inject transports/executors for anything external.
- **Fail safe:** never raise to a client/CLI for a missing key or bad input —
  return `None`/`[]`/an error envelope. Catch-and-classify (see the connector
  `_base` and the `/api/audit` `_safe` wrapper).
- **No secrets in logs or responses:** config is surfaced masked (`SET`/`MISSING`).
- **Comments** explain *why*, not *what*; avoid narrating obvious code.
- **API response shape:** success `{"ok": true, ...}`; error
  `{"ok": false, "status": "error", "message": ..., "errors": [...]}` (see
  [PERFORMANCE_AND_HARDENING_GUIDE.md](PERFORMANCE_AND_HARDENING_GUIDE.md)).

---

## 7. Module overview

| Module | Responsibility | Key guide |
|--------|----------------|-----------|
| `audit_intelligence` | Asset discovery, technology→control→framework mapping, evidence orchestration, validation, observations, repository/packs, persistence, asset-driven scheduler, `/api/audit` + `/mvp/audit` | [TECHNOLOGY_MAPPING_GUIDE](TECHNOLOGY_MAPPING_GUIDE.md), [ASSET_DISCOVERY_GUIDE](ASSET_DISCOVERY_GUIDE.md), [EVIDENCE_COLLECTION_GUIDE](EVIDENCE_COLLECTION_GUIDE.md), [EVIDENCE_VALIDATION_GUIDE](EVIDENCE_VALIDATION_GUIDE.md), [OBSERVATION_AND_REPOSITORY_GUIDE](OBSERVATION_AND_REPOSITORY_GUIDE.md), [AUDIT_INTELLIGENCE_PERSISTENCE_GUIDE](AUDIT_INTELLIGENCE_PERSISTENCE_GUIDE.md) |
| `operations` | Predefined-query engine + DB connectors; 11 enterprise integration adapters; scheduler module | [PREDEFINED_DATABASE_QUERY_MODULE](PREDEFINED_DATABASE_QUERY_MODULE.md), [INTEGRATION_ADAPTERS_GUIDE](INTEGRATION_ADAPTERS_GUIDE.md), [../operations/ECS_SCHEDULER_REFERENCE.md](../operations/ECS_SCHEDULER_REFERENCE.md) |
| `ai_sdlc` | AI-SDLC governance | [../AI/README.md](../AI/README.md) |
| `enterprise_grc` | Enterprise GRC / CMDB inventory | [Architecture Review](../architecture/ecs_enterprise_architecture_review.md) |
| `executive_overview` | Executive dashboards, demo metrics | [Product Manual](../PRODUCT/ECS_MASTER_PRODUCT_MANUAL.md) |
| `frameworks` | Framework catalog | [../FRAMEWORKS/README.md](../FRAMEWORKS/README.md) |
| `governance` | Governance workflows | [../WORKFLOWS/README.md](../WORKFLOWS/README.md) |
| `shared` | Cross-cutting state, utils (pagination, cache), routes, templates | [PERFORMANCE_AND_HARDENING_GUIDE](PERFORMANCE_AND_HARDENING_GUIDE.md) |

---

## 8. Subsystem architectures

### Connector architecture
Two collector families feed evidence:
1. **Baseline collectors** — the **predefined-query engine**
   (`modules/operations/engines/predefined_queries_engine.py`) runs curated,
   **read-only** checks against DB/OS/middleware targets.
2. **Enterprise connectors** — 11 config-driven adapter skeletons under
   `modules/operations/integrations/` (ServiceNow, Archer, SharePoint/Teams/
   Outlook via Microsoft Graph, Jira, Confluence, SonarQube, Checkmarx, Prisma
   Cloud, Tripwire). One shared interface (`get_config`/`is_configured`/
   `masked_config`/`health_check`/`fetch_*`/`normalize_*`), one response shape
   (`{ok, source, status, items, errors}`), injectable transport (no live calls
   in tests), secrets never logged.
   Guides: [INTEGRATION_ADAPTERS_GUIDE](INTEGRATION_ADAPTERS_GUIDE.md),
   [MS_GRAPH_CONNECTOR_GUIDE](MS_GRAPH_CONNECTOR_GUIDE.md),
   [CONNECTOR_DEEPENING_GUIDE](CONNECTOR_DEEPENING_GUIDE.md),
   [ENTERPRISE_CONNECTOR_UAT_SETUP](ENTERPRISE_CONNECTOR_UAT_SETUP.md).

### Scheduler architecture
- **Operational scheduler reference:** [../operations/ECS_SCHEDULER_REFERENCE.md](../operations/ECS_SCHEDULER_REFERENCE.md).
- **Asset-driven scheduler** (reads a UAT/local asset inventory, classifies each
  asset, routes it to a baseline collector or enterprise connector, and produces a
  bounded, deterministic dry-run plan):
  [UAT_ASSET_DRIVEN_SCHEDULER_DESIGN](UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md) and its
  onboarding companion [ECS_DEVELOPER_ONBOARDING_MANUAL](ECS_DEVELOPER_ONBOARDING_MANUAL.md).

### Evidence collection architecture
Orchestrator → records → validation → observations → repository (versioned,
hashed) → packs (verifiable manifest). See
[EVIDENCE_COLLECTION_GUIDE](EVIDENCE_COLLECTION_GUIDE.md),
[EVIDENCE_VALIDATION_GUIDE](EVIDENCE_VALIDATION_GUIDE.md),
[OBSERVATION_AND_REPOSITORY_GUIDE](OBSERVATION_AND_REPOSITORY_GUIDE.md).

### Technology classification
Deterministic fingerprinting from image/name/ports/CMDB-class →
`TechnologyFingerprint` → controls/frameworks. See
[ASSET_DISCOVERY_GUIDE](ASSET_DISCOVERY_GUIDE.md) and
[TECHNOLOGY_MAPPING_GUIDE](TECHNOLOGY_MAPPING_GUIDE.md).

### Diagnostics
Environment + connector diagnostics validate config presence, reachability, and
adapter health **without** running live queries by default. See
[../operations/CONNECTOR_TROUBLESHOOTING_RUNBOOK.md](../operations/CONNECTOR_TROUBLESHOOTING_RUNBOOK.md)
and the connector-health CLI in [§10](#10-running-ecs).

### REST API structure
- Audit Intelligence API: `/api/audit/*` (dashboard, assets, mapping, runs,
  repository, observations, packs, integrations, health) — consistent envelope,
  pagination, safe error handling
  ([PERFORMANCE_AND_HARDENING_GUIDE](PERFORMANCE_AND_HARDENING_GUIDE.md)).
- UI pages: `/mvp/audit/*` (executive-readiness, assets, technology-mapping,
  evidence-runs, validation-results, observations, repository, evidence-packs).
- Health: `/healthz` (liveness), `/readyz` (repo connectivity),
  `/api/platform/health` (connectors).
- UI-to-API flows: [LLD §8](../lld/ecs_lld.md).

### Database overview
In-process state by default; optional PostgreSQL ×3 (repository), pgvector
(embeddings), MinIO (artifacts), Redis (cache). The audit-intelligence durable
persistence foundation ships an interface + in-memory + SQL (SQLite default,
Postgres-ready) backend with an idempotent schema
(`docs/DB_SCHEMA_AUDIT_INTELLIGENCE.sql`). See
[AUDIT_INTELLIGENCE_PERSISTENCE_GUIDE](AUDIT_INTELLIGENCE_PERSISTENCE_GUIDE.md)
and [Data Architecture Reference](../architecture/ECS_DATA_ARCHITECTURE_REFERENCE.md).

### Docker overview
`docker-compose.yml` defines the app plus optional DBs, demo connectors, MinIO,
and Redis behind **profiles** (`db-targets`, `nginx-demo`, `infra-demo-extended`,
`sources`, `demo-connectors`, …). See [README_DEVELOPER.md §8](README_DEVELOPER.md)
and the [Deployment Reference](../DEPLOYMENT/ECS_DEPLOYMENT_REFERENCE.md).

---

## 9. Environment setup

> Full, per-OS instructions live in
> [../DEVELOPER_SETUP_GUIDE.md](../DEVELOPER_SETUP_GUIDE.md) and
> [README_DEVELOPER.md](README_DEVELOPER.md). This is the condensed path.

**Required software:** Git, Python 3.12 (3.11+ ok), Docker Desktop + Docker
Compose (only for the full stack). Node.js is **not** required (UI is Jinja2).

**Python + virtualenv + packages**
```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows Git Bash: source .venv/Scripts/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt   # pytest, httpx
cp .env.example .env                 # edit: local Docker or UAT endpoints + READ-ONLY creds
```

**Optional backing services (Docker Compose)** — PostgreSQL, pgvector, MinIO,
Redis, demo connectors are declared in `docker-compose.yml` behind profiles. Start
only what you need:
```bash
docker compose up -d postgres-demo                       # lightweight DB target
docker compose --profile db-targets up -d postgres-demo yugabyte mysql-demo
docker compose --profile sources up -d                   # gitea/jenkins/sonarqube demo connectors
```
Local ports: PostgreSQL **5432**, YugabyteDB **5433**, MySQL **3306**, NGINX
**8081→80**, Apache **8082→80**, Tomcat **8083→8080**, MongoDB **27017**, Oracle
**1521**, SQL Server **1433** (see README_DEVELOPER for the full table).

**Environment variables & YAML config**
- `ECS_ENV` selects the environment (`local`/`dev`/`sit`/`uat`/`prod`); default `local`.
- `config/environments/<env>.yaml` is deep-merged over `_base.yaml`.
- Secrets come from env vars only (`ECS_*`), never from YAML/code — YAML references
  them by `*_env` name or `${VAR:-default}`. See
  [../ENVIRONMENT_CONFIGURATION.md](../ENVIRONMENT_CONFIGURATION.md).

**Start ECS locally**
```bash
# Native (fastest — demo mode, in-memory, no DB/Docker):
export DEMO_MODE=true ECS_AUTH_ENABLED=false ECS_VALIDATE_CONFIG=off
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000
# or the helper:
./start_ecs.sh
```

**Verify startup**
```bash
curl -s http://127.0.0.1:8000/healthz        # liveness
curl -s http://127.0.0.1:8000/readyz         # repo connectivity
# UI:
open http://127.0.0.1:8000/mvp/audit/dashboard
# Full offline platform check (no network/DB): expect 10/10 ALL PASS
PYTHONPATH=. python scripts/run_ecs_demo_smoke.py
```

---

## 10. Running ECS

| Task | Command |
|------|---------|
| Run FastAPI (native/demo) | `PYTHONPATH=. uvicorn app.main:app --port 8000` |
| Run via Docker Compose | `./start_ecs.sh` or `docker compose up` |
| Offline end-to-end smoke | `PYTHONPATH=. python scripts/run_ecs_demo_smoke.py` |
| Production smoke | `PYTHONPATH=. python scripts/run_production_smoke.py` |
| Connector health (config-only) | `PYTHONPATH=. python scripts/run_uat_connector_health.py --adapter all` |
| Connector health (live, if configured) | `PYTHONPATH=. python scripts/run_uat_connector_health.py --adapter all --live` |
| Scheduler dry-run (asset-driven) | `PYTHONPATH=. python scripts/run_uat_asset_scheduler.py --config config/uat_assets.local.yaml --dry-run` |
| Run a predefined query | `PYTHONPATH=. python scripts/run_predefined_query.py` (see [PREDEFINED_DATABASE_QUERY_MODULE](PREDEFINED_DATABASE_QUERY_MODULE.md)) |
| Mocked connectors (tests) | `PYTHONPATH=. pytest tests/test_integration_adapters_mocked.py -q` |
| Compile check | `python -m compileall modules scripts tests` |
| Scoped tests | `PYTHONPATH=. pytest tests/test_<area>.py -q` |

**Debugging failures**
- Reproduce with a **scoped** test file first (fast; avoids the ~20s full-app import).
- App won't import? Run `python -m compileall <path>` to find syntax/import errors.
- Use `--json` on the smoke/health/scheduler CLIs for machine-readable detail.

**Inspecting logs**
- Native run: logs stream to the console.
- Docker: `docker compose logs -f ecs` (and `logs <service>` for a DB/connector).
- Health/readiness endpoints (`/healthz`, `/readyz`, `/api/platform/health`) are
  the first stop for "is it up and wired?".

**Testing policy:** run **scoped** `pytest` for the area you changed. Do **not**
run the full 2000+ suite unless necessary (it is slow). See
[E2E_SMOKE_TEST_GUIDE](E2E_SMOKE_TEST_GUIDE.md).

---

## 11. Extending ECS

Prefer **extending existing modules** over adding new ones.

**Add a connector** — implement the adapter under
`modules/operations/integrations/<name>.py` following the shared interface + the
`_base` helpers (config from env, injectable transport, masked config, classified
errors), register it in `integrations/__init__.py::ADAPTER_MODULES`, and add
mocked tests. Route it from the asset scheduler by adding one line to
`_CONNECTOR_ROUTES`. Guide: [INTEGRATION_ADAPTERS_GUIDE](INTEGRATION_ADAPTERS_GUIDE.md),
[CONNECTOR_DEEPENING_GUIDE](CONNECTOR_DEEPENING_GUIDE.md).

**Add a technology rule** — add a `(regex, canonical_tech)` to `_TEXT_RULES` (or a
port to `_PORT_RULES`) in
`modules/audit_intelligence/engines/technology_fingerprint.py`; keep names aligned
with the predefined-query catalog. Guide: [TECHNOLOGY_MAPPING_GUIDE](TECHNOLOGY_MAPPING_GUIDE.md).

**Add a scheduler job** — for asset-driven planning, add assets to a
`config/uat_assets.*.yaml`; for operational scheduling see
[../operations/ECS_SCHEDULER_REFERENCE.md](../operations/ECS_SCHEDULER_REFERENCE.md)
and [UAT_ASSET_DRIVEN_SCHEDULER_DESIGN](UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md).

**Add evidence mappings** — evidence maps flow from the predefined-query catalog
(control → technology → frameworks); extend the catalog/engine rather than the
mapping projection. Guide: [EVIDENCE_COLLECTION_GUIDE](EVIDENCE_COLLECTION_GUIDE.md),
[../operations/ECS_CONTROL_AND_EVIDENCE_REUSE_GUIDE.md](../operations/ECS_CONTROL_AND_EVIDENCE_REUSE_GUIDE.md).

**Add APIs** — add a thin route in the relevant `modules/<domain>/routes/`
registrar; return the standard envelope; paginate list responses; wrap with the
safe-error decorator. Register it in `app/main.py` if it's a new registrar.

**Add tests** — mirror the closest existing test file; keep tests **offline**
(inject transports/executors); prefer scoped, deterministic tests.

---

## 12. Troubleshooting

> Cross-refs: [../TROUBLESHOOTING_GUIDE.md](../TROUBLESHOOTING_GUIDE.md),
> [../operations/CONNECTOR_TROUBLESHOOTING_RUNBOOK.md](../operations/CONNECTOR_TROUBLESHOOTING_RUNBOOK.md),
> [../ECS_DEMO_MODE_SETUP_AND_TROUBLESHOOTING.md](../ECS_DEMO_MODE_SETUP_AND_TROUBLESHOOTING.md).

| Symptom | Likely cause & fix |
|---------|--------------------|
| **Docker** container won't start / OOM | Not enough RAM for heavy profiles (Oracle/SQL Server/Yugabyte). Start only lightweight profiles, or point `ECS_*_HOST` at a shared endpoint (README_DEVELOPER §4). |
| **PostgreSQL** connection refused | Container not up (`docker compose ps`), wrong port/host in `.env`, or credentials not read-only. Check `docker compose logs postgres-demo`. |
| **Python env** import errors | Wrong interpreter/venv, missing `requirements-dev.txt`, or `PYTHONPATH` not set. Activate `.venv`; run with `PYTHONPATH=.`; `python -m compileall` to locate the failure. |
| **Connector config** not detected | Env vars not exported / unresolved `${VAR}`. Verify with `run_uat_connector_health.py --adapter <name>` (shows `SET`/`MISSING`, never values). |
| **Microsoft Graph auth** fails | Missing `ECS_GRAPH_TENANT_ID`/`CLIENT_ID`/`CLIENT_SECRET` or insufficient app permissions/consent. See [MS_GRAPH_CONNECTOR_GUIDE](MS_GRAPH_CONNECTOR_GUIDE.md) + [ENTERPRISE_CONNECTOR_UAT_SETUP](ENTERPRISE_CONNECTOR_UAT_SETUP.md). Status `auth_error` ⇒ credential/scope. |
| **Scheduler** dry-run empty or all-unsupported | Config path wrong / malformed YAML (loader returns `{}` safely), or assets lack technology/asset_type. Run with `--json` to inspect classifications and `reasons`. |
| **YAML** mistakes | Indentation/tabs, or inline secrets (forbidden). Validate: `python -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" <file>`. |
| **Environment variable** issues | Wrong `ECS_ENV`, unresolved `${VAR}` (treated as unset), or `.env` not loaded. Confirm with `ECS_VALIDATE_CONFIG=on` for a fail-fast check. |

---

## 13. The wider documentation set

ECS already ships an extensive, indexed documentation package — **use it; do not
duplicate it.** Start at [../README.md](../README.md) (the docs index). Quick map
of the enterprise document set:

| Area | Source of truth |
|------|-----------------|
| Enterprise Architecture | [architecture/ecs_enterprise_architecture_review.md](../architecture/ecs_enterprise_architecture_review.md), [hld/ecs_hld.md](../hld/ecs_hld.md), [lld/ecs_lld.md](../lld/ecs_lld.md) |
| Developer onboarding | **this guide** + [README_DEVELOPER.md](README_DEVELOPER.md) + [../DEVELOPER_SETUP_GUIDE.md](../DEVELOPER_SETUP_GUIDE.md) |
| Installation / Environment setup | [../DEVELOPER_SETUP_GUIDE.md](../DEVELOPER_SETUP_GUIDE.md), [../ENVIRONMENT_CONFIGURATION.md](../ENVIRONMENT_CONFIGURATION.md) |
| Deployment | [../DEPLOYMENT/ECS_DEPLOYMENT_REFERENCE.md](../DEPLOYMENT/ECS_DEPLOYMENT_REFERENCE.md), [../architecture/ecs_deployment_architecture.md](../architecture/ecs_deployment_architecture.md), [../operations/DEPLOYMENT_RUNBOOK.md](../operations/DEPLOYMENT_RUNBOOK.md) |
| Administrator / Operations | [../TRAINING/ECS_ADMIN_GUIDE.md](../TRAINING/ECS_ADMIN_GUIDE.md), [../operations/ecs_runbook.md](../operations/ecs_runbook.md), [../operations/ECS_OPERATIONS_RUNBOOK.md](../operations/ECS_OPERATIONS_RUNBOOK.md) |
| UAT | [UAT_INTEGRATION_GUIDE.md](UAT_INTEGRATION_GUIDE.md), [../operations/UAT_VALIDATION_RUNBOOK.md](../operations/UAT_VALIDATION_RUNBOOK.md), [ENTERPRISE_CONNECTOR_UAT_SETUP.md](ENTERPRISE_CONNECTOR_UAT_SETUP.md) |
| Production / DR / Monitoring | [../operations/ECS_PRODUCTION_CHECKLIST.md](../operations/ECS_PRODUCTION_CHECKLIST.md), [../operations/ECS_DISASTER_RECOVERY_PLAN.md](../operations/ECS_DISASTER_RECOVERY_PLAN.md), [../operations/ECS_PRODUCTION_MONITORING_GUIDE.md](../operations/ECS_PRODUCTION_MONITORING_GUIDE.md) |
| Security | [../SECURITY/ECS_SECURITY_REFERENCE.md](../SECURITY/ECS_SECURITY_REFERENCE.md) |
| Scheduler | [../operations/ECS_SCHEDULER_REFERENCE.md](../operations/ECS_SCHEDULER_REFERENCE.md), [UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md](UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md) |
| Connectors / Integration | [INTEGRATION_ADAPTERS_GUIDE.md](INTEGRATION_ADAPTERS_GUIDE.md), [../INTEGRATIONS/README.md](../INTEGRATIONS/README.md) |
| Evidence / Controls / Frameworks | [EVIDENCE_COLLECTION_GUIDE.md](EVIDENCE_COLLECTION_GUIDE.md), [../FRAMEWORKS/README.md](../FRAMEWORKS/README.md) |
| Technology rules | [TECHNOLOGY_MAPPING_GUIDE.md](TECHNOLOGY_MAPPING_GUIDE.md), [ASSET_DISCOVERY_GUIDE.md](ASSET_DISCOVERY_GUIDE.md) |
| API / Database | [../lld/ecs_lld.md](../lld/ecs_lld.md) (UI-to-API flows), [../architecture/ECS_DATA_ARCHITECTURE_REFERENCE.md](../architecture/ECS_DATA_ARCHITECTURE_REFERENCE.md), [../DB_SCHEMA_AUDIT_INTELLIGENCE.sql](../DB_SCHEMA_AUDIT_INTELLIGENCE.sql) |
| Troubleshooting / Support | [../TROUBLESHOOTING_GUIDE.md](../TROUBLESHOOTING_GUIDE.md), [../operations/ECS_SUPPORT_RUNBOOK.md](../operations/ECS_SUPPORT_RUNBOOK.md) |
| Production readiness gaps | [PRODUCTION_READINESS_GAP_REGISTER.md](PRODUCTION_READINESS_GAP_REGISTER.md) |

---

*Welcome to ECS. Start with [§9 Environment setup](#9-environment-setup), get the
demo smoke to 10/10, open `/mvp/audit/dashboard`, then read the deep-dive guide
for whatever you're about to touch.*
