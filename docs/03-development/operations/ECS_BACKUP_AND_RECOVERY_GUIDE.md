# ECS Backup & Recovery Guide

**Purpose:** production backup/restore for ECS persistent stores. Grounded in `scripts/backup/`, `scripts/restore/`, `config/repository.yaml`, `config/vectorstore.yaml`, `ecs_platform/repository/schema.sql`. This guide operationalizes and extends `docs/03-development/operations/RECOVERY_RUNBOOK.md` (the authoritative source). Documentation only.

---

## 1. What to back up

| Store | Source of record? | Backup method | Priority |
|---|---|---|---|
| **`postgres` evidence repository** (`ecs_repository`) | **Yes** — evidence, audit_log, observations, frameworks, controls, lineage | `scripts/backup/backup.sh` (pg_dump custom format) | **P1** |
| **`minio` object store** (`ecs-evidence`) | **Yes** — raw artifact files | object-store snapshot / `mc mirror` | **P1** |
| **`pgvector`** (`ecs_vectors`) | No — derived embeddings | `backup.sh --vector` (optional; rebuildable) | P2 |
| **`redis`** | No — cache/queue | none needed (rebuildable; RDB `--save 60 1`) | P3 |
| `config/*.yaml` + `.env` | Yes — config | version control + secret store | P1 |

> The repository + object store together are the full system of record. Vectors and cache are **derived** and can be rebuilt.

---

## 2. Backup procedure

```bash
# Repository only (custom-format, checksummed, verified, pruned)
scripts/backup/backup.sh
# Repository + vector store
scripts/backup/backup.sh --vector
# Custom location / retention / also plain SQL
scripts/backup/backup.sh --out /var/backups/ecs --retention 30 --plain
```
Produces in `BACKUP_DIR` (default `<repo>/backups`): `ecs_repository_<UTC>.dump`, `.dump.sha256`, `.log` (+ `.sql` with `--plain`). The script **verifies** each archive (`pg_restore --list`) and **prunes** older than `BACKUP_RETENTION_DAYS` (default 14).

**Connection vars** (same as ECS, from `config/repository.yaml`): `ECS_REPO_PG_HOST/PORT/DATABASE/USER/PASSWORD`. Against Docker: exec in the `postgres` container or set host to the published `:5433`.

**Object store backup (operator-owned):**
```bash
mc alias set ecs http://localhost:9002 ecs_minio ecs_minio_secret
mc mirror --overwrite ecs/ecs-evidence /var/backups/ecs/objects/$(date -u +%Y%m%dT%H%M%SZ)
```

**Recommended schedule:** nightly cron / k8s CronJob → durable, encrypted, off-host storage. Keep DB dump and object-store snapshot from the same window aligned.

---

## 3. Restore procedure

```bash
# Latest, over live (maintenance window) — prompts to retype DB name unless --yes
scripts/restore/restore.sh --latest --clean
# Specific file
scripts/restore/restore.sh --file backups/ecs_repository_20260614T130000Z.dump --clean
# Into a fresh DB (safest)
scripts/restore/restore.sh --latest --create --db ecs_repository_recovered
# Vector store
scripts/restore/restore.sh --latest --label vectors
```
Safety: checksums verified when `.sha256` present; `--clean` drops existing objects first; `--jobs N` parallelizes.

**Post-restore steps:** (1) stop/maintenance app; (2) restore; (3) restore matching object-store snapshot; (4) start app — `init_schema()` idempotently reconciles additive columns; (5) confirm dashboards + audit/observation counts.

---

## 4. Validation drill (no production impact)

```bash
scripts/backup/validate_backup_restore.sh
```
Backs up → creates disposable temp DB → restores → compares row counts (`evidence`, `audit_log`, `observations`, `frameworks`, `controls`) → drops temp DB. **Exit 0 = PASS.** Run on a cadence and after any schema change. `--keep` to inspect.

---

## 5. RPO / RTO

| Metric | Driver | Recommendation |
|---|---|---|
| **RPO** | Backup frequency | Nightly = 24h; tighten with WAL archiving / more frequent dumps |
| **RTO** | Dump size + restore parallelism (`--jobs`) + object-store mirror | Measure during drill; document achieved RTO |

---

## 6. Rebuild of derived stores

- **Vector store:** re-embed from the repository (no separate restore needed if repo is intact).
- **Redis:** auto-rebuilds; or flush and warm.

---

## 7. Security

- Backups contain **sensitive evidence + audit data** — encrypt at rest, access-control `BACKUP_DIR`, same classification as production DB.
- Scripts never print passwords (`PGPASSWORD` in-process only).
- Keep `.sha256` sidecars with dumps to detect tampering.

---

## 8. Quick reference

| Situation | Command |
|---|---|
| Accidental data loss | `restore.sh --latest --clean` (maintenance) |
| Corrupt DB | `restore.sh --latest --create --db ecs_repository_new`, repoint |
| Migrate host | `backup.sh` → copy → `restore.sh --file ... --create` |
| Verify backup | `pg_restore --list <file>.dump` or validation drill |

See `ECS_DISASTER_RECOVERY_PLAN.md` for full-site recovery.
