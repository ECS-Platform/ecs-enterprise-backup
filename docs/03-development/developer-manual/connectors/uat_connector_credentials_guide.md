# ECS UAT Connector Credentials & Configuration Guide

The complete, per-connector credentials/configuration reference for validating the
**11 ECS enterprise integration connectors** in the **Connector Test Workbench**
during bank UAT.

- **Workbench UI:** `/mvp/connectors/test-workbench` (alias `/connectors/test-workbench`)
- **Workbench service:** `modules/audit_intelligence/services/connector_workbench.py`
- **Adapters:** `modules/operations/integrations/*`
- **Config:** set secrets in a git-ignored `.env.uat` (see
  [.env.uat.example](../.env.uat.example)); YAML references env by name (see
  [config/uat_connectors.example.yaml](../config/uat_connectors.example.yaml) and
  `config/environments/uat.yaml`).

> **Safety:** never commit real secrets, hosts, tenant IDs, or IPs. Use
> least-privilege, **read-only** service accounts. The workbench and adapters only
> ever show secrets as **SET / MISSING**, never the value. All examples below are
> placeholders.

---

## 1. How to set credentials (once)

```bash
# 1) Copy the example env file and fill in REAL UAT values (kept out of Git):
cp .env.uat.example .env.uat
#   edit .env.uat  (read-only service accounts; real UAT hosts)

# 2) Confirm .env.uat is git-ignored (must print nothing):
git status --porcelain | grep '\.env\.uat$' || echo "OK: .env.uat is not tracked"

# 3) Load it and select the UAT environment:
set -a; source .env.uat; set +a
export ECS_ENV=uat DEMO_MODE=false

# 4) Start ECS and open the Connector Test Workbench:
PYTHONPATH=. uvicorn app.main:app --port 8000
#   http://127.0.0.1:8000/mvp/connectors/test-workbench?role=owner&user=U
```

Secrets are read from the environment variables named below (the adapters'
`get_config()` reads them; YAML `*_env` keys point at them). Non-secret values
(hosts, IDs) may live in `config/environments/uat.yaml` via `${VAR:-default}`.

---

## 2. Validating a connector in the Workbench

Each connector supports four **read-only, safe** actions (no destructive writes):

| Action | Workbench button / API | What it does | Needs live creds? |
|--------|------------------------|--------------|-------------------|
| **Config status** | `GET /api/connectors/{name}/config-status` | Shows masked config (SET/MISSING) + `configured` flag | No |
| **Health check** | `POST /api/connectors/{name}/health-check` | Adapter's config-based readiness probe | No live call in skeleton; live only if a real transport is injected |
| **Dry-run** | `POST /api/connectors/{name}/dry-run` | What *would* run (`would_call`, auth, masked config) — no network | No |
| **Parser test (mock)** | `POST /api/connectors/{name}/parser-test` | Runs the adapter's primary fetch/parse against a **mock transport** (deterministic synthetic data) → normalized preview | No — mock only |

**Live test limitation:** the workbench never makes a live network call. A real
call happens only when real credentials **and** a live HTTP transport are wired at
the adapter level (production wiring / an explicit `--live` in
`scripts/run_uat_connector_health.py`). Use the workbench to confirm **config
presence, health readiness, and parser correctness** safely; use the CLI with
`--live` for an actual endpoint probe once creds are provisioned.

**Interpretation:**
- Config status `configured: true` → all required fields resolved (SET).
- A field shown `MISSING` → set its environment variable in `.env.uat`.
- Parser test `evidence_objects_detected > 0` → the parser/normalizer works.

---

## 3. Common error messages (all connectors)

| Symptom / status | Meaning | Fix |
|------------------|---------|-----|
| `not_configured` | A required field (base_url / auth) is missing | Set the missing env var(s); re-check config-status |
| `auth_error` (401/403) | Credential/token wrong, expired, or lacks scope | Re-issue the token/secret; confirm read scope; check `username` matches the token owner |
| `timeout` | Endpoint unreachable in time | Check VPN/routing + firewall; raise `*_TIMEOUT_SECONDS` |
| `connection_error` | Host unreachable / DNS / refused | Verify `*_BASE_URL` host resolves and the port is open |
| `http_error` (4xx/5xx) | Bad base URL / API path / server error | Verify base URL + API version; check server health |
| `adapter_error` | Adapter import/config raised | Check the env var names match exactly (see per-connector tables) |
| `parser_error` | Parse/normalize failed on the (mock) payload | Usually a config-shape issue; verify required non-secret IDs are set |

---

## 4. Rollback / removal (all connectors)

To disable or remove a connector's UAT credentials safely:

1. **Unset** its environment variables (remove the lines from `.env.uat`, or
   `unset ECS_<CONNECTOR>_*` in the shell).
2. Re-run **config-status** in the workbench → it should report `not_configured`
   (the adapter degrades cleanly; nothing crashes).
3. If configured via YAML, blank the `base_url` (`${VAR:-}`) — the `*_env` keys
   reference env only, so no secret is stored in YAML to remove.
4. Rotate/revoke the credential at the source system (ServiceNow/Jira/etc.) if it
   was ever issued.
5. Confirm `git status` shows **no** `.env.uat` and no secret staged.

There is **no destructive state** to undo — connectors are read-only and store no
data locally; removal is simply unsetting config.

---

## 5. Per-connector fields

Legend: **Secret?** = whether the value is sensitive. Env var names are the exact
names read by the adapter. "Provided by (bank UAT)" is the typical owner.

### 5.1 ServiceNow CMDB (`servicenow_cmdb`)
Auth: OAuth client-credentials **or** Basic (`ECS_SERVICENOW_AUTH_MODE`).

| Field | Env var | Secret? | Where to obtain | Provided by (bank UAT) | Example (masked) |
|-------|---------|---------|-----------------|------------------------|------------------|
| Base URL | `ECS_SERVICENOW_BASE_URL` | No | ServiceNow UAT instance URL | ServiceNow platform team | `https://<instance>-uat.service-now.example` |
| Auth mode | `ECS_SERVICENOW_AUTH_MODE` | No | `oauth` or `basic` | ServiceNow admin | `oauth` |
| Client ID | `ECS_SERVICENOW_CLIENT_ID` | No* | OAuth application registry | ServiceNow admin | `<oauth-client-id>` |
| Client secret | `ECS_SERVICENOW_CLIENT_SECRET` | **Yes** | OAuth application registry | ServiceNow admin | `<secret>` |
| Username | `ECS_SERVICENOW_USERNAME` | No | Read-only service account | IAM / ServiceNow admin | `svc_ecs_snow@bank.example` |
| Password | `ECS_SERVICENOW_PASSWORD` | **Yes** | Service-account credential | IAM | `<secret>` |
| Timeout / retries | `ECS_SERVICENOW_TIMEOUT_SECONDS` / `_MAX_RETRIES` | No | — | Platform Eng | `30` / `2` |

\* client_id is treated as non-secret but keep it access-controlled. **Validate:**
config-status → `configured: true`; parser-test → `fetch_servers` preview.
**Common errors:** `auth_error` (wrong client/secret or user for auth_mode).

### 5.2 Archer GRC (`archer`)
Auth: API token.

| Field | Env var | Secret? | Where to obtain | Provided by | Example (masked) |
|-------|---------|---------|-----------------|-------------|------------------|
| Base URL | `ECS_ARCHER_BASE_URL` | No | Archer UAT URL | GRC platform team | `https://archer-uat.example.bank` |
| API token | `ECS_ARCHER_API_TOKEN` | **Yes** | Archer API/user token | Archer admin | `<secret>` |
| Timeout | `ECS_ARCHER_TIMEOUT_SECONDS` | No | — | Platform Eng | `30` |

**Validate:** parser-test → `fetch_mapped_controls`. **Common errors:**
`not_configured` (base_url/token missing), `auth_error`.

### 5.3 SharePoint (Graph) (`sharepoint_graph`)
Auth: OAuth (Microsoft Graph) — shares tenant/app creds with Teams/Outlook.

| Field | Env var | Secret? | Where to obtain | Provided by | Example (masked) |
|-------|---------|---------|-----------------|-------------|------------------|
| Tenant ID | `ECS_GRAPH_TENANT_ID` | No | Azure AD tenant | Azure AD / IAM | `<tenant-guid>` |
| Client ID | `ECS_GRAPH_CLIENT_ID` | No | App registration | Azure AD / IAM | `<app-client-guid>` |
| Client secret | `ECS_GRAPH_CLIENT_SECRET` | **Yes** | App registration → secrets | Azure AD / IAM | `<secret>` |
| Site ID | `ECS_GRAPH_SITE_ID` | No | SharePoint site (Graph) | SharePoint admin | `<site-id>` |
| Drive ID (opt) | `ECS_GRAPH_DRIVE_ID` | No | SharePoint drive | SharePoint admin | `<drive-id>` |
| Site hostname (opt) | `ECS_SHAREPOINT_SITE_HOSTNAME` | No | SharePoint host | SharePoint admin | `<tenant>.sharepoint.example` |
| Site path (opt) | `ECS_SHAREPOINT_SITE_PATH` | No | Site relative path | SharePoint admin | `/sites/<evidence-site>` |
| Folder path (opt) | `ECS_SHAREPOINT_FOLDER_PATH` | No | Drive folder | Evidence owner | `<folder>` |
| Scope / authority | `ECS_GRAPH_SCOPE` / `ECS_GRAPH_AUTHORITY_URL` | No | Graph defaults | — | `https://graph.microsoft.com/.default` |

**App permissions:** Graph **application** permission `Sites.Read.All` (read-only),
admin-consented. **Validate:** parser-test → `fetch_drive_items`. **Common
errors:** `auth_error` (missing consent / wrong secret), `http_error` (bad site_id).

### 5.4 Microsoft Teams (Graph) (`teams_graph`)
Auth: OAuth (Graph) — shares `ECS_GRAPH_*` tenant/app creds.

| Field | Env var | Secret? | Where to obtain | Provided by | Example (masked) |
|-------|---------|---------|-----------------|-------------|------------------|
| Tenant/Client/Secret | `ECS_GRAPH_TENANT_ID` / `ECS_GRAPH_CLIENT_ID` / `ECS_GRAPH_CLIENT_SECRET` | secret = secret | App registration | Azure AD / IAM | see §5.3 |
| Team ID | `ECS_TEAMS_TEAM_ID` | No | Teams team | Collaboration admin | `<team-id>` |
| Channel ID (opt) | `ECS_TEAMS_CHANNEL_ID` | No | Teams channel | Collaboration admin | `<channel-id>` |
| Message limit | `ECS_TEAMS_MESSAGE_LIMIT` | No | — | Platform Eng | `50` |

**App permissions:** `Channel.ReadBasic.All`, `ChannelMessage.Read.All`
(read-only), admin-consented. **Validate:** parser-test → `fetch_channels`.

### 5.5 Outlook (Graph) (`outlook_graph`)
Auth: OAuth (Graph) — shares `ECS_GRAPH_*` tenant/app creds.

| Field | Env var | Secret? | Where to obtain | Provided by | Example (masked) |
|-------|---------|---------|-----------------|-------------|------------------|
| Tenant/Client/Secret | `ECS_GRAPH_*` (as §5.3) | secret = secret | App registration | Azure AD / IAM | see §5.3 |
| User ID / mailbox | `ECS_OUTLOOK_USER_ID` | No | Mailbox UPN/id | Messaging admin | `svc_ecs_audit@bank.example` |
| Mail folder | `ECS_OUTLOOK_MAIL_FOLDER` | No | Folder name | Evidence owner | `inbox` |
| Message limit | `ECS_OUTLOOK_MESSAGE_LIMIT` | No | — | Platform Eng | `50` |

**App permissions:** `Mail.Read` (application, read-only), admin-consented.
**Validate:** parser-test → `fetch_mail_folders`.

### 5.6 Jira (`jira` / YAML `jira_adapter`)
Auth: Basic (email + API token).

| Field | Env var | Secret? | Where to obtain | Provided by | Example (masked) |
|-------|---------|---------|-----------------|-------------|------------------|
| Base URL | `ECS_JIRA_BASE_URL` | No | Jira UAT URL | Jira admin | `https://jira-uat.example.bank` |
| Username | `ECS_JIRA_USERNAME` | No | Service account email | Jira admin / IAM | `svc_ecs_jira@bank.example` |
| API token | `ECS_JIRA_API_TOKEN` | **Yes** | Jira account API token | Jira admin | `<secret>` |
| Project key | `ECS_JIRA_PROJECT_KEY` | No | Jira project | App team | `ABC` |
| JQL (opt) | `ECS_JIRA_JQL` | No | Query scope | Auditor | `project = ABC` |
| API version | `ECS_JIRA_API_VERSION` | No | `2` or `3` | Platform Eng | `2` |

**Validate:** parser-test → `fetch_projects`. **Common errors:** `auth_error`
(token not owned by `username`, or lacks Browse Projects).

### 5.7 Confluence (`confluence` / YAML `confluence_adapter`)
Auth: Basic (email + API token).

| Field | Env var | Secret? | Where to obtain | Provided by | Example (masked) |
|-------|---------|---------|-----------------|-------------|------------------|
| Base URL | `ECS_CONFLUENCE_BASE_URL` | No | Confluence UAT URL | Confluence admin | `https://confluence-uat.example.bank` |
| Username | `ECS_CONFLUENCE_USERNAME` | No | Service account email | Confluence admin / IAM | `svc_ecs_confluence@bank.example` |
| API token | `ECS_CONFLUENCE_API_TOKEN` | **Yes** | Confluence API token | Confluence admin | `<secret>` |
| Space key | `ECS_CONFLUENCE_SPACE_KEY` | No | Confluence space | Doc owner | `SEC` |

**Validate:** parser-test → `fetch_spaces`. **Common errors:** `auth_error`,
`http_error` (wrong space key).

### 5.8 SonarQube (`sonarqube` / YAML `sonarqube_adapter`)
Auth: token.

| Field | Env var | Secret? | Where to obtain | Provided by | Example (masked) |
|-------|---------|---------|-----------------|-------------|------------------|
| Base URL | `ECS_SONARQUBE_BASE_URL` | No | SonarQube UAT URL | AppSec / DevOps | `https://sonar-uat.example.bank` |
| Token | `ECS_SONARQUBE_TOKEN` | **Yes** | SonarQube user token | AppSec admin | `<secret>` |
| Project key (opt) | `ECS_SONARQUBE_PROJECT_KEY` | No | SonarQube project | App team | `<project-key>` |

**Validate:** parser-test → `fetch_projects`. **Common errors:** `auth_error`
(token lacks "Execute Analysis"/"Browse" perm).

### 5.9 Checkmarx (`checkmarx`)
Auth: OAuth client-credentials.

| Field | Env var | Secret? | Where to obtain | Provided by | Example (masked) |
|-------|---------|---------|-----------------|-------------|------------------|
| Base URL | `ECS_CHECKMARX_BASE_URL` | No | Checkmarx UAT URL | AppSec admin | `https://checkmarx-uat.example.bank` |
| Client ID | `ECS_CHECKMARX_CLIENT_ID` | No | OAuth client | AppSec admin | `<client-id>` |
| Client secret | `ECS_CHECKMARX_CLIENT_SECRET` | **Yes** | OAuth client | AppSec admin | `<secret>` |
| Access token (opt) | `ECS_CHECKMARX_ACCESS_TOKEN` | **Yes** | Pre-issued token | AppSec admin | `<secret>` |
| Token URL (opt) | `ECS_CHECKMARX_TOKEN_URL` | No | OAuth token endpoint | AppSec admin | `<token-url>` |

**Validate:** parser-test → `fetch_scans`. **Common errors:** `auth_error`
(client/secret or token URL wrong).

### 5.10 Prisma Cloud (`prisma_cloud`)
Auth: access key / secret key (→ session token).

| Field | Env var | Secret? | Where to obtain | Provided by | Example (masked) |
|-------|---------|---------|-----------------|-------------|------------------|
| Base URL | `ECS_PRISMA_CLOUD_BASE_URL` | No | Prisma API URL (region) | Cloud security team | `https://api-uat.prismacloud.example` |
| Access key | `ECS_PRISMA_CLOUD_ACCESS_KEY` | No | Prisma access key id | Cloud security admin | `<access-key-id>` |
| Secret key | `ECS_PRISMA_CLOUD_SECRET_KEY` | **Yes** | Prisma access key secret | Cloud security admin | `<secret>` |
| Token (opt) | `ECS_PRISMA_CLOUD_TOKEN` | **Yes** | Pre-issued session token | Cloud security admin | `<secret>` |

**Validate:** parser-test → `fetch_alerts`. **Common errors:** `auth_error`
(access/secret pair invalid), `http_error` (wrong regional base URL).

### 5.11 Tripwire (`tripwire`)
Auth: Basic (username + password).

| Field | Env var | Secret? | Where to obtain | Provided by | Example (masked) |
|-------|---------|---------|-----------------|-------------|------------------|
| Base URL | `ECS_TRIPWIRE_BASE_URL` | No | Tripwire UAT URL | Infra / security team | `https://tripwire-uat.example.bank` |
| Username | `ECS_TRIPWIRE_USERNAME` | No | Read-only account | IAM / Tripwire admin | `svc_ecs_tripwire` |
| Password | `ECS_TRIPWIRE_PASSWORD` | **Yes** | Service-account credential | IAM | `<secret>` |

**Validate:** parser-test → `fetch_policy_results`. **Common errors:**
`auth_error`, `connection_error`.

---

## 6. Batch validation (CLI)

```bash
# Config-only health for all adapters (no network; SET/MISSING only):
PYTHONPATH=. python scripts/run_uat_connector_health.py --adapter all --no-network

# Live probe for a single configured adapter (real call — only after creds set):
PYTHONPATH=. python scripts/run_uat_connector_health.py --adapter jira --live

# Strict mode: non-zero exit if any CONFIGURED adapter is unhealthy:
PYTHONPATH=. python scripts/run_uat_connector_health.py --adapter all --strict
```

## 7. Field / env-var summary (quick reference)

| Connector | Base URL env | Secret env(s) | Non-secret id/scope env(s) |
|-----------|--------------|---------------|-----------------------------|
| ServiceNow CMDB | `ECS_SERVICENOW_BASE_URL` | `ECS_SERVICENOW_CLIENT_SECRET`, `ECS_SERVICENOW_PASSWORD` | `ECS_SERVICENOW_CLIENT_ID`, `ECS_SERVICENOW_USERNAME`, `ECS_SERVICENOW_AUTH_MODE` |
| Archer | `ECS_ARCHER_BASE_URL` | `ECS_ARCHER_API_TOKEN` | — |
| SharePoint Graph | (Graph) | `ECS_GRAPH_CLIENT_SECRET` | `ECS_GRAPH_TENANT_ID`, `ECS_GRAPH_CLIENT_ID`, `ECS_GRAPH_SITE_ID`, `ECS_GRAPH_DRIVE_ID`, `ECS_SHAREPOINT_*` |
| Teams Graph | (Graph) | `ECS_GRAPH_CLIENT_SECRET` | `ECS_GRAPH_TENANT_ID`, `ECS_GRAPH_CLIENT_ID`, `ECS_TEAMS_TEAM_ID`, `ECS_TEAMS_CHANNEL_ID` |
| Outlook Graph | (Graph) | `ECS_GRAPH_CLIENT_SECRET` | `ECS_GRAPH_TENANT_ID`, `ECS_GRAPH_CLIENT_ID`, `ECS_OUTLOOK_USER_ID`, `ECS_OUTLOOK_MAIL_FOLDER` |
| Jira | `ECS_JIRA_BASE_URL` | `ECS_JIRA_API_TOKEN` | `ECS_JIRA_USERNAME`, `ECS_JIRA_PROJECT_KEY`, `ECS_JIRA_API_VERSION` |
| Confluence | `ECS_CONFLUENCE_BASE_URL` | `ECS_CONFLUENCE_API_TOKEN` | `ECS_CONFLUENCE_USERNAME`, `ECS_CONFLUENCE_SPACE_KEY` |
| SonarQube | `ECS_SONARQUBE_BASE_URL` | `ECS_SONARQUBE_TOKEN` | `ECS_SONARQUBE_PROJECT_KEY` |
| Checkmarx | `ECS_CHECKMARX_BASE_URL` | `ECS_CHECKMARX_CLIENT_SECRET`, `ECS_CHECKMARX_ACCESS_TOKEN` | `ECS_CHECKMARX_CLIENT_ID`, `ECS_CHECKMARX_TOKEN_URL` |
| Prisma Cloud | `ECS_PRISMA_CLOUD_BASE_URL` | `ECS_PRISMA_CLOUD_SECRET_KEY`, `ECS_PRISMA_CLOUD_TOKEN` | `ECS_PRISMA_CLOUD_ACCESS_KEY` |
| Tripwire | `ECS_TRIPWIRE_BASE_URL` | `ECS_TRIPWIRE_PASSWORD` | `ECS_TRIPWIRE_USERNAME` |

---

## 8. Bank UAT provisioning checklist

- [ ] Read-only service accounts created for each in-scope connector.
- [ ] OAuth apps / API tokens issued (with least-privilege read scopes).
- [ ] Azure AD app registration created + **admin consent** for Graph read scopes.
- [ ] Real UAT hosts/IDs collected (no `localhost`; no public IPs in Git).
- [ ] Secrets placed only in `.env.uat` (git-ignored) or the secret manager.
- [ ] VPN/DNS/firewall path opened from the ECS host to each target.
- [ ] Workbench **config-status** shows `configured: true` for each connector.
- [ ] Workbench **parser-test** returns a non-empty normalized preview.
- [ ] (When ready) CLI `--live` health check passes for each configured connector.

Cross references: [.env.uat.example](../.env.uat.example) ·
[config/uat_connectors.example.yaml](../config/uat_connectors.example.yaml) ·
[connector_frontend_testing_matrix.md](connector_frontend_testing_matrix.md) ·
[DEVELOPER/ENTERPRISE_CONNECTOR_UAT_SETUP.md](ENTERPRISE_CONNECTOR_UAT_SETUP.md) ·
[DEVELOPER/MS_GRAPH_CONNECTOR_GUIDE.md](../connectors/MS_GRAPH_CONNECTOR_GUIDE.md).
