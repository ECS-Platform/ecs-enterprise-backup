# ECS Documentation

Welcome to the **Enterprise Evidence Collection System (ECS)** documentation.

This folder is organized by topic so you can find what you need without reading
everything. **New here? Start with [`00-start-here/`](00-start-here/README.md).**

> Looking for a specific document? See [How to find docs](#how-to-find-docs) or
> the full [Documentation Inventory](DOCUMENTATION_INVENTORY.md).

---

## Folder map

| Folder | What's inside |
| --- | --- |
| [`00-start-here/`](00-start-here/README.md) | Orientation, demo-mode setup, common commands, troubleshooting |
| [`developer-manual/`](developer-manual/README.md) | Engineering handbook, setup, config framework, API reference, module ownership |
| [`operations/`](operations/README.md) | Runbooks, UAT execution, query execution, backup/recovery, go-live, support |
| [`workbenches/`](workbenches/README.md) | Audit LLM Prompt Workbench + frontend workbench guides |
| [`benchmarks/`](benchmarks/README.md) | Local LLM benchmarking (16 GB / 20 GB), token estimation, performance |
| [`connectors/`](connectors/README.md) | Enterprise connector API, framework, Connector Test Workbench, per-connector docs |
| [`graph-api/`](graph-api/README.md) | Microsoft Graph (SharePoint / Teams / Outlook) integration |
| [`scheduler/`](scheduler/README.md) | Asset-driven scheduler runtime, call graph, asset discovery |
| [`evidence-management/`](evidence-management/README.md) | Evidence collection, validation, reuse, hash integrity, observations |
| [`audit-intelligence/`](audit-intelligence/README.md) | Audit LLM prompt inventory, NL audit queries, server-side processing |
| [`ai-sdlc/`](ai-sdlc/README.md) | AI architecture, local-LLM strategy, model abstraction, AI governance |
| [`architecture/`](architecture/README.md) | Architecture index, enterprise/solution arch, HLD (C4)/LLD, data & deployment architecture, workflows |
| [`deployment/`](deployment/GCP_DEPLOYMENT_GUIDE.md) | Cloud deployment (GCP: GKE, Cloud SQL/pgvector, GCS, IAM, CI/CD, promotion) |
| [`runbooks/`](runbooks/README.md) | Focused incident runbooks (scheduler, evidence upload, DB Agent, LLM, config, readiness) |
| [`product/`](product/README.md) | Product manual, feature/KPI/module refs, use-case catalogs, frameworks, training |
| [`testing/`](testing/README.md) | Testing guide, test strategy, load testing, UAT validation, E2E/smoke guides |
| [`production/`](production/README.md) | Deployment, hardening, monitoring, security, SSO/OIDC, readiness gaps |
| [`use-cases/`](use-cases/README.md) | Use-case implementation matrix, API mapping, UAT readiness, phase plans |
| [`diagrams/`](diagrams/README.md) | ER diagrams, sequence diagrams |
| [`archive/`](archive/README.md) | Point-in-time reports/audits + superseded docs (history only) |

---

## Canonical guides (one entry point per topic)

Newer navigator/hub docs that tie together the deep per-topic docs:

| Topic | Canonical doc |
| --- | --- |
| Enterprise architecture (bank/GCP/AWS, security zones, jump server) | [`architecture/ENTERPRISE_ARCHITECTURE.md`](architecture/ENTERPRISE_ARCHITECTURE.md) |
| Solution architecture (functional/runtime/integration/data/AI) | [`architecture/SOLUTION_ARCHITECTURE.md`](architecture/SOLUTION_ARCHITECTURE.md) |
| High-level design (C4) | [`architecture/HIGH_LEVEL_DESIGN.md`](architecture/HIGH_LEVEL_DESIGN.md) |
| Low-level design | [`architecture/LOW_LEVEL_DESIGN.md`](architecture/LOW_LEVEL_DESIGN.md) |
| Developer manual | [`developer-manual/DEVELOPER_MANUAL.md`](developer-manual/DEVELOPER_MANUAL.md) |
| Prompt testing (LLM/Ollama/Gemini/replay/benchmark) | [`developer-manual/PROMPT_TESTING_GUIDE.md`](developer-manual/PROMPT_TESTING_GUIDE.md) |
| Connector Test Workbench | [`developer-manual/TEST_WORKBENCH_GUIDE.md`](developer-manual/TEST_WORKBENCH_GUIDE.md) |
| Predefined query catalog | [`developer-manual/PREDEFINED_QUERY_CATALOG.md`](developer-manual/PREDEFINED_QUERY_CATALOG.md) |
| Database Agent (jump server) | [`developer-manual/DATABASE_AGENT_GUIDE.md`](developer-manual/DATABASE_AGENT_GUIDE.md) |
| Operations manual (day-2) | [`operations/OPERATIONS_MANUAL.md`](operations/OPERATIONS_MANUAL.md) |
| Testing guide | [`testing/TESTING_GUIDE.md`](testing/TESTING_GUIDE.md) |
| GCP deployment | [`deployment/GCP_DEPLOYMENT_GUIDE.md`](deployment/GCP_DEPLOYMENT_GUIDE.md) |
| Incident runbooks | [`runbooks/README.md`](runbooks/README.md) |

---

## Reading paths

Pick the path that matches your role. Each step links to the best starting doc.

### New Developer / New Tester Path

1. [`00-start-here/ARCHITECTURE_OVERVIEW.md`](00-start-here/ARCHITECTURE_OVERVIEW.md) — what ECS is, in one read.
2. [`00-start-here/DEMO_MODE_SETUP.md`](00-start-here/DEMO_MODE_SETUP.md) — run ECS locally in demo mode.
3. [`00-start-here/COMMON_COMMANDS.md`](00-start-here/COMMON_COMMANDS.md) — start/stop/test/seed commands.
4. [`developer-manual/README_DEVELOPER.md`](developer-manual/README_DEVELOPER.md) — the developer manual index.
5. [`developer-manual/DEVELOPER_SETUP_GUIDE.md`](developer-manual/DEVELOPER_SETUP_GUIDE.md) — full local setup.
6. [`architecture/ARCHITECTURE_INDEX.md`](architecture/ARCHITECTURE_INDEX.md) — how the system fits together.
7. [`testing/E2E_SMOKE_TEST_GUIDE.md`](testing/E2E_SMOKE_TEST_GUIDE.md) — how to run and write tests.
8. [`00-start-here/TROUBLESHOOTING_GUIDE.md`](00-start-here/TROUBLESHOOTING_GUIDE.md) — when something breaks.

### UAT Operator Path

1. [`operations/README.md`](operations/README.md) — the operations index.
2. [`operations/ECS_OPERATIONS_RUNBOOK.md`](operations/ECS_OPERATIONS_RUNBOOK.md) — day-to-day operation.
3. [`operations/UAT_VALIDATION_RUNBOOK.md`](operations/UAT_VALIDATION_RUNBOOK.md) — UAT validation steps.
4. [`operations/uat_ip_configuration_guide.md`](operations/uat_ip_configuration_guide.md) — configure UAT assets/IPs (no localhost).
5. [`connectors/ENTERPRISE_CONNECTOR_UAT_SETUP.md`](connectors/ENTERPRISE_CONNECTOR_UAT_SETUP.md) — connect real systems.
6. [`connectors/uat_connector_credentials_guide.md`](connectors/uat_connector_credentials_guide.md) — connector credentials.
7. [`scheduler/scheduler_runtime_flow.md`](scheduler/scheduler_runtime_flow.md) — scheduled evidence pull.
8. [`operations/ECS_GO_LIVE_CHECKLIST.md`](operations/ECS_GO_LIVE_CHECKLIST.md) — go-live checklist.

### Business / Auditor Path

1. [`product/ECS_MASTER_PRODUCT_MANUAL.md`](product/ECS_MASTER_PRODUCT_MANUAL.md) — what ECS does, for business users.
2. [`product/ECS_MASTER_USE_CASE_CATALOG.md`](product/ECS_MASTER_USE_CASE_CATALOG.md) — the use-case catalog.
3. [`product/ECS_MASTER_KPI_DICTIONARY.md`](product/ECS_MASTER_KPI_DICTIONARY.md) — every KPI, defined.
4. [`product/ECS_FUNCTIONAL_MANUAL.md`](product/ECS_FUNCTIONAL_MANUAL.md) — how to perform core workflows.
5. [`evidence-management/evidence_reuse_lifecycle_functional_design.md`](evidence-management/evidence_reuse_lifecycle_functional_design.md) — evidence reuse & observation lifecycle.
6. [`audit-intelligence/audit_llm_prompt_inventory.md`](audit-intelligence/audit_llm_prompt_inventory.md) — natural-language audit queries.
7. [`product/ECS_FRAMEWORK_REFERENCE.md`](product/ECS_FRAMEWORK_REFERENCE.md) — supported compliance frameworks.

### Local LLM / Benchmark Path

1. [`audit-intelligence/README.md`](audit-intelligence/README.md) — audit LLM overview.
2. [`audit-intelligence/audit_llm_prompt_inventory.md`](audit-intelligence/audit_llm_prompt_inventory.md) — the prompt library.
3. [`audit-intelligence/audit_llm_server_side_processing.md`](audit-intelligence/audit_llm_server_side_processing.md) — how prompts execute server-side.
4. [`workbenches/audit_llm_prompt_workbench_design.md`](workbenches/audit_llm_prompt_workbench_design.md) — the prompt workbench.
5. [`benchmarks/audit_llm_local_benchmark_plan.md`](benchmarks/audit_llm_local_benchmark_plan.md) — the benchmark plan.
6. [`benchmarks/audit_llm_16gb_20gb_testing_guide.md`](benchmarks/audit_llm_16gb_20gb_testing_guide.md) — 16 GB / 20 GB laptop testing.
7. [`ai-sdlc/README.md`](ai-sdlc/README.md) — AI architecture & local-LLM strategy.

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
