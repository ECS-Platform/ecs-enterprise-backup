# ECS — Troubleshooting Guide

Each entry is **Symptom → Root cause → Resolution → Verification**, derived from the actual code paths (`app/env_bootstrap.py`, `app/main.py`, `routes_platform.py`, `docker-compose.yml`, the seed scripts, and `docs/ECS_DEMO_MODE_SETUP_AND_TROUBLESHOOTING.md`).

---

## 1. `401 unauthorized` / "Missing Authorization header" on dashboards

**Symptom**
```json
{"error":"unauthorized","reason":"missing_token","detail":"Missing or malformed Authorization header."}
```
on `/dashboard`, `/mvp/roi`, executive pages (but `/`, `/login`, `/healthz` work).

**Root cause** — ECS is secure-by-default (`ECS_AUTH_ENABLED` defaults to `true` in `config/auth.yaml`). The uvicorn process did not receive `DEMO_MODE`/`ECS_AUTH_ENABLED`, so auth middleware enforces tokens. This happens when the flags are exported in a different shell than the one running uvicorn, or there is no `.env`.

**Resolution** — put the flags in the repo-root `.env` (loaded by `app/env_bootstrap.py` at startup):
```bash
cp .env.example .env
# ensure these lines:
#   DEMO_MODE=true
#   ECS_AUTH_ENABLED=false
# restart uvicorn
```

**Verification** — startup log shows `DEMO_MODE=true`, `ECS_AUTH_ENABLED=false`, `.env loaded=True via python-dotenv`; dashboards load without a token.

---

## 2. `ModuleNotFoundError: No module named 'yaml'` / `jwt` / `dotenv` on startup

**Symptom** — uvicorn crashes immediately importing `app.main` with a missing-module error.

**Root cause** — only a subset of dependencies installed. `start_ecs.sh` installs only `fastapi uvicorn jinja2 python-multipart`, but the app also needs `pyyaml` (config loading), `pyjwt[crypto]` (auth init at import time), `python-dotenv`, `psycopg2-binary`, and `openpyxl`.

**Resolution**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**Verification** — `python -c "import yaml, jwt, dotenv, psycopg2, openpyxl"` exits cleanly; uvicorn starts.

---

## 3. `.env` changes have no effect

**Symptom** — edited `.env` but ECS still uses old values.

**Root cause** — `app/env_bootstrap.py` loads `.env` with `override=False`: any variable **already present in the real environment wins**. A stale `export DEMO_MODE=...` in your shell (or compose `environment:`) overrides the file.

**Resolution** — unset the conflicting shell export (`unset DEMO_MODE ECS_AUTH_ENABLED`) or set the value in the actual environment instead of `.env`. `.env` is loaded once per process — **restart uvicorn** after editing.

**Verification** — `printenv DEMO_MODE` in the uvicorn shell matches your intent; restart and re-check the startup banner.

---

## 4. Port already in use (`Address already in use` / bind error)

**Symptom** — uvicorn or `docker compose up` fails to bind a port.

**Root cause** — another process holds the port. ECS uses: `8000` (app), `5432` (postgres-demo), `5433` (repository postgres), `5434` (pgvector), `6379` (redis), `9002`/`9001` (MinIO + console), `3000` (Gitea), `8080`/`50000` (Jenkins), `9000` (SonarQube), `2222` (Gitea SSH).

**Resolution**
```bash
# find the holder (macOS/Linux)
lsof -i :8000
# run uvicorn on another port
uvicorn app.main:app --reload --port 8001
# or stop the conflicting container
docker compose down
```

**Verification** — `lsof -i :8000` is empty before start; `curl http://127.0.0.1:<port>/healthz` returns ok.

---

## 5. `/readyz` returns 503 (`not-ready`)

**Symptom**
```json
{"status":"not-ready","repository_ok":false,"detail":"..."}
```

**Root cause** — `/readyz` (`routes_platform.py`) does a `SELECT 1` against the PostgreSQL evidence repository; 503 means Postgres is unreachable. **This is expected in native demo mode** (no DB).

**Resolution** — if you intend to run without a DB, ignore it and use `/healthz` (liveness) instead. To get a ready DB, start the stack:
```bash
docker compose up -d postgres
```
Confirm `ECS_REPO_PG_HOST/PORT/USER/PASSWORD` match the running Postgres.

**Verification** — `curl http://localhost:8000/readyz` returns `{"status":"ready","repository_ok":true}`.

---

## 6. Python version errors (syntax / typing)

**Symptom** — `SyntaxError`, or pip wheels fail to install.

**Root cause** — wrong interpreter. ECS targets **Python 3.12** (`Dockerfile: python:3.12-slim`).

**Resolution**
```bash
python3.12 -m venv venv && source venv/bin/activate
python --version            # must show 3.12.x
pip install -r requirements.txt
```

**Verification** — `python --version` shows 3.12 inside the venv; install succeeds.

---

## 7. "Should I run `npm install`?" / missing Node build

**Symptom** — expecting a frontend build step; looking for `npm install`/`npm run build`.

**Root cause** — there is **no Node frontend**. `package-lock.json` declares no packages; the UI is server-rendered Jinja2 with vanilla JS served from `modules/shared/static`.

**Resolution** — skip Node entirely. Just run the backend (`uvicorn app.main:app`). Template/CSS/JS changes are picked up on browser refresh.

**Verification** — UI renders at `http://127.0.0.1:8000/` with only the Python app running.

---

## 8. Permission denied running seed/backup scripts

**Symptom** — `permission denied: ./demo-data/recreate_demo.sh`.

**Root cause** — script bit not set, or invoked without a shell.

**Resolution**
```bash
chmod +x demo-data/*.sh scripts/backup/*.sh scripts/restore/*.sh
# or run via bash explicitly:
bash demo-data/recreate_demo.sh
```

**Verification** — `ls -l demo-data/recreate_demo.sh` shows `x`; the script runs.

---

## 9. Docker: connectors show "disconnected" / seeding fails

**Symptom** — Integration Health shows sources unreachable; `seed_demo_environment.sh` reports scan/job failures.

**Root cause** — source services not started (they live behind Docker Compose **profiles**), or seeded before SonarQube finished booting. By default `docker compose up` does **not** start `gitea`, `jenkins` (`sources` profile) or `sonarqube-demo`, `ubuntu-demo` (`demo-connectors` profile).

**Resolution**
```bash
docker compose --profile sources --profile demo-connectors up -d
# wait for SonarQube to report UP, then seed (the script already waits):
./demo-data/seed_demo_environment.sh
```

**Verification** — `curl http://localhost:9000/api/system/status` returns `"status":"UP"`; `curl http://localhost:8000/api/platform/health` shows non-zero evidence counts.

---

## 10. Docker: ECS connector can't reach Gitea/SonarQube/Jenkins

**Symptom** — connectors fail inside the container though the services are up.

**Root cause** — using `localhost` URLs from inside the container. Inter-container traffic must use **service names** (`gitea:3000`, `sonarqube-demo:9000`, `jenkins:8080`) — which is exactly what `docker-compose.yml` sets (`GITEA_URL=http://gitea:3000`, etc.). Host-side tools use `localhost:<mapped-port>`.

**Resolution** — don't override the in-container URLs with `localhost`. After seeding, wire the Gitea token and restart ECS:
```bash
export GITEA_TOKEN=$(cat demo-data/.gitea_token)
docker compose up -d ecs
```

**Verification** — `curl http://localhost:8000/api/platform/health` reports evidence from `gitea`, `jenkins`, `sonarqube`.

---

## 11. Database connection refused (host run)

**Symptom** — `connection refused` / `could not connect to server` from `/readyz` or durable-audit paths.

**Root cause** — repository Postgres is published on host port **5433** (`docker-compose.yml` maps `5433:5432`), but `.env.example` defaults `ECS_REPO_PG_PORT=5432`. A host process pointed at `5432` hits the wrong Postgres (or none).

**Resolution** — for a host-run ECS talking to the composed repository DB, set:
```bash
ECS_REPO_PG_HOST=localhost
ECS_REPO_PG_PORT=5433
ECS_REPO_PG_PASSWORD=ecs_password
```
(Inside the compose network ECS uses `ECS_REPO_PG_HOST=postgres` / port `5432`.)

**Verification** — `psql -h localhost -p 5433 -U ecs_user -d ecs_repository -c 'select 1'` succeeds; `/readyz` is ready.

---

## 12. LLM assistant returns generic / fallback answers

**Symptom** — the assistant won't use RAG; logs say `LLM-RAG disabled: provider not configured`.

**Root cause** — no reachable LLM provider. Default provider is local **Ollama** at `OLLAMA_URL` (`http://host.docker.internal:11434`); if Ollama isn't running (or a cloud key isn't set) ECS uses a deterministic fallback by design.

**Resolution** — run Ollama locally (`ollama serve` + `ollama pull qwen3:8b nomic-embed-text`) or set a cloud provider (`ECS_LLM_PROVIDER=gemini` + `GEMINI_API_KEY=...`). On Linux Docker, `extra_hosts: host.docker.internal:host-gateway` (already set) lets the container reach a host Ollama.

**Verification** — startup logs `LLM-RAG ready: provider=… model=… vector_chunks=…`.

---

## 13. macOS-specific notes

| Symptom | Cause | Resolution |
|---|---|---|
| `psycopg2` install fails | Missing libpq when building from source | `psycopg2-binary` (in `requirements.txt`) ships wheels — ensure you install `requirements.txt`, not `psycopg2`. If still failing: `brew install postgresql@16`. |
| Port `5000`/AirPlay confusion | macOS uses 5000 for AirPlay Receiver | ECS does **not** use 5000; ignore. |
| Container can't reach host Ollama | — | `host.docker.internal` resolves automatically on Docker Desktop for Mac (no `extra_hosts` needed). |
| `.DS_Store` noise in template audit | Finder metadata | harmless; git-ignored. |

---

## 14. First place to look

Always read the **startup banner** first — `ecs_lifespan` prints the effective `DEMO_MODE`, `ECS_AUTH_ENABLED`, and how `.env` was parsed. Most "it won't load" issues are an env-not-applied problem (entries 1–3 above). For the full demo-mode playbook see `docs/DEMO_MODE_SETUP.md`.
