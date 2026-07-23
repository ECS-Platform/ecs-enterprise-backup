# ECS Evidence Reference Guide

**Type:** Evidence management reference. **No code/UI/DB changes.** **Grounding:** `ecs_platform/repository/schema.sql` (`evidence`, `evidence_reviews`, `evidence_control_map`, `evidence_framework_map`, `evidence_lineage`), `ecs_platform/ingestion.py`, `ecs_platform/rag.py`, `config/repository.yaml`, governance/evidence engines, evidence routes. Inferred items marked **[Inferred/Target]**.

> **Phase-1 architecture entry points** (persistence planes, custody, multi-store
> lifecycle — use these when docs conflict on “what got written”):
> [`DATA_FLOW_ARCHITECTURE.md`](../../02-architecture/architecture/DATA_FLOW_ARCHITECTURE.md) ·
> [`EVIDENCE_LIFECYCLE.md`](../../02-architecture/architecture/EVIDENCE_LIFECYCLE.md).

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

Engine label mapping for submit/approve/reject:
[`ECS_STATE_TRANSITION_MATRIX.md`](../../02-architecture/architecture/ECS_STATE_TRANSITION_MATRIX.md).

## 2. Evidence repository

**Multiple stores coexist in Phase 1** (do not treat this section as “Postgres only”):

| Store | Role |
|---|---|
| Operations + AI in-process repositories | Default working enrollment / versioned artifacts for demo & many runtime paths |
| PostgreSQL (`ecs_repository`) | Durable schema / best-effort bridge from `register_upload` (`postgresql_persisted`) and platform repository APIs |
| MinIO (`ecs-evidence`) | Raw artifact **bytes** when SNAPSHOT custody stores successfully |
| Demo `ecs_state` | Deterministic showcase workflow when durable deps are absent |

Object store holds raw artifact files **when custody SNAPSHOT succeeds**. Demo mode can run with deterministic evidence and **no** DB. Details:
[`../architecture/DATA_FLOW_ARCHITECTURE.md`](../architecture/DATA_FLOW_ARCHITECTURE.md) §6.

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
- Phase-1 data flow / lifecycle architecture: [DATA_FLOW_ARCHITECTURE.md](../../02-architecture/architecture/DATA_FLOW_ARCHITECTURE.md) · [EVIDENCE_LIFECYCLE.md](../../02-architecture/architecture/EVIDENCE_LIFECYCLE.md)
- Controls: [ECS_CONTROL_REFERENCE_GUIDE.md](../../01-product/product/ECS_CONTROL_REFERENCE_GUIDE.md)
- Data model: [ECS_DATA_ARCHITECTURE_REFERENCE.md](../../02-architecture/architecture/ECS_DATA_ARCHITECTURE_REFERENCE.md)
- Lifecycle workflows: [ECS_USER_JOURNEYS.md](../../01-product/product/ECS_USER_JOURNEYS.md)
- AI search: [ECS_AI_ARCHITECTURE_REFERENCE.md](../ai-sdlc/ECS_AI_ARCHITECTURE_REFERENCE.md)
- Security: [ECS_SECURITY_REFERENCE.md](../production/ECS_SECURITY_REFERENCE.md)
