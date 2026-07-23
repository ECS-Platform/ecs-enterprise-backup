# ECS Test Workbench Guide

The **Connector Test Workbench** lets you exercise any connector safely — with no
credentials and no network — through config-status, dry-run, and parser-test, plus
scheduler simulation and evidence-ingestion simulation.

> **Reuse note.** The full design + REST/code paths live in
> [`connectors/connector_test_workbench_design.md`](connectors/connector_test_workbench_design.md);
> manual UI walkthrough in [`connectors/connector_frontend_manual_testing.md`](connectors/connector_frontend_manual_testing.md);
> per-connector matrix in [`connectors/connector_frontend_testing_matrix.md`](connectors/connector_frontend_testing_matrix.md).
> This page is the developer-manual entry point with **example JSON payloads**.

UI: `/mvp/connectors/test-workbench`. All actions are read-only / mock / dry-run.

---

## Actions & endpoints

| Action | Endpoint | Network? |
|--------|----------|----------|
| List connectors | `GET /api/connectors` | No |
| Config status (masked) | `GET /api/connectors/{name}/config-status` | No |
| Health check | `POST /api/connectors/{name}/health-check` | No (config-based) |
| Dry-run | `POST /api/connectors/{name}/dry-run` | No |
| Parser test (mock transport) | `POST /api/connectors/{name}/parser-test` | No |
| Collect (opt-in, live) | `POST /api/connectors/{name}/collect` | Only if `ECS_CONNECTOR_EXECUTION_ENABLED=true` + configured |

## Example: config-status

```bash
curl -s localhost:8000/api/connectors/jira/config-status
```
```json
{ "ok": true, "name": "jira", "configured": false,
  "masked_config": { "base_url_configured": false, "api_token": "MISSING" } }
```

## Example: dry-run

```bash
curl -s -X POST localhost:8000/api/connectors/jira/dry-run
```
```json
{ "ok": true, "name": "jira", "mode": "dry-run", "configured": false,
  "would_call": "fetch_projects", "auth": "Basic (email + API token)",
  "note": "No network call was made..." }
```

## Example: parser-test (drives the real parser against synthetic data)

```bash
curl -s -X POST localhost:8000/api/connectors/github/parser-test
```
```json
{ "ok": true, "name": "github", "method": "fetch_repositories",
  "source_object_count": 1, "evidence_objects_detected": 1,
  "parser_output_preview": [ { "source": "github", "object_type": "repository",
    "evidence_type": "repository", "source_object_id": "acme/payments" } ],
  "note": "Mock transport — deterministic synthetic data, no network call, no secrets." }
```

## Scheduler simulation (no execution)

```bash
curl -s localhost:8000/api/audit/scheduler/plan
curl -s -X POST localhost:8000/api/audit/scheduler/dry-run
```
Dry-run reports planned jobs + connector readiness with **no** queries/connector
calls. See [`../phase1/scheduler/scheduler_runtime_flow.md`](../phase1/scheduler/scheduler_runtime_flow.md)
and [`../phase1/scheduler/test_workbench_vs_scheduler.md`](../phase1/scheduler/test_workbench_vs_scheduler.md).

## Evidence-ingestion simulation

Inject a mock transport (tests) or run `parser-test` to validate the normalizer.
Live ingestion (opt-in) flows through the standard evidence bridge (SHA-256 +
audit-repo mirror). Test example: `tests/test_connector_execution_ingestion.py`,
`tests/test_cicd_scm_adapters.py`.

## Test commands

```bash
PYTHONPATH=. pytest tests/test_connector_test_workbench.py \
  tests/test_connector_execution_ingestion.py tests/test_cicd_scm_adapters.py -q
```

## Related
- [`connectors/INTEGRATION_ADAPTERS_GUIDE.md`](connectors/INTEGRATION_ADAPTERS_GUIDE.md) · [`DEVELOPER_MANUAL.md`](DEVELOPER_MANUAL.md) · [`../runbooks/SCHEDULER_FAILURE_RUNBOOK.md`](../runbooks/SCHEDULER_FAILURE_RUNBOOK.md)
