# Runbook: Scheduler Failure

Scheduled evidence collection is not running, failing, or stuck.

> Reference: [`../operations/ECS_SCHEDULER_REFERENCE.md`](../operations/ECS_SCHEDULER_REFERENCE.md)
> · [`../scheduler/scheduler_runtime_flow.md`](../developer-manual/phase1/scheduler/scheduler_runtime_flow.md)
> · executor: `modules/audit_intelligence/services/scheduler_execution.py`,
> planner: `asset_scheduler.py`.

## Symptoms
- No new evidence from scheduled runs; jobs stuck in queue; dead-letter growth;
  connector jobs skipped; run errors in logs (`PredefinedQueries` / scheduler tags).

## Diagnose
1. Confirm the app is healthy: `GET /healthz` (200), `GET /readyz`.
2. Inspect the plan (no execution): `GET /api/audit/scheduler/plan`.
3. Dry-run (no queries, no connector calls): `POST /api/audit/scheduler/dry-run`.
4. Execution history: `GET /api/audit/scheduler/history`.
5. Dead-letter queue: `list_dead_letters()` in `scheduler_execution.py` (in-process).
6. Connector readiness for planned jobs: `GET /api/audit/integrations/health`.

## Common causes & remediation
| Cause | Fix |
|-------|-----|
| Connector job skipped | Connector execution is opt-in: set `ECS_CONNECTOR_EXECUTION_ENABLED=true` **and** configure the adapter (see connector runbook). |
| Target unreachable / auth | Fix credentials/host; re-run. Non-retryable statuses (`auth_error`,`not_configured`) won't self-heal. |
| Jobs in dead-letter | Fix root cause, then `requeue_dead_letter()`. DLQ is in-process — a restart clears it (re-plan). |
| Baseline executor not injected | `execute_plan` needs an injected executor outside production; verify wiring. |
| Timeouts | Adjust `scheduler.timeout_sec` / connector `timeout_sec` in `config/environments/<env>.yaml`. |

## Verify
- `POST /api/audit/scheduler/dry-run` returns `ok: true` with expected job counts.
- New evidence appears in the repository / readiness views.

## Escalate
If the scheduler process is wedged, restart the app (state re-plans from config);
capture logs + `X-Request-ID`. See [`../operations/ECS_SUPPORT_RUNBOOK.md`](../operations/ECS_SUPPORT_RUNBOOK.md).
