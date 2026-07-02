# ECS Predefined Query Implementation Plan

**Mode:** READ-ONLY / ANALYSIS / DOCUMENTATION. **No code changes. No commits.** **Grounding:** `modules/operations/engines/predefined_queries_engine.py` (`run_predefined_query`, `run_postgresql_query`, `_run_connector_query`, `is_live_execution_enabled`), `postgresql_connector.py`, `linux_connector.py`, `sonarqube_connector.py`, `trivy_connector.py`, `gitleaks_connector.py`, `query_connectors.py`, `config/environments/_base.yaml`.

---

## 1. Current implementation (VERIFIED — already working)

Live execution **is implemented** and dispatched by `run_predefined_query(control_id, user)` → by `technology`:

| Technology | Connector (impl) | Mechanism | Status |
|---|---|---|---|
| PostgreSQL | `PostgreSQLConnector` | `psycopg2.connect()` + `cur.execute()`, `SET statement_timeout` | ✅ Implemented |
| Linux | `LinuxConnector` | `subprocess.run()` `docker exec` (ubuntu-demo), `LINUX_CONTROL_COMMANDS` map | ✅ Implemented |
| SonarQube | `SonarQubeConnector` | API mode (`SONAR_CONTROL_MODES`) | ✅ Implemented |
| Trivy | `TrivyConnector` | `subprocess.run()` (image scan) | ✅ Implemented |
| Gitleaks | `GitLeaksConnector` | `subprocess.run()` (secret scan) | ✅ Implemented |

Guards: `is_live_execution_enabled(control)` gates dispatch; unknown technology → structured `unsupported_technology`. PostgreSQL queries pass through the **read-only allow-list** (`ALLOWED_POSTGRESQL_QUERIES`, `_normalize_query_allowlist`).

## 2. Missing runtime execution (the real gap)

The **generic, remote-target** connectors in `query_connectors.py` are stubs:

| Generic connector | Intended targets | Current |
|---|---|---|
| `DatabaseConnector` | Oracle, MySQL, SQL Server (network) | `raise NotImplementedError` (connect + execute) |
| `SSHConnector` | remote Linux hosts (vs demo docker exec) | `raise NotImplementedError` |
| `APIConnector` | generic HTTP/API targets | `raise NotImplementedError` |

Also: `TECH_SIGNATURES` lacks MySQL / SQL Server / Tomcat / Application detection (those queries fall to manual/unsupported).

## 3. Required architecture (to close the gap)

```
Control(technology) → run_predefined_query → dispatch
  ├─ demo execution (DONE): PostgreSQL/Linux/SonarQube/Trivy/Gitleaks
  └─ remote execution (TO BUILD):
       DatabaseConnector → driver per dialect (oracledb / PyMySQL / pyodbc)
       SSHConnector      → paramiko/asyncssh to target host (key/password from env)
       APIConnector      → http_client with auth + pagination
       → ConnectorResult (rows/exit/stdout) → parse → evidence
```

Principles: reuse `ConnectorResult` contract + `connector_common.py`; per-dialect read-only allow-lists (mirror PostgreSQL allow-list); credentials strictly from env/vault; resilient (structured failure, never crash a batch).

## 4. Connector execution flow (target)

```
Framework target group (os/db/mw/appsec from env) → resolve target hosts
→ select control + query → detect_technology → instantiate connector (config from env)
→ connector.connect() → connector.execute(query) → ConnectorResult
→ parse pass/fail + extracted values → build evidence record
```

## 5. Evidence generation flow (existing pattern to reuse)
`_run_connector_query()` already converts a `ConnectorResult` into a query-execution result for demo connectors. Extend the same path so remote connectors feed `predefined_query_evidence` → evidence rows → `evidence_control_map` / `evidence_framework_map` → repository → Evidence Review workflow → dashboards (Predefined Queries KPIs).

## 6. Target environment flow
`config/environments/<ECS_ENV>.yaml` → `predefined_query_targets.{os_servers,db_servers,middleware_servers,appsec_targets}` (currently `[]`) + per-tech blocks (postgresql/linux/sonarqube/trivy/gitleaks). Populate per env; CSV env overrides (`ECS_TARGET_*`) supported by `environment_loader._apply_target_overrides()`.

## 7. YAML integration
- Add target host lists to `uat.yaml` / `prod.yaml` (no `_base.yaml` change needed).
- Add remote DB/SSH/API target blocks (host/port/service/user/`password_env`/`timeout_sec`) mirroring `databases:` in `_base.yaml` (oracle/mysql/sqlserver already have slots).
- Secrets remain `*_env` names only.

## 8. Estimated effort

| Workstream | Effort |
|---|---|
| `DatabaseConnector` (Oracle/MySQL/SQL Server, drivers, allow-lists) | 5 eng-days |
| `SSHConnector` (paramiko, key mgmt, command map) | 3 eng-days |
| `APIConnector` (auth, pagination) | 2 eng-days |
| `TECH_SIGNATURES` for MySQL/SQL Server/Tomcat/Application | 1 eng-day |
| Evidence-path wiring + parsers per dialect | 2 eng-days |
| Tests (unit + integration against test targets) | 3 eng-days |
| **Total** | **~16 eng-days** |

> Demo-target execution needs **0 additional effort** (already implemented). Effort above is solely for remote/production targets.

## Cross-references
- [Engineering Gap Analysis (P1-01/03)](ECS_P1_ENGINEERING_GAP_ANALYSIS.md) · [Connector Activation Plan](ECS_CONNECTOR_ACTIVATION_PLAN.md) · [Predefined Query Architecture](../operations/ECS_PREDEFINED_QUERY_ARCHITECTURE.md) · [Execution Roadmap](ECS_PHASE1_EXECUTION_ROADMAP.md)
