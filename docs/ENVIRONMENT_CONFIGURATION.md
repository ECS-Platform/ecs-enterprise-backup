# ECS — Environment Configuration Reference

Every environment variable ECS reads, derived from `.env.example`, `ecs_platform/config/loader.py`, and the YAML configs it resolves (`config/auth.yaml`, `config/rbac.yaml`, `config/llm.yaml`, `config/vectorstore.yaml`, `config/repository.yaml`, `config/integrations.yaml`, `config/roi.yaml`, `config/sufficiency.yaml`) plus `docker-compose.yml`.

## How configuration resolves

- **`.env` → `os.environ`:** `app/env_bootstrap.py` loads the repo-root `.env` at process start (`python-dotenv`, with a built-in fallback parser), **without overriding** values already in the environment (`override=False`). So container/CI env always wins over `.env`.
- **`${VAR}` / `${VAR:-default}` in YAML:** `ecs_platform/config/loader.py` substitutes env placeholders at load time and coerces `true/false`/integers. Empty string counts as "unset" and falls through to the default. No secrets live in YAML — every secret resolves from the environment.
- **Defaults below** are the YAML `${VAR:-default}` values (authoritative) or the `.env.example` placeholder where no YAML default exists.

**Legend — Required:** ✅ effectively required for the stated mode · ⚪ optional (has a working default) · 🔧 runtime-only (set automatically by Docker Compose).

---

## 1. Core / demo flags

| Variable | Required | Default | Purpose | Demo Override |
|---|:--:|---|---|---|
| `DEMO_MODE` | ✅ (demo) | `false` | Single master switch: when `true`, bypasses auth middleware, RBAC enforcement, and page/dashboard guards so every route loads without tokens. POC-only. | `true` |
| `ECS_AUTH_ENABLED` | ✅ (demo) | `true` (secure-by-default) | Master auth switch. `true` requires a valid identity on non-public paths. Set `false` for a no-IdP demo. | `false` |
| `ECS_CONFIG_DIR` | ⚪ | repo-root `/config` | Override the directory the config loader reads YAML from. | unset |

> For a native demo run **you must set `DEMO_MODE=true` and `ECS_AUTH_ENABLED=false`** — otherwise auth is on (secure-by-default) and pages return `401 unauthorized` without a token.

---

## 2. Authentication (`config/auth.yaml`)

| Variable | Required | Default | Purpose | Demo Override |
|---|:--:|---|---|---|
| `ECS_AUTH_PROVIDER` | ⚪ | `azure_ad` | Active IdP: `azure_ad` \| `oidc` \| `dev`. | (n/a, auth off) |
| `ECS_AZURE_TENANT_ID` | ⚪ (prod azure) | empty | Azure AD tenant id. | empty |
| `ECS_AZURE_CLIENT_ID` | ⚪ (prod azure) | empty | Azure AD app (client) id. | empty |
| `ECS_AZURE_ISSUER` | ⚪ | derived from tenant | Override issuer (sovereign clouds). | empty |
| `ECS_AZURE_JWKS_URI` | ⚪ | derived from tenant | Override JWKS URI. | empty |
| `ECS_OIDC_ISSUER` | ⚪ (oidc) | empty | Generic OIDC issuer (Okta/Keycloak…). | empty |
| `ECS_OIDC_JWKS_URI` | ⚪ (oidc) | empty | OIDC JWKS endpoint. | empty |
| `ECS_OIDC_CLIENT_ID` | ⚪ (oidc) | empty | OIDC client id. | empty |
| `ECS_AUTH_ALLOWED_AUDIENCES` | ⚪ | empty (→ client id) | Comma-separated accepted token audiences. | empty |
| `ECS_AUTH_LEEWAY_SECONDS` | ⚪ | `60` | Clock-skew tolerance for exp/nbf. | `60` |
| `ECS_AUTH_CLAIM_USER_ID` | ⚪ | `oid` | Claim → user id. | default |
| `ECS_AUTH_CLAIM_USERNAME` | ⚪ | `preferred_username` | Claim → username. | default |
| `ECS_AUTH_CLAIM_DISPLAY_NAME` | ⚪ | `name` | Claim → display name. | default |
| `ECS_AUTH_CLAIM_EMAIL` | ⚪ | `email` | Claim → email. | default |
| `ECS_AUTH_CLAIM_ROLES` | ⚪ | `roles` | Claim → roles. | default |
| `ECS_AUTH_CLAIM_GROUPS` | ⚪ | `groups` | Claim → groups (used by scope filtering). | default |
| `ECS_AUTH_DEV_MODE` | ⚪ | `false` | Local dev bypass: authenticate as a static principal **without** an IdP. Alternative to `DEMO_MODE` when you still want auth wiring on. | `false` (use `DEMO_MODE` instead) |
| `ECS_AUTH_DEV_USER_ID` | ⚪ | `dev-user` | Dev-mode principal user id. | default |
| `ECS_AUTH_DEV_USERNAME` | ⚪ | `developer` | Dev-mode username. | default |
| `ECS_AUTH_DEV_DISPLAY_NAME` | ⚪ | `Local Developer` | Dev-mode display name. | default |
| `ECS_AUTH_DEV_EMAIL` | ⚪ | `developer@localhost` | Dev-mode email. | default |
| `ECS_AUTH_DEV_ROLES` | ⚪ | `admin` | Dev-mode roles (drives RBAC later). | default |
| `ECS_AUTH_DEV_GROUPS` | ⚪ | empty | Dev-mode groups (drives scope). | empty |
| `ECS_AUTH_PUBLIC_PATHS` | ⚪ | `/,/login,/healthz,/readyz,/static,/static/ecs,/favicon.ico` | Paths that never require auth. | default |

**Can ECS run without these?** Yes — with `ECS_AUTH_ENABLED=false` (or `DEMO_MODE=true`) none of the Azure/OIDC values are needed. For production you must set the provider + its issuer/client values.

---

## 3. Authorization / RBAC (`config/rbac.yaml`, phased — all default OFF)

| Variable | Required | Default | Purpose | Demo Override |
|---|:--:|---|---|---|
| `ECS_RBAC_DELEGATION_ENABLED` | ⚪ | `false` | Route capability predicates through the consolidated PolicyEngine (legacy-parity). | `false` |
| `RBAC_ENFORCEMENT_ENABLED` | ⚪ | `false` | Derive effective role from the authenticated principal (foundation; not yet route-attached alone). | `false` |
| `RBAC_MUTATION_ENFORCEMENT_ENABLED` | ⚪ | `false` | Enforce permissions on high-risk mutation endpoints (escalate, assign-owner, connector sync, RAG reindex, AI-SDLC actions…). | `false` |
| `RBAC_PAGE_ENFORCEMENT_ENABLED` | ⚪ | `false` | Enforce dashboard/page access by canonical role. | `false` |
| `RBAC_SCOPE_FILTERING_ENABLED` | ⚪ | `false` | Filter list/search/dashboard rows to the principal's scope (vertical/function/app/control). | `false` |

All default `false` so ECS behaves as today; enable per phase. In demo mode (`DEMO_MODE=true`) RBAC enforcement is short-circuited regardless.

---

## 4. Durable audit & observations (require PostgreSQL)

| Variable | Required | Default | Purpose | Demo Override |
|---|:--:|---|---|---|
| `AUDIT_WORKFLOW_ENABLED` | ⚪ | `false` | Emit durable, attributable workflow audit records (submit/approve/reject/observation/escalation) to Postgres. | `false` |
| `OBSERVATIONS_DURABLE_ENABLED` | ⚪ | `false` | Mirror observation create/update/close/reopen to Postgres and hydrate on startup. | `false` |

Both no-op without the PostgreSQL evidence repository.

---

## 5. Evidence intelligence engines (deterministic, non-LLM, all default OFF)

| Variable | Required | Default | Purpose | Demo Override |
|---|:--:|---|---|---|
| `SUFFICIENCY_ENGINE_ENABLED` | ⚪ | `false` | Read-only evidence-sufficiency scoring (5 weighted dimensions, `config/sufficiency.yaml`). | `false`/`true` |
| `EVIDENCE_VERSIONING_ENABLED` | ⚪ | `false` | Evidence version tracking (Phase 5.4). | `false` |
| `EVIDENCE_LINEAGE_ENABLED` | ⚪ | `false` | Evidence lineage graph. | `false` |
| `OBSERVATION_READINESS_ENABLED` | ⚪ | `false` | Observation readiness / closure assist. | `false` |
| `EVIDENCE_REUSE_SCORING_ENABLED` | ⚪ | `false` | Cross-framework reuse scoring. | `false` |
| `EVIDENCE_CHANGE_DETECTION_ENABLED` | ⚪ | `false` | Difference engine. | `false` |
| `EVIDENCE_QUERY_ENABLED` | ⚪ | `false` | Evidence query API. | `false` |
| `EVIDENCE_TIMELINE_ENABLED` | ⚪ | `false` | Evidence timeline (Phase 5.5). | `false` |
| `EVIDENCE_SEARCH_DSL_ENABLED` | ⚪ | `false` | Search DSL execution (also needs `EVIDENCE_QUERY_ENABLED`). | `false` |
| `EVIDENCE_PORTFOLIO_ENABLED` | ⚪ | `false` | Portfolio analytics. | `false` |
| `ROI_CENTER_ENABLED` | ⚪ | `false` | Executive ROI & Value Realization Center (values from `config/roi.yaml`). | `false`/`true` |
| `CONNECTIVITY_ASSESSMENT_ENABLED` | ⚪ | `false` | Connectivity readiness assessment (Phase 5.3). | `false` |
| `CONNECTOR_CERTIFICATION_ENABLED` | ⚪ | `false` | Connector certification engine. | `false` |

When OFF, these engines compute nothing and ECS behavior is unchanged.

---

## 6. Evidence repository — PostgreSQL (`config/repository.yaml`)

| Variable | Required | Default | Purpose | Demo Override |
|---|:--:|---|---|---|
| `ECS_REPO_BACKEND` | ⚪ | `postgres` | Repository backend. | n/a |
| `ECS_REPO_PG_HOST` | ⚪ (stack) | `postgres` (compose) / `localhost` (.env) | Repository DB host. | 🔧 compose: `postgres` |
| `ECS_REPO_PG_PORT` | ⚪ | `5432` | Repository DB port (host-mapped to `5433`). | `5432` |
| `ECS_REPO_PG_DATABASE` | ⚪ | `ecs_repository` | Repository DB name. | default |
| `ECS_REPO_PG_USER` | ⚪ | `ecs_user` | Repository DB user. | default |
| `ECS_REPO_PG_PASSWORD` | ✅ (stack) | `change-me` | Repository DB password (secret; from env only). | 🔧 compose: `ecs_password` |
| `ECS_REPO_PG_SCHEMA` | ⚪ | `public` | DB schema. | default |
| `ECS_REPO_PG_MIN_POOL` | ⚪ | `1` | Min connection pool size. | default |
| `ECS_REPO_PG_MAX_POOL` | ⚪ | `10` | Max connection pool size. | default |
| `ECS_REPO_PG_TIMEOUT` | ⚪ | `30` | Statement timeout (sec). | default |
| `ECS_PG_USER` / `ECS_PG_PASSWORD` / `ECS_PG_DB` | ⚪ | `ecs_user` / `change-me` / `ecs_repository` | Legacy/alt repository creds referenced by `.env.example`. | compose sets `ECS_PG_*` for the demo-connectors Postgres |

**Can ECS run without a database?** Yes for the **showcase** demo (in-memory). `init_repository()` is best-effort and `/readyz` returns 503 without it, but `/` and dashboards still serve. Durable audit/observations, sufficiency persistence, and the connector evidence flow require Postgres.

---

## 7. Object store — MinIO/S3 (`config/repository.yaml`)

| Variable | Required | Default | Purpose | Demo Override |
|---|:--:|---|---|---|
| `ECS_OBJECT_STORE_ENABLED` | ⚪ | `true` | Toggle raw-artifact object storage. | n/a |
| `MINIO_ENDPOINT` | ⚪ (stack) | `minio:9000` | Object store endpoint. | 🔧 compose: `minio:9000` |
| `MINIO_BUCKET` | ⚪ | `ecs-evidence` | Bucket for evidence artifacts. | default |
| `MINIO_ACCESS_KEY` | ✅ (stack) | (env) | Object store access key (secret). | 🔧 compose: `ecs_minio` |
| `MINIO_SECRET_KEY` | ✅ (stack) | (env) | Object store secret key (secret). | 🔧 compose: `ecs_minio_secret` |
| `MINIO_SECURE` | ⚪ | `false` | Use TLS to object store. | `false` |

---

## 8. Vector store (`config/vectorstore.yaml`)

| Variable | Required | Default | Purpose | Demo Override |
|---|:--:|---|---|---|
| `ECS_VECTOR_PROVIDER` | ⚪ | `pgvector` | `pgvector` \| `chroma` \| `milvus`. | default |
| `ECS_VECTOR_DIM` | ⚪ | `768` | Embedding dimension (matches `nomic-embed-text` / `text-embedding-004`). | `768` |
| `ECS_VECTOR_COLLECTION` | ⚪ | `ecs_evidence_chunks` | Logical collection name. | default |
| `ECS_CHUNK_SIZE` | ⚪ | `1000` | RAG chunk size. | default |
| `ECS_CHUNK_OVERLAP` | ⚪ | `150` | RAG chunk overlap. | default |
| `ECS_VECTOR_PG_HOST` | ⚪ (stack) | `pgvector` | pgvector host. | 🔧 compose: `pgvector` |
| `ECS_VECTOR_PG_PORT` | ⚪ | `5432` | pgvector port (host-mapped `5434`). | default |
| `ECS_VECTOR_PG_DATABASE` | ⚪ | `ecs_vectors` | pgvector DB. | default |
| `ECS_VECTOR_PG_USER` | ⚪ | `ecs_user` | pgvector user. | default |
| `ECS_VECTOR_PG_PASSWORD` | ✅ (stack) | (env) | pgvector password (secret). | 🔧 compose: `ecs_password` |
| `ECS_VECTOR_PG_TABLE` | ⚪ | `evidence_embeddings` | Embeddings table. | default |
| `CHROMA_HOST` / `CHROMA_PORT` | ⚪ | `chroma` / `8000` | Chroma provider (if selected). | default |
| `MILVUS_HOST` / `MILVUS_PORT` | ⚪ | `milvus` / `19530` | Milvus provider (if selected). | default |

---

## 9. LLM / RAG (`config/llm.yaml`)

| Variable | Required | Default | Purpose | Demo Override |
|---|:--:|---|---|---|
| `ECS_LLM_PROVIDER` | ⚪ | `ollama` | `ollama` \| `gemini` \| `openai` \| `azure_openai` \| `claude`. | `ollama` (or unset) |
| `ECS_LLM_MODEL` | ⚪ | `qwen3:8b` | Chat model. | default |
| `ECS_EMBEDDING_MODEL` | ⚪ | `nomic-embed-text` | Embedding model. | default |
| `ECS_LLM_TEMPERATURE` | ⚪ | `0.1` | Sampling temperature. | default |
| `ECS_LLM_MAX_TOKENS` | ⚪ | `2048` | Max output tokens. | default |
| `ECS_LLM_TIMEOUT` | ⚪ | `180` | Request timeout (sec). | default |
| `ECS_OLLAMA_KEEP_ALIVE` | ⚪ | `30m` | Keep local model resident. | default |
| `OLLAMA_URL` | ⚪ | `http://host.docker.internal:11434` | Ollama daemon URL. | default |
| `OLLAMA_MODEL` | ⚪ | `qwen3:8b` | Ollama model override. | default |
| `GEMINI_API_KEY` / `GEMINI_BASE_URL` | ⚪ (gemini) | — / `https://generativelanguage.googleapis.com` | Gemini provider (secret key). | unset |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` | ⚪ (openai) | — / `https://api.openai.com/v1` | OpenAI provider (secret key). | unset |
| `AZURE_OPENAI_API_KEY` / `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_API_VERSION` / `AZURE_OPENAI_DEPLOYMENT` | ⚪ (azure) | — / — / `2024-02-15-preview` / — | Azure OpenAI provider. | unset |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL` | ⚪ (claude) | — / `https://api.anthropic.com` | Claude provider (secret key). | unset |
| `ECS_RAG_TOP_K` | ⚪ | `8` | RAG retrieval top-k. | default |
| `ECS_RAG_MIN_SCORE` | ⚪ | `0.0` | RAG min similarity. | default |
| `ECS_RAG_MAX_CHUNKS` | ⚪ | `12` | Max context chunks. | default |

**Can ECS run without an LLM?** Yes. When no provider is configured/reachable the assistant uses a deterministic fallback (logged: `LLM-RAG disabled … deterministic fallback`). RAG is grounded: `require_citations: true`, `refuse_without_evidence: true`.

---

## 10. Source-system connectors (`config/integrations.yaml`)

Enable a connector with `ECS_<NAME>_ENABLED=true` and supply its credentials. **Live-by-default in dev:** Gitea, SonarQube, Jenkins. **Interface-complete, disabled by default:** the rest.

| Variable | Required | Default | Purpose | Demo Override |
|---|:--:|---|---|---|
| `ECS_GITEA_ENABLED` | ⚪ | `true` | Enable Gitea connector (repos/commits/PRs/branch protections/releases). | `true` |
| `GITEA_URL` | ⚪ | `http://gitea:3000` | Gitea base URL. | compose default |
| `GITEA_TOKEN` | ⚪ (gitea) | empty | Gitea API token (written by seed script to `demo-data/.gitea_token`). | from seed |
| `ECS_GITEA_VERIFY_SSL` | ⚪ | `true` | Verify TLS. | `true` |
| `ECS_SONAR_ENABLED` | ⚪ | `true` | Enable SonarQube connector (quality gates/coverage/vulns/hotspots). | `true` |
| `SONAR_URL` | ⚪ | `http://sonarqube-demo:9000` | SonarQube URL. | compose default |
| `SONAR_TOKEN` / `SONAR_USER` / `SONAR_PASSWORD` | ⚪ | — / `admin` / `a123` (compose) | SonarQube auth (token or basic). | compose: `admin/a123` |
| `ECS_SONAR_VERIFY_SSL` | ⚪ | `true` | Verify TLS. | `true` |
| `ECS_JENKINS_ENABLED` | ⚪ | `true` | Enable Jenkins connector (jobs/builds/tests/artifacts). | `true` |
| `JENKINS_URL` | ⚪ | `http://jenkins:8080` | Jenkins URL. | compose default |
| `JENKINS_USER` / `JENKINS_TOKEN` | ⚪ | `admin` / `admin123` (compose) | Jenkins basic auth. | compose: `admin/admin123` |
| `ECS_JENKINS_VERIFY_SSL` | ⚪ | `true` | Verify TLS. | `true` |
| `ECS_JIRA_ENABLED` | ⚪ | `false` | Enable Jira connector. | `false` |
| `JIRA_URL` / `JIRA_USER` / `JIRA_TOKEN` | ⚪ (jira) | empty | Jira endpoint + credentials. | empty |
| `ECS_GITHUB_ENABLED` | ⚪ | `false` | Enable GitHub connector. | `false` |
| `GITHUB_URL` / `GITHUB_ORG` / `GITHUB_TOKEN` | ⚪ (github) | `https://api.github.com` / empty / empty | GitHub endpoint + org + token. | empty |
| `ECS_CONFLUENCE_ENABLED` | ⚪ | `false` | Enable Confluence connector. | `false` |
| `CONFLUENCE_URL` / `CONFLUENCE_USER` / `CONFLUENCE_TOKEN` | ⚪ (confluence) | empty | Confluence endpoint + credentials. | empty |
| `ECS_FIGMA_ENABLED` | ⚪ | `false` | Enable Figma connector. | `false` |
| `FIGMA_URL` / `FIGMA_TOKEN` / `FIGMA_TEAM_IDS` | ⚪ (figma) | `https://api.figma.com` / empty / empty | Figma endpoint + token + team ids. | empty |
| `ECS_SNOW_ENABLED` | ⚪ | `false` | Enable ServiceNow connector. | `false` |
| `SNOW_URL` / `SNOW_USER` / `SNOW_PASSWORD` | ⚪ (snow) | empty | ServiceNow endpoint + basic auth. | empty |
| `ECS_TEAMS_ENABLED` | ⚪ | `false` | Enable MS Teams connector (Graph). | `false` |
| `ECS_SHAREPOINT_ENABLED` | ⚪ | `false` | Enable SharePoint connector (Graph). | `false` |
| `MS_GRAPH_URL` / `MS_TENANT_ID` / `MS_CLIENT_ID` / `MS_CLIENT_SECRET` | ⚪ (teams/sharepoint) | `https://graph.microsoft.com/v1.0` / empty… | Shared MS Graph app registration. | empty |
| `SHAREPOINT_SITE_ID` | ⚪ (sharepoint) | empty | Target SharePoint site. | empty |
| `ECS_PRISMA_ENABLED` | ⚪ | `false` | Enable Prisma Cloud connector. | `false` |
| `PRISMA_URL` / `PRISMA_ACCESS_KEY` / `PRISMA_SECRET_KEY` | ⚪ (prisma) | empty | Prisma endpoint + credentials. | empty |
| `ECS_AZDO_ENABLED` | ⚪ | `false` | Enable Azure DevOps connector. | `false` |
| `AZDO_URL` / `AZDO_ORG` / `AZDO_TOKEN` | ⚪ (azdo) | `https://dev.azure.com` / empty / empty | Azure DevOps endpoint + org + PAT. | empty |
| `ECS_CONNECTOR_TIMEOUT` | ⚪ | `10` | Connector HTTP timeout (sec). | default |
| `ECS_CONNECTOR_RETRIES` | ⚪ | `1` | Connector retry count. | default |
| `ECS_CONNECTOR_PAGE_SIZE` | ⚪ | `100` | Connector pagination size. | default |

---

## 11. Backup / restore (`scripts/backup`, `scripts/restore`)

| Variable | Required | Default | Purpose | Demo Override |
|---|:--:|---|---|---|
| `BACKUP_DIR` | ⚪ | `./backups` | Output directory for DB backups (git-ignored). | default |
| `BACKUP_RETENTION_DAYS` | ⚪ | `14` | Prune backups older than N days (`0` = keep forever). | default |

(Backup scripts reuse the `ECS_REPO_PG_*` connection values from §6.)

---

## 12. Docker-Compose-only runtime variables

Set by `docker-compose.yml` for the demo-connector subsystem; you do not set these in `.env` for a native run:

| Variable | Compose value | Purpose |
|---|---|---|
| `ECS_PG_HOST` / `ECS_PG_PORT` / `ECS_PG_DATABASE` | `postgres-demo` / `5432` / `ecs_demo` | Demo-connectors Postgres. |
| `ECS_LINUX_CONTAINER` | `ubuntu-demo` | Target container for the Linux connector. |
| `ECS_GITLEAKS_SCAN_PATH` | `/app/demo-data/gitleaks-sample` | Path the gitleaks connector scans. |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection. |
| `ECS_CONFIG_DIR` | `/app/config` | Config directory inside the container. |

---

## 13. Minimal `.env` for each mode

**Native demo (no DB, no auth):**
```bash
DEMO_MODE=true
ECS_AUTH_ENABLED=false
```

**Docker full stack:** copy `.env.example` to `.env`; Docker Compose injects the DB/MinIO/connector values. Set `GITEA_TOKEN` after seeding (`export GITEA_TOKEN=$(cat demo-data/.gitea_token)`), and add LLM provider keys only if you want live RAG.

**Production (illustrative):** `ECS_AUTH_ENABLED=true`, `DEMO_MODE=false`, configure `ECS_AUTH_PROVIDER` + Azure/OIDC values, set strong `ECS_REPO_PG_PASSWORD`/`MINIO_*`, and progressively enable the RBAC flags (§3) and durable audit (§4).

> **Never commit `.env`, live tokens, or backups.** `.gitignore` excludes `.env`, `.env.*` (except `.env.example`), `demo-data/.gitea_token`, `demo-data/*.token`, `backups/`, and `*.dump`.
