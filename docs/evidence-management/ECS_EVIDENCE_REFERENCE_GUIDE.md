# ECS Evidence Reference Guide

**Type:** Evidence management reference. **No code/UI/DB changes.** **Grounding:** `ecs_platform/repository/schema.sql` (`evidence`, `evidence_reviews`, `evidence_control_map`, `evidence_framework_map`, `evidence_lineage`), `ecs_platform/ingestion.py`, `ecs_platform/rag.py`, `config/repository.yaml`, governance/evidence engines, evidence routes. Inferred items marked **[Inferred/Target]**.

---

## 1. Evidence lifecycle (state machine)

`Not Submitted → Collected/Submitted → Under Review → Approved` · with `→ Rejected → Resubmitted` loop · then aging `Approved → Expiring → Stale → Refresh`.

| State | Set by | Screen |
|---|---|---|
| Collected | connector/scheduler/upload | Evidence Explorer, Scheduler |
| Submitted | owner | Bulk Upload |
| Under Review | reviewer pickup | Evidence Review |
| Approved/Rejected | auditor | Evidence Review, Approval Analytics |
| Resubmitted | owner | Bulk Upload |
| Expiring/Stale | freshness engine | Evidence Health, Lifecycle |

Source: `evidence_reviews.status` (`Approved/Rejected/UnderReview/Collected/Expired`), `evidence_health_engine`, `governance_lifecycle_engine`.

## 2. Evidence repository

PostgreSQL system of record (`config/repository.yaml`, db `ecs_repository`). Core table `evidence` (uid, title, content, source_system, object_type, application, url, collected_timestamp) + maps + reviews + lineage. Object store (MinIO bucket `ecs-evidence`) holds raw artifact files. Demo mode falls back to deterministic evidence with no DB.

## 3. Evidence upload & bulk upload

- **Single/manual:** via owner workflows.
- **Bulk Upload** (`/mvp/upload`): mass import with validation, dedup, and auto-mapping to controls/frameworks. Workflow role: Evidence collection.
- **Connector ingestion:** `ecs_platform/ingestion.py` `sync_connector()` pulls from source systems.

## 4. Metadata & tagging

Evidence carries `source_system`, `object_type`, `application`, `url`, `collected_timestamp`, control/framework mappings. **Auto-tag/classification** via AI is a documented use case (UC-11) — deterministic/rule-driven today, local-LLM upgrade path (`provider.generate`). **[Inferred/Target]** for AI auto-classification at scale.

## 5. Validation, classification, approval, rejection, resubmission

- **Validation:** sufficiency scoring (deterministic `SUFFICIENCY_ENGINE`) + reviewer judgment (`/evidence/review`).
- **Classification:** type/control-area tagging (UC-11).
- **Approval/Rejection:** auditor action in Evidence Review; rejection captures a reason (consistency aided by UC-7 drafting). Writes `evidence_reviews` + `audit_log`.
- **Resubmission:** owner re-uploads; loops to Under Review.

## 6. Versioning, expiry, retention

- **Versioning:** lineage edges (`evidence_lineage`) record parent→child via operations; superseding evidence chains to its predecessor.
- **Expiry:** freshness engine flags expiring/stale by age; Lifecycle screen governs refresh.
- **Retention:** repository + object store retained per bank policy; backups per [Backup & Recovery](../operations/ECS_BACKUP_AND_RECOVERY_GUIDE.md). **[Inferred/Target]** for automated retention/archival enforcement.

## 7. Lineage & traceability

`evidence_lineage` records relationships (parent_uid → evidence via operation). RAG indexes lineage so the assistant can explain provenance. Every cited answer returns UID + source + timestamp (full traceability).

## 8. Evidence reuse

Cross-framework reuse via `control_framework_crosswalk` + `CONTROL_CROSSWALK`: one artifact satisfies multiple framework requirements (Reuse screen, `evidence_reuse()`). Core to the "collect once, reuse everywhere" thesis.

## 9. Archival

Approved/expired evidence is retained in the repository + object store; archival policy is **[Inferred/Target]** (no automated cold-archive tier shipped). Recommendation: object-store lifecycle rules on `ecs-evidence`.

## 10. Search & AI search

- **Search** (`/mvp/search`): faceted retrieval (app/framework/owner/status).
- **AI search:** semantic via pgvector (`provider.embed(query)` → `store.search`) and citation-grounded RAG (`/mvp/ai-assistant`, `/api/platform/assistant`). RBAC scope applied before retrieval.

## 11. Evidence security, encryption, storage

- **Security:** RBAC scope filter applied before any read (incl. AI); restricted role w/o assignments sees nothing.
- **Encryption:** in-transit HTTPS to sources/providers; at-rest = Postgres + MinIO storage encryption (`MINIO_SECURE=true` in prod) — **[Deploy/Infra]**.
- **Storage:** structured metadata in Postgres; raw artifacts in MinIO; embeddings in pgvector.
- **Audit:** `log_evidence_access: true` (`repository.yaml`) + `audit_log`.

---

## Cross-references
- Controls: [ECS_CONTROL_REFERENCE_GUIDE.md](../product/ECS_CONTROL_REFERENCE_GUIDE.md)
- Data model: [ECS_DATA_ARCHITECTURE_REFERENCE.md](../architecture/ECS_DATA_ARCHITECTURE_REFERENCE.md)
- Lifecycle workflows: [ECS_USER_JOURNEYS.md](../product/ECS_USER_JOURNEYS.md)
- AI search: [ECS_AI_ARCHITECTURE_REFERENCE.md](../ai-sdlc/ECS_AI_ARCHITECTURE_REFERENCE.md)
- Security: [ECS_SECURITY_REFERENCE.md](../production/ECS_SECURITY_REFERENCE.md)
