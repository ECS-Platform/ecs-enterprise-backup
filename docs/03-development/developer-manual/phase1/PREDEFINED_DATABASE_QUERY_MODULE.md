# Predefined Database Query Module — Developer Guide

**Applies to branch:** `cursor/predefined-queries-module`
**Scope:** Predefined read-only checks for databases (PostgreSQL, YugabyteDB/YSQL,
Aurora MySQL, Oracle, SQL Server, MongoDB, Aerospike), middleware/OS (NGINX,
Apache HTTPD, Tomcat, Redis, Linux, Red Hat Enterprise Linux 8.x/9.x), and
container platforms (Kubernetes, OpenShift). Also includes ServiceNow CMDB and
Archer integration skeletons.

> **Aerospike:** local testing, the 20 `ASX-*` queries, run-query behaviour, and
> the "why isn't my technology in the dropdown?" troubleshooting are documented in
> [AEROSPIKE_LOCAL_TESTING_GUIDE.md](../connectors/AEROSPIKE_LOCAL_TESTING_GUIDE.md).

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
| SQL Server | TDS | `pyodbc` (optional) | 1433 |
| MongoDB | Mongo wire | `pymongo` (optional) | 27017 |
| Redis | redis-cli (docker exec) | Redis connector (Linux subclass) | 6379 |
| Apache HTTPD | shell (docker exec) | Linux connector (reused) | n/a |
| Tomcat | shell (docker exec) | Linux connector (reused) | n/a |
| Kubernetes | `kubectl` (local CLI) | Kubernetes connector | n/a |
| OpenShift | `oc` (local CLI) | OpenShift connector | n/a |

Database queries are **read-only** and enforced by a per-technology **exact-SQL
allow-list** (MongoDB uses an admin-command allow-list). Middleware/OS/container
checks run **curated shell / CLI commands** from the code-defined catalog (never
user input), gated by control id. Only vetted queries/commands can execute live.

**Enterprise integrations (skeletons):** ServiceNow CMDB (`servicenow_cmdb`) and
Archer (`archer`) under `modules/operations/integrations/` — config-driven, with
an injectable HTTP transport (mocked in tests; no real calls). See §15.

---

## 2. Supported databases & queries

Supplementary query definitions live in
`modules/operations/engines/supplementary_query_catalog.py` (data only; kept
separate from execution logic). The primary control library remains the Excel
workbook `ECS_Query_Driven_Control_Library_Consolidated.xlsx`; supplementary
entries are merged additively (Excel always wins on `control_id` collision).

### PostgreSQL (`PGX-001`..`PGX-013`)
`SHOW ssl;` · `SHOW password_encryption;` · `SELECT * FROM pg_stat_replication;` ·
roles/privileges · database sizes · active sessions · installed extensions ·
pgaudit check · connection limits (`max_connections`) · long-running queries ·
database uptime (`pg_postmaster_start_time`) · schema/object inventory ·
security parameters (`log_connections`/`ssl`/`log_statement`).

### YugabyteDB / YSQL (`YBX-001`..`YBX-011`)
`SELECT * FROM yb_servers();` · `SELECT version();` · active sessions ·
roles/privileges · database sizes · user table list · extensions · `SHOW ssl;` ·
connection limits · long-running queries · security parameters.

### Aurora MySQL (`MYX-001`..`MYX-014`)
`SHOW VARIABLES LIKE 'have_ssl';` · `require_secure_transport` · `log_bin` ·
`server_audit%` · `mysql.user` accounts · `SELECT VERSION();` · `SHOW DATABASES;` ·
`SHOW PROCESSLIST;` · grants summary · `SHOW VARIABLES LIKE '%ssl%'` · connection
limit (`max_connections`) · long-running queries (`information_schema.processlist`) ·
failed connections (`Aborted_connects`) · uptime (`Uptime`).

### Oracle (`ORX-001`..`ORX-014`)
`v$version` · `v$database` open mode · `v$encryption_wallet` · `audit_trail`
parameter · profile failed-login/password policy · privileged users · role grants ·
tablespaces · datafile encryption · active sessions · connection/resource limits
(`v$resource_limit`) · instance uptime (`v$instance`) · long-running sessions ·
schema object inventory (`dba_objects`).

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

### Redis (`RDX-001`..`RDX-008`)
`INFO server` · persistence (`save`/`appendonly`) · `requirepass` · protected-mode ·
`bind` · `tls-port` · `maxmemory-policy`. Run via `redis-cli` inside the container.

### Apache HTTPD (`APX-001`..`APX-008`)
version · config test · loaded modules · `ServerTokens`/`ServerSignature` ·
`SSLProtocol` · access/error log config. Missing binaries → "not available".

### Tomcat (`TCX-001`..`TCX-008`)
version · Catalina process · `server.xml` · Connectors · manager app · `tomcat-users.xml` ·
shutdown port · `AccessLogValve`. Missing files/processes → "not available".

### SQL Server (`MSX-001`..`MSX-013`)
`@@VERSION` · edition/level · auth mode · logins · sysadmin members · databases ·
TDE state · security config · audit specs · default-trace auditing · connection
limit (`user connections`) · long-running requests (`sys.dm_exec_requests`) ·
uptime (`sys.dm_os_sys_info`). SQL Server/MongoDB allow-lists derive from the
catalog automatically (no engine edit needed to add a query).

### MongoDB (`MGX-001`..`MGX-010`)
`buildInfo` · `serverStatus` · auth (`getCmdLineOpts`) · TLS (`sslMode`) · users ·
roles · databases · audit param · replication status (`replSetGetStatus`) ·
current operations (`currentOp`). Admin commands run via `db.command()`.

### Kubernetes (`K8X-001`..`K8X-010`)
version · nodes · namespaces · cluster roles/bindings · pods · network policies ·
secrets inventory · service accounts · pod-security labels. Via `kubectl`.

### OpenShift (`OCX-001`..`OCX-010`)
version · cluster operators · nodes · projects · cluster roles/bindings · SCC ·
OAuth config · routes · image policy. Via `oc`.

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

### Extended technologies
```
# Redis (redis-cli in the container)
ECS_REDIS_HOST / ECS_REDIS_PORT / ECS_REDIS_PASSWORD(optional) / ECS_REDIS_CONTAINER / ECS_REDIS_TIMEOUT_SECONDS
# Apache HTTPD / Tomcat (docker exec)
ECS_APACHE_CONTAINER / ECS_APACHE_TIMEOUT_SECONDS
ECS_TOMCAT_CONTAINER / ECS_TOMCAT_TIMEOUT_SECONDS
# SQL Server (pyodbc; optional/heavy)
ECS_SQLSERVER_HOST / ECS_SQLSERVER_PORT / ECS_SQLSERVER_DATABASE / ECS_SQLSERVER_USERNAME / ECS_SQLSERVER_PASSWORD / ECS_SQLSERVER_TIMEOUT_SECONDS
# MongoDB (pymongo)
ECS_MONGODB_URI / ECS_MONGODB_DATABASE / ECS_MONGODB_CONTAINER / ECS_MONGODB_TIMEOUT_SECONDS
# Kubernetes / OpenShift (local kubectl / oc)
ECS_KUBECTL_PATH / ECS_KUBECONFIG / ECS_K8S_TIMEOUT_SECONDS
ECS_OC_PATH / ECS_OPENSHIFT_KUBECONFIG / ECS_OPENSHIFT_TIMEOUT_SECONDS
```

### Enterprise integrations
```
ECS_SERVICENOW_BASE_URL / ECS_SERVICENOW_CLIENT_ID / ECS_SERVICENOW_CLIENT_SECRET / ECS_SERVICENOW_TIMEOUT_SECONDS
ECS_ARCHER_BASE_URL / ECS_ARCHER_API_TOKEN / ECS_ARCHER_TIMEOUT_SECONDS
```

Use **read-only** DB/OS users. Passwords/tokens are read from the environment and
are never logged (diagnostics show SET/MISSING only).

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

### Technology Docker demo support matrix

| Technology | Local Docker Demo | Notes |
|------------|-------------------|-------|
| PostgreSQL | Yes | `postgres-demo` (port 5432) |
| YugabyteDB | Yes | `yugabyte` (`db-targets`, port 5433) |
| Aurora MySQL | Yes, via MySQL 8 | `mysql-demo` (`db-targets`, port 3306) |
| NGINX | Yes | `nginx-demo` (`nginx-demo` / `infra-demo`) |
| Linux | Yes, via `ubuntu-demo` | `demo-connectors` profile |
| Red Hat Enterprise Linux 8.x | Yes, via UBI8 demo container | `rhel8-demo` (`rhel-demo` / `infra-demo`) |
| Red Hat Enterprise Linux 9.x | Yes, via UBI9 demo container | `rhel9-demo` (`rhel-demo` / `infra-demo`) |
| Oracle | Optional heavy demo, 16/20 GB recommended | `oracle-demo` (`oracle-demo` profile only) |
| SQL Server | Optional heavy demo, 16/20 GB; Linux/amd64 image + EULA | `sqlserver-demo` (`sqlserver-demo` profile only) |
| MongoDB | Yes | `mongodb-demo` (`mongodb-demo` / `db-demo-extended`) |
| Redis | Yes (reuses existing `redis` service) | `redis` (predefined checks only) |
| Apache HTTPD | Yes | `apache-demo` (`apache-demo` / `infra-demo-extended`) |
| Tomcat | Yes | `tomcat-demo` (`tomcat-demo` / `infra-demo-extended`) |
| Kubernetes | Documentation-only local validation | needs a real cluster + `kubectl`; no heavy local cluster by default |
| OpenShift | Documentation-only local validation | needs a real cluster + `oc`; no heavy local cluster by default |
| Windows | **No on macOS/Linux Docker; remote/enterprise only** | see below |
| SonarQube | Yes | `sonarqube-demo` (`demo-connectors`) |
| GitLeaks | CLI/container (existing impl) | scans a local path |
| Trivy | CLI/container (existing impl) | image scan |

### Start / stop commands

```bash
# Lightweight infrastructure demo (NGINX + RHEL 8/9 — safe on 8 GB):
docker compose --profile nginx-demo --profile rhel-demo up -d \
    nginx-demo rhel8-demo rhel9-demo
# (equivalently: docker compose --profile infra-demo up -d nginx-demo rhel8-demo rhel9-demo)

# Extended middleware demo (Apache + Tomcat — safe on 8 GB):
docker compose --profile infra-demo-extended up -d apache-demo tomcat-demo

# Extended database demo (MongoDB — lightweight):
docker compose --profile db-demo-extended up -d mongodb-demo

# Oracle demo — HEAVY, 16/20 GB only (NOT part of infra-demo / default):
docker compose --profile oracle-demo up -d oracle-demo

# SQL Server demo — HEAVY/optional, 16/20 GB (Linux/amd64, Microsoft EULA):
docker compose --profile sqlserver-demo up -d sqlserver-demo

# All predefined local demo EXCLUDING Oracle & SQL Server:
docker compose --profile db-targets --profile nginx-demo --profile rhel-demo \
    --profile infra-demo-extended --profile db-demo-extended up -d \
    postgres-demo yugabyte mysql-demo nginx-demo rhel8-demo rhel9-demo \
    apache-demo tomcat-demo mongodb-demo

# Verify the extended targets (never prints secrets):
python scripts/check_predefined_extended_environment.py

# Stop:
docker compose --profile infra-demo-extended --profile db-demo-extended down
docker compose --profile oracle-demo --profile sqlserver-demo down
```

Then verify the environment (never prints passwords):
```bash
python scripts/check_predefined_technology_environment.py           # infra targets
python scripts/check_predefined_technology_environment.py --expect-oracle
python scripts/check_predefined_db_environment.py                    # database targets
```

### Container routing (RHEL / NGINX)

Shell technologies reuse the one `LinuxConnector` (docker exec). Container
resolution:

- **NGINX** → `ECS_NGINX_CONTAINER` (default `nginx-demo`) → fallback `ECS_LINUX_CONTAINER`.
- **Linux** → `ECS_LINUX_CONTAINER` (default `ubuntu-demo`).
- **RHEL 8.x** → `ECS_RHEL8_CONTAINER` (default `rhel8-demo`) → fallback `ECS_LINUX_CONTAINER`.
- **RHEL 9.x** → `ECS_RHEL9_CONTAINER` (default `rhel9-demo`) → fallback `ECS_LINUX_CONTAINER`.

> Minimal UBI RHEL containers may lack `systemd` / `auditd` / `firewalld` /
> `update-crypto-policies`. Every RHEL/Linux/NGINX check ends with `|| true`, so a
> missing tool yields empty/"not available" output rather than failing the run.

### Oracle demo (heavy — 16/20 GB machines only)

```bash
docker compose --profile oracle-demo up -d oracle-demo   # gvenzl/oracle-free:23-slim
```
Defaults: host `127.0.0.1`, port `1521`, service `FREEPDB1`, user `ecs_user`,
password `ecs_password` (local demo only — never reuse). Oracle is **not** started
by default and is **not** in `infra-demo`. If the image is unavailable in your
environment, point `ECS_ORACLE_*` at an external Oracle endpoint instead.

### Windows (not supported by local macOS/Linux Docker)

Windows containers cannot run under standard Docker Desktop on macOS/Linux in the
current Linux-container mode, so ECS deliberately ships **no Windows container**.
Windows predefined controls (technology label `Windows`) therefore show
**Connector Missing** locally, which is expected. Running them requires:

- a **Windows host** (or Windows-container mode), or an **enterprise remote
  connector** (e.g. PowerShell remoting / WinRM);
- appropriate **firewall / network** access to the target;
- credentials handled securely (never committed).

This is an enterprise/remote-only capability and is out of scope for the local
Docker demo.

### SQL Server (optional/heavy)

`sqlserver-demo` (`mcr.microsoft.com/mssql/server:2022-latest`) is under the
`sqlserver-demo` profile **only** — never default, never in an umbrella profile.
It needs ~2 GB+ RAM, is a Linux/amd64 image (emulated on Apple Silicon), and is
subject to the Microsoft EULA. The connector needs `pyodbc` + a Microsoft ODBC
driver (install on demand: `pip install pyodbc`; not in `requirements.txt`). Use
a read-only account; firewall TCP 1433. Or point `ECS_SQLSERVER_*` at an external
SQL Server.

### Kubernetes / OpenShift limitations

There is **no heavy local cluster** started by default (no kind/minikube in
compose). Local validation is **documentation-only**: install `kubectl` / `oc`,
point `ECS_KUBECONFIG` / `ECS_OPENSHIFT_KUBECONFIG` at a reachable cluster, and
run the `K8X-*` / `OCX-*` controls. Without a configured cluster the connectors
return a clean **"not configured"** or **"cluster unavailable"** result (never a
crash). Optional lightweight local clusters may be added later as clearly-isolated
profiles.

### ServiceNow CMDB & Archer integration skeletons

`modules/operations/integrations/servicenow_cmdb.py` and `.../archer.py` are
**skeletons** — config-driven clients with an injectable HTTP transport:
- ServiceNow: `ServiceNowCmdbClient.fetch_configuration_items()` / `fetch_assets()`
  + `map_ci_to_asset()`.
- Archer: `ArcherClient.fetch_controls()` / `fetch_frameworks()` +
  `map_archer_control()` / `map_archer_framework()`.
No real call is made in tests (a mock transport is injected). Credentials come
from env only (`ECS_SERVICENOW_*`, `ECS_ARCHER_*`) and are never logged;
`config_status()` reports presence as SET/MISSING for diagnostics. Production
wiring supplies a real HTTP transport (e.g. httpx/requests).

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
   (`PGX-`, `YBX-`, `MYX-`, `ORX-`, `MSX-`, `MGX-`).
2. Add the **exact normalized SQL** to the matching allow-list in
   `predefined_queries_engine.py` — **only** for the hardcoded allow-lists:
   `ALLOWED_POSTGRESQL_QUERIES` / `ALLOWED_YUGABYTE_QUERIES` /
   `ALLOWED_MYSQL_QUERIES` / `ALLOWED_ORACLE_QUERIES`. Normalization = lowercase,
   collapsed whitespace, trailing `;`.
   - **SQL Server (`MSX-*`) and MongoDB (`MGX-*`) need no engine edit** — their
     allow-lists (`ALLOWED_SQLSERVER_QUERIES` / `ALLOWED_MONGODB_COMMANDS`) are
     **derived from the catalog** automatically. Adding a catalog entry is enough.
3. (Optional) Add a test asserting it's covered by the allow-list
   (`tests/test_predefined_db_connectors.py::test_every_supplementary_query_in_allowlist`
   covers PG/YB/MY; extend the per-technology counts there when you add entries).
4. Regenerate the inventory doc: `python scripts/run_predefined_query_tests.py inventory`.
5. `python -m compileall modules` and `pytest tests/test_predefined_db_connectors.py`.

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
- `docs/03-development/operations/ECS_PREDEFINED_QUERY_EXECUTION_GUIDE.md`
- `docs/03-development/operations/ECS_CONNECTOR_INVENTORY.md`
- `docs/03-development/production/ECS_REMOTE_CONNECTOR_EXPANSION_PLAN.md`
