# Integration Guide — Microsoft Teams

**Grounding:** `config/integrations.yaml` (`teams`), `ecs_platform/ingestion.py`. Part of [Integrations Index](_legacy_INTEGRATIONS_index.md). Interface-complete, `enabled: false` by default.

## Architecture
ECS connector → Microsoft Graph (`${MS_GRAPH_URL}`) → pulls governance channel/approval/meeting artifacts → evidence → repository.

## Authentication
`auth_type: oauth2_client_credentials`; `MS_TENANT_ID` + `MS_CLIENT_ID` + `MS_CLIENT_SECRET`. No secrets hardcoded.

## Authorization
Azure AD app with Graph ChannelMessage/Meeting read scopes (least privilege). ECS RBAC governs visibility.

## Data Flow
`Graph API → sync_connector() → evidence (source_system=teams) → maps → dashboards`.

## Objects (collect)
`governance_channels, approval_messages, meeting_artifacts`.

## Evidence Sources
Approval messages, governance channel records, meeting artifacts → decision/approval evidence (governance, CAB-adjacent).

## Synchronization & Scheduling
Pull via Connector Scheduler; history in `sync_runs`.

## Error Handling
`timeout_sec=10`, `max_retries=1`; failures → Integration Health + [Connector Failure Playbook](../operations/ECS_CONNECTOR_FAILURE_PLAYBOOK.md).

## Security & Audit Logging
TLS; OAuth2 secret from env/vault (rotate); access logged in `audit_log`.

## Future UAT / PROD Configuration
- **UAT:** tenant/client/secret, `ECS_TEAMS_ENABLED=true`.
- **PROD:** vaulted secret, scoped Graph permissions, monitored sync.

## YAML Mapping
```yaml
teams:
  enabled: ${ECS_TEAMS_ENABLED:-false}
  type: teams
  base_url: ${MS_GRAPH_URL:-https://graph.microsoft.com/v1.0}
  auth_type: oauth2_client_credentials
  tenant_id_env: MS_TENANT_ID
  client_id_env: MS_CLIENT_ID
  client_secret_env: MS_CLIENT_SECRET
  verify_ssl: true
  collect: [governance_channels, approval_messages, meeting_artifacts]
```
