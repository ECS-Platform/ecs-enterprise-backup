# Integration Guide — Confluence

**Grounding:** `config/integrations.yaml` (`confluence`), `ecs_platform/ingestion.py`. Part of [Integrations Index](_legacy_INTEGRATIONS_index.md). Interface-complete, `enabled: false` by default.

## Architecture
ECS connector → Confluence REST API (`${CONFLUENCE_URL}`) → pulls documentation/policy artifacts → evidence → repository. Primary source for **policy/architecture documentation** evidence (ITPP, ISG, ISO27001).

## Authentication
`auth_type: token`; `CONFLUENCE_TOKEN` + `CONFLUENCE_USER`. No secrets hardcoded.

## Authorization
Service account scoped to relevant spaces. ECS RBAC governs evidence visibility.

## Data Flow
`Confluence API → sync_connector() → evidence (source_system=confluence) → control/framework maps → dashboards`.

## Objects (collect)
`spaces, pages, attachments, architecture_documents, policies`.

## Evidence Sources
Policy pages, architecture docs, attachments → governance/policy-adherence evidence; indexed for AI knowledge search (RAG governance documents).

## Synchronization & Scheduling
Pull via Connector Scheduler; history in `sync_runs`.

## Error Handling
`timeout_sec=10`, `max_retries=1`; failures → Integration Health + [Connector Failure Playbook](../operations/ECS_CONNECTOR_FAILURE_PLAYBOOK.md).

## Security & Audit Logging
TLS; env-sourced token; access logged in `audit_log`.

## Future UAT / PROD Configuration
- **UAT:** `CONFLUENCE_URL`, token/user, `ECS_CONFLUENCE_ENABLED=true`, space scope.
- **PROD:** vaulted token, least-privilege space access, monitored sync.

## YAML Mapping
```yaml
confluence:
  enabled: ${ECS_CONFLUENCE_ENABLED:-false}
  type: confluence
  base_url: ${CONFLUENCE_URL:-}
  auth_type: token
  token_env: CONFLUENCE_TOKEN
  username_env: CONFLUENCE_USER
  verify_ssl: true
  collect: [spaces, pages, attachments, architecture_documents, policies]
```
