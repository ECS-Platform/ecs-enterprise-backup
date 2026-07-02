# ECS Target Mapping Audit

**Status:** Reviewed + fixes implemented (not committed)
**Source of truth:** `config/environments/_base.yaml` (+ `local.yaml` overlay),
resolved through `config/environment_loader.py` → `get_predefined_query_targets()`.
**Last updated:** 2026-06-21

---

## 1. How targets are defined

`predefined_query_targets` has **two distinct kinds** of entries:

1. **Server lists** (`os_servers`, `db_servers`, `middleware_servers`, `appsec_targets`) —
   per-environment host/IP fleets used for **remote** SSH/DB execution in DEV/SIT/UAT/PROD.
   These are intentionally **empty in `local`**.
2. **Live demo-connector blocks** (`postgresql`, `linux`, `sonarqube`, `trivy`, `gitleaks`)
   — the deterministic local demo targets. These are inherited from `_base.yaml` and are
   what the local demo actually executes against.

> The startup warnings *"predefined_query_targets.os_servers is empty"* /
> *"db_servers is empty"* refer to kind (1) and are **expected** for `local`. They do **not**
> indicate the demo connectors are unconfigured — kind (2) is fully populated.

---

## 2. Target mapping audit

| Target key | Kind | Configured value (local, resolved) | Status | Notes |
|------------|------|--------------------------------------|--------|-------|
| `postgresql.host` | demo | `postgres-demo` (`${ECS_PG_HOST:-localhost}`) | ✅ Configured | In Docker → `postgres-demo`; on host → `localhost`. Both reachable. |
| `postgresql.port` | demo | `5432` | ✅ Configured | Published on host as `5432`. |
| `postgresql.database/user` | demo | `ecs_demo` / `ecs_user` | ✅ Configured | Matches `postgres-demo` container env. |
| `linux.container` | demo | `ubuntu-demo` (`${ECS_LINUX_CONTAINER:-ubuntu-demo}`) | ✅ Configured (**was Incorrect at runtime**) | Value correct; the **container was not named** `ubuntu-demo` → fixed via `container_name` (§4). |
| `sonarqube.base_url` | demo | `http://sonarqube-demo:9000` (`${ECS_SONAR_URL:-…}`) | ✅ Configured | Reachable in Docker; on host requires `ECS_SONAR_URL=http://localhost:9000`. |
| `sonarqube.user/password` | demo | `admin` / `ECS_SONAR_PASSWORD` (`a123` in compose) | ✅ Configured | Verified auth `admin:a123` against live SonarQube. |
| `trivy.image` | demo | `alpine:3.19` | ✅ Configured | On-demand scan image. |
| `gitleaks.scan_path` | demo | `/app/demo-data/gitleaks-sample` (`ECS_GITLEAKS_SCAN_PATH`) | ✅ Configured | Mounted read-only into the ECS container. |
| `os_servers` | list | `[]` | ✅ Intentionally empty (local) | Populated in DEV/SIT/UAT/PROD for remote SSH baselining. |
| `db_servers` | list | `[]` | ✅ Intentionally empty (local) | Populated in higher envs for remote DB baselining. |
| `middleware_servers` | list | `[]` | ✅ Intentionally empty (local) | NGINX/Tomcat fleets (higher envs). |
| `appsec_targets` | list | `[]` | ✅ Intentionally empty (local) | AppSec scan targets (higher envs). |
| `databases.oracle/mysql/sqlserver` | infra | empty host | ⚪ Unused (local) | Generic connectors not yet runnable. |

### Findings classification

- **Configured & correct:** all demo-connector blocks (`postgresql`, `sonarqube`, `trivy`,
  `gitleaks`) and the (intentionally empty) server lists.
- **Incorrect (runtime):** `linux.container` value was correct (`ubuntu-demo`) but the
  **container name** did not match → execution failed. Fixed by pinning `container_name`.
- **Missing:** none for local demo. Higher-environment server lists are empty by design and
  must be populated per environment before remote execution.
- **Unused:** `databases.oracle/mysql/sqlserver`, `middleware_servers`, `appsec_targets` in
  local (generic connectors are interface-only).

---

## 3. Connector ↔ container cross-check (live)

| Compose service | Running container (before) | DNS / exec name expected by ECS | Match before | After fix |
|-----------------|----------------------------|----------------------------------|--------------|-----------|
| `postgres-demo` | `ecs-postgres-demo-1` | `postgres-demo` (DNS, TCP) | DNS ✅ | `container_name: postgres-demo` ✅ |
| `sonarqube-demo` | `ecs-sonarqube-demo-1` | `sonarqube-demo` (DNS, HTTP) | DNS ✅ | `container_name: sonarqube-demo` ✅ |
| `ubuntu-demo` | `ecs-ubuntu-demo-1` | `ubuntu-demo` (**docker exec name**) | ❌ **mismatch** | `container_name: ubuntu-demo` ✅ |

DNS-based connectors (PostgreSQL, SonarQube) worked before the fix because compose adds a
service-name network alias. The Linux connector uses **`docker exec <name>`**, which requires
the **container name** (not the DNS alias) — hence the rename was required.

---

## 4. Fixes implemented

1. `docker-compose.yml` — added `container_name: postgres-demo`, `container_name: ubuntu-demo`,
   `container_name: sonarqube-demo` so connector references resolve deterministically.
2. Technology-mapping fix for `OS-001` documented in `ECS_CONNECTOR_INVENTORY.md` §4 (the
   query was Linux but mis-detected as Unknown; without correct technology the resolver never
   selected the Linux connector or its target).

No server-list values were invented. Empty `local` lists are left empty (correct).

---

## 5. Higher-environment guidance (no change made)

To enable remote execution in DEV/SIT/UAT/PROD, populate the relevant lists in
`config/environments/<env>.yaml`, e.g.:

```yaml
predefined_query_targets:
  os_servers:  ["10.20.1.11", "10.20.1.12"]    # SSH targets
  db_servers:  ["10.20.2.21"]                   # remote DB hosts
```

These feed `build_connector_config()` (`query_connectors.py`), which creates `SSHConnector` /
`DatabaseConnector` entries — note those generic connectors are currently interface-only and
require activation (tracked in `docs/PHASE1/ECS_CONNECTOR_ACTIVATION_PLAN.md`).
