# ECS Enterprise Connector UAT Setup

**Audience:** Bank developers configuring the ECS enterprise evidence connectors
against real UAT endpoints.
**Golden rules:** no real IPs/hostnames/secrets in Git; read-only service
accounts; secrets in `.env.uat` (git-ignored) or a secret manager; connectors
make no live call in tests.

> Cross-refs: [MS_GRAPH_CONNECTOR_GUIDE.md](../connectors/MS_GRAPH_CONNECTOR_GUIDE.md),
> [INTEGRATION_ADAPTERS_GUIDE.md](INTEGRATION_ADAPTERS_GUIDE.md),
> [UAT_INTEGRATION_GUIDE.md](UAT_INTEGRATION_GUIDE.md).

---

## 1. How connectors resolve config

Each connector resolves each field as: environment variable → YAML block in
`config/environments/<env>.yaml` (`connectors:` section) → code default. Secrets
are referenced by `*_env` variable name in YAML (never inline) and read from the
environment. Placeholders like `${VAR:-default}` treat an unset var as the default.

Switch from local demo to bank UAT with **no code change**:
```bash
export ECS_ENV=uat
set -a; source .env.uat; set +a     # never commit .env.uat
```

Generate a placeholder env template to populate:
```bash
python scripts/generate_env_template.py --env uat   # -> .env.uat.template
```

Check config/health without any live call:
```bash
python scripts/run_uat_connector_health.py --adapter all --no-network
python scripts/run_uat_connector_health.py --adapter <name> --live   # if configured
```

---

## 2. Per-connector UAT configuration

### Microsoft Graph (SharePoint / Teams / Outlook)
See [MS_GRAPH_CONNECTOR_GUIDE.md](../connectors/MS_GRAPH_CONNECTOR_GUIDE.md) for Azure App
Registration + Graph permissions. Shared vars: `ECS_GRAPH_TENANT_ID`,
`ECS_GRAPH_CLIENT_ID`, `ECS_GRAPH_CLIENT_SECRET`, `ECS_GRAPH_SCOPE`,
`ECS_GRAPH_AUTHORITY_URL`. Connector vars: SharePoint (`ECS_GRAPH_SITE_ID`,
`ECS_SHAREPOINT_SITE_HOSTNAME`, `ECS_SHAREPOINT_SITE_PATH`,
`ECS_SHAREPOINT_FOLDER_PATH`), Teams (`ECS_TEAMS_TEAM_ID`,
`ECS_TEAMS_CHANNEL_ID`), Outlook (`ECS_OUTLOOK_USER_ID`,
`ECS_OUTLOOK_MAIL_FOLDER`).

### ServiceNow CMDB
Read-only account or OAuth app. Auth mode is selectable:
| Variable | Meaning |
|----------|---------|
| `ECS_SERVICENOW_BASE_URL` | `https://<instance>.service-now.com` |
| `ECS_SERVICENOW_AUTH_MODE` | `oauth` (default) or `basic` |
| `ECS_SERVICENOW_CLIENT_ID` / `ECS_SERVICENOW_CLIENT_SECRET` | OAuth client-credentials |
| `ECS_SERVICENOW_USERNAME` / `ECS_SERVICENOW_PASSWORD` | Basic-auth fallback |

Fetches (Table API, paginated): `fetch_cis`, `fetch_servers`, `fetch_applications`,
`fetch_databases` over `cmdb_ci*` tables; supports `sysparm_query`. Grant the
service account **read** on the CMDB tables in scope.

### Jira
| Variable | Meaning |
|----------|---------|
| `ECS_JIRA_BASE_URL`, `ECS_JIRA_USERNAME`, `ECS_JIRA_API_TOKEN` | Basic auth (email + API token) |
| `ECS_JIRA_PROJECT_KEY`, `ECS_JIRA_JQL` | Optional defaults |
| `ECS_JIRA_API_VERSION` | `2` (default) or `3` |

Fetches: `fetch_projects`, `fetch_issues(jql)`, `fetch_issue(key)`,
`fetch_issue_comments(key)`.

### Confluence
| Variable | Meaning |
|----------|---------|
| `ECS_CONFLUENCE_BASE_URL` | Cloud base usually ends with `/wiki` |
| `ECS_CONFLUENCE_USERNAME`, `ECS_CONFLUENCE_API_TOKEN` | Basic auth |
| `ECS_CONFLUENCE_SPACE_KEY` | Optional default space |

Fetches: `fetch_spaces`, `fetch_pages(space_key)`, `fetch_page(id)`,
`fetch_attachments(id)` (metadata only).

### SonarQube
| Variable | Meaning |
|----------|---------|
| `ECS_SONARQUBE_BASE_URL`, `ECS_SONARQUBE_TOKEN` | Token auth (token as Basic user, empty password) |
| `ECS_SONARQUBE_PROJECT_KEY` | Optional default project |

Fetches: `fetch_projects`, `fetch_quality_gate(project)`,
`fetch_measures(project, metrics)`, `fetch_issues(project, severities)`.

### Prisma Cloud
| Variable | Meaning |
|----------|---------|
| `ECS_PRISMA_CLOUD_BASE_URL` | `https://api.<region>.prismacloud.io` |
| `ECS_PRISMA_CLOUD_ACCESS_KEY`, `ECS_PRISMA_CLOUD_SECRET_KEY` | Access/secret key |

Auth: `POST /login` → JWT sent as `x-redlock-auth`. Fetches:
`fetch_cloud_accounts`, `fetch_alerts`, `fetch_resources`,
`fetch_compliance_posture` (endpoint paths configurable per tenant).

---

## 3. Secret handling

- Secrets only in `.env.uat` (git-ignored) or a secret manager (Vault / cloud /
  K8s Secrets). YAML holds `*_env` **names**, never values.
- ECS never logs secrets — masked config and adapter `repr` show `SET`/`MISSING`.
- Prefer read-only service accounts and least-privilege scopes/permissions.

---

## 4. Read-only permissions summary

| Connector | Grant |
|-----------|-------|
| MS Graph | `Sites.Read.All`, `Files.Read.All`, Teams `*.ReadBasic.All` + `ChannelMessage.Read.All`, `Mail.Read` (app) |
| ServiceNow | read on `cmdb_ci*` tables |
| Jira / Confluence | read on target projects / spaces |
| SonarQube | token with read/browse on target projects |
| Prisma Cloud | read-only role for accounts/alerts/resources/compliance |

---

## 5. Testing with mocked transports

Every connector accepts an injectable `transport`; unit tests supply mock
responses so **no external system is contacted**. See
`tests/test_enterprise_connector_auth_headers.py` and
`tests/test_enterprise_connectors_uat_config.py`.

Validate offline:
```bash
PYTHONPATH=. pytest \
  tests/test_ms_graph_connectors.py tests/test_sharepoint_graph_connector.py \
  tests/test_teams_graph_connector.py tests/test_outlook_graph_connector.py \
  tests/test_enterprise_connectors_uat_config.py \
  tests/test_enterprise_connector_auth_headers.py \
  tests/test_integration_adapters_mocked.py tests/test_integration_connectors_deepening.py
```

---

## 6. Switching local demo → bank UAT (recap)

1. Populate `.env.uat` from the secret manager (placeholders in
   `.env.uat.template`). Never commit it.
2. `export ECS_ENV=uat && set -a; source .env.uat; set +a`.
3. `python scripts/run_uat_connector_health.py --adapter all --no-network` then
   `--live` for configured adapters.
4. Follow the **Bank Developer UAT Checklist** in
   [UAT_INTEGRATION_GUIDE.md](UAT_INTEGRATION_GUIDE.md).
