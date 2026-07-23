# ECS Runtime Call Graph & Sequence Diagrams

**Status:** Current · **Owner:** Audit Intelligence / Platform

> Derived from repository inspection. Every endpoint, service, and class named
> below exists in the repository (see the connector/scheduler/workbench references
> for source paths). No APIs are invented.

This document maps ECS runtime from FastAPI endpoint → service → repository →
connector → parser → validation → observation → dashboard → LLM, and provides
sequence diagrams for the key flows.

---

## 1. High-level call graph

```mermaid
flowchart TD
    subgraph API["FastAPI endpoints"]
      A1["/api/connectors/*"]
      A2["/api/evidence-reuse/*"]
      A3["/api/audit/integrations*"]
      A4["/api/audit/observations*"]
      A5["/api/audit/dashboard"]
      A6["/api/audit/packs"]
      A7["/api/audit-llm/query"]
    end
    subgraph SVC["Services"]
      S1["connector_workbench"]
      S2["evidence_reuse_service"]
      S3["evidence_service"]
      S4["audit_repository_service"]
      S5["dashboard_service"]
      S6["asset_scheduler"]
      S7["llm/execution_service"]
    end
    subgraph ENG["Engines / repositories"]
      E1["integrations registry + adapters"]
      E2["evidence_orchestrator"]
      E3["evidence_repository (SHA-256)"]
      E4["evidence_validation"]
      E5["observation_generation"]
      E6["evidence_packs"]
      E7["technology_control_mapping"]
      E8["asset_discovery / technology_fingerprint"]
    end
    RAG["ecs_platform/rag.py::answer"]

    A1 --> S1 --> E1
    A2 --> S2 --> E3
    S2 --> E4
    S2 --> E5
    S2 --> E7
    A3 --> E1
    A4 --> S4 --> E5
    A5 --> S5 --> E3
    A6 --> S4 --> E6
    A7 --> S7 --> RAG
    S6 --> E8
    S6 --> E7
    S6 --> E1
    S6 --> S3 --> E2 --> E3
    E2 --> E4 --> E5
    S5 --> RAG
```

## 2. Endpoint → service → downstream (reference table)

| Endpoint | Service | Downstream |
| --- | --- | --- |
| `GET /api/connectors` | `connector_workbench.list_connectors` | integrations registry |
| `GET /api/connectors/{name}/config-status` | `connector_workbench.config_status` | `integrations.<name>.masked_config` |
| `POST /api/connectors/{name}/health-check` | `connector_workbench.health_check` | `integrations.<name>.health_check` |
| `POST /api/connectors/{name}/dry-run` | `connector_workbench.dry_run` | adapter primary method (no call) |
| `POST /api/connectors/{name}/parser-test` | `connector_workbench.parser_test` | adapter `fetch_*`/`normalize_*` (mock) |
| `GET /connectors/test-workbench` | `connector_test_workbench` (route) | `connector_workbench.list_connectors` |
| `GET /api/evidence-reuse/records` | `evidence_reuse_service.records` | `evidence_repository.search` |
| `POST /api/evidence-reuse/analyze` | `evidence_reuse_service.analyze` | repository + `technology_control_mapping` |
| `POST /api/evidence-reuse/validate-completeness` | `evidence_reuse_service.validate_completeness` | repository + mapping |
| `POST /api/evidence-reuse/generate-observations` | `evidence_reuse_service.generate_observations` | `observation_generation` |
| `POST /api/evidence-reuse/check-closure` | `evidence_reuse_service.check_closure` | `observation_generation.transition` |
| `GET /api/evidence-reuse/readiness` | `evidence_reuse_service.readiness` | repository + mapping |
| `GET /api/evidence-reuse/observations` | `evidence_reuse_service.observations` | `observation_generation` |
| `GET /api/audit/integrations` | (route) | `integrations.masked_config_all` |
| `GET /api/audit/integrations/health` | (route) | `integrations.health_check_all` |
| `GET /api/audit/integrations/{name}/health` | (route) | `integrations.<name>.health_check` |
| `GET /api/audit/observations` | `audit_repository_service.list_observations` | `observation_generation.list_observations` |
| `POST /api/audit/observations/{id}/transition` | `audit_repository_service.transition_observation` | `observation_generation.transition` |
| `GET /api/audit/dashboard` | `dashboard_service` | repository + observations |
| `GET /api/audit/packs` | `audit_repository_service` | `evidence_packs` |
| `POST /api/audit-llm/query` | `llm/execution_service.execute` | `ecs_platform/rag.py::answer` |

> CLI (not REST): `scripts/run_uat_asset_scheduler.py` → `asset_scheduler.dry_run`.

---

## 3. Sequence diagrams

Connector fetches (1–7) share the pattern from
`docs/03-development/developer-manual/connectors/enterprise_connector_api_reference.md §3`; each is shown with its concrete
endpoints. In the **workbench** context the transport is an in-process mock; in
**scheduler execution** it is a real transport. Adapters never raise (errors are
classified into the standard status vocabulary).

### 3.1 SharePoint fetch

```mermaid
sequenceDiagram
    participant Caller
    participant SP as SharePointGraphClient
    participant AAD as Azure AD
    participant G as Microsoft Graph
    Caller->>SP: fetch_drive_items()
    SP->>SP: is_configured()? (tenant+client+secret+site_id)
    SP->>AAD: authenticate() POST oauth2/v2.0/token (client_credentials)
    AAD-->>SP: access_token (cached)
    SP->>G: GET /drives/{drive_id}/root/children?$top=N (Bearer)
    G-->>SP: { value:[...], @odata.nextLink }
    loop nextLink until end / max_items / max_pages
        SP->>G: GET nextLink
        G-->>SP: { value:[...] }
    end
    SP->>SP: normalize_item() (evidence_type=sharepoint_document)
    SP-->>Caller: { ok, source, status, items }
```

### 3.2 Teams fetch

```mermaid
sequenceDiagram
    participant Caller
    participant TM as TeamsGraphClient
    participant AAD as Azure AD
    participant G as Microsoft Graph
    Caller->>TM: fetch_channels(team_id)
    TM->>AAD: authenticate() (client_credentials)
    AAD-->>TM: access_token
    TM->>G: GET /teams/{team_id}/channels (Bearer)
    G-->>TM: { value:[...], @odata.nextLink }
    TM->>TM: normalize_channel() (evidence_type=teams_channel)
    TM-->>Caller: { ok, items }
```

### 3.3 Outlook fetch

```mermaid
sequenceDiagram
    participant Caller
    participant OL as OutlookGraphClient
    participant AAD as Azure AD
    participant G as Microsoft Graph
    Caller->>OL: fetch_messages(user_id, folder)
    OL->>OL: is_configured()? (Graph creds + user_id)
    OL->>AAD: authenticate() (client_credentials)
    AAD-->>OL: access_token
    OL->>G: GET /users/{user_id}/mailFolders/{folder}/messages?$top=N
    G-->>OL: { value:[...], @odata.nextLink }
    OL->>OL: normalize_message() (evidence_type=outlook_message)
    OL-->>Caller: { ok, items }
```

### 3.4 Jira fetch

```mermaid
sequenceDiagram
    participant Caller
    participant J as JiraClient
    participant JR as Jira REST API
    Caller->>J: fetch_issues(jql)
    J->>J: is_configured()? (base_url+username+api_token)
    loop startAt/maxResults (collect_paginated)
        J->>JR: GET /rest/api/{v}/search?jql=..&startAt=..&maxResults=.. (Basic auth)
        JR-->>J: { issues:[...] } | classified error
    end
    J->>J: normalize_issue() (evidence_type=jira_issue)
    J-->>Caller: { ok, items }
```

### 3.5 Confluence fetch

```mermaid
sequenceDiagram
    participant Caller
    participant C as ConfluenceClient
    participant CF as Confluence REST API
    Caller->>C: fetch_pages(space_key)
    C->>C: is_configured()? (base_url+username+api_token)
    loop pagination (collect_paginated)
        C->>CF: GET /wiki/rest/api/content?spaceKey=.. (Basic auth)
        CF-->>C: { results:[...] }
    end
    C->>C: normalize_page() (evidence_type=confluence_page)
    C-->>Caller: { ok, items }
```

### 3.6 Prisma Cloud fetch

```mermaid
sequenceDiagram
    participant Caller
    participant P as PrismaCloudClient
    participant PC as Prisma Cloud API
    Caller->>P: fetch_alerts()
    P->>P: is_configured()? (base_url+access_key+secret_key)
    P->>PC: POST /login (access_key, secret_key)
    PC-->>P: { token } (JWT, cached)
    loop offset/limit (collect_paginated)
        P->>PC: GET /v2/alert?offset=..&limit=.. (x-redlock-auth: token)
        PC-->>P: { items:[...] }
    end
    P->>P: normalize_alert()
    P-->>Caller: { ok, items }
```

### 3.7 ServiceNow fetch

```mermaid
sequenceDiagram
    participant Caller
    participant SN as ServiceNowAdapter
    participant AUTH as ServiceNow OAuth (oauth_token.do)
    participant T as ServiceNow Table API
    Caller->>SN: fetch_servers(sysparm_query)
    SN->>SN: is_configured()? (base_url + OAuth or Basic)
    alt auth_mode=oauth
        SN->>AUTH: POST /oauth_token.do (client_credentials)
        AUTH-->>SN: { access_token } (cached; Bearer)
    else auth_mode=basic
        SN->>SN: basic_auth_header(username,password)
    end
    loop sysparm_limit/offset (collect_paginated)
        SN->>T: GET /api/now/table/cmdb_ci_server?sysparm_limit=..&sysparm_offset=..
        T-->>SN: { result:[...] }
    end
    SN->>SN: normalize_ci() (evidence_type=cmdb_ci)
    SN-->>Caller: { ok, items }
```

### 3.8 Scheduler batch run

```mermaid
sequenceDiagram
    participant CLI as run_uat_asset_scheduler.py
    participant SCH as asset_scheduler
    participant DISC as asset_discovery
    participant MAP as technology_control_mapping
    participant REG as integrations registry
    participant EVS as evidence_service
    participant REPO as evidence_repository
    participant VAL as evidence_validation
    participant OBS as observation_generation
    CLI->>SCH: dry_run(config_path)
    SCH->>DISC: discover_from_manual() (fingerprint)
    DISC-->>SCH: Asset[]
    loop each asset
        SCH->>SCH: classify_asset() (route via _CONNECTOR_ROUTES)
        SCH->>MAP: controls/frameworks for technology
    end
    SCH->>REG: config-only readiness per connector
    SCH-->>CLI: dry-run report (NO live calls)
    note over CLI,OBS: execute_plan() (opt-in)
    CLI->>EVS: start_run() baseline jobs
    EVS->>REPO: store_from_run() (SHA-256)
    EVS->>VAL: validate_records()
    VAL->>OBS: generate_observation() (FAIL/WARNING)
```

### 3.9 Evidence reuse

```mermaid
sequenceDiagram
    participant UI as Evidence Reuse page
    participant API as /api/evidence-reuse/analyze
    participant SVC as evidence_reuse_service.analyze
    participant REPO as evidence_repository
    participant MAP as technology_control_mapping
    UI->>API: POST analyze (filters)
    API->>SVC: analyze(filters)
    SVC->>REPO: search(latest_only) (+ ensure_seeded)
    REPO-->>SVC: EvidenceArtifact[]
    loop each record
        SVC->>MAP: frameworks_for_control() (fallback)
    end
    SVC-->>API: { reuse_summary (reuse_factor, effort_saved), reuse_rows }
    API-->>UI: JSON (matrix + KPIs)
```

### 3.10 Observation creation

```mermaid
sequenceDiagram
    participant API as /api/evidence-reuse/generate-observations
    participant SVC as evidence_reuse_service.generate_observations
    participant COMP as validate_completeness
    participant OBS as observation_generation
    API->>SVC: POST generate-observations (filters)
    SVC->>COMP: validate_completeness() -> gaps (missing/failed/stale)
    loop each gap without existing open observation
        SVC->>OBS: generate_observation(ValidationResult)
        OBS-->>SVC: Observation (Draft) + history[created]
    end
    SVC-->>API: { created_count, created[], skipped_existing }
```

### 3.11 Observation closure

```mermaid
sequenceDiagram
    participant API as /api/evidence-reuse/check-closure
    participant SVC as evidence_reuse_service.check_closure
    participant REPO as evidence_repository
    participant OBS as observation_generation
    API->>SVC: POST check-closure (require_approval)
    SVC->>REPO: records() -> satisfied controls
    loop each open observation with satisfying evidence
        alt require_approval=true (maker-checker)
            SVC->>OBS: transition(Draft->Submitted) (READY FOR CLOSURE; not closed)
        else require_approval=false
            SVC->>OBS: transition(... -> Closed)
        end
        OBS-->>SVC: updated Observation (+history)
    end
    SVC-->>API: { ready_for_closure[], closed[], not_eligible[] }
```

### 3.12 Audit LLM query

```mermaid
sequenceDiagram
    participant UI as Audit LLM Workbench
    participant API as /api/audit-llm/query
    participant EXE as llm/execution_service.execute
    participant DR as deterministic_router
    participant CB as context_builder
    participant RAG as ecs_platform/rag.py::answer
    participant P as LLM provider (ecs_platform/llm_engine)
    UI->>API: POST query { question, ... }
    API->>EXE: execute(...)
    EXE->>DR: build_deterministic_context()
    EXE->>CB: build_context()
    EXE->>RAG: answer(question, role, top_k, application, framework)
    RAG->>P: get_provider() (if grounded) 
    P-->>RAG: completion
    RAG-->>EXE: { ok, grounded, answer, citations, diagnostics }
    EXE-->>API: response
    API-->>UI: JSON (answer + citations)
```

> Note: `answer()` returns `grounded=false` with `mode='fallback'` when no LLM key
> is configured (deterministic assistant is used instead).

---

## 4. Related documentation

- `docs/03-development/developer-manual/connectors/enterprise_connector_api_reference.md`
- `docs/03-development/developer-manual/connectors/microsoft_graph_connector_api_reference.md`
- `docs/03-development/developer-manual/connectors/connector_test_workbench_design.md`
- `docs/03-development/developer-manual/phase1/scheduler/scheduler_runtime_flow.md`
- `docs/03-development/developer-manual/phase1/scheduler/test_workbench_vs_scheduler.md`
- `docs/03-development/evidence-management/evidence_reuse_lifecycle_functional_design.md`
