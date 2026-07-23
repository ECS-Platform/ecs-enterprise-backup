# ECS Local LLM Operations Guide

**Purpose:** operate the AI layer — local Ollama LLM, embeddings, and the pgvector store that power RAG and copilots. Grounded in `config/llm.yaml`, `config/vectorstore.yaml`, `docker-compose.yml`, `ecs_platform/rag`. Documentation only.

> **Default posture:** ECS uses a **keyless, on-prem local LLM** — Ollama running `qwen3:8b`, with `nomic-embed-text` embeddings (dim 768). This keeps evidence/prompts on-premises. Switching to a managed provider (`gemini/openai/azure_openai/claude`) is **config-only** (`ECS_LLM_PROVIDER`), no code change.

---

## 1. Components

| Component | Config | Default |
|---|---|---|
| LLM provider | `llm.provider` (`ECS_LLM_PROVIDER`) | `ollama` |
| LLM model | `llm.model` / `OLLAMA_MODEL` | `qwen3:8b` |
| Embedding model | `llm.embedding_model` | `nomic-embed-text` |
| Vector dim | `ECS_VECTOR_DIM` | `768` |
| Ollama endpoint | `OLLAMA_URL` | `http://host.docker.internal:11434` |
| Keep-alive | `ECS_OLLAMA_KEEP_ALIVE` | `30m` |
| Timeout | `ECS_LLM_TIMEOUT` | `180s` |
| Temperature / max tokens | `ECS_LLM_TEMPERATURE` / `ECS_LLM_MAX_TOKENS` | `0.1` / `2048` |
| Vector store | `vectorstore.provider` | `pgvector` (`ecs_vectors`, table `evidence_embeddings`, collection `ecs_evidence_chunks`) |
| RAG guardrails | `rag.*` | `require_citations: true`, `refuse_without_evidence: true`, `top_k 8`, `max_context_chunks 12` |

> **Networking:** the dockerized app reaches a **host-local** Ollama daemon via `host.docker.internal` (compose `extra_hosts: host.docker.internal:host-gateway`). On Linux this mapping is required; on Docker Desktop it is automatic.

---

## 2. Startup sequence (AI layer)

```bash
# 1. Host: install + run Ollama daemon
ollama serve &                       # listens on :11434
# 2. Pull models referenced by config
ollama pull qwen3:8b
ollama pull nomic-embed-text
# 3. Verify daemon + models
curl -fsS host.docker.internal:11434/api/tags   # from container
curl -fsS localhost:11434/api/tags              # from host
# 4. Ensure pgvector is up (docker compose up -d pgvector)
# 5. Start ECS; embeddings populate as evidence is ingested
```

---

## 3. Health checks

| Check | Command | Healthy |
|---|---|---|
| Ollama daemon | `curl :11434/api/tags` | lists `qwen3:8b`, `nomic-embed-text` |
| Model responds | `curl :11434/api/generate -d '{"model":"qwen3:8b","prompt":"ping","stream":false}'` | JSON response |
| Vector store | `psql -d ecs_vectors -c 'select count(*) from evidence_embeddings;'` | count ≈ evidence chunks |
| End-to-end RAG | AI Assistant (`/mvp/ai-assistant`) query | grounded answer **with citations** |

---

## 4. Monitoring points

- Ollama latency / queue depth; model residency (`keep_alive`).
- Host GPU/CPU/RAM (8B model is memory-heavy).
- Embedding backlog: vector count vs evidence count.
- RAG refusal rate (high refusals → empty/sparse vector store, not a bug — guardrail working).
- Timeout rate vs `ECS_LLM_TIMEOUT=180s`.

---

## 5. Failure scenarios → recovery

| Symptom | Root cause | Recovery |
|---|---|---|
| AI Assistant returns nothing / refuses | empty vector store | re-embed evidence; confirm `evidence_embeddings` populated |
| "model not found" | model not pulled | `ollama pull qwen3:8b` (and `nomic-embed-text`) |
| AI features down, rest of ECS fine | Ollama daemon down/unreachable | start `ollama serve`; check `OLLAMA_URL`/`host.docker.internal` |
| First query very slow | cold model | raise/keep `ECS_OLLAMA_KEEP_ALIVE`; warm with a ping |
| Timeouts | model too large for host / long context | reduce `max_context_chunks`, raise timeout, or use managed provider |
| Dimension error on insert | `ECS_VECTOR_DIM` ≠ embedding model dim | align dim (768 for nomic/text-embedding-004); re-create table |
| Citations missing but answer given | guardrail bypass risk | confirm `require_citations: true`, `refuse_without_evidence: true` |

---

## 6. Switching provider (config-only, no code change)

```bash
# Managed example (Gemini)
export ECS_LLM_PROVIDER=gemini
export GEMINI_API_KEY=...            # OPENAI_API_KEY / ANTHROPIC_API_KEY / AZURE_OPENAI_* for others
docker compose up -d ecs
```
Embedding dim must match the chosen embedding model (`ECS_VECTOR_DIM`). Re-embed if you change embedding models.

---

## 7. Vector store operations

- **Rebuild:** vectors are **derived** from the repository — safe to drop + re-embed; never the source of record.
- **Backup:** optional (`scripts/backup/backup.sh --vector`); usually rebuilt rather than restored.
- **Provider switch:** `ECS_VECTOR_PROVIDER` supports `pgvector | chroma | milvus` (config-only).

---

## 8. Data residency & security

- Local Ollama keeps prompts + evidence context **on-prem** (no third-party calls) — preferred for regulated/banking data.
- Managed providers send context off-host — review data-classification before enabling; keys via env/vault only.
- RAG refuses to answer without grounding evidence (`refuse_without_evidence`) — reduces hallucination risk.

---

## 9. Escalation

L2 platform eng (daemon, networking, pgvector) → AI owner (model choice, prompt/RAG behavior). For platform-wide health see `ECS_PRODUCTION_MONITORING_GUIDE.md`.
