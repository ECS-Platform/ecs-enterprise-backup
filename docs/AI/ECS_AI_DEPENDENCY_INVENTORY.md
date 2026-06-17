# ECS AI Dependency Inventory (Phase 1)

**Release tag:** `ecs-local-llm-readiness-enterprise-v1`
**Method:** Static repository scan of `/Users/nikhil/Documents/ECS`. Every claim is file:line grounded. Nothing is inferred or invented.
**Scope rule honored:** Documentation only. No production code, providers, or functionality were modified.

---

## 0. Executive Finding

> **ECS is already local-LLM-capable today.** It ships a config-selected provider abstraction
> (`ecs_platform/llm_engine/provider.py`) whose effective default is **Ollama (local, keyless)**
> running `qwen3:8b`, with `nomic-embed-text` for embeddings into a local **pgvector** store.
> Cloud providers (OpenAI, Anthropic/Claude, Gemini, Azure OpenAI) are **optional** alternatives
> selected by env/config. No cloud LLM is required at runtime.

| Dimension | State |
|---|---|
| Provider abstraction exists | **Yes** — `ecs_platform/llm_engine/provider.py` |
| Default provider | **Ollama (local)** via `config/llm.yaml:7` (`${ECS_LLM_PROVIDER:-ollama}`) |
| Default model | **`qwen3:8b`** (`config/llm.yaml:8`) |
| Default embedding model | **`nomic-embed-text`** (`config/llm.yaml:9`) |
| Vector store | **pgvector** (local Postgres) — `config/vectorstore.yaml`, `ecs_platform/vectorstore/pgvector_store.py` |
| Cloud LLM required at runtime? | **No** (cloud is optional) |
| Heavy ML SDKs installed | **No** — inference is stdlib `urllib.request` only |

---

## 1. Provider Usage Matrix

The real inference layer is `ecs_platform/llm_engine/provider.py`. SDKs are **not** used; all calls
are stdlib HTTP (`urllib.request`).

| Provider | Class | Endpoint(s) | Auth env var(s) | Locality | Lines |
|---|---|---|---|---|---|
| **Ollama** | `OllamaProvider` | `{OLLAMA_URL}/api/chat`, `/api/embeddings` | none (keyless) | **Local / air-gap-capable** | `provider.py:157-227` |
| OpenAI | `OpenAIProvider` | `https://api.openai.com/v1/chat/completions`, `/embeddings` | `OPENAI_API_KEY` | Cloud | `provider.py:96-119` |
| Azure OpenAI | `AzureOpenAIProvider` | `{AZURE_OPENAI_ENDPOINT}/openai/deployments/{dep}/chat/completions` | `AZURE_OPENAI_API_KEY` + endpoint/deployment | Cloud / private | `provider.py:122-134` |
| Anthropic (Claude) | `ClaudeProvider` | `https://api.anthropic.com/v1/messages` | `ANTHROPIC_API_KEY` | Cloud | `provider.py:137-154` |
| Google Gemini | `GeminiProvider` | `https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent` / `:embedContent` | `GEMINI_API_KEY` | Cloud | `provider.py:63-93` |

Provider registry and selection:

```230:246:ecs_platform/llm_engine/provider.py
_PROVIDERS = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "azure_openai": AzureOpenAIProvider,
    "claude": ClaudeProvider,
    "ollama": OllamaProvider,
}

def get_provider(config: dict[str, Any] | None = None) -> LLMProvider:
    cfg = (config or load_llm_config()).get("llm", {})
    name = cfg.get("provider", "gemini")
```

> **Default nuance:** the in-code fallback string in `get_provider` is `"gemini"`, but the
> effective runtime default is **Ollama** because `config/llm.yaml:7` sets
> `provider: ${ECS_LLM_PROVIDER:-ollama}` and `load_llm_config()` supplies that YAML. With no env
> overrides, ECS runs fully local. (Recommendation in the migration plan: align the code fallback
> to `ollama` to remove ambiguity.)

### Providers requested in the brief — presence in code

| Requested | Status | Evidence |
|---|---|---|
| OpenAI | **Implemented** | `provider.py:96-119` |
| Anthropic | **Implemented** | `provider.py:137-154` |
| Gemini | **Implemented** | `provider.py:63-93` |
| Azure OpenAI | **Implemented** | `provider.py:122-134` |
| Ollama | **Implemented (default)** | `provider.py:157-227` |
| HuggingFace | **Not present** | no import/endpoint found |
| Qwen | **As a model, not a provider** | `qwen3:8b` default model run *through Ollama* (`config/llm.yaml:8`); `<think>` stripping for qwen at `provider.py:18-23` |
| Llama | **As a model via Ollama** | only as model name strings; no dedicated provider |
| DeepSeek | **As a model via Ollama** | only `<think>` handling (`provider.py:22`); no dedicated provider |
| Mistral | **Not present** | no provider/import |
| Gemma | **As a model via Ollama** | model-name only; no dedicated provider |

> Qwen / Llama / DeepSeek / Mistral / Gemma are **Ollama-served models**, not separate API
> providers. Running them is a configuration change (`ECS_LLM_MODEL=…`), not new code.

---

## 2. Embedding APIs

| Path | Mechanism | Lines |
|---|---|---|
| Ollama embeddings (default) | `POST {OLLAMA_URL}/api/embeddings`, model `nomic-embed-text` | `provider.py:195-206` |
| OpenAI embeddings | `POST /v1/embeddings` | `provider.py` (OpenAI `embed`) |
| Gemini embeddings | `:embedContent` | `provider.py:63-93` |
| RAG indexing | `reindex_evidence()` embeds chunks via configured provider | `ecs_platform/rag.py:259-293` |
| Ingestion indexing | `_index()` | `ecs_platform/ingestion.py:203-231` |

**Heuristic "semantic" search (NOT embeddings):** `modules/governance/engines/search_module.py:119-137`
(`_semantic_score()` is substring/word-overlap scoring, labeled "Semantic" at ≥60). Documented so it
is not mistaken for vector search.

---

## 3. Vector DB Integrations

| Backend | Status | Evidence |
|---|---|---|
| **pgvector (Postgres)** | **Implemented & default** | `ecs_platform/vectorstore/pgvector_store.py` (cosine `<=>` search, table `evidence_embeddings`, dim 768); `config/vectorstore.yaml`; `pgvector/pgvector:pg16` in `docker-compose.yml:144-153` |
| Chroma | Config placeholder, **not implemented** | `config/vectorstore.yaml:20-25`; factory raises (`vectorstore/factory.py:15-19`) |
| Milvus | Config placeholder, **not implemented** | same |
| Pinecone / Weaviate / Qdrant | **Not present** | no client libs/imports |

Vector search SQL:

```97:101:ecs_platform/vectorstore/pgvector_store.py
        sql = (
            f"SELECT chunk_id, evidence_uid, text, metadata, "
            f"1 - (embedding <=> %s::vector) AS score "
            f"FROM {self._table} {filter_clause} "
            f"ORDER BY embedding <=> %s::vector LIMIT %s"
```

---

## 4. External Inference APIs (non-LLM)

The "AI assistants" used in the demo UX are **deterministic, not external**:

| Component | External call? | Evidence |
|---|---|---|
| Showcase chatbot (`/mvp/chat`) | **No** — keyword/intent routing over in-memory state | `modules/shared/services/chatbot_engine.py:683-707`; `chatbot_enhanced.py:102-113` |
| AI SDLC / AI Governance UI | **No** — mock/demo data | `modules/ai_sdlc/engines/ai_sdlc_governance_mock.py:1-5`; `ai_sdlc_governance_service.py:1` |
| Platform RAG assistant (`/api/platform/assistant`) | **Optional** — calls configured provider when set, else deterministic fallback | `ecs_platform/rag.py:642-653`; fallback `ecs_platform/governance.py:709-743` |

---

## 5. Dependency Manifest

Only manifest: `requirements.txt` (12 lines). **No** `openai`, `anthropic`, `google-generativeai`,
`transformers`, `torch`, `sentence-transformers`, `faiss`, `langchain`, `llama-cpp-python`, `ollama`
(python client), `chromadb`, `pinecone`, `weaviate`, `qdrant`, `cohere`, `mistralai`, `httpx`,
`requests`, `numpy`, or `tiktoken` are present.

```1:12:requirements.txt
fastapi
uvicorn
jinja2
python-multipart
openpyxl
psycopg2-binary
# Environment loading (.env -> os.environ) for demo-mode flags at startup
python-dotenv
# ECS platform foundation
pyyaml
# Authentication foundation (Phase 1: Azure AD / OIDC / JWT validation)
pyjwt[crypto]
```

**Implication for air-gap:** because inference is stdlib HTTP, ECS has **no heavyweight Python ML
dependency to vendor**. For local LLM the only runtime dependency is a reachable **Ollama daemon**
(separate process/container) + a local **pgvector** Postgres — both deployable on-prem/air-gapped.

---

## 6. AI-Related Configuration & Flags

| Variable | Default | Source |
|---|---|---|
| `ECS_LLM_PROVIDER` | `ollama` | `config/llm.yaml:7` |
| `ECS_LLM_MODEL` | `qwen3:8b` | `config/llm.yaml:8` |
| `ECS_EMBEDDING_MODEL` | `nomic-embed-text` | `config/llm.yaml:9` |
| `ECS_LLM_TEMPERATURE` / `_MAX_TOKENS` / `_TIMEOUT` | 0.1 / 2048 / 180 | `config/llm.yaml:10-12` |
| `OLLAMA_URL` / `OLLAMA_MODEL` | `http://host.docker.internal:11434` / `qwen3:8b` | `config/llm.yaml:20-21` |
| `ECS_OLLAMA_KEEP_ALIVE` | `30m` | `config/llm.yaml:14`, `provider.py:168-171` |
| `GEMINI_API_KEY` / `OPENAI_API_KEY` / `AZURE_OPENAI_*` / `ANTHROPIC_API_KEY` | unset | `config/llm.yaml:23-35`, `docker-compose.yml:72-75` |
| `ECS_VECTOR_PROVIDER` / `ECS_VECTOR_DIM` | `pgvector` / `768` | `config/vectorstore.yaml:4-5` |
| `DEMO_MODE` | bypasses auth/RBAC (non-LLM) | `app/auth/demo.py:30` |

Startup logging confirms graceful local/offline behavior: if a provider is unconfigured, the
assistant logs *"LLM-RAG disabled: provider not configured (assistant uses deterministic fallback)"*
(`app/main.py:150-168`).

---

## 7. Known Doc Drift (to correct in repo over time — not changed here)

`ECS_ARCHITECTURE_BASELINE.md:768` still states *"❌ Real LLM integration (no OpenAI / Anthropic /
Bedrock call)"*. This is **outdated**: `ecs_platform/llm_engine/provider.py` implements real HTTP
calls to OpenAI, Anthropic, Gemini, Azure OpenAI, and Ollama. Flagged for a future doc-sync (no code
change performed as part of this assessment).

---

## 8. Phase 1 Conclusion

ECS's AI dependency posture is **favorable for local/air-gapped deployment**: a working provider
abstraction already defaults to local Ollama + local pgvector, cloud is opt-in, and there are no
heavy ML packages to ship. The remaining work is **not** "build local LLM support" — it is
**hardening, validation, benchmarking, and rollout** (covered in Phases 7–13).
