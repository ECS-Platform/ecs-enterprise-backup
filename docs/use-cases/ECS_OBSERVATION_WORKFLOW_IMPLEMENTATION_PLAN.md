# ECS Observation Workflow Implementation Plan

**Mode:** READ-ONLY / ANALYSIS / DOCUMENTATION. **No code changes. No commits.** **Grounding:** `app/observations/store.py`, `ecs_platform/repository/repository.py` (`upsert/get/close/reopen/list_observation`), `ecs_platform/repository/schema.sql` (`observations`), `app/main.py` (hydrate-on-startup, persist-on-close/reopen), `modules/shared/services/ecs_state.py` (`missing_evidence_registry`, `closed_observations`).

> **Key correction:** durable persistence is **already implemented** as a best-effort write-through store, **gated by `OBSERVATIONS_DURABLE_ENABLED` (default FALSE)**. This is an **enablement + validation** plan, not a from-scratch build.

---

## 1. Current state (VERIFIED)

- **In-memory primary:** `ecs_state.missing_evidence_registry` (open/active) + `ecs_state.closed_observations` (closed) drive all dashboards/workflows.
- **Durable write-through (flag-gated):** `app/observations/store.py`
  - `persist_observation()` — upsert create/update (+ `observation.create/update` audit)
  - `persist_close()` / `persist_reopen()` — durable close/reopen
  - `hydrate_into_memory()` — repopulate memory from Postgres on startup (memory wins on conflict)
  - `migrate_memory_to_durable()` — one-time idempotent migration
- **Already wired in `app/main.py`:** startup hydration + persist on close/reopen, all behind the flag.
- **Repository methods exist:** `upsert_observation`, `get_observation`, `close_observation`, `reopen_observation`, `list_observations`.
- **Schema:** `observations` table (Phase-4 additive columns: `framework, control_id, severity, remediation_plan, closed_by/at, comments JSONB`).
- **Audit:** `observation.*` events via `app/audit/service.py` (`AuditRecord`, `prev_hash` chain).

## 2. Durable state design (as implemented — to be activated)

- **Design guarantees:** flag-off = no-ops (behaves as before); best-effort (errors swallowed, never breaks a workflow); reuses `EvidenceRepository` + `AuditService` (no new persistence/audit framework).
- **Conflict policy:** in-memory wins for the current process; hydration only fills entries not already in memory.
- **Activation:** set `OBSERVATIONS_DURABLE_ENABLED=true`; run `migrate_memory_to_durable()` once; restart to validate hydration.

## 3. Workflow transitions (durable-backed)

```
(create) Open/Pending Upload ──persist_observation──► observations(status=Open)
   │ update (owner/severity/remediation) ─persist_observation(update)─► row updated
   │ close (auditor / auto on control closure) ─persist_close──► status=Closed, closed_by/at
   └ reopen ─persist_reopen──► status=Open
startup ─hydrate_into_memory──► memory repopulated from rows
```
Each transition emits an `observation.*` audit event with `before/after_state` + `request_id`.

## 4. Audit trail requirements

| Requirement | Mechanism (present) |
|---|---|
| Tamper-evident chain | `audit_log.prev_hash` |
| Who/when/what | `actor`, `created_at`, `action`, `resource=observation_id` |
| Before/after | `before_state` / `after_state` JSONB |
| Correlate request | `request_id`, `auth_source="workflow"` |
| Survive restart | `hydrate_into_memory()` |

## 5. Implementation plan (enablement)

| Step | Action | Effort |
|---|---|---|
| 1 | Enable `OBSERVATIONS_DURABLE_ENABLED=true` in UAT env | 0.25d |
| 2 | Run `migrate_memory_to_durable()` (idempotent) | 0.25d |
| 3 | Validate restart hydration (counts match, dashboards unchanged) | 1d |
| 4 | Validate `observation.*` audit events + hash chain | 0.5d |
| 5 | Regression: close/reopen/auto-close paths with flag ON | 1d |
| 6 | Enable in PROD after sign-off; document runbook | 0.5d |
| | **Total** | **~3.5 eng-days** |

**Technical risk:** Low (best-effort, flag-gated, additive). **Residual:** in-memory-wins means a process holding stale memory won't be overwritten by DB — acceptable per design; document operationally.

## Cross-references
- [Engineering Gap Analysis (P1-05)](ECS_P1_ENGINEERING_GAP_ANALYSIS.md) · [Workflow Validation](../testing/ECS_WORKFLOW_VALIDATION_REPORT.md) · [Data Architecture](../architecture/ECS_DATA_ARCHITECTURE_REFERENCE.md) · [RAF Plan](ECS_RAF_IMPLEMENTATION_PLAN.md)
