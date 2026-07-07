# ECS Load Testing Reference

**Type:** Performance/capacity reference. **No code/UI/DB changes.** **Grounding:** architecture (FastAPI modular monolith, PostgreSQL/pgvector/MinIO/Redis, Ollama local LLM via `host.docker.internal`), connector defaults (`config/integrations.yaml`: `timeout_sec=10`, `max_retries=1`, `page_size=100`), 39 pytest suites. **No dedicated load-test harness ships today — all projected targets below are [Inferred/Target] and must be validated before quoting in UAT/PROD.**

---

## Method (recommended)
Use Locust/k6 against FastAPI endpoints + a seeded repository; measure p50/p95 latency, throughput, error rate, and resource use. Profile separately: web/render, repository queries, connector sync, and AI/RAG (Ollama is the dominant latency factor).

## Scale scenarios **[Inferred/Target]**

| Scenario | Apps | Evidence (approx) | Notes |
|---|---|---|---|
| Small | 10 | ~5k | single-node dev/demo |
| Medium | 50 | ~25k | indexes on source/app/type sufficient |
| Large | 100 | ~50k | tune Postgres connections/pool |
| X-Large | 500 | ~250k | read replicas / partitioning candidate |
| Enterprise | 1000 | ~500k+ | horizontal scale + queue offload |

## Load dimensions

- **Evidence Load:** bulk ingest + reindex; bounded by Postgres write + embedding throughput. Incremental reindex uses `content_hash` dedup to avoid re-embedding.
- **User Load:** concurrent dashboard renders (server-rendered Jinja2 — CPU + query bound; no client build).
- **AI Load:** concurrent RAG queries; **Ollama is the bottleneck** (single local model, `keep_alive` keeps model resident). Scale via larger GPU host or cloud provider fallback.
- **Query Load:** predefined-query execution against targets; bounded by connector `timeout_sec`/concurrency.
- **Database Load:** read-heavy KPI aggregation; mitigate with indexes (present), pooling, and caching (Redis).

## Expected results **[Inferred/Target — validate]**
- Dashboard p95 < 1s up to ~100 apps on a single node (no async caching today → recompute per request).
- RAG p95 dominated by LLM generation (seconds); embedding lookup (pgvector) sub-second at <500k chunks.
- Connector sync scales with `page_size`/parallelism; health checks fail fast (10s).

## Capacity planning
- **Vertical first:** more CPU/RAM for app + Postgres; GPU for Ollama.
- **Then horizontal:** multiple app replicas behind a load balancer (stateless render), Postgres read replicas, queue-based connector sync.
- **AI:** offload heavy/long-context jobs to cloud provider (hybrid) per [LLM Decision Matrix](../ai-sdlc/ECS_LOCAL_VS_CLOUD_LLM_DECISION_MATRIX.md).
- **Caching:** add KPI result caching (Redis) for large tenants — **[Phase 2 enhancement]**.

## Cross-references
- Deployment scaling: [ECS_DEPLOYMENT_REFERENCE.md](../production/ECS_DEPLOYMENT_REFERENCE.md)
- AI operations: [ECS_LOCAL_LLM_OPERATIONS_GUIDE.md](../operations/OPERATIONS_ECS_LOCAL_LLM_OPERATIONS_GUIDE.md)
- Data model/indexes: [ECS_DATA_ARCHITECTURE_REFERENCE.md](../architecture/ECS_DATA_ARCHITECTURE_REFERENCE.md)
