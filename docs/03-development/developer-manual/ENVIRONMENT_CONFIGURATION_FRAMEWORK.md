# ECS Environment Configuration Framework

**Release tag:** `ecs-environment-configuration-framework-v1`

A single, YAML-driven configuration layer that lets ECS be deployed into
**Local, Dev, SIT, UAT, and Production** by editing YAML only — **no source
code changes**. It builds on the existing `ecs_platform.config` loader (which
already resolves `${VAR}` / `${VAR:-default}` placeholders and keeps every
secret in environment variables) and adds the missing piece: a unifying
**environment selector** and per-environment configuration files.

---

## 1. How it works

```
ECS_ENV ─────────────┐
                     ▼
config/environments/_base.yaml   (schema-complete defaults)
        +  config/environments/<ECS_ENV>.yaml   (per-env overrides)
        =  deep-merged, ${VAR}-resolved configuration
                     ▼
        config/environment_loader.get_environment_config()
                     ▼
   modules / connectors / predefined queries / reports
```

* **`ECS_ENV`** selects the active environment. Valid values:
  `local` (default), `dev`, `sit`, `uat`, `prod`.
* **`config/environments/_base.yaml`** is the schema-complete base with safe
  defaults that reproduce historical demo behaviour.
* **`config/environments/<env>.yaml`** contains only the values that differ for
  that environment. It is **deep-merged on top of** `_base.yaml`.
* Every scalar still supports `${VAR}` / `${VAR:-default}`, so any single field
  can also be overridden by an environment variable at runtime (Docker / K8s).
* **No secret is ever stored in YAML.** Passwords, tokens, and keys are
  referenced by the *name* of the environment variable that supplies them
  (`password_env`, `token_env`, `*_env`).

### Entry points

| File | Purpose |
|------|---------|
| `config/environments/_base.yaml`      | Schema-complete defaults (all sections) |
| `config/environments/local.yaml`      | Local / docker-compose demo (historical defaults) |
| `config/environments/dev.yaml`        | Shared development cluster |
| `config/environments/sit.yaml`        | System Integration Test |
| `config/environments/uat.yaml`        | User Acceptance Test |
| `config/environments/prod.yaml`       | Production |
| `config/environment_loader.py`        | `get_environment_config()` + typed accessors |
| `config/config_validation.py`         | Startup validation with meaningful errors |

---

## 2. Configuration schema

Top-level sections (see `_base.yaml` for the full, commented schema):

| Section | Contents |
|---------|----------|
| `environment`               | Environment identifier (`local`…`prod`) |
| `tenant`, `region`          | Tenant / region identifiers |
| `applications`              | Banking applications: `host`, `port`, `base_url`, `business_unit`, `criticality`, `enabled` |
| `databases`                 | `postgres` (evidence repository), `oracle`, `mysql`, `sqlserver` |
| `connectors`                | Evidence-source URLs: jira, confluence, servicenow, github, gitea, teams, sharepoint, azure_devops, jenkins, sonarqube, prisma_cloud, figma |
| `framework_targets`         | Per-framework `enabled` + `target_groups` (reference into `predefined_query_targets`) |
| `predefined_query_targets`  | `os_servers`, `db_servers`, `middleware_servers`, `appsec_targets` lists + live demo connectors (postgresql/linux/sonarqube/trivy/gitleaks) |
| `storage`                   | `object_store` (MinIO / S3) |
| `authentication`            | `sso` (saml / oidc / azure_ad) |
| `llm`                       | provider / model / base_url |
| `reporting`                 | `export_path`, `format` |

### Accessing configuration in code

```python
from config.environment_loader import (
    get_environment_config, active_environment,
    get_database, get_connector_url, get_target_servers, get_application,
)

env   = active_environment()                 # "uat"
cfg   = get_environment_config()             # full merged dict
pg    = get_database("postgres")             # {host, port, database, user, password_env, ...}
jira  = get_connector_url("jira")            # "https://jira.uat.bank.local"
os_t  = get_target_servers("os_servers")     # ["10.10.10.1", "10.10.10.2"]
nb    = get_application("netbanking")         # {host, port, base_url, ...}
```

---

## 3. Migration guide (what changed, and why nothing breaks)

ECS was already ~95% environment-driven: connector URLs, the evidence
repository, the object store, and the LLM provider all resolved from
`${VAR:-default}` placeholders in `config/*.yaml`. This framework adds the
environment selector and **routes the predefined-query execution targets**
through the same layer.

**Refactored to read from `get_environment_config()`** (with the original env
var and default preserved as fallbacks — behaviour is identical when no env
file overrides are present):

| File | Function | Now sourced from |
|------|----------|------------------|
| `modules/operations/engines/postgresql_connector.py` | `get_postgresql_config()` | `predefined_query_targets.postgresql` |
| `modules/operations/engines/linux_connector.py`      | `get_linux_config()`      | `predefined_query_targets.linux` |
| `modules/operations/engines/sonarqube_connector.py`  | `get_sonarqube_config()`  | `predefined_query_targets.sonarqube` |
| `modules/operations/engines/trivy_connector.py`      | `get_trivy_config()`      | `predefined_query_targets.trivy` |
| `modules/operations/engines/gitleaks_connector.py`   | `get_gitleaks_config()`   | `predefined_query_targets.gitleaks` |
| `modules/operations/engines/query_connectors.py`     | `CONNECTOR_CONFIG` / `build_connector_config()` | `predefined_query_targets.*` server lists |

**Resolution order (per field):** active-environment YAML → matching `ECS_*`
environment variable → historical default. Because the YAML defaults already
embed the env vars and historical values, `ECS_ENV=local` (the default)
reproduces the previous demo exactly. Verified: the full test suite passes and
`local` connector configs are byte-for-byte unchanged.

---

## 4. UAT integration guide

1. Edit **`config/environments/uat.yaml`** only.
2. Set application hosts, database hosts, connector URLs, and the predefined
   query target lists (`os_servers`, `db_servers`, `middleware_servers`,
   `appsec_targets`). The shipped file already contains the standard UAT
   examples (`os_servers: [10.10.10.1, 10.10.10.2]`, `db_servers: [10.10.20.1,
   10.10.20.2]`).
3. Export the **secrets** as environment variables (never put them in YAML):
   ```bash
   export ECS_REPO_PG_PASSWORD=...        # evidence repository
   export ECS_PG_PASSWORD=...             # predefined-query PG target
   export JIRA_TOKEN=... CONFLUENCE_TOKEN=... SNOW_USER=... SNOW_PASSWORD=...
   export MINIO_ACCESS_KEY=... MINIO_SECRET_KEY=...
   ```
4. Validate before starting:
   ```bash
   ECS_ENV=uat python -m config.config_validation
   ```
5. Start ECS:
   ```bash
   ECS_ENV=uat python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

## 5. Production integration guide

Identical to UAT, but use **`config/environments/prod.yaml`** and:

* Source all `*_env` secrets from a vault / Kubernetes Secret — never a file
  on disk.
* Keep `authentication.sso.enabled: true` and
  `storage.object_store.secure: true` (both default to `true` in `prod.yaml`;
  validation warns if disabled in prod).
* The shipped `prod.yaml` ships the standard production target examples
  (`os_servers: [172.16.10.1, 172.16.10.2]`, `db_servers: [172.16.20.1,
  172.16.20.2]`); replace with the real production inventory.
* Run `ECS_ENV=prod python -m config.config_validation` in the deploy pipeline
  and **fail the deploy on a non-zero exit code**.

## 6. Deployment guide (Docker / Kubernetes)

```dockerfile
# Select the environment at container runtime — no rebuild per env.
ENV ECS_ENV=uat
```

```yaml
# Kubernetes — one image, environment chosen by env var; secrets from a Secret.
env:
  - name: ECS_ENV
    value: "prod"
  - name: ECS_REPO_PG_PASSWORD
    valueFrom: { secretKeyRef: { name: ecs-secrets, key: repo-pg-password } }
  - name: JIRA_TOKEN
    valueFrom: { secretKeyRef: { name: ecs-secrets, key: jira-token } }
# Optionally mount an external config dir and point ECS_CONFIG_DIR at it to
# override the baked-in config/ entirely.
```

* `ECS_CONFIG_DIR` (existing) relocates the entire `config/` directory, so the
  environment files can live in a mounted ConfigMap/volume.
* Per-target server lists can also be injected as comma-separated env vars:
  `ECS_TARGET_OS_SERVERS`, `ECS_TARGET_DB_SERVERS`, `ECS_TARGET_MW_SERVERS`,
  `ECS_TARGET_APPSEC`.

---

## 7. Validation framework

`config/config_validation.py` validates a resolved environment and fails with
clear, actionable errors. Severity is environment-aware: gaps that are normal
on a laptop (`local`) are warnings; the same gaps in `sit`/`uat`/`prod` are
errors.

```bash
python -m config.config_validation            # active env (ECS_ENV)
python -m config.config_validation --all      # every env file present
python -m config.config_validation uat        # a named env
```

Checks: valid environment id, all required sections present, evidence-repository
DB host/port/db/user populated, enabled connectors have URLs, framework targets
reference valid target groups, OS/DB target lists present (strict envs),
`reporting.export_path` set, and production hardening (SSO + secure object
store).

See also: `docs/03-development/developer-manual/ECS_CONFIGURATION_DEPENDENCY_MATRIX.md`,
`docs/03-development/developer-manual/ECS_PERSONA_CONFIGURATION_MATRIX.md`,
`docs/03-development/developer-manual/ECS_APPLICATION_CONFIGURATION_MATRIX.md`,
`docs/03-development/developer-manual/ECS_ENVIRONMENT_VALIDATION_MATRIX.md`,
`docs/03-development/developer-manual/ECS_HARDCODED_DEPENDENCY_INVENTORY.md`.
