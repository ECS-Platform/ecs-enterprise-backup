# ECS Audit Intelligence — Persistence Foundation Guide

**Audience:** Developers and operators making ECS audit-intelligence state durable
(moving from in-memory demo state toward a production database).
**Status:** Foundation shipped. In-memory is the default and remains fully
supported; a SQL backend (SQLite default, Postgres-ready) is provided as a
skeleton you can enable without changing call sites.

> Cross-refs: [OBSERVATION_AND_REPOSITORY_GUIDE.md](../evidence-management/OBSERVATION_AND_REPOSITORY_GUIDE.md),
> [PRODUCTION_HARDENING_GUIDE.md](../production/PRODUCTION_HARDENING_GUIDE.md),
> [PRODUCTION_READINESS_GAP_REGISTER.md](../production/PRODUCTION_READINESS_GAP_REGISTER.md).
> Schema: [`docs/DB_SCHEMA_AUDIT_INTELLIGENCE.sql`](../DB_SCHEMA_AUDIT_INTELLIGENCE.sql).

---

## 1. Why this exists

The audit-intelligence engines keep working state in fast, dependency-free
module-level stores:

| Entity | Engine store |
|--------|--------------|
| Evidence runs (+ per-control results) | `engines/evidence_orchestrator.py` (`_RUNS`) |
| Validation results | derived per run (validation engine) |
| Observations | `engines/observation_generation.py` (`_OBSERVATIONS`) |
| Evidence versions | `engines/evidence_repository.py` (`_STORE`, `_TIMELINE`) |
| Evidence packs | assembled on demand from the repository |
| Scheduler history | `evidence_orchestrator` scheduler hooks / audit trail |

This is ideal for the demo, tests, and single-process runs, but state is lost on
restart and does not span workers. The **persistence foundation** adds a durable
store *alongside* the engines — it does not replace them — so you can adopt
durability incrementally and safely.

---

## 2. Components

```
modules/audit_intelligence/services/persistence.py
    AuditPersistence            # abstract interface (7 entities)
    InMemoryAuditPersistence    # reference impl (default; thread-safe)
    get_persistence()/set_persistence()/reset_persistence()   # pluggable provider
    *_to_dict() / *_from_dict() # serialization helpers (JSON-safe round-trip)

modules/audit_intelligence/services/sql_persistence.py
    SqlAuditPersistence         # DB-API backend (SQLite default, Postgres-ready)
    sqlite_file_factory(path)   # file-backed SQLite factory

docs/DB_SCHEMA_AUDIT_INTELLIGENCE.sql    # canonical Postgres DDL (JSONB)
tests/test_audit_persistence_foundation.py   # in-memory + SQLite tests (no live DB)
```

### Entities covered (the seven durable surfaces)
1. evidence runs — `EvidenceRun`
2. evidence results — `EvidenceRecord` (embedded in each run)
3. validation results — `ValidationResult`
4. observations — `Observation`
5. evidence versions — `EvidenceArtifact` (versioned per `evidence_key`)
6. evidence packs — manifest dicts
7. scheduler history — event dicts

> **No secrets are ever persisted.** Evidence rows carry SHA-256 hashes + short
> checksums + non-secret metadata only. Raw evidence bodies are never stored.

---

## 3. The interface

```python
from modules.audit_intelligence.services.persistence import get_persistence

store = get_persistence()                 # in-memory by default
store.save_run(run)                       # EvidenceRun
run = store.get_run(run_id)               # -> EvidenceRun | None
runs = store.list_runs()                  # newest-first
results = store.get_run_results(run_id)   # list[EvidenceRecord]

store.save_validation_results(run_id, results)
store.get_validation_results(run_id)

store.save_observation(obs); store.get_observation(id); store.list_observations()

store.append_evidence_version(artifact)   # EvidenceArtifact (auto-ordered by version)
store.get_evidence_versions(evidence_key) # ascending
store.list_evidence_latest()              # latest per key

store.save_pack(pack_id, manifest); store.get_pack(pack_id); store.list_packs()

store.record_scheduler_event(event); store.get_scheduler_history(limit=100)  # newest-first

store.counts()                            # {runs, observations, evidence_keys, packs, scheduler_events}
```

Contract: methods never raise for a missing key (return `None` / `[]`). Stored
objects are deep-copied via serialization, so mutating a caller's object after
`save_*` does not corrupt the store.

---

## 4. Choosing a backend

### In-memory (default)
Nothing to do — `get_persistence()` lazily creates an `InMemoryAuditPersistence`.
Semantically identical to the engine stores; thread-safe.

### SQLite (durable, no server)
```python
from modules.audit_intelligence.services.persistence import set_persistence
from modules.audit_intelligence.services.sql_persistence import (
    SqlAuditPersistence, sqlite_file_factory)

set_persistence(SqlAuditPersistence(sqlite_file_factory("/var/lib/ecs/audit.db")))
```
Great for a single-node deployment or local durability. Tests use in-memory SQLite
(`SqlAuditPersistence()` with no factory).

### Postgres (production target)
```python
import psycopg
from modules.audit_intelligence.services.sql_persistence import SqlAuditPersistence
from modules.audit_intelligence.services.persistence import set_persistence

_conn = psycopg.connect(os.environ["ECS_AUDIT_DB_URL"])   # from a secret manager
set_persistence(SqlAuditPersistence(lambda: _conn, paramstyle="pyformat"))
```
Apply the schema first:
```bash
psql "$ECS_AUDIT_DB_URL" -f docs/DB_SCHEMA_AUDIT_INTELLIGENCE.sql
```
The DDL is idempotent (`IF NOT EXISTS`) and uses `JSONB` documents + indexed
scalar columns. `psycopg`/`psycopg2` are **not** ECS dependencies — install them
only when enabling Postgres.

> Connection pooling, retries, and migrations tooling (e.g. Alembic) are
> deliberately out of scope for the skeleton — see the readiness register.

---

## 5. Serialization

Each model exposes `to_dict()`; the persistence module adds the inverse
(`run_from_dict`, `record_from_dict`, `validation_from_dict`,
`observation_from_dict`, `artifact_from_dict`). Deserializers are **tolerant**:
unknown keys are ignored and missing keys fall back to model defaults, so the
JSON document schema can evolve without breaking older/newer rows.

The SQL backend stores the full document as JSON(B) plus a few indexed scalar
columns (ids, `created_at`, `version`, `severity`, `status`) for efficient reads.

---

## 6. Wiring the engines to persistence (adoption path)

The foundation is intentionally decoupled so adoption is incremental and
non-breaking. Recommended pattern (not yet wired by default):

1. After `evidence_orchestrator.execute_run(...)`, call
   `get_persistence().save_run(run)` and `save_validation_results(...)`.
2. After `evidence_repository.store_evidence(...)`, mirror the returned artifact
   with `append_evidence_version(artifact)`.
3. After `observation_generation.generate_*`, call `save_observation(obs)`.
4. In the scheduler hook (`enqueue_scheduled_run`), call
   `record_scheduler_event({...})`.
5. On startup, hydrate the in-memory engines from `list_*` if you want warm state.

Keep the in-memory engines as the read/compute path for the dashboard; treat the
persistence layer as the durable system of record. Do this behind a feature flag
so the demo path is unchanged.

---

## 7. Testing

`tests/test_audit_persistence_foundation.py` runs the full interface against both
the in-memory backend and **in-memory SQLite** (parametrized), plus a file-backed
SQLite durability test — **no live database required**. Run:

```bash
PYTHONPATH=. pytest tests/test_audit_persistence_foundation.py
```

---

## 8. Known limitations (skeleton)

- Engines are **not** auto-wired to persistence yet (adoption is opt-in, §6).
- No connection pooling / retry / circuit-breaking in the SQL backend.
- No migration framework — schema is a single idempotent SQL file.
- `list_evidence_latest()` groups in Python for dialect portability (fine at
  audit volumes; a window-function view can optimize large Postgres datasets).
- Retention/archival is an operator policy (see the schema footer + gap register).
