# Evidence Repository

## Purpose

Provide a single, authoritative view of persisted compliance evidence—linking operations records, audit versions, custody objects, workflow status, and integrity hashes—for auditors, owners, and downstream features (dashboard, search, chatbot).

## Business problem solved

Evidence scattered across uploads, scheduler runs, and connector outputs is hard to audit. The repository consolidates identity, version, metadata, and object references in one read model.

## Phase-1 scope

- **In scope:** Operations in-memory repository; audit intelligence version store with optional SQL persistence; merge via authoritative reader; REST listing; integrity and workflow fields; FCM-enriched metadata; API detail by evidence ID.
- **Out of scope:** External GRC system of record replacement; long-term archival tiering policies.

## High-level workflow

```
register_upload / store_evidence (collection)
  → Operations row + audit version
  → Authoritative reader merges by evidence_id
  → Consumers: /api/evidence/repository, search, dashboard stats, chatbot presets
```

## Existing implementation (reuse current code)

| Area | Module / service |
|------|------------------|
| Operations store | `modules/operations/engines/evidence_repository.py` |
| Audit store | `modules/audit_intelligence/engines/evidence_repository.py` |
| Read facade | `modules/shared/services/evidence_authoritative_reader.py` |
| Service stats | `modules/audit_intelligence/services/audit_repository_service.py` |

## Existing APIs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/evidence/repository` | Authoritative list + stats |
| GET | `/api/evidence/search` | Search with filters |
| GET | `/api/audit/evidence` | Audit repository search |
| GET | `/api/audit/evidence/{evidence_key}/versions` | Version history |

## Existing UI pages

| Page | Route |
|------|-------|
| Evidence Dashboard | `/mvp/evidence-dashboard` |
| Search | `/mvp/search` |
| Evidence Health | `/mvp/evidence-health` |
| Scheduler fetched evidence | `/mvp/scheduler/fetched-evidence/view` |

## Existing tests

- `tests/test_evidence_authoritative_reader.py`
- `tests/test_evidence_repository_persistence.py`
- `tests/test_phase1_e2e_lifecycle_validation.py`
- `tests/test_audit_intelligence_api.py`
- `tests/test_evidence_repository.py`

## Demo scenario

1. Collect evidence via scheduler or upload one file.
2. Call `GET /api/evidence/repository?limit=20` — verify `evidence_id`, `sha256`, `version`, `audit_repository_synced`.
3. Open **Evidence Dashboard** — Repository Keys KPI reflects persisted keys.
4. Clear demo state only in test; in UI, use **Search** to resolve the same `evidence_id` returned by the API.

## Known Phase-1 limitations

- Operations repository is in-process; SQL persistence covers audit artifacts, not all ops workflow fields after cold restart.
- Version number on ops list stays at 1; version history lives in audit repository.
- RAG/chatbot may read canonical PostgreSQL paths separately from the authoritative reader facade.
