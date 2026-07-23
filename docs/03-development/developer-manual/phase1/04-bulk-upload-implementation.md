# Bulk Evidence Upload — Phase-1 Implementation

## Purpose

Register multiple user-uploaded files into the same evidence pipeline used by automated collection.

## Business requirement

See [Bulk Evidence Upload (business)](../../../01-product/use-cases/phase1/04-bulk-evidence-upload.md).

## Functional flow

```
GET /mvp/upload → form
POST /mvp/upload/bulk (multipart files[], framework, application)
  → guard_upload (RBAC)
  → for each file: register_upload → custody → mirror → index hook
  → redirect with notice; recent uploads on page
```

## High-level design

Thin UI wrapper over `register_upload`; no separate bulk repository. Each file is an independent evidence row.

## Components

| Component | Path |
|-----------|------|
| Routes | `modules/shared/routes/routes_mvp.py` (`mvp_bulk_upload`, `mvp_upload_page`) |
| Registration | `modules/operations/engines/evidence_repository.register_upload` |
| RBAC | `modules/shared/services/role_permissions.guard_upload` |
| Single-file API | `app/evidence_api.upload_evidence` |

## APIs

| Method | Path |
|--------|------|
| POST | `/mvp/upload/bulk` |
| POST | `/evidence/upload` |
| GET | `/mvp/upload` |

## Database objects

Same as audit evidence persistence path — [../database/AUDIT_INTELLIGENCE_PERSISTENCE_GUIDE.md](../database/AUDIT_INTELLIGENCE_PERSISTENCE_GUIDE.md).

## Metadata

`framework_tags`, `application_tags`, `uploaded_by`, `original_filename`; FCM enrichment on register when control known.

## Scheduler interaction

None (manual path). Uploaded evidence may appear in later scheduler dedup if same bytes collected elsewhere.

## Object storage

Custody mode from `ECS_EVIDENCE_CUSTODY_MODE` (often REFERENCE_ONLY for manual uploads unless SNAPSHOT forced).

## Repository integration

Standard `register_upload` → audit mirror → authoritative reader.

## Dashboard integration

Uploads increment repository KPIs and appear in search/discovery.

## Search integration

Filename and framework searchable via `search_evidences`.

## Chatbot integration

Included in `latest_5_evidences` and deterministic queries over `collect_persisted_evidence_rows()`.

## Configuration

RBAC roles in persona matrices — [../ECS_PERSONA_CONFIGURATION_MATRIX.md](../ECS_PERSONA_CONFIGURATION_MATRIX.md).

## Feature flags

`ECS_AUTH_ENABLED`, upload guards per role.

## Source files

Template: `templates/mvp_bulk_upload.html`. Engine: `evidence_repository.py`.

## Testing

- `tests/test_usecase_batch1_evidence_workflows.py`
- `tests/test_evidence_custody.py`
- `tests/test_rbac_page_enforcement_phase2_step2c.py`

## Troubleshooting

403 on upload: `guard_upload` denied role. DUPLICATE on re-upload: expected for identical bytes.

## Known limitations

Bulk form does not collect control ID (single-file API does). No virus scan.
