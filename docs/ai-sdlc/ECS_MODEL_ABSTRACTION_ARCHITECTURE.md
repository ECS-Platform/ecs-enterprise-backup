# ECS Model Abstraction Architecture (Phase 8)

**Release tag:** `ecs-local-llm-readiness-enterprise-v1`

---

## 1. The abstraction already exists

ECS ships a provider abstraction in `ecs_platform/llm_engine/provider.py`. An abstract base defines
the contract; concrete providers implement HTTP calls; a registry + factory selects one by config.

```30:50:ecs_platform/llm_engine/provider.py
class LLMProvider(ABC):
    def __init__(self, cfg: dict[str, Any], provider_cfg: dict[str, Any]):
        ...
    def configured(self) -> bool:
        return bool(self.api_key())
    @abstractmethod
    def generate(self, prompt: str, *, system: str = "") -> str: ...
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...
```

```230:246:ecs_platform/llm_engine/provider.py
_PROVIDERS = {
    "gemini": GeminiProvider, "openai": OpenAIProvider,
    "azure_openai": AzureOpenAIProvider, "claude": ClaudeProvider,
    "ollama": OllamaProvider,
}
def get_provider(config=None):
    name = cfg.get("provider", "gemini")   # YAML default = ollama
```

### Current class hierarchy (as implemented)

```
LLMProvider (ABC)                      provider.py:30
├── GeminiProvider        (cloud)      provider.py:63
├── OpenAIProvider        (cloud)      provider.py:96
├── AzureOpenAIProvider   (cloud/priv) provider.py:122
├── ClaudeProvider        (cloud)      provider.py:137
└── OllamaProvider        (LOCAL)      provider.py:157   ← default via config
```

Contract methods every provider implements: `generate(prompt, system)`, `embed(texts)`,
`configured()`, `api_key()` (Ollama returns "" — keyless).

---

## 2. Mapping requested classes → ECS reality

The brief requests `AIProvider` with cloud + local subclasses. ECS's equivalent is `LLMProvider`.

| Requested class | ECS status | Notes |
|---|---|---|
| `AIProvider` (base) | **= `LLMProvider`** (`provider.py:30`) | Same role: abstract `generate`/`embed` |
| `OpenAIProvider` | **Implemented** | `provider.py:96` |
| `AnthropicProvider` | **Implemented as `ClaudeProvider`** | `provider.py:137` |
| `GeminiProvider` | **Implemented** | `provider.py:63` |
| `OllamaProvider` | **Implemented (default)** | `provider.py:157` |
| `QwenProvider` | **Not needed** — Qwen runs *through* `OllamaProvider` (`ECS_LLM_MODEL=qwen3:8b`) | model, not provider |
| `LlamaProvider` | **Not needed** — Llama via Ollama (`ECS_LLM_MODEL=llama3:8b`) | model, not provider |
| `DeepSeekProvider` | **Not needed** — DeepSeek via Ollama; `<think>` stripping already present (`provider.py:18-23`) | model, not provider |
| `MistralProvider` | **Not needed** — Mistral via Ollama (`ECS_LLM_MODEL=mistral`) | model, not provider |
| `GemmaProvider` | **Not needed** — Gemma via Ollama (`ECS_LLM_MODEL=gemma`) | model, not provider |

> **Architectural recommendation:** Do **not** create per-model provider classes (QwenProvider,
> LlamaProvider, etc.). The correct abstraction boundary is the **API protocol** (Ollama, OpenAI,
> Anthropic, Gemini, Azure), and the model is a *parameter* (`ECS_LLM_MODEL`). The existing design is
> already correct: one `OllamaProvider` serves Qwen/Llama/DeepSeek/Mistral/Gemma by model name. This
> matches the "do not refactor" constraint — no new classes are required for local LLM operation.

---

## 3. Selection & configuration flow

```
config/llm.yaml ──load_llm_config()──> get_provider()
   provider: ${ECS_LLM_PROVIDER:-ollama}        ecs_platform/config/loader.py
   model:    ${ECS_LLM_MODEL:-qwen3:8b}
        │
        ▼
   _PROVIDERS[name]  ──>  OllamaProvider(cfg, provider_cfg)   (default)
        │                         │
        ▼                         ▼
   provider.generate()     provider.embed()
   (RAG: rag.py:649)       (index/query: rag.py / ingestion.py) ──> pgvector
```

Secrets resolved via `resolve_secret()` (`ecs_platform/config/loader.py:140-142`). Cloud providers are
**credential-optional**: constructing a provider never requires keys; only network calls do
(`provider.py:1-6`). This is why importing the module never breaks offline/air-gapped startup.

---

## 4. Recommended (documentation-only) hardening — NOT applied here

These are recommendations for a future, separately-scoped change (this assessment makes **no code
changes**):

1. **Align the code default to `ollama`.** `get_provider` falls back to `"gemini"` if YAML is missing
   (`provider.py:241`); set it to `"ollama"` so even a missing config stays local/offline-safe.
2. **Add a circuit-breaker / fallback chain** (e.g. local Ollama primary → deterministic fallback)
   centrally, so any provider failure degrades to the existing deterministic answers.
3. **Per-task model routing** (small model for classification, larger for summaries) via config.
4. **Remove the unused `ResponseGenerator`** (`generator.py:54`, no call sites) to avoid drift.
5. **Provider health/warm endpoint** is already present for Ollama (`OllamaProvider.warm()`,
   `provider.py:208-227`) — expose uniformly across providers.

---

## 5. Target architecture (local-first, banking)

```
            ┌─────────────────────────── ECS App (FastAPI) ───────────────────────────┐
            │  Deterministic engines (no model)   │   RAG assistant (rag.py)           │
            │  • dashboards, workflows, frameworks │   • retrieve (pgvector)            │
            │  • drilldowns, reports, AI-SDLC mock │   • generate (provider.generate)   │
            └───────────────────────────┬─────────┴───────────────┬───────────────────┘
                                         │                         │
                                  provider.embed()          provider.generate()
                                         │                         │
                              ┌──────────▼─────────────────────────▼──────────┐
                              │        LLMProvider (get_provider)              │
                              │   default → OllamaProvider (LOCAL, keyless)    │
                              └──────────┬─────────────────────────┬──────────┘
                                         │                         │
                         ┌───────────────▼──────┐        ┌─────────▼─────────────┐
                         │  Ollama daemon (local)│        │  pgvector (local PG)  │
                         │  qwen3:8b, nomic-embed│        │  evidence_embeddings  │
                         └───────────────────────┘        └───────────────────────┘
   (Optional, opt-in via config: OpenAI / Azure OpenAI / Anthropic / Gemini for non-air-gapped envs)
```

## 6. Conclusion

The model abstraction layer the brief asks to "design" **already exists and is sound**. For local LLM,
no new provider classes are needed — Qwen/Llama/DeepSeek/Mistral/Gemma are model parameters served by
the existing `OllamaProvider`. Recommended hardening is documented above and intentionally **not**
implemented, per the no-code-change constraint.
