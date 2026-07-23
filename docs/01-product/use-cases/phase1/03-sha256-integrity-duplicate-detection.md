# SHA-256 Hash Integrity & Duplicate Detection

## Purpose

Guarantee evidence integrity and prevent duplicate repository noise by hashing artefact content, detecting logical duplicates when only run timestamps differ, and supporting version decisions when substantive content changes.

## Business problem solved

Auditors require proof that evidence was not tampered with and that repeated scheduler runs do not inflate evidence counts. Hashing and duplicate detection provide custody integrity and idempotent collection.

## Phase-1 scope

- **In scope:** Full artefact SHA-256 (`content_sha256` / record `sha256`); substantive-content hash for predefined queries (`substantive_content_sha256` / `canonical_fingerprint` excluding volatile fields); duplicate status on identical hash or canonical match; integrity status on operations records; audit repository dedup by `source_item_id` + content hash or substantive hash.
- **Out of scope:** Blockchain anchoring; cross-tenant hash federation.

## High-level workflow

```
Generate evidence JSON/bytes
  → Compute full artifact SHA-256 (integrity / custody)
  → Compute substantive canonical fingerprint (predefined queries)
  → find_existing (sha256 then canonical)
  → If duplicate: return DUPLICATE, skip new version, ops row, embedding
  → If changed substantive: new audit version + new ops row when policy requires
  → Store hash in metadata; integrity_check on register
```

## Existing implementation (reuse current code)

| Area | Module / service |
|------|------------------|
| Hashing | `evidence_repository.compute_hash`, `predefined_query_publisher.canonical_fingerprint_hash` |
| Duplicate detection | `predefined_query_publisher.find_existing_predefined_query_evidence`, `register_upload` (sha256 + canonical) |
| Audit dedup | `audit_intelligence/engines/evidence_repository._find_substantive_duplicate` |
| Integrity display | `evidence_repository.integrity_check`, `/api/evidence/{evidence_id}/integrity` |

## Existing APIs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/evidence/{evidence_id}/integrity` | Integrity check result |
| GET | `/api/evidence/repository` | Includes `sha256`, duplicate state |
| POST | `/mvp/upload/bulk` | Returns DUPLICATE status on identical bytes |

## Existing UI pages

| Page | Route |
|------|-------|
| Evidence Health / integrity KPIs | `/mvp/evidence-health` |
| Scheduler summary (duplicates skipped) | `/mvp/scheduler` |
| Evidence Dashboard integrity KPI | `/mvp/evidence-dashboard` |

## Existing tests

- `tests/test_predefined_query_evidence_dedup.py`
- `tests/test_predefined_query_incremental_embedding.py`
- `tests/test_evidence_authoritative_reader.py`
- `tests/test_common_controls_phase1_validation.py` (identical recollect)
- `tests/test_phase1_e2e_lifecycle_validation.py` (Scenario C)

## Demo scenario

1. Run **PGX-001** twice on the same day with the same query result.
2. Second run returns **DUPLICATE** — no new evidence version, no extra embedding.
3. Change query result (e.g. SSL `off` vs `on`) — new version and hash appear in repository.
4. Upload the same file twice via **Bulk Upload** — second upload status is DUPLICATE.

## Known Phase-1 limitations

- Canonical/substantive dedup for predefined queries is scoped to **evidence period (calendar day)**.
- In-memory fingerprint indexes are not rehydrated from PostgreSQL on cold restart.
- Full artifact hash includes volatile scheduler fields; business dedup relies on substantive hash for predefined queries.
