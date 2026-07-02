# ECS Scheduler Reference

**Type:** Operations scheduler architecture. **No code/UI/DB changes.** **Grounding:** `/mvp/scheduler`, `/mvp/platform/scheduler`, `scheduler_intelligence` engine, `ecs_platform/ingestion.py` (`sync_connector`), `sync_runs` table, `config/integrations.yaml`. Inferred items marked **[Inferred/Target]**.

---

## Purpose
Automate recurring evidence collection and governance jobs so controls stay current without manual effort. Surfaces success rate, job counts, and failures (KPIs on Scheduler screen).

## Scheduler types

| Type | What it runs | Backed by |
|---|---|---|
| **Evidence Scheduler** | Connector pulls → evidence into repo | `sync_connector()`, `sync_runs` |
| **Assessment Scheduler** | Recompute coverage/readiness | governance/completeness engines |
| **Framework Scheduler** | Per-framework refresh cycles | framework engines **[Inferred/Target]** |
| **Connector Scheduler** | Per-connector sync cadence | `config/integrations.yaml` schedules |
| **Notification Scheduler** | Alerts (expiring/failed) | notification layer **[Inferred/Target]** |
| **Workflow Scheduler** | Periodic review / re-attestation triggers | workflow engine **[Inferred/Target]** |
| **AI Scheduler** | RAG reindex / embedding refresh | `reindex_evidence()` **[Inferred/Target schedule]** |

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
