# ECS Environment Configuration Guide

**Goal:** moving ECS between **LOCAL → UAT → PRODUCTION → DR** requires **ONLY
configuration changes** — never source-code changes.

This is the entry point for the environment-configuration guides:

| Guide | Purpose |
|---|---|
| [01_DEPLOYMENT_CONFIGURATION_GUIDE.md](01_DEPLOYMENT_CONFIGURATION_GUIDE.md) | How the config framework resolves per environment |
| [02_UAT_CONFIGURATION_GUIDE.md](02_UAT_CONFIGURATION_GUIDE.md) | UAT deployment configuration |
| [03_PRODUCTION_CONFIGURATION_GUIDE.md](03_PRODUCTION_CONFIGURATION_GUIDE.md) | Production deployment configuration |
| [04_DR_CONFIGURATION_GUIDE.md](04_DR_CONFIGURATION_GUIDE.md) | Disaster-recovery configuration |
| [05_CONNECTOR_CONFIGURATION_GUIDE.md](05_CONNECTOR_CONFIGURATION_GUIDE.md) | Per-connector endpoint/credential config |
| [06_SECRETS_MANAGEMENT_GUIDE.md](06_SECRETS_MANAGEMENT_GUIDE.md) | How secrets are handled + masked |
| [07_BANK_DEPLOYMENT_GUIDE.md](07_BANK_DEPLOYMENT_GUIDE.md) | Bank rollout: config-only checklist |
| [08_ROLLBACK_GUIDE.md](08_ROLLBACK_GUIDE.md) | Rolling back a config/deployment |
| [09_IP_MIGRATION_GUIDE.md](09_IP_MIGRATION_GUIDE.md) | Move ECS across environments by editing config only |

---

## 1. The model

```
ECS_ENV  ──selects──►  config/environments/<env>.yaml
                          deep-merged over  config/environments/_base.yaml
                          with ${VAR:-default} resolved from the process env
```

- **One switch:** `ECS_ENV` ∈ `local | dev | sit | uat | prod | dr`.
- **`_base.yaml`** is the schema-complete default layer. Each env file overrides
  only what differs.
- **Every value** supports `${VAR}` / `${VAR:-default}`, so any field can also be
  overridden by a single environment variable (Docker/K8s/vault friendly).
- **No secret** is ever stored in YAML — YAML holds only the *name* of the env var
  (`*_env`) that supplies each secret.

## 2. What is configurable (all of it)

| Area | Section | Key variables |
|---|---|---|
| Application identity | `application` | `ECS_HOST`, `ECS_PORT`, `ECS_PUBLIC_URL`, `ECS_BASE_URL` |
| Evidence DB | `databases.postgres` | `ECS_REPO_PG_HOST/PORT/DATABASE/USER/PASSWORD` |
| Redis / cache | `redis`, `caching` | `REDIS_HOST/PORT/SSL/PASSWORD`, `ECS_CACHE_*` |
| Object storage | `storage.object_store` | `MINIO_ENDPOINT/BUCKET/SECURE/ACCESS_KEY/SECRET_KEY` |
| Vector store | `vector_store` | `ECS_VECTOR_PROVIDER`, `ECS_VECTOR_PG_HOST/PORT/DATABASE` |
| LLM / embeddings | `llm` | `ECS_LLM_PROVIDER/MODEL`, `OLLAMA_URL` |
| Scheduler | `scheduler` | `ECS_SCHEDULER_ENABLED/WORKERS/TIMEOUT_SECONDS/MAX_RETRIES` |
| Connector execution | `connector_execution` | `ECS_CONNECTORS_ENABLED`, `ECS_CONNECTOR_TIMEOUT_SECONDS/MAX_RETRIES/SSL_VERIFY/PROXY_URL` |
| Connectors (per system) | `connectors.*` | base_url / version / timeout / retry / creds via `*_env` |
| Security | `security`, `authentication` | `ECS_AUTH_ENABLED`, `ECS_FORCE_HTTPS`, `ECS_SSO_ENABLED` |
| Logging / monitoring | `logging`, `monitoring` | `ECS_LOG_LEVEL/FORMAT`, `ECS_MONITORING_ENABLED` |
| Reporting | `reporting` | `ECS_REPORT_EXPORT_PATH`, `ECS_REPORT_FORMAT` |
| Future extensions | `extensions` | `ECS_MCP_ENDPOINT`, `ECS_AGENT_ENDPOINT`, `ECS_PLUGIN_ENDPOINT` |
| Query targets | `predefined_query_targets` | `ECS_TARGET_OS_SERVERS/_DB_SERVERS/_MW_SERVERS/_APPSEC` (CSV) |

## 3. Tools

```bash
# Validate config structure for one/all environments (no secrets needed):
python scripts/config_tools.py validate-config prod
python scripts/config_tools.py validate-all

# Validate a deploy tier WITH secrets (run with that env's secrets loaded):
python scripts/config_tools.py validate-prod --check-secrets

# Inspect the resolved, secret-safe profile for an environment:
python scripts/config_tools.py show-current-config prod

# See exactly what differs between two environments:
python scripts/config_tools.py compare-envs local prod

# Scaffold a .env template listing every variable an environment references:
python scripts/config_tools.py generate-env-template dr > .env.dr
```

## 4. Guarantees

- Config files validate structurally with **no credentials present** (CI-friendly).
- Remote environments (`uat`/`prod`/`dr`) are rejected if any endpoint resolves to
  `localhost`/loopback.
- Secrets are shown as `SET`/`MISSING` everywhere (profiles, validation, diagnostics).
- Adding a brand-new environment = add `config/environments/<env>.yaml` + register
  the name — no other code change.
