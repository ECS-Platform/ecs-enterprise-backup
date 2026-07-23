# ECS Integration Architecture — Index

**Type:** Integration reference index. **No code/UI/DB changes.** **Grounding:** `config/integrations.yaml`, `ecs_platform/ingestion.py` (`sync_connector`), `ecs_platform/config/loader.py` (`${ENV}`/`${ENV:-default}` resolution), `/mvp/integrations`, `/mvp/integration-health`, `connectors`/`sync_runs` tables.

> **Security stance (all connectors):** No URLs/credentials/tokens hardcoded — every sensitive value resolves from environment variables at load time. SaaS/enterprise connectors are **interface-complete but `enabled: false`** until a tenant sets env vars + `enabled: true` (no code change). Self-hostable systems (Gitea, SonarQube, Jenkins) default `enabled: true` for development. Global defaults: `timeout_sec=10`, `max_retries=1`, `page_size=100` (health checks fail fast).

## Guides

| Integration | Type | Auth | Default enabled | Doc |
|---|---|---|---|---|
| Jira | `jira` | token/oauth2/basic | false | [JIRA.md](JIRA.md) |
| Confluence | `confluence` | token | false | [CONFLUENCE.md](CONFLUENCE.md) |
| ServiceNow | `servicenow` | basic | false | [SERVICENOW.md](SERVICENOW.md) |
| Prisma Cloud | `prisma` | prisma_credentials | false | [PRISMA_CLOUD.md](PRISMA_CLOUD.md) |
| SharePoint | `sharepoint` | oauth2_client_credentials | false | [SHAREPOINT.md](SHAREPOINT.md) |
| Microsoft Teams | `teams` | oauth2_client_credentials | false | [MICROSOFT_TEAMS.md](MICROSOFT_TEAMS.md) |
| Azure DevOps | `azure_devops` | pat | false | [AZURE_DEVOPS.md](AZURE_DEVOPS.md) |
| GitHub | `github` | token | false | [GITHUB.md](GITHUB.md) |
| Jenkins | `jenkins` | basic | true (dev) | [JENKINS.md](JENKINS.md) |

> Also shipped (not in the requested 9): **Gitea**, **SonarQube**, **Figma**, plus operations-layer query connectors (Linux, PostgreSQL, Trivy, Gitleaks). Total **12 source-system connectors**.

## Common structure
Each guide covers: Architecture · Authentication · Authorization · Data Flow · Objects · Evidence Sources · Synchronization · Scheduling · Error Handling · Security · Audit Logging · Future UAT Config · Future PROD Config · YAML Mapping.

## Related
- Scheduler: [ECS_SCHEDULER_REFERENCE.md](../operations/ECS_SCHEDULER_REFERENCE.md)
- Onboarding: [ECS_APPLICATION_ONBOARDING_GUIDE.md](../operations/ECS_APPLICATION_ONBOARDING_GUIDE.md)
- Connector failures: [ECS_CONNECTOR_FAILURE_PLAYBOOK.md](../operations/ECS_CONNECTOR_FAILURE_PLAYBOOK.md)
- Security: [ECS_SECURITY_REFERENCE.md](../production/ECS_SECURITY_REFERENCE.md)
