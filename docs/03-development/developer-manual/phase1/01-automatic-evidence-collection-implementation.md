# Automatic Evidence Collection — Phase-1 Implementation

## Purpose

Implement scheduled and manual collection of SharePoint and deterministic predefined-query evidence into the ECS repository stack.

## Business requirement

See [Automatic Evidence Collection (business)](../../../01-product/use-cases/phase1/01-automatic-evidence-collection.md).

## Functional flow

```
Scheduler / POST /mvp/predefined-queries/run
  → asset_scheduler.plan_evidence / execute_plan (SharePoint)
  → predefined_queries_engine.run_predefined_query
  → connector_common.complete_connector_execution
  → predefined_query_publisher.publish_predefined_query_evidence
  → evidence_repository.register_upload → custody → audit mirror → index hook
```

Deep dive: [EVIDENCE_COLLECTION_GUIDE.md](EVIDENCE_COLLECTION_GUIDE.md), [scheduler/scheduler_runtime_flow.md](scheduler/scheduler_runtime_flow.md).

## High-level design

- **Orchestration:** `scheduler_module.run_scheduler_collection` aggregates connector, mock, common-controls, and predefined-query sources.
- **Connectors:** SharePoint via `sharepoint_graph` + asset scheduler; predefined queries via technology-specific connector runners.
- **Persistence:** Single path through `register_upload` and audit `store_evidence`.

Design reference: [../../design/phase1/Mock SharePoint Graph Evidence Collection.md](../../../02-architecture/design/phase1/Mock%20SharePoint%20Graph%20Evidence%20Collection.md).

## Components

| Component | Path |
|-----------|------|
| Scheduler | `modules/operations/engines/scheduler_module.py` |
| Asset plan/execute | `modules/audit_intelligence/services/asset_scheduler.py` |
| PQ engine | `modules/operations/engines/predefined_queries_engine.py` |
| Publisher | `modules/operations/engines/predefined_query_publisher.py` |
| SharePoint | `modules/operations/integrations/sharepoint_graph.py` |

## APIs

| Method | Path |
|--------|------|
| POST | `/mvp/scheduler/run` |
| POST | `/mvp/predefined-queries/run` |
| GET | `/api/predefined-queries`, `/api/predefined-queries/{control_id}` |

Full mapping: [../../use-cases/phase1/reference/use_case_backend_api_mapping.md](../../../01-product/use-cases/phase1/reference/use_case_backend_api_mapping.md).

## Database objects

- Audit SQL persistence: `SqlAuditPersistence` — evidence versions (`modules/audit_intelligence/services/sql_persistence.py`).
- Schema reference: [../database/AUDIT_INTELLIGENCE_PERSISTENCE_GUIDE.md](../database/AUDIT_INTELLIGENCE_PERSISTENCE_GUIDE.md), [../../architecture/ECS_DATA_ARCHITECTURE_REFERENCE.md](../../../02-architecture/architecture/ECS_DATA_ARCHITECTURE_REFERENCE.md).

## Metadata

Collected metadata includes `source_type`, `query_id`, `scheduler_run_id`, `object_key`, FCM enrichment — see [02-metadata-tagging-implementation.md](02-metadata-tagging-implementation.md).

## Scheduler interaction

Primary entry: [scheduler/ECS_SCHEDULER_REFERENCE.md](scheduler/ECS_SCHEDULER_REFERENCE.md). Feature flags: `ECS_PREDEFINED_QUERY_SCHEDULER_ENABLED`, `ECS_MOCK_EVIDENCE_COLLECTION_ENABLED`, `ECS_COMMON_CONTROLS_COLLECTION_ENABLED`.

## Object storage

SNAPSHOT custody via `evidence_custody.resolve_custody` → `LocalObjectStore` / MinIO. See [../../use-cases/phase1/12-object-storage-evidence-custody.md](../../../01-product/use-cases/phase1/12-object-storage-evidence-custody.md).

## Repository integration

`register_upload` → `_mirror_to_audit_repository` → authoritative reader merge. See [../../use-cases/phase1/05-evidence-repository.md](../../../01-product/use-cases/phase1/05-evidence-repository.md).

## Dashboard integration

Collection KPIs via `module_capabilities._evidence_dashboard_view` → scheduler summary embedded in dashboard collection block.

## Search integration

Indexed after persist through `ecs_platform/evidence_indexing.index_after_persist`; searchable via `search_module.search_evidences`.

## Chatbot integration

Presets `latest_5_evidences`, `evidence_by_scheduler_run` read `collect_persisted_evidence_rows()`.

## Configuration

- `config/uat_assets.local.yaml`, `config/predefined_query_phase1_registry.yaml`
- Env: `ECS_EVIDENCE_CUSTODY_MODE`, `ECS_EVIDENCE_SNAPSHOT_ENABLED`, `DEMO_MODE`

See [../ENVIRONMENT_CONFIGURATION.md](../ENVIRONMENT_CONFIGURATION.md).

## Feature flags

| Flag | Effect |
|------|--------|
| `ECS_PREDEFINED_QUERY_SCHEDULER_ENABLED` | PQ batch in scheduler |
| `ECS_MOCK_EVIDENCE_COLLECTION_ENABLED` | Demo mock evidence tree |
| `ECS_COMMON_CONTROLS_COLLECTION_ENABLED` | Common control folders (separate use case) |

## Source files

Listed under **Components**. Additional: [PREDEFINED_DATABASE_QUERY_MODULE.md](PREDEFINED_DATABASE_QUERY_MODULE.md), [ECS_PREDEFINED_QUERY_EXECUTION_GUIDE.md](ECS_PREDEFINED_QUERY_EXECUTION_GUIDE.md).

## Testing

- `tests/test_phase1_e2e_lifecycle_validation.py`
- `tests/test_scheduler_run_wiring.py`
- `tests/test_predefined_query_phase1_validation.py`
- [../testing/E2E_SMOKE_TEST_GUIDE.md](../../../04-testing/testing/E2E_SMOKE_TEST_GUIDE.md)

## Troubleshooting

- Zero PQ persisted: check `ECS_PREDEFINED_QUERY_SCHEDULER_ENABLED`, control capability diagnosis, `execution_persist_enabled()`.
- SharePoint mock vs live: [../connectors/SHAREPOINT.md](../connectors/SHAREPOINT.md).
- Scheduler partial failure: inspect `source_breakdown` in run JSON.

## Known limitations

- Phase-1 automated sources: SharePoint path + predefined queries only (per product scope).
- Live SharePoint off by default; mock/demo ingestion common.
- Incremental embedding fingerprint indexes in-memory until repopulated.
