# Phase-1 Developer Manual

Implementation guides for frozen Phase-1 evidence capabilities. Each document links to existing deep references—do not duplicate full module specs here.

## Implementation guides

| Topic | Developer manual | Business use case |
|-------|------------------|-------------------|
| Automatic Evidence Collection | [01-automatic-evidence-collection-implementation.md](01-automatic-evidence-collection-implementation.md) | [../../use-cases/phase1/01-automatic-evidence-collection.md](../../../01-product/use-cases/phase1/01-automatic-evidence-collection.md) |
| Metadata Tagging | [02-metadata-tagging-implementation.md](02-metadata-tagging-implementation.md) | [../../use-cases/phase1/02-metadata-tagging.md](../../../01-product/use-cases/phase1/02-metadata-tagging.md) |
| Hash Integrity & Duplicate Detection | [03-hash-integrity-implementation.md](03-hash-integrity-implementation.md) | [../../use-cases/phase1/03-sha256-integrity-duplicate-detection.md](../../../01-product/use-cases/phase1/03-sha256-integrity-duplicate-detection.md) |
| Bulk Evidence Upload | [04-bulk-upload-implementation.md](04-bulk-upload-implementation.md) | [../../use-cases/phase1/04-bulk-evidence-upload.md](../../../01-product/use-cases/phase1/04-bulk-evidence-upload.md) |
| Evidence Dashboard | [05-evidence-dashboard-implementation.md](05-evidence-dashboard-implementation.md) | [../../use-cases/phase1/06-evidence-dashboard.md](../../../01-product/use-cases/phase1/06-evidence-dashboard.md) |

## Related Phase-1 references (moved here)

- [PREDEFINED_DATABASE_QUERY_MODULE.md](PREDEFINED_DATABASE_QUERY_MODULE.md)
- [PREDEFINED_QUERY_CATALOG.md](PREDEFINED_QUERY_CATALOG.md)
- [EVIDENCE_COLLECTION_GUIDE.md](EVIDENCE_COLLECTION_GUIDE.md)
- [EVIDENCE_VALIDATION_GUIDE.md](EVIDENCE_VALIDATION_GUIDE.md)
- [ECS_PREDEFINED_QUERY_EXECUTION_GUIDE.md](ECS_PREDEFINED_QUERY_EXECUTION_GUIDE.md)
- [scheduler/](scheduler/) — runtime flow, asset discovery, scheduler reference

## Cross-cutting

- Repository & reader: [../../use-cases/phase1/05-evidence-repository.md](../../../01-product/use-cases/phase1/05-evidence-repository.md), [../../use-cases/phase1/14-authoritative-evidence-reader.md](../../../01-product/use-cases/phase1/14-authoritative-evidence-reader.md)
- Database: [../database/](../database/)
- API supplements: [../api/](../api/)
- Testing: [../testing/](../../../04-testing/testing)
