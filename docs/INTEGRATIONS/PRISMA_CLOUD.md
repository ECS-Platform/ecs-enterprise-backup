# Integration Guide — Prisma Cloud

**Grounding:** `config/integrations.yaml` (`prisma_cloud`), `ecs_platform/ingestion.py`. Part of [Integrations Index](README.md). Interface-complete, `enabled: false` by default.

## Architecture
ECS connector → Prisma Cloud API (`${PRISMA_URL}`) → pulls CSPM findings → evidence → repository. Primary source for **Cloud Security** posture (see [Cloud Security framework](../FRAMEWORKS/CLOUD_SECURITY.md)).

## Authentication
`auth_type: prisma_credentials`; `PRISMA_ACCESS_KEY` + `PRISMA_SECRET_KEY`. No secrets hardcoded.

## Authorization
Read-only Prisma role for findings/compliance. ECS RBAC governs visibility.

## Data Flow
`Prisma API → sync_connector() → evidence (source_system=prisma) → control/framework maps → dashboards/risk`.

## Objects (collect)
`cloud_findings, compliance_violations, risk_reports`.

## Evidence Sources
Cloud misconfig findings, compliance violations, risk reports → cloud-security/VAPT evidence; feeds Risk Register + correlation.

## Synchronization & Scheduling
Pull via Connector Scheduler; history in `sync_runs`.

## Error Handling
`timeout_sec=10`, `max_retries=1`; failures → Integration Health + [Connector Failure Playbook](../operations/ECS_CONNECTOR_FAILURE_PLAYBOOK.md).

## Security & Audit Logging
TLS; env/vault-sourced keys (rotate); access logged in `audit_log`.

## Future UAT / PROD Configuration
- **UAT:** `PRISMA_URL`, access/secret keys, `ECS_PRISMA_ENABLED=true`.
- **PROD:** vaulted keys with rotation, least-privilege role, monitored sync.

## YAML Mapping
```yaml
prisma_cloud:
  enabled: ${ECS_PRISMA_ENABLED:-false}
  type: prisma
  base_url: ${PRISMA_URL:-}
  auth_type: prisma_credentials
  access_key_env: PRISMA_ACCESS_KEY
  secret_key_env: PRISMA_SECRET_KEY
  verify_ssl: true
  collect: [cloud_findings, compliance_violations, risk_reports]
```
