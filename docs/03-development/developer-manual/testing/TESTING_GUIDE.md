# ECS Testing Guide

The unified entry point for testing ECS: compile checks, pytest, and per-area test
suites (connectors, predefined queries, prompts/LLM, DB Agent, workbenches,
dry-run, config validation).

> **Reuse note.** Detailed guides already exist; this page unifies the commands
> and links out (it does not duplicate). Test strategy context is in
> [`../developer-manual/ECS_ENGINEERING_HANDBOOK.md`](../developer-manual/ECS_ENGINEERING_HANDBOOK.md) §9.

---

## Compile + full suite

```bash
python -m compileall -q app modules scripts tests config
PYTHONPATH=. pytest -q -p no:cacheprovider
```

Tests run offline by default (`DEMO_MODE=true`, `ECS_AUTH_ENABLED=false`,
`ECS_VALIDATE_CONFIG=off`). CI mirrors this — `.github/workflows/ci.yml`,
`.github/workflows/config-validation.yml`; `make ci` / `make test` locally.

## Targeted suites

| Area | Command | Guide |
|------|---------|-------|
| Smoke / E2E | `pytest tests/test_ecs_demo_smoke.py tests/test_final_audit_route_smoke.py -q` | [`E2E_SMOKE_TEST_GUIDE.md`](E2E_SMOKE_TEST_GUIDE.md) |
| Connectors | `pytest tests/test_connector_test_workbench.py tests/test_integration_adapters_mocked.py tests/test_cloud_security_connectors.py tests/test_cicd_scm_adapters.py -q` | [`../developer-manual/TEST_WORKBENCH_GUIDE.md`](../developer-manual/TEST_WORKBENCH_GUIDE.md) |
| Connector execution/ingestion | `pytest tests/test_connector_execution_ingestion.py -q` | [`../connectors/INTEGRATION_ADAPTERS_GUIDE.md`](../connectors/INTEGRATION_ADAPTERS_GUIDE.md) |
| Predefined queries | `pytest tests/test_predefined_db_connectors.py tests/test_predefined_extended_connectors.py -q` | [`PREDEFINED_QUERY_TESTING_GUIDE.md`](PREDEFINED_QUERY_TESTING_GUIDE.md) |
| Scheduler | `pytest tests/test_uat_asset_scheduler.py tests/test_scheduler_execution.py -q` | [`../scheduler/README.md`](../scheduler/README.md) |
| Prompts / LLM | `pytest tests/test_audit_llm_workbench.py tests/test_audit_llm_evaluation.py tests/test_rag_answer_validation.py -q` | [`../developer-manual/PROMPT_TESTING_GUIDE.md`](../developer-manual/PROMPT_TESTING_GUIDE.md) |
| DB Agent | `pytest tests/test_db_agent.py -q` | [`../developer-manual/DATABASE_AGENT_GUIDE.md`](../developer-manual/DATABASE_AGENT_GUIDE.md) |
| Security headers / hardening | `pytest tests/test_security_headers.py tests/test_production_hardening.py tests/test_security_mode.py -q` | [`../production/PRODUCTION_HARDENING_GUIDE.md`](../production/PRODUCTION_HARDENING_GUIDE.md) |
| Config validation | `pytest tests/test_uat_config_placeholders.py tests/test_deployment_config.py -q` | [`../runbooks/CONFIG_VALIDATION_FAILURE_RUNBOOK.md`](../runbooks/CONFIG_VALIDATION_FAILURE_RUNBOOK.md) |
| RBAC | `pytest tests/test_authz_phase2.py tests/test_rbac_enforcement_phase2_step2b.py -q` | [`../architecture/ECS_ROLE_ACTION_MATRIX.md`](../../../02-architecture/architecture/ECS_ROLE_ACTION_MATRIX.md) |

## Dry-run / config validation checks

```bash
# Scheduler dry-run (no queries, no connector calls)
curl -s -X POST localhost:8000/api/audit/scheduler/dry-run
# Connector dry-run / parser-test (no network)
curl -s -X POST localhost:8000/api/connectors/jira/dry-run
# Environment config validation
ECS_ENV=uat python -m config.config_validation uat
```

## Load / performance
- [`ECS_LOAD_TESTING_REFERENCE.md`](ECS_LOAD_TESTING_REFERENCE.md) · benchmarks in [`../benchmarks/`](../../../04-testing/benchmarks/README.md).

## Validation reports
- [`ECS_KPI_VALIDATION_REPORT.md`](ECS_KPI_VALIDATION_REPORT.md) · [`ECS_SCREEN_VALIDATION_REPORT.md`](ECS_SCREEN_VALIDATION_REPORT.md) · [`ECS_WORKFLOW_VALIDATION_REPORT.md`](ECS_WORKFLOW_VALIDATION_REPORT.md)

## Related
- [`../developer-manual/DEVELOPER_MANUAL.md`](../developer-manual/DEVELOPER_MANUAL.md) · [`../operations/UAT_VALIDATION_RUNBOOK.md`](../operations/UAT_VALIDATION_RUNBOOK.md)
