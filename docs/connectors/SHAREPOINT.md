# Integration Guide — SharePoint

**Grounding:** `config/integrations.yaml` (`sharepoint`), `ecs_platform/ingestion.py`. Part of [Integrations Index](_legacy_INTEGRATIONS_index.md). Interface-complete, `enabled: false` by default. (Demo evidence frequently sourced from "SharePoint Library".)

## Architecture
ECS connector → Microsoft Graph (`${MS_GRAPH_URL}`) → SharePoint site (`SHAREPOINT_SITE_ID`) → pulls policy/document/evidence files → evidence → repository + object store.

## Authentication
`auth_type: oauth2_client_credentials`; `MS_TENANT_ID` + `MS_CLIENT_ID` + `MS_CLIENT_SECRET`. No secrets hardcoded.

## Authorization
Azure AD app registration with Graph Sites.Read scope (least privilege). ECS RBAC governs visibility.

## Data Flow
`Graph API → sync_connector() → evidence files (source_system=sharepoint) → MinIO + maps → dashboards`.

## Objects (collect)
`policies, documents, evidence_files`.

## Evidence Sources
Policy docs, evidence libraries → governance/policy + uploaded artifact evidence; indexed for RAG.

## Synchronization & Scheduling
Pull via Connector Scheduler; history in `sync_runs`.

## Error Handling
`timeout_sec=10`, `max_retries=1`; failures → Integration Health + [Connector Failure Playbook](../operations/ECS_CONNECTOR_FAILURE_PLAYBOOK.md).

## Security & Audit Logging
TLS; OAuth2 client secret from env/vault (rotate); access logged in `audit_log`.

## Future UAT / PROD Configuration
- **UAT:** tenant/client/secret + `SHAREPOINT_SITE_ID`, `ECS_SHAREPOINT_ENABLED=true`.
- **PROD:** vaulted secret with rotation, scoped Graph permissions, monitored sync.

## YAML Mapping
```yaml
sharepoint:
  enabled: ${ECS_SHAREPOINT_ENABLED:-false}
  type: sharepoint
  base_url: ${MS_GRAPH_URL:-https://graph.microsoft.com/v1.0}
  site_id_env: SHAREPOINT_SITE_ID
  auth_type: oauth2_client_credentials
  tenant_id_env: MS_TENANT_ID
  client_id_env: MS_CLIENT_ID
  client_secret_env: MS_CLIENT_SECRET
  verify_ssl: true
  collect: [policies, documents, evidence_files]
```
