# ECS Production Checklist

**Purpose:** verify ECS is configured safely for production. Grounded in `config/*.yaml`, `docker-compose.yml`, `.env.example`, `app/auth/*`. Documentation only — no code changed.

> ECS defaults are **secure-by-default**: `ECS_AUTH_ENABLED=true`, `DEMO_MODE=false`. The Docker Compose file ships **demo credentials** (`ecs_password`, `ecs_minio_secret`, `admin/a123`, `admin123`) — these **must be replaced** for production.

---

## 1. Security & access

- [ ] `ECS_AUTH_ENABLED=true` (RBAC + OIDC/JWT enforced).
- [ ] `DEMO_MODE=false`.
- [ ] `config/auth.yaml`: real OIDC issuer/audience; demo bypass disabled.
- [ ] RBAC on **canonical** `config/rbac.yaml` (`rbac_catalog`, 9 roles); legacy `role_permissions.py` not relied upon.
- [ ] Page guard + mutation guard active (verify a 403 for an unauthorized action).
- [ ] All demo secrets replaced (DB, MinIO, Sonar, Jenkins, LLM keys) via host `.env` / vault — **never** in YAML or git.

## 2. Data services

- [ ] `postgres` evidence repository on durable, backed-up storage (not the demo `postgres-demo`).
- [ ] `ECS_REPO_PG_*` point to the production DB; pool (`min 1/max 10`) and `statement_timeout=30s` reviewed.
- [ ] `pgvector` provisioned; `ECS_VECTOR_DIM` matches embedding model (768 for `nomic-embed-text`/`text-embedding-004`).
- [ ] `minio`/S3 bucket `ecs-evidence` exists; `MINIO_SECURE=true` with TLS in prod.
- [ ] `redis` reachable (`REDIS_URL`).
- [ ] Schema applied (`init_schema()` / `schema.sql`); migration strategy decided (Alembic roadmap in recovery runbook).

## 3. AI / LLM

- [ ] LLM provider chosen (`ECS_LLM_PROVIDER`): local `ollama` (data stays on-prem) **or** managed (`gemini/openai/azure_openai/claude`) with key in env.
- [ ] If Ollama: daemon reachable (`OLLAMA_URL`), models pulled (`qwen3:8b`, `nomic-embed-text`).
- [ ] RAG guardrails confirmed: `require_citations: true`, `refuse_without_evidence: true`.
- [ ] Vector store populated (embeddings count ≈ evidence count).

## 4. Connectors

- [ ] Only required connectors enabled (`ECS_<X>_ENABLED=true`); others remain disabled.
- [ ] Each enabled connector authenticates (`/api/platform/health` = Connected).
- [ ] Credentials least-privilege (see `demo-data/SAAS_CONNECTOR_READINESS.md` scopes).
- [ ] First sync completed and evidence visible in Evidence Explorer.

## 5. Runtime & deployment

- [ ] Remove dev `--reload` and source bind-mounts from the production app command (compose dev settings).
- [ ] `restart: unless-stopped` (or k8s restart policy) set.
- [ ] `/healthz` wired to liveness; `/readyz` wired to readiness/LB.
- [ ] Resource limits set (CPU/mem) for app + DBs.
- [ ] Reverse proxy / TLS termination in front of `:8000`.

## 6. Observability

- [ ] Log aggregation for `ecs` container.
- [ ] Alerts on `/readyz` 503, 5xx rate, DB/vector/MinIO/Redis health (see `ECS_PRODUCTION_MONITORING_GUIDE.md`).
- [ ] Connector sync failure alerts.

## 7. Backup & recovery

- [ ] `scripts/backup/backup.sh` scheduled (nightly) to durable off-host storage.
- [ ] Restore drill passed (`scripts/backup/validate_backup_restore.sh` → exit 0).
- [ ] RPO/RTO agreed; `ECS_BACKUP_AND_RECOVERY_GUIDE.md` + `ECS_DISASTER_RECOVERY_PLAN.md` reviewed.

## 8. Validation

- [ ] `./venv/bin/pytest` green (39 suites).
- [ ] Smoke test: login → CIO dashboard → a framework → audit prep → report.
- [ ] Health endpoints return expected status under load.

---

**Sign-off:** Platform eng ____ · Security ____ · DBA ____ · Product owner ____ · Date ____
