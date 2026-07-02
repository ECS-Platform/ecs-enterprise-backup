# ECS Connector Activation Plan (PostgreSQL · Linux · SonarQube · Trivy · Gitleaks)

**Mode:** READ-ONLY / ANALYSIS / DOCUMENTATION. **No code changes. No commits.** **Grounding:** `modules/operations/engines/{postgresql,linux,sonarqube,trivy,gitleaks}_connector.py` (`get_*_config`), `predefined_queries_engine.run_predefined_query`, `config/environments/_base.yaml` (`predefined_query_targets`), `docker-compose.yml` (`postgres-demo`, `ubuntu-demo`, `sonarqube-demo`, `demo-connectors` profile).

> These 5 connectors have **working execution code** (psycopg2 / docker-exec / subprocess / API). "Activation" = bring up the target, supply config/credentials via env, and validate live execution — **no code change required for demo targets**.

---

## Common activation pattern
1. Provision/point at the target (demo container or real host).
2. Set env vars (config resolves: env YAML → `ECS_*` env → historical default).
3. Confirm `is_live_execution_enabled(control)` true for the control's technology.
4. Run `run_predefined_query(control_id, user)` (via `/mvp/predefined-queries/run`).
5. Verify `ConnectorResult` → evidence row → Predefined Queries KPIs.

---

## 1. PostgreSQL (`postgresql_connector.py`)

- **Activation:** start `postgres-demo` (compose) or point at a real read-only DB.
- **Credentials/env:** `ECS_PG_HOST`, `ECS_PG_PORT` (5432), `ECS_PG_DATABASE` (ecs_demo), `ECS_PG_USER` (ecs_user), `ECS_PG_PASSWORD`, `ECS_PG_TIMEOUT_SEC` (30). YAML: `predefined_query_targets.postgresql`.
- **Safety:** only `ALLOWED_POSTGRESQL_QUERIES` (read-only) execute; `SET statement_timeout`.
- **Validation:** run a PG control (e.g., `show ssl`, `pg_stat_replication`); expect rows + pass/fail evidence. Negative test: wrong password → structured `authentication_failure`.

## 2. Linux (`linux_connector.py`)

- **Activation:** start `ubuntu-demo` container (demo-connectors profile). Execution = `docker exec`.
- **Credentials/env:** `ECS_LINUX_CONTAINER` (ubuntu-demo), `ECS_LINUX_TIMEOUT_SEC` (30). Commands from `LINUX_CONTROL_COMMANDS`.
- **Validation:** run a Linux control (e.g., `cat /etc/ssh/sshd_config`, `timedatectl`); expect stdout parsed to pass/fail. Negative: container down → structured failure (no crash).
- **Note:** remote (non-container) hosts need the **`SSHConnector`** (currently NotImplemented — see [Predefined Query Implementation Plan](ECS_PREDEFINED_QUERY_IMPLEMENTATION_PLAN.md)).

## 3. SonarQube (`sonarqube_connector.py`)

- **Activation:** start `sonarqube-demo` (compose) or point at a real instance; issue a token.
- **Credentials/env:** `ECS_SONAR_URL` (http://sonarqube-demo:9000), `ECS_SONAR_USER` (admin), `ECS_SONAR_TOKEN` (preferred) or `ECS_SONAR_PASSWORD`, `ECS_SONAR_TIMEOUT_SEC` (30). Modes from `SONAR_CONTROL_MODES`.
- **Validation:** run an AppSec control (quality gate / `/api/issues/search`); expect issues/coverage → evidence. Negative: bad token → `authentication_failure`.

## 4. Trivy (`trivy_connector.py`)

- **Activation:** ensure Trivy available (image `aquasec/trivy`); subprocess scan.
- **Credentials/env:** `ECS_TRIVY_IMAGE` (alpine:3.19 default scan target), `ECS_TRIVY_TIMEOUT_SEC` (120). No auth (local scan).
- **Validation:** run a Trivy control (`trivy image`); expect CVE summary → evidence. Negative: missing binary/image → structured failure.

## 5. Gitleaks (`gitleaks_connector.py`)

- **Activation:** ensure Gitleaks available (image `zricethezav/gitleaks`); subprocess scan.
- **Credentials/env:** `ECS_GITLEAKS_SCAN_PATH` (repo/path to scan), `ECS_GITLEAKS_TIMEOUT_SEC` (120). No auth.
- **Validation:** run a Gitleaks control (`gitleaks detect`); expect secret-findings summary → evidence. Negative: invalid path → structured failure.

---

## Credential management (all)
- Secrets only via env vars / vault (never in YAML or repo).
- Use **read-only** service accounts (PG user, Sonar token scope).
- UAT/PROD: vault-sourced, rotated; set in `uat.yaml`/`prod.yaml` env or container env.

## Validation procedures (checklist)
- [ ] Target reachable (health/port check)
- [ ] Env vars set + resolved (`get_*_config()` returns expected host/port)
- [ ] Control flagged live-executable (`is_live_execution_enabled`)
- [ ] Positive run → evidence row created + mapped to control/framework
- [ ] Negative run (bad creds/target down) → **structured error, no 500**
- [ ] KPIs update on `/mvp/predefined-queries`
- [ ] Audit log records the execution

## Effort
**~3–5 eng-days** total (config + bring-up + per-connector positive/negative validation). **0 code change** for these 5 against demo/reachable targets. (Remote DB/SSH/API targets are a separate build — see Predefined Query Implementation Plan.)

## Cross-references
- [Predefined Query Implementation Plan](ECS_PREDEFINED_QUERY_IMPLEMENTATION_PLAN.md) · [Connector Readiness](../operations/ECS_CONNECTOR_READINESS_REPORT.md) · [Environment Framework Review](../operations/ECS_ENVIRONMENT_FRAMEWORK_REVIEW.md) · [Execution Roadmap](ECS_PHASE1_EXECUTION_ROADMAP.md)
