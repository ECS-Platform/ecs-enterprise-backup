# Metadata Tagging

## Purpose

Tag every evidence artefact with business-meaningful metadata so it can be mapped to frameworks, controls, applications, environments, policies, procedures, and evidence requirements—and reused across dashboard, search, repository, and chatbot surfaces.

## Business problem solved

Untagged files cannot be tied to compliance obligations. Consistent metadata lets the same evidence support multiple frameworks, drill-down KPIs, filtered search, and deterministic chatbot answers without re-uploading.

## Phase-1 scope

- **In scope:** Framework and application tags on upload/collection; control/query identifiers; source connector and collection source; environment; FCM policy/procedure/evidence-requirement enrichment; common-control slugs and FCM cross-references for predefined queries; scheduler run ID; validation verdict (common controls); object key and custody fields.
- **Out of scope:** User-defined custom tag schemas; automated ML classification of document content.

## High-level workflow

```
Evidence collected or uploaded
  → Standardized filename (enforce_naming)
  → Metadata dict assembled at publish/register time
  → FCM enrichment (policy_refs, procedure_ids, evidence_requirement_ids)
  → Stored on operations record + audit artifact metadata
  → Exposed via authoritative reader, search, dashboard, chatbot presets
```

## Existing implementation (reuse current code)

| Area | Module / service |
|------|------------------|
| Upload metadata | `modules/operations/engines/evidence_repository.register_upload` |
| FCM enrichment | `modules/shared/services/evidence_authoritative_reader._enrich_fcm_mappings` |
| Predefined query tags | `predefined_query_publisher._enrich_predefined_query_metadata` |
| Common control tags | `common_controls_collector.collect_common_control_folder` |
| Naming convention | `evidence_repository.enforce_naming` |

## Existing APIs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/evidence/naming-preview` | Preview standardized name |
| POST | `/api/evidence/validate-metadata` | Validate metadata payload |
| GET | `/api/evidence/repository` | List persisted evidence with metadata |
| GET | `/api/predefined-queries/{control_id}/mappings` | Query → common control → FCM refs |
| GET | `/api/common-controls/{slug}` | Common control metadata and mappings |

## Existing UI pages

| Page | Route |
|------|-------|
| Bulk upload (tags via form) | `/mvp/upload` |
| Evidence Dashboard | `/mvp/evidence-dashboard` |
| Search (framework/application filters) | `/mvp/search` |
| Framework Control Master | `/mvp/framework-control-master` |

## Existing tests

- `tests/test_evidence_authoritative_reader.py` (`test_fcm_mapping_enriched_on_upload`)
- `tests/test_predefined_query_phase1_validation.py`
- `tests/test_common_controls_phase1_validation.py`
- `tests/test_evidence_repository_persistence.py`
- `tests/test_technology_control_mapping.py`

## Demo scenario

1. Run predefined query **PGX-001** or collect a common control folder.
2. Call `GET /api/evidence/repository?limit=10` — inspect `metadata` for `query_id`, `common_control_slugs`, `fcm_reference_count`, `policy_refs`.
3. Open **Search**, filter by **Net Banking** — evidence appears with application and framework tags.
4. Open **Framework Control Master** drill-down for **PCI-C-01** — policy and evidence requirement IDs align with enriched metadata.

## Known Phase-1 limitations

- FCM enrichment is best-effort from file catalogue; not all controls have automatic metadata match.
- Predefined-query FCM linkage is indirect (query → common control → domain-based FCM refs).
- Metadata on operations rows may be absent after cold read if only audit SQL artifact is hydrated.
