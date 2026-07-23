# ECS Operations Runbook

> Operational procedures for the ECS platform, derived from `Dockerfile`, `docker-compose.yml`,
> `start_ecs.sh`, `config/`, and the health/lifespan logic in `app/main.py` /
> `app/routes_platform.py`. Items beyond the repo are tagged **[RECOMMENDATION]**.

---

## 1. Startup Procedures

### 1.1 Local (developer)

`start_ecs.sh` performs: `pkill -f uvicorn`, install core deps, run `uvicorn app.main:app --reload`,
then open `http://127.0.0.1:8000`.

```bash
# From repo root
bash start_ecs.sh
# or manually:
uvicorn app.main:app --reload
# open http://127.0.0.1:8000
```

> **Python version note:** the project targets **Python 3.12** (`Dockerfile`). If multiple Python
> versions are installed, invoke the 3.12 interpreter explicitly, e.g.
> `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m uvicorn app.main:app --reload`.

### 1.2 Docker Compose (demo / integrated)

```bash
# Core stack (app + postgres-demo + postgres + pgvector + redis + minio)
docker compose up -d

# Include demo connector targets (Ubuntu, SonarQube)
docker compose --profile demo-connectors up -d

# Include source systems (Gitea, Jenkins)
docker compose --profile sources up -d
```

App: `http://localhost:8000`. MinIO console: `http://localhost:9001`.

### 1.3 Container (production-style)

```bash
docker build -t ecs:latest .
docker run -d -p 8000:8000 \
  -e ECS_AUTH_ENABLED=true -e ECS_AUTH_PROVIDER=azure_ad \
  -e DEMO_MODE=false \
  ecs:latest
```

> **Production guardrails:** set `DEMO_MODE=false` (otherwise auth is bypassed —
> `app/auth/demo.py`) and provide Azure AD / OIDC settings (`config/auth.yaml`, `.env.example`).

### 1.4 Startup verification

On boot, the lifespan (`app/main.py`) seeds demo workflow state, refreshes the evidence repository,
self-heals governance, validates predefined queries, best-effort initializes DB schema, and warms LLM
models. Verify:

```bash
curl -fsS http://localhost:8000/healthz     # liveness
curl -fsS http://localhost:8000/readyz      # readiness (checks PostgreSQL)
curl -fsS http://localhost:8000/api/platform/health   # connector health
```

---

## 2. Shutdown Procedures

### Local
```bash
pkill -f uvicorn
```

### Docker Compose
```bash
docker compose down                 # stop containers, keep volumes
docker compose down --volumes       # stop and DELETE data volumes (destructive)
docker compose --profile sources --profile demo-connectors down   # include profile services
```

### Single container
```bash
docker stop <container_id> && docker rm <container_id>
```

> **Note:** default app state is in-process and is lost on shutdown; durable data lives in the
> PostgreSQL/MinIO/Redis volumes (`ecs_repo_data`, `ecs_vector_data`, `ecs_redis_data`,
> `ecs_minio_data`). A clean shutdown does not require draining the web tier because there is no
> persistent in-app queue.

---

## 3. Backup Procedures

Backups target the **durable backing services** (the app tier is stateless/seeded).

### PostgreSQL (repository + vectors + demo)
```bash
# Evidence repository (port 5433 -> service "postgres", db ecs_repository)
docker compose exec postgres pg_dump -U ecs_user ecs_repository > backup_ecs_repository_$(date +%F).sql

# Vector store (port 5434 -> service "pgvector", db ecs_vectors)
docker compose exec pgvector pg_dump -U ecs_user ecs_vectors > backup_ecs_vectors_$(date +%F).sql

# Demo DB (port 5432 -> service "postgres-demo", db ecs_demo)
docker compose exec postgres-demo pg_dump -U ecs_user ecs_demo > backup_ecs_demo_$(date +%F).sql
```

### MinIO object store (evidence files)
```bash
# Using mc client against console/API at :9002 (root user ecs_minio)
mc alias set ecs http://localhost:9002 ecs_minio ecs_minio_secret
mc mirror ecs/ ./minio-backup-$(date +%F)/
```

### Config
Back up `config/auth.yaml` and `config/rbac.yaml` (version-controlled in repo) and any host
environment/secret files.

> **[RECOMMENDATION]** automate nightly `pg_dump` + MinIO mirror to immutable, encrypted, off-site
> storage; define retention aligned to banking record-keeping requirements.

---

## 4. Recovery Procedures

### PostgreSQL restore
```bash
docker compose up -d postgres
docker compose exec -T postgres psql -U ecs_user -d ecs_repository < backup_ecs_repository_<date>.sql
# repeat for pgvector/ecs_vectors and postgres-demo/ecs_demo as needed
```

### MinIO restore
```bash
mc mirror ./minio-backup-<date>/ ecs/
```

### Full environment recovery
```bash
docker compose up -d                      # bring up backing services
# restore PostgreSQL + MinIO from latest backups (above)
docker compose restart ecs                # app re-seeds/self-heals on startup
curl -fsS http://localhost:8000/readyz    # confirm readiness
```

> The app re-runs seeding and `self_heal_governance` on startup, so the web tier recovers without
> manual data fixes once backing stores are restored.

---

## 5. Incident Management

| Severity | Example | First action |
|---|---|---|
| SEV1 | App down / `/healthz` failing | Check `ecs` container logs; restart; verify port 8000 |
| SEV1 | `/readyz` failing | PostgreSQL (`postgres`) unreachable — check DB container/health |
| SEV2 | Drilldowns show "Unable to load records" | Check API status for `/api/ecs/*-drill`; confirm latest static asset version (cache-bust); inspect server logs |
| SEV2 | Connector sync failing | `GET /api/platform/health`; check connector target container/credentials |
| SEV3 | Stale UI / wrong CSS or JS | Confirm `_no_cache_html` active and `asset_ver` cache-busting; hard refresh |
| SEV3 | LLM/RAG assistant errors | Check `OLLAMA_URL` / provider keys; `GET /api/platform/rag/status` |

**General loop:** detect (probes/alerts) → triage (logs + health endpoints) → mitigate (restart /
failover / disable failing connector) → verify (`/healthz`, `/readyz`, affected feature) →
post-incident review.

**Logs:**
```bash
docker compose logs -f ecs
docker compose logs -f postgres pgvector minio redis
```

---

## 6. Monitoring Guidance

- **Liveness:** `GET /healthz` (poll ~10–30s).
- **Readiness:** `GET /readyz` (gates traffic on PostgreSQL availability) — use for LB health checks.
- **Connector health:** `GET /api/platform/health` (per-connector status).
- **RAG/LLM status:** `GET /api/platform/rag/status`, `/api/platform/llm`, `/api/platform/gemini`.
- **Backing services:** PostgreSQL (`postgres`, `pgvector`) and MinIO ship compose healthchecks
  (`pg_isready`, `mc ready`). Redis persists with `--save 60 1`.

**[RECOMMENDATION]** export metrics (request latency/error rate, drilldown failures, connector sync
success, evidence workflow throughput) to a metrics/APM stack; alert on `/readyz` failures, elevated
5xx, and connector sync failures.

---

## 7. Troubleshooting Guide

| Symptom | Likely cause | Resolution |
|---|---|---|
| `No module named uvicorn` | Wrong Python interpreter (3.14 vs 3.12) | Use the Python 3.12 interpreter explicitly |
| `/readyz` returns not-ready | PostgreSQL (`postgres`) down/unhealthy | Start/repair DB container; check `pg_isready` healthcheck |
| Drilldown modal stuck/"Unable to load records" | API error/timeout or stale JS cache | Check `/api/ecs/*-drill` response & status; verify `?v=<mtime>` asset versioning; hard refresh |
| HTTP 422 on a drill endpoint | Malformed `count` param | Backend `_safe_count` + JS `safeCount` handle this; confirm latest code/asset version loaded |
| Sidebar clipped / wrong layout in one browser | Stale HTML/inline CSS cache | `_no_cache_html` middleware forces revalidation; clear cache / hard refresh |
| Auth blocking all routes unexpectedly | `ECS_AUTH_ENABLED=true` without valid provider config | Configure Azure AD/OIDC in `config/auth.yaml`/env, or set `DEMO_MODE=true` for demo only |
| Auth bypassed in production | `DEMO_MODE=true` | Set `DEMO_MODE=false` and verify provider config |
| Connector sync fails | Target unreachable / bad credentials | Bring up `--profile demo-connectors`/`--profile sources`; verify env credentials |
| LLM assistant fails | Ollama not reachable / no provider key | Verify `OLLAMA_URL` (`host.docker.internal:11434`) or set `ECS_LLM_PROVIDER`+keys |
| Reports/export empty | No matching data for role/scope | Verify role data scope (`role_filter_scope.py`); check `export_history` |

**Health-check quick script:**
```bash
for ep in /healthz /readyz /api/platform/health; do
  echo "== $ep =="; curl -fsS "http://localhost:8000$ep" || echo "FAILED";
done
```
