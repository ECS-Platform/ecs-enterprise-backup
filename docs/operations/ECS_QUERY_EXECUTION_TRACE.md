# ECS Query Execution Trace

**Status:** Reviewed + fixes implemented (not committed)
**Method:** Each control was executed against the **live** demo stack
(`ecs-ecs-1` for in-container; host venv for the Linux end-to-end proof) on 2026-06-21.
**Controls traced:** `APP-001`, `OS-001`, `OS-002`, `DB-001`.
**Last updated:** 2026-06-21

---

## Common path

```
POST /mvp/predefined-queries/run  (routes_mvp.mvp_predefined_query_run)
  → run_predefined_query(control_id, user)            predefined_queries_engine.py
      1. get_control_by_id(control_id)
      2. is_live_execution_enabled(control)            → control_id ∈ LIVE_CONTROL_IDS AND assess_execution_capability().executable
      3. dispatch on control["technology"]             ← technology set at load by detect_technology(query)
      4. connector = <Tech>Connector(get_<tech>_config())
      5. connector.connect() → connector.execute(cmd) → complete_connector_execution()
```

Where the technology in step 3 is wrong, dispatch never reaches the right connector. Where
the connector's target name is wrong, `connect()`/`execute()` fails. Both failure modes were
present and are now fixed.

---

## DB-001 — PostgreSQL — ✅ works (no defect)

| Stage | Result |
|-------|--------|
| Query | `SHOW ssl;` |
| `detect_technology` | **PostgreSQL** (matches `show ssl`) |
| `LIVE_CONTROL_IDS` | ✅ `DB-001` present |
| `assess_execution_capability` | **Ready** (psycopg2 present, wired) |
| Resolver | `run_postgresql_query` → allow-list `show ssl;` ✅ |
| Config | host=`postgres-demo` port=`5432` db=`ecs_demo` |
| `connect()` | ✅ TCP connect to `postgres-demo:5432` (`PG OK`) |
| `execute()` | ✅ returns rows |
| **Verdict** | **Executes successfully.** No defect. (Host mode: `localhost:5432`, psycopg2 present in venv.) |

**Where it stops:** it does not stop — completes successfully.

---

## APP-001 — SonarQube — ✅ works (no defect)

| Stage | Result |
|-------|--------|
| Query | `curl http://sonarqube/api/issues/search` |
| `detect_technology` | **SonarQube** (matches `/api/issues/search`) |
| `LIVE_CONTROL_IDS` | ✅ `APP-001` present |
| `assess_execution_capability` | **Ready** |
| Resolver | `SonarQubeConnector`, mode = `SONAR_CONTROL_MODES["APP-001"] = projects` |
| Config | base_url=`http://sonarqube-demo:9000`, auth `admin:a123` |
| `connect()` | ✅ `/api/system/status` → `{"status":"UP","version":"9.9.8"}` |
| `execute("projects")` | ✅ `/api/projects/search` → project count |
| **Verdict** | **Executes successfully.** No defect inside Docker. (Host mode requires `ECS_SONAR_URL=http://localhost:9000`.) |

**Where it stops:** it does not stop — completes successfully.

---

## OS-001 — Linux — ❌ stopped at technology detection → ✅ fixed

| Stage | Before fix | After fix |
|-------|-----------|-----------|
| Query | `yum check-update` | `yum check-update` |
| `detect_technology` | **Unknown** (no Linux pattern matched `yum`) | **Linux** (added `yum ` pattern) |
| `assess_execution_capability` | **Unsupported Technology** | **Ready** |
| `run_predefined_query` | returns `unsupported_control` — **never dispatched** | dispatches to Linux connector |
| Command run | — | `LINUX_CONTROL_COMMANDS["OS-001"] = hostname` |
| `connect()` (`docker exec ubuntu-demo true`) | would fail (wrong container name + no docker CLI) | ✅ after `container_name: ubuntu-demo` (+ image rebuild for in-container) |
| `execute()` | — | ✅ `ok=True`, output `ubuntu-demo` |
| **Verdict** | **Stopped at step 3 (technology = Unknown).** | **Executes successfully.** |

**Where it stopped:** technology detection (`detect_technology` returned `Unknown`), so the
resolver returned `unsupported_control` and never selected the Linux connector. Secondary
blocker (container name / docker CLI) would also have applied once detection was fixed.

---

## OS-002 — Linux — ❌ stopped at connector connect → ✅ fixed

| Stage | Before fix | After fix |
|-------|-----------|-----------|
| Query | `cat /etc/ssh/sshd_config` | same |
| `detect_technology` | **Linux** (matched `/etc/ssh`) ✅ | Linux ✅ |
| `assess_execution_capability` | **Ready** | Ready |
| Command run | `LINUX_CONTROL_COMMANDS["OS-002"] = uptime` | `uptime` |
| `connect()` (`docker exec ubuntu-demo true`) | ❌ in-container: *"Docker CLI not available"*; host: *"No such container: ubuntu-demo"* | ✅ `container_name: ubuntu-demo` (host); + image rebuild (in-container) |
| `execute()` | — | ✅ `ok=True`, output `…up 1:04, load average: 2.81…` |
| **Verdict** | **Stopped at `connect()`.** | **Executes successfully.** |

**Where it stopped:** `LinuxConnector.connect()` — `docker exec ubuntu-demo` failed because
(a) the running ECS image had no `docker` CLI and (b) the demo container was named
`ecs-ubuntu-demo-1`, not `ubuntu-demo`.

---

## Root-cause summary

| Control | Stop point | Cause | Fix |
|---------|-----------|-------|-----|
| DB-001 | — | none | — |
| APP-001 | — | none | — |
| OS-001 | Technology detection | `yum check-update` not in Linux patterns → Unknown | Added Linux package/service patterns |
| OS-002 | Connector `connect()` | wrong container name + missing docker CLI in ECS image | `container_name: ubuntu-demo`; rebuild ECS image (Dockerfile already installs `docker.io`) |

The original "PostgreSQL unavailable / SonarQube unreachable" reports could not be reproduced
inside the running Docker stack (both execute). They are consistent with **host/venv** runs
where the service DNS names don't resolve (`postgres-demo`, `sonarqube-demo`) — for host runs
set `ECS_PG_HOST=localhost` and `ECS_SONAR_URL=http://localhost:9000`. See
`ECS_CONNECTOR_INVENTORY.md` and `ECS_TARGET_MAPPING_AUDIT.md`.
