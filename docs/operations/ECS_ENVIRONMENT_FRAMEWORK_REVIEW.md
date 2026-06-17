# ECS Environment Framework Review (Phase 1)

**Mode:** READ-ONLY / ANALYSIS / REPORTING. **No config/code changes. No commits.** **Grounding:** `config/environment_loader.py`, `config/environments/_base.yaml` + `local|dev|sit|uat|prod.yaml`, `ecs_platform/config/loader.py`. Complements [Deployment Reference](../DEPLOYMENT/ECS_DEPLOYMENT_REFERENCE.md), [Environment Configuration](../ENVIRONMENT_CONFIGURATION.md).

---

## 1. Framework overview (verified)

ECS selects the active environment via **`ECS_ENV`** (default `local`; validated against `("local","dev","sit","uat","prod")`). `_base.yaml` is schema-complete; each env file is **deep-merged on top** (override wins), then every value is env-resolved (`${VAR}` / `${VAR:-default}`). **All 5 env files + `_base.yaml` present on disk** (`available_environments()`).

```
ECS_ENV → active_environment() (validate) → load _base.yaml → deep_merge(env.yaml)
→ ${VAR} resolution (loader) → CSV target overrides → cached merged config
```

## 2. Per-environment validation

| Env | File | Purpose | Validated |
|---|---|---|---|
| local | `local.yaml` | dev/demo defaults (docker-compose service names) | ✅ present |
| dev | `dev.yaml` | integration dev | ✅ present |
| sit | `sit.yaml` | system integration test | ✅ present (resolves SIT gap noted in Deployment Reference) |
| uat | `uat.yaml` | pre-prod validation | ✅ present |
| prod | `prod.yaml` | production | ✅ present |

> **Correction to prior doc:** the [Deployment Reference](../DEPLOYMENT/ECS_DEPLOYMENT_REFERENCE.md) marked SIT `[Inferred/Target]`; a `sit.yaml` **does exist**. SIT is therefore a first-class environment. (Documentation-only correction — see EF-P3-02.)

## 3. Validation results

### 3.1 YAML loading (✅)
`ecs_platform/config/loader.py`: `${VAR}`/`${VAR:-default}` regex resolution, bool/int coercion, whole-string type preservation, `lru_cache`, `ConfigError` on missing/invalid YAML or non-mapping root. **Sound.**

### 3.2 Fallback logic (✅)
- `environment_loader` "never raises on import"; `get_environment_config()` degrades to base defaults if an env file is missing (demo keeps working).
- `query_connectors._STATIC_CONNECTOR_CONFIG` is a verbatim fallback when the env layer yields nothing — historical demo behavior preserved.
- `_base.yaml` defaults mirror docker-compose service names, so loading with no env vars changes nothing.

### 3.3 Environment overrides (✅)
- Any field overridable by env var via `${VAR}` substitution (Docker/K8s friendly).
- Predefined-query target server lists overridable by **CSV env vars** (`ECS_TARGET_OS_SERVERS`, `_DB_SERVERS`, `_MW_SERVERS`, `_APPSEC`) via `_apply_target_overrides()`.
- Typed accessors (`get_connector`, `get_database`, `get_predefined_query_targets`, etc.) prevent raw-dict reach-in.

### 3.4 Secrets posture (✅)
No secret stored in any env file — only the **name** of the env var (`*_env`). Secrets resolve from process env at load. Consistent with [Security Reference](../SECURITY/ECS_SECURITY_REFERENCE.md).

## 4. Gap classification

| ID | Finding | Severity | Recommendation (document only) |
|---|---|---|---|
| EF-P2-01 | `predefined_query_targets` server lists empty by default (os/db/mw/appsec = `[]`) | **P2** | Populate per-env target lists in `uat.yaml`/`prod.yaml` before live query execution (config edit at deploy time, not under this read-only mandate). |
| EF-P3-01 | SSO/IdP slots present but disabled (`ECS_SSO_ENABLED:-false`) | **P3** | Enable + configure OIDC/SAML for UAT/PROD; document steps. |
| EF-P3-02 | Deployment Reference marked SIT inferred | **P3** | Update Deployment Reference note: SIT file exists. |

## 5. Verdict
**Environment framework: GO.** Loader, deep-merge, env substitution, fallback, and override logic are all implemented and validated across 5 environments + base. Only deploy-time config population (P2 target lists) and SSO enablement (P3) remain — no code change required.

## Cross-references
- [Deployment Reference](../DEPLOYMENT/ECS_DEPLOYMENT_REFERENCE.md) · [Environment Configuration](../ENVIRONMENT_CONFIGURATION.md) · [Connector Readiness](ECS_CONNECTOR_READINESS_REPORT.md) · [Predefined Query Readiness](ECS_PREDEFINED_QUERY_READINESS_REPORT.md)
