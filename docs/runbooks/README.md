# ECS Runbooks

Focused incident runbooks for ECS operations. Each runbook is symptom → diagnose
→ remediate → verify.

> Many operational runbooks already live in
> [`../operations/`](../operations/README.md). This folder adds the **focused
> failure runbooks** that were previously scattered, and links to the existing
> ones so responders have a single entry point. Day-2 operations overview:
> [`../operations/OPERATIONS_MANUAL.md`](../operations/OPERATIONS_MANUAL.md).

## Runbook index

| Scenario | Runbook |
|----------|---------|
| Connector failure | [`../operations/CONNECTOR_TROUBLESHOOTING_RUNBOOK.md`](../operations/CONNECTOR_TROUBLESHOOTING_RUNBOOK.md) · [`../operations/ECS_CONNECTOR_FAILURE_PLAYBOOK.md`](../operations/ECS_CONNECTOR_FAILURE_PLAYBOOK.md) |
| Scheduler failure | [`SCHEDULER_FAILURE_RUNBOOK.md`](SCHEDULER_FAILURE_RUNBOOK.md) |
| Evidence upload failure | [`EVIDENCE_UPLOAD_FAILURE_RUNBOOK.md`](EVIDENCE_UPLOAD_FAILURE_RUNBOOK.md) |
| DB Agent failure | [`DB_AGENT_FAILURE_RUNBOOK.md`](DB_AGENT_FAILURE_RUNBOOK.md) |
| LLM / prompt execution failure | [`LLM_PROMPT_FAILURE_RUNBOOK.md`](LLM_PROMPT_FAILURE_RUNBOOK.md) |
| Config validation failure | [`CONFIG_VALIDATION_FAILURE_RUNBOOK.md`](CONFIG_VALIDATION_FAILURE_RUNBOOK.md) |
| Degraded readiness (`/readyz` 503) | [`DEGRADED_READINESS_RUNBOOK.md`](DEGRADED_READINESS_RUNBOOK.md) |
| Production rollback | [`../operations/ROLLBACK_RUNBOOK.md`](../operations/ROLLBACK_RUNBOOK.md) · [`../operations/ECS_ROLLBACK_PROCEDURE.md`](../operations/ECS_ROLLBACK_PROCEDURE.md) |
| Backup / recovery | [`../operations/RECOVERY_RUNBOOK.md`](../operations/RECOVERY_RUNBOOK.md) · [`../operations/ECS_BACKUP_AND_RECOVERY_GUIDE.md`](../operations/ECS_BACKUP_AND_RECOVERY_GUIDE.md) |
| Disaster recovery | [`../operations/ECS_DISASTER_RECOVERY_PLAN.md`](../operations/ECS_DISASTER_RECOVERY_PLAN.md) |

## Health & signals

- Liveness: `GET /healthz` — process up (no I/O).
- Readiness: `GET /readyz` — 200 ready / 503 degraded (checks PostgreSQL).
- Connector health: `GET /api/platform/health`, `GET /api/audit/integrations/health`.
- Monitoring thresholds: [`../operations/ECS_PRODUCTION_MONITORING_GUIDE.md`](../operations/ECS_PRODUCTION_MONITORING_GUIDE.md).
