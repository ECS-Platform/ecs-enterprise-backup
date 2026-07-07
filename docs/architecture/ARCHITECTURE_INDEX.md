# ECS Architecture Index

**Purpose:** Single entry point to every ECS (Evidence Collection System)
architecture document — with purpose, sourcing, and cross references. Generated
during the final enterprise consolidation pass (pre-UAT). This index adds no new
architecture; it maps what already exists.

> Note: on case-insensitive filesystems `docs/ARCHITECTURE/` resolves to the
> existing `docs/architecture/` directory; this index lives there.

---

## 1. Architecture documents

| Document | Purpose | Sourced from | Status |
|----------|---------|--------------|--------|
| [ecs_enterprise_architecture_review.md](ecs_enterprise_architecture_review.md) | Current implemented enterprise architecture (modules, boundaries, data flow) | Live code under `modules/`, `app/`, `ecs_platform/` | ✅ Current |
| [ECS_DATA_ARCHITECTURE_REFERENCE.md](ECS_DATA_ARCHITECTURE_REFERENCE.md) | Data model / persistence: repository + governance schema + vector store | `ecs_platform/repository/schema.sql`, `governance_schema.sql`, `pgvector_store.py` | ✅ Current |
| [ecs_deployment_architecture.md](ecs_deployment_architecture.md) | Deployment topology (containers, ports, profiles, config) | `Dockerfile`, `docker-compose.yml`, `config/` | ✅ Current |
| [../hld/ecs_hld.md](ecs_hld.md) | High-Level Design — components, flows, assumptions/recommendations | Repo-wide | ✅ Current |
| [../lld/ecs_lld.md](ecs_lld.md) | Low-Level Design — per-module components, functions, data | Repo-wide | ✅ Current |
| [../diagrams/ecs_sequence_diagrams.md](../diagrams/ecs_sequence_diagrams.md) | System sequence diagrams (Mermaid) | Routes, engines, frontend drilldown | ✅ Current |
| [../diagrams/ecs_er_diagrams.md](../diagrams/ecs_er_diagrams.md) | Entity-relationship diagrams (Mermaid) | Dataclasses / Pydantic models / schema | ✅ Current |

### Closely-related design references (not in `architecture/` but architectural)

| Document | Purpose |
|----------|---------|
| [../DEVELOPER/AUDIT_INTELLIGENCE_PERSISTENCE_GUIDE.md](../audit-intelligence/AUDIT_INTELLIGENCE_PERSISTENCE_GUIDE.md) | Persistence foundation (in-memory + SQL/Postgres skeleton) design |
| [../DEVELOPER/UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md](../scheduler/UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md) | Asset-driven scheduler + evidence-routing design |
| [../DEVELOPER/MS_GRAPH_CONNECTOR_GUIDE.md](../graph-api/MS_GRAPH_CONNECTOR_GUIDE.md) | Microsoft Graph connector foundation (SharePoint/Teams/Outlook) |
| [../DEVELOPER/CONNECTOR_DEEPENING_GUIDE.md](../connectors/CONNECTOR_DEEPENING_GUIDE.md) | Shared enterprise connector base (`_base.py`) design |
| [../DB_SCHEMA_AUDIT_INTELLIGENCE.sql](../DB_SCHEMA_AUDIT_INTELLIGENCE.sql) | Canonical audit-intelligence DB schema |
| [../DEPLOYMENT/](../DEPLOYMENT) & [`deploy/README.md`](../../deploy/README.md) | Deployment pack (compose/nginx/systemd/k8s examples) |

---

## 2. Architecture at a glance (verified this pass)

```
Assets → Fingerprinting → Technology Rules → Predefined Query Engine (187 controls / 21 techs)
                                   │                         │
                                   ▼                         ▼
                          Asset-driven Scheduler      Connectors (13 query connectors)
                                   │                   Integrations (11 enterprise adapters)
                                   ▼                         │
                          Evidence Planner ─────────────────┘
                                   ▼
     Evidence Collection → Validation → Observations → Evidence Repository/Packs → Executive Dashboard
```

- **Runtime:** FastAPI (`app/main.py`), Jinja UI, Python engines under `modules/`.
- **Persistence:** in-memory by default; DB-ready SQL/Postgres foundation
  (`modules/audit_intelligence/services/persistence.py` + `sql_persistence.py`).
- **Deployment:** container (`Dockerfile`, `uvicorn app.main:app`), 21 Compose
  services (opt-in profiles), plus a non-production `deploy/` example pack.

---

## 3. Layer → primary code map

| Layer | Code |
|-------|------|
| Predefined Query Engine | `modules/operations/engines/predefined_queries_engine.py`, `supplementary_query_catalog.py` |
| Query connectors (13) | `modules/operations/engines/*_connector.py` |
| Enterprise integrations (11) | `modules/operations/integrations/*` (`_base.py`, `ms_graph_base.py`) |
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

Repository-grounded developer references for the enterprise connectors, Microsoft
Graph integration, the Connector Test Workbench, and the scheduler runtime:

- [Microsoft Graph connector API reference](../graph-api/microsoft_graph_connector_api_reference.md)
- [Enterprise connector API reference (11 connectors)](../connectors/enterprise_connector_api_reference.md)
- [Connector Test Workbench design & runtime](../connectors/connector_test_workbench_design.md)
- [Scheduler runtime flow](../scheduler/scheduler_runtime_flow.md)
- [Test Workbench vs. Scheduler](../scheduler/test_workbench_vs_scheduler.md)
- [Runtime call graph & sequence diagrams](../scheduler/runtime_call_graph.md)
- [Evidence reuse & observation lifecycle (functional design)](../evidence-management/evidence_reuse_lifecycle_functional_design.md)
