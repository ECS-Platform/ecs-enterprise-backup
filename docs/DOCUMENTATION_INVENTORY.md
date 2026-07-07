# ECS Documentation Inventory

**Purpose:** A single, authoritative map of the ECS (Evidence Collection System)
documentation set — organised by area, with purpose, owner, status, and cross
references. Generated during the final enterprise consolidation pass (pre-UAT).

**Scope:** 240 Markdown documents across `docs/` (29 areas). This inventory is a
**directory-level** index; for a per-file navigation/contradiction audit see
[`docs/AUDIT/ECS_DOCUMENTATION_INVENTORY.md`](AUDIT/ECS_DOCUMENTATION_INVENTORY.md)
(this file supersedes it as the top-level entry point and does not duplicate it).

> Ground-truth product facts (verified from code this pass): **187 predefined
> controls**, **21 technologies**, **11 enterprise integration adapters**,
> **13 predefined-query connectors** (+ shared `ms_graph_base`), **21 Docker
> Compose services**.

---

## 1. How to read this inventory

- **Status legend:** ✅ Current · 🟡 Current but references demo-seed numbers that
  differ from the live catalog (documented drift; not a defect) · 🗄️ Historical /
  phase report (kept for traceability; not maintained).
- **Owner** is the maintaining role, not an individual (this is an open repo).

---

## 2. Area inventory

| Area (dir) | Docs | Purpose | Owner | Status | Key entry points |
|------------|------|---------|-------|--------|------------------|
| `docs/` (root) | 31 | Cross-cutting reports, audits, this inventory, top-level READMEs | Platform | ✅ | [README.md](README.md), [DOCUMENTATION_AUDIT_REPORT.md](DOCUMENTATION_AUDIT_REPORT.md), [FINAL_REPOSITORY_HEALTH_REPORT.md](FINAL_REPOSITORY_HEALTH_REPORT.md) |
| `docs/API/` | 1 | REST API reference (implemented endpoints only) | Platform Eng | ✅ | [API/ECS_API_REFERENCE.md](API/ECS_API_REFERENCE.md) |
| `docs/DEVELOPER/` | 23 | Developer onboarding, module guides, connector guides, UAT setup, hardening | Platform Eng | ✅ | [DEVELOPER/README_DEVELOPER.md](DEVELOPER/README_DEVELOPER.md) |
| `docs/architecture/` (a.k.a. `ARCHITECTURE`) | 3 | Enterprise/data/deployment architecture references | Architecture | ✅ | [ARCHITECTURE/ARCHITECTURE_INDEX.md](ARCHITECTURE/ARCHITECTURE_INDEX.md) |
| `docs/hld/`, `docs/lld/` | 2 | High-/low-level design | Architecture | ✅ | [hld/ecs_hld.md](hld/ecs_hld.md), [lld/ecs_lld.md](lld/ecs_lld.md) |
| `docs/diagrams/` | 2 | Sequence + ER diagrams (Mermaid) | Architecture | ✅ | [diagrams/ecs_sequence_diagrams.md](diagrams/ecs_sequence_diagrams.md) |
| `docs/operations/` | 31 | Runbooks: deployment, rollback, monitoring, DR, backup, connector playbooks, query execution | SRE / Ops | ✅ | [operations/DEPLOYMENT_RUNBOOK.md](operations/DEPLOYMENT_RUNBOOK.md), [operations/ECS_OPERATIONS_RUNBOOK.md](operations/ECS_OPERATIONS_RUNBOOK.md) |
| `docs/INTEGRATIONS/` | 11 | Per-connector integration references | Platform Eng | ✅ | see [DEVELOPER/INTEGRATION_ADAPTERS_GUIDE.md](DEVELOPER/INTEGRATION_ADAPTERS_GUIDE.md) |
| `docs/FRAMEWORKS/` | 18 | Compliance framework catalog + mappings (RBI, PCI DSS, ISO 27001, ITPP, …) | Audit / GRC | ✅ | framework catalog |
| `docs/WORKFLOWS/` | 8 | Workflow orchestration, state/SLA/role/notification matrices | Product | ✅ | [WORKFLOWS/README.md](WORKFLOWS/README.md) |
| `docs/PRODUCT/`, `docs/product_manual/` | 14 | Product user manual, feature/module/KPI/persona references | Product | ✅ | [PRODUCT/ECS_PRODUCT_USER_MANUAL.md](PRODUCT/ECS_PRODUCT_USER_MANUAL.md) |
| `docs/AI/` | 36 | AI-SDLC, LLM, benchmark, ROI, token-calculation docs | AI/ML | 🗄️/✅ | AI module docs |
| `docs/AUDIT/` | 10 | Navigation, documentation, technical-debt, feature-inventory audits | Platform | 🟡 | [AUDIT/ECS_DOCUMENTATION_INVENTORY.md](AUDIT/ECS_DOCUMENTATION_INVENTORY.md) |
| `docs/PHASE1/` | 10 | Phase-1 delivery reports | Delivery | 🗄️ | phase reports |
| `docs/executive/` | 7 | Executive knowledge/consolidation/readiness reports | Leadership | 🗄️/✅ | [executive/ECS_MASTER_KNOWLEDGE_CONSOLIDATION_REPORT.md](executive/ECS_MASTER_KNOWLEDGE_CONSOLIDATION_REPORT.md) |
| `docs/UAT/` | 3 | UAT validation reports (workflow, screen, KPI) | QA / UAT | ✅ | UAT validation reports |
| `docs/UX/` | 5 | Navigation/IA, demo trustability | Design | ✅ | UX reviews |
| `docs/TRAINING/`, `docs/KPI/` | 12 | Training manual, KPI dictionary | Enablement | ✅ | training/KPI |
| `docs/PRODUCTION/`, `docs/SECURITY/`, `docs/DEPLOYMENT/`, `docs/TESTING/`, `docs/EVIDENCE/`, `docs/CONTROLS/`, `docs/DEMO/`, `docs/benchmarks/` | 17 | Focused single-topic references | Various | ✅ | topic-specific |

---

## 3. Canonical entry points by audience

| Audience | Start here |
|----------|-----------|
| New developer | [DEVELOPER/README_DEVELOPER.md](DEVELOPER/README_DEVELOPER.md) → [DEVELOPER/ECS_DEVELOPER_ONBOARDING_MANUAL.md](DEVELOPER/ECS_DEVELOPER_ONBOARDING_MANUAL.md) |
| Connectors / UAT wiring | [DEVELOPER/INTEGRATION_ADAPTERS_GUIDE.md](DEVELOPER/INTEGRATION_ADAPTERS_GUIDE.md), [DEVELOPER/ENTERPRISE_CONNECTOR_UAT_SETUP.md](DEVELOPER/ENTERPRISE_CONNECTOR_UAT_SETUP.md), [DEVELOPER/MS_GRAPH_CONNECTOR_GUIDE.md](DEVELOPER/MS_GRAPH_CONNECTOR_GUIDE.md) |
| Predefined queries | [DEVELOPER/PREDEFINED_DATABASE_QUERY_MODULE.md](DEVELOPER/PREDEFINED_DATABASE_QUERY_MODULE.md), [operations/ECS_PREDEFINED_QUERY_EXECUTION_GUIDE.md](operations/ECS_PREDEFINED_QUERY_EXECUTION_GUIDE.md), [DEVELOPER/AEROSPIKE_LOCAL_TESTING_GUIDE.md](DEVELOPER/AEROSPIKE_LOCAL_TESTING_GUIDE.md) |
| Scheduler | [DEVELOPER/UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md](DEVELOPER/UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md), [operations/ECS_SCHEDULER_REFERENCE.md](operations/ECS_SCHEDULER_REFERENCE.md) |
| Operations / go-live | [operations/DEPLOYMENT_RUNBOOK.md](operations/DEPLOYMENT_RUNBOOK.md), [operations/PRODUCTION_CHECKLIST.md](operations/PRODUCTION_CHECKLIST.md), [operations/ROLLBACK_RUNBOOK.md](operations/ROLLBACK_RUNBOOK.md) |
| Architecture | [ARCHITECTURE/ARCHITECTURE_INDEX.md](ARCHITECTURE/ARCHITECTURE_INDEX.md) |
| API | [API/ECS_API_REFERENCE.md](API/ECS_API_REFERENCE.md) |
| Product | [PRODUCT/ECS_PRODUCT_USER_MANUAL.md](PRODUCT/ECS_PRODUCT_USER_MANUAL.md) |
| Leadership demo | [DEVELOPER/DEMO_RUNBOOK.md](DEVELOPER/DEMO_RUNBOOK.md), [DEVELOPER/LEADERSHIP_DEMO_SCRIPT.md](DEVELOPER/LEADERSHIP_DEMO_SCRIPT.md) |

---

## 4. Known documentation drift (non-blocking)

- **Catalog vs demo-seed numbers.** Some AUDIT/executive/phase reports cite
  demo-seed dataset numbers (e.g. "17 frameworks / 320 controls / 10 connectors")
  that differ from the live catalog (**187 controls / 21 technologies / 11
  adapters**). This is documented drift in
  [AUDIT/ECS_DOCUMENTATION_INVENTORY.md](AUDIT/ECS_DOCUMENTATION_INVENTORY.md) §5,
  not a functional defect. Historical/phase reports are intentionally not
  retro-edited.
- **Consolidated-count fixes applied this pass:** DEMO_RUNBOOK, LEADERSHIP_DEMO_SCRIPT,
  and TECHNOLOGY_MAPPING_GUIDE updated 167→187 controls / 20→21 technologies to
  reflect the Aerospike addition.

---

## 5. Connector & runtime API references

Repository-grounded developer references (added for connectors, Microsoft Graph,
the Connector Test Workbench, and the scheduler runtime):

| Document | Purpose |
|---|---|
| [microsoft_graph_connector_api_reference.md](microsoft_graph_connector_api_reference.md) | Microsoft Graph auth, discovery/retrieval, pagination, config |
| [enterprise_connector_api_reference.md](enterprise_connector_api_reference.md) | All 11 connectors: adapter, auth, endpoints, normalizers, env, tests |
| [connector_test_workbench_design.md](connector_test_workbench_design.md) | Workbench code path, APIs, sequence + dependency diagrams |
| [scheduler_runtime_flow.md](scheduler_runtime_flow.md) | Full scheduler lifecycle (trigger → readiness → evidence → observations) |
| [test_workbench_vs_scheduler.md](test_workbench_vs_scheduler.md) | Difference + shared connector code path |
| [runtime_call_graph.md](runtime_call_graph.md) | Endpoint→service→repo→connector call graph + 12 sequence diagrams |
| [connector_frontend_testing_matrix.md](connector_frontend_testing_matrix.md) | Per-connector frontend testing matrix |
| [connector_frontend_manual_testing.md](connector_frontend_manual_testing.md) | Manual frontend test cases |
| [evidence_reuse_lifecycle_functional_design.md](evidence_reuse_lifecycle_functional_design.md) | Functional evidence reuse / observation lifecycle |

---

## 6. Maintenance

When adding a technology, connector, or module, update: this inventory, the
relevant `DEVELOPER/*` guide, `API/ECS_API_REFERENCE.md` (if routes change),
`ARCHITECTURE/ARCHITECTURE_INDEX.md` (if architecture changes), the connector
references above (if a connector changes), and the count references in
DEMO_RUNBOOK / LEADERSHIP_DEMO_SCRIPT. Keep historical reports immutable; record
new facts in current docs.
