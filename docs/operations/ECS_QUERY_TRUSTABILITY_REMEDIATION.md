# ECS Query Execution Trustability Remediation

**Objective:** the UI execution state must always reflect actual runtime state — never a stale URL notice.
**Constraint:** implement and stop. No commits.
**Date:** 2026-06-22

> **Environment note.** During an unrelated host disk-full recovery, the working directory was
> re-cloned from `ECS-Platform/ecs-enterprise-backup.git` (HEAD `830a91c`). That re-clone discarded
> the previous uncommitted work, including the root-cause doc this task referenced. This remediation
> was therefore re-derived from the known root cause and implemented on the current codebase. Live
> HTTP validation against the demo stack is **pending Docker restart**; the logic and the template
> banner decision were validated offline (see §5).

---

## 1. Root cause being remediated

The predefined-query **detail** page rendered its top banner from the `notice` URL query parameter
produced by the `/run` redirect. Because that notice is persisted in the address bar, a failure
message (e.g. *"SonarQube not reachable"* / *"psycopg2 not installed"* / *"Could not connect"*) would
**survive** the condition that produced it and could appear **alongside** a successful Result tab and
generated evidence — a contradictory, untrustworthy state.

Authoritative runtime signals were already available on the control object but were not driving the
banner:
- `latest_execution` (status, rows, duration, timestamp, error_message)
- `latest_result` (evidence_id)
- `execution_history`

---

## 2. Remediation design

A single source of truth, `derive_runtime_state(control)`, now computes the banner from runtime
signals only. The route reconciles the stale notice against it; the template renders from it.

**Decision rules implemented**

| Rule | Implementation |
|------|----------------|
| 1. Successful execution overrides stale failure notices | `suppress_notice=True` on success; route sets `ctx["notice"]=""` |
| 2. After success, clear stale notice / connector / dependency / execution banners | success branch is exclusive; capability/prep warning guarded by `not runtime.success` |
| 3. Status derived from `latest_execution` / `latest_result` / `execution_history`, not URL notice | `derive_runtime_state()` reads only those fields |
| 4. On success show SUCCESS · Rows · Duration · Evidence ID · Timestamp | success banner renders all five |
| 5. On failure show Exception · Connector · Failure Point · Suggested Action | failure banner renders all four |
| 6. Contradictory states never co-occur (e.g. SUCCESS + "SonarQube unreachable") | `if/elif` exclusivity + notice suppression on success |
| 7. If evidence exists → status = SUCCESS regardless of stale notices | `succeeded = (status=="success") or has_evidence` |

---

## 3. Files changed

| File | Change |
|------|--------|
| `modules/operations/engines/predefined_queries_engine.py` | Added `derive_runtime_state()` + `_runtime_suggested_action()` — the single source of truth for the banner |
| `modules/shared/routes/routes_mvp.py` | Detail route now builds `runtime` and **suppresses the stale notice** (`ctx["notice"]=""`) on success |
| `modules/operations/templates/mvp_predefined_query_detail.html` | Banner rewritten to render from `runtime` (success / failure / fallback); capability/prep warning guarded so it cannot co-exist with a success |

No API routes, DB schema, connectors, or execution logic were modified.

### Core logic

```python
has_evidence = bool(lr.get("evidence_id"))
succeeded = str(le.get("status", "")).lower() == "success" or has_evidence   # Rule 7
status = "SUCCESS" if succeeded else ("FAILED" if le else "NOT_EXECUTED")
# failure_point classified from error_message: Connector connection / Driver-dependency /
# Execution gate-allow-list / Query execution
return {..., "error_message": "" if succeeded else err, "suppress_notice": succeeded}
```

### Route reconciliation

```python
runtime = derive_runtime_state(control)
ctx["runtime"] = runtime
if runtime["suppress_notice"]:
    ctx["notice"] = ""          # SUCCESS wipes the stale failure notice (Rules 1, 2, 6)
```

### Template banner (mutually exclusive)

```
{% if runtime and runtime.success %}      → SUCCESS · Rows · Duration · Evidence ID · Timestamp
{% elif runtime and runtime.failed %}     → Exception · Connector · Failure point · Suggested action
{% elif notice %}                          → transient action notice (only when never executed)
```

---

## 4. Failure-point classification (for Rule 5)

| Error text contains | Failure Point | Suggested Action |
|---------------------|---------------|------------------|
| reachable / connect / refused / timeout / no route / unavailable / not connected | Connector connection | Confirm the target service is running and reachable, then re-run |
| not installed / driver | Driver / dependency | Install the required driver, then re-run |
| not enabled / allow-list / unsupported | Execution gate / allow-list | Enable this control for live execution, then re-run |
| (other) | Query execution | Review the query and target permissions, then re-run |

---

## 5. Validation — OS-001, DB-001, APP-001

`derive_runtime_state()` imports cleanly and **no linter errors** were introduced. Two offline
harnesses were run (Docker was down, so live HTTP is pending — see note).

### 5a. Deriver unit checks

| Scenario | Result |
|----------|--------|
| OS-001 success + evidence | `SUCCESS`, suppress_notice=True ✅ |
| DB-001 stale "Could not connect" **but evidence exists** | `SUCCESS`, error cleared, suppress_notice=True ✅ (Rule 7) |
| APP-001 connect failure, no evidence | `FAILED`, failure_point=`Connector connection`, action set ✅ |
| APP-001 success | `SUCCESS`, evidence_id surfaced ✅ |
| never executed | `NOT_EXECUTED`, no suppression ✅ |

### 5b. Banner decision (route suppression + template if/elif), the critical contradiction test

| Scenario (notice in URL) | Rendered banner | Contradiction? |
|--------------------------|-----------------|----------------|
| **APP-001 success** + stale `"SonarQube not reachable"` notice | `SUCCESS Rows:1 Dur:2638ms Evidence:PQ-EVD-000001 …` — stale text **absent** | **None** ✅ (Rules 1 & 6) |
| **DB-001** evidence + stale `"Could not connect"` notice | `SUCCESS … Evidence:PQ-EVD-000002` — "Could not connect" **absent** | **None** ✅ (Rule 7) |
| **APP-001** genuine failure, no evidence | `FAILED Exception:… Connector:SonarQube FailurePoint:Connector connection Action:…` | n/a ✅ (Rule 5) |
| **OS-001** success | `SUCCESS Rows:3 Dur:120ms Evidence:PQ-EVD-000010 …` | n/a ✅ (Rule 4) |

**Result: ALL PASS.** "SUCCESS" and "SonarQube unreachable" can no longer be shown together.

### 5c. Pending live validation (after Docker restart)
```
docker compose --profile demo-connectors up -d
# then, in ecs-ecs-1, run each control and reload the detail page:
#   OS-001, DB-001, APP-001 → expect SUCCESS banner with rows/duration/evidence,
#   and NO residual "not reachable" / "psycopg2" / "Could not connect" text.
```

---

## 6. Outcome

- The detail banner is now a pure function of durable runtime state.
- Stale failure notices are dropped the moment a run succeeds or evidence exists.
- Success and failure banners are mutually exclusive — contradictory states are structurally
  impossible.
- Failures now present the actual exception, connector, failure point, and a remediation action.

**Implemented and stopped. No commit made.**
