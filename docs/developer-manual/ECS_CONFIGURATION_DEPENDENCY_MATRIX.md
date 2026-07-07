# ECS Configuration Dependency Matrix

Maps every ECS module to its configuration dependencies and the YAML section
that now drives them. Source of truth: `config/environments/<ECS_ENV>.yaml`
(deep-merged over `_base.yaml`) via `config/environment_loader.py`.

Legend — **Current Source**: `env-yaml` = already environment-driven via the
environment loader; `integrations.yaml` / `repository.yaml` / `llm.yaml` =
existing `${VAR}`-driven config files (also surfaced under the env schema);
`static/demo` = deterministic demo data, no external endpoint.
**Migration Required**: `No` = already externalized; `Done` = refactored in this
release; `N/A` = no environment-specific values.

## 2.1 Module → Configuration dependency

| Module | Submodule | Requires YAML Config | Config Category | Current Source | Migration Required |
|--------|-----------|----------------------|-----------------|----------------|--------------------|
| Operations | Scheduler | No (deterministic) | — | static/demo | N/A |
| Operations | Predefined Queries | **Yes** | predefined_query_targets | env-yaml | Done |
| Operations | Integrations Health | **Yes** | connectors | integrations.yaml + env-yaml | No |
| Operations | Onboarding | No | connectivity policy | connectivity.yaml | N/A |
| Operations | Workflow Engine | No | — | static/demo | N/A |
| Operations | Evidence Workflow | No | — | static/demo | N/A |
| Frameworks | C-SITE / PCI-DSS / DPSC / ISG / MBSS / ASST / ITPP / ITDRM | **Yes** | framework_targets → predefined_query_targets | env-yaml | Done |
| Frameworks | OS / DB / Middleware Baselining | **Yes** | predefined_query_targets (os/db/middleware_servers) | env-yaml | Done |
| Frameworks | Application Security / VAPT | **Yes** | predefined_query_targets (appsec_targets) | env-yaml | Done |
| Evidence Governance | Collection | **Yes** | connectors, storage | integrations.yaml + repository.yaml | No |
| Evidence Governance | Repository | **Yes** | databases.postgres, storage.object_store | repository.yaml + env-yaml | No |
| Evidence Governance | Validation / Approval / Reuse / Lifecycle | No | — | databases.postgres | No |
| Evidence Governance | Search | No (optional vector) | vectorstore | vectorstore.yaml | N/A |
| Governance | Governance / Compliance / Risk / Audit / Findings / Remediation dashboards | No | — | databases.postgres | No |
| Executive Overview | Enterprise / Pan India / Trends / Reports / KPIs / Value / ROI | No | reporting.export_path (reports) | env-yaml + roi.yaml | No |
| AI Governance | Model / Prompt Registry, Posture, Risk Monitoring | No | llm | llm.yaml + env-yaml | No |
| AI SDLC | Requirements / Design / Development / Testing / Release / Prod Monitoring | No | — | static/demo | N/A |
| Audit Preparation | Readiness / Control Coverage / Sufficiency / Packages | No | reporting.export_path | env-yaml | No |
| Control Management | Library / Mapping / Validation / Testing | **Yes** | predefined_query_targets | env-yaml | Done |
| Application Inventory | Net Banking / Mobile / Payments / CBS / UPI | **Yes** | applications | env-yaml | Done |
| Connector Framework | Jira / Confluence / ServiceNow / Teams / SharePoint / GitHub / Gitea / Azure DevOps / Jenkins / SonarQube / Prisma | **Yes** | connectors | integrations.yaml + env-yaml | No |
| Infrastructure | Linux / Windows / Oracle / PostgreSQL / MySQL / SQL Server / Nginx / Apache / Middleware | **Yes** | databases, predefined_query_targets | env-yaml | Done |
| Search & Drilldowns | Universal Drilldowns / Tagging / Semantic / Vector Search | No | vectorstore, llm | vectorstore.yaml + llm.yaml | N/A |
| Reporting | Executive / Framework / Audit Reports / Report Packs | **Yes** | reporting.export_path | env-yaml | No |

## 2.2 Connector → YAML mapping

| Connector | YAML key | URL field (default) | Secret env (from integrations.yaml) |
|-----------|----------|---------------------|-------------------------------------|
| Jira         | `connectors.jira`         | `${JIRA_URL}` | `JIRA_TOKEN` / `JIRA_USER` |
| Confluence   | `connectors.confluence`   | `${CONFLUENCE_URL}` | `CONFLUENCE_TOKEN` / `CONFLUENCE_USER` |
| ServiceNow   | `connectors.servicenow`   | `${SNOW_URL}` | `SNOW_USER` / `SNOW_PASSWORD` |
| GitHub       | `connectors.github`       | `${GITHUB_URL:-https://api.github.com}` | `GITHUB_TOKEN` |
| Gitea        | `connectors.gitea`        | `${GITEA_URL:-http://gitea:3000}` | `GITEA_TOKEN` |
| Teams        | `connectors.teams`        | `${MS_GRAPH_URL:-…/v1.0}` | `MS_TENANT_ID` / `MS_CLIENT_ID` / `MS_CLIENT_SECRET` |
| SharePoint   | `connectors.sharepoint`   | `${MS_GRAPH_URL:-…/v1.0}` | `MS_*` / `SHAREPOINT_SITE_ID` |
| Azure DevOps | `connectors.azure_devops` | `${AZDO_URL:-https://dev.azure.com}` | `AZDO_TOKEN` |
| Jenkins      | `connectors.jenkins`      | `${JENKINS_URL:-http://jenkins:8080}` | `JENKINS_USER` / `JENKINS_TOKEN` |
| SonarQube    | `connectors.sonarqube`    | `${SONAR_URL:-http://sonarqube-demo:9000}` | `SONAR_TOKEN` |
| Prisma Cloud | `connectors.prisma_cloud` | `${PRISMA_URL}` | `PRISMA_ACCESS_KEY` / `PRISMA_SECRET_KEY` |
| Figma        | `connectors.figma`        | `${FIGMA_URL:-https://api.figma.com}` | `FIGMA_TOKEN` |

## 2.3 Database → YAML mapping

| Database | YAML key | Host default | Port | Secret env |
|----------|----------|--------------|------|------------|
| PostgreSQL (evidence repository) | `databases.postgres` | `${ECS_REPO_PG_HOST:-postgres}` | 5432 | `ECS_REPO_PG_PASSWORD` |
| PostgreSQL (predefined-query target) | `predefined_query_targets.postgresql` | `${ECS_PG_HOST:-localhost}` | 5432 | `ECS_PG_PASSWORD` |
| Oracle    | `databases.oracle`    | `${DB_ORACLE_HOST}` | 1521 | `DB_ORACLE_PASSWORD` |
| MySQL     | `databases.mysql`     | `${DB_MYSQL_HOST}` | 3306 | `DB_MYSQL_PASSWORD` |
| SQL Server| `databases.sqlserver` | `${DB_SQLSERVER_HOST}` | 1433 | `DB_SQLSERVER_PASSWORD` |

## 2.4 Application → YAML mapping

All under `applications.<key>` with `host` / `port` / `base_url` /
`business_unit` / `criticality` / `enabled`. Keys: `netbanking`,
`mobilebanking`, `payments`, `cbs`, `upi`, `los`, `lms`, `crm`, `treasury`,
`cards`, `trade_finance`, `merchant_acquiring`, `api_gateway`, `middleware`,
`authentication_services`. See `docs/developer-manual/ECS_APPLICATION_CONFIGURATION_MATRIX.md`.

## 2.5 Framework → YAML mapping

All under `framework_targets.<key>` with `enabled` + `target_groups`. Keys:
`csite`, `pci_dss`, `dpsc`, `isg`, `mbss`, `asst`, `itpp`, `itdrm`,
`os_baselining`, `db_baselining`, `middleware_baselining`,
`application_security`, `vapt`. Each `target_groups` entry references a key in
`predefined_query_targets` (`os_servers`, `db_servers`, `middleware_servers`,
`appsec_targets`).

## 2.6 Storage / Auth / LLM / Reporting

| Capability | YAML key | Defaults / env |
|------------|----------|----------------|
| Object store | `storage.object_store` | `${MINIO_ENDPOINT:-minio:9000}`, `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` |
| SSO | `authentication.sso` | `${ECS_SSO_ENABLED}`, `ECS_SSO_CLIENT_ID` / `ECS_SSO_CLIENT_SECRET` |
| LLM | `llm` | `${ECS_LLM_PROVIDER:-ollama}`, `${OLLAMA_URL}` |
| Reporting | `reporting.export_path` | `${ECS_REPORT_EXPORT_PATH}` |
