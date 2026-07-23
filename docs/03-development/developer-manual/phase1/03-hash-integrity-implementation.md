# Hash Integrity & Duplicate Detection — Phase-1 Implementation

## Purpose

Compute SHA-256 hashes, detect duplicates before new versions/embeddings, and surface integrity status.

## Business requirement

See [SHA-256 Integrity (business)](../../../01-product/use-cases/phase1/03-sha256-integrity-duplicate-detection.md).

## Functional flow

```
Build artifact bytes/JSON
  → content_sha256 = SHA-256(full artifact)     # integrity / custody
  → substantive hash = canonical_fingerprint_hash (PQ; excludes executed_at, run id)
  → find_existing_predefined_query_evidence(sha256, canonical)
  → register_upload duplicate guards (sha256 + canonical metadata)
  → audit store_evidence _find_substantive_duplicate
  → if duplicate: status DUPLICATE, embedding_skipped
```

## High-level design

Dual-hash model for predefined queries: **full artifact hash** for custody integrity; **substantive hash** for business dedup. Common controls dedup on file content SHA-256.

## Components

| Component | Path |
|-----------|------|
| Hashing | `evidence_repository.compute_hash` |
| Canonical fingerprint | `predefined_query_publisher.build_canonical_fingerprint` |
| PQ dedup | `predefined_query_publisher.find_existing_predefined_query_evidence` |
| Ops dedup | `evidence_repository.find_upload_by_sha256`, `find_upload_by_canonical_fingerprint` |
| Audit dedup | `evidence_repository._find_substantive_duplicate` |
| Index skip | `ecs_platform/evidence_indexing._evidence_version_indexed` |

## APIs

| Method | Path |
|--------|------|
| GET | `/api/evidence/{evidence_id}/integrity` |
| GET | `/api/evidence/repository` | duplicate_state in rows |

## Database objects

`content_hash` on `EvidenceArtifact`; SQL persistence indexes by `source_item_id` + hash — [../database/OBSERVATION_AND_REPOSITORY_GUIDE.md](../database/OBSERVATION_AND_REPOSITORY_GUIDE.md).

## Metadata

`content_sha256`, `substantive_content_sha256`, `canonical_fingerprint`, `duplicate_kind` (`sha256` | `canonical`).

## Scheduler interaction

Scheduler `duplicates` / `embedding_skipped` counts from PQ run results; mock evidence `duplicates_skipped`.

## Object storage

Duplicate substantive content does not create second object when publish returns early.

## Repository integration

Duplicate ops uploads return existing `evidence_id`; audit returns existing version on substantive match.

## Dashboard integration

Integrity KPI from `get_health_dashboard()`; duplicate runs do not inflate new-evidence counts.

## Search integration

No duplicate search rows when persistence dedupes correctly.

## Chatbot integration

Duplicate preset handlers read enrollment/workflow state; no duplicate citations for DUPLICATE status.

## Configuration

`ECS_PREDEFINED_QUERY_CUSTODY`, evidence period derived from `executed_at` date.

## Feature flags

None specific; dedup always on unless `allow_duplicate=True` on register_upload.

## Source files

See **Components**. Tests: `tests/test_predefined_query_evidence_dedup.py`, `tests/test_predefined_query_incremental_embedding.py`.

## Testing

- `tests/test_predefined_query_evidence_dedup.py`
- `tests/test_predefined_query_incremental_embedding.py`
- `tests/test_phase1_e2e_lifecycle_validation.py` (Scenario C)
- `tests/test_evidence_authoritative_reader.py`

## Troubleshooting

Duplicates not detected across restarts: fingerprint index in `ecs_state` not rehydrated — rerun once or rely on ops metadata scan in `find_upload_by_canonical_fingerprint`.

## Known limitations

Substantive dedup per evidence period (day). Full JSON hash changes every run if only timestamps differ; business dedup uses canonical hash.
