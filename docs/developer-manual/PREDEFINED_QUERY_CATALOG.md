# ECS Predefined Query Catalog

Entry point to the master catalog of predefined queries (by technology, query ID,
framework, control, evidence produced, read-only status, environment support).

> **Reuse note — do not duplicate.** The master catalog is **auto-generated** and
> already exists; regenerating it by hand would drift. This page points to it and
> explains how to regenerate and extend.

## Master catalog (authoritative, auto-generated)
- **[`../use-cases/PREDEFINED_QUERY_INVENTORY.md`](../use-cases/PREDEFINED_QUERY_INVENTORY.md)** —
  full inventory: Query ID, name, technology, frameworks, execution type, evidence
  type, read-only status (208+ controls). Regenerate with:

```bash
PYTHONPATH=. python scripts/run_predefined_query_tests.py inventory
```

## Coverage & execution
- Framework/technology coverage: [`../use-cases/PREDEFINED_QUERY_FRAMEWORK_COVERAGE_MATRIX.md`](../use-cases/PREDEFINED_QUERY_FRAMEWORK_COVERAGE_MATRIX.md)
- Per-control execution matrix: [`../operations/PREDEFINED_QUERY_EXECUTION_MATRIX.md`](../operations/PREDEFINED_QUERY_EXECUTION_MATRIX.md)
- Execution workflow: [`../operations/ECS_PREDEFINED_QUERY_EXECUTION_WORKFLOW.md`](../operations/ECS_PREDEFINED_QUERY_EXECUTION_WORKFLOW.md)
- Architecture: [`../operations/ECS_PREDEFINED_QUERY_ARCHITECTURE.md`](../operations/ECS_PREDEFINED_QUERY_ARCHITECTURE.md)

## Environment support & config
- Targets are defined per environment in `config/environments/<env>.yaml`
  (`predefined_query_targets`) and via `ECS_*` env vars — see
  [`../operations/environment-configuration/00_ENVIRONMENT_CONFIGURATION_GUIDE.md`](../operations/environment-configuration/00_ENVIRONMENT_CONFIGURATION_GUIDE.md)
  and [`../operations/PREDEFINED_QUERY_LOCAL_TO_UAT_MIGRATION_GUIDE.md`](../operations/PREDEFINED_QUERY_LOCAL_TO_UAT_MIGRATION_GUIDE.md).
- All queries are **read-only** (allow-list + statement timeouts).

## Add / develop queries
- [`PREDEFINED_DATABASE_QUERY_MODULE.md`](PREDEFINED_DATABASE_QUERY_MODULE.md) — add queries/connectors, run, test.
- Testing: [`../testing/PREDEFINED_QUERY_TESTING_GUIDE.md`](../testing/PREDEFINED_QUERY_TESTING_GUIDE.md).

## Related
- [`DATABASE_AGENT_GUIDE.md`](DATABASE_AGENT_GUIDE.md) (jump-server execution) · [`DEVELOPER_MANUAL.md`](DEVELOPER_MANUAL.md)
