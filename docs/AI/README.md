# ECS Local LLM Readiness, Universal Coverage & Migration Program

**Release tag:** `ecs-local-llm-readiness-enterprise-v1`
**Type:** Assessment, inventory, architecture & migration documentation. **No production code,
providers, or functionality were modified** (constraint honored).
**Grounding:** Every claim traces to repository file:line. Reference/estimate content (benchmarks,
quality tiers) is explicitly labeled as such and not presented as measured fact.

---

## Headline Finding

> **ECS is already local-LLM-capable.** It ships a config-selected provider abstraction
> (`ecs_platform/llm_engine/provider.py`) that **defaults to local Ollama** (`qwen3:8b`) with
> `nomic-embed-text` embeddings into a local **pgvector** store. Cloud providers are optional. Most AI
> features are deterministic (no model). No cloud LLM is required at runtime. This program is therefore
> **validation + hardening + rollout**, not new development.

---

## Documents (by phase)

| Phase | Document | Covers |
|---|---|---|
| 1 | [ECS_AI_DEPENDENCY_INVENTORY.md](ECS_AI_DEPENDENCY_INVENTORY.md) | Providers, embeddings, vector DBs, deps, flags |
| 2 | [ECS_AI_FEATURE_INVENTORY.md](ECS_AI_FEATURE_INVENTORY.md) | Every AI feature + LLM/deterministic classification |
| 3 | [ECS_AI_MODULE_COVERAGE_MATRIX.md](ECS_AI_MODULE_COVERAGE_MATRIX.md) | Operations, Frameworks, Evidence, Governance, Executive, AI Gov, AI SDLC |
| 4 | [ECS_AI_PERSONA_COVERAGE_MATRIX.md](ECS_AI_PERSONA_COVERAGE_MATRIX.md) | All logins/personas/roles → readiness |
| 5 | [ECS_AI_APPLICATION_COVERAGE_MATRIX.md](ECS_AI_APPLICATION_COVERAGE_MATRIX.md) | Governed banking applications |
| 6 | [ECS_AI_CONNECTOR_COVERAGE_MATRIX.md](ECS_AI_CONNECTOR_COVERAGE_MATRIX.md) | Integration/connector layers |
| 7 | [ECS_EMBEDDING_STRATEGY.md](ECS_EMBEDDING_STRATEGY.md) | Embedding models, dims, pgvector, bge/e5/instructor |
| 8 | [ECS_MODEL_ABSTRACTION_ARCHITECTURE.md](ECS_MODEL_ABSTRACTION_ARCHITECTURE.md) | Provider abstraction (exists) + recommendations |
| 9 | [ECS_MODEL_COMPATIBILITY_MATRIX.md](ECS_MODEL_COMPATIBILITY_MATRIX.md) | Qwen/Llama/DeepSeek/Mistral/Gemma via Ollama |
| 10 | [ECS_AI_PERFORMANCE_BENCHMARK.md](ECS_AI_PERFORMANCE_BENCHMARK.md) | Reproducible harness + reference ranges |
| 11 | [ECS_BANKING_AI_ARCHITECTURE.md](ECS_BANKING_AI_ARCHITECTURE.md) | Air-gap/on-prem/private/UAT/prod readiness |
| 12 | [ECS_LOCAL_LLM_UNIVERSAL_VALIDATION_MATRIX.md](ECS_LOCAL_LLM_UNIVERSAL_VALIDATION_MATRIX.md) | Everything assessed in one matrix |
| 13 | [ECS_LOCAL_LLM_MIGRATION_PLAN.md](ECS_LOCAL_LLM_MIGRATION_PLAN.md) | Current/future state, risks, effort, rollout |

---

## Implementation, Testing & Use Case Guide (`ecs-local-llm-readiness-enterprise-v1`)

Practitioner-facing set showing how ECS operates on local LLMs (Ollama/Qwen/Llama/Mistral/Phi/Gemma/
DeepSeek). Documentation only — no source changes.

| Phase | Document | Covers |
|---|---|---|
| 1 | [ECS_LOCAL_LLM_DEVELOPER_GUIDE.md](ECS_LOCAL_LLM_DEVELOPER_GUIDE.md) | Provider abstraction, Ollama, models, embeddings, pgvector, vector/RAG/Copilot flows + sequence diagrams |
| 2 | [ECS_LOCAL_LLM_DEPLOYMENT_GUIDE.md](ECS_LOCAL_LLM_DEPLOYMENT_GUIDE.md) | Mac/Windows/Linux/UAT/Prod install, model pulls, pgvector, validation, troubleshooting |
| 3 | [ECS_LOCAL_LLM_SCREEN_MAPPING.md](ECS_LOCAL_LLM_SCREEN_MAPPING.md) | Per-page: current behaviour, local-LLM opportunity, effort |
| 4 | [ECS_LOCAL_LLM_USE_CASE_CATALOG.md](ECS_LOCAL_LLM_USE_CASE_CATALOG.md) | 28 use cases (value/input/output/persona/app/framework/ROI) |
| 4/5 | [ECS_LOCAL_LLM_BANKING_USE_CASES.md](ECS_LOCAL_LLM_BANKING_USE_CASES.md) | Banking use cases + full persona mapping |
| 6 | [ECS_LOCAL_LLM_TESTING_GUIDE.md](ECS_LOCAL_LLM_TESTING_GUIDE.md) | Functional/Perf/Security/Accuracy/Hallucination/RAG/Vector tests |
| — | [ECS_LOCAL_LLM_OPERATIONS_GUIDE.md](ECS_LOCAL_LLM_OPERATIONS_GUIDE.md) | Day-2 ops, health, change mgmt, failure modes, air-gap checklist |
| 7 | [ECS_LOCAL_LLM_PHASE1_ROADMAP.md](ECS_LOCAL_LLM_PHASE1_ROADMAP.md) | MoSCoW Phase-1 recommendations + effort/dependencies |

---

## AI Documentation Review Program (`ecs-ai-documentation-review-v1`)

Architecture/decision/governance/security set produced by the AI documentation review.
**Documentation only — no source changes.** Grounded in `ecs_platform/llm_engine/provider.py`,
`ecs_platform/rag.py`, `ecs_platform/llm_engine/prompt_builder.py`, `config/llm.yaml`,
`config/vectorstore.yaml`. Inferred/target content is labeled.

| # | Document | Covers |
|---|---|---|
| 1 | [ECS_LOCAL_VS_CLOUD_LLM_DECISION_MATRIX.md](ECS_LOCAL_VS_CLOUD_LLM_DECISION_MATRIX.md) | Local/cloud/hybrid capabilities, banking suitability, cost/security/privacy/air-gap, recommendation matrix |
| 2 | [ECS_LLM_USE_CASE_COVERAGE_MATRIX.md](ECS_LLM_USE_CASE_COVERAGE_MATRIX.md) | 82 use cases × local/cloud/hybrid/recommended/complexity/ROI across all 11 domains |
| 3 | [ECS_LOCAL_LLM_USE_CASE_CATALOG_V2.md](ECS_LOCAL_LLM_USE_CASE_CATALOG_V2.md) | 104 use cases (problem/inputs/flow/outputs/personas/screens/APIs/data/benefits) |
| 4 | [ECS_AI_FUNCTIONAL_REQUIREMENTS.md](ECS_AI_FUNCTIONAL_REQUIREMENTS.md) | FR/NFR/Security/AI/Performance/Explainability/Auditability requirements |
| 5 | [ECS_AI_ARCHITECTURE_REFERENCE.md](ECS_AI_ARCHITECTURE_REFERENCE.md) | Ollama/Qwen3/embeddings/pgvector/RAG/retrieval/provider abstraction/hybrid/cloud/AI gov controls |
| 6 | [ECS_AI_GOVERNANCE_OPERATING_MODEL.md](ECS_AI_GOVERNANCE_OPERATING_MODEL.md) | Use-case lifecycle, model/prompt approval, risk, monitoring, revalidation, retirement |
| 7 | [ECS_AI_SECURITY_ARCHITECTURE.md](ECS_AI_SECURITY_ARCHITECTURE.md) | Data classification, prompt security, RBAC, PII, audit logging, encryption, model security |
| 8 | [ECS_AI_DOCUMENT_COMPLETENESS_REPORT.md](ECS_AI_DOCUMENT_COMPLETENESS_REPORT.md) | Coverage %, missing areas, enhancements, Phase 2 & 3 roadmaps |
| 9 | [ECS_AI_LIFECYCLE_REFERENCE.md](ECS_AI_LIFECYCLE_REFERENCE.md) | Consolidated local/cloud/hybrid + prompt→embedding→RAG→governance→testing→monitoring lifecycle thread (Enterprise Knowledge Completion Phase 14) |

---

## Key code anchors

| Concern | File:line |
|---|---|
| Provider abstraction + registry | `ecs_platform/llm_engine/provider.py:30-246` |
| Local (Ollama) provider, keyless | `ecs_platform/llm_engine/provider.py:157-227` |
| LLM config (default ollama / qwen3:8b / nomic-embed) | `config/llm.yaml:7-9` |
| Vector store (pgvector, dim 768) | `ecs_platform/vectorstore/pgvector_store.py:97-101`, `config/vectorstore.yaml` |
| RAG generate / fallback | `ecs_platform/rag.py:642-653`, `ecs_platform/governance.py:709-743` |
| Deterministic chatbot | `modules/shared/services/chatbot_engine.py:683-707` |
| Frameworks catalog (15) | `modules/frameworks/engines/framework_catalog.py:740-756` |
| Roles (9 canonical) | `app/auth/roles.py:36-64` |
| Logins (12) | `modules/executive_overview/templates/login.html:24-37` |
| Connectors registry (12) | `ecs_platform/connectors/factory.py:12-25` |

---

## Success-criteria coverage

| Required "every X assessed" | Document |
|---|---|
| Every login | Phase 4 / 12 |
| Every persona | Phase 4 / 12 |
| Every application | Phase 5 / 12 |
| Every module | Phase 3 / 12 |
| Every framework | Phase 3 / 12 |
| Every connector | Phase 6 / 12 |
| Every dashboard | Phase 3 / 12 |
| Every report | Phase 12 |
| Every workflow | Phase 12 |
| Every drilldown | Phase 12 |

## Gaps surfaced (definition gaps, NOT AI-runtime gaps)

- Frameworks not in catalog: **MBSS, Middleware Baselining**.
- Applications not in catalog: **LMS, Authentication Services, Middleware (as app)**; Merchant
  Acquiring → only "Merchant Portal".
- Personas not modeled as roles: **Audit Manager, Governance Owner, Risk Owner, Evidence Owner,
  Reviewer, Approver**.
- SaaS connectors needing non-AI egress in air-gap: **Teams, Prisma Cloud, Figma**.

None of these block local-LLM operation. Remediation is out of scope for this (no-code) assessment.
