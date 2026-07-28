# Phase-1 Chatbot Retrieval Quality Catalogue

Baseline audit-question set for hybrid chatbot routing validation (Teammate 2).

## Files

| File | Role |
|------|------|
| `phase1_chatbot_retrieval_catalogue.json` | ≥50 labelled questions + expected path metadata |
| `phase1_chatbot_retrieval_config.json` | Benchmark pointer / scoring notes |

This catalogue is **not** a duplicate of `rag_golden_set.json` (synthetic IDs). It targets `chatbot_answer` hybrid paths: preset (`@ceq:`), deterministic intents, RAG, and no-evidence refusal.

## Runner

`scripts/run_phase1_chatbot_retrieval_benchmark.py` — evaluation-only harness mirroring hybrid `chatbot_answer` routing (preset / deterministic / RAG / refusal). Does not modify production retrieval.

Structure check (no full 60-question run):

```bash
python scripts/run_phase1_chatbot_retrieval_benchmark.py --config benchmarks/config/phase1_chatbot_retrieval_config.json --validate-only
```

Full baseline (writes gitignored JSON under `benchmarks/output/phase1_chatbot_retrieval/`):

```bash
python scripts/run_phase1_chatbot_retrieval_benchmark.py --config benchmarks/config/phase1_chatbot_retrieval_config.json
```

Latency smoke (first 5 questions only):

```bash
python scripts/run_phase1_chatbot_retrieval_benchmark.py --config benchmarks/config/phase1_chatbot_retrieval_config.json --limit 5
```

The runner applies host-side endpoints (same as `scripts/benchmark_env.sh`), rewrites
`OLLAMA_URL=http://host.docker.internal:11434` → `http://localhost:11434`, forces a
one-time canonical hydrate under `suppress_startup_indexing()`, and suppresses
hydration indexing during preset/deterministic reads. RAG query-time embedding
remains enabled. Stage timings print per question.

Do **not** use `scripts/run_rag_benchmark.py` for this catalogue (RAG-only).
