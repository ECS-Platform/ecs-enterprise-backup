# ECS Hardcoded Configuration Dependency Inventory (Phase 1)

Repository-wide scan for hardcoded environment-specific values (IPs, URLs,
hosts, ports, DB/connector/application endpoints, framework targets, filesystem
paths, tenant/environment identifiers).

## Key finding

ECS was **already substantially environment-driven**: connector URLs, the
evidence repository, the object store, and the LLM provider all resolve from
`${VAR}` / `${VAR:-default}` placeholders in `config/*.yaml`, with secrets held
only in environment variables. The only true hardcoded
environment-specific targets were in the **Predefined Queries** connector layer
(execution hosts/ports) — these are now externalized into the environment
schema. The defaults below are demo/docker-compose service names retained as
**fallbacks**, so the demo is unchanged.

## Inventory

| File | Line(s) | Value | Purpose | Module | Environment Dependency | Status |
|------|---------|-------|---------|--------|------------------------|--------|
| `modules/operations/engines/query_connectors.py` | 10–20 (was) | `postgres-demo`, `ubuntu-demo`, `sonarqube-demo`, `oracle-db:1521`, `postgres-db:5432`, `ubuntu-host:22`, `sonarqube-server:9000` | Predefined-query connector targets | Operations / Predefined Queries | Host/port per env | **Migrated** → built from `predefined_query_targets.*`; static map kept as fallback |
| `modules/operations/engines/postgresql_connector.py` | 16–24 | `localhost`, `5432`, `ecs_demo`, `ecs_user`, `ecs_password` | PG predefined-query target | Operations | Host/port/db/creds per env | **Migrated** → `predefined_query_targets.postgresql` (env var + default fallback) |
| `modules/operations/engines/linux_connector.py` | 20–24 | `ubuntu-demo` | Linux exec target | Operations | Container per env | **Migrated** → `predefined_query_targets.linux` |
| `modules/operations/engines/sonarqube_connector.py` | 19–26 | `http://sonarqube-demo:9000`, `admin`/`admin` | SonarQube API target | Operations | URL/creds per env | **Migrated** → `predefined_query_targets.sonarqube` |
| `modules/operations/engines/trivy_connector.py` | 13, 16–20 | `alpine:3.19` | Trivy scan image | Operations | Image per env | **Migrated** → `predefined_query_targets.trivy` |
| `modules/operations/engines/gitleaks_connector.py` | 16–21 | `<repo>/demo-data/gitleaks-sample` | GitLeaks scan path | Operations | Path per env | **Migrated** → `predefined_query_targets.gitleaks` (absolute repo default fallback) |
| `config/integrations.yaml` | 11–185 | `${GITEA_URL:-http://gitea:3000}`, `${SONAR_URL:-…}`, `${JENKINS_URL:-…}`, etc. | Connector URLs | Connector Framework | URL per env | Already externalized (`${VAR}`) — surfaced under `connectors.*` |
| `config/repository.yaml` | 6–24 | `${ECS_REPO_PG_HOST:-postgres}`, `${MINIO_ENDPOINT:-minio:9000}` | Evidence repository + object store | Evidence Governance | Host/port per env | Already externalized — surfaced under `databases.postgres` / `storage` |
| `config/llm.yaml` | 7–35 | `${OLLAMA_URL:-http://host.docker.internal:11434}`, provider base URLs | LLM provider | AI Governance | URL per env | Already externalized — surfaced under `llm` |
| `app/main.py` | (bind) | `0.0.0.0` / `127.0.0.1` | Dev server bind address | Platform | Not env-specific (operator-supplied) | No action (CLI flag) |

## Not found (clean)

* No hardcoded **public IP addresses** in `app/` or `modules/` application code
  (only `0.0.0.0` / `127.0.0.1` dev-bind literals).
* No hardcoded **tenant identifiers** — tenant resolves from `${ECS_TENANT}`.
* No hardcoded **environment names** branching logic (`if env == "prod"` …);
  the only environment concept is the new `ECS_ENV` selector.
* **Application endpoints** (Net Banking, etc.) were referenced only by *name*
  in deterministic demo data — no network endpoints were hardcoded. Forward
  looking host/port/base_url slots are now provided under `applications.*`.

## Conclusion

All environment-specific execution targets are now sourced from
`config/environments/<ECS_ENV>.yaml`. Remaining literals are **safe fallbacks**
that only apply when the environment layer yields no value, preserving the local
demo exactly.
