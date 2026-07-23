# Deterministic Predefined Queries

## Purpose

Execute catalogued, technology-specific queries (PostgreSQL, NGINX, Redis, etc.) that produce **deterministic JSON evidence** for control baselining—with duplicate-safe persistence and framework/common-control mapping.

## Business problem solved

Repeated manual query execution for audits is inconsistent. Predefined queries standardize what is run, how results are formatted, and how evidence is hashed and stored.

## Phase-1 scope

- **In scope:** Phase-1 registry of ready queries; live/demo execution; JSON artefact with columns/result; substantive-content dedup; scheduler batch collection; APIs for list/detail/mappings; incremental PGVector indexing; workflow enrollment.
- **Out of scope:** Ad hoc SQL editor for production DBs without guardrails; LLM-generated query text.

## High-level workflow

```
User or scheduler selects control_id (e.g. PGX-001)
  → Connector executes query → ConnectorResult
  → publish_predefined_query_evidence
  → build_artifact_json → full SHA-256 + canonical fingerprint
  → Duplicate check → register_upload → audit version → index (if new)
  → complete_connector_execution returns evidence_id / DUPLICATE
```

## Existing implementation (reuse current code)

| Area | Module / service |
|------|------------------|
| Engine | `modules/operations/engines/predefined_queries_engine.py` |
| Publisher | `modules/operations/engines/predefined_query_publisher.py` |
| Connector glue | `modules/operations/engines/connector_common.py` |
| Service layer | `modules/operations/services/predefined_queries_service.py` |
| Registry | `config/predefined_query_phase1_registry.yaml` |

## Existing APIs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/predefined-queries` | Catalogue list |
| GET | `/api/predefined-queries/{control_id}` | Control detail |
| GET | `/api/predefined-queries/{control_id}/mappings` | Common control + FCM refs |
| POST | `/mvp/predefined-queries/run` | Execute with persistence |

## Existing UI pages

| Page | Route |
|------|-------|
| Predefined Queries | `/mvp/predefined-queries` |
| Query detail / run | `/mvp/predefined-queries/detail?control_id=PGX-001` |

## Existing tests

- `tests/test_predefined_query_phase1_validation.py`
- `tests/test_predefined_query_evidence_dedup.py`
- `tests/test_predefined_query_incremental_embedding.py`
- `tests/test_predefined_query_phase1.py`
- `tests/test_predefined_query_evidence_workflow.py`

## Demo scenario

1. Open **Predefined Queries**, select **PGX-001** (PostgreSQL SSL).
2. Run query — JSON evidence persisted, object key under `predefined-query/...`.
3. Run again same day same result — **DUPLICATE**, no new embedding.
4. `GET /api/predefined-queries/PGX-001/mappings` — shows encryption-in-transit common control linkage.

## Known Phase-1 limitations

- Execution targets depend on demo/UAT asset config; unsupported controls are diagnosed and skipped.
- Substantive dedup is per evidence period (day).
- Volatile fields (`executed_at`, `scheduler_run_id`) are excluded from canonical hash but retained in artefact metadata.
