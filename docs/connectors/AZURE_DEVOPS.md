# Integration Guide — Azure DevOps

**Grounding:** `config/integrations.yaml` (`azure_devops`), `ecs_platform/ingestion.py`. Part of [Integrations Index](_legacy_INTEGRATIONS_index.md). Interface-complete, `enabled: false` by default.

## Architecture
ECS connector → Azure DevOps API (`${AZDO_URL}`, org `${AZDO_ORG}`) → pulls SDLC/delivery objects → evidence → repository. Source for AppSec/AI-SDLC delivery evidence.

## Authentication
`auth_type: pat`; `AZDO_TOKEN` (Personal Access Token). No secrets hardcoded.

## Authorization
PAT scoped to read repos/pipelines/PRs (least privilege). ECS RBAC governs visibility.

## Data Flow
`AZDO API → sync_connector() → evidence (source_system=azure_devops) → maps → dashboards`.

## Objects (collect)
`repositories, pull_requests, pipelines, releases`.

## Evidence Sources
PR approvals, pipeline runs, releases → secure-SDLC/change evidence; AI-SDLC stage gates.

## Synchronization & Scheduling
Pull via Connector Scheduler; history in `sync_runs`.

## Error Handling
`timeout_sec=10`, `max_retries=1`; failures → Integration Health + [Connector Failure Playbook](../operations/ECS_CONNECTOR_FAILURE_PLAYBOOK.md).

## Security & Audit Logging
TLS; PAT from env/vault (rotate); access logged in `audit_log`.

## Future UAT / PROD Configuration
- **UAT:** `AZDO_URL`, `AZDO_ORG`, `AZDO_TOKEN`, `ECS_AZDO_ENABLED=true`.
- **PROD:** vaulted PAT with rotation, least-privilege scope, monitored sync.

## YAML Mapping
```yaml
azure_devops:
  enabled: ${ECS_AZDO_ENABLED:-false}
  type: azure_devops
  base_url: ${AZDO_URL:-https://dev.azure.com}
  organization: ${AZDO_ORG:-}
  auth_type: pat
  token_env: AZDO_TOKEN
  verify_ssl: true
  collect: [repositories, pull_requests, pipelines, releases]
```
