# ECS Connector Readiness Report (Phase 1)

**Mode:** READ-ONLY / ANALYSIS / REPORTING. **No connector implementation changes. No commits.** **Grounding:** `ecs_platform/connectors/*` (real connector clients), `ecs_platform/ingestion.py` (`sync_connector`), `ecs_platform/connectors/http_client.py` + `_msgraph.py`, `modules/operations/engines/query_connectors.py` (interfaces only), `config/integrations.yaml`, `config/environments/_base.yaml`. Complements [Integrations Index](../developer-manual/connectors/_legacy_INTEGRATIONS_index.md).

> **Two connector classes in ECS:**
> 1. **Source-system connectors** (`ecs_platform/connectors/`) — real runtime clients with `sync()` invoked by `sync_connector()`; HTTP via `http_client`/`_msgraph`; gated by `enabled` flags; resilient (a bad connector returns a structured failure, never a 500).
> 2. **Predefined-query connectors** (`query_connectors.py`) — **interfaces only, no runtime execution** (per module docstring); targets sourced from the environment layer with a static demo fallback.

---

## 1. Readiness matrix

| Connector | Class | Runtime client | Default enabled | Readiness |
|---|---|---|---|---|
| **PostgreSQL** | Query target | ❌ interface-only (`query_connectors`) | demo target | **Partial** — target config wired, allow-listed read-only queries; no execution runtime shipped |
| **Linux** | Query target | ❌ interface-only | demo target (`ubuntu-demo`) | **Partial** |
| **SonarQube** | Source + query target | ✅ `sonarqube_connector.py` | `true` (dev) | **Implemented** (ingestion runtime); also a query target |
| **Trivy** | Query target | ❌ interface-only | demo target | **Partial** |
| **Gitleaks** | Query target | ❌ interface-only | demo target | **Partial** |
| **Jira** | Source | ✅ `jira_connector.py` | `false` | **Implemented**, disabled until configured |
| **Confluence** | Source | ✅ `confluence_connector.py` | `false` | **Implemented**, disabled |
| **ServiceNow** | Source | ✅ `servicenow_connector.py` | `false` | **Implemented**, disabled |
| **SharePoint** | Source (MS Graph) | ✅ `sharepoint_connector.py` + `_msgraph.py` | `false` | **Implemented**, disabled |
| **Teams** | Source (MS Graph) | ✅ `teams_connector.py` + `_msgraph.py` | `false` | **Implemented**, disabled |

> Also shipped source connectors (not in the requested list): Gitea (`true`), Jenkins (`true`), GitHub, Azure DevOps, Prisma Cloud, Figma — all real clients via `factory.py`. **12 source connectors total.**

## 2. Classification

### Implemented (interface + runtime)
SonarQube, Jira, Confluence, ServiceNow, SharePoint, Teams (+ Gitea, Jenkins, GitHub, Azure DevOps, Prisma, Figma). Each has a connector client with `sync()`, env-resolved config, TLS (`verify_ssl`), fail-fast health checks (`timeout_sec=10`, `max_retries=1`), and audit-logged ingestion. **Disabled by default** except self-hostable dev systems (Gitea/SonarQube/Jenkins).

### Partial (interface only — no execution runtime)
PostgreSQL, Linux, Trivy, Gitleaks (and Oracle/MySQL/SQL Server/Nginx/Tomcat targets). `query_connectors.py` defines the interfaces + target maps; **actual query execution against live targets is not implemented** — demo reports deterministically via static fallback. Requires `CONNECTOR_CONFIG` + execution runtime to go live.

### Future
- Execution runtime for predefined-query connectors (PostgreSQL/Linux/Trivy/Gitleaks/Oracle/etc.).
- Additional MS Graph scopes; OAuth refresh automation; per-connector retry/backoff tuning.

## 3. Gap classification

| ID | Finding | Severity | Recommendation (document only — DO NOT IMPLEMENT) |
|---|---|---|---|
| CN-P2-01 | Predefined-query connectors are interface-only (no live execution) | **P2** | Document as Phase-2 build item; demo/UAT uses deterministic fallback. Do not implement under read-only mandate. |
| CN-P3-01 | Source connectors disabled by default | **P3** | Expected (no-secrets-in-repo posture); document per-env enablement (env vars + `enabled:true`). |
| CN-P3-02 | Live source-connector validation needs real tenants | **P3** | Plan UAT connectivity tests with tenant credentials. |

## 4. Verdict
**Connector layer: GO for demo/UAT.** Source-system connectors are runtime-complete and safely disabled until configured (no code change to onboard — env vars only). Predefined-query connectors are interface-complete (Partial) and documented as a Phase-2 execution-runtime build. No connector code modified.

## Cross-references
- [Integrations Index](../developer-manual/connectors/_legacy_INTEGRATIONS_index.md) · [Predefined Query Readiness](ECS_PREDEFINED_QUERY_READINESS_REPORT.md) · [Environment Framework Review](ECS_ENVIRONMENT_FRAMEWORK_REVIEW.md) · [Connector Failure Playbook](ECS_CONNECTOR_FAILURE_PLAYBOOK.md)
