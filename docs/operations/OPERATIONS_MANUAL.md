# ECS Operations Manual (Day-2)

The single entry point for running ECS in production/UAT: health checks, logs,
scheduler operations, and per-component failure handling. Deep procedures live in
the existing runbooks — this manual is the map.

> **Reuse note.** Do not duplicate the runbooks below; this consolidates day-2
> operations and links out.

---

## Health & readiness
| Check | Endpoint | Meaning |
|-------|----------|---------|
| Liveness | `GET /healthz` | Process up (no I/O) |
| Readiness | `GET /readyz` | 200 ready / 503 degraded (checks PostgreSQL) |
| App health | `GET /api/audit/health` | Application-level status |
| Connector health | `GET /api/platform/health`, `GET /api/audit/integrations/health` | Config-based connector health |

Monitoring thresholds & golden signals: [`ECS_PRODUCTION_MONITORING_GUIDE.md`](ECS_PRODUCTION_MONITORING_GUIDE.md).

## Logs
- ECS logs to stdout with module tags (`ecs_logging`); startup logs the resolved
  `Security mode:` + `Active environment:`. Correlate with `X-Request-ID`.
- Aggregation on GCP: [`../deployment/GCP_DEPLOYMENT_GUIDE.md`](../deployment/GCP_DEPLOYMENT_GUIDE.md) §9.

## Core day-2 references
- Primary ops runbook: [`ECS_OPERATIONS_RUNBOOK.md`](ECS_OPERATIONS_RUNBOOK.md)
- Alternate ops runbook: [`ecs_runbook.md`](ecs_runbook.md)
- L1/L2 triage: [`ECS_SUPPORT_RUNBOOK.md`](ECS_SUPPORT_RUNBOOK.md)
- Monitoring: [`ECS_PRODUCTION_MONITORING_GUIDE.md`](ECS_PRODUCTION_MONITORING_GUIDE.md)
- Scheduler reference: [`ECS_SCHEDULER_REFERENCE.md`](ECS_SCHEDULER_REFERENCE.md)

## Failure handling (focused runbooks)
| Component | Runbook |
|-----------|---------|
| Connector | [`CONNECTOR_TROUBLESHOOTING_RUNBOOK.md`](CONNECTOR_TROUBLESHOOTING_RUNBOOK.md) · [`ECS_CONNECTOR_FAILURE_PLAYBOOK.md`](ECS_CONNECTOR_FAILURE_PLAYBOOK.md) |
| Scheduler | [`../runbooks/SCHEDULER_FAILURE_RUNBOOK.md`](../runbooks/SCHEDULER_FAILURE_RUNBOOK.md) |
| Evidence upload | [`../runbooks/EVIDENCE_UPLOAD_FAILURE_RUNBOOK.md`](../runbooks/EVIDENCE_UPLOAD_FAILURE_RUNBOOK.md) |
| DB Agent | [`../runbooks/DB_AGENT_FAILURE_RUNBOOK.md`](../runbooks/DB_AGENT_FAILURE_RUNBOOK.md) |
| LLM / prompt | [`../runbooks/LLM_PROMPT_FAILURE_RUNBOOK.md`](../runbooks/LLM_PROMPT_FAILURE_RUNBOOK.md) |
| Config validation | [`../runbooks/CONFIG_VALIDATION_FAILURE_RUNBOOK.md`](../runbooks/CONFIG_VALIDATION_FAILURE_RUNBOOK.md) |
| Degraded readiness | [`../runbooks/DEGRADED_READINESS_RUNBOOK.md`](../runbooks/DEGRADED_READINESS_RUNBOOK.md) |

## Lifecycle operations
- Deploy: [`DEPLOYMENT_RUNBOOK.md`](DEPLOYMENT_RUNBOOK.md) · GCP: [`../deployment/GCP_DEPLOYMENT_GUIDE.md`](../deployment/GCP_DEPLOYMENT_GUIDE.md)
- Rollback: [`ROLLBACK_RUNBOOK.md`](ROLLBACK_RUNBOOK.md) · [`ECS_ROLLBACK_PROCEDURE.md`](ECS_ROLLBACK_PROCEDURE.md)
- Backup/recovery: [`ECS_BACKUP_AND_RECOVERY_GUIDE.md`](ECS_BACKUP_AND_RECOVERY_GUIDE.md) · [`RECOVERY_RUNBOOK.md`](RECOVERY_RUNBOOK.md)
- DR: [`ECS_DISASTER_RECOVERY_PLAN.md`](ECS_DISASTER_RECOVERY_PLAN.md)
- Go-live: [`ECS_GO_LIVE_CHECKLIST.md`](ECS_GO_LIVE_CHECKLIST.md) · [`ECS_PRODUCTION_CHECKLIST.md`](ECS_PRODUCTION_CHECKLIST.md)

## All runbooks
See [`../runbooks/README.md`](../runbooks/README.md) for the complete index.
