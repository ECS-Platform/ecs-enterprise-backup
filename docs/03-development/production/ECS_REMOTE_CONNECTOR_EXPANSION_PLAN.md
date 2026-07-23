# ECS Remote Connector Expansion Plan

**Mode:** READ-ONLY / ANALYSIS / DOCUMENTATION. **No code changes. No commits.** **Grounding:** `modules/operations/engines/query_connectors.py` (`DatabaseConnector`/`SSHConnector`/`APIConnector` stubs), `postgresql_connector.py` (reference impl with psycopg2 + read-only allow-list), `predefined_queries_engine.run_predefined_query`, `config/environments/_base.yaml` (`databases:` slots: oracle/mysql/sqlserver).

> **Context:** demo/reachable targets already execute (PostgreSQL/Linux/SonarQube/Trivy/Gitleaks). This plan covers the **generic remote production connectors** that currently `raise NotImplementedError`. Pattern to follow: `postgresql_connector.py` (config from env layer → `ConnectorResult` → evidence → dashboards) + read-only query allow-list.

---

## Shared design (all remote connectors)
- Config from active-env YAML → `ECS_*` env → default; secrets only via `*_env` names / vault.
- **Read-only allow-list per dialect** (mirror `ALLOWED_POSTGRESQL_QUERIES`); enforce statement timeouts.
- Return `ConnectorResult` (rows/exit/stdout/error_type) → reuse `_run_connector_query()` evidence path.
- Structured failure (timeout / auth_failure / connection_refused), never crash a batch.
- Register dispatch in `run_predefined_query()` by `technology`; add `TECH_SIGNATURES` entries.

## 1. Oracle
| Item | Detail |
|---|---|
| Driver | `oracledb` (thin mode preferred; thick needs Instant Client) |
| Config | `databases.oracle` slot + `ECS_ORACLE_*` (host/port/service/user/`password_env`) |
| Targets | DB baseline controls (audit settings, profiles, privileges, encryption) |
| Effort | 2–3 eng-days |
| Risk | Med — thick-client deps, privilege to read DBA views |

## 2. MySQL
| Item | Detail |
|---|---|
| Driver | `PyMySQL` (pure-python) or `mysqlclient` |
| Config | `databases.mysql` + `ECS_MYSQL_*` |
| Targets | DB baseline (`SHOW VARIABLES`, user/grants, SSL, audit) |
| Effort | 1–2 eng-days |
| Risk | Low–Med |
| Tech signatures | add `MySQL` to `TECH_SIGNATURES` |

## 3. SQL Server
| Item | Detail |
|---|---|
| Driver | `pyodbc` (+ MS ODBC Driver 18) or `pymssql` |
| Config | `databases.sqlserver` + `ECS_MSSQL_*` |
| Targets | DB baseline (sys configs, logins, TDE state, audit) |
| Effort | 2 eng-days |
| Risk | Med — ODBC driver install on host/image |
| Tech signatures | add `SQLServer` |

## 4. Windows (host)
| Item | Detail |
|---|---|
| Mechanism | WinRM (`pywinrm`) or remote PowerShell; (no SSH by default on Windows) |
| Config | `ECS_WIN_*` (host/user/`password_env`/transport) |
| Targets | OS baseline (registry, services, audit policy, patch state via `Get-HotFix`) |
| Effort | 3–4 eng-days |
| Risk | Med–High — WinRM auth (Kerberos/NTLM), HTTPS listener, command mapping |

## 5. Generic SSH (Linux remote)
| Item | Detail |
|---|---|
| Mechanism | `paramiko` (or `asyncssh`); key or password auth |
| Config | `ECS_SSH_*` (host/port/user/key_path or `password_env`) |
| Targets | OS baseline on real hosts (vs demo `docker exec` LinuxConnector) |
| Effort | 3 eng-days |
| Risk | Med — key management, host-key verification, command map reuse (`LINUX_CONTROL_COMMANDS`) |

## 6. Generic API
| Item | Detail |
|---|---|
| Mechanism | reuse `ecs_platform/connectors/http_client.py` patterns; auth (Bearer/Basic/OAuth2), pagination |
| Config | `ECS_API_*` (base_url/auth/token_env) |
| Targets | AppSec/middleware/cloud APIs returning JSON evidence |
| Effort | 2 eng-days |
| Risk | Low–Med — varied auth/response shapes |

## Dependencies
- New Python drivers: `oracledb`, `PyMySQL`/`mysqlclient`, `pyodbc`(+ODBC), `pywinrm`, `paramiko`/`asyncssh`.
- OS-level: MS ODBC driver (SQL Server); Oracle Instant Client (only if thick mode).
- Network egress + read-only service accounts to each target; firewall rules.
- Populated per-env target lists (`predefined_query_targets`) — see [Predefined Query Plan](../../01-product/use-cases/ECS_PREDEFINED_QUERY_IMPLEMENTATION_PLAN.md).

## Effort summary
| Connector | Effort |
|---|---|
| Oracle | 2–3d |
| MySQL | 1–2d |
| SQL Server | 2d |
| Windows (WinRM) | 3–4d |
| Generic SSH | 3d |
| Generic API | 2d |
| Tech signatures + parsers + tests | 3d |
| **Total** | **~16–19 eng-days** |

## Risks
| Risk | Mitigation |
|---|---|
| Driver/OS dependency install in container | Bake into image; document; test in CI |
| Dialect-specific query portability | Per-dialect allow-list + controls library mapping |
| Privilege to read system views | Define minimal read-only grants per target |
| Host-key / WinRM auth complexity | Phase Windows last; pilot one host first |

## Cross-references
- [Predefined Query Implementation Plan](../../01-product/use-cases/ECS_PREDEFINED_QUERY_IMPLEMENTATION_PLAN.md) · [Connector Activation Plan](../../01-product/use-cases/ECS_CONNECTOR_ACTIVATION_PLAN.md) · [Production Master Plan](../production/ECS_PRODUCTION_READINESS_MASTER_PLAN.md) · [Final Roadmap](../production/ECS_FINAL_PRODUCTION_ROADMAP.md)
