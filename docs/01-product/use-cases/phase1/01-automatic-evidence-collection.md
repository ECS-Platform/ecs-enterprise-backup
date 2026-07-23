# Automatic Evidence Collection

## Purpose

Automatically collect compliance evidence from configured sources on a schedule or manual trigger, normalize it, and persist it into the ECS Evidence Repository so auditors and application owners can review, search, and map evidence to controls.

## Business problem solved

Manual evidence gathering is slow, inconsistent, and hard to trace. Automatic collection gives repeatable, timestamped artefacts tied to applications, environments, and controls—with the same path used for scheduler runs and connector execution.

## Phase-1 scope

- **In scope:** Scheduled and manual collection via the ECS Scheduler; SharePoint Graph connector path (mock/demo by default); Deterministic Predefined Query execution with evidence persistence; custody snapshot to object storage; mirror into audit and operations repositories; workflow enrollment.
- **Out of scope:** Live SharePoint enabled by default; non-deterministic AI collection; additional connector families beyond Phase-1 SharePoint and predefined-query paths.

## High-level workflow

```
Scheduler / manual run
  → Select application & framework scope
  → Execute SharePoint connector jobs and/or predefined queries
  → Validate connector result (predefined queries: deterministic)
  → Apply custody (SNAPSHOT) and store object
  → Register operations evidence row + audit repository version
  → Optional PGVector indexing (incremental)
  → Enroll in owner workflow queue
```

## Existing implementation (reuse current code)

| Area | Module / service |
|------|------------------|
| Scheduler orchestration | `modules/operations/engines/scheduler_module.py` |
| SharePoint ingestion | `modules/operations/integrations/sharepoint_graph.py`, asset scheduler plan/execute |
| Predefined query execution | `modules/operations/engines/predefined_queries_engine.py`, `connector_common.py`, `predefined_query_publisher.py` |
| Persistence | `modules/operations/engines/evidence_repository.register_upload`, audit `evidence_repository.store_evidence` |
| Custody & objects | `modules/audit_intelligence/services/evidence_custody.py`, `ecs_platform/storage/object_store.py` |

## Existing APIs

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/mvp/scheduler/run` | Manual collection run (HTML redirect or JSON with headers) |
| GET | `/mvp/scheduler/run-status` | Async run progress |
| GET | `/mvp/scheduler/fetched-evidence/view` | Inspect fetched evidence for a run |
| POST | `/mvp/predefined-queries/run` | Run single predefined query with persistence |
| GET | `/api/audit/runs` | Audit intelligence run APIs (orchestrated collection) |

## Existing UI pages

| Page | Route |
|------|-------|
| Scheduler | `/mvp/scheduler` |
| Predefined Queries | `/mvp/predefined-queries`, `/mvp/predefined-queries/detail` |
| Fetched evidence viewer | `/mvp/scheduler/fetched-evidence/view` |

## Existing tests

- `tests/test_phase1_e2e_lifecycle_validation.py`
- `tests/test_scheduler_run_wiring.py`
- `tests/test_scheduler_source_summary.py`
- `tests/test_unified_evidence_lifecycle.py`
- `tests/test_predefined_query_evidence_ingestion.py`
- `tests/test_sharepoint_graph_connector.py`
- `tests/test_connector_execution_ingestion.py`

## Demo scenario

1. Open **Scheduler** (`/mvp/scheduler?role=owner&user=Demo`).
2. Select **Net Banking** and **PCI DSS** (or leave defaults in demo mode).
3. Click **Run collection** — mock SharePoint and predefined-query paths execute when flags allow.
4. Open **Fetched evidence** or **Evidence Dashboard** — new rows appear with `scheduler_run_id` metadata.
5. Optionally run **PGX-001** from **Predefined Queries** for a visible PostgreSQL SSL artefact.

## Known Phase-1 limitations

- SharePoint live collection requires explicit configuration; demo uses mock/local paths.
- Collection scope is filtered by RBAC application/framework selections.
- Common Control folders are collected by the same scheduler but are documented under Common Control Library.
- PGVector embedding is incremental but fingerprint indexes are in-memory until repopulated after cold restart.
