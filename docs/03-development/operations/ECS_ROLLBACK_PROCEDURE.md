# ECS Rollback Procedure

**Purpose:** safely revert ECS after a bad deploy or cut-over. Grounded in `docker-compose.yml`, `scripts/restore/`, `ecs_platform/repository/schema.sql`. Documentation only.

> **Golden rule:** the **evidence repository is the source of truth**. Vector store, Redis cache, and MinIO-derived indexes are rebuildable. Always take a backup *before* rolling back, even in an incident (`scripts/backup/backup.sh`).

---

## 1. Decision matrix

| Situation | Rollback type | Section |
|---|---|---|
| Bad app build (code defect, startup crash) | **App-only** (re-deploy previous image) | §2 |
| Bad config/env (auth lockout, wrong DB) | **Config rollback** | §3 |
| Schema change caused breakage | **Schema rollback** (restore) | §4 |
| Data corruption / wrong data | **Data restore** | §5 |
| Cut-over failed end-to-end | **Full cut-over rollback** | §6 |

---

## 2. App-only rollback (most common, lowest risk)

```bash
# Re-deploy the last known-good image tag
docker compose pull ecs            # or set image: ecs:<previous-tag>
docker compose up -d ecs
curl -fsS localhost:8000/healthz && curl -i localhost:8000/readyz
```
No DB change. Schema is unchanged, so the previous app version reconciles via idempotent `init_schema()`. **Verify:** health 200/200, smoke a dashboard.

## 3. Config / environment rollback

1. Restore the previous `.env` / secret set (and `config/*.yaml` if changed).
2. `docker compose up -d ecs` (env is read at startup).
3. If auth lockout: temporarily set `ECS_AUTH_ENABLED=false` **only** in a controlled maintenance window to regain access, fix `auth.yaml`, then re-enable.
**Verify:** users can authenticate; `/readyz` 200.

## 4. Schema rollback

ECS schema is **additive/idempotent** (`CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`) — there are **no automated down-migrations** (see `RECOVERY_RUNBOOK.md §5`). To revert a schema change:

1. Stop the app (maintenance).
2. Restore the pre-change backup into a fresh DB:
   ```bash
   scripts/restore/restore.sh --latest --create --db ecs_repository_rollback
   ```
3. Repoint `ECS_REPO_PG_DATABASE` to the restored DB (or restore over live with `--clean` after a fresh backup).
4. Deploy the matching previous app version.
**Verify:** counts for `evidence`, `audit_log`, `observations` match the backup; dashboards load.

## 5. Data restore (corruption / accidental loss)

```bash
# 1. Capture current (corrupt) state for forensics
scripts/backup/backup.sh --out backups/forensic
# 2. Restore latest good backup over live (maintenance window)
scripts/restore/restore.sh --latest --clean        # prompts to retype DB name unless --yes
# 3. Restart app
docker compose up -d ecs
```
Checksums (`.sha256`) are verified automatically. **Verify:** run the validation row-count comparison; confirm audit/observation counts.

## 6. Full cut-over rollback

1. Disable traffic at the proxy/LB.
2. Restore pre-cutover repository backup (§5) and, if needed, vector store (`restore.sh --label vectors`).
3. Re-deploy the previous app image + previous config/env.
4. Bring up backing services; confirm container healthchecks.
5. `/healthz` 200, `/readyz` 200, `/api/platform/health` Connected.
6. Smoke as key personas; re-enable traffic.
7. Post-mortem; re-plan cut-over.

---

## 7. Post-rollback rebuild of derived stores (non-source-of-record)

| Store | Rebuild |
|---|---|
| Vector store (`pgvector`) | Re-embed from repository (safe; derived) |
| Redis cache | Auto-rebuilds on demand; or `redis-cli FLUSHDB` |
| MinIO artifacts | Restore from object-store backup if affected |

## 8. Verification gate (all rollbacks)

- [ ] `/healthz` 200, `/readyz` 200.
- [ ] `/api/platform/health` healthy for enabled connectors.
- [ ] Repository row counts match expected backup.
- [ ] Persona smoke test passes.
- [ ] Audit log writing.

## 9. Escalation

App/config rollback: L2 platform eng. Schema/data restore: L2 DBA + DR lead. Record every rollback in the incident log with the backup file used.
