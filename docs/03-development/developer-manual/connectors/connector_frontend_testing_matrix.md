# Connector Frontend Testing Matrix

**Status:** Current · **Owner:** Platform / Integrations · **Applies to:** ECS enterprise evidence connectors

This matrix records **how each enterprise connector can be tested**, with emphasis on
whether testing is available from the **ECS frontend**. It reflects the code in
`modules/operations/integrations/` and the routes/templates in
`modules/audit_intelligence/` and `modules/shared/`.

All frontend/API test actions are **read-only and safe**: connector health check,
config status, dry-run readiness, and a **mock parser test** (deterministic synthetic
data, **no network call, no secrets**). No destructive writes are performed.

---

## 1. Where connectors can be tested

| Surface | What it does | Location |
| --- | --- | --- |
| **Connector Test Workbench (UI)** | Select connector + env, view config status, run health check, dry-run, and mock parser test with output preview | `GET /connectors/test-workbench` (alias `GET /mvp/connectors/test-workbench`) |
| **Connector REST API** | Programmatic health/config/dry-run/parser-test | `/api/connectors`, `/api/connectors/{name}/config-status`, `/api/connectors/{name}/health-check`, `/api/connectors/{name}/dry-run`, `/api/connectors/{name}/parser-test` |
| **Integrations pages (UI)** | Framework-aware integration health overview + demo sync | `GET /mvp/integrations`, `GET /mvp/integrations-hub` |
| **Audit integrations API** | Masked config + config-based health for all adapters | `GET /api/audit/integrations`, `GET /api/audit/integrations/health`, `GET /api/audit/integrations/{name}/health` |
| **CLI / scripts** | Batch health + scheduler dry-run | `scripts/run_uat_connector_health.py`, `scripts/run_uat_asset_scheduler.py --dry-run` |
| **Config validation** | Validate UAT config (no `localhost`, secrets via env) | `scripts/validate_uat_config.py` |

---

## 2. Per-connector matrix

Legend for **Current status**: **Frontend** = testable in the Connector Test Workbench UI ·
**API** = REST endpoints available · **CLI** = script available · **Config** = config validation only.

| Connector | Parser available | Config source | Backend service | API route | Frontend screen | Manual frontend test steps | Test data required | Current status | Gap |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **SharePoint (Graph)** | `SharePointGraphClient.fetch_drive_items` / `fetch_documents` | `config/integrations.yaml` (`sharepoint_graph_adapter`) + `ECS_GRAPH_*`, `ECS_SHAREPOINT_*` | `sharepoint_graph.py` | `/api/connectors/sharepoint_graph/*` | Connector Test Workbench | Open workbench → select **SharePoint (Graph)** → Config status → Health check → Parser test | None for mock; real: tenant/client/site IDs + Graph secret | Frontend + API + CLI | Live pull needs Azure app + Graph consent |
| **Teams (Graph)** | `TeamsGraphClient.fetch_channels` | `config/integrations.yaml` (`teams_graph_adapter`) + `ECS_GRAPH_*`, `ECS_TEAMS_*` | `teams_graph.py` | `/api/connectors/teams_graph/*` | Connector Test Workbench | Select **Microsoft Teams (Graph)** → Health check → Parser test | None for mock; real: team/channel IDs | Frontend + API | Live pull needs Graph consent |
| **Outlook (Graph)** | `OutlookGraphClient.fetch_mail_folders` | `config/integrations.yaml` (`outlook_graph_adapter`) + `ECS_GRAPH_*`, `ECS_OUTLOOK_*` | `outlook_graph.py` | `/api/connectors/outlook_graph/*` | Connector Test Workbench | Select **Outlook (Graph)** → Health check → Parser test | None for mock; real: mailbox user id | Frontend + API | Live pull needs Graph consent |
| **ServiceNow CMDB** | `ServiceNowAdapter.fetch_servers` (also `fetch_cis/applications/databases`) | `config/integrations.yaml` (`servicenow_adapter`) + `ECS_SERVICENOW_*` | `servicenow_cmdb.py` | `/api/connectors/servicenow_cmdb/*` | Connector Test Workbench | Select **ServiceNow CMDB** → Config status → Dry-run → Parser test | None for mock; real: instance URL + OAuth/Basic | Frontend + API + CLI | Live pull needs read-only SNOW account |
| **Jira** | `JiraClient.fetch_projects` (also `fetch_issues`) | `config/integrations.yaml` (`jira_adapter`) + `ECS_JIRA_*` | `jira.py` | `/api/connectors/jira/*` | Connector Test Workbench | Select **Jira** → Config status → Parser test | None for mock; real: base URL + email + API token | Frontend + API | Live pull needs Jira API token |
| **Confluence** | `ConfluenceClient.fetch_spaces` (also `fetch_pages`) | `config/integrations.yaml` (`confluence_adapter`) + `ECS_CONFLUENCE_*` | `confluence.py` | `/api/connectors/confluence/*` | Connector Test Workbench | Select **Confluence** → Config status → Parser test | None for mock; real: base URL + email + API token | Frontend + API | Live pull needs Confluence API token |
| **SonarQube** | `SonarQubeClient.fetch_projects` (also `fetch_issues/quality_gate/measures`) | `config/integrations.yaml` (`sonarqube_adapter`) + `ECS_SONARQUBE_*` | `sonarqube.py` | `/api/connectors/sonarqube/*` | Connector Test Workbench | Select **SonarQube** → Config status → Parser test | None for mock; real: base URL + token | Frontend + API | Live pull needs Sonar token |
| **Checkmarx** | `CheckmarxClient.fetch_scans` | `config/integrations.yaml` (`checkmarx_adapter`) + `ECS_CHECKMARX_*` | `checkmarx.py` | `/api/connectors/checkmarx/*` | Connector Test Workbench | Select **Checkmarx** → Config status → Parser test | None for mock; real: base URL + client id/secret | Frontend + API | Live pull needs Checkmarx OAuth app |
| **Prisma Cloud** | `PrismaCloudClient.fetch_alerts` (also `fetch_resources/compliance_posture`) | `config/integrations.yaml` (`prisma_cloud_adapter`) + `ECS_PRISMA_CLOUD_*` | `prisma_cloud.py` | `/api/connectors/prisma_cloud/*` | Connector Test Workbench | Select **Prisma Cloud** → Config status → Parser test | None for mock; real: base URL + access/secret key | Frontend + API | Live pull needs Prisma keys |
| **Tripwire** | `TripwireClient.fetch_policy_results` | `config/integrations.yaml` (`tripwire_adapter`) + `ECS_TRIPWIRE_*` | `tripwire.py` | `/api/connectors/tripwire/*` | Connector Test Workbench | Select **Tripwire** → Config status → Parser test | None for mock; real: base URL + username/password | Frontend + API | Live pull needs Tripwire account |
| **Archer** (bonus, also registered) | `ArcherClient.fetch_mapped_controls` | `config/integrations.yaml` (`archer_adapter`) + `ECS_ARCHER_*` | `archer.py` | `/api/connectors/archer/*` | Connector Test Workbench | Select **Archer GRC** → Config status → Parser test | None for mock; real: base URL + API token | Frontend + API | Live pull needs Archer token |

> **Note on the mock parser test.** When a connector is not yet configured with real
> credentials, the parser test still runs against an **injected mock transport** using a
> harmless non-secret stub config, so the connector's real parse/normalize path is
> exercised and previewed. This proves the parser works before any bank credentials are
> supplied. It never performs a network call and never returns a secret.

---

## 3. Before this change (gap that was closed)

Prior to the Connector Test Workbench, connectors were testable only via:

- `GET`-only audit integration APIs (`/api/audit/integrations*`) — masked config + config health, **no** dry-run or parser test.
- CLI scripts (`run_uat_connector_health.py`, scheduler dry-run).
- The `/mvp/integrations` page, which targets the demo integrations config and offers only a **health overview + demo "Sync"** — no per-connector parser/dry-run test action.

There was **no frontend screen** to select one of the 11 enterprise connectors and run a
health check, config validation, dry-run, or parser test with an output preview. The
Connector Test Workbench closes that gap **without duplicating connector logic** — it
orchestrates the existing adapter registry and each adapter's existing `is_configured()`,
`masked_config()`, `health_check()`, and primary `fetch_*` method.

---

## 4. Safety guarantees

- **Read-only only.** No writes to any external system.
- **No live network by default.** Parser test uses a local mock transport; health check
  is the adapter's config-based probe.
- **No secrets.** Only masked `SET`/`MISSING` config views are returned; secret values are
  never rendered in the UI or returned by the API (verified by tests).
- **No destructive actions** are exposed in the UI or API.

See `docs/03-development/developer-manual/connectors/connector_frontend_manual_testing.md` for step-by-step frontend test cases.
