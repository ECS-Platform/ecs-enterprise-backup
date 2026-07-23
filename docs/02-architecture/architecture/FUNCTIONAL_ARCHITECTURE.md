# ECS Functional Architecture (Phase 1)

Single entry point for the **functional architecture** view of the frozen Phase-1
implementation. This navigator maps business capabilities to modules and
workflows already documented elsewhere — it does not duplicate process detail.

> **Reuse note.** Capability list and entry points:
> [`ecs_hld.md`](ecs_hld.md) §1. Business process / BPMN-style model:
> [`ECS_BUSINESS_PROCESS_MODEL.md`](ECS_BUSINESS_PROCESS_MODEL.md). Use cases:
> [`../product/ECS_MASTER_USE_CASE_CATALOG.md`](../product/ECS_MASTER_USE_CASE_CATALOG.md).
> Workflow orchestration:
> [`ECS_WORKFLOW_ORCHESTRATION_GUIDE.md`](ECS_WORKFLOW_ORCHESTRATION_GUIDE.md).

---

## 1. Functional capability map

| Capability | What users get (Phase 1) | Primary module(s) | Deep dive |
|------------|--------------------------|-------------------|-----------|
| Evidence collection & upload | Manual upload, connector sync, scheduled collection | `operations`, `audit_intelligence` | [`../evidence-management/EVIDENCE_COLLECTION_GUIDE.md`](../evidence-management/EVIDENCE_COLLECTION_GUIDE.md) |
| Predefined query automation | Control-linked queries against tech targets | `operations` | [`../operations/ECS_PREDEFINED_QUERY_ARCHITECTURE.md`](../operations/ECS_PREDEFINED_QUERY_ARCHITECTURE.md) |
| Evidence repository & versioning | Store, search, version, integrity | `operations`, `ecs_platform/repository` | [`../evidence-management/OBSERVATION_AND_REPOSITORY_GUIDE.md`](../evidence-management/OBSERVATION_AND_REPOSITORY_GUIDE.md) |
| Evidence workflow | Submit / review / approve / reject / clarify | `shared`, `governance` | [`ECS_STATE_TRANSITION_MATRIX.md`](ECS_STATE_TRANSITION_MATRIX.md) |
| Evidence reuse | Cross-control / cross-framework reuse | `operations`, `governance` | [`../evidence-management/evidence_reuse_lifecycle_functional_design.md`](../evidence-management/evidence_reuse_lifecycle_functional_design.md) |
| Framework assessment | Per-framework dashboards, control mapping, FCM | `frameworks` | [`../api/framework_control_master.md`](../api/framework_control_master.md) |
| Observations & findings | Open / assign / remediate / close | `governance`, `audit_intelligence` | [`../evidence-management/OBSERVATION_AND_REPOSITORY_GUIDE.md`](../evidence-management/OBSERVATION_AND_REPOSITORY_GUIDE.md) |
| Scheduler operations | Asset-driven plans, run/retry/pause | `audit_intelligence`, `operations` | [`SCHEDULER_ARCHITECTURE.md`](SCHEDULER_ARCHITECTURE.md) |
| Enterprise integrations | SaaS / DevSecOps / Graph adapters | `operations/integrations`, `ecs_platform/connectors` | [`../connectors/ECS_MASTER_INTEGRATION_MATRIX.md`](../connectors/ECS_MASTER_INTEGRATION_MATRIX.md) |
| Executive analytics & ROI | Persona dashboards, KPIs, ROI center | `executive_overview` | [`ecs_hld.md`](ecs_hld.md) §1 |
| Enterprise GRC | Risk, exceptions, CMDB-style views | `enterprise_grc` | [`ecs_hld.md`](ecs_hld.md) §1 |
| AI-SDLC governance | Stage gates, AI posture, controlled docs | `ai_sdlc` | [`../ai-sdlc/`](../ai-sdlc/README.md) |
| Audit intelligence / RAG Q&A | Citation-grounded NL queries, prompt workbench | `audit_intelligence`, `ecs_platform/rag` | [`../ai-sdlc/ECS_AI_ARCHITECTURE_REFERENCE.md`](../ai-sdlc/ECS_AI_ARCHITECTURE_REFERENCE.md) |
| Reporting & audit packaging | Report catalog, exports, packs | `executive_overview`, `governance` | [`ECS_BUSINESS_PROCESS_MODEL.md`](ECS_BUSINESS_PROCESS_MODEL.md) |

---

## 2. Functional value chain

```mermaid
flowchart LR
  INV["Application &\nasset inventory"] --> PLAN["Schedule / plan\ncollection"]
  PLAN --> COLL["Collect evidence\n(upload · connector · PQE)"]
  COLL --> STORE["Repository &\ncustody"]
  STORE --> MAP["Map to controls\n& frameworks"]
  MAP --> VAL["Validate &\nobserve"]
  VAL --> REV["Review / approve\n/ reuse"]
  REV --> AUD["Dashboards · packs\n· RAG Q&A"]
```

Process-level detail (actors, events, gates):
[`ECS_BUSINESS_PROCESS_MODEL.md`](ECS_BUSINESS_PROCESS_MODEL.md).
Sequence-level detail:
[`ECS_SEQUENCE_DIAGRAMS.md`](ECS_SEQUENCE_DIAGRAMS.md).

---

## 3. Persona → function (summary)

| Persona (canonical roles) | Primary functions |
|---------------------------|-------------------|
| Application Owner | Upload/submit evidence, respond to rejections, onboarding |
| Auditor / Reviewer | Review queues, approve/reject, observations, audit prep |
| Compliance / ISG | Framework admin, completeness, exception governance |
| CIO / Vertical / Functional Head | Readiness KPIs, executive/pan-India views |
| Security Officer | Security findings, compensating controls |
| Platform Admin | Integrations, scheduler, connector workbench, config |

Role → action detail:
[`ECS_ROLE_ACTION_MATRIX.md`](ECS_ROLE_ACTION_MATRIX.md).
RBAC config:
`config/rbac.yaml` (enforcement is flag-gated; see
[`../production/ECS_SECURITY_REFERENCE.md`](../production/ECS_SECURITY_REFERENCE.md)).

---

## 4. Functional vs logical vs technical

| If you need… | Go to |
|--------------|-------|
| What the product does for users | **This document** + Business Process Model |
| How components collaborate | [`LOGICAL_ARCHITECTURE.md`](LOGICAL_ARCHITECTURE.md) |
| Stack, ports, stores, deployment | [`TECHNICAL_ARCHITECTURE.md`](TECHNICAL_ARCHITECTURE.md) |
| System boundary & externals | [`SYSTEM_ARCHITECTURE.md`](SYSTEM_ARCHITECTURE.md) |

---

## Verification notes

- Capability ↔ module mapping matches [`ecs_hld.md`](ecs_hld.md) §1 and
  [`ecs_enterprise_architecture_review.md`](ecs_enterprise_architecture_review.md) §2.
- Gates marked **(Inferred Enterprise Workflow)** in the Business Process Model
  are not claimed as fully enforced in code.
