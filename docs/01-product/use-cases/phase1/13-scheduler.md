# Scheduler

## Purpose

Orchestrate Phase-1 evidence collection sources in one run: connector/mock SharePoint jobs, common controls, and predefined queries—reporting per-source success, duplicates, failures, and embedding counts.

## Business problem solved

Operations teams need a single “collect now” action with visible breakdown—not siloed scripts per source. The scheduler coordinates scope, run ID, and partial failure handling.

## Phase-1 scope

- **In scope:** Manual UI trigger and JSON/async modes; application/framework filtering; source breakdown (connector, mock evidence, common controls, predefined queries); duplicate and embedding summary counts; progress events; run ID propagation; feature flags to skip sources.
- **Out of scope:** OS cron daemon; multi-region collection fan-out.

## High-level workflow

```
POST /mvp/scheduler/run (applications[], frameworks[])
  → run_scheduler_collection
  → Optional live connector plan OR demo mock evidence tree
  → collect_all_common_controls (if enabled)
  → collect_scheduled_predefined_queries (if enabled)
  → build_run_source_breakdown → summary + pgvector_detail
  → Persist run in _execution_history
```

## Existing implementation (reuse current code)

| Area | Module / service |
|------|------------------|
| Orchestrator | `modules/operations/engines/scheduler_module.py` |
| Asset plan | `modules/audit_intelligence/services/asset_scheduler.py` |
| PQ batch | `collect_scheduled_predefined_queries` |
| CC batch | `common_controls_collector.collect_all_common_controls` |

## Existing APIs

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/mvp/scheduler/run` | Start collection |
| GET | `/mvp/scheduler/run-status` | Poll async run |
| POST | `/mvp/scheduler/retry` | Retry failed step (demo) |
| POST | `/mvp/scheduler/pause` / `/resume` | Demo controls |

## Existing UI pages

| Page | Route |
|------|-------|
| Scheduler | `/mvp/scheduler` |
| Fetched evidence | `/mvp/scheduler/fetched-evidence/view` |

## Existing tests

- `tests/test_scheduler_run_wiring.py`
- `tests/test_scheduler_source_summary.py`
- `tests/test_scheduler_collection_progress.py`
- `tests/test_common_controls_scheduler.py`
- `tests/test_phase1_e2e_lifecycle_validation.py` (Scenarios E, disabled collectors)

## Demo scenario

1. Open **Scheduler** with demo flags: mock evidence, common controls, predefined queries enabled.
2. Run for **Net Banking** / **PCI DSS**.
3. Review summary: sources executed, persisted count, duplicates skipped, pgvector detail.
4. Disable `ECS_PREDEFINED_QUERY_SCHEDULER_ENABLED` — predefined-query row shows **skipped** cleanly.
5. Simulate one PQ failure — common controls still **persisted**; run status **Partial**.

## Known Phase-1 limitations

- SharePoint live path stubbed unless connector transport enabled; `sp_enabled=False` in breakdown by default.
- Async run progress is in-process, not distributed queue.
- Embedding counts depend on provider configuration; demo may show provider_unavailable.
