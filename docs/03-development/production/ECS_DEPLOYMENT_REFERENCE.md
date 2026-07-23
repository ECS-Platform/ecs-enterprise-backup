# ECS Deployment Reference

**Type:** Deployment architecture reference. **No code/UI/DB changes.** **Grounding:** `docker-compose.yml` (10 services, `sources`/`demo-connectors` profiles), `Dockerfile`, `start_ecs.sh`, `.env.example`, `config/*.yaml`, `scripts/backup/*`, `scripts/restore/*`. Builds on [docs/DEPLOYMENT_GUIDE / operations runbooks]. Inferred items marked **[Inferred/Target]**.

---

## Topology (containers)
`ecs` (FastAPI app), `postgres-demo`, `postgres` (repo `ecs_repository`), `pgvector` (`ecs_vectors`), `redis`, `minio`, plus demo connectors `ubuntu-demo`, `sonarqube-demo`, `gitea`, `jenkins`. Profiles: `sources`, `demo-connectors`. Local LLM (Ollama) runs on host, reached via `host.docker.internal`.

## Environments

| Env | Purpose | Auth | Data | Connectors | LLM |
|---|---|---|---|---|---|
| **Local** | dev/demo | DEMO_MODE | synthetic seeds | self-host on; SaaS off | Ollama local |
| **DEV** | integration dev | optional | seeded + some live | Gitea/Sonar/Jenkins | Ollama local |
| **SIT** **[Inferred/Target]** | system integration test | enabled | test data | selected SaaS (UAT creds) | local/cloud |
| **UAT** | pre-prod validation | enabled (OIDC) | UAT data | SaaS via env + `enabled:true` | local/hybrid |
| **PROD** | production | enabled (OIDC) | live | all required, vaulted secrets | local-first/hybrid |

## Deploy (local)
`./start_ecs.sh` (or `docker compose up`) builds the app image and starts services; schema is applied idempotently on startup; demo data seeds deterministically. Health: `/healthz` (liveness), `/readyz` (repo connectivity), `/api/platform/health` (connectors). See [Developer Setup](../developer-manual/DEVELOPER_SETUP_GUIDE.md).

## Environment promotion
`Local → DEV → SIT → UAT → PROD`. Promote the **same image**; change behavior only via env vars + `config/*.yaml` (`enabled`, URLs, secrets). No code change to onboard a tenant/connector. Idempotent additive schema makes forward DB changes safe.

## Rollback
Redeploy previous image tag; schema is additive (no destructive migrations) so prior app version remains compatible. Full procedure: [Rollback Procedure](../operations/ECS_ROLLBACK_PROCEDURE.md).

## Disaster recovery
RPO/RTO, failover, and restore order: [Disaster Recovery Plan](../operations/ECS_DISASTER_RECOVERY_PLAN.md) and [Recovery Runbook](../operations/RECOVERY_RUNBOOK.md).

## Backup & restore
`scripts/backup/backup.sh` (Postgres repo + pgvector + MinIO) and `scripts/restore/restore.sh`; validate with `scripts/backup/validate_backup_restore.sh`. Full guide: [Backup & Recovery](../operations/ECS_BACKUP_AND_RECOVERY_GUIDE.md).

## Go-live gates
See [Production Checklist](../operations/ECS_PRODUCTION_CHECKLIST.md) and [Go-Live Checklist](../operations/ECS_GO_LIVE_CHECKLIST.md): auth enabled, secrets vaulted, TLS, backups verified, monitoring on, connectors validated.

## Cross-references
- Operations readiness: [ECS_OPERATIONAL_READINESS_REPORT.md](../operations/ECS_OPERATIONAL_READINESS_REPORT.md)
- Security: [ECS_SECURITY_REFERENCE.md](../production/ECS_SECURITY_REFERENCE.md)
- Environment vars: [ENVIRONMENT_CONFIGURATION.md](../developer-manual/ENVIRONMENT_CONFIGURATION.md)
