# ECS Data Architecture Reference

**Type:** Data architecture reference. **No code/UI/DB changes.** **Grounding:** `ecs_platform/repository/schema.sql`, `ecs_platform/repository/governance_schema.sql`, `ecs_platform/vectorstore/pgvector_store.py`. Inferred items marked **[Inferred/Target]**.

---

## Stores (physical)

| Store | Tech | Purpose |
|---|---|---|
| Evidence Repository | PostgreSQL (`ecs_repository`) | structured evidence, controls, frameworks, maps, audit |
| Vector Store | pgvector (`ecs_vectors`) | `evidence_embeddings` (768-dim) for semantic/RAG search |
| Object Store | MinIO (`ecs-evidence`) | raw evidence artifact files |
| Cache/Queue | Redis | caching/queueing |

> Demo mode runs without these stores using deterministic in-memory seeds. Schema is **idempotent + additive only** (`CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`) — safe on startup, no destructive migrations.

## Logical data model (entities & relationships)

```
frameworks 1───* application_frameworks *───1 applications
controls *───* frameworks            (control_framework_crosswalk / control_catalog)
evidence *───* controls              (evidence_control_map)
evidence *───* frameworks            (evidence_framework_map)
evidence 1───* evidence_lineage      (provenance: parent_uid, operation, actor)
evidence 1───* evidence_reviews      (status: Approved/Rejected/UnderReview/...)
evidence *───* correlation_groups    (via correlation_members)
evidence 1───1 evidence_embeddings   (by evidence_uid; chunked)
connectors 1───* sync_runs           (collection history)
applications 1───* observations      (findings)
* ─── audit_log                      (actor/action/resource + before/after, prev_hash chain)
```

## Core models

### Evidence Model
`evidence(evidence_uid UNIQUE, source_system, source_object_id, object_type, title, content, owner, url, application, collected_timestamp, content_hash, metadata JSONB)`; unique `(source_system, source_object_id, object_type)`; indexes on source/app/type. `content_hash` enables incremental reindex dedup.

### Control Model
`controls(control_id UNIQUE, name, description, domain)` + governance `control_catalog`; mapped to evidence via `evidence_control_map(confidence)`.

### Framework Model
`frameworks(code UNIQUE, name)`; `application_frameworks` (app↔framework); `control_framework_crosswalk` (control↔framework, enables cross-framework reuse).

### Observation Model
`observations(observation_id UNIQUE, application_id, title, status, owner, framework, control_id, severity, remediation_plan, comments JSONB, closed_by/at...)`. **Note (from schema comments):** durable table exists; observation workflow still uses in-memory state — **[partial wiring]**.

### Workflow Model
Evidence review workflow via `evidence_reviews(status,...)`; collection workflow via `collection_schedules` + `sync_runs`; audit trail in `audit_log` (with `before_state/after_state/request_id/prev_hash`).

### RAF Model (Risk/Assurance/Findings) **[Inferred/Composite]**
No single `raf` table; risk/assurance is composed from `observations` (findings) + correlation groups + framework coverage + exception state. Surfaced on Risk Register / Audit Prep.

### AI Model
`evidence_embeddings(chunk_id, evidence_uid, text, metadata, embedding vector(768))` in pgvector; auto-migrates dimension if embedding model changes. RAG reads embeddings + repository (see [AI Architecture](../ai-sdlc/ECS_AI_ARCHITECTURE_REFERENCE.md)).

### Connector Model
`connectors(name UNIQUE, type, enabled, base_url, last_health, last_checked)`; runtime config from `config/integrations.yaml`.

### Scheduler Model
`collection_schedules` (governance schema) + `sync_runs(connector, started_at, finished_at, ok, collected, error)` for execution history. See [Scheduler Reference](../operations/ECS_SCHEDULER_REFERENCE.md).

## Integrity & audit
- Tamper-evident audit chain via `audit_log.prev_hash`.
- Lineage + correlation provide full evidence traceability.
- Foreign keys with `ON DELETE CASCADE` on maps/members keep referential integrity.

## Cross-references
- Evidence lifecycle: [ECS_EVIDENCE_REFERENCE_GUIDE.md](../evidence-management/ECS_EVIDENCE_REFERENCE_GUIDE.md)
- Controls: [ECS_CONTROL_REFERENCE_GUIDE.md](../product/ECS_CONTROL_REFERENCE_GUIDE.md)
- Security: [ECS_SECURITY_REFERENCE.md](../production/ECS_SECURITY_REFERENCE.md)
- AI/vector: [ECS_AI_ARCHITECTURE_REFERENCE.md](../ai-sdlc/ECS_AI_ARCHITECTURE_REFERENCE.md)
