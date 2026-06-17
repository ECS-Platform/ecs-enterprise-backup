# ECS Embedding Strategy (Phase 7)

**Release tag:** `ecs-local-llm-readiness-enterprise-v1`

---

## 1. Current state (code-grounded)

| Element | Current | Evidence |
|---|---|---|
| Embedding provider | Configured provider (default **Ollama**) | `config/llm.yaml:7-9` |
| Embedding model | **`nomic-embed-text`** (default) | `config/llm.yaml:9` |
| Vector dimension | **768** | `config/vectorstore.yaml:5`, `docker-compose.yml:70` |
| Vector store | **pgvector** (Postgres), cosine `<=>` | `ecs_platform/vectorstore/pgvector_store.py:97-101` |
| Index build | `reindex_evidence()` / ingestion `_index()` | `ecs_platform/rag.py:259-293`, `ingestion.py:203-231` |
| Chunking | size 1000 / overlap 150 | `config/vectorstore.yaml:9-10` |

### Two distinct "search" implementations (important)

1. **Real embeddings + pgvector** (platform RAG): `provider.embed()` → `pgvector_store` cosine search.
   Used by the RAG assistant retrieval (`rag.py:456-463`). **This is true vector search.**
2. **Heuristic keyword search labeled "Semantic"**: `modules/governance/engines/search_module.py:119-137`
   — substring/word-overlap scoring (NOT embeddings). Evidence Reuse (`app/evidence_intel/reuse.py:8`)
   is explicitly "NO-LLM". These are candidates for future embedding upgrade (optional).

---

## 2. Embedding workloads in ECS

| Workload | Today | Recommended local model |
|---|---|---|
| Semantic / knowledge search (RAG) | nomic-embed-text via Ollama → pgvector | **bge-large-en-v1.5** (quality) or keep **nomic-embed-text** (speed) |
| Evidence similarity / reuse | heuristic (not embeddings) | upgrade to **bge-small-en-v1.5** for low latency at scale |
| Framework / control similarity | not embedded today | **e5-large-v2** or **instructor-xl** for instruction-tuned matching |

---

## 3. Recommended local embedding models (all Ollama/local-servable)

| Model | Dim | Strengths | Footprint | ECS fit |
|---|---|---|---|---|
| **nomic-embed-text** (current default) | 768 | Fast, long-context (8k), Apache-2.0, native Ollama | ~0.5 GB | **Primary** — already wired; dim matches `ECS_VECTOR_DIM=768` |
| **bge-large-en-v1.5** | 1024 | Top retrieval quality (MTEB), strong for compliance jargon | ~1.3 GB | **Quality tier** — needs `ECS_VECTOR_DIM=1024` + reindex |
| **bge-small-en-v1.5** | 384 | Very low latency, small RAM | ~0.13 GB | **High-throughput tier** — needs dim=384 + reindex |
| **e5-large-v2** | 1024 | Strong with "query:"/"passage:" prefixes | ~1.3 GB | Alt quality tier (dim=1024) |
| **instructor-xl** | 768 | Instruction-conditioned embeddings (task-aware) | ~4.9 GB | Specialized control/framework matching; heavier |

### Dimension compatibility caution

`ECS_VECTOR_DIM` (default **768**) and the pgvector column dimension **must match the embedding
model**. Switching to a 1024-dim model (bge-large/e5-large) or 384-dim (bge-small) **requires**:
1. Update `ECS_EMBEDDING_MODEL` and `ECS_VECTOR_DIM`.
2. Recreate the `evidence_embeddings` table at the new dimension.
3. Full **reindex** (`reindex_evidence()`).

Mixing dimensions corrupts cosine search; this is the single biggest operational risk in an embedding
swap. nomic-embed-text (768) is the **zero-migration default**.

---

## 4. Recommended strategy (banking, air-gapped)

| Tier | Model | When |
|---|---|---|
| **Default / Production** | `nomic-embed-text` (768) | Out-of-box; no reindex; fully local & keyless |
| **Quality (audit-grade retrieval)** | `bge-large-en-v1.5` (1024) | When retrieval precision on dense compliance text matters; plan reindex window |
| **Scale (large evidence corpora)** | `bge-small-en-v1.5` (384) | When index size/latency dominate |

All three are **fully local** via Ollama (or a local embedding server). No cloud embedding API is
needed for air-gapped deployments.

---

## 5. Upgrades (optional, out of current scope)

- Route `search_module.py` "semantic" search and `evidence_intel/reuse.py` through `provider.embed()` +
  pgvector to make them *truly* semantic. Today they are heuristic.
- Add a configurable per-workload embedding model (search vs reuse vs framework-similarity).

## 6. Conclusion

ECS already performs **real local embeddings** (nomic-embed-text → pgvector) by default. The embedding
strategy is therefore **production-viable for air-gap today**, with a clear, dimension-aware path to
higher-quality local models (bge/e5/instructor) when retrieval quality is prioritized.
