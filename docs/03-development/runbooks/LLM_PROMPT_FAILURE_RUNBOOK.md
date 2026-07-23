# Runbook: LLM / Prompt Execution Failure

RAG answers, the Prompt Workbench, or benchmarks fail, return fallback text, or
time out.

> Reference: [`../operations/AI_ECS_LOCAL_LLM_OPERATIONS_GUIDE.md`](../operations/AI_ECS_LOCAL_LLM_OPERATIONS_GUIDE.md)
> · [`../developer-manual/PROMPT_TESTING_GUIDE.md`](../developer-manual/PROMPT_TESTING_GUIDE.md)
> · [`../workbenches/audit_llm_prompt_workbench_design.md`](../workbenches/audit_llm_prompt_workbench_design.md).

## Symptoms
- Answers marked `[FALLBACK]` or `mode: fallback`/`no_evidence`; timeouts;
  benchmark errors; empty citations; RAG status not ready.

## Diagnose
1. RAG/LLM status: `GET /api/platform/rag/status`, `GET /api/platform/rag/llm`.
2. Provider config: `config/llm.yaml` (`ECS_LLM_PROVIDER`, `ECS_LLM_MODEL`,
   `OLLAMA_URL`); vectors: `config/vectorstore.yaml` (pgvector).
3. Classify/estimate (always deterministic, no model): `POST /api/audit-llm/classify`,
   `POST /api/audit-llm/query` with `use_rag:false`.
4. Benchmark dry-run (no model): `POST /api/audit-llm/benchmark` (`dry_run:true`).

## Common causes & remediation
| Cause | Fix |
|-------|-----|
| Provider unreachable (Ollama down) | Start/point `OLLAMA_URL`; deterministic fallback keeps the app working. |
| No evidence indexed | Reindex: `POST /api/platform/rag/reindex`; confirm pgvector connectivity. |
| Refusal (`no_evidence`) | Expected grounding gate when no evidence/facts match — not a failure. |
| RBAC denied | Denied roles never reach retrieval/model — check the caller's role. |
| Timeouts | Tune `ECS_LLM_TIMEOUT` / benchmark profile (`config/audit_llm_benchmark_profiles.yaml`). |
| Wrong RAM profile | Only `local_16gb_safe` / `local_20gb_extended` are valid (no 28/60 GB). |

## Verify
- `GET /api/platform/rag/status` healthy; a grounded query returns citations;
  benchmark completes (dry-run or live per profile).

## Escalate
Model/host capacity issues → see the 16/20 GB testing guide
[`../benchmarks/audit_llm_16gb_20gb_testing_guide.md`](../../04-testing/benchmarks/audit_llm_16gb_20gb_testing_guide.md).
