# ECS — Common Commands

Copy-paste command catalog. Every command is derived from the repository (`requirements.txt`, `Dockerfile`, `docker-compose.yml`, `start_ecs.sh`, `app/main.py`, `scripts/`, `demo-data/`). Run Python commands with the virtual environment activated.

> **Tooling.** A `Makefile` provides convenience targets (`make help`, `make install`, `make run`, `make test`, `make ci`, `make smoke`, `make compile`, …) that wrap the underlying commands below. There is no `pyproject.toml`/`pytest.ini` and no Node/`npm` toolchain — the raw commands are plain `pip`, `uvicorn`, `pytest`, `docker compose`, and the shell scripts under `demo-data/` and `scripts/`.

---

## Environment setup

```bash
python3.12 -m venv venv                 # create venv (Python 3.12)
source venv/bin/activate                # activate (macOS/Linux/WSL)
pip install -r requirements.txt         # install the 9 runtime deps
pip install pytest                      # test runner (not in requirements.txt)
cp .env.example .env                    # create env file (then set DEMO_MODE/ECS_AUTH_ENABLED)
```

---

## Start ECS (native)

```bash
# Recommended: hot-reload dev server on 127.0.0.1:8000
uvicorn app.main:app --reload

# Bind to all interfaces / custom port
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Convenience script (installs a SUBSET of deps, kills existing uvicorn, opens browser)
./start_ecs.sh
```

## Stop ECS (native)

```bash
pkill -f uvicorn                        # stop all uvicorn processes (as start_ecs.sh does)
# or Ctrl-C in the foreground terminal
```

---

## Start / stop ECS (Docker)

```bash
docker compose up                       # core platform (foreground)
docker compose up -d                    # core platform (detached)
docker compose --profile sources up -d            # + Gitea + Jenkins
docker compose --profile demo-connectors up -d     # + SonarQube + ubuntu-demo
docker compose --profile sources --profile demo-connectors up -d   # everything

docker compose ps                       # service status
docker compose logs -f ecs              # follow ECS logs
docker compose restart ecs              # restart just the app
docker compose down                     # stop & remove containers (keeps volumes)
docker compose down -v                  # stop & remove containers AND volumes (clean slate)
```

## Rebuild Docker image

```bash
docker compose build ecs                # rebuild the ECS image
docker compose build --no-cache ecs     # rebuild ignoring cache
docker compose up -d --build ecs        # rebuild + restart
```

---

## Health checks

```bash
curl -s http://127.0.0.1:8000/healthz                # liveness  -> {"status":"ok"}
curl -s http://127.0.0.1:8000/readyz                 # readiness -> 200 (DB up) / 503 (no DB)
curl -s http://localhost:8000/api/platform/health    # evidence counts by source/type
```

---

## Tests

```bash
pytest                                  # full suite (39 files under tests/)
pytest -q                               # quiet
pytest -v                               # verbose
pytest tests/test_roi_engine.py         # one file
pytest tests/test_roi_engine.py::<test_name>     # one test
pytest -k "rbac"                         # by keyword (e.g. RBAC suites)
pytest -k "rbac or sufficiency" -v
pytest --maxfail=1 -x                    # stop on first failure
```

---

## Lint / format

No linter or formatter is configured in the repo (no `ruff`, `flake8`, `black`, or `pre-commit` config present). If your team standardizes on tools, install them into the venv, e.g.:

```bash
pip install ruff black                  # not currently part of the project
ruff check .
black .
```
(Adopt only by team agreement — these are not repository dependencies today.)

---

## Validation & certification scripts (`scripts/`)

```bash
python scripts/validate_templates.py             # Jinja parse + macro audit + live render
python scripts/validate_demo_engine.py            # demo overview + /api/demo/* endpoints
python scripts/validate_demo_readiness.py
python scripts/validate_audit_prep.py             # /mvp/audit-prep across roles
python scripts/validate_framework_loader.py
python scripts/validate_post_migration.py
python scripts/run_ecs_validation.py
python scripts/platform_certification.py
python scripts/module_focus_certification.py
python scripts/role_route_matrix_certification.py
```

---

## Demo data

```bash
# Full lifecycle: down -v -> up -> seed -> sync -> verify (DESTROYS volumes)
./demo-data/recreate_demo.sh

# Seed 6 apps across Gitea/Jenkins/SonarQube (writes demo-data/.gitea_token)
./demo-data/seed_demo_environment.sh

# Targeted seeders
python demo-data/seed_governance.py
./demo-data/seed_jenkins_demo.sh
./demo-data/seed_sonarqube_demo.sh
./demo-data/seed_pipeline_demo.sh

# Wire the Gitea token into ECS and restart it
export GITEA_TOKEN=$(cat demo-data/.gitea_token)
docker compose up -d ecs
```

## Refresh evidence (trigger connector collection)

```bash
# Per connector (mutation-guarded; demo mode bypasses the guard)
curl -s -X POST http://localhost:8000/api/platform/sync/gitea
curl -s -X POST http://localhost:8000/api/platform/sync/jenkins
curl -s -X POST http://localhost:8000/api/platform/sync/sonarqube

# Via the UI route
curl -s -X POST "http://localhost:8000/mvp/platform/sync-all?role=admin&user=Admin"

# List collected evidence (optionally filtered)
curl -s "http://localhost:8000/api/platform/evidence?source_system=gitea"
curl -s "http://localhost:8000/api/platform/evidence?application=payments"
```

---

## Reset database / clean slate

```bash
docker compose down -v                  # removes ecs_repo_data, ecs_vector_data, etc.
docker compose up -d                    # fresh DBs; schema re-inits best-effort on ECS startup
# (Native showcase has no DB to reset — demo state regenerates each startup.)
```

## Clear caches

```bash
# Python bytecode caches
find . -type d -name __pycache__ -prune -exec rm -rf {} +
find . -type f -name '*.pyc' -delete

# Pytest cache
rm -rf .pytest_cache

# Config loader cache is in-process (lru_cache); a process restart clears it.
# Redis (Docker stack):
docker compose exec redis redis-cli FLUSHALL
```

---

## Backup & restore (PostgreSQL repository — Docker stack)

```bash
scripts/backup/backup.sh                         # dump repository to $BACKUP_DIR (default ./backups)
scripts/backup/validate_backup_restore.sh        # round-trip validation
scripts/restore/restore.sh <dump-file>           # restore from a dump
```
Configured by `BACKUP_DIR` (`./backups`) and `BACKUP_RETENTION_DAYS` (`14`) in `.env`. Backups are git-ignored.

---

## Generate reports

```bash
# Excel/control-library exports use openpyxl inside the app (reporting module).
# docker-compose.yml bind-mounts a control-library workbook read-only:
#   ./ECS_Query_Driven_Control_Library_Consolidated.xlsx -> /app/... (provide this
#   file locally if you rely on it; the repo ships ECS_ROI.xlsx / ROI.xlsx instead).
# Reports are produced through the UI (Executive Overview > Reports) and the
# governance reporting routes; there is no standalone CLI report command.
```

---

## Service URLs & ports (Docker stack)

| Service | URL / port |
|---|---|
| ECS app | http://localhost:8000 |
| Repository Postgres | localhost:5433 (→ container 5432) |
| pgvector | localhost:5434 (→ container 5432) |
| Demo-connectors Postgres | localhost:5432 |
| Redis | localhost:6379 |
| MinIO API / console | http://localhost:9002 / http://localhost:9001 |
| Gitea | http://localhost:3000 |
| Jenkins | http://localhost:8080 |
| SonarQube | http://localhost:9000 |

---

## Quick reference

| Task | Command |
|---|---|
| Start ECS (native) | `uvicorn app.main:app --reload` |
| Stop ECS (native) | `pkill -f uvicorn` |
| Start full stack | `docker compose --profile sources --profile demo-connectors up -d` |
| Stop full stack | `docker compose down` |
| Clean slate | `docker compose down -v` |
| Run tests | `pytest` |
| Recreate demo | `./demo-data/recreate_demo.sh` |
| Refresh evidence | `curl -X POST localhost:8000/api/platform/sync/<connector>` |
| Liveness check | `curl localhost:8000/healthz` |
| Rebuild image | `docker compose build ecs` |
