# ECS P1 Engineering Gap Analysis

**Mode:** READ-ONLY / ANALYSIS / DOCUMENTATION. **No code/UI/CSS changes. No commits/pushes. No file changes outside `docs/`.** **Inputs:** `ECS_PHASE1_GO_LIVE_READINESS_REPORT.md`, `ECS_PREDEFINED_QUERY_READINESS_REPORT.md`, `ECS_CONNECTOR_READINESS_REPORT.md`, `ECS_LOCAL_LLM_VALIDATION_REPORT.md`, `ECS_WORKFLOW_VALIDATION_REPORT.md`. **Grounding:** direct source inspection (paths cited per finding).

> ### ⚠ Correction to prior readiness reports (verified this pass)
> Deeper inspection revised two earlier conclusions — applied throughout this analysis:
> 1. **Predefined-query execution is NOT entirely interface-only.** `modules/operations/engines/predefined_queries_engine.run_predefined_query()` wires **concrete, working execution** for **PostgreSQL** (`postgresql_connector.py`, psycopg2), **Linux** (`linux_connector.py`, `docker exec`), **SonarQube** (`sonarqube_connector.py`, API), **Trivy** & **Gitleaks** (`*_connector.py`, subprocess). Only the **generic** `DatabaseConnector` / `SSHConnector` / `APIConnector` in `query_connectors.py` raise `NotImplementedError` (i.e., remote Oracle/MySQL/SQL Server, SSH hosts, generic APIs).
> 2. **Observation durability is implemented**, not absent. `app/observations/store.py` is a write-through durable store (upsert/close/reopen + `hydrate_into_memory()` + `migrate_memory_to_durable()`), already called from `app/main.py`, **gated by `OBSERVATIONS_DURABLE_ENABLED` (default FALSE)**. The gap is **enablement + migration + validation**, not a build.

---

## P1-01 — Predefined-query execution for **production (non-demo) targets**

| Aspect | Detail |
|---|---|
| **Root cause** | Concrete execution exists only for demo connectors (PostgreSQL/Linux/SonarQube/Trivy/Gitleaks). Generic remote-target connectors are stubs: `DatabaseConnector.execute()`, `SSHConnector.execute()`, `APIConnector.execute()` all `raise NotImplementedError("…execution not yet enabled")`. |
| **Affected modules** | `modules/operations/engines` (predefined queries), `config/environments` |
| **Files** | `query_connectors.py` (L123–166 stubs), `predefined_queries_engine.py` (`run_predefined_query`, L676+), `connector_common.py`, `_base.yaml` (`predefined_query_targets`) |
| **Dependencies** | psycopg2 (have), Oracle (`oracledb`/cx_Oracle — **new**), MySQL (`mysqlclient`/`PyMySQL` — **new**), SQL Server (`pyodbc` — **new**), SSH (`paramiko` — **new**); network access + read-only service accounts to prod targets |
| **Estimated effort** | **8–13 eng-days** (DatabaseConnector multi-engine ~5d, SSHConnector ~3d, APIConnector ~2d, tests ~3d) |
| **Technical risk** | Medium — driver/dialect differences, network/firewall, credential handling, query-dialect portability |
| **Business risk** | High if live evidence collection from prod DB/OS is a Phase-1 commitment; otherwise Medium |
| **UAT impact** | UAT can validate demo-target execution today; remote-target execution untestable until built + targets provisioned |
| **Production impact** | Blocks automated evidence from remote Oracle/MySQL/SQL Server/SSH/API targets; demo-class targets unaffected |

## P1-02 — Source connectors disabled & unvalidated against real tenants

| Aspect | Detail |
|---|---|
| **Root cause** | SaaS/enterprise connectors are runtime-complete but `enabled: false` by default (no-secrets-in-repo posture); never exercised against real tenant endpoints |
| **Affected modules** | `ecs_platform/connectors`, `ecs_platform/ingestion.py` |
| **Files** | `factory.py` (`_REGISTRY`), `jira_connector.py`, `confluence_connector.py`, `servicenow_connector.py`, `sharepoint_connector.py`, `teams_connector.py` (+ `_msgraph.py`, `http_client.py`), `config/integrations.yaml` |
| **Dependencies** | Tenant URLs + credentials (env/vault), network egress, Azure AD app registration (Graph: SharePoint/Teams) |
| **Estimated effort** | **3–5 eng-days** (config + per-connector connectivity validation; no code expected) |
| **Technical risk** | Low–Medium — auth flows (OAuth2 client credentials, PAT), TLS, rate limits |
| **Business risk** | Medium — evidence ingestion from systems of record pending validation |
| **UAT impact** | Required for UAT connectivity sign-off |
| **Production impact** | Connectors must be enabled + validated per tenant before go-live |

## P1-03 — Per-environment predefined-query target lists empty

| Aspect | Detail |
|---|---|
| **Root cause** | `predefined_query_targets.{os_servers,db_servers,middleware_servers,appsec_targets}` default to `[]` in `_base.yaml`; env files don't yet populate them |
| **Affected modules** | `config/environments` |
| **Files** | `_base.yaml`, `uat.yaml`, `prod.yaml`; override via `ECS_TARGET_OS_SERVERS`/`_DB_SERVERS`/`_MW_SERVERS`/`_APPSEC` |
| **Dependencies** | CMDB/asset inventory, network reachability, P1-01 (remote execution) for the lists to be actionable |
| **Estimated effort** | **1–2 eng-days** (config population + review) |
| **Technical risk** | Low (config only) |
| **Business risk** | Medium — no remote targets = no remote evidence |
| **UAT impact** | Populate UAT lists to validate end-to-end |
| **Production impact** | Required for production scope of automated queries |

## P1-04 — Production security hardening (SSO/OIDC, at-rest encryption)

| Aspect | Detail |
|---|---|
| **Root cause** | SSO slots disabled (`ECS_SSO_ENABLED:-false`); at-rest encryption is infra-dependent (`MINIO_SECURE`, Postgres TDE/disk) |
| **Affected modules** | `app/auth`, `config/auth.yaml`, `config/environments/_base.yaml` (`authentication`, `storage`), infra |
| **Files** | `config/auth.yaml`, `_base.yaml` (`authentication.sso`, `storage.object_store.secure`), deployment manifests |
| **Dependencies** | Enterprise IdP (OIDC/SAML metadata, client id/secret), KMS/disk encryption, vault for secrets |
| **Estimated effort** | **3–6 eng-days** (OIDC wiring/validation ~3d, encryption verification + secrets ~2d) — plus infra team |
| **Technical risk** | Medium — IdP integration, token/session handling |
| **Business risk** | High — production auth + data-at-rest are compliance prerequisites (PCI/RBI) |
| **UAT impact** | Validate OIDC in UAT with non-prod IdP |
| **Production impact** | Hard gate — cannot go live without enterprise auth + encryption verified |

## P1-05 — Observation durable persistence **enablement** (not build)

| Aspect | Detail |
|---|---|
| **Root cause** | Write-through durable store implemented but **flag-gated off** (`OBSERVATIONS_DURABLE_ENABLED` default FALSE); in-memory remains primary read path |
| **Affected modules** | `app/observations`, `ecs_platform/repository`, `modules/shared/services/ecs_state.py` |
| **Files** | `app/observations/store.py` (persist/hydrate/migrate), `ecs_platform/repository/repository.py` (`upsert/get/close/reopen/list_observation`), `ecs_platform/repository/schema.sql` (`observations`), `app/main.py` (hydrate-on-startup, persist-on-close/reopen) |
| **Dependencies** | Reachable Postgres repository; one-time `migrate_memory_to_durable()` run |
| **Estimated effort** | **2–4 eng-days** (enable flag, run migration, validate hydration/restart durability, regression test) |
| **Technical risk** | Low — best-effort design (errors swallowed, never breaks workflow); memory-wins-on-conflict |
| **Business risk** | Medium — audit integrity/restart durability of observations |
| **UAT impact** | Validate persistence + restart hydration in UAT with flag ON |
| **Production impact** | Enable flag in prod for durable observations + audit chain (`observation.*` events) |

---

## Summary table

| ID | Gap | True nature | Effort | Tech risk | Prod gate |
|---|---|---|---:|---|---|
| P1-01 | Remote-target query execution | Build generic DB/SSH/API connectors | 8–13d | Med | If remote evidence in scope |
| P1-02 | Source connector validation | Enable + validate (config) | 3–5d | Low–Med | Yes (per tenant) |
| P1-03 | Target lists empty | Config population | 1–2d | Low | Yes |
| P1-04 | SSO + at-rest encryption | Wire + verify (+infra) | 3–6d | Med | **Hard gate** |
| P1-05 | Observation durability | Enable + migrate + validate | 2–4d | Low | Recommended |

**Total P1 effort: ~17–30 eng-days** (≈3.5–6 eng-weeks for one engineer; ~2–3 calendar weeks with 2–3 engineers + infra support). Demo/UAT is GO today; these close production live-evidence + compliance gates.

## Cross-references
- [Predefined Query Implementation Plan](ECS_PREDEFINED_QUERY_IMPLEMENTATION_PLAN.md) · [Observation Workflow Plan](ECS_OBSERVATION_WORKFLOW_IMPLEMENTATION_PLAN.md) · [RAF Plan](ECS_RAF_IMPLEMENTATION_PLAN.md) · [Connector Activation Plan](ECS_CONNECTOR_ACTIVATION_PLAN.md) · [Execution Roadmap](ECS_PHASE1_EXECUTION_ROADMAP.md)
- Source reports: [Go-Live](../../../../05-archive/archive/ECS_PHASE1_GO_LIVE_READINESS_REPORT.md) · [Predefined Query Readiness](../../../../03-development/operations/ECS_PREDEFINED_QUERY_READINESS_REPORT.md) · [Connector Readiness](../../../../03-development/operations/ECS_CONNECTOR_READINESS_REPORT.md) · [Workflow Validation](../../../../04-testing/testing/ECS_WORKFLOW_VALIDATION_REPORT.md)
