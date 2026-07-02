# Integration Guide — Jira

**Grounding:** `config/integrations.yaml` (`jira`), `ecs_platform/ingestion.py`. Part of [Integrations Index](README.md). Interface-complete, `enabled: false` by default.

## Architecture
ECS connector → Jira REST API (`${JIRA_URL}`) → pulls governance/delivery objects → normalized to evidence → repository → control/framework mapping. Used for ITPP/AppSec/AI-SDLC delivery evidence (approvals, workflow states).

## Authentication
`auth_type: token` (also oauth2/basic). Token in `JIRA_TOKEN`; `JIRA_USER` = Atlassian Cloud email for basic/token. No secrets hardcoded.

## Authorization
Connector service account scoped to required projects (least privilege). ECS RBAC controls who views ingested Jira evidence.

## Data Flow
`Jira API → sync_connector() → evidence rows (source_system=jira) → evidence_control_map / evidence_framework_map → dashboards`.

## Objects (collect)
`projects, issues, stories, epics, approvals, comments, workflow_states`.

## Evidence Sources
Approvals, workflow-state transitions, issue/epic records → change/governance and AI-SDLC stage evidence.

## Synchronization & Scheduling
Pull-based via Evidence/Connector Scheduler; cadence per schedule. Run history in `sync_runs`. See [Scheduler](../operations/ECS_SCHEDULER_REFERENCE.md).

## Error Handling
Global defaults: `timeout_sec=10`, `max_retries=1`. Failures surface on Integration Health; escalate via [Connector Failure Playbook](../operations/ECS_CONNECTOR_FAILURE_PLAYBOOK.md).

## Security & Audit Logging
TLS (`verify_ssl: true`); token from env/secret store; ingested access logged (`audit_log`).

## Future UAT / PROD Configuration
- **UAT:** set `JIRA_URL` (UAT site), `JIRA_TOKEN`/`JIRA_USER`, `ECS_JIRA_ENABLED=true`, restricted project scope.
- **PROD:** prod site URL, vaulted token, `verify_ssl: true`, least-privilege account, monitored sync.

## YAML Mapping
```yaml
jira:
  enabled: ${ECS_JIRA_ENABLED:-false}
  type: jira
  base_url: ${JIRA_URL:-}
  auth_type: token
  token_env: JIRA_TOKEN
  username_env: JIRA_USER
  verify_ssl: true
  collect: [projects, issues, stories, epics, approvals, comments, workflow_states]
```
