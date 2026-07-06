# Predefined Database Query Module — Developer Guide

**Applies to branch:** `cursor/predefined-queries-module`
**Scope:** Predefined read-only checks for databases (PostgreSQL, YugabyteDB/YSQL,
Aurora MySQL, Oracle) and infrastructure (NGINX, Linux, Red Hat Enterprise Linux
8.x, Red Hat Enterprise Linux 9.x).

---

## 1. Purpose

The Predefined Query Module lets ECS run a curated, **read-only** set of database
baselining checks (SSL/TLS posture, privileges, extensions, replication, audit
config, etc.) against enterprise databases, capture the output as **evidence**,
and map it to compliance frameworks — without a human running SQL by hand.

This guide covers these technologies:

| Technology | Wire / execution | Driver / connector | Default port |
|------------|------------------|--------------------|--------------|
| PostgreSQL | PostgreSQL | `psycopg2` | 5432 |
| YugabyteDB (YSQL) | PostgreSQL-compatible | `psycopg2` (reused) | 5433 |
| Aurora MySQL | MySQL-compatible | `PyMySQL` | 3306 |
| Oracle | Oracle Net | `python-oracledb` (thin) | 1521 |
| NGINX | shell (docker exec) | Linux connector (reused) | n/a (container/SSH) |
| Linux | shell (docker exec) | Linux connector | n/a (container/SSH) |
| Red Hat Enterprise Linux 8.x | shell (docker exec) | Linux connector (reused) | n/a |
| Red Hat Enterprise Linux 9.x | shell (docker exec) | Linux connector (reused) | n/a |

Database queries are **read-only** and enforced by a per-technology **exact-SQL
allow-list**. Infrastructure (NGINX/Linux/RHEL) checks run **curated shell
commands** from the code-defined catalog (never user input), gated by control id.
Only vetted queries/commands can execute live.

---

## 2. Supported databases & queries

Supplementary query definitions live in
`modules/operations/engines/supplementary_query_catalog.py` (data only; kept
separate from execution logic). The primary control library remains the Excel
workbook `ECS_Query_Driven_Control_Library_Consolidated.xlsx`; supplementary
entries are merged additively (Excel always wins on `control_id` collision).

### PostgreSQL (`PGX-001`..`PGX-008`)
`SHOW ssl;` · `SHOW password_encryption;` · `SELECT * FROM pg_stat_replication;` ·
roles/privileges · database sizes · active sessions · installed extensions ·
pgaudit check.

### YugabyteDB / YSQL (`YBX-001`..`YBX-008`)
`SELECT * FROM yb_servers();` · `SELECT version();` · active sessions ·
roles/privileges · database sizes · user table list · extensions · `SHOW ssl;`.

### Aurora MySQL (`MYX-001`..`MYX-010`)
`SHOW VARIABLES LIKE 'have_ssl';` · `require_secure_transport` · `log_bin` ·
`server_audit%` · `mysql.user` accounts · `SELECT VERSION();` · `SHOW DATABASES;` ·
`SHOW PROCESSLIST;` · grants summary · `SHOW VARIABLES LIKE '%ssl%'`.

### Oracle (`ORX-001`..`ORX-010`)
`v$version` · `v$database` open mode · `v$encryption_wallet` · `audit_trail`
parameter · profile failed-login/password policy · privileged users · role grants ·
tablespaces · datafile encryption · active sessions.

### NGINX (`NGX-001`..`NGX-008`)
`nginx -v` · `nginx -t` · TLS protocols/ciphers · `server_tokens` · access/error
log config · enabled sites. (Shell commands executed inside the NGINX container.)

### Linux (`LNX-001`..`LNX-008`)
`/etc/os-release` · `uname -a` · running services · firewall status · SSH
PermitRootLogin/PasswordAuthentication · sudoers · local users.

### Red Hat Enterprise Linux 8.x (`RH8-001`..`RH8-008`)
`/etc/redhat-release` · crypto policy · SELinux · firewalld · auditd · SSH
settings · installed security updates (`dnf/yum updateinfo`). Technology label:
**Red Hat Enterprise Linux 8.x**.

### Red Hat Enterprise Linux 9.x (`RH9-001`..`RH9-008`)
`/etc/redhat-release` · crypto policy · SELinux · firewalld · auditd · SSH
settings · FIPS mode. Technology label: **Red Hat Enterprise Linux 9.x**.

---

## 3. Connector architecture

```
predefined_queries_engine.run_predefined_query(control_id, user)
  ├─ PostgreSQL   → run_postgresql_query() → PostgreSQLConnector (psycopg2)
  ├─ YugabyteDB   → run_yugabyte_query()   → YugabyteConnector(PostgreSQLConnector)
  ├─ Aurora MySQL → run_mysql_query()      → MySQLConnector (PyMySQL)
  └─ Linux / SonarQube / Trivy / GitLeaks  → existing connectors
        │
        └─ each: connect() → execute(query) → disconnect()
                 → complete_connector_execution()  (audit + evidence + API payload)
```

| File | Responsibility |
|------|----------------|
| `modules/operations/engines/predefined_queries_engine.py` | Catalog load, technology detection, capability assessment, allow-lists, dispatch |
| `modules/operations/engines/query_connectors.py` | `ConnectorResult`, `BaseConnector`, `connector_for_technology()` routing |
| `modules/operations/engines/postgresql_connector.py` | PostgreSQL connector (psycopg2) + shared config helpers (`_safe_int`, `_clean`) |
| `modules/operations/engines/yugabyte_connector.py` | YugabyteDB connector — thin subclass of PostgreSQL (PG-wire) |
| `modules/operations/engines/mysql_connector.py` | Aurora MySQL / MySQL 8 connector (PyMySQL) |
| `modules/operations/engines/supplementary_query_catalog.py` | Code-defined supplementary DB queries (data only) |
| `modules/operations/engines/connector_common.py` | Shared post-execution path (audit → evidence → payload) |

All connectors return the same `ConnectorResult(success, output, error_message,
duration_ms, metadata)` and pipe-delimited text output, so downstream handling is
identical regardless of technology.

**Design principles honoured:** additive changes; no duplicate engine; query
catalog separate from execution; credentials externalised; passwords never
logged; graceful degradation when a driver is missing or a DB is unreachable.

---

## 4. Where to configure IPs / hosts / ports

Two layers, resolved in this order per field (first non-empty wins):

1. **Active-environment YAML** — `config/environments/_base.yaml` (overridable per
   env in `config/environments/<env>.yaml`), block
   `predefined_query_targets.{postgresql,yugabyte,aurora_mysql}`. Values there use
   `${ENV_VAR:-default}` placeholders.
2. **Environment variables** — the `ECS_*` vars below (also honoured by the YAML).

> **Never hard-code UAT/cloud IPs, endpoints, or credentials in source code.**
> Put them in `.env` (local, git-ignored) or the environment YAML / your
> deployment's secret store.

`ECS_ENV` selects the environment (`local` default; also `dev`, `sit`, `uat`,
`prod`).

### Exact place to enter each value

Set these in your **`.env`** (copied from `.env.example`) — this is the primary
place a developer enters connection details. (Equivalently, set the same values
in `config/environments/<env>.yaml` under `predefined_query_targets`.)

| Field | PostgreSQL | YugabyteDB | Aurora MySQL |
|-------|------------|------------|--------------|
| Host / IP / endpoint | `ECS_PG_HOST` | `ECS_YB_HOST` | `ECS_MYSQL_HOST` |
| Port | `ECS_PG_PORT` (5432) | `ECS_YB_PORT` (5433) | `ECS_MYSQL_PORT` (3306) |
| Database name | `ECS_PG_DATABASE` | `ECS_YB_DATABASE` | `ECS_MYSQL_DATABASE` |
| Username | `ECS_PG_USER` | `ECS_YB_USER` | `ECS_MYSQL_USER` |
| Password | `ECS_PG_PASSWORD` | `ECS_YB_PASSWORD` | `ECS_MYSQL_PASSWORD` |
| SSL/TLS | `ECS_PG_SSLMODE` | `ECS_YB_SSLMODE` | `ECS_MYSQL_SSL` (true/false) |
| Timeout (s) | `ECS_PG_TIMEOUT_SECONDS` | `ECS_YB_TIMEOUT_SECONDS` | `ECS_MYSQL_TIMEOUT_SECONDS` |

- **Local Docker:** keep the defaults (`localhost` + the ports above). Bring the
  targets up with `docker compose --profile db-targets up -d`.
- **UAT / cloud:** put the real endpoint/credentials in `.env` (or the env YAML) —
  e.g. `ECS_MYSQL_HOST=my-aurora.cluster-xxxx.<region>.rds.amazonaws.com`. Never
  commit real endpoints/credentials.

Run `python scripts/check_predefined_db_environment.py` after editing `.env` to
confirm each field resolves and the target is reachable (passwords are shown only
as SET/MISSING).

---

## 5. Required environment variables

Placeholders are in `.env.example`. Copy to `.env` and fill real values.

### PostgreSQL
```
ECS_PG_HOST            (default localhost)
ECS_PG_PORT            (default 5432)
ECS_PG_DATABASE        (default ecs_demo)
ECS_PG_USER            (default ecs_user)
ECS_PG_PASSWORD
ECS_PG_SSLMODE         (disable|allow|prefer|require|verify-ca|verify-full; default prefer)
ECS_PG_TIMEOUT_SECONDS (default 30)   # legacy ECS_PG_TIMEOUT_SEC still honoured
```

### YugabyteDB (YSQL)
```
ECS_YB_HOST            (default localhost)
ECS_YB_PORT            (default 5433)
ECS_YB_DATABASE        (default yugabyte)
ECS_YB_USER            (default yugabyte)
ECS_YB_PASSWORD
ECS_YB_SSLMODE         (default prefer)
ECS_YB_TIMEOUT_SECONDS (default 30)
```

### Aurora MySQL
```
ECS_MYSQL_HOST            (default localhost)
ECS_MYSQL_PORT            (default 3306)
ECS_MYSQL_DATABASE        (default ecs_demo)
ECS_MYSQL_USER            (default ecs_user)
ECS_MYSQL_PASSWORD
ECS_MYSQL_SSL             (true|false; true requires TLS)
ECS_MYSQL_TIMEOUT_SECONDS (default 30)
```

### Oracle
```
ECS_ORACLE_HOST            (default localhost)
ECS_ORACLE_PORT            (default 1521)
ECS_ORACLE_SERVICE_NAME    (default XEPDB1)
ECS_ORACLE_USER            (default ecs_user)
ECS_ORACLE_PASSWORD
ECS_ORACLE_TIMEOUT_SECONDS (default 30)
```
Requires an **external Oracle endpoint** (or an optional Oracle XE container on a
16/20 GB machine). No Oracle container starts by default.

### NGINX
```
ECS_NGINX_CONTAINER        (default nginx-demo)   # docker-exec target
ECS_NGINX_TIMEOUT_SECONDS  (default 30)
# Future remote SSH mode (not yet executed):
# ECS_NGINX_HOST / ECS_NGINX_SSH_USER / ECS_NGINX_SSH_KEY_PATH
```

### Linux / RHEL 8.x / RHEL 9.x
```
ECS_LINUX_CONTAINER        (default ubuntu-demo)  # shared by Linux + RHEL checks
ECS_LINUX_TIMEOUT_SECONDS  (default 30)
# Future remote SSH mode (not yet executed):
# ECS_LINUX_HOST / ECS_LINUX_SSH_USER / ECS_LINUX_SSH_KEY_PATH
```
Linux, RHEL 8.x, and RHEL 9.x controls all run shell commands via the same
docker-exec connector; the RHEL split is a catalog/label distinction (point
`ECS_LINUX_CONTAINER` at the appropriate target).

Use **read-only** DB/OS users. Passwords are read from the environment and are
never logged.

---

## 6. Local Docker testing (16 GB machine recommended)

The DB target containers are **opt-in** (compose profile `db-targets`) so they do
not run by default on 8 GB laptops.

```bash
# PostgreSQL demo target is always available (postgres-demo, port 5432):
docker compose up -d postgres-demo

# YugabyteDB (5433) + MySQL 8 as Aurora stand-in (3306):
docker compose --profile db-targets up -d yugabyte mysql-demo
```

Defaults created locally:

| Target | Host | Port | DB / user / pass |
|--------|------|------|------------------|
| PostgreSQL | localhost | 5432 | ecs_demo / ecs_user / ecs_password |
| YugabyteDB | localhost | 5433 | yugabyte / yugabyte / (none) |
| MySQL 8 (Aurora sim) | localhost | 3306 | ecs_demo / ecs_user / ecs_password |

> Aurora MySQL is AWS-managed; MySQL 8 is wire-compatible for these read-only
> baselining checks and is sufficient for local validation.

> **8 GB machines:** run only `postgres-demo`. Hand off `--profile db-targets`
> (Yugabyte + MySQL) validation to a 16 GB teammate, or point `ECS_*_HOST` at a
> shared UAT endpoint instead.

---

## 7. UAT / cloud configuration

1. Put the real endpoints in your `.env` or `config/environments/uat.yaml`
   (`predefined_query_targets.*`), **never** in code.
2. Use a **read-only** DB account (no DBA/admin).
3. Set `ECS_PG_SSLMODE` / `ECS_YB_SSLMODE` and `ECS_MYSQL_SSL` per bank policy
   (typically `require`/`verify-full` for PostgreSQL/Yugabyte, `true` for MySQL).
4. Ensure DNS resolves the cloud endpoint from the ECS host / your laptop / VPN.
5. Ensure VPN / bank network routing is active.

---

## 8. Firewall / network requirements

For UAT / cloud connectivity, the network path from the **source**
(developer laptop / VPN / ECS backend host) to the **database** must allow
**outbound** access on the listener port:

| Target | Port (TCP) |
|--------|------------|
| PostgreSQL | **5432** |
| Yugabyte YSQL | **5433** |
| Aurora MySQL | **3306** |
| Oracle | **1521** |
| Remote Linux / NGINX via SSH (future mode) | **22** |
| NGINX HTTP / HTTPS (as applicable) | 80 / 443 |

Checklist:

- Use **read-only** DB/OS users; avoid DBA/admin users.
- Ensure **DNS resolution** for cloud endpoints from the source host.
- Ensure **VPN / bank network routing** is active.
- Ensure the **database/host security group / firewall** allows the source subnet.
- Ensure **SSL/TLS mode** is configured as required by bank policy.
- **AWS Aurora:** the RDS **security group inbound** must allow the
  client/VPN/ECS subnet on **TCP 3306**.
- **Cloud PostgreSQL / Yugabyte:** allow the ECS backend/client subnet on the
  DB listener port (**5432 / 5433**).
- **Oracle:** allow the source subnet to the listener on **TCP 1521** (and the
  correct service name / PDB).
- **NGINX / Linux / RHEL:** local checks use `docker exec` (no network port). For
  remote hosts (future SSH mode), allow **TCP 22** to the target.
- **UAT IPs/endpoints** go in environment YAML or `.env`, **not** hard-coded in
  source.

---

## 9. How to run the predefined queries

### From the UI
Open **Operations → Predefined Queries** (`/mvp/predefined-queries`). Rows whose
status is **Ready** (implemented connector + driver installed + target
configured) show a **Run Query** action. Running one executes the allow-listed
query, records an audit entry, and stores the output as evidence.

### Programmatically (Python)
```python
from modules.operations.engines.predefined_queries_engine import (
    run_predefined_query, run_postgresql_query, run_yugabyte_query, run_mysql_query,
)

run_predefined_query("PGX-001", "developer")   # auto-dispatch by technology
run_yugabyte_query("YBX-001", "developer")      # YugabyteDB
run_mysql_query("MYX-001", "developer")         # Aurora MySQL
```

### Minimal CLI runner
A safe, dependency-light runner is provided:
```bash
python scripts/run_predefined_db_query.py --list                 # list DB controls + status
python scripts/run_predefined_db_query.py --control PGX-001      # run one (needs a reachable DB)
python scripts/run_predefined_db_query.py --control MYX-001 --user analyst
```
It never executes anything outside the allow-list and prints a JSON result.

### Onboarding diagnostic (run this first)
Before running queries, verify environment/config/connectivity:
```bash
export PYTHONPATH="$PWD"
python scripts/check_predefined_db_environment.py         # text report
python scripts/check_predefined_db_environment.py --json  # machine-readable
scripts/check_predefined_db_environment.sh                # wrapper (auto venv + PYTHONPATH)
```
It checks, per database: config resolution (passwords shown only as SET/MISSING),
Docker container status, TCP connectivity, and a `SELECT 1` login — printing an
**actionable recommendation** on any failure. Exit code 0 = all pass, 1 = failure.
Flags: `--skip-postgres`, `--skip-yugabyte`, `--skip-mysql`, `--no-docker-check`, `--json`.

---

## 9a. Validate each database

Start the local targets first (16 GB machine):
```bash
docker compose --profile db-targets up -d postgres-demo yugabyte mysql-demo
sleep 20
python scripts/check_predefined_db_environment.py
```

### Validate PostgreSQL
```bash
python scripts/check_predefined_db_environment.py --skip-yugabyte --skip-mysql
python scripts/run_predefined_db_query.py --control PGX-001    # SHOW ssl;
```
Expect TCP + login **PASS** and a query result.

### Validate YugabyteDB
```bash
python scripts/check_predefined_db_environment.py --skip-postgres --skip-mysql
python scripts/run_predefined_db_query.py --control YBX-001    # SELECT * FROM yb_servers();
```
YSQL is PostgreSQL-wire; the same psycopg2 driver is used on port 5433.

### Validate Aurora MySQL (local MySQL 8)
```bash
python scripts/check_predefined_db_environment.py --skip-postgres --skip-yugabyte
python scripts/run_predefined_db_query.py --control MYX-001    # SHOW VARIABLES LIKE 'have_ssl';
```
If login **FAILS** with "Authentication failed", it's a credential mismatch — see
the Aurora MySQL troubleshooting row in §12.

---

## 10. How to add a new predefined query

1. Add an entry to the appropriate list in
   `modules/operations/engines/supplementary_query_catalog.py` (id, name, SQL,
   `technology`, description). Use an id prefix that won't collide with Excel
   (`PGX-`, `YBX-`, `MYX-`).
2. Add the **exact normalized SQL** to the matching allow-list in
   `predefined_queries_engine.py` (`ALLOWED_POSTGRESQL_QUERIES` /
   `ALLOWED_YUGABYTE_QUERIES` / `ALLOWED_MYSQL_QUERIES`). Normalization =
   lowercase, collapsed whitespace, trailing `;`.
3. (Optional) Add a test asserting it's covered by the allow-list.
4. `python -m compileall modules` and `pytest tests/test_predefined_db_connectors.py`.

The control becomes **Ready** automatically when its driver is installed and the
control id is in `LIVE_CONTROL_IDS` (supplementary ids are added there
automatically).

---

## 11. How to add a new database connector

1. Create `modules/operations/engines/<tech>_connector.py` with:
   - `get_<tech>_config()` reading `ECS_<TECH>_*` env vars (+ optional YAML block),
     using `_safe_int` / `_clean` for placeholder-safe parsing.
   - A connector class exposing `connect() -> bool`, `execute(query) -> ConnectorResult`,
     `disconnect()`. Return the standard `ConnectorResult` + pipe-delimited output.
2. Add the technology to `TECHNOLOGY_RULES`, `_IMPLEMENTED_CONNECTOR_TECH`, and
   `_dependency_available()` in `predefined_queries_engine.py`.
3. Add a `run_<tech>_query()` dispatch branch and an allow-list.
4. Add routing in `query_connectors.connector_for_technology()`.
5. Add the driver to `requirements.txt` and (optionally) a `db-targets`
   docker-compose service.
6. Add a YAML block under `predefined_query_targets` and `.env.example` vars.
7. Add tests.

---

## 12. Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| Status **Dependency Missing** | Driver not installed. `pip install -r requirements.txt` (psycopg2-binary / PyMySQL). |
| Status **Configuration Required** | Control not in `LIVE_CONTROL_IDS` or query not allow-listed. |
| `Could not connect to the database` | Target not running / firewall / wrong host or port. Check `docker compose ps`, security group, VPN. |
| `Authentication failed` / `Access denied` | Wrong DB user/password, or user lacks connect/read rights. Use a read-only account with access. |
| MySQL `command denied` on `mysql.user` | The read-only user lacks `SELECT` on `mysql.user`. Grant read on the needed system tables or skip those controls. |
| Yugabyte `yb_servers()` not found | Not a YugabyteDB endpoint, or too old a version. Confirm the host/port is YSQL (5433). |
| TLS errors | Adjust `ECS_PG_SSLMODE` / `ECS_YB_SSLMODE` / `ECS_MYSQL_SSL` to match server policy. |
| Query times out | Increase `ECS_*_TIMEOUT_SECONDS`; check DB load/network. |
| Unresolved `${...}` in config | Ensure the env var is exported before startup, or rely on the built-in default. |

Passwords are never printed in logs or errors.

> **Tip:** run `python scripts/check_predefined_db_environment.py` first — it
> pinpoints which layer fails (config / Docker / TCP / login) and prints the
> recommended fix, without ever revealing passwords.

### Aurora MySQL — "Authentication failed. Verify MySQL credentials."

- **Symptom:** the MySQL predefined query (e.g. `MYX-001`) fails with
  *"Authentication failed. Verify MySQL credentials."*
- **Meaning:** ECS **reached** the MySQL/Aurora server (TCP OK) but the
  **username / password / database** does not match — it is **not** a network or
  firewall problem.
- **Check** (inspect what the container actually expects):
  ```bash
  docker compose config | grep MYSQL
  docker inspect mysql-demo
  docker logs mysql-demo
  ```
- **Fix:** align your `.env` values with the target DB (or the container's
  `MYSQL_ROOT_PASSWORD` / `MYSQL_USER` / `MYSQL_PASSWORD` / `MYSQL_DATABASE`):
  ```bash
  # In .env — must match the MySQL/Aurora account you intend to use:
  ECS_MYSQL_USER=ecs_user
  ECS_MYSQL_PASSWORD=<the matching password>
  ECS_MYSQL_DATABASE=ecs_demo
  ```
  The local `mysql-demo` container (see `docker-compose.yml`) creates
  `MYSQL_USER=ecs_user` / `MYSQL_PASSWORD=ecs_password` / `MYSQL_DATABASE=ecs_demo`
  and a root account via `MYSQL_ROOT_PASSWORD`. Use `ecs_user` (not root) for
  normal validation, and ensure the password matches. Re-run
  `python scripts/check_predefined_db_environment.py --skip-postgres --skip-yugabyte`
  to confirm the login now passes.

---

## 13. New developer — checkout & run

```bash
git status
git checkout cursor/predefined-queries-module
git pull origin cursor/predefined-queries-module

python -m venv .venv
source .venv/bin/activate           # Windows Git Bash: source .venv/Scripts/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt   # pytest + httpx (dev/test deps)

cp .env.example .env
# Edit .env: set local Docker or UAT/cloud DB endpoints + read-only credentials.

export PYTHONPATH="$PWD"

# Onboarding diagnostic (config/Docker/TCP/login; never prints passwords):
python scripts/check_predefined_db_environment.py

# Unit tests (no live DB required):
pytest tests/test_predefined_db_connectors.py tests/test_predefined_db_environment_diagnostic.py

# (Optional) local DB targets on a 16 GB machine:
docker compose up -d postgres-demo
docker compose --profile db-targets up -d yugabyte mysql-demo

# List DB predefined queries and their status:
python scripts/run_predefined_db_query.py --list

# Run one against a reachable DB:
python scripts/run_predefined_db_query.py --control PGX-001

# Commit / push (only your changes):
git status
git add .
git commit -m "feat: add predefined database query connectors"
git push origin cursor/predefined-queries-module
```

---

## 14. Cross-references
- `docs/operations/ECS_PREDEFINED_QUERY_EXECUTION_GUIDE.md`
- `docs/operations/ECS_CONNECTOR_INVENTORY.md`
- `docs/PRODUCTION/ECS_REMOTE_CONNECTOR_EXPANSION_PLAN.md`
