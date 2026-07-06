# ECS Predefined-Query Connectors — UAT Integration Guide

**Audience:** Bank developers configuring ECS predefined-query connectors and the
enterprise integration skeletons for **UAT** (and understanding the path to
Production).
**Golden rules:** never commit `.env.uat`; never put real IPs/FQDNs or secrets in
any committed file (including this guide); use **read-only service accounts**.

> Cross-refs: [PREDEFINED_DATABASE_QUERY_MODULE.md](PREDEFINED_DATABASE_QUERY_MODULE.md)
> (module internals + full env-var reference), [README_DEVELOPER.md](README_DEVELOPER.md).

---

## 1. Purpose

ECS predefined queries run read-only baselining checks against enterprise systems
(databases, middleware, OS, container platforms) and capture the output as
evidence. Out of the box the connectors point at **local Docker demo containers**.
This guide explains how to repoint every connector at **real bank UAT endpoints**
using environment variables — with no code changes, no secrets in git, and no
hard-coded IPs.

---

## 2. Local Docker vs Bank UAT vs Production

| | Local Docker demo | Bank UAT | Production |
|---|---|---|---|
| Purpose | Developer laptop demo/validation | Acceptance testing against the UAT landscape | Live evidence collection |
| Targets | `docker compose` demo containers | Real **UAT** IP/FQDN endpoints | Real **PROD** endpoints |
| Selected by | Default container names in `_base.yaml` | `ECS_ENV=uat` + `.env.uat` env vars | `ECS_ENV=prod` + a prod secret store |
| Credentials | Throwaway demo defaults | Bank **read-only service accounts** | Bank service accounts via a vault/secret manager |
| Secrets location | `.env` (local) | `.env.uat` (local, git-ignored) | Deployment secret store (never files in git) |
| Network | localhost | VPN / jump host into UAT segment | Controlled prod network |

- **Docker is only for the local demo** — do not start any demo container for UAT.
- **UAT** must use real IP/FQDN endpoints, configured via environment variables.
- **Production** uses the same variables but sourced from a secret manager (Vault,
  cloud secrets, K8s secrets) — never from committed files. This guide focuses on
  UAT; the mechanism is identical for prod with a different secret source.

---

## 3. Configuration hierarchy (precedence)

ECS resolves each setting per field, first non-empty wins:

```
1. Environment variable (ECS_*)          <- highest precedence (from .env / .env.uat / shell / vault)
2. config/environments/<ECS_ENV>.yaml    <- e.g. uat.yaml (non-secret UAT defaults)
3. config/environments/_base.yaml        <- generic defaults (Docker demo names)
4. Built-in code default                 <- lowest precedence
```

| File | Role | Secrets? | Committed? |
|------|------|----------|------------|
| `config/environments/_base.yaml` | Generic defaults (Docker demo hostnames) | No | Yes |
| `config/environments/uat.yaml` | Non-secret UAT defaults (`${VAR:-placeholder}`) | No | Yes |
| `.env` | Local demo overrides | Demo only | **No** (git-ignored) |
| `.env.uat` | Real UAT endpoints + credentials for your machine | **Yes** | **NEVER** (git-ignored) |
| Environment variables | Final override (incl. CI/vault-injected) | Yes | n/a |

Select the environment with `ECS_ENV=uat`. The YAML `${ENV_VAR:-default}`
placeholders already honour the env vars, so setting `ECS_*` in `.env.uat` is all
you normally need.

Confirm `.env.uat` is ignored before you begin:
```bash
git check-ignore .env.uat   # must print ".env.uat"
```

---

## 4. Technology-specific configuration

These are the variables ECS actually reads. Variables marked _(roadmap)_ are
reserved for a future remote/SSH or context-selection mode and are **not consumed
yet** — set them for forward-compatibility only.

| Technology | Connector | Variables |
|------------|-----------|-----------|
| **Oracle** (1521) | oracle_connector (python-oracledb) | `ECS_ORACLE_HOST` · `ECS_ORACLE_PORT` · `ECS_ORACLE_SERVICE_NAME` · `ECS_ORACLE_USER` · `ECS_ORACLE_PASSWORD` · `ECS_ORACLE_TIMEOUT_SECONDS` |
| **SQL Server** (1433) | sqlserver_connector (pyodbc) | `ECS_SQLSERVER_HOST` · `ECS_SQLSERVER_PORT` · `ECS_SQLSERVER_DATABASE` · `ECS_SQLSERVER_USERNAME` · `ECS_SQLSERVER_PASSWORD` · `ECS_SQLSERVER_TIMEOUT_SECONDS` |
| **MongoDB** (27017) | mongodb_connector (pymongo) | `ECS_MONGODB_URI` · `ECS_MONGODB_DATABASE` · `ECS_MONGODB_TIMEOUT_SECONDS` |
| **Redis** (6379) | redis_connector (redis-cli) | `ECS_REDIS_HOST` · `ECS_REDIS_PORT` · `ECS_REDIS_PASSWORD` (optional) · `ECS_REDIS_TIMEOUT_SECONDS` |
| **Linux** | Linux connector (docker exec today) | `ECS_LINUX_CONTAINER` (demo); _(roadmap)_ `ECS_LINUX_HOST` · `ECS_LINUX_USERNAME` · `ECS_LINUX_AUTH_MODE` · `ECS_SSH_KEY_PATH` |
| **RHEL 8.x / 9.x** | Linux connector | `ECS_RHEL8_CONTAINER` · `ECS_RHEL9_CONTAINER` (demo); fall back to `ECS_LINUX_CONTAINER`; roadmap SSH as Linux |
| **NGINX** | Linux connector | `ECS_NGINX_CONTAINER` (demo); _(roadmap)_ `ECS_NGINX_HOST` · `ECS_NGINX_SSH_USER` · `ECS_NGINX_SSH_KEY_PATH` |
| **Apache HTTPD** | Linux connector | `ECS_APACHE_CONTAINER` (demo); _(roadmap)_ `ECS_APACHE_HOST` |
| **Tomcat** | Linux connector | `ECS_TOMCAT_CONTAINER` (demo); _(roadmap)_ `ECS_TOMCAT_HOST` |
| **Kubernetes** | kubernetes_connector (kubectl) | `ECS_KUBECTL_PATH` · `ECS_KUBECONFIG` · `ECS_K8S_TIMEOUT_SECONDS`; _(roadmap)_ `ECS_K8S_CONTEXT` |
| **OpenShift** | openshift_connector (oc) | `ECS_OC_PATH` · `ECS_OPENSHIFT_KUBECONFIG` · `ECS_OPENSHIFT_TIMEOUT_SECONDS`; _(roadmap)_ `ECS_OPENSHIFT_CONTEXT` |
| **ServiceNow CMDB** | integrations/servicenow_cmdb | `ECS_SERVICENOW_BASE_URL` · `ECS_SERVICENOW_CLIENT_ID` · `ECS_SERVICENOW_CLIENT_SECRET` · `ECS_SERVICENOW_TIMEOUT_SECONDS` |
| **Archer** | integrations/archer | `ECS_ARCHER_BASE_URL` · `ECS_ARCHER_API_TOKEN` · `ECS_ARCHER_TIMEOUT_SECONDS` |

Notes:
- The Oracle module variable is `ECS_ORACLE_USER` (not `..._USERNAME`); SQL Server
  uses `ECS_SQLSERVER_USERNAME`.
- **Linux/RHEL/NGINX/Apache/Tomcat** run via `docker exec` today. For **remote UAT
  hosts**, run the checks from a jump host inside the UAT segment whose local shell
  reaches the targets; native SSH mode (the `ECS_*_HOST` vars) is on the roadmap.
- **Kubernetes/OpenShift** select the UAT cluster via the kubeconfig you point at
  (`ECS_KUBECONFIG` / `ECS_OPENSHIFT_KUBECONFIG`); set its `current-context` or run
  `kubectl config use-context <ctx>` (dedicated `*_CONTEXT` vars are roadmap).
- **Integration config** may live under the `connectors:` **or** the older
  `integrations:` YAML section, keyed `servicenow_cmdb`/`archer` (or legacy
  `servicenow`) — all are read (see §10).

---

## 5. Developer onboarding (UAT)

```bash
# 1. Clone + branch (see README_DEVELOPER.md), then venv:
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt
# SQL Server only: pip install pyodbc  (+ a Microsoft ODBC driver)

# 2. Create your UAT env file (git-ignored) from the template:
cp .env.example .env.uat
#    edit .env.uat -> real UAT hosts/ports + read-only service accounts (see §14)

# 3. Select the UAT environment + load your vars:
export ECS_ENV=uat
set -a; source .env.uat; set +a          # 'set -a' handles values with spaces

# 4. Confirm connectivity/config (never prints secrets — see §10):
python3 scripts/check_predefined_technology_environment.py --no-docker-check
python3 scripts/check_predefined_extended_environment.py  --no-docker-check
```

Request from your platform/security team **before** onboarding: VPN access, a
jump-host account, read-only DB/OS service accounts, and firewall rules for your
source subnet (§6–§9).

---

## 6. VPN requirements

- Connect to the **bank VPN** (or work from an approved jump host) before running
  any UAT check — UAT endpoints are not reachable from the open internet.
- Ensure **split-tunnel/routing** actually routes the UAT subnets over the VPN.
- Ensure **DNS resolution** of UAT FQDNs works over the VPN (or use IPs / a
  jump host that can resolve them).

---

## 7. Firewall considerations

The path from your **source** (laptop over VPN, jump host, or ECS backend) to each
target must allow **outbound** access on the listener port:

| Target | Port (TCP) |
|--------|------------|
| Oracle | 1521 |
| SQL Server | 1433 |
| MongoDB | 27017 |
| Redis | 6379 |
| PostgreSQL / Yugabyte | 5432 / 5433 |
| Remote Linux/RHEL/NGINX/Apache/Tomcat (roadmap SSH) | 22 |
| Kubernetes / OpenShift API | as configured (usually 6443) |
| ServiceNow / Archer | 443 (HTTPS) |

Ask the network team to allow your **source subnet** to the target on these ports
(DB/host security groups + any perimeter firewall).

---

## 8. Service accounts

- Use dedicated **service accounts**, never personal logins or DBA/admin accounts.
- One purpose-built account per technology (e.g. `ecs_ro` for DBs).
- Credentials come from the environment (`.env.uat` / vault), referenced in YAML
  only by `*_env` variable name — never the value.
- Rotate per bank policy; update `.env.uat` (never a committed file).

---

## 9. Read-only accounts

- Every predefined check is **read-only** — grant the service account the minimum
  read privileges only (e.g. `SELECT` on catalog/`sys.*`/`mysql.user`,
  `CONFIG GET`/`INFO` for Redis, `get`/`version` for kubectl/oc).
- Do **not** grant write/DDL/admin. If a check needs a system table the account
  can't read (e.g. `mysql.user`), grant that read explicitly or skip that control.

---

## 10. How diagnostics work

Two safe, read-only diagnostics report config + reachability and **never print
secrets** (passwords, Mongo URI, ServiceNow/Archer tokens show as `SET`/`MISSING`):

```bash
# Base targets (PostgreSQL/Yugabyte/MySQL + NGINX/Linux/RHEL/Oracle):
python3 scripts/check_predefined_technology_environment.py [--json] [--no-docker-check] [--expect-oracle]
python3 scripts/check_predefined_db_environment.py         [--json] [--no-docker-check] [--skip-*]

# Extended targets (Redis/Apache/Tomcat/MongoDB/SQL Server + kubectl/oc + ServiceNow/Archer):
python3 scripts/check_predefined_extended_environment.py   [--json] [--no-docker-check] [--strict]
```

- `--no-docker-check`: skip container checks (use for UAT / no-Docker mode); the
  report still shows each target's resolved host/port/user and secret SET/MISSING.
- `--json`: machine-readable output. `--strict`: fail if an expected demo
  container is not running.
- Each connector fails **gracefully** (structured error, no stack trace) so the
  diagnostic pinpoints the failing layer (config → DNS → TCP → auth → query).

Integration configuration is resolved from either the `connectors:` or the older
`integrations:` section of the active environment YAML, keyed `servicenow_cmdb` /
`archer` (or the legacy `servicenow`) — so old and new layouts both work.

---

## 11. Common troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Connection timeout | Target unreachable / firewall / VPN down | Confirm VPN + routing; open the port; `nc -vz <host> <port>` from a jump host. |
| DNS failure | UAT FQDN not resolvable | Use the IP, add DNS/`/etc/hosts`, or use a jump host that resolves it. |
| Firewall blocked | Source subnet not allowed | Request a security-group/firewall rule for your subnet on the port. |
| Wrong port | Non-default listener | Set the correct `ECS_*_PORT`. |
| Wrong service name (Oracle) | `ORA-12514` | Fix `ECS_ORACLE_SERVICE_NAME` (service/PDB); confirm with the DBA. |
| Bad credentials | Wrong/locked account | Use the correct read-only service account; fix `.env.uat` (never docs). |
| Missing ODBC driver (SQL Server) | `pyodbc`/driver absent | `pip install pyodbc` + Microsoft ODBC Driver 17/18. |
| kubectl context missing | No/incorrect kubeconfig | Set `ECS_KUBECONFIG`; `kubectl config use-context <ctx>`. |
| oc context missing | Not logged in | Set `ECS_OPENSHIFT_KUBECONFIG`; `oc login <uat-api>`. |
| ServiceNow/Archer token failure | Missing/expired/invalid creds | Refresh the ServiceNow client id/secret or Archer token in `.env.uat`; `config_status()` shows SET/MISSING. |

---

## 12. Security guidelines

- Use **read-only service accounts**; least privilege; no DBA/admin.
- Access UAT via **VPN / jump host / firewall** only.
- Secrets live in `.env.uat` (git-ignored) or a vault — **never** in YAML, code,
  docs, logs, tickets, or screenshots.
- Diagnostics and connectors **never print** passwords/tokens (SET/MISSING only).
- Prefer TLS where the target supports it (`ECS_*_SSLMODE` / `ECS_MYSQL_SSL` /
  Mongo `tls=` in the URI) per bank policy.
- Rotate credentials on the bank's schedule.

---

## 13. What must NEVER be committed

- `.env.uat` (or any `.env.*` except `.env.example`).
- Real IPs, FQDNs, hostnames, ports for production/UAT bank systems.
- Any password, API token, client secret, connection string with credentials,
  kubeconfig, or SSH private key.
- Screenshots/logs containing the above.

`.gitignore` already blocks `.env` and `.env.*` (only `.env.example` is tracked).
Double-check with `git status` before every commit.

---

## 14. Example `.env.uat` template (placeholders only)

Copy into `.env.uat` and replace every `<...>`. **No real values belong in any
committed file.**

```bash
ECS_ENV=uat

# ---------------- Oracle ----------------
ECS_ORACLE_HOST=<uat-oracle-host-or-ip>
ECS_ORACLE_PORT=1521
ECS_ORACLE_SERVICE_NAME=<uat-service-name>
ECS_ORACLE_USER=<service-account>          # module reads ECS_ORACLE_USER
ECS_ORACLE_PASSWORD=<do-not-commit>
ECS_ORACLE_TIMEOUT_SECONDS=30

# ---------------- SQL Server ----------------
ECS_SQLSERVER_HOST=<uat-sqlserver-host-or-ip>
ECS_SQLSERVER_PORT=1433
ECS_SQLSERVER_DATABASE=<uat-database>
ECS_SQLSERVER_USERNAME=<service-account>
ECS_SQLSERVER_PASSWORD=<do-not-commit>
ECS_SQLSERVER_TIMEOUT_SECONDS=30

# ---------------- MongoDB ----------------
ECS_MONGODB_URI=mongodb://<service-account>:<do-not-commit>@<uat-mongo-host>:27017/?authSource=admin
ECS_MONGODB_DATABASE=admin
ECS_MONGODB_TIMEOUT_SECONDS=30

# ---------------- Redis ----------------
ECS_REDIS_HOST=<uat-redis-host-or-ip>
ECS_REDIS_PORT=6379
ECS_REDIS_PASSWORD=<do-not-commit-or-blank>
ECS_REDIS_TIMEOUT_SECONDS=30

# ---------------- Linux / RHEL / NGINX / Apache / Tomcat (roadmap SSH mode) ----
ECS_LINUX_HOST=<uat-linux-host-or-ip>
ECS_LINUX_USERNAME=<ssh-service-account>
ECS_LINUX_AUTH_MODE=key                     # key | password
ECS_SSH_KEY_PATH=<path-to-private-key>
ECS_NGINX_HOST=<uat-nginx-host-or-ip>
ECS_APACHE_HOST=<uat-apache-host-or-ip>
ECS_TOMCAT_HOST=<uat-tomcat-host-or-ip>

# ---------------- Kubernetes ----------------
ECS_KUBECTL_PATH=kubectl
ECS_KUBECONFIG=<path-to-uat-kubeconfig>
ECS_K8S_CONTEXT=<uat-context-name>          # roadmap; else set current-context in kubeconfig
ECS_K8S_TIMEOUT_SECONDS=30

# ---------------- OpenShift ----------------
ECS_OC_PATH=oc
ECS_OPENSHIFT_KUBECONFIG=<path-to-uat-kubeconfig>
ECS_OPENSHIFT_CONTEXT=<uat-context-name>    # roadmap; else set current-context in kubeconfig
ECS_OPENSHIFT_TIMEOUT_SECONDS=30

# ---------------- ServiceNow CMDB ----------------
ECS_SERVICENOW_BASE_URL=https://<uat-instance>.service-now.com
ECS_SERVICENOW_CLIENT_ID=<client-id>
ECS_SERVICENOW_CLIENT_SECRET=<do-not-commit>
ECS_SERVICENOW_TIMEOUT_SECONDS=30

# ---------------- Archer ----------------
ECS_ARCHER_BASE_URL=https://<uat-archer-host>
ECS_ARCHER_API_TOKEN=<do-not-commit>
ECS_ARCHER_TIMEOUT_SECONDS=30
```

---

## 15. How to switch between Docker demo and real UAT

**No code change is needed — it's environment-driven.**

**Docker demo (default):**
```bash
unset ECS_ENV                 # or ECS_ENV=local
docker compose --profile db-targets --profile infra-demo up -d   # start demo targets
# connectors resolve to the demo container hostnames from _base.yaml
```

**Real UAT:**
```bash
export ECS_ENV=uat
set -a; source .env.uat; set +a
# do NOT start any demo container; connectors resolve to your UAT endpoints
python3 scripts/check_predefined_extended_environment.py --no-docker-check
```

**Switch back to demo:** stop loading `.env.uat` (open a fresh shell), `unset
ECS_ENV`, and start the demo containers again. Because UAT values only exist in
your shell/`.env.uat`, nothing about the switch touches git.

---

## 16. Enterprise integration adapters (UAT)

Beyond the predefined-query connectors, ECS ships 9 config-driven integration
adapters (ServiceNow CMDB, Archer, SharePoint/Graph, Jira, Confluence, SonarQube,
Checkmarx, Prisma Cloud, Tripwire). For UAT, set their `ECS_*` variables in
`.env.uat` (never committed) — see
[INTEGRATION_ADAPTERS_GUIDE.md](INTEGRATION_ADAPTERS_GUIDE.md) for the full variable
list and behaviour. Non-secret defaults live in the `connectors:` section of
`uat.yaml`; all secrets resolve from the `*_env` environment variables.

Check adapter configuration/health without any live call:

```bash
# All adapters (masked config; secrets shown as SET/MISSING only):
curl -s "http://127.0.0.1:8000/api/audit/integrations?role=owner&user=AppOwner"
curl -s "http://127.0.0.1:8000/api/audit/integrations/health?role=owner&user=AppOwner"
```

`not_configured` is the expected state until you populate the adapter's env vars.

---

## Validation (this guide's config)

```bash
PYTHONPATH=. pytest tests/test_predefined_extended_connectors.py
PYTHONPATH=. pytest tests/test_enterprise_integrations_skeleton.py
PYTHONPATH=. pytest tests/test_integration_adapters_mocked.py tests/test_uat_config_placeholders.py
python3 -m compileall modules/operations scripts tests
docker compose config      # validates compose (demo profiles are opt-in)
```
