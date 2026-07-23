# Metadata Tagging — Phase-1 Implementation

## Purpose

Attach consistent, framework-aware metadata to every evidence artefact at collection or upload time.

## Business requirement

See [Metadata Tagging (business)](../../../01-product/use-cases/phase1/02-metadata-tagging.md).

## Functional flow

```
register_upload / publish_predefined_query_evidence / common_controls_collector
  → metadata dict (source, control, application, framework, FCM refs)
  → enforce_naming(filename, framework, application)
  → _enrich_fcm_mappings (authoritative reader / register path)
  → persisted on ops record + audit EvidenceArtifact.metadata
```

## High-level design

Metadata is a flat dict on the operations record, mirrored to audit artifact tuple metadata. FCM enrichment is best-effort from `config/framework_control_master/` without duplicating catalogue rows.

## Components

| Component | Path |
|-----------|------|
| FCM enrichment | `modules/shared/services/evidence_authoritative_reader._enrich_fcm_mappings` |
| PQ enrichment | `modules/operations/engines/predefined_query_publisher._enrich_predefined_query_metadata` |
| Common control tags | `modules/operations/engines/common_controls_collector` |
| Technology mapping | `modules/audit_intelligence/engines/technology_control_mapping.py` |
| Naming | `modules/operations/engines/evidence_repository.enforce_naming` |

## APIs

| Method | Path |
|--------|------|
| GET | `/api/evidence/naming-preview` |
| POST | `/api/evidence/validate-metadata` |
| GET | `/api/predefined-queries/{id}/mappings` |
| GET | `/api/common-controls/{slug}` |

## Database objects

Metadata stored as JSON-compatible fields on SQL evidence version rows when persistence enabled — see [../database/AUDIT_INTELLIGENCE_PERSISTENCE_GUIDE.md](../database/AUDIT_INTELLIGENCE_PERSISTENCE_GUIDE.md).

## Metadata

Key fields: `framework_tags`, `application_tags`, `control`, `query_id`, `common_control_slug`, `policy_refs`, `procedure_ids`, `evidence_requirement_ids`, `framework_independent`, `collection_source`, `scheduler_run_id`, `substantive_content_sha256`, `validation_verdict`.

## Scheduler interaction

Scheduler run ID written in `collect_scheduled_predefined_queries` loop and common-control `collect_common_control_folder`.

## Object storage

`object_key`, `object_uri`, `custody_mode` on record; `content_sha256` in metadata.

## Repository integration

Authoritative reader merges ops + audit metadata: `collect_authoritative_evidence_rows()`.

## Dashboard integration

FCM progress uses enrollment + metadata; common-controls summary reads `collection_source == CommonControls`.

## Search integration

Filters on `framework`, `application`, `control` from authoritative rows.

## Chatbot integration

`collect_persisted_evidence_rows()` exposes `source_type`, `control_id`, `framework` for presets.

## Configuration

Framework catalogue: `config/framework_control_master/`. Common controls: `CommonControls/*/manifest.json`.

## Feature flags

No dedicated metadata flag; collection flags gate whether metadata is produced.

## Source files

See **Components**. Guide: [../TECHNOLOGY_MAPPING_GUIDE.md](../TECHNOLOGY_MAPPING_GUIDE.md).

## Testing

- `tests/test_evidence_authoritative_reader.py` (FCM enrichment)
- `tests/test_predefined_query_phase1_validation.py`
- `tests/test_common_controls_phase1_validation.py`

## Troubleshooting

Missing FCM refs: control ID not in framework YAML or no match in `_enrich_fcm_mappings`. Missing common-control slugs: query ID not in `common_controls_catalog`.

## Known limitations

PQ → FCM linkage indirect via common controls. Ops metadata lost on cold read if only SQL artifact hydrated.
