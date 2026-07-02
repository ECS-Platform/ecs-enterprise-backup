# ECS Local Model Compatibility Matrix (Phase 9)

**Release tag:** `ecs-local-llm-readiness-enterprise-v1`

**Compatibility basis (code-grounded):** ECS talks to local models via **Ollama's REST API**
(`POST /api/chat`, `POST /api/embeddings`) in `OllamaProvider` (`provider.py:157-206`). Therefore
**any model Ollama can serve is technically compatible with ECS** — selection is a config value
(`ECS_LLM_MODEL`), not code. The provider already strips `<think>…</think>` reasoning blocks
(`provider.py:18-23`), making reasoning models (qwen3, deepseek-r1) render cleanly.

> **Note on quality ratings:** The functional/compatibility columns are derived from the ECS
> integration contract (chat + embeddings over Ollama) and each model's documented capabilities.
> Quality tiers are **reference guidance**, not live ECS benchmark measurements. See the Performance
> Benchmark doc for the measurement methodology to run in a real environment.

---

## 1. Generation-model compatibility (served via OllamaProvider)

| Model | Ollama tag | ECS chat API compat | `<think>` handled | Typical RAM (Q4) | Governance-text quality (reference) | Recommended ECS tier |
|---|---|---|---|---|---|---|
| **Qwen3 8B** (default) | `qwen3:8b` | ✅ `/api/chat` | ✅ (`provider.py:22`) | ~6–8 GB | High; strong instruction following | **Default / UAT→Prod** |
| Llama 3 8B | `llama3:8b` | ✅ | n/a | ~6–8 GB | High; well-rounded | Prod-candidate alt |
| DeepSeek-R1 (distill 7B/8B) | `deepseek-r1:7b` | ✅ | ✅ reasoning stripped | ~6–9 GB | High reasoning; verbose | Analysis/UAT |
| Mistral 7B | `mistral` | ✅ | n/a | ~5–7 GB | Good; fast | Throughput tier |
| Gemma 2 9B | `gemma2:9b` | ✅ | n/a | ~7–9 GB | Good–High | Prod-candidate alt |
| Qwen3 14B / Llama3 70B | `qwen3:14b` / `llama3:70b` | ✅ | ✅/n/a | 12 GB / 40+ GB | Higher quality | High-end (GPU) |

## 2. Embedding-model compatibility (served via OllamaProvider.embed)

| Model | Ollama tag | Dim | ECS `ECS_VECTOR_DIM` change? | Tier |
|---|---|---|---|---|
| **nomic-embed-text** (default) | `nomic-embed-text` | 768 | No (matches default) | **Default** |
| bge-large | `bge-large` | 1024 | Yes → 1024 + reindex | Quality |
| bge-small | `bge-small` | 384 | Yes → 384 + reindex | Scale |
| mxbai-embed-large | `mxbai-embed-large` | 1024 | Yes → 1024 + reindex | Quality alt |

## 3. Compatibility verdicts

| Model | Compatible with ECS? | Notes |
|---|---|---|
| Ollama (runtime) | ✅ **Yes — native** | The local provider IS the Ollama client (`provider.py:157-227`) |
| Qwen3:8b | ✅ **Yes — default** | `config/llm.yaml:8` |
| Llama3:8b | ✅ Yes | config change only |
| DeepSeek-R1 | ✅ Yes | reasoning blocks already stripped |
| Mistral | ✅ Yes | config change only |
| Gemma | ✅ Yes | config change only |

**No model requires code changes** to integrate — only `ECS_LLM_MODEL` (and, for embeddings, a
matching `ECS_VECTOR_DIM` + reindex).

## 4. Validation procedure (to run in target environment — no code change)

1. `ollama pull qwen3:8b && ollama pull nomic-embed-text`
2. Set `ECS_LLM_PROVIDER=ollama`, `ECS_LLM_MODEL=qwen3:8b`, `OLLAMA_URL=http://<host>:11434`.
3. Check `GET /api/platform/rag/status` and `/api/platform/rag/llm` (status routes from `app/routes_governance.py`).
4. Warm models (`OllamaProvider.warm()` path) to avoid cold-start.
5. Ask the assistant a grounded governance question via `/api/platform/assistant`; confirm
   `"mode": "rag"`, `"grounded": true` (`rag.py:642-653`).
6. Reindex evidence and confirm pgvector returns scored results.

## 5. Conclusion

ECS is **compatible with all evaluated local models** out of the box via Ollama. Qwen3:8b +
nomic-embed-text is the **zero-change default**. Swapping models is configuration, not engineering.
