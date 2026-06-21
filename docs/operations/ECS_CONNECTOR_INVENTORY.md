# ECS Connector Inventory

**Status:** Reviewed + fixes implemented (not committed)
**Scope:** Predefined-query connector execution readiness. No UI / KPI / navigation changes.
**Verification:** All facts below were probed against the **running** demo stack
(`ecs-ecs-1` + demo-connector containers) on 2026-06-21.
**Last updated:** 2026-06-21

---

## 1. Summary verdict

The reported failures were **not** caused by the demo containers being down — they are up
and reachable. Root causes:

| Symptom (reported) | Actual root cause | Layer |
|--------------------|-------------------|-------|
| PostgreSQL "unavailable" | **No defect inside Docker** — `postgres-demo:5432` is reachable and `DB-001/2/3` execute successfully. (On the host/venv it works against `localhost:5432`.) | — |
| SonarQube "unreachable" | **No defect inside Docker** — `sonarqube-demo:9000` returns `status: UP` and `APP-001` executes successfully. | — |
| Ubuntu/Linux "unreachable" | **Two real defects:** (1) `OS-001` query `yum check-update` was mis-classified as *Unknown*; (2) the Linux connector runs `docker exec ubuntu-demo`, but the container was auto-named `ecs-ubuntu-demo-1`, and the ECS image (stale) had no `docker` CLI. | Technology mapping + demo-container reference + image |

`os_servers` / `db_servers` being empty in the startup log is **expected and correct** for
`local`: those lists are for remote SSH/DB fleets in higher environments. Local demo
execution uses the live demo-connector blocks (`postgresql` / `linux` / `sonarqube` /
`trivy` / `gitleaks`), not the server lists.

---

## 2. Connector inventory (per technology)

Legend — **Demo Ready** = executes successfully in the local docker-compose demo after the
fixes in §4. **Reachable** = the target endpoint responded during live probing.

| Technology | Connector class | Execution engine | Target source | Configured target | Reachable | Demo Ready |
|------------|-----------------|------------------|---------------|-------------------|-----------|------------|
| PostgreSQL | `PostgreSQLConnector` | `psycopg2` TCP (SQL allow-list) | `predefined_query_targets.postgresql` → `ECS_PG_*` | `postgres-demo:5432/ecs_demo` | ✅ (`PG OK`) | ✅ `DB-001/2/3` |
| Linux | `LinuxConnector` | `docker exec <container> sh -c` | `predefined_query_targets.linux` → `ECS_LINUX_CONTAINER` | `ubuntu-demo` | ✅ (after rename) | ✅ `OS-001/002` |
| SonarQube | `SonarQubeConnector` | REST (`/api/...`) over `urllib` | `predefined_query_targets.sonarqube` → `ECS_SONAR_*` | `http://sonarqube-demo:9000` | ✅ (`status: UP`, v9.9.8) | ✅ `APP-001/002`* |
| GitLeaks | `GitLeaksConnector` | subprocess / container scan | `predefined_query_targets.gitleaks.scan_path` | `/app/demo-data/gitleaks-sample` | ✅ (in-repo path) | ✅ `APP-002` |
| Trivy | `TrivyConnector` | container image scan | `predefined_query_targets.trivy.image` | `alpine:3.19` | n/a (on-demand) | ✅ (wired) |
| Oracle | `DatabaseConnector` (generic) | — | `databases.oracle` | none (local) | ❌ | ❌ interface-only (`NotImplementedError`) |
| Windows | `SSHConnector` (generic) | — | — | none | ❌ | ❌ interface-only |
| NGINX | `SSHConnector` (generic) | — | `middleware_servers` | none (local) | ❌ | ❌ interface-only |

\* `APP-002` in the catalog is **GitLeaks** (`gitleaks detect`); `APP-001` is SonarQube.
`SONAR_CONTROL_MODES` maps `APP-001 → projects`, `APP-002 → issues` for any SonarQube-typed
control, but the catalog wires `APP-002` to GitLeaks.

---

## 3. Resolver & technology-mapping chain

```
Run Query (control_id)
  → run_predefined_query()                        modules/operations/engines/predefined_queries_engine.py
      → is_live_execution_enabled(control)         (control_id ∈ LIVE_CONTROL_IDS  AND  assess_execution_capability.executable)
      → dispatch by control.technology:
          PostgreSQL → run_postgresql_query()  → PostgreSQLConnector(get_postgresql_config())
          Linux      → LinuxConnector(get_linux_config())   command = LINUX_CONTROL_COMMANDS[control_id] | query
          SonarQube  → SonarQubeConnector(get_sonarqube_config())  mode = SONAR_CONTROL_MODES[control_id] | query
          Trivy      → TrivyConnector(get_trivy_config())
          GitLeaks   → GitLeaksConnector(get_gitleaks_config())
```

- **Technology** is derived at load time by `detect_technology(query)` against
  `TECHNOLOGY_RULES` (ordered pattern list). This is the layer that mis-classified `OS-001`.
- **Target/host/port** is resolved per connector by `get_*_config()`, in the order:
  active-environment YAML (`config/environments/<ECS_ENV>.yaml` →
  `predefined_query_targets.<tech>`) → `ECS_*` env var → historical default.
- `connector_for_technology()` (`query_connectors.py`) returns the live connector for
  implemented technologies and `None` for generic/unimplemented ones (graceful "Connector
  Missing").

---

## 4. Fixes implemented (Phase 4 — mapping / demo-container only)

1. **Technology mapping** — `predefined_queries_engine.py`, `TECHNOLOGY_RULES["Linux"]`:
   added `systemctl`, `yum `, `apt-get`, `dpkg`, `rpm -`, `/etc/passwd`, `/etc/group`,
   `hostname`, `uptime`. `OS-001` (`yum check-update`) now classifies as **Linux** (was
   *Unknown → Unsupported Technology*). Side-effect (correct): `OS-004` (`cat /etc/passwd`)
   and `OS-005` (`systemctl list-units`) now classify as Linux/*Configuration Required*
   instead of *Unknown*. No other control reclassified (verified — `MW-003`, `ITPP-001/004`,
   `PCI-002` correctly remain Unknown).

2. **Demo-container reference** — `docker-compose.yml`: pinned
   `container_name: ubuntu-demo` (also `postgres-demo`, `sonarqube-demo`) so
   `docker exec ubuntu-demo` and the DNS names resolve regardless of the compose project
   prefix. Previously the container was `ecs-ubuntu-demo-1`, so `docker exec ubuntu-demo`
   failed with *"No such container"*.

3. **ECS image rebuild (operational, no code change needed)** — the Linux connector needs
   the `docker` CLI inside the ECS container. The `Dockerfile` **already** installs
   `docker.io`, but the running image (built `2026-06-11 12:18 UTC`) predates that line
   (committed `16:30 UTC` same day), so the live container reports `docker: not found`.
   Resolution: `docker compose build ecs && docker compose up -d ecs`.

---

## 5. Post-fix verification (live)

| Control | Technology | Capability | Live execution result |
|---------|------------|------------|------------------------|
| DB-001 | PostgreSQL | Ready | ✅ `ok=True` (executes `SHOW ssl;` against `postgres-demo`) |
| DB-002 / DB-003 | PostgreSQL | Ready | ✅ wired + allow-listed |
| APP-001 | SonarQube | Ready | ✅ `ok=True` (project count from `sonarqube-demo`) |
| APP-002 | GitLeaks | Ready | ✅ wired (in-repo scan path) |
| OS-001 | Linux *(fixed)* | Ready | ✅ `ok=True`, output `ubuntu-demo` (host run; in-container after image rebuild) |
| OS-002 | Linux | Ready | ✅ `ok=True`, output `…up 1:04, load average…` |

See `ECS_QUERY_EXECUTION_TRACE.md` for the per-control trace and `ECS_TARGET_MAPPING_AUDIT.md`
for the full target-list audit.
