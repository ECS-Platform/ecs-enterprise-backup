# ECS Local vs Cloud LLM Decision Matrix

**Type:** Architecture decision documentation. **No code changed.** **Grounding:** `config/llm.yaml`, `ecs_platform/llm_engine/provider.py` (5-provider abstraction), `ecs_platform/rag.py`, `config/vectorstore.yaml`. Inferred/estimate content (cost, latency) is labeled **[estimate]** — ECS ships no measured benchmark.

> **Bottom line:** ECS is **provider-agnostic and defaults to a local, keyless Ollama model** (`qwen3:8b` + `nomic-embed-text` → pgvector). Cloud is opt-in via one env var (`ECS_LLM_PROVIDER`). For a regulated bank, **local-first** is the recommended default; cloud/hybrid are available without code change.

---

## 1. What ECS actually implements

| Capability | Implementation | Evidence |
|---|---|---|
| Provider abstraction | `get_provider()` resolves `ollama \| gemini \| openai \| azure_openai \| claude` | `provider.py:230-246` |
| Default provider | **Ollama (local, keyless)** | `config/llm.yaml:7`, `provider.py:157-177` |
| Models | `qwen3:8b` (gen), `nomic-embed-text` (embed, dim 768) | `llm.yaml:8-9`, `vectorstore.yaml:5` |
| Vector store | pgvector (also chroma/milvus by config) | `vectorstore.yaml:3`, `pgvector_store.py` |
| Switch provider | env-only, no code change | `ECS_LLM_PROVIDER` |
| Grounding guard | refuse w/o evidence; require citations | `rag.py:637-640`, `prompt_builder.py:7-18` |

---

## 2. Local LLM capabilities (Ollama / qwen3:8b)

| Dimension | Capability |
|---|---|
| Deployment | On-prem, **keyless**, host daemon `:11434`; container reaches via `host.docker.internal` |
| Data egress | **None** — prompts + evidence stay on-prem |
| Cost | No per-token cost; **[estimate]** capex = GPU/host only |
| Models | Qwen3, Llama, Mistral, Phi, Gemma, DeepSeek (any Ollama model) |
| Embeddings | `nomic-embed-text` (local) → pgvector |
| Latency | **[estimate]** higher first-token (cold start mitigated by `keep_alive=30m`, `warm()`) |
| Quality | **[estimate]** strong for grounded GRC summarization; below frontier cloud on complex reasoning |
| Air-gap | ✅ Fully supported (no external calls) |
| Scaling | Vertical (bigger host/GPU) or remote/in-cluster Ollama (`OLLAMA_URL`) |

## 3. Cloud LLM capabilities (Gemini / OpenAI / Azure OpenAI / Claude)

| Dimension | Capability |
|---|---|
| Deployment | Managed API; requires `*_API_KEY` |
| Data egress | Prompts + retrieved evidence leave the bank's boundary — **data-classification gate required** |
| Cost | **[estimate]** per-token opex; scales with usage |
| Quality | **[estimate]** frontier reasoning; larger context windows |
| Latency | **[estimate]** low + elastic; no local GPU |
| Air-gap | ❌ Not possible (external network) |
| Embeddings | Gemini/OpenAI embeddings (Claude has none — `provider.py:153-154`) |
| Ops burden | Low infra; high vendor/contract/DPA governance |

## 4. Hybrid model

ECS supports hybrid **operationally** (config-selected provider; switchable per environment). Patterns:

| Pattern | How | When |
|---|---|---|
| Local default + cloud burst | Default `ollama`; switch `ECS_LLM_PROVIDER=gemini` for heavy tasks/environments | Cost/quality balance |
| Local embeddings + cloud generation | Local `nomic-embed-text` keeps evidence vectors on-prem; cloud only sees retrieved snippets | Reduce egress surface |
| Local prod + cloud dev/UAT | Per-environment provider | Faster iteration off-prod |
| Sensitivity routing **[roadmap]** | Route by data classification (not a runtime feature today) | Future Phase 2 |

> Note: today the provider is a **single global selection** per deployment. Per-request/per-classification routing is a **documented enhancement**, not shipped.

## 5. Banking suitability

| Criterion | Local | Cloud | Hybrid |
|---|:--:|:--:|:--:|
| Data residency / sovereignty | ✅ Best | ⚠️ DPA-dependent | ✅ Good |
| RBI / on-prem mandate fit | ✅ | ❌/⚠️ | ✅ |
| Auditability of AI I/O | ✅ on-prem logs | ⚠️ vendor logs | ✅ |
| Frontier reasoning quality | ⚠️ | ✅ | ✅ |
| Cost predictability | ✅ fixed | ⚠️ usage | ✅ |
| Time-to-value | ✅ (already default) | ✅ | ✅ |

## 6. Cost comparison **[estimate]**

| Factor | Local | Cloud |
|---|---|---|
| Model usage | ₹0/token (fixed host capex) | per-token opex |
| Infra | GPU/host + ops | none |
| Scaling cost | step (new hardware) | linear (usage) |
| Best for | steady, high-volume, sensitive | spiky, low-volume, non-sensitive |

## 7. Security comparison

| Control | Local | Cloud |
|---|---|---|
| Evidence leaves boundary | ❌ never | ✅ yes (snippets) |
| Key management | none (keyless) | API keys in vault/env |
| Attack surface | host daemon only | + vendor API, network |
| RBAC pre-filter (ECS) | ✅ `rag.py:_rbac_filter` | ✅ same (applied before model) |
| Prompt-injection exposure | grounded-only context | grounded-only context |

## 8. Privacy comparison

| Aspect | Local | Cloud |
|---|---|---|
| PII/evidence exposure to third party | none | possible (review classification) |
| Training-on-data risk | none | vendor-policy dependent |
| Right-to-erasure simplicity | high (on-prem) | vendor-dependent |

## 9. Air-gap suitability

| Mode | Verdict |
|---|---|
| **Local (Ollama)** | ✅ Fully air-gappable — keyless, no egress; models pre-pulled |
| Cloud | ❌ Requires internet |
| Hybrid (local-only in air-gap) | ✅ Run local provider; cloud disabled |

Note: some **non-AI** connectors (Teams, Prisma Cloud, Figma) need egress; that is independent of the LLM and out of scope here (see README gaps).

---

## 10. Recommendation matrix

| Scenario | Recommended mode | Rationale |
|---|---|---|
| Production, regulated banking data | **Local (Ollama qwen3:8b)** | Data residency, audit, fixed cost, air-gap |
| Air-gapped / on-prem mandate | **Local only** | No egress possible |
| Dev/UAT iteration | **Cloud or local** | Speed; non-prod data |
| Heavy reasoning / long context (non-sensitive) | **Cloud (Gemini/OpenAI)** | Frontier quality |
| Mixed sensitivity, cost-conscious | **Hybrid** (local default, cloud burst) | Balance |
| Embeddings for sensitive evidence | **Local embeddings always** | Keep vectors on-prem even if generation is cloud |

**ECS default and recommendation for banking: local-first.** It is already the shipped default and requires no change to operate fully on-prem; cloud and hybrid remain one env var away.

---

**Cross-links:** [Architecture Reference](ECS_AI_ARCHITECTURE_REFERENCE.md) · [Security Architecture](ECS_AI_SECURITY_ARCHITECTURE.md) · [Use Case Coverage Matrix](ECS_LLM_USE_CASE_COVERAGE_MATRIX.md) · [Banking AI Architecture](ECS_BANKING_AI_ARCHITECTURE.md) · [Model Compatibility](ECS_MODEL_COMPATIBILITY_MATRIX.md)
