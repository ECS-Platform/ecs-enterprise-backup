# Object Storage & Evidence Custody

## Purpose

Persist immutable evidence bytes in configured object storage (local path or MinIO in docker-compose) with SNAPSHOT custody, integrity hashes, and resolvable object keys for audit download.

## Business problem solved

Reference-only metadata is insufficient for auditors who must inspect actual artefacts. Custody ensures bytes are stored, hashed, and referenced from repository records.

## Phase-1 scope

- **In scope:** SNAPSHOT custody mode (default for scheduler/predefined queries via env); REFERENCE_ONLY for manual uploads when configured; `LocalObjectStore` and MinIO adapter; object key convention; integrity hash = stored bytes; duplicate skips second object when substantive unchanged.
- **Out of scope:** WORM legal vault; client-side encryption key management UI.

## High-level workflow

```
Evidence bytes produced (JSON/file)
  → evidence_custody.resolve_custody
  → put_immutable(object_key, bytes) when SNAPSHOT
  → content_hash recorded on artifact + metadata object_key / object_uri
  → Authoritative reader exposes object_reference for download/drill paths
```

## Existing implementation (reuse current code)

| Area | Module / service |
|------|------------------|
| Custody service | `modules/audit_intelligence/services/evidence_custody.py` |
| Object store | `ecs_platform/storage/object_store.py` (`LocalObjectStore`, MinIO) |
| Key helper | `object_key_for_evidence`, predefined-query `artifact_object_key` |
| Indexing from snapshot | `ecs_platform/evidence_indexing.resolve_indexable_text` |

## Existing APIs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/evidence/repository` | `object_uri`, `object_key`, custody_mode |
| GET | `/api/evidence/{evidence_id}/integrity` | Hash vs stored content |

## Existing UI pages

| Page | Route |
|------|-------|
| Scheduler fetched evidence view | Object key / URI in metadata |
| Evidence Dashboard / Search | object_reference in row detail |

## Existing tests

- `tests/test_evidence_custody.py`
- `tests/test_evidence_pgvector_indexing.py` (snapshot from object store)
- `tests/test_phase1_e2e_lifecycle_validation.py`
- `tests/test_evidence_repository_persistence.py`

## Demo scenario

1. Set `ECS_EVIDENCE_CUSTODY_MODE=SNAPSHOT` (demo default for collection).
2. Run **PGX-001** — note `object_key` like `predefined-query/.../*.json`.
3. Verify local object store path under configured root contains file whose SHA-256 matches repository `sha256`.
4. Duplicate run — same object reference reused, no second object for unchanged substantive content.

## Known Phase-1 limitations

- Default docker/local paths are environment-specific; not production bucket policies.
- REFERENCE_ONLY uploads keep metadata without guaranteed byte storage.
- Object store artefacts under `data/evidence-objects/` from test runs should not be committed.
