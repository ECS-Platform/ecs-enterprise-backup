# ECS Predefined Query — Execution Guide

How the predefined-query module runs, per environment. This is the operator
entry point; deep engine internals live in the companion docs referenced below.

> Related (do not duplicate): architecture in
> [ECS_PREDEFINED_QUERY_ARCHITECTURE.md](ECS_PREDEFINED_QUERY_ARCHITECTURE.md),
> workflow in [ECS_PREDEFINED_QUERY_EXECUTION_WORKFLOW.md](ECS_PREDEFINED_QUERY_EXECUTION_WORKFLOW.md),
> per-control matrix in [PREDEFINED_QUERY_EXECUTION_MATRIX.md](PREDEFINED_QUERY_EXECUTION_MATRIX.md),
> full inventory in [../use-cases/PREDEFINED_QUERY_INVENTORY.md](../use-cases/PREDEFINED_QUERY_INVENTORY.md),
> coverage in [../use-cases/PREDEFINED_QUERY_FRAMEWORK_COVERAGE_MATRIX.md](../use-cases/PREDEFINED_QUERY_FRAMEWORK_COVERAGE_MATRIX.md).

---

## 1. Model

```
Control (Excel + supplementary catalog)
  -> technology  -> connector (query_connectors.connector_for_technology)
  -> execute (SQL / shell / CLI / REST)  against a TARGET
  -> parse + validate  -> evidence (complete_connector_execution -> repository)
```

- **Catalog:** the Excel control library + `modules/operations/engines/supplementary_query_catalog.py` (187 controls).
- **Engine:** `modules/operations/engines/predefined_queries_engine.py` (`run_predefined_query(control_id, user)`).
- **Connectors:** `modules/operations/engines/*_connector.py` (PostgreSQL, Oracle, MySQL, SQL Server, MongoDB, Yugabyte, Linux/NGINX/Apache/Tomcat/RHEL, Redis, Aerospike, Kubernetes, OpenShift, SonarQube, Trivy, GitLeaks).
- **Targets (how to connect):** the per-technology blocks under `predefined_query_targets:` in `config/environments/<env>.yaml`.
- **Targets (which named systems):** the operator registry `config/predefined_query_targets.<env>.yaml`.

Execution is **safe by design**: DB queries are exact-string allow-listed; shell/CLI controls run curated read-only commands; a missing driver/target degrades to a structured "Connector Missing / Configuration Required" status (never a crash).

## 2. Inspect before running

```bash
python scripts/run_predefined_query_tests.py summary
python scripts/run_predefined_query_tests.py dry-run --technology NGINX
python scripts/run_predefined_query_tests.py validate-targets --all
```

`dry-run` reports per-control readiness (`assess_execution_capability`) without any
live connection.

## 3. Run locally (Docker demo targets)

Bring up test targets by weight (see the Testing Guide for profiles):

```bash
docker compose -f docker-compose.predefined-queries.yml --profile minimal up -d
# or --profile standard / --profile extended
```

Then execute a control via the CLI runner (existing):

```bash
PYTHONPATH=. python scripts/run_predefined_query.py NGX-001 --user operator
PYTHONPATH=. python scripts/run_predefined_db_query.py PGX-001 --user operator
```

Or via the UI / API (Predefined Queries page → Run Query). Diagnostics:

```bash
python scripts/check_predefined_technology_environment.py
python scripts/check_predefined_extended_environment.py
python scripts/check_predefined_db_environment.py
```

## 4. Switch to UAT / PROD / DR (config only)

No code change — select the environment and point the config at the real hosts:

```bash
export ECS_ENV=uat            # or prod / dr
# option A: server lists via env vars (comma-separated)
export ECS_TARGET_OS_SERVERS=<uat-os-hosts> ECS_TARGET_DB_SERVERS=<uat-db-hosts>
# option B: per-technology endpoints via the env YAML / env vars
#   ECS_PG_HOST, ECS_ORACLE_HOST, ECS_NGINX_HOST/container, etc.
# option C: named targets in config/predefined_query_targets.uat.yaml (enabled: true)
```

See [PREDEFINED_QUERY_LOCAL_TO_UAT_MIGRATION_GUIDE.md](PREDEFINED_QUERY_LOCAL_TO_UAT_MIGRATION_GUIDE.md).

## 5. Credentials

Secrets are read from the environment (`*_env` names in the YAML) or a vault —
never stored in YAML. In the named-target registry, targets reference secrets by
`credential_ref` (e.g. `vault://ecs/uat/postgres`). Diagnostics/config output show
secrets as `SET`/`MISSING` only.

## 6. Evidence

On success, `complete_connector_execution(...)` records an execution audit and
registers evidence via `register_with_evidence_repository(...)` → the evidence
repository (and mirrors to the audit-intelligence repository). Each result carries
the control_id, technology, framework(s), query, row/line count, output excerpt,
and an evidence id/filename.

## 7. Scheduler

The asset scheduler (`modules/audit_intelligence/services/asset_scheduler.py`)
plans evidence jobs from the asset config and executes them
(`execute_plan` / `scheduler_execution.execute_parallel`). Predefined-query
targets are selected from the environment config + the target registry — the
scheduler is reused, not re-implemented.

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Connector Missing` | driver not installed | `pip install -r requirements.txt` (psycopg2/pymysql/oracledb/pyodbc/pymongo) |
| `Configuration Required` | target host/creds absent | set `ECS_*_HOST`/`*_PASSWORD` or enable the registry target |
| `not reachable` | firewall/VPN/host down | confirm network path from the ECS host to the target |
| Wrong environment | `ECS_ENV` unset | `export ECS_ENV=uat` (etc.) |
| localhost in UAT/PROD/DR | copy-paste error | validators reject it — fix the host in the registry / env YAML |
