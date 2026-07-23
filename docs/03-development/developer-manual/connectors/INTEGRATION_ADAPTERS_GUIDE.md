# ECS Enterprise Integration Adapters Guide

**Package:** `modules/operations/integrations/`

Config-driven, credential-externalised adapter skeletons for enterprise systems.
All adapters share one interface and one response shape, never log secrets, and
never make live calls in tests (the HTTP transport is injectable).

---

## 1. Adapters

| Adapter | Module | Auth | Fetches (normalized) |
|---|---|---|---|
| ServiceNow CMDB | `servicenow_cmdb.py` | OAuth client id/secret **or** Basic | assets / CIs (servers/apps/databases) |
| Archer | `archer.py` | API token | controls / frameworks |
| SharePoint / Graph | `sharepoint_graph.py` | OAuth (MS Graph) | sites / drives / items / file metadata |
| Microsoft Teams / Graph | `teams_graph.py` | OAuth (MS Graph) | teams / channels / messages / tabs |
| Outlook / Graph | `outlook_graph.py` | OAuth (MS Graph) | mail folders / messages / attachment metadata |
| Jira | `jira.py` | basic (email + API token) | projects / issues / comments |
| Confluence | `confluence.py` | basic (email + API token) | spaces / pages / attachments |
| SonarQube | `sonarqube.py` | token | projects / quality gate / measures / issues |
| Checkmarx | `checkmarx.py` | OAuth client id/secret | scans |
| Prisma Cloud | `prisma_cloud.py` | access key / secret key | accounts / alerts / resources / compliance |
| Tripwire | `tripwire.py` | basic (user + password) | policy results |
| AWS (cloud posture) | `aws_connector.py` | access key / secret key (+ collector endpoint) | Security Hub findings / Config compliance |
| Azure (cloud posture) | `azure_connector.py` | OAuth (tenant/client/secret) or token | Defender security assessments |
| GCP (cloud posture) | `gcp_connector.py` | service-account JSON or access token (+ collector) | SCC findings / Cloud Asset Inventory |
| Nessus (Tenable) | `nessus.py` | access key / secret key | scans / vulnerabilities |
| Qualys | `qualys.py` | basic (user + password) | host detections / compliance posture |
| GitHub | `github.py` → reuses `ecs_platform` `GitHubConnector` | Bearer (PAT / App) | repositories / PRs / branch protections |
| Jenkins | `jenkins.py` → reuses `ecs_platform` `JenkinsConnector` | basic (user + API token) | CI jobs / builds / test results |
| Azure DevOps | `azure_devops.py` → reuses `ecs_platform` `AzureDevOpsConnector` | PAT (basic) | repositories / PRs / pipelines |

> The three Microsoft Graph connectors share `ms_graph_base.py` (OAuth2
> client-credentials + `@odata.nextLink` pagination). See
> [MS_GRAPH_CONNECTOR_GUIDE.md](../connectors/MS_GRAPH_CONNECTOR_GUIDE.md) and
> [ENTERPRISE_CONNECTOR_UAT_SETUP.md](ENTERPRISE_CONNECTOR_UAT_SETUP.md).
>
> The cloud/scanner adapters (AWS, Azure, GCP, Nessus, Qualys) intentionally add
> **no cloud SDKs** — they use the same injectable `BaseAdapter`/transport
> contract. AWS/GCP read posture from a configurable collector/export endpoint
> (`*_POSTURE_BASE_URL`); a real deployment fronts the cloud APIs with that
> collector (or injects a signing transport). `archer.py` (RSA Archer GRC, API
> token → controls/frameworks) is also registered.

> **Two connector frameworks exist.** This guide covers the *audit-intelligence*
> adapter stack (`modules/operations/integrations/`) used by the Connector Test
> Workbench, scheduler, and evidence executor. A separate *platform ingestion*
> stack lives in `ecs_platform/connectors/` (real `HttpClient` + `test_connection`,
> wired via `ConnectorFactory`).
>
> **GitHub, Jenkins, and Azure DevOps** are now first-class audit-intelligence
> adapters (`github.py`, `jenkins.py`, `azure_devops.py`) that are **thin wrappers
> reusing the existing `ecs_platform` connector clients** — no HTTP client or
> authentication is duplicated. The bridge (`_platform_bridge.py`) builds the
> platform `ConnectorConfig`, injects a mock `HttpClient` for workbench/dry-run
> (no network), runs the platform connector's own `collect_evidence`, and maps the
> resulting `EvidenceItem` list into the standard adapter response. They are in
> `ADAPTER_MODULES`, the workbench `_ADAPTER_TESTS` map, the scheduler routing
> table, and the executor. See their docs: [GITHUB.md](GITHUB.md),
> [JENKINS.md](JENKINS.md), [AZURE_DEVOPS.md](AZURE_DEVOPS.md).

---

## 2. Common interface

Every adapter module exposes:

- `get_config() -> dict` — resolve config from env / YAML.
- `is_configured() -> bool`.
- `masked_config() -> dict` — secret-safe view (secrets shown as `SET`/`MISSING`).
- `health_check() -> dict` — readiness (config-based in the skeleton).
- `fetch_*(…) -> dict` — standard response (below).
- `normalize_*(record) -> dict` — map a raw record to an ECS shape.
- a `<Name>Client` dataclass accepting `config=` and `transport=` (inject in tests).

Shared machinery lives in `_base.py` (`BaseAdapter`, retry/backoff, pagination,
error classification, response builders).

### Standard response shape

```json
{ "ok": true, "source": "jira", "status": "ok",
  "items": [ ... ], "errors": [] }
```

`status` vocabulary: `ok` · `empty` · `not_configured` · `auth_error` · `timeout`
· `connection_error` · `http_error` · `transport_error`.

---

## 3. Configuration variables

Set via environment (`.env` / `.env.uat`) or the YAML `connectors:` section
(`_base.yaml` / `uat.yaml`). Secrets are referenced by `*_env` name in YAML, never
inline.

| Adapter | Variables |
|---|---|
| ServiceNow | `ECS_SERVICENOW_BASE_URL` · `ECS_SERVICENOW_CLIENT_ID` · `ECS_SERVICENOW_CLIENT_SECRET` · `ECS_SERVICENOW_TIMEOUT_SECONDS` |
| Archer | `ECS_ARCHER_BASE_URL` · `ECS_ARCHER_API_TOKEN` · `ECS_ARCHER_TIMEOUT_SECONDS` |
| SharePoint/Graph | `ECS_GRAPH_TENANT_ID` · `ECS_GRAPH_CLIENT_ID` · `ECS_GRAPH_CLIENT_SECRET` · `ECS_GRAPH_SITE_ID` · `ECS_GRAPH_DRIVE_ID` · `ECS_GRAPH_TIMEOUT_SECONDS` |
| Jira | `ECS_JIRA_BASE_URL` · `ECS_JIRA_USERNAME` · `ECS_JIRA_API_TOKEN` · `ECS_JIRA_TIMEOUT_SECONDS` |
| Confluence | `ECS_CONFLUENCE_BASE_URL` · `ECS_CONFLUENCE_USERNAME` · `ECS_CONFLUENCE_API_TOKEN` · `ECS_CONFLUENCE_TIMEOUT_SECONDS` |
| SonarQube | `ECS_SONARQUBE_BASE_URL` · `ECS_SONARQUBE_TOKEN` · `ECS_SONARQUBE_TIMEOUT_SECONDS` |
| Checkmarx | `ECS_CHECKMARX_BASE_URL` · `ECS_CHECKMARX_CLIENT_ID` · `ECS_CHECKMARX_CLIENT_SECRET` · `ECS_CHECKMARX_TIMEOUT_SECONDS` |
| Prisma Cloud | `ECS_PRISMA_CLOUD_BASE_URL` · `ECS_PRISMA_CLOUD_ACCESS_KEY` · `ECS_PRISMA_CLOUD_SECRET_KEY` · `ECS_PRISMA_CLOUD_TIMEOUT_SECONDS` |
| Tripwire | `ECS_TRIPWIRE_BASE_URL` · `ECS_TRIPWIRE_USERNAME` · `ECS_TRIPWIRE_PASSWORD` · `ECS_TRIPWIRE_TIMEOUT_SECONDS` |
| AWS | `AWS_POSTURE_BASE_URL` · `AWS_REGION` · `AWS_ACCESS_KEY_ID` · `AWS_SECRET_ACCESS_KEY` · `AWS_ACCOUNT_ID` · `AWS_TIMEOUT_SECONDS` |
| Azure | `AZURE_MGMT_BASE_URL` · `AZURE_TENANT_ID` · `AZURE_CLIENT_ID` · `AZURE_CLIENT_SECRET` · `AZURE_SUBSCRIPTION_ID` · `AZURE_ACCESS_TOKEN` · `AZURE_TIMEOUT_SECONDS` |
| GCP | `GCP_POSTURE_BASE_URL` · `GCP_PROJECT_ID` · `GCP_REGION` · service-account JSON **or** access token · `GCP_TIMEOUT_SECONDS` |
| Nessus | `NESSUS_BASE_URL` · `NESSUS_ACCESS_KEY` · `NESSUS_SECRET_KEY` · `NESSUS_TIMEOUT_SECONDS` |
| Qualys | `QUALYS_BASE_URL` · `QUALYS_USERNAME` · `QUALYS_PASSWORD` · `QUALYS_TIMEOUT_SECONDS` |
| Archer | `ECS_ARCHER_BASE_URL` · `ECS_ARCHER_API_TOKEN` · `ECS_ARCHER_TIMEOUT_SECONDS` |
| GitHub | `ECS_GITHUB_BASE_URL` (default `https://api.github.com`) · `ECS_GITHUB_ORG` · `ECS_GITHUB_TOKEN` · `ECS_GITHUB_TIMEOUT_SECONDS` |
| Jenkins | `ECS_JENKINS_BASE_URL` · `ECS_JENKINS_USERNAME` · `ECS_JENKINS_API_TOKEN` · `ECS_JENKINS_TIMEOUT_SECONDS` |
| Azure DevOps | `ECS_AZDO_BASE_URL` (default `https://dev.azure.com`) · `ECS_AZDO_ORG` · `ECS_AZDO_TOKEN` (PAT) · `ECS_AZDO_TIMEOUT_SECONDS` |

> YAML note: the Jira/Confluence/SonarQube *adapters* read the `jira_adapter` /
> `confluence_adapter` / `sonarqube_adapter` YAML blocks (the legacy `jira` /
> `confluence` / `sonarqube` connector entries have a different url/enabled shape).
> Cloud/scanner adapters read the `aws` / `azure` / `gcp` / `nessus` / `qualys`
> YAML blocks (or the `*_connector` aliases) and honour the env vars above.

---

## 4. Registry + REST

`modules.operations.integrations` exposes:
`list_adapters()`, `masked_config_all()`, `health_check_all()`.

REST (see the API guide): `GET /api/audit/integrations`,
`GET /api/audit/integrations/health`, `GET /api/audit/integrations/{name}/health`.

---

## 5. Usage & testing

```python
from modules.operations.integrations import jira

# Production: get_config() reads env/YAML; a real transport is injected at wiring time.
# Tests: inject a mock transport (no network):
def transport(method, url, headers, params):
    return {"issues": [{"key": "J-1", "fields": {"summary": "Fix TLS", "status": {"name": "Open"}}}]}

client = jira.JiraClient(config={"base_url": "https://j", "username": "u",
                                 "api_token": "t"}, transport=transport)
result = client.fetch_issues(jql="project = SEC")
# {"ok": True, "source": "jira", "status": "ok", "items": [{"issue_key": "J-1", ...}], "errors": []}
```

Run the mocked adapter tests (no network — every test injects a mock transport):

```bash
# Core enterprise adapters (Jira/Confluence/SonarQube/Checkmarx/Prisma/Tripwire/…)
PYTHONPATH=. pytest tests/test_integration_adapters_mocked.py
# Cloud posture + vulnerability scanners (AWS/Azure/GCP/Nessus/Qualys)
PYTHONPATH=. pytest tests/test_cloud_security_connectors.py
# MS Graph adapters (SharePoint/Teams/Outlook)
PYTHONPATH=. pytest tests/test_sharepoint_graph_connector.py \
  tests/test_teams_graph_connector.py tests/test_outlook_graph_connector.py
# Connector Test Workbench (config-status / dry-run / parser-test) + executor
PYTHONPATH=. pytest tests/test_connector_test_workbench.py \
  tests/test_connector_execution_ingestion.py
```

**Mock / dry-run modes** (no credentials, no network — see
[connector_test_workbench_design.md](connector_test_workbench_design.md)):
`config_status` (masked config), `dry_run` (reports what *would* run),
`parser_test` (runs the real parser against a synthetic mock transport). Live
collection is opt-in only (`ECS_CONNECTOR_EXECUTION_ENABLED=true` **and** a
configured adapter), via `connector_executor` — evidence collected this way is
uploaded through the standard evidence bridge (SHA-256 + audit-repo mirror).

---

## 6. Behaviour guarantees

- **Secret masking:** `masked_config()` / diagnostics never reveal secret values.
- **Retry/backoff:** timeouts / connection / HTTP errors are retried (bounded);
  `auth_error` / `not_configured` are not (they won't self-heal).
- **Pagination:** `fetch_*` paginates and is bounded by `max_items` / `max_pages`.
- **Graceful degradation:** missing config → `not_configured` (never a crash);
  startup never fails if optional integrations are absent.

---

## 7. Extending / adding an adapter

1. Create `modules/operations/integrations/<name>.py` with `get_config`,
   `is_configured`, `masked_config`, a `<Name>Client(BaseAdapter)`, `fetch_*`,
   `normalize_*`, and `health_check`.
2. Reuse `_base` helpers (`env`, `yaml_block`, `mask_secret`, `collect_paginated`,
   `not_configured_response`).
3. Add its name to `ADAPTER_MODULES` in `__init__.py`.
4. Add config placeholders to `.env.example`, `_base.yaml`, `uat.yaml`.
5. Add mocked tests.

## 8. Limitations & production-security notes

- Skeletons: live OAuth token exchange and production HTTP clients are wired at
  deployment (inject a real `transport`); the default transport refuses live calls.
- `health_check()` is config-based unless a live transport is injected.
- **Cloud posture (AWS/GCP):** these read from a configurable collector/export
  endpoint (`AWS_POSTURE_BASE_URL` / `GCP_POSTURE_BASE_URL`) rather than calling
  the cloud provider SDK directly (no boto3/google-cloud dependency). A live
  deployment provides that collector or injects a signing transport. Azure uses
  OAuth2 client-credentials against the management API.
- **Production security:** use least-privilege, read-only credentials for every
  connector; store secrets in a secret manager / Vault (never in Git); front
  connectors with TLS and, where possible, restrict egress. Secrets are always
  referenced by `*_env` name in YAML and shown only as `SET`/`MISSING`.
- **CI/CD connectors (GitHub, Jenkins, Azure DevOps)** are audit-intelligence
  adapters that **reuse** the `ecs_platform/connectors/` clients via
  `_platform_bridge.py` (see the dual-stack note in §1) — no HTTP/auth duplication.
  Live collection uses the platform connector's real `HttpClient`; workbench and
  dry-run modes inject a mock transport (no network).
