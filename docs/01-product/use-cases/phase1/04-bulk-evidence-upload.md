# Bulk Evidence Upload

## Purpose

Allow application owners and control owners to upload multiple evidence files in one action, apply framework and application tags, and register them in the same Evidence Repository used by automated collection.

## Business problem solved

Not all evidence comes from connectors. Bulk upload gives a governed path for ad hoc files (policies, scans, exports) with naming standards and immediate repository visibility.

## Phase-1 scope

- **In scope:** Multi-file HTML form upload; framework and application selection; `register_upload` per file; SHA-256 duplicate detection; audit mirror; optional SNAPSHOT custody; workflow enrollment.
- **Out of scope:** Virus scanning; OCR; automatic control inference from file content.

## High-level workflow

```
User selects files + framework + application on Upload page
  → POST /mvp/upload/bulk
  → For each file: enforce_naming → register_upload → custody → audit mirror → search index hook
  → Redirect with success notice; recent uploads listed on page
```

## Existing implementation (reuse current code)

| Area | Module / service |
|------|------------------|
| UI route | `routes_mvp.mvp_bulk_upload`, `mvp_upload_page` |
| Registration | `modules/operations/engines/evidence_repository.register_upload` |
| RBAC | `modules/shared/services/role_permissions.guard_upload` |
| Single-file API | `app/evidence_api.upload_evidence` (richer metadata) |

## Existing APIs

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/mvp/upload/bulk` | Multipart bulk upload (UI) |
| POST | `/evidence/upload` | Single upload with JSON envelope |
| GET | `/mvp/upload` | Upload page and recent list |

## Existing UI pages

| Page | Route |
|------|-------|
| Bulk Upload | `/mvp/upload` |

## Existing tests

- `tests/test_usecase_batch1_evidence_workflows.py` (`test_bulk_upload_endpoint_bridges_each_file`)
- `tests/test_evidence_authoritative_reader.py`
- `tests/test_evidence_custody.py`
- `tests/test_rbac_page_enforcement_phase2_step2c.py` (upload guard)

## Demo scenario

1. Open **Bulk Upload** (`/mvp/upload?role=owner&user=Demo`).
2. Choose **PCI DSS**, **Net Banking**, select 2–3 small PDF/TXT files.
3. Submit — notice shows count registered.
4. Open **Search** or **Evidence Dashboard** — uploaded filenames appear with `manual_upload` / upload source.
5. Re-upload identical bytes — duplicate detected, count unchanged.

## Known Phase-1 limitations

- Bulk upload does not run predefined-query or SharePoint connectors.
- Control ID must be supplied on single-file API; bulk form uses application/framework only unless extended via query params.
- Indexing depends on configured embedding provider; demo mode may skip live PGVector calls.
