# ECS Connector Configuration Guide

Every connector endpoint is configurable via `config/environments/*.yaml`
(`connectors:` section) + `${VAR}` env vars. Credentials are referenced by `*_env`
name and resolved from the environment — never stored in YAML.

## Supported connectors + endpoint vars

| Connector | Base URL var | Credential vars (`*_env`) |
|---|---|---|
| ServiceNow CMDB | `ECS_SERVICENOW_BASE_URL` | `ECS_SERVICENOW_CLIENT_ID/CLIENT_SECRET` or `_USERNAME/_PASSWORD` (`ECS_SERVICENOW_AUTH_MODE`) |
| Archer | `ECS_ARCHER_BASE_URL` | `ECS_ARCHER_API_TOKEN` |
| SharePoint / Teams / Outlook (Graph) | `MS_GRAPH_URL` / site vars | `ECS_GRAPH_TENANT_ID/CLIENT_ID/CLIENT_SECRET` |
| Jira | `ECS_JIRA_BASE_URL` | `ECS_JIRA_USERNAME` + `ECS_JIRA_API_TOKEN` |
| Confluence | `ECS_CONFLUENCE_BASE_URL` | `ECS_CONFLUENCE_USERNAME` + `ECS_CONFLUENCE_API_TOKEN` |
| SonarQube | `ECS_SONARQUBE_BASE_URL` | `ECS_SONARQUBE_TOKEN` |
| Checkmarx | `ECS_CHECKMARX_BASE_URL` | `ECS_CHECKMARX_CLIENT_ID/CLIENT_SECRET` |
| Prisma Cloud | `ECS_PRISMA_CLOUD_BASE_URL` | `ECS_PRISMA_CLOUD_ACCESS_KEY/SECRET_KEY` |
| Tripwire | `ECS_TRIPWIRE_BASE_URL` | `ECS_TRIPWIRE_USERNAME/PASSWORD` |
| GitHub / Gitea / Azure DevOps / Jenkins | `GITHUB_URL` / `GITEA_URL` / `AZDO_URL` / `JENKINS_URL` | token vars per connector |
| AWS / Azure / GCP / Nessus / Qualys | per-connector `*_BASE_URL` / region | per-connector credential `*_env` |

> The Jira/Confluence/SonarQube evidence *adapters* read the `jira_adapter` /
> `confluence_adapter` / `sonarqube_adapter` YAML blocks (the plain `jira` /
> `confluence` / `sonarqube` connector entries carry the legacy url/enabled shape).

## Common per-connector knobs
Each adapter block supports (where applicable): `base_url`, `api_version`,
`timeout_sec`, `max_retries`, plus auth (`client_id`/`client_secret_env`,
`username`/`password_env`, `token_env`, `api_token_env`), `tenant_id`, and
certificate/proxy via the global `connector_execution` section
(`ECS_CONNECTOR_SSL_VERIFY`, `ECS_CONNECTOR_PROXY_URL`).

## Global connector-execution defaults
```yaml
connector_execution:
  enabled:     ${ECS_CONNECTORS_ENABLED:-true}
  timeout_sec: ${ECS_CONNECTOR_TIMEOUT_SECONDS:-30}
  max_retries: ${ECS_CONNECTOR_MAX_RETRIES:-2}
  ssl_verify:  ${ECS_CONNECTOR_SSL_VERIFY:-true}
  proxy_url:   ${ECS_CONNECTOR_PROXY_URL:-}
```

## Configure a connector for an environment
1. Set its `*_BASE_URL` (and `api_version`/`timeout`/`retry` if non-default) in the
   env file / vault.
2. Set its credential `*_env` variables (secrets).
3. Validate: `python scripts/config_tools.py validate-config <env>`.
4. Health-check (config-safe, no live call in skeletons):
   `GET /api/audit/integrations/health`.

## Rules
- No connector URL/secret is hard-coded in source; all come from config.
- Secrets are shown as SET/MISSING in profiles/diagnostics — never the value.
- In remote environments a connector URL that resolves to localhost is rejected.
