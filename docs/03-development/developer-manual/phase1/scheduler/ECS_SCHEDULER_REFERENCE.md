# ECS Scheduler Reference

**Type:** Operations scheduler product reference. **No code/UI/DB changes.** **Grounding:** `/mvp/scheduler`, `/mvp/platform/scheduler`, `scheduler_intelligence` engine, `ecs_platform/ingestion.py` (`sync_connector`), `sync_runs` table, `config/integrations.yaml`. Inferred items marked **[Inferred/Target]**.

> **Phase-1 Scheduler Architecture (implemented planner + collection runner):**
> [`../architecture/SCHEDULER_ARCHITECTURE.md`](../architecture/SCHEDULER_ARCHITECTURE.md).
> Runtime flow:
> [`../scheduler/scheduler_runtime_flow.md`](../scheduler/scheduler_runtime_flow.md).
>
> Many “scheduler types” below are **product taxonomy / target**. Do not treat
> every row as a distinct Phase-1 worker process.

---

## Purpose
Automate recurring evidence collection and governance jobs so controls stay current without manual effort. Surfaces success rate, job counts, and failures (KPIs on Scheduler screen).

## Scheduler types

| Type | What it runs | Backed by | Phase-1 note |
|---|---|---|---|
| **Evidence / asset-driven collection** | Plan + optional execute (baseline PQE / connectors) | `asset_scheduler`, `scheduler_module`, `connector_executor` | **Implemented** — see Scheduler Architecture |
| **Evidence Scheduler (platform sync)** | Connector pulls → evidence into repo | `sync_connector()`, `sync_runs` | Platform ingestion path (config-dependent) |
| **Assessment Scheduler** | Recompute coverage/readiness | governance/completeness engines | UI/engines; not a separate cron service |
| **Framework Scheduler** | Per-framework refresh cycles | framework engines **[Inferred/Target]** | |
| **Connector Scheduler** | Per-connector sync cadence | `config/integrations.yaml` schedules | Partially via sync_runs / integrations |
| **Notification Scheduler** | Alerts (expiring/failed) | notification layer **[Inferred/Target]** | |
| **Workflow Scheduler** | Periodic review / re-attestation triggers | workflow engine **[Inferred/Target]** | |
| **AI Scheduler** | RAG reindex / embedding refresh | `reindex_evidence()` **[Inferred/Target schedule]** | Indexing may run as side-effect of enroll |

> Demo mode renders scheduler metrics deterministically. Real scheduling is driven by connector sync runs recorded in `sync_runs`.

## Execution flow

```
Schedule trigger → resolve connector/job → execute (sync_connector / engine recompute)
→ record sync_runs (started, status, counts) → ingest evidence + map controls/frameworks
→ update KPIs → emit failure alerts on error
```

## Failure handling & retry logic
- Each run logs status in `sync_runs` (success/failure + record counts).
- Failures surface on Scheduler + Integration Health screens.
- **Retry:** connector errors are retried per connector policy; persistent failures escalate via [Connector Failure Playbook](ECS_CONNECTOR_FAILURE_PLAYBOOK.md). **[Inferred/Target]** for configurable backoff/max-retries.

## Monitoring
- **Scheduler screen:** success rate, jobs run, failures.
- **Integration Health:** per-connector last-run + status.
- **sync_runs:** durable run history for audit.

## Reporting
- Scheduler success-rate trend → Trends/Governance Analytics.
- Failed jobs → Connector Failure Playbook + Risk Register (if control freshness at risk).

## Cross-references
- Connector failures: [ECS_CONNECTOR_FAILURE_PLAYBOOK.md](ECS_CONNECTOR_FAILURE_PLAYBOOK.md)
- Query execution: [ECS_PREDEFINED_QUERY_ARCHITECTURE.md](ECS_PREDEFINED_QUERY_ARCHITECTURE.md)
- Onboarding: [ECS_APPLICATION_ONBOARDING_GUIDE.md](ECS_APPLICATION_ONBOARDING_GUIDE.md)
