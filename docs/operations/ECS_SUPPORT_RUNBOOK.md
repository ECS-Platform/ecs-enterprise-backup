# ECS Support Runbook

**Audience:** L1/L2 support. **Goal:** triage and resolve incidents by symptom. Grounded in `app/routes_platform.py`, `app/auth/*`, `config/*.yaml`, `docker-compose.yml`, and existing `docs/TROUBLESHOOTING_GUIDE.md` / `docs/operations/ecs_runbook.md`. Documentation only.

---

## 1. First-response checklist (any incident)

```bash
curl -fsS localhost:8000/healthz                 # app process up?
curl -i  localhost:8000/readyz                   # repo reachable? (503 => DB issue)
curl -fsS localhost:8000/api/platform/health     # connector + DB overview
docker compose ps                                # container states
docker compose logs --tail=200 ecs               # recent app errors
```

Classify: **App down** (`/healthz` fails) · **Degraded** (`/readyz` 503) · **Feature-specific** (one module/connector) · **Cosmetic** (UI/data).

---

## 2. Symptom → root cause → resolution → verification

| # | Symptom | Likely root cause | Resolution | Verify |
|---|---|---|---|---|
| 1 | `/healthz` fails / app unreachable | container crashed or port 8000 busy | `docker compose restart ecs`; `lsof -i:8000` kill stray uvicorn | `/healthz` 200 |
| 2 | `/readyz` returns 503 | Postgres repository down/unreachable | start `postgres`; check `pg_isready`; verify `ECS_REPO_PG_*` | `/readyz` 200 |
| 3 | Every page returns 401/403 | `ECS_AUTH_ENABLED=true` without working OIDC | configure `config/auth.yaml` IdP, or demo: `ECS_AUTH_ENABLED=false` | page loads |
| 4 | Pages show "Repository unavailable" | repo down (real mode) | restore DB connectivity; demo mode auto-falls back | data renders |
| 5 | Connector shows "disabled" | `ECS_<X>_ENABLED` unset | set flag + creds in host `.env`; `docker compose up -d ecs` | Integration Health = Connected |
| 6 | Connector "auth failed" | bad/expired token | rotate credential; re-sync | `/api/platform/health` ok |
| 7 | AI Assistant returns no answer / "no evidence" | Ollama down or empty vector store | start Ollama + pull model; re-embed | citation returned |
| 8 | AI Assistant slow | model not resident / cold | raise `ECS_OLLAMA_KEEP_ALIVE`; warm model | latency normal |
| 9 | Evidence upload fails | MinIO down or bucket missing | restart `minio`; create bucket `ecs-evidence` | upload ok |
| 10 | `.env` change not applied | edited after start | restart app (env read at startup) | value visible |
| 11 | Slow pages, no errors | Redis down (cache miss) | restart `redis` | latency normal |
| 12 | Demo looks empty/broken | not in demo mode | set `DEMO_MODE=true ECS_AUTH_ENABLED=false`; run validator | validator READY |
| 13 | Schema error on startup | partial/old DB | `init_schema()` is idempotent; if corrupt, restore from backup | startup clean |
| 14 | Count mismatch in UI vs docs | catalog vs demo-seed | expected; see `docs/AUDIT/ECS_DOCUMENTATION_INVENTORY.md §5` | n/a |

---

## 3. Diagnostics by subsystem

| Subsystem | Command |
|---|---|
| App | `docker compose logs -f ecs` |
| Repository | `docker compose exec postgres psql -U ecs_user -d ecs_repository -c '\dt'` |
| Vector store | `docker compose exec pgvector psql -U ecs_user -d ecs_vectors -c 'select count(*) from evidence_embeddings;'` |
| Object store | open MinIO console `:9001` |
| Redis | `docker compose exec redis redis-cli ping` |
| Ollama (host) | `curl host.docker.internal:11434/api/tags` |
| Connectors | `curl localhost:8000/api/platform/health` |

---

## 4. Severity & response

| Sev | Definition | Examples | Target response |
|---|---|---|---|
| **S1** | Platform down / data loss | `/healthz` fails; repo corruption | Immediate; invoke DR if data loss |
| **S2** | Major feature down | repo `/readyz` 503; all connectors failing | < 30 min |
| **S3** | Single feature/connector degraded | one connector auth fail; AI slow | next business day |
| **S4** | Cosmetic / count drift | demo-seed labels | backlog |

---

## 5. Escalation

L1 (this runbook) → **L2 platform eng/DBA** (DB, vector, storage, connectors) → **L3 app/AI owners** (defects, models). Data loss / site failure → **DR lead** (`ECS_DISASTER_RECOVERY_PLAN.md`). Connector specifics → `ECS_CONNECTOR_FAILURE_PLAYBOOK.md`. LLM specifics → `ECS_LOCAL_LLM_OPERATIONS_GUIDE.md`.

---

## 6. Known-good demo recovery (fastest reset)

```bash
DEMO_MODE=true ECS_AUTH_ENABLED=false ./venv/bin/python scripts/validate_demo_readiness.py
# If a Dockerized demo is corrupt:
bash demo-data/recreate_demo.sh
```
