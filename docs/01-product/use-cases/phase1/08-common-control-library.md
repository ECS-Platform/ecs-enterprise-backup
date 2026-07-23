# Common Control Library

## Purpose

Maintain ten framework-independent common controls with mock evidence, deterministic validation, and FCM cross-references—collectable via the scheduler and reusable across all supported frameworks.

## Business problem solved

The same operational control (e.g. encryption in transit) applies to many frameworks. A shared library avoids duplicating control definitions and lets one evidence artefact support multiple framework mappings.

## Phase-1 scope

- **In scope:** Ten controls under `CommonControls/`; manifest + evidence.json per folder; deterministic validation (PASS/WARNING/FAIL); observation on FAIL; scheduler collection; framework-independent metadata; FCM reference resolution; REST catalogue APIs.
- **Out of scope:** Live scanner integration; AI validation.

## High-level workflow

```
Scheduler (or direct collector) discovers CommonControls/<slug>/
  → Load manifest + evidence.json
  → validate_evidence (deterministic rules)
  → Custody SNAPSHOT → store_evidence + register_upload
  → enroll_collected_evidence; generate observation if FAIL
  → Metadata: framework_independent=true, fcm_reference_count, validation_verdict
```

## Existing implementation (reuse current code)

| Area | Module / service |
|------|------------------|
| Catalogue | `modules/operations/engines/common_controls_catalog.py` |
| Collector | `modules/operations/engines/common_controls_collector.py` |
| Service / FCM refs | `modules/frameworks/services/common_controls_service.py` |
| Observations | `modules/audit_intelligence/engines/observation_generation.py` |

## Existing APIs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/common-controls` | List all controls |
| GET | `/api/common-controls/{slug}` | Detail + framework mappings |
| GET | `/api/common-controls/framework/{framework_id}` | Controls for a framework |

## Existing UI pages

| Page | Route |
|------|-------|
| Evidence Dashboard (common controls summary) | `/mvp/evidence-dashboard` |
| Scheduler (common controls source row) | `/mvp/scheduler` |

## Existing tests

- `tests/test_common_controls_phase1_validation.py`
- `tests/test_common_controls_scheduler.py`
- `tests/test_phase1_e2e_lifecycle_validation.py` (Certificate Management FAIL scenario)

## Demo scenario

1. Enable `ECS_COMMON_CONTROLS_COLLECTION_ENABLED=true`.
2. Run **Scheduler** — ten folders discovered, collected, metadata persisted.
3. Inspect **certificate-management** — validation **FAIL** (expiring cert), observation created, evidence still in repository.
4. `GET /api/common-controls/encryption-at-rest` — shows FCM mappings for PCI DSS, Database Baseline, etc.
5. Recollect **audit-logging** unchanged — duplicate detected, one ops row.

## Known Phase-1 limitations

- Evidence files are mock JSON under `CommonControls/`, not live infrastructure scans.
- Controls remain **framework-independent** in metadata; framework mapping is via FCM cross-reference, not duplicate control rows.
- Predefined query IDs in manifests link to alternate collection paths documented under Deterministic Predefined Queries.
