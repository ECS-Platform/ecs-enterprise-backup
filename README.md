# ECS — Evidence & Compliance System

> Banking Governance, Risk, Compliance, Audit & Evidence-Management platform.
> FastAPI + Jinja2 (server-rendered), Python 3.12. Runs as a deterministic
> **demo** with zero external dependencies, or as a full connector-driven
> platform via Docker Compose.

This README is the **executive quick start**. For depth, see the onboarding set:

| Document | Purpose |
|---|---|
| [`docs/DEVELOPER_SETUP_GUIDE.md`](docs/DEVELOPER_SETUP_GUIDE.md) | Step-by-step setup for macOS / Linux / Windows (WSL) |
| [`docs/LOCAL_DEVELOPMENT_GUIDE.md`](docs/LOCAL_DEVELOPMENT_GUIDE.md) | Day-to-day local dev workflow, hot reload, tests |
| [`docs/ENVIRONMENT_CONFIGURATION.md`](docs/ENVIRONMENT_CONFIGURATION.md) | Every environment variable, required/default/purpose |
| [`docs/DEMO_MODE_SETUP.md`](docs/DEMO_MODE_SETUP.md) | Running ECS in demo mode (no auth, no DB) |
| [`docs/COMMON_COMMANDS.md`](docs/COMMON_COMMANDS.md) | Command catalog (start/stop/test/seed/backup…) |
| [`docs/TROUBLESHOOTING_GUIDE.md`](docs/TROUBLESHOOTING_GUIDE.md) | Symptom → root cause → resolution → verification |
| [`docs/ARCHITECTURE_OVERVIEW.md`](docs/ARCHITECTURE_OVERVIEW.md) | Mission, modules, evidence flow, RBAC, APIs, UI |

---

## What ECS is

ECS is a **modular monolith**: one FastAPI app (`app/main.py`, entry `app.main:app`) that composes six business-domain packages under `modules/` (`executive_overview`, `frameworks`, `operations`, `governance`, `enterprise_grc`, `ai_sdlc`) plus a shared core (`modules/shared/`) and an infrastructure layer (`ecs_platform/`: connectors, evidence repository, vector store, RAG, config loader).

- **Backend:** FastAPI + Uvicorn (`requirements.txt`).
- **Frontend:** Server-rendered Jinja2 (Bootstrap + vanilla JS in `modules/shared/static/js/drilldown_engine.js`). **There is no Node/npm build** — `package-lock.json` declares no packages.
- **Data:** In-process deterministic demo state by default; optional PostgreSQL + pgvector + MinIO + Redis via `docker-compose.yml`.
- **Config:** YAML under `config/` with `${ENV}` resolution (`ecs_platform/config/loader.py`); flags loaded from `.env` at startup (`app/env_bootstrap.py`).

---

## Fastest start (demo mode, no Docker, no database)

Requires **Python 3.12** and **git**. Runs entirely on deterministic in-memory data.

```bash
# 1. Clone
git clone <your-ecs-remote-url> ECS
cd ECS

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate            # Windows (WSL): same; native PowerShell: venv\Scripts\Activate.ps1

# 3. Install Python dependencies (the complete, canonical set)
pip install -r requirements.txt

# 4. Configure demo mode (no Azure AD, no JWT, no RBAC enforcement)
cp .env.example .env
# then edit .env and set:
#   DEMO_MODE=true
#   ECS_AUTH_ENABLED=false

# 5. Run the app
uvicorn app.main:app --reload

# 6. Open the UI
#   http://127.0.0.1:8000/
#   Liveness:  http://127.0.0.1:8000/healthz   -> {"status":"ok"}
```

> **Note on `start_ecs.sh`:** the repo ships a convenience script, but it installs only a *subset* of dependencies (`fastapi uvicorn jinja2 python-multipart`) and kills existing uvicorn processes. Prefer `pip install -r requirements.txt` so `pyyaml`, `pyjwt`, `python-dotenv`, `psycopg2-binary` and `openpyxl` are present. See [`docs/COMMON_COMMANDS.md`](docs/COMMON_COMMANDS.md).

### Expected startup output (abridged)

The lifespan handler (`app/main.py::ecs_lifespan`) logs a startup banner and seeds demo state:

```
[ECSStartup] ECS Startup
[ECSStartup] DEMO_MODE=true
[ECSStartup] ECS_AUTH_ENABLED=false
[ECSStartup] .env loaded=True via python-dotenv
[ECSPlatform] Evidence repository unavailable: ...   # expected without Postgres
[ECSPlatform] LLM-RAG disabled: provider not configured (assistant uses deterministic fallback)
... platform ready on 127.0.0.1:8000
```

The "repository unavailable" and "LLM-RAG disabled" lines are **normal in demo mode** — the app serves fully without a database or LLM.

---

## Full stack (Docker Compose — real connectors, DB, RAG)

Requires **Docker** + **Docker Compose**.

```bash
# Core platform (app + Postgres x2 + pgvector + Redis + MinIO)
docker compose up

# Add self-hosted source systems (Gitea + Jenkins)
docker compose --profile sources up -d

# Add the SonarQube demo connector
docker compose --profile demo-connectors up -d

# One-shot: tear down, rebuild, seed 6 apps, sync evidence, verify
./demo-data/recreate_demo.sh
```

Service ports (from `docker-compose.yml`): app `8000`, postgres-demo `5432`, repository postgres `5433`, pgvector `5434`, redis `6379`, MinIO `9002` (console `9001`), Gitea `3000`, Jenkins `8080`, SonarQube `9000`.

---

## Run the tests

```bash
pip install pytest          # not in requirements.txt; install separately
pytest                      # runs the 39 suites in tests/
pytest tests/test_roi_engine.py -v
```

There is no `pytest.ini`, `pyproject.toml` or `conftest.py`; pytest uses discovery defaults.

---

## Repository layout (top level)

```
app/            FastAPI entry point, route registrars, auth, env bootstrap, subsystems
modules/        Six business domains + shared core (engines + Jinja templates)
ecs_platform/   Connectors, evidence repository, pgvector store, RAG, config loader
config/         YAML config (auth, rbac, llm, vectorstore, repository, integrations, roi, sufficiency…)
demo-data/      Seed scripts (Gitea/Jenkins/SonarQube), demo narrative, sample assets
scripts/        Validators, certification, backup/restore, migration utilities
tests/          39 pytest suites
docs/           Architecture, HLD/LLD, diagrams, runbook, and this onboarding set
Dockerfile      python:3.12-slim image (uvicorn app.main:app)
docker-compose.yml  10-service local stack
requirements.txt    9 Python dependencies
.env.example    Authoritative environment template
```

---

## License / status

Internal banking platform. Demo state is synthetic and deterministic. Never commit `.env`, live credentials, `demo-data/.gitea_token`, or database backups (all git-ignored).
