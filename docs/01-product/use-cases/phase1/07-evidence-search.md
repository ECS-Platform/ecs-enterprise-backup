# Evidence Search

## Purpose

Let users discover persisted evidence by keyword, framework, application, owner, and status—and link results back to authoritative repository records for review.

## Business problem solved

Finding the right evidence across hundreds of artefacts is error-prone. Search provides a filtered, scored list aligned with repository metadata rather than ad hoc folder browsing.

## Phase-1 scope

- **In scope:** Keyword search over framework, control, filename, application; filter by framework/application/owner/status; semantic score when query provided; reuse suggestions from reuse graph; REST and UI discovery endpoints.
- **Out of scope:** Full-text OCR inside PDFs; cross-bank federated search.

## High-level workflow

```
User enters query + filters on Search page
  → search_module.search_evidences / build_search_discovery
  → Reads collect_authoritative_evidence_rows()
  → Returns ranked persisted results + reuse suggestions
  → UI renders rows with evidence_id, sha256, collection_source
```

## Existing implementation (reuse current code)

| Area | Module / service |
|------|------------------|
| Search engine | `modules/governance/engines/search_module.py` |
| Data source | `modules/shared/services/evidence_authoritative_reader.collect_authoritative_evidence_rows` |
| UI | `routes_mvp` search page, `module_capabilities._search_view` |

## Existing APIs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/evidence/search` | Query + filter API |
| GET | `/mvp/search` | Search UI |

## Existing UI pages

| Page | Route |
|------|-------|
| Evidence Search | `/mvp/search` |

## Existing tests

- `tests/test_evidence_authoritative_reader.py` (`test_search_module_reads_persisted_metadata_only`)
- `tests/test_phase1_e2e_lifecycle_validation.py`
- `tests/test_batch2_rest_ui.py`
- `tests/test_platform_ui.py`

## Demo scenario

1. Persist evidence for **PGX-001** (predefined query) and one upload.
2. Open **Search**, query `PGX-001` — result shows evidence_id and **DB Baselining** / **Net Banking**.
3. Filter by framework **PCI DSS** — SharePoint/upload items appear when tagged.
4. Call `GET /api/evidence/search?q=PGX-001` — JSON matches UI rows.

## Known Phase-1 limitations

- Search does not match raw **evidence_id** strings; use control ID, filename, or application.
- Duplicate vectors in PGVector do not create duplicate search rows (dedup at persistence).
- Changed versions follow latest authoritative row; historical version search is via audit versions API, not main search UI.
