# ECS Observation Durability Enablement Plan

**Mode:** READ-ONLY / ANALYSIS / DOCUMENTATION. **No code changes. No commits.** **Grounding:** `app/observations/store.py`, `ecs_platform/repository/repository.py` (`upsert/get/close/reopen/list_observation`), `ecs_platform/repository/schema.sql` (`observations`), `app/main.py` (startup hydrate; persist on close/reopen), `modules/shared/services/ecs_state.py`.

> **This is an ENABLEMENT plan** — the durable write-through store already exists and is wired into `app/main.py`, gated by `OBSERVATIONS_DURABLE_ENABLED` (default FALSE). See companion: [Observation Workflow Implementation Plan](../../01-product/use-cases/ECS_OBSERVATION_WORKFLOW_IMPLEMENTATION_PLAN.md).

---

## 1. Current state
- In-memory primary read path: `ecs_state.missing_evidence_registry` (open) + `ecs_state.closed_observations` (closed).
- Durable write-through (flag-gated): `persist_observation()`, `persist_close()`, `persist_reopen()`, `hydrate_into_memory()`, `migrate_memory_to_durable()`.
- Already invoked in `app/main.py`: hydrate on startup, persist on close/reopen.
- Best-effort design: flag-off = no-ops; all functions swallow errors (never break a workflow); memory wins on conflict.
- Audit: `observation.create/update/close/reopen` via `app/audit/service.py` (hash-chained).

## 2. `OBSERVATIONS_DURABLE_ENABLED`
| Value | Behavior |
|---|---|
| unset / false / 0 / no / off (**default**) | All store functions no-op; ECS behaves exactly as before |
| 1 / true / yes / on | Write-through persistence + startup hydration + migration active |

**Set in env** per environment (UAT first, then PROD). Requires a reachable Postgres repository (already present in compose).

## 3. Migration
- Run once (idempotent, upsert-keyed by `observation_id`): `migrate_memory_to_durable()` migrates `missing_evidence_registry` + `closed_observations` into the `observations` table.
- Returns counts `{registry, closed, errors}`; safe to re-run.
- Trigger options: at controlled startup with flag ON, or a one-shot ops script invoking the function.

## 4. Validation
| Check | Expectation |
|---|---|
| Flag resolves true | `durable_observations_enabled()` → True |
| Migration counts | `registry`+`closed` match in-memory totals; `errors == 0` |
| Restart hydration | After restart, `hydrate_into_memory()` repopulates same open/closed counts; dashboards unchanged |
| Audit events | `observation.*` recorded with before/after + `prev_hash` chain intact |
| Close/reopen | New transitions persist + audit; memory and DB consistent |
| No UI change | Screens render identically (no template/CSS change) |

## 5. Rollback
- **Instant rollback:** set `OBSERVATIONS_DURABLE_ENABLED=false` and restart → store reverts to no-ops; in-memory behavior restored. No schema rollback needed (table is additive and harmless when unused).
- Persisted rows remain (no destructive change); re-enabling resumes from durable state.
- Because writes are best-effort and additive, there is **no data-loss path** from toggling the flag.

## 6. Effort & risk
| Item | Effort |
|---|---|
| Enable flag (UAT) + run migration | 0.5d |
| Validate restart hydration + audit | 1d |
| Regression (close/reopen/auto-close) | 1d |
| Enable in PROD + runbook entry | 0.5d |
| **Total** | **~3 eng-days** |

**Risk:** Low — flag-gated, additive, best-effort, instantly reversible. **Residual:** memory-wins means a long-running process won't be overwritten by DB changes from elsewhere; document operationally.

## Cross-references
- [Observation Workflow Plan](../../01-product/use-cases/ECS_OBSERVATION_WORKFLOW_IMPLEMENTATION_PLAN.md) · [Production Master Plan](../production/ECS_PRODUCTION_READINESS_MASTER_PLAN.md) · [Data Architecture](../../02-architecture/architecture/ECS_DATA_ARCHITECTURE_REFERENCE.md)
