# ECS Predefined Query Execution Architecture

**Type:** Operations architecture reference. **No code/UI/DB changes.** **Grounding:** `modules/operations/engines/predefined_queries_engine.py` (loads `ECS_Query_Driven_Control_Library_Consolidated.xlsx`, `detect_technology`, `TECH_SIGNATURES`), `query_connectors.py`, `/mvp/predefined-queries`. Complements (does not duplicate) [Execution Workflow](ECS_PREDEFINED_QUERY_EXECUTION_WORKFLOW.md) and [Execution Guide](ECS_PREDEFINED_QUERY_EXECUTION_GUIDE.md). Inferred items marked **[Inferred/Target]**.

---

## Pipeline

```
Framework → Control → Predefined Query → Connector → Target → Execution
→ Output Parsing → Evidence → Repository → Workflow → Dashboard
```

| Stage | Mechanism |
|---|---|
| Framework → Control | `FRAMEWORK_CATALOG` (305 controls) |
| Control → Query | control library Excel (`ECS_Query_Driven_Control_Library_Consolidated.xlsx`); `predefined = bool(query)` |
| Query → Technology | `detect_technology()` via `TECH_SIGNATURES` (deterministic, no AI) |
| Query → Connector → Target | `query_connectors.py` (`CONNECTOR_CONFIG`) routes to target host/service |
| Execution | connector runs query/command against target |
| Parsing | output parsed → pass/fail + extracted values |
| Evidence | result stored as evidence + mapped to control/framework |
| Repository | `evidence` + maps in PostgreSQL |
| Workflow | review/approval (Evidence Review) |
| Dashboard | coverage/maturity KPIs, Predefined Queries screen |

## Target technologies (`TECH_SIGNATURES`)

| Target | Detection signatures (sample) | Status |
|---|---|---|
| **PostgreSQL** | `pg_stat_replication`, `show ssl`, `show password_encryption`, `pg_*` | Supported |
| **Linux** | `df -h`, `free -m`, `timedatectl`, `/etc/ssh/sshd_config`, `systemctl status` | Supported |
| **Nginx** | `nginx -t`, `nginx -T` | Supported |
| **Oracle** | `dba_role_privs`, `v$encryption_wallet`, `v$*`, `dba_*` | Supported |
| **Windows** | `get-hotfix`, `get-mpcomputerstatus`, `get-aduser`, `powershell` | Supported |
| **SonarQube** | `/api/issues/search`, `sonarqube` | Supported |
| **Trivy** | `trivy image`, `trivy` | Supported |
| **Gitleaks** | `gitleaks detect`, `gitleaks` | Supported |
| **MySQL** | (SQL-style queries) | **[Inferred/Target]** — not in `TECH_SIGNATURES` |
| **SQL Server** | (T-SQL/PowerShell) | **[Inferred/Target]** |
| **Tomcat** | (middleware config checks) | **[Inferred/Target]** |
| **Application Targets** | API/app-specific checks | **[Inferred/Target]** |

> Queries whose technology can't be detected → counted as **unsupported/manual** on the Predefined Queries screen (KPIs: controls, queries, manual, unsupported).

## Safety
PostgreSQL queries are constrained by an **allow-list** (`ALLOWED_POSTGRESQL_QUERIES`, `_normalize_query_allowlist`) — read-only checks only, no arbitrary SQL. Connector execution requires `CONNECTOR_CONFIG` loaded (`_connector_config_loaded()`); demo mode reports without live execution.

## Reporting
- **Operations:** automation coverage (controls with queries vs manual/unsupported).
- **Compliance/Audit:** objective pass/fail evidence per control.
- **Risk:** failing checks → findings → Risk Register.

## Cross-references
- Workflow detail: [ECS_PREDEFINED_QUERY_EXECUTION_WORKFLOW.md](ECS_PREDEFINED_QUERY_EXECUTION_WORKFLOW.md)
- Guide: [ECS_PREDEFINED_QUERY_EXECUTION_GUIDE.md](ECS_PREDEFINED_QUERY_EXECUTION_GUIDE.md)
- Baselining frameworks: [OS](../product/OS_BASELINING.md) · [DB](../product/DATABASE_BASELINING.md) · [Nginx](../product/NGINX_BASELINING.md) · [AppSec](../product/APPLICATION_SECURITY.md)
- Scheduler: [ECS_SCHEDULER_REFERENCE.md](ECS_SCHEDULER_REFERENCE.md)
