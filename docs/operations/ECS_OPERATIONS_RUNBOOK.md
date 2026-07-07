# ECS Operations Runbook

**Audience:** platform operators / SRE running ECS. **Scope:** day-to-day operation of every ECS component. **Constraint:** documentation only — grounded in `docker-compose.yml`, `app/routes_platform.py`, `config/*.yaml`, `ecs_platform/`, and `scripts/`. No source code changed.

> **Topology (from `docker-compose.yml`):** `ecs` app (`:8000`) + backing services: `postgres` evidence repository (`:5433→5432`, db `ecs_repository`), `pgvector` (`:5434→5432`, db `ecs_vectors`), `redis` (`:6379`), `minio` (`:9002` API / `:9001` console), `postgres-demo` (`:5432`). Profile services: `gitea` (`:3000`) + `jenkins` (`:8080`) under `sources`; `ubuntu-demo` + `sonarqube-demo` (`:9000`) under `demo-connectors`. LLM via **host-local Ollama** (`qwen3:8b`, `:11434`).

---

## 1. Global startup sequence

Bring up in dependency order (the app `depends_on: postgres-demo, postgres, pgvector`):

```bash
# 1. Backing data services first (they have container healthchecks)
docker compose up -d postgres pgvector redis minio postgres-demo
# 2. (optional) real source systems
docker compose --profile sources up -d gitea jenkins
docker compose --profile demo-connectors up -d ubuntu-demo sonarqube-demo
# 3. Application (auto-runs uvicorn app.main:app on :8000)
docker compose up -d ecs
# 4. Verify
curl -fsS localhost:8000/healthz        # liveness  -> {"status":"ok"}
curl -fsS localhost:8000/readyz         # readiness -> 200 when repo reachable
curl -fsS localhost:8000/api/platform/health   # connector + DB overview
```

**Local (no Docker):** `DEMO_MODE=true ECS_AUTH_ENABLED=false ./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000`. `.env` is auto-loaded at startup (`app/env_bootstrap.py`). Schema is created idempotently on first repo use (`EvidenceRepository.init_schema()` runs `ecs_platform/repository/schema.sql`).

---

## 2. Health checks (authoritative)

| Probe | Endpoint | What it checks | Healthy | Use for |
|---|---|---|---|---|
| **Liveness** | `GET /healthz` | Process up; **does no I/O** by design | `200 {"status":"ok"}` | Container restart policy |
| **Readiness** | `GET /readyz` | PostgreSQL repository reachable (`SELECT 1`) | `200 {"status":"ready","repository_ok":true}`; else `503` | LB / traffic gating |
| **Platform health** | `GET /api/platform/health` | `health_overview()` — connector states + DB | JSON per connector | Ops dashboards / Integration Health UI |
| **Container DB** | compose `pg_isready` | Postgres/pgvector up | healthcheck pass | Compose dependency |
| **Object store** | compose `mc ready local` | MinIO up | healthcheck pass | Compose dependency |

> **Design note:** `/healthz` intentionally avoids dependency I/O so a slow DB never restarts a healthy app. `/readyz` is the dependency-aware gate.

---

## 3. Per-component operations

For each: **Purpose · Startup · Dependencies · Health · Monitoring · Failure scenarios · Recovery · Escalation.**

### 3.1 ECS application (`ecs`)
- **Purpose:** FastAPI + Jinja2 server-rendered platform; serves all ~79 screens, APIs, RAG.
- **Startup:** `uvicorn app.main:app --host 0.0.0.0 --port 8000` (compose adds `--reload` for dev).
- **Dependencies:** Postgres repository (hard for `/readyz`), pgvector (RAG), MinIO (artifacts), Redis (cache/queue), Ollama (AI). Degrades gracefully to demo data when deps are down in demo mode.
- **Health:** `/healthz`, `/readyz`.
- **Monitoring:** request errors in `docker compose logs -f ecs`; 5xx rate; readiness flapping.
- **Failure scenarios:** (a) repo down → `/readyz` 503; (b) port 8000 busy; (c) bad `.env` → auth lockout.
- **Recovery:** `docker compose restart ecs`; fix env; confirm `/readyz` 200.
- **Escalation:** L1 ops → L2 platform eng → app owner.

### 3.2 Evidence repository — `postgres` (db `ecs_repository`)
- **Purpose:** durable system of record (`evidence`, `audit_log`, `observations`, `frameworks`, `controls`, lineage/mapping).
- **Startup:** container with `pg_isready` healthcheck; volume `ecs_repo_data`.
- **Dependencies:** none (foundational).
- **Health:** `pg_isready -U ecs_user -d ecs_repository`; app `/readyz`.
- **Monitoring:** connections vs `max_pool=10`; `statement_timeout=30s`; disk on `ecs_repo_data`; replication lag (if HA added).
- **Failure scenarios:** down → all repo-backed pages fail; disk full; corruption.
- **Recovery:** see `ECS_BACKUP_AND_RECOVERY_GUIDE.md` (`scripts/restore/restore.sh --latest --clean`).
- **Escalation:** L2 DBA → DR plan if data loss.

### 3.3 Vector store — `pgvector` (db `ecs_vectors`)
- **Purpose:** embeddings for RAG (`evidence_embeddings` table, collection `ecs_evidence_chunks`, dim 768).
- **Startup:** container with `pg_isready`; volume `ecs_vector_data`.
- **Dependencies:** embedding model (`nomic-embed-text` via Ollama) to (re)populate.
- **Health:** `pg_isready -d ecs_vectors`.
- **Monitoring:** row count vs evidence count; query latency; dim mismatch (`ECS_VECTOR_DIM`).
- **Failure scenarios:** down → AI Assistant returns no citations (refuses, by design); embeddings stale.
- **Recovery:** restart; **re-embed** from repository (rebuild is safe — vectors are derived, not source of record).
- **Escalation:** L2 platform eng / AI owner.

### 3.4 Object store — `minio` (bucket `ecs-evidence`)
- **Purpose:** raw evidence artifacts (files, scan reports, attachments).
- **Startup:** `server /data`; `mc ready local` healthcheck; volume `ecs_minio_data`.
- **Health:** console `:9001`; `mc ready`.
- **Monitoring:** bucket size; 4xx/5xx; credential validity (`MINIO_ACCESS_KEY/SECRET_KEY`).
- **Failure scenarios:** down → artifact upload/download fails (metadata still in repo).
- **Recovery:** restart; restore bucket from object-store backup; re-link.
- **Escalation:** L2 storage.

### 3.5 Cache/queue — `redis`
- **Purpose:** cache + lightweight queueing (`REDIS_URL`).
- **Startup:** `redis-server --save 60 1`; volume `ecs_redis_data`.
- **Health:** `redis-cli ping` → PONG.
- **Monitoring:** memory, evictions, connected clients.
- **Failure scenarios:** down → cache miss / slower responses (non-fatal, recomputed).
- **Recovery:** restart (cache is rebuildable; not source of record).
- **Escalation:** L2 platform eng.

### 3.6 Local LLM — Ollama (`qwen3:8b`)
- **Purpose:** keyless local LLM + embeddings for RAG/copilot. Default provider.
- **Startup:** **host daemon** on `:11434`; container reaches it via `host.docker.internal` (`extra_hosts`).
- **Dependencies:** model pulled (`ollama pull qwen3:8b`, `ollama pull nomic-embed-text`).
- **Health:** `curl host.docker.internal:11434/api/tags`.
- **Monitoring:** latency, GPU/CPU, `keep_alive=30m` residency.
- **Failure scenarios:** daemon down / model missing → AI features unavailable (rest of ECS unaffected).
- **Recovery:** start daemon, pull model; or switch provider `ECS_LLM_PROVIDER=gemini` (no code change).
- **Escalation:** see `ECS_LOCAL_LLM_OPERATIONS_GUIDE.md`.

### 3.7 Connectors (12)
- **Purpose:** automated evidence collection from source systems.
- **Startup:** disabled by default; enabled via `ECS_<X>_ENABLED=true` + credentials.
- **Health:** `/api/platform/health` (per-connector); Integration Health UI.
- **Failure/Recovery/Escalation:** see `ECS_CONNECTOR_FAILURE_PLAYBOOK.md`.

### 3.8 Functional modules (7 nav groups)
Executive Overview · Frameworks · Operations · Governance · Evidence Governance · Enterprise GRC · AI SDLC. All are served by the `ecs` app; their operational health is the app's health plus the backing services they read (repo/pgvector/minio). Demo mode renders them on deterministic data with no backing services. Module reference: `docs/product/ECS_MODULE_REFERENCE.md`.

---

## 4. Routine operational tasks

| Task | Command |
|---|---|
| Tail app logs | `docker compose logs -f ecs` |
| Restart app | `docker compose restart ecs` |
| Backup repository | `scripts/backup/backup.sh` (`--vector` to include vectors) |
| Validate backups | `scripts/backup/validate_backup_restore.sh` |
| Sync a connector | `POST /api/platform/sync/{connector}` (admin) |
| Run demo readiness | `python scripts/validate_demo_readiness.py` → expect READY |
| Run tests | `./venv/bin/pytest` (39 suites) |

---

## 5. Escalation matrix

| Tier | Owner | Handles |
|---|---|---|
| L1 | Ops on-call | restarts, health checks, known playbooks |
| L2 | Platform eng / DBA | DB/vector/storage, connector configs, recovery |
| L3 | App/AI owners | code-level defects, model issues |
| DR lead | per `ECS_DISASTER_RECOVERY_PLAN.md` | data loss, site failure |

See `ECS_SUPPORT_RUNBOOK.md` for symptom-driven triage and `ECS_PRODUCTION_MONITORING_GUIDE.md` for alert thresholds.

---

## 6. Connector operations references

- **Connector API reference (11 connectors):** [../enterprise_connector_api_reference.md](../connectors/enterprise_connector_api_reference.md)
- **Microsoft Graph connector reference:** [../microsoft_graph_connector_api_reference.md](../graph-api/microsoft_graph_connector_api_reference.md)
- **Scheduler runtime flow (dry-run + execution):** [../scheduler_runtime_flow.md](../scheduler/scheduler_runtime_flow.md)
- **Connector Test Workbench (safe health/parser testing):** [../connector_test_workbench_design.md](../connectors/connector_test_workbench_design.md)
- **Runtime call graph & sequence diagrams:** [../runtime_call_graph.md](../scheduler/runtime_call_graph.md)
- **Batch vs manual (scheduler vs workbench):** [../test_workbench_vs_scheduler.md](../scheduler/test_workbench_vs_scheduler.md)

Connector health at runtime: `GET /api/audit/integrations/health` (all) and
`GET /api/audit/integrations/{name}/health` (one); scheduler dry-run via
`scripts/run_uat_asset_scheduler.py --dry-run`.
