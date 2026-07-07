# Integration Guide — ServiceNow

**Grounding:** `config/integrations.yaml` (`servicenow`), `ecs_platform/ingestion.py`. Part of [Integrations Index](_legacy_INTEGRATIONS_index.md). Interface-complete, `enabled: false` by default. (Demo evidence frequently sourced from "ServiceNow GRC".)

## Architecture
ECS connector → ServiceNow REST API (`${SNOW_URL}`) → pulls ITSM/GRC records → evidence → repository. Source for **change/incident/CAB** governance evidence (PCI change, ITPP, CSITE).

## Authentication
`auth_type: basic`; `SNOW_USER` + `SNOW_PASSWORD`. No secrets hardcoded.

## Authorization
Integration user with read scope on incident/change/problem tables. ECS RBAC governs visibility.

## Data Flow
`ServiceNow API → sync_connector() → evidence (source_system=servicenow) → control/framework maps → dashboards`.

## Objects (collect)
`incidents, change_requests, problem_records, cab_approvals`.

## Evidence Sources
CAB approvals, change records, incidents → change-management/IR evidence; feeds cross-tool correlation (incident → control chains).

## Synchronization & Scheduling
Pull via Connector Scheduler; history in `sync_runs`.

## Error Handling
`timeout_sec=10`, `max_retries=1`; failures → Integration Health + [Connector Failure Playbook](../operations/ECS_CONNECTOR_FAILURE_PLAYBOOK.md).

## Security & Audit Logging
TLS; env-sourced basic creds (prefer vault); access logged in `audit_log`.

## Future UAT / PROD Configuration
- **UAT:** `SNOW_URL`, user/password, `ECS_SNOW_ENABLED=true`.
- **PROD:** vaulted credentials (rotate), least-privilege integration user, monitored sync.

## YAML Mapping
```yaml
servicenow:
  enabled: ${ECS_SNOW_ENABLED:-false}
  type: servicenow
  base_url: ${SNOW_URL:-}
  auth_type: basic
  username_env: SNOW_USER
  password_env: SNOW_PASSWORD
  verify_ssl: true
  collect: [incidents, change_requests, problem_records, cab_approvals]
```
