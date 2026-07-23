# Authoritative Evidence Reader

## Purpose

Expose a single read facade that merges operations repository rows with audit/SQL artifacts so Search, Dashboard, Chatbot presets, and REST APIs see consistent evidence identity and metadata.

## Business problem solved

Without a merge layer, consumers would see ops-only or audit-only partial records. The authoritative reader prevents drift and supports cold hydration from SQL when ops memory is cleared.

## Phase-1 scope

- **In scope:** `collect_authoritative_evidence_rows`, `get_authoritative_evidence`, `repository_stats`; merge by `evidence_id`; FCM enrichment on read path; workflow status fields; audit_repository_synced flag; used by search and chatbot deterministic queries.
- **Out of scope:** Write path (still via register_upload / store_evidence); external MDM sync.

## High-level workflow

```
Consumer requests evidence list/detail
  → collect_authoritative_evidence_rows(latest_only=True)
  → Index ops evidence_repository by evidence_id
  → Merge audit search() artifacts (hydrate SQL if configured)
  → Enrich workflow + object + FCM fields
  → Return unified dict rows
```

## Existing implementation (reuse current code)

| Area | Module / service |
|------|------------------|
| Facade | `modules/shared/services/evidence_authoritative_reader.py` |
| Ops source | `modules/operations/engines/evidence_repository.evidence_repository` |
| Audit source | `modules/audit_intelligence/engines/evidence_repository.search` + SQL hydration |
| REST | `routes_audit_intelligence.api_evidence_repository` |

## Existing APIs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/evidence/repository` | Primary authoritative listing |
| Used internally | `collect_persisted_evidence_rows()` | Chatbot + presets |

## Existing UI pages

| Page | Route |
|------|-------|
| All repository-backed UIs | Search, Dashboard, Scheduler evidence view |

## Existing tests

- `tests/test_evidence_authoritative_reader.py`
- `tests/test_phase1_e2e_lifecycle_validation.py` (Scenario F cold read)
- `tests/test_common_controls_phase1_validation.py` (`test_authoritative_reader_includes_common_control_rows`)

## Demo scenario

1. Collect predefined-query and common-control evidence.
2. `GET /api/evidence/repository` — each item has merged sha256, metadata, version.
3. In integration test pattern: clear ops list, call reader again — audit/SQL rows still visible (`test_audit_only_artifact_visible_after_ops_clear`).
4. Chatbot preset **Last 5 evidences** uses same rows as API.

## Known Phase-1 limitations

- Workflow/enrollment fields may be missing after ops clear until re-enrollment.
- Stats `indexed_for_search` reflects ops search_index flags, not live PGVector row counts.
- Canonical PostgreSQL hydration is throttled; very fresh rows may lag briefly in edge cases.
