# ECS Local LLM Testing Guide (Phase 6)

**Release tag:** `ecs-local-llm-readiness-enterprise-v1`
**Scope:** Documentation only. Test cases reference real endpoints and code paths.

Covers Functional, Performance, Security, Accuracy, Hallucination, RAG, and Vector Search testing for
ECS running on local LLM (Ollama + pgvector).

Key endpoints under test:
- `GET /api/platform/rag/status` (`routes_governance.py:334`)
- `GET /api/platform/rag/llm` (`:344`)
- `GET /api/platform/assistant?q=...` (`:321`)
- `POST /api/platform/rag/warm` / `reindex` (`:349`, `:359`)

---

## 1. Functional testing

| ID | Test | Steps | Expected outcome |
|---|---|---|---|
| F1 | Provider selected = Ollama | Set `ECS_LLM_PROVIDER=ollama`; call `/api/platform/rag/status` | Status reports local provider configured |
| F2 | LLM connectivity | `GET /api/platform/rag/llm` with Ollama up | Connectivity OK |
| F3 | Grounded answer | `GET /api/platform/assistant?q=<known evidence question>` | `mode:"rag"`, `grounded:true`, non-empty `answer` |
| F4 | Deterministic fallback | Stop Ollama; repeat F3 | `mode:"fallback"`, still returns `keyword_answer` (no 500) |
| F5 | Reindex (admin) | `POST /api/platform/rag/reindex` as platform admin | Returns indexed count; non-admin → denied |
| F6 | Warm models (admin) | `POST /api/platform/rag/warm` | Returns warm status |
| F7 | Empty query guard | `GET /api/platform/assistant?q=` | HTTP 400 `q is required` (`routes_governance.py:327`) |
| F8 | Reasoning-model cleanliness | Use `qwen3:8b`/`deepseek-r1`; ask a question | Answer has **no** `<think>` tags (`provider.py:18-23`) |

## 2. Performance testing

| ID | Metric | Method | Target (guidance) |
|---|---|---|---|
| P1 | First-token / cold start | Time first query after restart | High; mitigate via warm + `keep_alive` |
| P2 | Warm latency (qwen3:8b) | Avg over 20 queries warmed | Record p50/p95 per Phase 10 benchmark |
| P3 | Embedding latency | Time `provider.embed([text])` | Sub-second for short text on GPU |
| P4 | Vector search latency | Time pgvector `<=>` query | Low; ensure index present |
| P5 | Throughput | Concurrent assistant calls | Record QPS at acceptable p95 |
| P6 | Keep-alive effect | Compare with/without `ECS_OLLAMA_KEEP_ALIVE=30m` | Warm path materially faster |

> Capture CPU/RAM/GPU per model; compare to the Performance Benchmark + Compatibility Matrix docs.

## 3. Security testing

| ID | Test | Expected |
|---|---|---|
| S1 | No external egress | Network capture during a query | Traffic only to local Ollama + Postgres; no internet |
| S2 | Keyless start (air-gap) | Start ECS with no API keys | App boots; Ollama path works (`provider.py:1-6`) |
| S3 | RBAC scope on answers | Restricted role with no app assignments asks a question | No out-of-scope evidence; explicit deny (`rag.py:470-474`) |
| S4 | Admin-only mutations | Non-admin calls `/rag/reindex` or `/rag/warm` | Denied by `guard_mutation` (`routes_governance.py:351-355`) |
| S5 | Provider lock | Force `ECS_LLM_PROVIDER=ollama` | No cloud provider instantiated |
| S6 | Prompt-injection containment | Evidence containing "ignore instructions…" | Answer stays grounded; scope not bypassed |

## 4. Accuracy testing

| ID | Test | Method | Expected |
|---|---|---|---|
| A1 | Grounded correctness | Curated Q→expected-fact set over known evidence | Answers match facts from retrieved evidence |
| A2 | Citation alignment | Inspect returned evidence vs answer | Answer supported by retrieved uids |
| A3 | Framework mapping correctness | Ask cross-framework reuse question | Mapping consistent with `control_framework_crosswalk` |
| A4 | Model comparison | Run A1 set across qwen3 / llama3 / mistral | Record accuracy per model (Compatibility Matrix) |

## 5. Hallucination testing

| ID | Test | Method | Expected |
|---|---|---|---|
| H1 | Out-of-corpus question | Ask about data not in evidence | Model says it lacks evidence; does not fabricate |
| H2 | Empty retrieval | Force no retrieval hits | `grounded:false` / fallback, not invented detail |
| H3 | Fabricated control IDs | Ask for non-existent control | No invented control numbers |
| H4 | Scope leakage | Restricted persona asks broad question | No data outside assigned apps |

> Grounding contract: answer should be driven by retrieved evidence; when retrieval is empty the
> pipeline returns fallback rather than free-form generation (`rag.py:599-653`).

## 6. RAG testing

| ID | Test | Expected |
|---|---|---|
| R1 | Retrieval mode = vector | Provider configured + index populated | `_retrieve` returns mode `"vector"` (`rag.py:463`) |
| R2 | Retrieval mode = repository | Provider down | mode `"repository"` deterministic SQL (`rag.py:475-495`) |
| R3 | Filter by application | Pass `application=` | Only that app's evidence retrieved (`rag.py:452`) |
| R4 | Filter by framework | Pass `framework=` | Crosswalk-filtered evidence (`rag.py:485`) |
| R5 | Enrichment present | Inspect answer facts | Source/timestamp/controls/framework map attached (`rag.py:500+`) |
| R6 | End-to-end grounded | Full pipeline up | `mode:"rag"`, `grounded:true` |

## 7. Vector search testing

| ID | Test | Expected |
|---|---|---|
| V1 | Dimension match | `ECS_VECTOR_DIM` vs embedding length | Equal (768 for nomic-embed-text) |
| V2 | Cosine ranking | Query near a known item | That item ranks top (`pgvector_store.py:97-101`) |
| V3 | Metadata filter | Search with `filters={application}` | Only matching rows returned |
| V4 | Reindex integrity | After `reindex_evidence` | Row count matches evidence; search non-empty |
| V5 | Model swap dim change | Switch to bge-large (1024) | Old index must be rebuilt at new dim (negative test → mismatch error before rebuild) |

---

## 8. Suggested validation run order

```bash
# 1. Infra
curl -s localhost:11434/api/tags | jq '.models[].name'
# 2. ECS RAG health
curl -s http://<ecs>/api/platform/rag/status | jq
curl -s http://<ecs>/api/platform/rag/llm    | jq
# 3. Functional grounded answer
curl -s "http://<ecs>/api/platform/assistant?q=Which%20PCI%20DSS%20controls%20have%20rejected%20evidence" | jq '.mode,.grounded'
# 4. Fallback (stop ollama, repeat step 3) -> mode:fallback, keyword_answer present
# 5. Vector (admin): reindex then re-query
curl -s -X POST http://<ecs>/api/platform/rag/reindex | jq
```

**Pass criteria:** F1–F8 pass; fallback works with Ollama down; RAG returns `mode:rag/grounded:true`
with Ollama up; vector dimension matches; RBAC scope holds for restricted personas.
