# ECS — Developer Setup Guide

Step-by-step environment setup for a **brand-new engineer** on macOS, Linux, and Windows (WSL2). Every command, path, dependency and port below is derived from the repository (`requirements.txt`, `Dockerfile`, `docker-compose.yml`, `start_ecs.sh`, `app/main.py`, `app/env_bootstrap.py`, `.env.example`, `config/`).

> **Two ways to run ECS — pick one:**
> 1. **Native (Python only)** — fastest; runs ECS in **demo mode** with deterministic in-memory data. No database, no Docker, no LLM required.
> 2. **Docker Compose** — full stack with PostgreSQL, pgvector, MinIO, Redis, and real source connectors (Gitea/Jenkins/SonarQube).
>
> This guide covers both. Start with Native to get the UI up in minutes.

---

## 0. What you are installing

| Component | Version / source | Required for |
|---|---|---|
| Python | **3.12** (`Dockerfile`: `python:3.12-slim`) | Always |
| git | any recent | Cloning |
| pip dependencies | `requirements.txt` (9 packages) | Always |
| Docker + Docker Compose | any recent | Only for the full stack |
| Node.js / npm | **Not required** | The UI is server-rendered Jinja2; `package-lock.json` declares no packages |

The 9 Python dependencies (`requirements.txt`): `fastapi`, `uvicorn`, `jinja2`, `python-multipart`, `openpyxl`, `psycopg2-binary`, `python-dotenv`, `pyyaml`, `pyjwt[crypto]`.
`pytest` is **not** in `requirements.txt` — install it separately to run the 39 suites in `tests/`.

---

## 1. macOS

### 1.1 Prerequisites

```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python 3.12 and git
brew install python@3.12 git

# (Optional, for the full stack) Docker Desktop
brew install --cask docker
```

Verify:

```bash
python3.12 --version     # Python 3.12.x
git --version
```

### 1.2 Clone

```bash
git clone <your-ecs-remote-url> ECS
cd ECS
```

### 1.3 Virtual environment + dependencies

```bash
python3.12 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pytest                 # optional: to run the test suite
```

**Reproducible / production installs.** `requirements.txt` uses flexible minimum
(`>=`) pins for development. For a **reproducible** build (production/UAT/CI-parity)
install the pinned lockfile instead:

```bash
pip install -r requirements.lock          # exact pinned versions
# or:  make install-locked
```

Regenerate the lock after changing `requirements.txt` (from a known-good venv):

```bash
make lock                                  # -> scripts/gen_requirements_lock.py
# or, if pip-tools is available:
pip install pip-tools && pip-compile --output-file=requirements.lock requirements.txt
```

### 1.4 Environment variables (demo mode)

```bash
cp .env.example .env
```

Edit `.env` and set (the two flags that matter for a no-auth local run):

```bash
DEMO_MODE=true
ECS_AUTH_ENABLED=false
```

Everything else can stay at its `.env.example` default. See `docs/developer-manual/ENVIRONMENT_CONFIGURATION.md` for the full table.

### 1.5 Database initialization — not required in demo mode

ECS boots without any database. The lifespan handler calls `init_repository()` **best-effort** and logs `Evidence repository unavailable: …` when Postgres is absent — this is expected and non-fatal. Skip to 1.7. (For durable persistence, use the Docker stack in §4.)

### 1.6 Seed data — automatic in demo mode

Demo workflow state is seeded automatically on startup by `seed_demo_workflow_state()` (`modules/executive_overview/engines/demo_seed.py`), invoked from `app/main.py::ecs_lifespan`. No manual seed step is needed for the showcase UI. (Connector-driven evidence seeding is a Docker-stack activity — see §4.4.)

### 1.7 Start the app

```bash
uvicorn app.main:app --reload
```

### 1.8 Health-check verification

```bash
curl -s http://127.0.0.1:8000/healthz
# {"status": "ok"}
```

Open `http://127.0.0.1:8000/` in a browser → you should see the ECS login/role chooser.

### 1.9 Expected output

Startup logs include the banner from `ecs_lifespan`:

```
[ECSStartup] ECS Startup
[ECSStartup] DEMO_MODE=true
[ECSStartup] ECS_AUTH_ENABLED=false
[ECSStartup] .env loaded=True via python-dotenv
[ECSPlatform] Evidence repository unavailable: ...
[ECSPlatform] LLM-RAG disabled: provider not configured (assistant uses deterministic fallback)
```

---

## 2. Linux (Debian/Ubuntu)

### 2.1 Prerequisites

```bash
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv python3-pip git
# psycopg2-binary ships wheels; if building from source you'd also need:
#   sudo apt-get install -y build-essential libpq-dev
# (Optional, full stack) Docker Engine + Compose plugin:
#   https://docs.docker.com/engine/install/
```

Verify:

```bash
python3.12 --version
git --version
```

### 2.2 Clone, venv, dependencies

```bash
git clone <your-ecs-remote-url> ECS
cd ECS
python3.12 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pytest                 # optional
```

### 2.3 Environment variables

```bash
cp .env.example .env
# set DEMO_MODE=true and ECS_AUTH_ENABLED=false in .env
```

### 2.4 Database / seed

Same as macOS §1.5–1.6: not required in demo mode; demo state seeds automatically at startup.

### 2.5 Start + verify

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
curl -s http://127.0.0.1:8000/healthz     # {"status":"ok"}
```

Use `--host 0.0.0.0` if you need to reach the app from another machine; otherwise the default `127.0.0.1` is fine.

---

## 3. Windows (WSL2)

ECS uses bash scripts, `psycopg2`, and a Unix-style layout. **Run it inside WSL2 (Ubuntu)**, not native Windows PowerShell.

### 3.1 Enable WSL2 + Ubuntu (PowerShell as Administrator)

```powershell
wsl --install -d Ubuntu
# reboot if prompted, then open the "Ubuntu" app
```

### 3.2 Inside the Ubuntu (WSL) shell — prerequisites

```bash
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv python3-pip git
```

If `python3.12` is unavailable on your Ubuntu release:

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv
```

For the full Docker stack, install **Docker Desktop for Windows** and enable **WSL2 integration** (Docker Desktop → Settings → Resources → WSL Integration).

### 3.3 Clone INSIDE the WSL filesystem (not /mnt/c)

```bash
cd ~
git clone <your-ecs-remote-url> ECS
cd ECS
```

> Cloning into the Linux home (`~`) rather than `/mnt/c/...` avoids slow file I/O and permission issues.

### 3.4 venv + dependencies + env

```bash
python3.12 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pytest                 # optional
cp .env.example .env
# set DEMO_MODE=true and ECS_AUTH_ENABLED=false in .env
```

### 3.5 Start + verify

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

From Windows, open `http://localhost:8000/` (WSL2 forwards localhost). Verify:

```bash
curl -s http://127.0.0.1:8000/healthz     # {"status":"ok"}
```

---

## 4. Full stack with Docker Compose (all platforms)

The stack is defined in `docker-compose.yml` (10 services). The `ecs` service builds from the root `Dockerfile` (`python:3.12-slim`, `uvicorn app.main:app`) and bind-mounts `app/`, `modules/`, `ecs_platform/` for hot reload.

### 4.1 Core platform

```bash
docker compose up
```

Brings up: `ecs` (8000), `postgres-demo` (5432), `postgres` repository (host 5433), `pgvector` (host 5434), `redis` (6379), `minio` (host 9002, console 9001).

### 4.2 Add source systems (Gitea + Jenkins)

```bash
docker compose --profile sources up -d
```

### 4.3 Add SonarQube demo connector

```bash
docker compose --profile demo-connectors up -d
```

### 4.4 Seed connector evidence (the differentiator demo)

```bash
# End-to-end: tear down (with volumes) -> up -> seed 6 apps -> sync -> verify
./demo-data/recreate_demo.sh
```

This seeds 6 applications (`mobile-banking net-banking upi payments treasury api-gateway`) across Gitea/Jenkins/SonarQube (`demo-data/seed_demo_environment.sh`), writes `demo-data/.gitea_token`, then triggers ECS evidence collection and prints verification counts.

### 4.5 Verify the full stack

```bash
curl -s http://localhost:8000/healthz                 # {"status":"ok"}
curl -s http://localhost:8000/readyz                  # {"status":"ready", ...} once Postgres is reachable
curl -s http://localhost:8000/api/platform/health     # evidence counts by source/type
```

UI entry points seeded by the script:

```
http://localhost:8000/mvp/integration-health?role=admin&user=Admin
http://localhost:8000/mvp/evidence-explorer?role=admin&user=Admin
```

---

## 5. Post-setup checklist

- [ ] `python --version` shows 3.12 inside the activated venv.
- [ ] `pip install -r requirements.txt` completed without errors.
- [ ] `.env` exists with `DEMO_MODE=true` and `ECS_AUTH_ENABLED=false` (native demo run).
- [ ] `uvicorn app.main:app --reload` starts and logs the `[ECSStartup]` banner.
- [ ] `curl http://127.0.0.1:8000/healthz` returns `{"status":"ok"}`.
- [ ] Browser loads `http://127.0.0.1:8000/`.
- [ ] (Optional) `pytest` runs the suite in `tests/`.

Stuck? See `docs/00-start-here/TROUBLESHOOTING_GUIDE.md`.
