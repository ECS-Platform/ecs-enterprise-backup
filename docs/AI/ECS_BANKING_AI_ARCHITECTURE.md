# ECS Banking AI Architecture & Deployment Readiness (Phase 11)

**Release tag:** `ecs-local-llm-readiness-enterprise-v1`

---

## 1. Deployment topologies (all supported by current design)

Because inference is stdlib HTTP to a config-selected provider (default **local Ollama**) and the
vector store is local **pgvector**, ECS supports every target topology:

| Topology | LLM | Embeddings | Vector store | Internet needed for AI? |
|---|---|---|---|---|
| **Air-gapped** | Ollama on-prem (qwen3:8b) | Ollama nomic-embed-text | pgvector (local PG) | **No** |
| **On-prem** | Ollama on-prem | Ollama | pgvector | **No** |
| **Private cloud** | Ollama in VPC, or Azure OpenAI (private) | Ollama / Azure | pgvector | No / private only |
| **UAT** | Ollama (single node) | Ollama | pgvector | No |
| **Production** | Ollama (GPU node[s], keep-alive) | Ollama | pgvector | No |

Air-gap enablers in code: keyless `OllamaProvider` (`provider.py:173-177`), credential-optional
construction (`provider.py:1-6`), deterministic fallback when provider unset
(`app/main.py:150-168`, `governance.py:709-743`), local pgvector default (`config/vectorstore.yaml`).

---

## 2. Reference air-gapped architecture

```
                       Bank private network (no internet egress for AI)
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │  ECS App (FastAPI, uvicorn)                                                     │
 │   • Deterministic governance/compliance/risk/audit engines (no model)          │
 │   • RAG assistant  ── provider.generate() ──┐                                   │
 │   • Evidence index ── provider.embed() ─────┼──────────────┐                    │
 └─────────────────────────────────────────────┼──────────────┼────────────────-─┘
                                                ▼              ▼
                                   ┌────────────────────┐  ┌──────────────────────┐
                                   │ Ollama (GPU node)  │  │ Postgres + pgvector   │
                                   │ qwen3:8b           │  │ evidence_embeddings   │
                                   │ nomic-embed-text   │  │ (dim 768)             │
                                   └────────────────────┘  └──────────────────────┘
        Connectors (Jira/Confluence/ServiceNow/SonarQube/Gitea/…) on the same private network
```

---

## 3. Data-sensitivity → deployment suitability

Classification of ECS data domains for **local LLM** processing:

| Data domain | Sensitivity | Local LLM verdict | Rationale |
|---|---|---|---|
| Audit Evidence | High | **Production Ready (local only)** | Must not leave bank network; local keeps it in-perimeter |
| Governance Data | High | **Production Ready (local only)** | Same |
| Compliance Data | High | **Production Ready (local only)** | Regulatory residency |
| Risk Data | High | **Production Ready (local only)** | Sensitive findings |
| AI SDLC Data | Medium | **UAT→Production Ready (local)** | Currently mock; local-safe |
| Executive Reporting | Medium | **Production Ready (local)** | Aggregated; local-safe |

> For all high-sensitivity domains, **cloud LLM is "Not Recommended"** without an explicit
> data-residency/DPA exception. Local Ollama is the compliant default.

---

## 4. Provider readiness classification (banking)

| Provider | Banking classification | Justification |
|---|---|---|
| **Ollama (local, qwen3:8b)** | **Production Ready** | In-perimeter, keyless, default; deterministic fallback if down |
| Ollama (llama3/mistral/gemma/deepseek-r1) | **UAT Ready → Prod-candidate** | Compatible; validate per §Phase 9/10 |
| Azure OpenAI (private) | **UAT Ready** (Prod with residency sign-off) | Private networking possible; still external dependency |
| OpenAI / Gemini / Anthropic (public) | **Demo Only / Not Recommended for sensitive data** | Public egress; data-residency risk |

---

## 5. Banking controls that this architecture supports

| Control concern | How ECS meets it | Evidence |
|---|---|---|
| Data residency / no egress | Local Ollama + pgvector default | `config/llm.yaml:7`, `config/vectorstore.yaml` |
| Explainability / reproducibility | Most AI features are deterministic | feature inventory (Phase 2) |
| Graceful degradation | Deterministic fallback when LLM unavailable | `rag.py:642-648`, `governance.py:709-743` |
| Access control over AI surface | RBAC governs pages/data; provider is global | persona matrix (Phase 4) |
| Auditability | AI SDLC posture/prompt registry (mock today) provides governance scaffolding | `ai_sdlc_governance_mock.py` |
| Secret hygiene | Keys via env/secret resolver; local needs none | `config/loader.py:140-142`, `provider.py:173` |

---

## 6. Hardening checklist for production (recommendations — not applied here)

1. Pin Ollama model digests; vendor model blobs into the air-gapped registry.
2. GPU node sizing per Phase 10 benchmark; enable `ECS_OLLAMA_KEEP_ALIVE` (already supported).
3. Align code default provider to `ollama` (`provider.py:241`).
4. Add provider health to readiness probes; alert on fallback-mode.
5. Quality gate: run the Phase 10 harness on 20+ ECS prompts before sign-off.
6. If higher retrieval quality is needed, plan a bge-large reindex window (dimension change).

## 7. Conclusion

ECS's architecture is **banking-deployment ready for local LLM** across air-gapped, on-prem, private
cloud, UAT, and production. The compliant default (local Ollama + pgvector, deterministic fallback)
keeps all high-sensitivity data in-perimeter with no internet dependency for AI.
