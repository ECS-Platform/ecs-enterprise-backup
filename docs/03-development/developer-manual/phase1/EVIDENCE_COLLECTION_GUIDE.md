# ECS Evidence Collection Orchestrator Guide

**Module:** Audit Intelligence — Milestone 2 (Evidence Collection Orchestrator)
**Package:** `modules/audit_intelligence/`

---

## 1. Purpose

Turn a **scope** into evidence:

```
Asset / Application / Environment / Framework / Technology / Entire Bank
  -> applicable controls (via the mapping engine)
  -> execute each control through the predefined-query engine
  -> capture evidence metadata + status
  -> run summary + audit trail
```

The orchestrator is the coordination layer **on top of** the (production)
predefined-query engine. It adds **no execution logic** and changes **no
connector** — it calls `predefined_queries_engine.run_predefined_query()` and
records normalized results.

---

## 2. Architecture

```
modules/audit_intelligence/
  models.py                              # EvidenceRun, EvidenceRecord, statuses
  engines/evidence_orchestrator.py       # scope -> run -> execute -> status/retry/audit
  services/evidence_service.py           # serialized facade (also ties in validation)
```

**Execution is pluggable:** `execute_run(run_id, executor=…)` accepts an
`executor(control_id, user) -> result_dict`. The default is the real engine; tests
inject a mock so runs are fully offline. Non-executable controls (no live
connector in this environment) are marked `Configuration Required` **without**
attempting a connection, so a run never crashes.

**State:** in-memory run store (`get_run`, `list_runs`, `reset_runs`). Durable
persistence is the Evidence Repository (Milestone 3).

---

## 3. Statuses

| Status | Meaning |
|---|---|
| `Queued` | created, not yet executed |
| `Running` | execution in progress |
| `Completed` | all records succeeded |
| `Failed` | all records failed |
| `Partially Completed` | some succeeded, some did not |
| `Connector Missing` | driver/connector unavailable (per record) |
| `Configuration Required` | control not enabled / not configured (per record) |
| `Retry` | (reserved) record queued for retry |
| `Cancelled` | run/record cancelled |

---

## 4. API (`evidence_orchestrator`)

| Function | Purpose |
|---|---|
| `resolve_scope(kind, value)` | control_ids for `technology`/`framework`/`control`/`asset`/`application`/`environment`/`all` |
| `create_run(...)` | build a `Queued` run |
| `execute_run(run_id, executor=…, user=…)` | execute queued records |
| `retry_failed(run_id, executor=…)` | re-run only failed/connector/config records |
| `cancel_run(run_id)` | cancel queued/running records |
| `run_scope(...)` | create + execute in one call |
| `enqueue_scheduled_run(...)` / `due_runs()` | scheduler hooks (enqueue without executing; list queued) |
| `get_run` / `list_runs` / `reset_runs` | run store access |

### Service facade (`evidence_service`)

`start_run(...)`, `get_run(id)`, `list_runs()`, `retry_run(id)`, `cancel_run(id)`,
`validate_run(id)`, `run_and_validate(...)` — all return serialized dicts.

---

## 5. Usage

```python
from modules.audit_intelligence.services import evidence_service as svc

# Run all NGINX controls and validate the evidence:
result = svc.run_and_validate(scope_kind="technology", scope_value="NGINX",
                              requested_by="alice")
result["run"]["summary"]              # counts by status
result["validation"]["compliance"]    # compliance % + evidence quality
```

Scheduler pattern (decoupled enqueue/execute):

```python
from modules.audit_intelligence.engines import evidence_orchestrator as orch
run = orch.enqueue_scheduled_run(scope_kind="framework", scope_value="PCI DSS", schedule_id="nightly")
# ... later, a worker: for r in orch.due_runs(): orch.execute_run(r.run_id)
```

---

## 6. Tests

`tests/test_evidence_orchestrator.py`, `tests/test_evidence_service.py` — scoping,
statuses, retry, cancel, audit trail, scheduler hooks, exception isolation,
non-executable handling. Offline (mock executor).

---

## 7. Assumptions & limitations

- **`application` / `environment` scopes** currently resolve to *all controls*
  because assets are not yet persisted with app/env linkage (Milestone 3 narrows
  this using the asset inventory). Documented assumption.
- In-memory runs only (no persistence yet); durable storage is Milestone 3.
- Retry re-runs failed/connector/config records that are executable; it does not
  implement backoff/scheduling (an external scheduler owns cadence).
