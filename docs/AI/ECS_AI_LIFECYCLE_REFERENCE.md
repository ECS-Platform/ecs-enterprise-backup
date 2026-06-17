# ECS AI Lifecycle Reference (Consolidated)

**Type:** AI lifecycle consolidation + navigation. **No code/UI/DB changes.** **Purpose:** Phase-14 completion — single thread through Local/Cloud/Hybrid LLM, provider selection, and the prompt → embedding → RAG → governance → testing → monitoring lifecycle, **cross-linking the 30 authoritative `docs/AI/` documents** (no content duplication). **Grounding:** `ecs_platform/llm_engine/provider.py`, `rag.py`, `prompt_builder.py`, `vectorstore/pgvector_store.py`, `config/llm.yaml`.

---

## Lifecycle thread

```
Provider selection → Prompt build (RBAC scope) → Embedding (query+evidence)
→ Retrieval (pgvector + repo fallback) → Grounding gate → Generation w/ citations
→ Governance (registry/approval/posture) → Testing → Monitoring → Revalidation/Retirement
```

| Stage | What happens | Authoritative doc |
|---|---|---|
| **Local LLM** | Ollama `qwen3:8b` via `host.docker.internal`, keyless, `keep_alive` | [Architecture Reference](ECS_AI_ARCHITECTURE_REFERENCE.md), [Deployment](ECS_LOCAL_LLM_DEPLOYMENT_GUIDE.md) |
| **Cloud LLM** | Gemini/OpenAI/Azure/Claude providers (interface-complete) | [Decision Matrix](ECS_LOCAL_VS_CLOUD_LLM_DECISION_MATRIX.md), [Model Abstraction](ECS_MODEL_ABSTRACTION_ARCHITECTURE.md) |
| **Hybrid** | local-first; cloud fallback for heavy/long-context | [Decision Matrix](ECS_LOCAL_VS_CLOUD_LLM_DECISION_MATRIX.md) |
| **Provider selection** | `LLMProvider` ABC, config-driven, lazy SDK import | [Model Abstraction](ECS_MODEL_ABSTRACTION_ARCHITECTURE.md), [Compatibility Matrix](ECS_MODEL_COMPATIBILITY_MATRIX.md) |
| **Prompt lifecycle** | `SYSTEM_PROMPT` (evidence-only, `[E#]` citations, refuse-without-evidence), approval | [Governance Operating Model](ECS_AI_GOVERNANCE_OPERATING_MODEL.md), [Security](ECS_AI_SECURITY_ARCHITECTURE.md) |
| **Embedding lifecycle** | `nomic-embed-text` 768-dim; incremental reindex w/ `content_hash`; dim auto-migrate | [Embedding Strategy](ECS_EMBEDDING_STRATEGY.md) |
| **RAG lifecycle** | RBAC filter → retrieve → reuse/framework map → context → grounding gate → cite | [Architecture Reference](ECS_AI_ARCHITECTURE_REFERENCE.md) |
| **Use cases** | 28→100+ catalog, coverage matrices (persona/module/connector/app) | [Catalog V2](ECS_LOCAL_LLM_USE_CASE_CATALOG_V2.md), [Coverage Matrix](ECS_LLM_USE_CASE_COVERAGE_MATRIX.md) |
| **Governance** | use-case lifecycle, model/prompt approval, posture (6 dims), revalidation, retirement | [Governance Operating Model](ECS_AI_GOVERNANCE_OPERATING_MODEL.md), [AI Governance framework](../FRAMEWORKS/AI_GOVERNANCE.md) |
| **Testing** | grounding/citation/refusal tests, validation matrices | [Testing Guide](ECS_LOCAL_LLM_TESTING_GUIDE.md), [Universal Validation Matrix](ECS_LOCAL_LLM_UNIVERSAL_VALIDATION_MATRIX.md) |
| **Monitoring** | connectivity (`llm_connectivity()`), `rag_status()`, perf benchmarks, hallucination rate | [Operations Guide](ECS_LOCAL_LLM_OPERATIONS_GUIDE.md), [Performance Benchmark](ECS_AI_PERFORMANCE_BENCHMARK.md), [Production Monitoring](../operations/ECS_PRODUCTION_MONITORING_GUIDE.md) |

## Phase-14 coverage statement
All Phase-14 topics are **covered by existing `docs/AI/` documents** (see [AI README index](README.md) and [Completeness Report](ECS_AI_DOCUMENT_COMPLETENESS_REPORT.md)). This reference adds the unifying lifecycle thread and cross-navigation; no new AI capability is implied. Inferred/Phase-2 items (e.g., automated AI scheduler for reindex, scaled cloud fallback) are flagged in the respective docs.

## Cross-references
- AI index: [docs/AI/README.md](README.md)
- AI Governance framework: [../FRAMEWORKS/AI_GOVERNANCE.md](../FRAMEWORKS/AI_GOVERNANCE.md)
- Security: [ECS_AI_SECURITY_ARCHITECTURE.md](ECS_AI_SECURITY_ARCHITECTURE.md)
