# Evidence Versioning

## Purpose

Track substantive changes to evidence over time so auditors can see historical states while preventing unnecessary new versions when only collection metadata (timestamps, run IDs) changes.

## Business problem solved

Controls must be proven at a point in time, but re-running collection daily should not create spurious versions. Versioning balances audit history with idempotent collection.

## Phase-1 scope

- **In scope:** Automatic version increment per evidence key in audit repository; monotonic version numbers; content-hash and substantive-hash dedup; version timeline; latest-only search default; changed predefined-query result → new version; common-control JSON change → new version.
- **Out of scope:** Legal hold branching; signed version manifests.

## High-level workflow

```
store_evidence / register_upload (new substantive content)
  → _next_version(evidence_key)
  → Append EvidenceArtifact version with content_hash
  → Persist to SQL (when enabled) + timeline event
  → Duplicate substantive match → return existing version (no increment)
  → PGVector indexes new version chunks only when content changed
```

## Existing implementation (reuse current code)

| Area | Module / service |
|------|------------------|
| Version store | `modules/audit_intelligence/engines/evidence_repository.py` |
| Dedup | `_find_in_memory_duplicate`, `_find_substantive_duplicate` |
| Predefined query versioning | `predefined_query_publisher` + stable `source_item_id` per period |
| Read APIs | `audit_repository_service.evidence_versions`, `evidence_timeline` |

## Existing APIs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/audit/evidence/{evidence_key}/versions` | All versions for a key |
| GET | `/api/evidence/repository` | Includes merged version field |

## Existing UI pages

| Page | Route |
|------|-------|
| Evidence Dashboard / Search | Shows latest version; drill via audit APIs |
| Audit intelligence surfaces | Version history where exposed |

## Existing tests

- `tests/test_evidence_authoritative_reader.py` (`test_version_increments_in_audit_repository`)
- `tests/test_predefined_query_phase1_validation.py` (`test_changed_artifact_content_creates_new_audit_version`)
- `tests/test_common_controls_phase1_validation.py` (`test_changed_evidence_creates_new_version`)
- `tests/test_phase1_e2e_lifecycle_validation.py` (Scenario D)

## Demo scenario

1. Collect **PGX-001** — audit version **1**.
2. Change substantive result, collect again — version **2**, distinct `content_hash`.
3. Recollect identical result same day — **DUPLICATE**, still version **1** only in history.
4. Modify `CommonControls/backup-restore/evidence.json` RPO value — new common-control version.

## Known Phase-1 limitations

- Operations repository row shows `version: 1`; authoritative version is on audit artifact.
- MAX_VERSIONS_PER_KEY trims very old in-memory versions in demo.
- Cross-day identical logical results create new period versions by design.
