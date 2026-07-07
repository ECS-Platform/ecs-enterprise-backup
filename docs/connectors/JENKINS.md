# Integration Guide — Jenkins

**Grounding:** `config/integrations.yaml` (`jenkins`), `ecs_platform/ingestion.py`, `docker-compose.yml` (`jenkins` service, `demo-connectors` profile). Part of [Integrations Index](_legacy_INTEGRATIONS_index.md). Self-hostable — **`enabled: true` by default for development**.

## Architecture
ECS connector → Jenkins API (`${JENKINS_URL:-http://jenkins:8080}`) → pulls CI/CD build/test evidence → repository. Source for AppSec/AI-SDLC build + test evidence.

## Authentication
`auth_type: basic`; `JENKINS_USER` + `JENKINS_TOKEN`. No secrets hardcoded.

## Authorization
User/token scoped to read jobs/builds/artifacts (least privilege). ECS RBAC governs visibility.

## Data Flow
`Jenkins API → sync_connector() → evidence (source_system=jenkins) → maps → dashboards`.

## Objects (collect)
`jobs, builds, test_results, artifacts`.

## Evidence Sources
Build results, test results, artifacts → CI/CD + secure-SDLC evidence (AppSec, AI-SDLC test gates).

## Synchronization & Scheduling
Pull via Connector/Evidence Scheduler; history in `sync_runs`. Local stack provides a real Jenkins for development.

## Error Handling
`timeout_sec=10`, `max_retries=1`; failures → Integration Health + [Connector Failure Playbook](../operations/ECS_CONNECTOR_FAILURE_PLAYBOOK.md).

## Security & Audit Logging
TLS in prod (`ECS_JENKINS_VERIFY_SSL`); token from env/vault; access logged in `audit_log`.

## Future UAT / PROD Configuration
- **UAT:** `JENKINS_URL`, user/token, keep `ECS_JENKINS_ENABLED=true`, `verify_ssl=true`.
- **PROD:** TLS endpoint, vaulted token (rotate), least-privilege user, monitored sync.

## YAML Mapping
```yaml
jenkins:
  enabled: ${ECS_JENKINS_ENABLED:-true}
  type: jenkins
  base_url: ${JENKINS_URL:-http://jenkins:8080}
  auth_type: basic
  username_env: JENKINS_USER
  password_env: JENKINS_TOKEN
  verify_ssl: ${ECS_JENKINS_VERIFY_SSL:-true}
  collect: [jobs, builds, test_results, artifacts]
```
