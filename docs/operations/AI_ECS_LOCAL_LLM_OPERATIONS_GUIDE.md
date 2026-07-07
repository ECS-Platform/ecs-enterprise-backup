# ECS Local LLM Operations Guide

**Release tag:** `ecs-local-llm-readiness-enterprise-v1`
**Scope:** Documentation only. Day-2 operations for ECS running on local LLM (Ollama + pgvector).

---

## 1. Operational components

| Component | Role | Where |
|---|---|---|
| Ollama daemon | Serves chat + embedding models | host `:11434`, `OllamaProvider` (`provider.py:157`) |
| Postgres + pgvector | Vector store + evidence repo | `docker-compose.yml:144-153`, `pgvector_store.py` |
| ECS app | RAG orchestration + UI | FastAPI (`app/main.py`) |

## 2. Health & monitoring

| Signal | Endpoint / source | Healthy |
|---|---|---|
| RAG configured + index | `GET /api/platform/rag/status` | provider configured, index present |
| LLM connectivity | `GET /api/platform/rag/llm` | reachable |
| Assistant working | `GET /api/platform/assistant?q=ping` | `mode:rag` (or graceful `fallback`) |
| Ollama models | `GET :11434/api/tags` | required models listed |
| Startup provider log | `app/main.py:150-168` | logs active provider/model |

**Alerting recommendations**
- Alert if assistant `mode` stays `fallback` for N minutes (model down).
- Alert on Ollama `:11434` unreachable.
- Alert on pgvector connection failures / empty index after reindex.

## 3. Routine operations

### 3.1 Warm models (reduce cold-start)
```bash
curl -s -X POST http://<ecs>/api/platform/rag/warm | jq    # admin only
```
Backed by `warm_models()` → `provider.warm()` (`routes_governance.py:349-357`, `provider.py:208-227`).
Set `ECS_OLLAMA_KEEP_ALIVE=30m` so models stay resident.

### 3.2 Reindex evidence (after data load)
```bash
curl -s -X POST http://<ecs>/api/platform/rag/reindex | jq # admin only
```
Backed by `reindex_evidence()` (`rag.py:259`); incremental by default. Run after bulk evidence import
or embedding-model change.

### 3.3 Model management
```bash
ollama list                         # installed models
ollama pull qwen3:8b                # update / add
ollama rm <model>                   # remove unused
```

## 4. Change management

| Change | Procedure | Risk |
|---|---|---|
| Switch chat model | Set `ECS_LLM_MODEL`, pull model, warm | Low (no code change) |
| Switch embedding model | Set `ECS_EMBEDDING_MODEL`, **rebuild index at new dim**, set `ECS_VECTOR_DIM` | Medium (dim mismatch breaks search) |
| Switch provider to cloud | Set `ECS_LLM_PROVIDER` + key | High for banking (egress) — avoid in air-gap |
| Capacity scale | Add GPU node / route Ollama | Medium |

> **Critical rule:** embedding dimension in `ECS_VECTOR_DIM` must equal the model's output dim. Changing
> the embedding model requires recreating `evidence_embeddings` and a full reindex.

## 5. Backup & recovery

| Asset | Backup | Recovery |
|---|---|---|
| Evidence + embeddings | Postgres backup (includes `evidence_embeddings`) | Restore DB; reindex if needed |
| Ollama models | `~/.ollama/models` blob backup | Restore blobs or re-pull (online) |
| Config | Version `config/llm.yaml`, `config/vectorstore.yaml`, env | Redeploy |

## 6. Failure modes & responses

| Failure | Effect | Response |
|---|---|---|
| Ollama down | Assistant → `fallback` (still answers via keyword) | Restart Ollama; warm; verify status |
| pgvector down | Retrieval → repository SQL or deny | Restore Postgres; check connectivity |
| Empty index | Vector retrieval misses → repository fallback | Run reindex |
| Dim mismatch | Search errors after model swap | Recreate table at correct dim + reindex |
| Cold latency spike | Slow first queries | Warm + keep-alive |
| Cloud egress attempt | Provider misconfig in air-gap | Lock `ECS_LLM_PROVIDER=ollama`; block egress |

## 7. Capacity planning

- Size the Ollama node from the Phase 10 Performance Benchmark for the chosen model tier
  (`qwen3:8b` baseline; quality tier larger).
- pgvector sized to evidence volume × embedding dim (768 default).
- Keep one warm chat model + one warm embedding model resident (`keep_alive`).

## 8. Air-gap operational checklist

- [ ] `ECS_LLM_PROVIDER=ollama`, no cloud keys present
- [ ] Models vendored / pinned; `ollama list` shows required models
- [ ] AI egress blocked at network policy
- [ ] `/api/platform/rag/status` + `/llm` in readiness probes
- [ ] Fallback verified (stop Ollama → assistant still answers)
- [ ] Reindex job scheduled after evidence loads
- [ ] Postgres backups include `evidence_embeddings`
