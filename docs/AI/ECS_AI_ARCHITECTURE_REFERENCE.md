# ECS AI Architecture Reference

**Type:** Architecture documentation. **No code changed.** Grounding in `ecs_platform/llm_engine/` (`provider.py`, `generator.py`, `retriever.py`, `prompt_builder.py`), `ecs_platform/rag.py`, `ecs_platform/vectorstore/`, `config/llm.yaml`, `config/vectorstore.yaml`.

---

## 1. Layered architecture

```
┌──────────────────────────────────────────────────────────────┐
│ UI / Routes:  /mvp/ai-assistant  /api/platform/assistant       │
│               /mvp/ai-ops-assistant  /mvp/ai-sdlc/*  /mvp/ai-*  │
├──────────────────────────────────────────────────────────────┤
│ RAG Orchestrator (ecs_platform/rag.py)                          │
│   RBAC filter → Retrieval → Enrich(reuse+crosswalk)            │
│   → Governance facts → Grounding gate → Generate → Cite        │
├───────────────┬───────────────────────┬───────────────────────┤
│ Provider      │ Vector Store          │ Repository (governance) │
│ abstraction   │ pgvector              │ PostgreSQL evidence      │
│ (llm_engine)  │ (vectorstore/)        │ + crosswalk + audit_log  │
├───────────────┴───────────────────────┴───────────────────────┤
│ Models: Ollama qwen3:8b (gen) · nomic-embed-text (embed, 768)   │
│ Optional cloud: Gemini · OpenAI · Azure OpenAI · Claude         │
└──────────────────────────────────────────────────────────────┘
```

## 2. Ollama (local runtime)

- Keyless local daemon on `:11434`; container reaches host via `host.docker.internal` (compose `extra_hosts`). Override with `OLLAMA_URL` for remote/in-cluster.
- `OllamaProvider` (`provider.py:157-227`): `POST /api/chat` (generation), `POST /api/embeddings` (embeddings), `keep_alive` residency, `warm()` to pre-load, `configured()` true whenever a base URL is set (no key).
- Strips `<think>…</think>` reasoning blocks (`_strip_think`).

## 3. Qwen3 (default model)

- `qwen3:8b` (`llm.yaml:8`, `OLLAMA_MODEL`). Reasoning-capable; ECS removes its think-blocks for clean audit output.
- Swappable to any Ollama model (Llama/Mistral/Phi/Gemma/DeepSeek) — see [Model Compatibility](ECS_MODEL_COMPATIBILITY_MATRIX.md). Generation params: `temperature=0.1`, `num_predict=max_output_tokens=2048`.

## 4. Embeddings

- Default `nomic-embed-text` (local), dim **768** (`ECS_VECTOR_DIM`). Generated via `provider.embed()` (Ollama `/api/embeddings`).
- Cloud embeddings available (Gemini `text-embedding-004`=768, OpenAI). **Claude has no embeddings** (`provider.py:153-154`) — pair with a separate embedding provider.
- Chunking: `chunk_size=1000`, `chunk_overlap=150` (`vectorstore.yaml:8-10`).

## 5. PGVector (vector store)

- Provider `pgvector` (also `chroma`, `milvus` by config). DB `ecs_vectors`, table `evidence_embeddings`, collection `ecs_evidence_chunks`.
- `pgvector_store.py` implements init/upsert/search (cosine). Upsert keyed on `chunk_id` → idempotent re-index.
- Counts/health surfaced via `rag_status()` (`vector_count`, `indexed_pct`).

## 6. RAG pipeline (`rag.py:599-656`)

1. **RBAC filter** — `_rbac_filter` maps UI role → `rbac.yaml` role; `policy.authorize(read_evidence)` returns scope filter. Restricted role w/o assignments → deny.
2. **Retrieval** — `_retrieve`: vector-first (`provider.embed(query)` → `store.search` with app/source filters); deterministic repository fallback (framework/status/app/source + scope-aware SQL).
3. **Enrichment** — `_enrich`: attaches source/timestamp + controls + framework refs via `CONTROL_CROSSWALK`.
4. **Governance facts** — `_governance_facts`: injects computed portfolio/coverage/gap/reuse metrics.
5. **Grounding gate** — if no evidence and no facts → return `NO_EVIDENCE_MESSAGE` (before any model call).
6. **Generate** — `provider.generate(prompt, system=SYSTEM_PROMPT)`.
7. **Cite** — returns answer + citations + rbac + retrieval_mode + facts + model/provider.

## 7. Retrieval layer

- **Semantic:** pgvector cosine over chunked evidence + governance docs.
- **Deterministic fallback:** SQL across `evidence`/`evidence_reviews`/`control_framework_crosswalk` with RBAC scope (`rag.py:476-495`).
- **Indexed corpus** (`reindex_evidence` + `_governance_documents`): evidence, applications, control catalog + crosswalk, evidence reviews/observations, lineage edges, last 500 audit events.
- **Incremental:** content-hash per chunk; unchanged chunks skipped; batches of 50.

## 8. Provider abstraction

- `LLMProvider` ABC with `generate()` + `embed()`; `_PROVIDERS` registry (`ollama|gemini|openai|azure_openai|claude`); `get_provider()` reads `config/llm.yaml`.
- Credential-optional construction; `configured()` gates network calls; lazy SDK/HTTP via `urllib`. Switching providers is **config-only**.
- `generator.py` / `retriever.py` provide engine-level generate/retrieve helpers around the provider + vector store.

## 9. Hybrid LLM architecture

- Single global provider per deployment, selected by `ECS_LLM_PROVIDER`. Hybrid achieved by per-environment selection (local prod, cloud dev) and the local-embeddings + cloud-generation split.
- Per-request/classification routing is a documented **target** (not shipped) — see [Decision Matrix](ECS_LOCAL_VS_CLOUD_LLM_DECISION_MATRIX.md) §4.

## 10. Cloud LLM integration

- Gemini (`v1beta generateContent`/`embedContent`), OpenAI (`chat/completions`,`embeddings`), Azure OpenAI (deployment URL + `api-version`), Claude (`v1/messages`, no embeddings). Keys via `*_API_KEY` env (`resolve_secret`).
- Same RAG pipeline, grounding gate, citations, and RBAC apply regardless of provider.

## 11. AI governance controls (in architecture)

- **Pre-model RBAC** scope filtering (data minimization).
- **Grounding gate** + **mandatory citations** (anti-hallucination).
- **`refuse_without_evidence: true`**, **`require_citations: true`** (`llm.yaml:41-42`).
- **Think-block stripping** (no exposed CoT).
- **AI governance posture** (6 dimensions: data privacy, model risk, prompt safety, bias, audit trail, human-in-loop) via `ecs_ai_governance_drilldowns`.
- **AI SDLC gates** (`ai_sdlc_*`) for governed AI delivery.
- **Audit log** indexed for traceability.

---

**Cross-links:** [Functional Requirements](ECS_AI_FUNCTIONAL_REQUIREMENTS.md) · [Security Architecture](ECS_AI_SECURITY_ARCHITECTURE.md) · [Governance Operating Model](ECS_AI_GOVERNANCE_OPERATING_MODEL.md) · [Model Abstraction](ECS_MODEL_ABSTRACTION_ARCHITECTURE.md) · [Embedding Strategy](ECS_EMBEDDING_STRATEGY.md) · [Banking AI Architecture](ECS_BANKING_AI_ARCHITECTURE.md)
