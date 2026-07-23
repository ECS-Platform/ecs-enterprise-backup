# ECS Documentation

Welcome to the **Enterprise Evidence Collection System (ECS)** documentation.

This folder is organized by topic so you can find what you need without reading
everything. **New here? Start with [`00-start-here/`](01-product/00-start-here/README.md).**

> Looking for a specific document? See [How to find docs](#how-to-find-docs) or
> the full [Documentation Inventory](DOCUMENTATION_INVENTORY.md).

---

## Folder map

| Folder | What's inside |
| --- | --- |
| [`00-start-here/`](01-product/00-start-here/README.md) | Orientation, demo-mode setup, common commands, troubleshooting |
| [`developer-manual/`](03-development/developer-manual/README.md) | Engineering handbook, **Phase-1 implementation**, API, database, connectors, testing |
| [`design/`](02-architecture/design/README.md) | Functional designs & SRS (supplements business use cases) |
| [`reports/`](04-testing/reports/README.md) | Validation reports, KPI audits, benchmark outcomes |
| [`operations/`](03-development/operations/README.md) | Runbooks, UAT execution, query execution, backup/recovery, go-live, support |
| [`workbenches/`](03-development/workbenches/README.md) | Audit LLM Prompt Workbench + frontend workbench guides |
| [`benchmarks/`](04-testing/benchmarks/README.md) | Local LLM benchmarking (16 GB / 20 GB), token estimation, performance |
| [`connectors/`](03-development/developer-manual/connectors/README.md) | Enterprise connector API, framework, Connector Test Workbench, per-connector docs *(under developer-manual)* |
| [`graph-api/`](03-development/developer-manual/connectors/README.md) | Microsoft Graph — merged into developer-manual/connectors |
| [`scheduler/`](03-development/developer-manual/phase1/scheduler/README.md) | Asset-driven scheduler runtime *(under developer-manual/phase1)* |
| [`evidence-management/`](03-development/evidence-management/README.md) | Evidence collection, validation, reuse, hash integrity, observations |
| [`audit-intelligence/`](03-development/audit-intelligence/README.md) | Audit LLM prompt inventory, NL audit queries, server-side processing |
| [`ai-sdlc/`](03-development/ai-sdlc/README.md) | AI architecture, local-LLM strategy, model abstraction, AI governance |
| [`architecture/`](02-architecture/architecture/README.md) | Architecture index, enterprise/solution arch, HLD (C4)/LLD, data & deployment architecture, workflows |
| [`api/`](03-development/developer-manual/api/README.md) | Phase 1 API supplements *(under developer-manual)* |
| [`deployment/`](03-development/deployment/GCP_DEPLOYMENT_GUIDE.md) | Cloud deployment (GCP: GKE, Cloud SQL/pgvector, GCS, IAM, CI/CD, promotion) |
| [`runbooks/`](03-development/runbooks/README.md) | Focused incident runbooks (scheduler, evidence upload, DB Agent, LLM, config, readiness) |
| [`product/`](01-product/product/README.md) | Product manual, feature/KPI/module refs, use-case catalogs, frameworks, training |
| [`testing/`](04-testing/testing/README.md) | Testing guide, test strategy, load testing, UAT validation, E2E/smoke guides |
| [`production/`](03-development/production/README.md) | Deployment, hardening, monitoring, security, SSO/OIDC, readiness gaps |
| [`use-cases/`](01-product/use-cases/README.md) | **phase1/** business use cases, phase2–4 plans, reference matrices |
| [`diagrams/`](02-architecture/diagrams/README.md) | ER diagrams, sequence diagrams |
| [`archive/`](05-archive/archive/README.md) | Point-in-time reports/audits + superseded docs (history only) |

---

## Canonical guides (one entry point per topic)

Newer navigator/hub docs that tie together the deep per-topic docs:

| Topic | Canonical doc |
| --- | --- |
| Enterprise architecture (bank/GCP/AWS, security zones, jump server) | [`architecture/ENTERPRISE_ARCHITECTURE.md`](02-architecture/architecture/ENTERPRISE_ARCHITECTURE.md) |
| Solution architecture (functional/runtime/integration/data/AI) | [`architecture/SOLUTION_ARCHITECTURE.md`](02-architecture/architecture/SOLUTION_ARCHITECTURE.md) |
| High-level design (C4) | [`architecture/HIGH_LEVEL_DESIGN.md`](02-architecture/architecture/HIGH_LEVEL_DESIGN.md) |
| Low-level design | [`architecture/LOW_LEVEL_DESIGN.md`](02-architecture/architecture/LOW_LEVEL_DESIGN.md) |
| Developer manual | [`developer-manual/DEVELOPER_MANUAL.md`](03-development/developer-manual/DEVELOPER_MANUAL.md) |
| Prompt testing (LLM/Ollama/Gemini/replay/benchmark) | [`developer-manual/PROMPT_TESTING_GUIDE.md`](03-development/developer-manual/PROMPT_TESTING_GUIDE.md) |
| Connector Test Workbench | [`developer-manual/TEST_WORKBENCH_GUIDE.md`](03-development/developer-manual/TEST_WORKBENCH_GUIDE.md) |
| Predefined query catalog | [`developer-manual/PREDEFINED_QUERY_CATALOG.md`](03-development/developer-manual/PREDEFINED_QUERY_CATALOG.md) |
| Database Agent (jump server) | [`developer-manual/DATABASE_AGENT_GUIDE.md`](03-development/developer-manual/DATABASE_AGENT_GUIDE.md) |
| Operations manual (day-2) | [`operations/OPERATIONS_MANUAL.md`](03-development/operations/OPERATIONS_MANUAL.md) |
| Testing guide | [`testing/TESTING_GUIDE.md`](04-testing/testing/TESTING_GUIDE.md) |
| GCP deployment | [`deployment/GCP_DEPLOYMENT_GUIDE.md`](03-development/deployment/GCP_DEPLOYMENT_GUIDE.md) |
| Incident runbooks | [`runbooks/README.md`](03-development/runbooks/README.md) |

---

## Reading paths

Pick the path that matches your role. Each step links to the best starting doc.

### New Developer / New Tester Path

1. [`00-start-here/ARCHITECTURE_OVERVIEW.md`](01-product/00-start-here/ARCHITECTURE_OVERVIEW.md) — what ECS is, in one read.
2. [`00-start-here/DEMO_MODE_SETUP.md`](01-product/00-start-here/DEMO_MODE_SETUP.md) — run ECS locally in demo mode.
3. [`00-start-here/COMMON_COMMANDS.md`](01-product/00-start-here/COMMON_COMMANDS.md) — start/stop/test/seed commands.
4. [`developer-manual/README_DEVELOPER.md`](03-development/developer-manual/README_DEVELOPER.md) — the developer manual index.
5. [`developer-manual/DEVELOPER_SETUP_GUIDE.md`](03-development/developer-manual/DEVELOPER_SETUP_GUIDE.md) — full local setup.
6. [`architecture/ARCHITECTURE_INDEX.md`](02-architecture/architecture/ARCHITECTURE_INDEX.md) — how the system fits together.
7. [`testing/E2E_SMOKE_TEST_GUIDE.md`](04-testing/testing/E2E_SMOKE_TEST_GUIDE.md) — how to run and write tests.
8. [`00-start-here/TROUBLESHOOTING_GUIDE.md`](01-product/00-start-here/TROUBLESHOOTING_GUIDE.md) — when something breaks.

### UAT Operator Path

1. [`operations/README.md`](03-development/operations/README.md) — the operations index.
2. [`operations/ECS_OPERATIONS_RUNBOOK.md`](03-development/operations/ECS_OPERATIONS_RUNBOOK.md) — day-to-day operation.
3. [`operations/UAT_VALIDATION_RUNBOOK.md`](03-development/operations/UAT_VALIDATION_RUNBOOK.md) — UAT validation steps.
4. [`operations/uat_ip_configuration_guide.md`](03-development/operations/uat_ip_configuration_guide.md) — configure UAT assets/IPs (no localhost).
5. [`connectors/ENTERPRISE_CONNECTOR_UAT_SETUP.md`](03-development/developer-manual/connectors/ENTERPRISE_CONNECTOR_UAT_SETUP.md) — connect real systems.
6. [`connectors/uat_connector_credentials_guide.md`](03-development/developer-manual/connectors/uat_connector_credentials_guide.md) — connector credentials.
7. [`scheduler/scheduler_runtime_flow.md`](03-development/developer-manual/phase1/scheduler/scheduler_runtime_flow.md) — scheduled evidence pull.
8. [`operations/ECS_GO_LIVE_CHECKLIST.md`](03-development/operations/ECS_GO_LIVE_CHECKLIST.md) — go-live checklist.

### Business / Auditor Path

1. [`product/ECS_MASTER_PRODUCT_MANUAL.md`](01-product/product/ECS_MASTER_PRODUCT_MANUAL.md) — what ECS does, for business users.
2. [`product/ECS_MASTER_USE_CASE_CATALOG.md`](01-product/product/ECS_MASTER_USE_CASE_CATALOG.md) — the use-case catalog.
3. [`product/ECS_MASTER_KPI_DICTIONARY.md`](01-product/product/ECS_MASTER_KPI_DICTIONARY.md) — every KPI, defined.
4. [`product/ECS_FUNCTIONAL_MANUAL.md`](01-product/product/ECS_FUNCTIONAL_MANUAL.md) — how to perform core workflows.
5. [`evidence-management/evidence_reuse_lifecycle_functional_design.md`](03-development/evidence-management/evidence_reuse_lifecycle_functional_design.md) — evidence reuse & observation lifecycle.
6. [`audit-intelligence/audit_llm_prompt_inventory.md`](03-development/audit-intelligence/audit_llm_prompt_inventory.md) — natural-language audit queries.
7. [`product/ECS_FRAMEWORK_REFERENCE.md`](01-product/product/ECS_FRAMEWORK_REFERENCE.md) — supported compliance frameworks.

### Local LLM / Benchmark Path

1. [`audit-intelligence/README.md`](03-development/audit-intelligence/README.md) — audit LLM overview.
2. [`audit-intelligence/audit_llm_prompt_inventory.md`](03-development/audit-intelligence/audit_llm_prompt_inventory.md) — the prompt library.
3. [`audit-intelligence/audit_llm_server_side_processing.md`](03-development/audit-intelligence/audit_llm_server_side_processing.md) — how prompts execute server-side.
4. [`workbenches/audit_llm_prompt_workbench_design.md`](03-development/workbenches/audit_llm_prompt_workbench_design.md) — the prompt workbench.
5. [`benchmarks/audit_llm_local_benchmark_plan.md`](04-testing/benchmarks/audit_llm_local_benchmark_plan.md) — the benchmark plan.
6. [`benchmarks/audit_llm_16gb_20gb_testing_guide.md`](04-testing/benchmarks/audit_llm_16gb_20gb_testing_guide.md) — 16 GB / 20 GB laptop testing.
7. [`ai-sdlc/README.md`](03-development/ai-sdlc/README.md) — AI architecture & local-LLM strategy.

---

## How to find docs

```bash
# List every doc, grouped by folder:
find docs -name "*.md" | sort

# List the folders and their READMEs:
find docs -name "README.md" | sort

# Full-text search the docs (ripgrep):
rg -i "your search term" docs/

# Find a doc by (partial) filename:
find docs -iname "*keyword*.md"
```

- Full catalog with purpose/owner/status: [`DOCUMENTATION_INVENTORY.md`](DOCUMENTATION_INVENTORY.md).
- Every folder has a `README.md` describing its contents and what to read first.

---

## Conventions

- **One topic per folder.** A doc that spans topics lives in its primary folder and
  is cross-linked from related folder READMEs.
- **`archive/`** holds point-in-time reports and superseded docs — kept for history,
  not current truth.
- **Nothing is deleted.** This structure was produced by moving files (tracked as
  git renames) via `scripts/reorganize_docs.py`; folder READMEs are generated by
  `scripts/gen_docs_folder_readmes.py`.
