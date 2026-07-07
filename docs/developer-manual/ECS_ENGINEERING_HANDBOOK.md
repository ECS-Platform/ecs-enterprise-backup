# ECS Engineering Handbook

> **The single authoritative source** for getting productive on ECS: setup, onboarding,
> environment configuration, architecture, demo mode, troubleshooting, commands, branching,
> release, and developer workflow.
>
> This handbook **consolidates** existing documentation. Where a deep, accurate guide already
> exists it is **linked, not duplicated** (it is named *authoritative child* below). Where prior
> docs conflicted, this handbook states the **code-verified** answer and notes the superseded doc.
> See [`DOCUMENTATION_GAP_ANALYSIS.md`](../archive/DOCUMENTATION_GAP_ANALYSIS.md) for the audit behind it.

**Last verified against code:** 2026-06-16 · **Default branch:** `main` · **Active dev branch
pattern:** `cursor/*`

---

## Contents

1. [What ECS is (90-second orientation)](#1-what-ecs-is)
2. [Day-1 onboarding path](#2-day-1-onboarding-path)
3. [Setup](#3-setup)
4. [Environment configuration](#4-environment-configuration)
5. [Demo mode](#5-demo-mode)
6. [Architecture](#6-architecture)
7. [Developer workflow](#7-developer-workflow)
8. [Command catalog](#8-command-catalog)
9. [Testing & validation](#9-testing--validation)
10. [Branching strategy](#10-branching-strategy)
11. [Release process](#11-release-process)
12. [Troubleshooting](#12-troubleshooting)
13. [Backup, restore & recovery](#13-backup-restore--recovery)
14. [Module ownership](#14-module-ownership)
15. [Authoritative document map](#15-authoritative-document-map)

---

## 1. What ECS is

ECS (Evidence & Compliance System) is a **banking Governance, Risk, Compliance, Audit &
Evidence-Management platform**, built as a **modular monolith**: one FastAPI app
(`app/main.py`, ASGI object `app.main:app`) that composes six business-domain packages under
`modules/` plus a shared core and an infrastructure layer.

| Layer | Detail |
|---|---|
| **Backend** | FastAPI + Uvicorn, **Python 3.12** (`Dockerfile`: `python:3.12-slim`). |
| **Frontend** | Server-rendered **Jinja2** + Bootstrap 5.3 (CDN) + vanilla JS. **No Node/npm build** — `package-lock.json` declares no packages; do not run `npm install`. |
| **Data** | Deterministic **in-memory** demo state by default; optional PostgreSQL + pgvector + MinIO + Redis via Docker Compose. |
| **Config** | YAML under `config/` with `${ENV}` resolution; flags loaded from `.env` at startup. |
| **Modules** | `executive_overview`, `frameworks`, `operations`, `governance`, `enterprise_grc`, `ai_sdlc`, plus `modules/shared/` and `ecs_platform/`. |

**Verified platform facts** (computed from source, 2026-06-16):
**9** Python dependencies · **15** static frameworks (runtime-extensible) · **305** controls ·
**702** evidence items · **12** enterprise connectors · **9** RBAC roles · **10** Docker services ·
**39** test files.

**Key consequence:** ECS boots fully with **no database and no LLM** — both are optional,
best-effort dependencies.

---

## 2. Day-1 onboarding path

Follow this order; each step links to the authoritative detail.

1. **Read** §1 above and skim [`docs/README.md`](README.md) (architecture package index).
2. **Set up** your machine → §3 / [`DEVELOPER_SETUP_GUIDE.md`](DEVELOPER_SETUP_GUIDE.md).
3. **Run in demo mode** → §5. Confirm `curl http://127.0.0.1:8000/healthz` → `{"status":"ok"}`.
4. **Log in as each primary role** (`cio`, `owner`, `auditor`, `vertical_head`) and walk the dashboards.
5. **Learn the inner loop** → §7 / [`LOCAL_DEVELOPMENT_GUIDE.md`](LOCAL_DEVELOPMENT_GUIDE.md).
6. **Trace one drilldown:** UI click → `/api/ecs/universal-drill` → drill engine
   (`modules/shared/drilldowns/ecs_universal_drill_engine.py`).
7. **Run the tests & template validator** → §9.
8. **Find your module owner** → §14 / [`ECS_MODULE_OWNERSHIP.md`](ECS_MODULE_OWNERSHIP.md).

**First-week checklist**

- [ ] `python --version` → 3.12 inside the activated venv.
- [ ] `pip install -r requirements.txt` completed cleanly (9 packages).
- [ ] `.env` exists; demo flags set (§5).
- [ ] `uvicorn app.main:app --reload` logs the `[ECSStartup]` banner.
- [ ] `/healthz` returns ok; browser loads `/`.
- [ ] `pytest` runs the suite in `tests/`.
- [ ] You can name your module's owner, key engines, and test files.

---

## 3. Setup

**Authoritative child:** [`docs/developer-manual/DEVELOPER_SETUP_GUIDE.md`](DEVELOPER_SETUP_GUIDE.md) — full
per-OS instructions for macOS, Linux, and Windows (WSL2), plus the Docker stack.

**Fastest start (demo mode, no Docker, no DB)** — requires Python 3.12 + git:

```bash
git clone <your-ecs-remote-url> ECS && cd ECS
python3.12 -m venv venv && source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt      # 9 packages — the canonical set
pip install pytest                    # optional: not in requirements.txt
cp .env.example .env                  # then set demo flags (see §5)
uvicorn app.main:app --reload
# http://127.0.0.1:8000/   ·   health: http://127.0.0.1:8000/healthz
```

> **Do not rely on `start_ecs.sh` for setup.** It installs only a *subset* of dependencies
> (`fastapi uvicorn jinja2 python-multipart`) and kills running uvicorn processes. Always use
> `pip install -r requirements.txt` so `openpyxl`, `psycopg2-binary`, `python-dotenv`, `pyyaml`,
> and `pyjwt[crypto]` are present.

**Full stack (Docker Compose — real connectors, DB, RAG)** — requires Docker:

```bash
docker compose up                                  # core: app + 2x postgres + pgvector + redis + minio
docker compose --profile sources up -d             # add Gitea + Jenkins
docker compose --profile demo-connectors up -d     # add SonarQube
./demo-data/recreate_demo.sh                        # down -v -> up -> seed 6 apps -> sync -> verify
```

Service ports (`docker-compose.yml`): app `8000`, postgres-demo `5432`, repository postgres
`5433`, pgvector `5434`, redis `6379`, MinIO `9002` (console `9001`), Gitea `3000`, Jenkins
`8080`, SonarQube `9000`.

---

## 4. Environment configuration

**Source of truth:** the repo-root **`.env.example`** (≈10 KB, fully commented). Copy it:
`cp .env.example .env`. `.env` is **git-ignored** — never commit secrets.

**How env loading works (code-verified — corrects older docs):** the very first import in
`app/main.py` is `from app import env_bootstrap`. `app/env_bootstrap.py::load_env()` loads the
repo-root `.env` into `os.environ` **using `python-dotenv`** (with a built-in parser fallback) and
`override=False`, so real environment / container values still win. This runs **before** auth and
RBAC initialize, guaranteeing `DEMO_MODE` and `ECS_AUTH_ENABLED` exist at startup.

> ⚠️ **Supersedes** `ECS_DEMO_MODE_SETUP_AND_TROUBLESHOOTING.md`, which states ".env is not loaded
> automatically / no `load_dotenv()`." That is **incorrect for the current build** — `.env` *is*
> loaded. You no longer need to `export` flags in the same shell (though that still works because
> `override=False`).

**Defaults are secure-by-default.** In `.env.example`: `ECS_AUTH_ENABLED=true`,
`ECS_AUTH_PROVIDER=azure_ad`, `DEMO_MODE=false`. You must opt into demo mode (§5).

**Most-used flags**

| Variable | Default | Purpose |
|---|---|---|
| `DEMO_MODE` | `false` | Master demo switch — bypasses **all** enforcement when `true`. |
| `ECS_AUTH_ENABLED` | `true` | Authentication middleware (Azure AD / OIDC / JWT). |
| `ECS_AUTH_PROVIDER` | `azure_ad` | `azure_ad` \| `oidc` \| `dev`. |
| `RBAC_ENFORCEMENT_ENABLED` | per `.env.example` | RBAC enforcement. |
| `RBAC_PAGE_ENFORCEMENT_ENABLED` | per `.env.example` | Page/dashboard guards. |
| `ECS_REPO_PG_*` | see `config/repository.yaml` | Evidence repository Postgres (optional). |
| `ECS_VECTOR_PG_*` | see `config/vectorstore.yaml` | Vector store (optional). |
| `BACKUP_DIR` / `BACKUP_RETENTION_DAYS` | `./backups` / `14` | Backup location / retention (§13). |

For the complete annotated list, read `.env.example` directly (Azure AD, OIDC, JWT tuning, LLM/RAG,
integrations, durability flags, etc.).

---

## 5. Demo mode

Demo mode runs ECS with deterministic in-memory data and **no auth, no DB, no LLM**.

**Enable it** by setting in `.env`:

```bash
DEMO_MODE=true
ECS_AUTH_ENABLED=false
# Optional, to fully relax guards in older flows:
RBAC_ENFORCEMENT_ENABLED=false
RBAC_PAGE_ENFORCEMENT_ENABLED=false
```

Then `uvicorn app.main:app --reload`. Because `.env` is loaded at startup (§4), **a separate
`export` step is not required**.

**Expected startup banner** (abridged — from `ecs_lifespan`):

```
[ECSStartup] ECS Startup
[ECSStartup] DEMO_MODE=true
[ECSStartup] ECS_AUTH_ENABLED=false
[ECSStartup] .env loaded=True via python-dotenv
[ECSPlatform] Evidence repository unavailable: ...     # normal without Postgres
[ECSPlatform] LLM-RAG disabled: provider not configured # normal without an LLM
... platform ready on 127.0.0.1:8000
```

The "repository unavailable" and "LLM-RAG disabled" lines are **expected** in demo mode — the app
serves fully without a database or LLM. Demo workflow state is seeded automatically on startup by
`seed_demo_workflow_state()`; no manual seed step is needed for the showcase UI. (Connector-driven
evidence seeding is a Docker-stack activity — see §3 / §8.)

**Verify:**

```bash
curl -s http://127.0.0.1:8000/healthz       # {"status":"ok"}
curl -I http://127.0.0.1:8000/dashboard     # HTTP/1.1 200 OK (not 401)
```

---

## 6. Architecture

The deep architecture package lives under `docs/` and is indexed by
[`docs/README.md`](README.md). Read it in this order by role:

| Audience | Path |
|---|---|
| Engineers | [LLD](../architecture/ecs_lld.md) → [ER diagrams](../diagrams/ecs_er_diagrams.md) → [Sequences](../diagrams/ecs_sequence_diagrams.md) |
| Architects | [EA review](../architecture/ecs_enterprise_architecture_review.md) → [HLD](../architecture/ecs_hld.md) → [Deployment](../architecture/ecs_deployment_architecture.md) |
| Ops / SRE | [Operations runbook](../operations/ecs_runbook.md) → [Deployment](../architecture/ecs_deployment_architecture.md) |
| Executives | [Technology dossier](../archive/ecs_technology_dossier.md) → [EA review](../architecture/ecs_enterprise_architecture_review.md) |

**Startup flow (what happens on boot)** — entry `app/main.py`:

1. `.env` loaded first (`app/env_bootstrap.py`), before auth/RBAC init.
2. FastAPI app constructed with `lifespan=ecs_lifespan`.
3. Middleware: `_no_cache_html` (HTML `Cache-Control: no-cache`) + `register_authentication`
   (pass-through when auth disabled).
4. Static mount `/static/ecs` → `modules/shared/static`; Jinja `ChoiceLoader` over 8 template dirs.
5. Routes registered: `register_mvp_routes`, `register_evidence_routes`, `register_platform_routes`,
   `register_governance_routes`, `register_ai_sdlc_routes`, `register_grc_demo_routes`.
6. Lifespan: logging + banner → `refresh_repository_from_frameworks` → `seed_demo_workflow_state`
   → `self_heal_governance` → `validate_startup` → best-effort `init_repository` /
   `init_governance_schema` (never blocks) → LLM-RAG status + background `warm_models` →
   `log_platform_ready`.

**Source-of-truth anchors**

| Concern | File(s) |
|---|---|
| Entry & routing | `app/main.py` |
| Env loading | `app/env_bootstrap.py` |
| Cross-cutting state / workflow | `modules/shared/services/ecs_state.py`, `evidence_workflow_engine.py` |
| Universal drilldown | `modules/shared/drilldowns/ecs_universal_drill_engine.py` |
| Framework catalog | `modules/frameworks/engines/framework_catalog.py` |
| AI-SDLC | `modules/ai_sdlc/engines/ai_sdlc_workflow_engine.py` |
| Auth & RBAC | `app/auth/`, `config/auth.yaml`, `config/rbac.yaml` |
| Deployment | `Dockerfile`, `docker-compose.yml` |

> **Shim note:** several `app/*.py` files re-export canonical implementations from `modules/*`.
> Prefer editing the canonical `modules/*` source for new code.

---

## 7. Developer workflow

**Authoritative child:** [`docs/developer-manual/LOCAL_DEVELOPMENT_GUIDE.md`](LOCAL_DEVELOPMENT_GUIDE.md).

**There is no separate frontend build.** The UI is server-rendered Jinja2; static CSS/JS live in
`modules/shared/static` served at `/static/ecs`. Cache-busting via `app/main.py::asset_ver()`
(`?v=<mtime>`); `_no_cache_html` middleware prevents stale HTML. Just refresh the browser.

**Typical inner loop**

```bash
source venv/bin/activate
uvicorn app.main:app --reload          # leave running in one terminal
# edit modules/<domain>/engines/*.py  or  templates/*.html
# refresh browser; --reload restarts on .py changes
python scripts/validate_templates.py   # after any template edit
pytest -k "<area>"                       # run the relevant suites
```

**Where code lives**

| Concern | Location |
|---|---|
| App entry, route registrars | `app/main.py` |
| Auth (middleware, providers, enforcement) | `app/auth/` |
| Executive dashboards / reports / ROI | `modules/executive_overview/` |
| Framework catalog / dashboards / ITPP | `modules/frameworks/` |
| Scheduler / upload / integrations / connectors | `modules/operations/` |
| Evidence health/approval/lifecycle/audit-prep | `modules/governance/` |
| Risk register / CMDB / heatmaps / correlation | `modules/enterprise_grc/` |
| SDLC gates / control tower / AI posture | `modules/ai_sdlc/` |
| Shared state, RBAC, drilldown, UX, workflow | `modules/shared/` |
| Connectors, repository, vector store, RAG, config | `ecs_platform/` |
| YAML config | `config/` |

---

## 8. Command catalog

**Run / serve**

```bash
uvicorn app.main:app --reload                                   # local demo (127.0.0.1:8000)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000        # expose on LAN
docker compose up                                              # full stack
docker compose --profile sources --profile demo-connectors up -d
pkill -f uvicorn                                               # stop stray servers
```

**Demo data (Docker stack)**

```bash
./demo-data/recreate_demo.sh                                   # full rebuild + seed + verify
./demo-data/seed_demo_environment.sh                          # seed 6 apps across Gitea/Jenkins/SonarQube
python demo-data/seed_governance.py                          # seed governance data
curl -X POST localhost:8000/api/platform/sync/<gitea|jenkins|sonarqube>   # trigger evidence sync
```

**Test & validate** (see §9 for detail)

```bash
pip install pytest && pytest                                  # full suite (39 files)
python scripts/validate_templates.py                         # Jinja parse + macro + live render
python scripts/platform_certification.py                     # platform certification
```

**Backup / restore** (Postgres stack, see §13)

```bash
scripts/backup/backup.sh [--vector] [--out DIR] [--retention N] [--plain]
scripts/backup/validate_backup_restore.sh
scripts/restore/restore.sh --latest --clean
```

**Health checks**

```bash
curl -s localhost:8000/healthz                # liveness
curl -s localhost:8000/readyz                 # readiness (once Postgres reachable)
curl -s localhost:8000/api/platform/health    # evidence counts by source/type
```

---

## 9. Testing & validation

`pytest` is **not** in `requirements.txt`; install separately: `pip install pytest`. There is **no
`pytest.ini`, `pyproject.toml`, `setup.cfg`, or `conftest.py`** — pytest uses discovery defaults
over `tests/` (**39 test files**).

```bash
pytest                                  # full suite
pytest -q                               # quiet
pytest tests/test_roi_engine.py -v      # one file, verbose
pytest -k "rbac"                         # by keyword
```

**Validation / certification scripts** (run with the venv active):

```bash
python scripts/validate_templates.py          # parse + macro audit + live render via TestClient
python scripts/validate_demo_engine.py
python scripts/validate_demo_readiness.py
python scripts/validate_audit_prep.py
python scripts/validate_framework_loader.py
python scripts/platform_certification.py
python scripts/role_route_matrix_certification.py
```

Always run `scripts/validate_templates.py` after a template change.

**CI gate levels** (from the dependency report): `test_ecs_demo_readiness.py` and
`test_ecs_platform_governance.py` are **P0** (block release); framework/AI-SDLC drilldown suites
are P1; demo-polish / module-KPI suites are P2.

---

## 10. Branching strategy

**Current reality (verified):** default branch is **`main`**; active development happens on
**`cursor/*`** feature branches (e.g. `cursor/predefined-queries-module`) pushed to `origin`
(`github.com/ECS-Platform/ecs-enterprise-backup`). `old-origin` is a legacy backup remote.

**Working model**

| Branch | Use |
|---|---|
| `main` | Integration / default; protected. Always demo-ready (P0 suites green). |
| `cursor/<topic>` or `feature/<topic>` | Day-to-day feature work; branch from `main`, PR back to `main`. |
| `module/<domain>/*` | *Recommended* per-module convention (`ECS_MODULE_OWNERSHIP.md` §5). |
| `shared/*` | Shared-contract changes — require **2 module-owner approvals** (RFC first). |
| `platform/*` | Bootstrap / routing changes. |

**Rules**

- Branch from up-to-date `main`; rebase or merge `main` before opening a PR.
- **PR size guideline:** ≤15 files within a single module boundary.
- Changes to shared hotspots (`routes_mvp.py`, `module_capabilities.py`, `enterprise_context.py`,
  `ecs_state.py`, `enterprise_theme.html`, `ecs_nav_groups.html`) require coordination with the
  Shared/Platform owner (§14).
- Never commit `.env`, credentials, `demo-data/.gitea_token`, or DB backups (all git-ignored).

---

## 11. Release process

ECS has no separate package artifact; a "release" is a verified, tagged state of `main` deployed
via the container image (`Dockerfile`, `uvicorn app.main:app`).

**Checklist**

1. **Green gates on `main`:** `pytest` passes; P0 suites (`test_ecs_demo_readiness.py`,
   `test_ecs_platform_governance.py`) green; `python scripts/validate_templates.py` and
   `python scripts/platform_certification.py` pass.
2. **Demo smoke:** start in demo mode, log in as `cio`/`owner`/`auditor`/`vertical_head`, confirm
   dashboards and one drilldown render.
3. **Counts sanity:** verify against §1 (15 frameworks, 305 controls, 702 evidence, 12 connectors,
   9 roles, 10 services). Use `executive/documentation_audit.md` commands if in doubt.
4. **Tag:** annotated tag on the release commit, e.g. `git tag -a vYYYY.MM.DD-demo -m "..."`
   (follow the existing `demo-ready-*` / `roi-executive-dashboard-v*` naming seen in history).
5. **Build & deploy image:** `docker build -t ecs-api:<tag> .`; deploy per environment
   (DEV → UAT → PROD); set environment-specific `.env`/secrets (never baked into the image).
6. **Post-deploy verify:** `/healthz`, `/readyz` (with Postgres), `/api/platform/health`.
7. **Data safety (stateful deploys):** take a backup before deploy (§13); `init_schema()` is
   idempotent and reconciles additive columns on start.

> Schema change management is currently additive-via-`IF NOT EXISTS`; Alembic adoption is the
> planned path — see [`RECOVERY_RUNBOOK.md`](../operations/RECOVERY_RUNBOOK.md) §5.

---

## 12. Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| `401 unauthorized` / "missing_token" on pages | Demo flags not set in the env the server reads | Set `DEMO_MODE=true` + `ECS_AUTH_ENABLED=false` in `.env` and restart. `.env` **is** auto-loaded (§4); confirm the `[ECSStartup]` banner shows the flags. |
| Port 8000 in use | Prior uvicorn | `pkill -f uvicorn` or run on another `--port`. |
| `Evidence repository unavailable: ... host "postgres"` | No Postgres (demo) | **Expected** in demo mode; non-fatal. |
| `LLM-RAG disabled` | No LLM provider | **Expected**; assistant uses deterministic fallback. |
| Unstyled pages | Bootstrap CDN blocked | Allow jsDelivr or vendor Bootstrap locally. |
| Empty drill modal | Missing `role` in API call | Ensure `drilldown_engine.js` passes `role`. |
| Stale HTML/CSS after edit | Browser cache | `_no_cache_html` handles HTML; hard-refresh if needed; static uses `?v=<mtime>`. |
| Template error after edit | Jinja strictness | `python scripts/validate_templates.py`. |
| State "lost" after restart | In-memory design | Expected; lifespan re-seeds demo state. |
| `pytest: command not found` | Not installed | `pip install pytest` in the venv. |
| Import errors | Wrong path | Use `modules.*` canonical path (or an existing `app/*` shim). |

For operational (production/Postgres) incidents, see [`operations/ecs_runbook.md`](../operations/ecs_runbook.md).

---

## 13. Backup, restore & recovery

**Authoritative child:** [`docs/operations/RECOVERY_RUNBOOK.md`](../operations/RECOVERY_RUNBOOK.md) — full backup, restore,
validation-drill, DR quick reference, and the Alembic migration roadmap for the PostgreSQL evidence
repository.

Quick reference:

```bash
scripts/backup/backup.sh                                  # timestamped, checksummed dump to BACKUP_DIR
scripts/backup/validate_backup_restore.sh                # round-trip drill (exit 0 = PASS)
scripts/restore/restore.sh --latest --clean              # restore latest over live DB (maintenance window)
scripts/restore/restore.sh --latest --create --db ecs_repository_recovered
```

Backups contain **sensitive evidence/audit data** — store `BACKUP_DIR` on encrypted,
access-controlled storage; they are git-ignored.

---

## 14. Module ownership

**Authoritative child:** [`docs/developer-manual/ECS_MODULE_OWNERSHIP.md`](ECS_MODULE_OWNERSHIP.md) — owner matrix,
per-module scope, acceptance criteria, collaboration rules, test ownership, and definition of done.

| Module | Team | Owns (summary) |
|---|---|---|
| `executive_overview` | Executive Analytics | Role dashboards, demo KPI drill, reports, trends. |
| `frameworks` | Framework Engineering | Framework catalog, per-framework dashboards & drills, loader/admin, ITPP. |
| `operations` | Platform Operations | Scheduler, bulk upload, integrations, onboarding, AI Ops. |
| `governance` | Evidence & Audit | Audit prep, evidence health/lifecycle/completeness, evidence review workflows. |
| `enterprise_grc` | GRC Analytics | Risk register, CMDB, exceptions, heatmaps, correlation, GRC drills. |
| `ai_sdlc` | AI Governance | AI SDLC home, control tower, gates, posture, registry. |
| `shared` | Platform Core | Theme, nav, universal drill, state registry, RBAC, charts (RFC to change). |
| `platform` | Platform Core | `main.py` bootstrap, login, route registration, CI/validation runners. |

**Dependency rule:** `Module → Shared` ✅; `Module → Platform` (router registration) ✅;
`Shared → Module` ❌; `Module A → Module B` ❌ (use shared contracts).

---

## 15. Authoritative document map

This handbook is the entry point. It **links** these authoritative children and **supersedes** the
stale ones.

| Topic | Authoritative source |
|---|---|
| Quick start | [`README.md`](../README.md) |
| Setup (per-OS + Docker) | [`docs/developer-manual/DEVELOPER_SETUP_GUIDE.md`](DEVELOPER_SETUP_GUIDE.md) |
| Developer workflow | [`docs/developer-manual/LOCAL_DEVELOPMENT_GUIDE.md`](LOCAL_DEVELOPMENT_GUIDE.md) |
| Environment config | This handbook §4 + `.env.example` |
| Demo mode | This handbook §5 |
| Architecture package | [`docs/README.md`](README.md) (EA/HLD/LLD/ER/sequences/deployment/dossier/runbook) |
| Backup / restore / migration | [`docs/operations/RECOVERY_RUNBOOK.md`](../operations/RECOVERY_RUNBOOK.md) |
| Module ownership & branching | [`docs/developer-manual/ECS_MODULE_OWNERSHIP.md`](ECS_MODULE_OWNERSHIP.md) |
| Cross-module coupling | [`docs/developer-manual/ECS_DEPENDENCY_REPORT.md`](ECS_DEPENDENCY_REPORT.md) |
| Gap analysis behind this handbook | [`docs/archive/DOCUMENTATION_GAP_ANALYSIS.md`](../archive/DOCUMENTATION_GAP_ANALYSIS.md) |

**Superseded / use with caution**

| Document | Status |
|---|---|
| `docs/00-start-here/ECS_DEMO_MODE_SETUP_AND_TROUBLESHOOTING.md` | **Superseded by §4–§5/§12.** Its ".env not loaded" claim is incorrect for the current build. |
| `docs/architecture/ECS_Architecture_and_Deployment_Guide.md` §13/§15–§17 | **Superseded** for setup/deps/env (states 4 deps, "no Docker", "no .env"). Its as-built-vs-target comparison remains useful. |
| Root `architecture/ecs_enterprise_architecture_review.md` | Duplicate of `docs/architecture/...`; use the `docs/` copy. |
| `ECS_ARCHITECTURE_BASELINE.md` counts | Use computed counts in §1 (305 controls / 702 evidence, not ~307/~706). |
