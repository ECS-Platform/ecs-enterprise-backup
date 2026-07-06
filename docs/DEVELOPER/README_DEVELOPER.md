# ECS Developer Onboarding — Start Here

Entry point for any new developer on the **Evidence Collection System (ECS)**.
Follow this top-to-bottom to get a working local environment and run the
predefined database query module.

> Deep-dive for the database query module: [PREDEFINED_DATABASE_QUERY_MODULE.md](PREDEFINED_DATABASE_QUERY_MODULE.md).

---

## 1. ECS overview

ECS is an enterprise **Evidence Collection and Audit Readiness** platform (not a
GRC platform). It automates collection of compliance evidence — including
running curated, **read-only** database baselining checks (the *Predefined Query
Module*) — maps results to frameworks, and drives audit-readiness workflows.
Backend: **FastAPI + Jinja + Python**.

---

## 2. Repository structure

```
app/                     FastAPI app entrypoint (app/main.py), routes, auth
modules/                 Feature modules (module-oriented)
  operations/engines/    Predefined query engine + DB connectors
  ai_sdlc/ ...           Other feature modules
  shared/                Shared services, templates, routes
ecs_platform/            Platform foundation (config loader, repository, RAG)
config/                  YAML config + environments/<env>.yaml
scripts/                 Operational + diagnostic scripts
tests/                   Pytest test suite
docs/                    Documentation (DEVELOPER/, operations/, ...)
requirements.txt         Runtime dependencies
requirements-dev.txt     Development/test dependencies (pytest, httpx)
docker-compose.yml       Local services (app, DBs, demo connectors)
.env.example             Environment template (copy to .env)
```

---

## 3. Required software

| Software | Notes |
|----------|-------|
| **Git** | Clone / branch / commit |
| **Python 3.11+** | Runtime (3.11, 3.12, or newer) |
| **Docker Desktop** | Runs local databases / services |
| **Docker Compose** | Bundled with Docker Desktop |
| **Cursor** (optional) | AI-assisted development |

---

## 4. Recommended hardware

| RAM | Suitable for |
|-----|--------------|
| **8 GB** | Code generation / light development only. **Do not** run the full Docker DB stack, Ollama, or benchmarks. |
| **16 GB** | Docker, databases, Ollama, benchmarking, and integration testing. |

> On an 8 GB machine, run only lightweight containers (e.g. `postgres-demo`) or
> point `ECS_*_HOST` at a shared UAT endpoint. Hand off the full `db-targets`
> profile (Yugabyte + MySQL) to a 16 GB teammate.

---

## 5. Branch to use

```
cursor/predefined-queries-module
```

---

## 6. First-time checkout

```bash
# HTTPS
git clone https://github.com/ECS-Platform/ecs-enterprise-backup.git
cd ecs-enterprise-backup
git checkout cursor/predefined-queries-module
git pull origin cursor/predefined-queries-module
```

---

## 7. Python virtual environment

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

### Windows (Git Bash)
```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

Then copy the environment template and edit values:
```bash
cp .env.example .env
# Edit .env: set local Docker or UAT/cloud DB endpoints + READ-ONLY credentials.
```

---

## 8. Docker startup

```bash
# Lightweight PostgreSQL demo target (always available):
docker compose up -d postgres-demo

# Full predefined-query DB targets (16 GB machine): PostgreSQL + Yugabyte + MySQL 8
docker compose --profile db-targets up -d postgres-demo yugabyte mysql-demo
```

Local ports: PostgreSQL **5432**, YugabyteDB YSQL **5433**, MySQL (Aurora sim) **3306**.

---

## 9. Run predefined database queries

```bash
export PYTHONPATH="$PWD"           # Windows Git Bash: same command

# Database-only runner:
python scripts/run_predefined_db_query.py --list           # list DB controls + status
python scripts/run_predefined_db_query.py --control PGX-001   # PostgreSQL
python scripts/run_predefined_db_query.py --control YBX-001   # YugabyteDB
python scripts/run_predefined_db_query.py --control MYX-001   # Aurora MySQL

# General runner (all technologies: DB + Oracle + NGINX + Linux + RHEL):
python scripts/run_predefined_query.py --list
python scripts/run_predefined_query.py --list --technology Oracle
python scripts/run_predefined_query.py --control ORX-001    # Oracle
python scripts/run_predefined_query.py --control NGX-001    # NGINX
python scripts/run_predefined_query.py --control LNX-001    # Linux
python scripts/run_predefined_query.py --control RH8-001    # RHEL 8.x
python scripts/run_predefined_query.py --control RH9-001    # RHEL 9.x
```

Only allow-listed, read-only queries (and curated shell commands) run. Supported
technologies: PostgreSQL, YugabyteDB, Aurora MySQL, Oracle, NGINX, Linux, Red Hat
Enterprise Linux 8.x, and Red Hat Enterprise Linux 9.x. Details:
[PREDEFINED_DATABASE_QUERY_MODULE.md](PREDEFINED_DATABASE_QUERY_MODULE.md).

---

## 10. Run tests

```bash
export PYTHONPATH="$PWD"
python -m pytest tests/test_predefined_db_connectors.py \
                 tests/test_predefined_db_environment_diagnostic.py
```

These do **not** require live Docker or databases.

---

## 11. Run onboarding diagnostics

Before running queries, verify your environment/config/connectivity:

```bash
export PYTHONPATH="$PWD"
python scripts/check_predefined_db_environment.py

# Or the wrapper (auto-activates .venv, sets PYTHONPATH):
scripts/check_predefined_db_environment.sh

# Machine-readable / partial checks:
python scripts/check_predefined_db_environment.py --json
python scripts/check_predefined_db_environment.py --skip-mysql --no-docker-check
```

The diagnostic prints each DB's config (passwords shown only as **SET/MISSING**),
Docker container status, TCP connectivity, and a `SELECT 1` login check with an
**actionable recommendation** on failure. Exit code 0 = all pass, 1 = a failure.

---

## 12. Stop Docker containers

```bash
docker compose --profile db-targets down     # stop DB targets
docker compose down                           # stop everything
```

---

## 13. Full onboarding command blocks

### Windows Git Bash (16 GB laptop)
```bash
cd ~/Documents/ecs-enterprise-backup

docker compose --profile db-targets up -d postgres-demo yugabyte mysql-demo

sleep 20

python -m venv .venv
source .venv/Scripts/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt

export PYTHONPATH="$PWD"

python scripts/check_predefined_db_environment.py

python -m pytest tests/test_predefined_db_connectors.py tests/test_predefined_db_environment_diagnostic.py

python scripts/run_predefined_db_query.py --list

python scripts/run_predefined_db_query.py --control PGX-001
python scripts/run_predefined_db_query.py --control YBX-001
python scripts/run_predefined_db_query.py --control MYX-001

docker compose --profile db-targets down
```

### macOS / Linux
```bash
cd ~/Documents/ecs-enterprise-backup

docker compose --profile db-targets up -d postgres-demo yugabyte mysql-demo

sleep 20

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt

export PYTHONPATH="$PWD"

python scripts/check_predefined_db_environment.py

python -m pytest tests/test_predefined_db_connectors.py tests/test_predefined_db_environment_diagnostic.py

python scripts/run_predefined_db_query.py --list

python scripts/run_predefined_db_query.py --control PGX-001
python scripts/run_predefined_db_query.py --control YBX-001
python scripts/run_predefined_db_query.py --control MYX-001

docker compose --profile db-targets down
```

> The repo directory name may differ (e.g. `ECS` vs `ecs-enterprise-backup`);
> adjust the `cd` path to wherever you cloned it.

---

## 14. Troubleshooting links

- **Predefined DB query module + full troubleshooting table:**
  [PREDEFINED_DATABASE_QUERY_MODULE.md](PREDEFINED_DATABASE_QUERY_MODULE.md)
- **Release notes / changelog:** [../../CHANGELOG.md](../../CHANGELOG.md)
  (see the `ecs-predefined-db-complete-v1` milestone for the predefined database
  query module release summary)
- **Environment/connectivity diagnostic:** `scripts/check_predefined_db_environment.py`
- **Local auth / demo mode:** `docs/LOCAL_AUTH_DEMO_FIX.md`, `docs/DEMO_MODE_SETUP.md`
- **Common commands:** `docs/COMMON_COMMANDS.md`

### Quick fixes
| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError` running scripts | `export PYTHONPATH="$PWD"` (run from repo root). |
| Status **Dependency Missing** | `pip install -r requirements.txt` (psycopg2-binary / PyMySQL). |
| `pytest: command not found` | `pip install -r requirements-dev.txt`. |
| DB `Connection refused` | Start the container / check host, port, VPN, security group. |
| MySQL **Authentication failed** | Align `ECS_MYSQL_USER/PASSWORD/DATABASE` with docker-compose / target creds (see module doc). |
