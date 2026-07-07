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

> The three Microsoft Graph connectors share `ms_graph_base.py` (OAuth2
> client-credentials + `@odata.nextLink` pagination). See
> [MS_GRAPH_CONNECTOR_GUIDE.md](MS_GRAPH_CONNECTOR_GUIDE.md) and
> [ENTERPRISE_CONNECTOR_UAT_SETUP.md](ENTERPRISE_CONNECTOR_UAT_SETUP.md).

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

> YAML note: the Jira/Confluence/SonarQube *adapters* read the `jira_adapter` /
> `confluence_adapter` / `sonarqube_adapter` YAML blocks (the legacy `jira` /
> `confluence` / `sonarqube` connector entries have a different url/enabled shape).

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

Run the mocked adapter tests:

```bash
PYTHONPATH=. pytest tests/test_integration_adapters_mocked.py
```

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

## 8. Limitations

- Skeletons: live OAuth token exchange and production HTTP clients are wired at
  deployment (inject a real `transport`); the default transport refuses live calls.
- `health_check()` is config-based unless a live transport is injected.
