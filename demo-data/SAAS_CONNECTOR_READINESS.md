# ECS SaaS Connector Readiness

Scope: Jira Cloud, Confluence Cloud, GitHub, Microsoft Teams, SharePoint.
No real accounts are connected. This is a configuration-readiness assessment:
every connector is **interface-complete and disabled by default**; a tenant is
onboarded by setting env vars and flipping `enabled: true` — no code change.

## Readiness matrix

| Connector | YAML entry | Connector code | docker-compose env | UI (Health + Explorer) | Status |
|-----------|:---------:|:--------------:|:------------------:|:----------------------:|--------|
| Jira Cloud | ✅ `integrations.jira` | ✅ `jira_connector.py` | ✅ | ✅ | **Ready to onboard** |
| Confluence Cloud | ✅ `integrations.confluence` | ✅ `confluence_connector.py` | ✅ | ✅ | **Ready to onboard** |
| GitHub | ✅ `integrations.github` | ✅ `github_connector.py` | ✅ | ✅ | **Ready to onboard** |
| Microsoft Teams | ✅ `integrations.teams` | ✅ `teams_connector.py` + `_msgraph.py` | ✅ *(added)* | ✅ chip *(added)* | **Ready to onboard** |
| SharePoint | ✅ `integrations.sharepoint` | ✅ `sharepoint_connector.py` + `_msgraph.py` | ✅ *(added)* | ✅ chip *(added)* | **Ready to onboard** |

> *(added)* = gap found and fixed in this pass. Before: Teams/SharePoint had YAML
> + connector code but **no env passthrough** in `docker-compose.yml`, so the
> container could never receive Microsoft Graph credentials. Now wired:
> `MS_TENANT_ID`, `MS_CLIENT_ID`, `MS_CLIENT_SECRET`, `SHAREPOINT_SITE_ID`,
> `MS_GRAPH_URL`, `ECS_TEAMS_ENABLED`, `ECS_SHAREPOINT_ENABLED`.

## Exact environment variables

Place in a host-level `.env` (next to `docker-compose.yml`) — never commit secrets.

```bash
# --- Jira Cloud (API token + account email) ---
ECS_JIRA_ENABLED=true
JIRA_URL=https://your-org.atlassian.net
JIRA_USER=you@your-org.com           # Atlassian account email
JIRA_TOKEN=<atlassian-api-token>      # id.atlassian.com > Security > API tokens

# --- Confluence Cloud (same Atlassian token works) ---
ECS_CONFLUENCE_ENABLED=true
CONFLUENCE_URL=https://your-org.atlassian.net/wiki
CONFLUENCE_USER=you@your-org.com
CONFLUENCE_TOKEN=<atlassian-api-token>

# --- GitHub (org-scoped PAT or fine-grained token) ---
ECS_GITHUB_ENABLED=true
GITHUB_URL=https://api.github.com     # or https://ghe.example.com/api/v3 for Enterprise
GITHUB_ORG=your-org
GITHUB_TOKEN=<github-pat>

# --- Microsoft 365: Teams + SharePoint (one Entra app registration) ---
ECS_TEAMS_ENABLED=true
ECS_SHAREPOINT_ENABLED=true
MS_GRAPH_URL=https://graph.microsoft.com/v1.0
MS_TENANT_ID=<entra-tenant-id>
MS_CLIENT_ID=<app-registration-client-id>
MS_CLIENT_SECRET=<app-registration-secret>
SHAREPOINT_SITE_ID=<graph-site-id>     # e.g. contoso.sharepoint.com,<guid>,<guid>
```

## Required API permissions / scopes

| Connector | Auth | Minimum permissions |
|-----------|------|---------------------|
| Jira Cloud | API token (Basic: email + token) | `read:jira-work`, `read:jira-user` (project + issue read) |
| Confluence Cloud | API token (Basic: email + token) | `read:confluence-space.summary`, `read:confluence-content.summary` |
| GitHub | PAT / fine-grained token | `repo` (read), `read:org`; for fine-grained: Contents/Pull requests/Metadata = Read |
| Teams | Entra app, OAuth2 client credentials | Application: `Team.ReadBasic.All`, `Channel.ReadBasic.All`, `ChannelMessage.Read.All` |
| SharePoint | Entra app, OAuth2 client credentials | Application: `Sites.Read.All`, `Files.Read.All` |

## Onboarding checklist (per connector)

1. [ ] Create the credential in the source system (API token / PAT / Entra app + secret).
2. [ ] Grant the minimum read permissions above and admin-consent (Teams/SharePoint).
3. [ ] Add the env vars to the host `.env` (above). **Do not hardcode in YAML.**
4. [ ] Set `ECS_<CONNECTOR>_ENABLED=true`.
5. [ ] `docker compose up -d ecs` (re-reads env; no rebuild needed).
6. [ ] Open **Integration Health** → confirm the connector shows `Connected / Authenticated`.
7. [ ] Click **Sync Now** for the connector.
8. [ ] Open **Evidence Explorer** → filter by the source chip → confirm rows.
9. [ ] Confirm control/framework mappings flow into **Evidence Reuse** + **Framework Coverage**.

## Verification (no real account needed)

- `GET /api/platform/health` lists all 5 connectors. While disabled they report
  `detail: "disabled"`; the YAML + code + env wiring is what makes them
  one-flag-away from live.
- `ConnectorFactory` resolves all 5 types from `_REGISTRY`, so enabling the flag
  is sufficient to activate collection.
