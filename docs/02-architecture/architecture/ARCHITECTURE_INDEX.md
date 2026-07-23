# ECS Architecture Index

**Purpose:** Single entry point to every ECS (Evidence Collection System)
architecture document — with purpose, sourcing, and cross references. Generated
during the final enterprise consolidation pass (pre-UAT). This index adds no new
architecture; it maps what already exists.

> Note: on case-insensitive filesystems `docs/ARCHITECTURE/` resolves to the
> existing `docs/02-architecture/architecture/` directory; this index lives there.

---

## 1. Architecture documents

### Phase-1 architecture views (navigators)

| Document | Purpose | Sourced from | Status |
|----------|---------|--------------|--------|
| [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) | System boundary, subsystems, context — links C4 / overview / review | Existing architecture docs + `app/`, `modules/` | ✅ Current |
| [FUNCTIONAL_ARCHITECTURE.md](FUNCTIONAL_ARCHITECTURE.md) | Business capabilities, personas, value chain | HLD §1, Business Process Model, use-case catalog | ✅ Current |
| [LOGICAL_ARCHITECTURE.md](LOGICAL_ARCHITECTURE.md) | Logical component relationships (UI → API → collection → stores → RAG) | Engines/services + data/AI/scheduler/connector docs | ✅ Current |
| [TECHNICAL_ARCHITECTURE.md](TECHNICAL_ARCHITECTURE.md) | Runtime stack, stores, AI tech, deployment summary | Deployment + data + AI architecture docs | ✅ Current |
| [ecs_deployment_architecture.md](ecs_deployment_architecture.md) | **Deployment Architecture** — Compose topology, stores, host LLM, profiles, config boundaries | `Dockerfile`, `docker-compose.yml`, `config/` | ✅ Current |
| [INTEGRATION_ARCHITECTURE.md](INTEGRATION_ARCHITECTURE.md) | **Integration Architecture** — boundaries, two planes, scheduler/PQE, evidence handoff | Master Integration Matrix + adapters guide | ✅ Current |
| [CONNECTOR_ARCHITECTURE.md](CONNECTOR_ARCHITECTURE.md) | **Connector Architecture** — stacks, contracts, lifecycle, registration | Adapters / factory / PQE / workbench docs | ✅ Current |
| [DATA_FLOW_ARCHITECTURE.md](DATA_FLOW_ARCHITECTURE.md) | **Data Flow Architecture** — initiation → collect → register → persistence planes → consumption | `register_upload`, custody, Matrix, evidence guides | ✅ Current |
| [EVIDENCE_LIFECYCLE.md](EVIDENCE_LIFECYCLE.md) | **Evidence Lifecycle** — collection→custody→index stages + review axis | Evidence guides, state matrix, data flow | ✅ Current |
| [SCHEDULER_ARCHITECTURE.md](SCHEDULER_ARCHITECTURE.md) | **Scheduler Architecture** — planner + collection runner, accounting, boundaries | `asset_scheduler`, `scheduler_module`, scheduler runtime docs | ✅ Current |

### Core design & topology

| Document | Purpose | Sourced from | Status |
|----------|---------|--------------|--------|
| [SOLUTION_ARCHITECTURE.md](SOLUTION_ARCHITECTURE.md) | Solution layer map (functional/runtime/integration/data/AI) | Per-layer authoritative docs | ✅ Current |
| [HIGH_LEVEL_DESIGN.md](HIGH_LEVEL_DESIGN.md) | C4 Context / Container / Component | Complements `ecs_hld.md` | ✅ Current |
| [LOW_LEVEL_DESIGN.md](LOW_LEVEL_DESIGN.md) | LLD navigator (services → deep docs) | `ecs_lld.md` + sequences | ✅ Current |
| [ecs_enterprise_architecture_review.md](ecs_enterprise_architecture_review.md) | Current implemented enterprise architecture (modules, boundaries, data flow) | Live code under `modules/`, `app/`, `ecs_platform/` | ✅ Current |
| [ECS_DATA_ARCHITECTURE_REFERENCE.md](ECS_DATA_ARCHITECTURE_REFERENCE.md) | Data model / persistence: repository + governance schema + vector store + Phase 1 FCM file catalogue | `ecs_platform/repository/schema.sql`, `governance_schema.sql`, `pgvector_store.py`, `config/framework_control_master/` | ✅ Current |
| [ecs_hld.md](ecs_hld.md) | High-Level Design — components, flows, assumptions/recommendations | Repo-wide | ✅ Current |
| [ecs_lld.md](ecs_lld.md) | Low-Level Design — per-module components, functions, data | Repo-wide | ✅ Current |
| [../diagrams/ecs_sequence_diagrams.md](../diagrams/ecs_sequence_diagrams.md) | System sequence diagrams (Mermaid) | Routes, engines, frontend drilldown | ✅ Current |
| [../diagrams/ecs_er_diagrams.md](../diagrams/ecs_er_diagrams.md) | Entity-relationship diagrams (Mermaid) | Dataclasses / Pydantic models / schema | ✅ Current |

### Closely-related design references (not in `architecture/` but architectural)

| Document | Purpose |
|----------|---------|
| [../DEVELOPER/AUDIT_INTELLIGENCE_PERSISTENCE_GUIDE.md](../../03-development/audit-intelligence/AUDIT_INTELLIGENCE_PERSISTENCE_GUIDE.md) | Persistence foundation (in-memory + SQL/Postgres skeleton) design |
| [../DEVELOPER/UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md](../../03-development/developer-manual/phase1/scheduler/UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md) | Asset-driven scheduler + evidence-routing design |
| [../DEVELOPER/MS_GRAPH_CONNECTOR_GUIDE.md](../../03-development/developer-manual/connectors/MS_GRAPH_CONNECTOR_GUIDE.md) | Microsoft Graph connector foundation (SharePoint/Teams/Outlook) |
| [../DEVELOPER/CONNECTOR_DEEPENING_GUIDE.md](../../03-development/developer-manual/connectors/CONNECTOR_DEEPENING_GUIDE.md) | Shared enterprise connector base (`_base.py`) design |
| [../use-cases/Phase-1/Framework Control Master and Evidence Dashboard.md](../../01-product/use-cases/Phase-1/Framework%20Control%20Master%20and%20Evidence%20Dashboard.md) | Phase 1 FCM catalogue, repository/service layer, Evidence Dashboard Framework Progress integration |
| [../api/framework_control_master.md](../../03-development/developer-manual/api/framework_control_master.md) | FCM + Evidence Dashboard progress API endpoints |
| [../DB_SCHEMA_AUDIT_INTELLIGENCE.sql](../DB_SCHEMA_AUDIT_INTELLIGENCE.sql) | Canonical audit-intelligence DB schema |
| [../DEPLOYMENT/](../DEPLOYMENT) & [`deploy/README.md`](../../deploy/README.md) | Deployment pack (compose/nginx/systemd/k8s examples) |

---

## 2. Architecture at a glance (verified this pass)

```
Assets → Fingerprinting → Technology Rules → Predefined Query Engine
                                   │                         │
                                   ▼                         ▼
                          Asset-driven Scheduler      Query connectors (Matrix §2)
                                   │                   Enterprise adapters (Matrix §1)
                                   ▼                         │
                          Evidence Planner ─────────────────┘
                                   ▼
     Evidence Collection → Validation → Observations → Evidence Repository/Packs → Executive Dashboard
```

Inventory status (✅/⚙/🔵/🟡):
[ECS_MASTER_INTEGRATION_MATRIX.md](../../03-development/developer-manual/connectors/ECS_MASTER_INTEGRATION_MATRIX.md).

- **Runtime:** FastAPI (`app/main.py`), Jinja UI, Python engines under `modules/`.
- **Persistence:** in-memory by default; DB-ready SQL/Postgres foundation
  (`modules/audit_intelligence/services/persistence.py` + `sql_persistence.py`).
- **Deployment:** container (`Dockerfile`, `uvicorn app.main:app`), Compose default
  plane (ecs + postgres-demo + postgres + pgvector + redis + minio) plus
  **profile-gated** optional targets; see
  [ecs_deployment_architecture.md](ecs_deployment_architecture.md). Non-production
  `deploy/` example pack also exists.

---

## 3. Layer → primary code map

| Layer | Code |
|-------|------|
| Predefined Query Engine | `modules/operations/engines/predefined_queries_engine.py`, `supplementary_query_catalog.py` |
| Query connectors | `modules/operations/engines/*_connector.py` (inventory: Master Integration Matrix §2) |
| Enterprise integrations | `modules/operations/integrations/*` (`_base.py`, `ms_graph_base.py`) (inventory: Matrix §1 + Adapters Guide) |
| Audit Intelligence | `modules/audit_intelligence/engines/*`, `services/*` |
| Fingerprinting / rules | `modules/audit_intelligence/engines/technology_fingerprint.py`, `predefined_queries_engine.TECHNOLOGY_RULES` |
| Scheduler | `modules/audit_intelligence/services/asset_scheduler.py` |
| Persistence | `modules/audit_intelligence/services/persistence.py`, `sql_persistence.py` |
| REST + UI routes | `modules/**/routes/*`, `app/main.py` |

See [ARCHITECTURE_INDEX](ARCHITECTURE_INDEX.md) siblings above for the full text of
each document. For the doc-wide inventory see
[../DOCUMENTATION_INVENTORY.md](../DOCUMENTATION_INVENTORY.md).

---

## 4. Connector & runtime reference (API + sequence diagrams)

Architecture navigators first:

- [Integration Architecture](INTEGRATION_ARCHITECTURE.md)
- [Connector Architecture](CONNECTOR_ARCHITECTURE.md)
- [Deployment Architecture](ecs_deployment_architecture.md)
- [Data Flow Architecture](DATA_FLOW_ARCHITECTURE.md)
- [Evidence Lifecycle](EVIDENCE_LIFECYCLE.md)
- [Scheduler Architecture](SCHEDULER_ARCHITECTURE.md)
- [Master Integration Matrix](../../03-development/developer-manual/connectors/ECS_MASTER_INTEGRATION_MATRIX.md) (inventory SoT)

Repository-grounded developer references:

- [Microsoft Graph connector API reference](../../03-development/developer-manual/connectors/microsoft_graph_connector_api_reference.md)
- [Enterprise connector API reference](../../03-development/developer-manual/connectors/enterprise_connector_api_reference.md)
- [Connector Test Workbench design & runtime](../../03-development/developer-manual/connectors/connector_test_workbench_design.md)
- [Scheduler runtime flow](../../03-development/developer-manual/phase1/scheduler/scheduler_runtime_flow.md)
- [Test Workbench vs. Scheduler](../../03-development/developer-manual/phase1/scheduler/test_workbench_vs_scheduler.md)
- [Runtime call graph & sequence diagrams](../../03-development/developer-manual/phase1/scheduler/runtime_call_graph.md)
- [Evidence reuse & observation lifecycle (functional design)](../../03-development/evidence-management/evidence_reuse_lifecycle_functional_design.md)

