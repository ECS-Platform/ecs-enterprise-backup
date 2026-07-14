# Predefined-Query Demo Readiness — Operator Guide

A concise pre-flight guide for preparing the ECS demo environment before running
predefined-query demonstrations. Everything here uses **existing** commands only
(`scripts/start_ecs_demo.sh`, `docker compose`, `docker ps`).

> Sources: `scripts/start_ecs_demo.sh`, `scripts/ecs_demo_startup.py`,
> `docker-compose.yml`, root `start_ecs.sh`. Run all commands from the repository root.

---

## 0. Unified startup — `./start_ecs.sh` (recommended entry point)

`./start_ecs.sh` is the single launcher for the demo. **You never need to run
Uvicorn manually** — the launcher owns starting/stopping the ECS backend.

Run it with no arguments for the interactive menu:

```bash
./start_ecs.sh
```

```text
D = Docker demo mode
R = normal development / host Uvicorn mode
S = status
Q = quit
```

Equivalent non-interactive flags (interactive keys and flags do the same thing):

```bash
./start_ecs.sh --demo     # D: Docker demo mode
./start_ecs.sh --run      # R: normal development / host Uvicorn mode
./start_ecs.sh --status   # S: status (read-only)
./start_ecs.sh --help     # usage
```

How each mode behaves:

- **D / `--demo` (Docker demo mode):** stops any confirmed **host** ECS/Uvicorn
  processes, then starts the Docker ECS stack via
  `./scripts/start_ecs_demo.sh --all --skip-heavy`. Demo mode **never** starts
  Uvicorn itself.
- **R / `--run` (normal development / host Uvicorn):** stops **only** the Docker
  ECS application container, then starts the existing host-development flow
  (`.venv/bin/python -m uvicorn app.main:app --reload`, or the plain `uvicorn`
  fallback when there is no `.venv`). Supporting services — **PostgreSQL, Redis,
  MinIO, the demo databases, and connector containers — keep running** (they are
  never stopped, and no volumes are removed).
- **S / `--status`:** reports the current runtime as one of `docker`,
  `host-python`, `none`, or `conflict`, plus the Docker ECS container state, host
  ECS PID(s), the owner of port 8000, and the `/healthz` result. Read-only.
- **Q:** quit without changes.

Key guarantees:

- **Only one ECS backend runs at a time** — Docker demo mode and host development
  mode are mutually exclusive; the launcher stops the other runtime's ECS before
  starting.
- **Unrelated processes on port 8000 are never killed automatically.** If a
  non-ECS process owns :8000, the launcher prints its PID and full command and
  exits without touching it — free the port yourself, then retry.
- **Ctrl+C** stops host development mode when Uvicorn is running in the
  foreground.

> The `./scripts/start_ecs_demo.sh …` commands in the sections below are the
> underlying demo orchestrator that `./start_ecs.sh --demo` calls; use them
> directly when you need a specific mode (e.g. `--core` or `--status-only`).

---

## 0A. Final demo workflow (single source for the CIO demo)

This is the authoritative, up-to-date workflow after all launcher improvements.
Startup modes and runtime behaviour are detailed in **§0** above; this section
adds the recommended demo sequence, screen order, limitations, troubleshooting
pointers, and success criteria.

### Startup modes (recap of §0)

| Mode | Command | What it does |
|---|---|---|
| Development (host Uvicorn) | `./start_ecs.sh --run` (menu **R**) | Stops only the Docker ECS container, then runs host Uvicorn (`.venv` preferred). |
| Docker Demo | `./start_ecs.sh --demo` (menu **D**) | Stops host ECS, then starts the Docker ECS stack (`start_ecs_demo.sh --all --skip-heavy`). |
| Status | `./start_ecs.sh --status` (menu **S**) | Read-only: runtime, container, host PIDs, :8000 owner, `/healthz`. |
| Interactive | `./start_ecs.sh` | Menu with **D / R / S / Q**. |

**Do not start Uvicorn manually** — the launcher owns the ECS backend.

### Runtime behaviour (recap of §0)
- Only **one** ECS runtime is active at a time.
- **Docker mode stops the host ECS**; **development mode stops the Docker ECS**.
- Duplicate ECS instances are prevented (a healthy host instance is kept; strays are stopped).
- **Unrelated processes are never terminated** — a non-ECS owner of :8000 is reported (PID + command) and the launcher exits.

### Recommended demo startup sequence
1. **Docker running** — confirm Docker Desktop is up (`docker ps`).
2. `./start_ecs.sh --status` — confirm state before starting.
3. `./start_ecs.sh --demo` — bring up the Docker demo stack.
4. **Verify `/healthz`** — status shows `runtime: docker` and `/healthz: ok`.
5. **Open the browser** at `http://127.0.0.1:8000` (hard-refresh if a stale tab).
6. **Verify one predefined query** — run an enabled control (e.g. a PostgreSQL `PGX-*`).
7. **Optional LLM warm-up** — pre-warm the local model if you will demo the assistant.

### Recommended demo flow (screen order)
1. Executive Dashboard (`/dashboard/cio`)
2. Predefined Queries (`/mvp/predefined-queries`)
3. Connector Test Workbench (`/mvp/connectors/test-workbench`)
4. Evidence Repository (`/mvp/audit/repository`)
5. Evidence Packs (`/mvp/audit/packs`)
6. Evidence Reuse (`/mvp/evidence-story`)
7. ECS Benchmark (`/mvp/ecs-benchmark`)
8. LLM Prompt Workbench (`/mvp/audit/llm-workbench`)

### Known demo limitations (expected, not defects)
- **Connector Test Workbench** uses a **mock transport** without live credentials — demo Dry Run + Parser Test; do not run live "Collect".
- **ECS Benchmark** is a **simulated** comparison (ECS vs manual) — press Run to animate; state that real numbers come from the pilot.
- **Evidence Repository** seeded data may show **Unknown / Unassessed** in the technology/verdict breakdown until validation runs — lead with volume + versioning, avoid that drill.
- **Heavy demo targets** (Yugabyte, Oracle, SQL Server, SonarQube, Aerospike) may show **SKIPPED** under `--all --skip-heavy` — expected on a typical laptop.
- **Kubernetes / OpenShift / Windows** show **EXTERNAL** (no local target) — informational only.

### Troubleshooting (summary — see recovery guide for step-by-step)
- **Port 8000 conflict** — launcher prints the non-ECS PID/command; free that process and retry.
- **Docker unavailable** — start Docker Desktop; re-run `--status`.
- **Runtime conflict** (host + Docker) — use `./start_ecs.sh` (it stops the other runtime); confirm `runtime: docker`.
- **Health check failure** — `/healthz` not ok → restart the failing service; re-run `--demo`.
- **Browser cache** — hard-refresh / reopen the tab; keep demo tabs pre-opened.
- **Predefined query failure** — use a control already marked **Ready**; or show catalog + expected evidence.
- **LLM unavailable** — use offline-safe features (Classify / Token Estimate / dry-run benchmark); deterministic outputs still work.

> Full step-by-step recovery is maintained separately in the **ECS Demo Recovery
> Cheat Sheet**; this section is a summary and does not duplicate it. See also
> §7 (troubleshooting table) below.

### Demo success criteria (healthy state)
- `runtime: docker`
- `/healthz` = OK
- Executive Dashboard loads
- Connector Test Workbench opens
- Evidence Repository populated (evidence keys / versions shown)
- One predefined query executes successfully
- No blocking **FAIL** status for the screens you will demo

---

## 1. Prerequisites

- **Docker Desktop running.** The startup script exits immediately if the Docker
  daemon is not available.
- **Correct Git branch:** `cursor/predefined-queries-module`.
  ```bash
  git branch --show-current      # expect: cursor/predefined-queries-module
  ```
- **Virtual environment activated.** `start_ecs_demo.sh` auto-activates
  `.venv/bin/activate` (or `.venv/Scripts/activate` on Windows Git Bash) if present.
  To activate manually:
  ```bash
  source .venv/bin/activate
  ```

---

## 2. Clean startup (avoid two ECS instances)

ECS must run **either** as the Docker `ecs` container **or** as a host-Python
process on port 8000 — never both. The predefined-query smoke probes execute
inside whichever runtime is detected, so a stray host process causes confusing,
false failures.

- **Detect if ECS is already running / which runtime:** run a non-destructive
  status check; the first output line reports the runtime:
  ```bash
  ./scripts/start_ecs_demo.sh --status-only
  # prints:  ECS runtime: docker        (Docker container on :8000)
  #          ECS runtime: host-python   (a local uvicorn on :8000)
  #          ECS runtime: none          (nothing on :8000)
  ```
  You can also list containers directly:
  ```bash
  docker ps           # look for an "…-ecs-1" container on 0.0.0.0:8000
  ```
- **Stop an existing host-Python ECS (if required):** any start command that
  actually starts services (i.e. **not** `--status-only`) automatically stops a
  host `uvicorn app.main:app` bound to :8000 before bringing up the Docker `ecs`
  container. So simply run:
  ```bash
  ./scripts/start_ecs_demo.sh --core
  # if a host process was stopped, it prints: Stopped host uvicorn on :8000: pid <n>
  ```
- **Avoid two instances simultaneously:** prefer the **Docker** runtime for demos.
  Do not manually launch `uvicorn` while the Docker `ecs` container is up. If both
  somehow occupy :8000, the script reports a port issue (see §7).

---

## 3. Demo startup sequence

Run these from the repository root. Each is idempotent (safe to re-run).

- **`./scripts/start_ecs_demo.sh --status-only`**
  Reports current state (runtime + technology status table) **without starting or
  stopping anything**. Use it first, to see what is already running.

- **`./scripts/start_ecs_demo.sh --core`**
  Starts only the core backing services (`postgres-demo`, `postgres`, `pgvector`,
  `redis`, `minio`) plus the ECS app, waits for readiness, and prints the status
  table. Use for a lightweight demo (PostgreSQL controls) or on an 8 GB laptop.
  This is also the **default** if you run the script with no mode flag.

- **`./scripts/start_ecs_demo.sh --all --skip-heavy`**
  Starts core + the lightweight demo targets, **skipping the heavy ones**
  (Yugabyte, Oracle, SQL Server, SonarQube, Aerospike). Use for a broad
  predefined-query demo on a typical laptop. It also runs the control smoke probes
  automatically. Omit `--skip-heavy` only on a 16 GB+ machine when you need the
  heavy targets.

> Optional: `--technology <NAME>` (e.g. `SonarQube`) prepares just one technology
> plus core. `--json` emits the report as JSON. `--help` lists all flags.

---

## 4. Expected validation (status meanings)

The status table prints one row per technology. Acceptable outcomes:

| Status | Meaning |
|---|---|
| **PASS** | Container running, readiness probe succeeded, connector config resolved (and the control probe succeeded where run). |
| **WARN** | Non-blocking issue — reachable/started but a soft check is incomplete (e.g. an expected secret shows `MISSING`, a port-in-use notice, or an optional scanner image is absent). Does not fail startup. |
| **SKIPPED** | Technology not selected for this run (e.g. an optional target you did not start), so it was not checked. |
| **EXTERNAL** | Requires infrastructure outside the local demo (Kubernetes, OpenShift) or is unsupported locally (Windows). Informational only. |

**Warnings acceptable for a local demo:**
- Heavy targets **SKIPPED** when using `--all --skip-heavy` (Yugabyte, Oracle,
  SQL Server, SonarQube, Aerospike) — expected.
- **EXTERNAL** for Kubernetes / OpenShift, and Windows — expected (no local target).
- **WARN** for Trivy when the `aquasec/trivy` image has not been pulled (see §7).
- **WARN** on a technology whose secret shows `MISSING` but you are not demoing it.

A **FAIL** on a technology you intend to demo (or a CORE FAILURE line) is **not**
acceptable — resolve before demoing (see §7).

---

## 5. Representative demo controls

These controls are the built-in smoke probes for their technologies (executed
automatically during `--all` / `--probe-connectors` runs, in the detected ECS
runtime). Use them as your demo talking points:

| Control | Technology | Requires (target) |
|---|---|---|
| **MYX-002** | Aurora MySQL (MySQL 8 locally) | `mysql-demo` (profile `db-targets`) |
| **APP-001** | SonarQube | `sonarqube-demo` (heavy; profile `demo-connectors`) |
| **PGX-001** | PostgreSQL (one PostgreSQL control) | `postgres-demo` (core — always up) |
| a MongoDB control | MongoDB | `mongodb-demo` (profile `db-demo-extended`) |
| **ASX-001** | Aerospike | `ecs-aerospike` (heavy; profile `aerospike`) |

> Notes: `PGX-001` works with just `--core`. `MYX-002` needs the `db-targets`
> profile (started by `--all`). `APP-001` and `ASX-001` are **heavy** and are
> skipped by `--skip-heavy`; run without `--skip-heavy` (16 GB+) to demo them.
> For a MongoDB control, start `mongodb-demo` (included by `--all`).

---

## 6. Demo shutdown

- **Stop ECS cleanly** (leave data volumes intact):
  ```bash
  docker compose stop ecs
  ```
- **Stop the demo containers as well**, when you are finished. Include the
  profiles you started so their services are included:
  ```bash
  docker compose \
    --profile db-targets --profile db-demo-extended \
    --profile demo-connectors --profile infra-demo \
    --profile infra-demo-extended --profile aerospike \
    down
  ```
  For a core-only session, `docker compose down` is sufficient. Add `-v` **only**
  if you intend to discard demo data volumes.

---

## 7. Quick troubleshooting

| Symptom | What it means / fix |
|---|---|
| **Docker not running** — `ERROR: Docker Desktop/daemon is not available.` | Start Docker Desktop, wait until it is ready, then re-run the command. |
| **Port 8000 already in use** — `port 8000 is in use by a non-ECS process` (CORE FAILURE) | A non-ECS process holds :8000. Free that port (stop the other app) and re-run. A **host uvicorn** on :8000 is stopped automatically by any non-`--status-only` run. |
| **ECS runtime mismatch** — probes fail although a container looks up | Confirm the runtime with `./scripts/start_ecs_demo.sh --status-only` (top line). For demos use **docker**; do not also run a host `uvicorn`. Re-running `--core`/`--all` recreates the ECS container if it is unhealthy or off the compose network. |
| **Yugabyte intentionally skipped** — Yugabyte shows SKIPPED | Expected with `--all --skip-heavy` (Yugabyte is a heavy target). To include it, run without `--skip-heavy` on a 16 GB+ machine. |
| **Trivy image missing** — Trivy shows WARN (`aquasec/trivy image missing`) | Non-blocking for the demo. To clear it, pull the image: `docker pull aquasec/trivy`, then re-run `--status-only`. |

---

## 8. One-page pre-demo checklist (< 5 minutes)

1. [ ] Docker Desktop is running.
2. [ ] On branch `cursor/predefined-queries-module` (`git branch --show-current`).
3. [ ] Virtual environment active (or rely on the script to auto-activate `.venv`).
4. [ ] `./scripts/start_ecs_demo.sh --status-only` → note **ECS runtime** (want `docker` or `none`; not a stray `host-python`).
5. [ ] Start the stack:
       - Light demo → `./scripts/start_ecs_demo.sh --core`
       - Broad demo → `./scripts/start_ecs_demo.sh --all --skip-heavy`
6. [ ] Confirm top line reads `ECS runtime: docker` and the status table shows **PASS** for the technologies you will demo.
7. [ ] Acceptable non-blockers only: heavy targets **SKIPPED** (with `--skip-heavy`), **EXTERNAL** for K8s/OpenShift/Windows, Trivy **WARN** if unused.
8. [ ] Verify your demo controls are ready: **PGX-001** (core), **MYX-002** (needs `--all`); for **APP-001**/**ASX-001** run without `--skip-heavy`.
9. [ ] Re-run `--status-only` any time to reconfirm before you present.
10. [ ] After the demo: `docker compose stop ecs` (and `docker compose … down` with your profiles to stop demo containers).
