# ECS Recovery Runbook — Backup, Restore & Migration Readiness

**Scope:** Operational recovery for the ECS PostgreSQL **evidence repository** (the
durable system of record: `evidence`, `audit_log`, `observations`, `frameworks`,
`controls`, lineage and mapping tables) and, optionally, the **vector store**.

**Out of scope (by design for this phase):** High availability, DR automation,
failover orchestration, monitoring/alerting, and metrics. This runbook covers
backup, restore, validation, and the schema-migration roadmap only.

> ⚠️ All commands are **destructive when restoring over a populated database**.
> Always restore drills into a *temporary* database first (see §4).

---

## 0. Prerequisites

- PostgreSQL client tools on PATH: `pg_dump`, `pg_restore`, `psql` (libpq 14+).
- Network reachability to the repository DB.
- Connection settings are read from the **same** variables ECS uses
  (`config/repository.yaml`). The scripts auto-load a local `.env` if present.

| Variable | Default | Meaning |
|---|---|---|
| `ECS_REPO_PG_HOST` | `localhost` | Repository host |
| `ECS_REPO_PG_PORT` | `5432` | Repository port |
| `ECS_REPO_PG_DATABASE` | `ecs_repository` | Repository database |
| `ECS_REPO_PG_USER` | `ecs_user` | Repository user |
| `ECS_REPO_PG_PASSWORD` | _(unset)_ | Repository password |
| `ECS_VECTOR_PG_*` | see `config/vectorstore.yaml` | Optional vector store |
| `BACKUP_DIR` | `<repo>/backups` | Where backups are written |
| `BACKUP_RETENTION_DAYS` | `14` | Prune backups older than N days |

> When running against the Docker stack, exec inside the `postgres` container or
> set `ECS_REPO_PG_HOST` to the published host/port.

---

## 1. Backup Procedure

Take a timestamped, compressed, integrity-checked backup:

```bash
# Repository only (default)
scripts/backup/backup.sh

# Repository + vector store
scripts/backup/backup.sh --vector

# Custom location / retention / also emit plain SQL
scripts/backup/backup.sh --out /var/backups/ecs --retention 30 --plain
```

**What it produces** in `BACKUP_DIR`:

- `ecs_repository_<UTC-timestamp>.dump` — canonical custom-format archive.
- `ecs_repository_<UTC-timestamp>.dump.sha256` — checksum for integrity.
- `ecs_repository_<UTC-timestamp>.log` — `pg_dump` verbose log.
- `ecs_repository_<UTC-timestamp>.sql` — *only* with `--plain`.

The script **verifies** every archive with `pg_restore --list` and **prunes**
artifacts older than `BACKUP_RETENTION_DAYS` (set `--retention 0` to disable).

**Recommended schedule (operator-owned, not automated here):** nightly via cron
or a Kubernetes CronJob invoking `backup.sh`, writing to durable off-host storage.

---

## 2. Restore Procedure

### 2a. Restore the latest backup

```bash
scripts/restore/restore.sh --latest --clean
```

### 2b. Restore a specific backup

```bash
scripts/restore/restore.sh --file backups/ecs_repository_20260614T130000Z.dump --clean
```

### 2c. Restore into a fresh/empty database

```bash
scripts/restore/restore.sh --latest --create --db ecs_repository_recovered
```

**Safety:** unless `--yes` is passed, restore **prompts** you to retype the target
DB name before proceeding. Checksums are verified when a `.sha256` sidecar exists.
`--clean` drops existing objects first (`pg_restore --clean --if-exists`).

**Vector store restore:** add `--label vectors` (uses `ECS_VECTOR_PG_*`).

### 2d. Post-restore application steps

1. Ensure ECS is **stopped** (or in maintenance) during a production restore.
2. Restore into the target DB.
3. Start ECS — `init_schema()` is idempotent and reconciles any additive columns.
4. Confirm dashboards load and observation/audit counts look correct.

---

## 3. Validation Procedure (Drill)

Prove backups are restorable **without touching production**:

```bash
scripts/backup/validate_backup_restore.sh
```

This will: take a fresh backup → create a disposable temp DB → restore into it →
compare row counts for `evidence`, `audit_log`, `observations`, `frameworks`,
`controls` (source vs restored) → drop the temp DB. Exit code `0` = **PASS**.

Use `--keep` to retain the temp DB for inspection, `--temp-db NAME` to control its
name. Run this drill on a regular cadence and after any schema change.

---

## 4. Disaster Recovery Quick Reference

| Situation | Action |
|---|---|
| Accidental data loss | `restore.sh --latest --clean` into the live DB (maintenance window). |
| Corrupt database | `restore.sh --latest --create --db ecs_repository_new`, repoint ECS. |
| Migrate to new host | `backup.sh` on old host → copy dump → `restore.sh --file ... --create` on new host. |
| Verify a backup | `pg_restore --list <file>.dump` and/or run the validation drill. |

**RPO/RTO note:** RPO is bounded by backup frequency; RTO by dump size and restore
parallelism (`restore.sh --jobs N`). Tune the operator-owned schedule accordingly.

---

## 5. Migration Assessment & Roadmap

### 5.1 Current schema management

- Single source of truth: `ecs_platform/repository/schema.sql`.
- Applied at startup by `EvidenceRepository.init_schema()`, which executes the file
  verbatim. All `CREATE TABLE` statements use `IF NOT EXISTS`.
- Schema evolution to date (e.g. Phase 4 audit/observation columns) is **additive**
  via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, making re-application idempotent.

**Strengths:** simple, idempotent, no extra tooling, safe to re-run.

**Limitations for banking-grade change control:**

- **No version ledger** — there is no record of which migration has been applied;
  drift between environments is undetectable from the DB itself.
- **No down-migrations / rollback** of schema changes.
- **Destructive changes are unmanaged** — renames, type changes, backfills, and
  data migrations cannot be expressed safely with `IF NOT EXISTS` alone.
- **No ordering guarantees** beyond file order; no per-change author/timestamp.

### 5.2 Recommended target: Alembic (adoption path — NOT implemented in this phase)

Adopt [Alembic](https://alembic.sqlalchemy.org/) as the migration framework while
keeping the current bootstrap working during transition:

1. **Baseline (no behavior change).** Add `alembic` to `requirements.txt`, run
   `alembic init migrations`, and configure `sqlalchemy.url` to read `ECS_REPO_PG_*`.
2. **Stamp existing databases.** Generate an initial revision that matches the
   *current* `schema.sql`, then `alembic stamp head` on every existing environment
   so they are marked as already-migrated (no DDL runs).
3. **New changes go through Alembic.** From this point, every schema change is a
   reviewed, versioned revision with `upgrade()`/`downgrade()`. Keep changes
   additive-first; gate destructive steps behind explicit, reviewed revisions.
4. **Switch the startup path.** Replace the `init_schema()` call with
   `alembic upgrade head` at deploy time (or a pre-start init container), and
   retain `schema.sql` only as generated documentation of the baseline.
5. **CI guardrail.** Add a check that fails if models/baseline change without a
   corresponding new revision (`alembic check`).

**Why not now:** this phase is operational hardening (backup/restore). Migrating to
Alembic touches startup and deployment and is sequenced as a **separate** change.

---

## 6. Security Notes

- Scripts never print passwords; `PGPASSWORD` is only exported in-process.
- Backups contain **sensitive evidence and audit data** — store `BACKUP_DIR` on
  encrypted, access-controlled storage and apply the same retention/classification
  policy as the production database.
- Keep checksum sidecars with their dumps to detect tampering/corruption.
