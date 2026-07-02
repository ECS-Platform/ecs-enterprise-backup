# Integration Guide — GitHub

**Grounding:** `config/integrations.yaml` (`github`), `ecs_platform/ingestion.py`. Part of [Integrations Index](README.md). Interface-complete, `enabled: false` by default. (Mirrors the always-on Gitea connector's object model.)

## Architecture
ECS connector → GitHub API (`${GITHUB_URL:-https://api.github.com}`, org `${GITHUB_ORG}`) → pulls SCM/SDLC objects → evidence → repository. Source for AppSec/secure-SDLC evidence.

## Authentication
`auth_type: token`; `GITHUB_TOKEN`. No secrets hardcoded.

## Authorization
Token scoped to read repo/PR/branch-protection (least privilege). ECS RBAC governs visibility.

## Data Flow
`GitHub API → sync_connector() → evidence (source_system=github) → maps → dashboards`.

## Objects (collect)
`repositories, commits, pull_requests, review_approvals, branch_protections, releases`.

## Evidence Sources
PR review approvals, branch protections, releases → secure-SDLC/change-control evidence (AppSec, AI-SDLC).

## Synchronization & Scheduling
Pull via Connector Scheduler; history in `sync_runs`.

## Error Handling
`timeout_sec=10`, `max_retries=1`; failures → Integration Health + [Connector Failure Playbook](../operations/ECS_CONNECTOR_FAILURE_PLAYBOOK.md).

## Security & Audit Logging
TLS; token from env/vault (rotate); access logged in `audit_log`.

## Future UAT / PROD Configuration
- **UAT:** `GITHUB_ORG`, `GITHUB_TOKEN`, `ECS_GITHUB_ENABLED=true`.
- **PROD:** vaulted fine-grained token with rotation, org-scoped read, monitored sync.

## YAML Mapping
```yaml
github:
  enabled: ${ECS_GITHUB_ENABLED:-false}
  type: github
  base_url: ${GITHUB_URL:-https://api.github.com}
  org: ${GITHUB_ORG:-}
  auth_type: token
  token_env: GITHUB_TOKEN
  verify_ssl: true
  collect: [repositories, commits, pull_requests, review_approvals, branch_protections, releases]
```
