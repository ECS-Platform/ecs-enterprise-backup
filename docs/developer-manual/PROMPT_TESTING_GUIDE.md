# ECS Prompt Testing Guide

Developer guide for testing ECS prompts and the LLM/RAG stack: local LLM (Ollama),
the Gemini/cloud abstraction, the prompt inventory, execution, **replay**,
**comparison**, benchmarking, token metrics, and grounding/hallucination checks.

> **Reuse note.** Architecture and workbench design live elsewhere and are not
> duplicated here — this is the hands-on developer recipe that ties them together
> (and fills the replay/comparison + "add a prompt test" gaps).
> - LLM architecture: [`../ai-sdlc/ECS_AI_ARCHITECTURE_REFERENCE.md`](../ai-sdlc/ECS_AI_ARCHITECTURE_REFERENCE.md)
> - Local LLM dev: [`../ai-sdlc/ECS_LOCAL_LLM_DEVELOPER_GUIDE.md`](../ai-sdlc/ECS_LOCAL_LLM_DEVELOPER_GUIDE.md)
> - Prompt inventory (40 prompts): [`../audit-intelligence/audit_llm_prompt_inventory.md`](../audit-intelligence/audit_llm_prompt_inventory.md)
> - Workbench design: [`../workbenches/audit_llm_prompt_workbench_design.md`](../workbenches/audit_llm_prompt_workbench_design.md)
> - Benchmarks (16/20 GB): [`../benchmarks/audit_llm_16gb_20gb_testing_guide.md`](../benchmarks/audit_llm_16gb_20gb_testing_guide.md)

---

## 1. Model providers (local + cloud abstraction)

- Provider abstraction: `ecs_platform/llm_engine/provider.py` — `get_provider()`
  resolves from `config/llm.yaml` (`ECS_LLM_PROVIDER`, default `ollama`;
  `ECS_LLM_MODEL`, default `qwen3:8b`).
- **Local (Ollama):** `OLLAMA_URL` (default `http://host.docker.internal:11434`).
  Keyless; `configured()` = base URL set.
- **Cloud (Gemini/OpenAI/Azure/Claude):** require API keys; same interface.
- **Deterministic fallback:** if the provider is unconfigured/unreachable, the
  audit-LLM path returns a deterministic result marked `[FALLBACK]`; RAG returns
  `mode: fallback` / `no_evidence`. Nothing crashes.

## 2. RAM profiles (only two valid)

`local_16gb_safe` and `local_20gb_extended` (+ a `worst_case_enterprise_dry_run`
profile). **No 28 GB / 60 GB profile** exists in config or UI. Defined in
`config/audit_llm_benchmark_profiles.yaml`.

## 3. Prompt inventory & execution

```bash
# List prompts / profiles
curl -s localhost:8000/api/audit-llm/prompts
curl -s localhost:8000/api/audit-llm/profiles

# Classify a query (deterministic, no model)
curl -s -X POST localhost:8000/api/audit-llm/classify -H 'content-type: application/json' \
  -d '{"query":"summarize expired evidence"}'

# Token estimate (deterministic)
curl -s -X POST localhost:8000/api/audit-llm/token-estimate -H 'content-type: application/json' \
  -d '{"query":"summarize expired evidence"}'

# Execute a prompt (real LLM unless dry-run profile / provider down)
curl -s -X POST localhost:8000/api/audit-llm/query -H 'content-type: application/json' \
  -d '{"user_query":"summarize expired evidence","ram_profile":"local_16gb_safe"}'
```

Execution service: `modules/audit_intelligence/llm/execution_service.py::execute`.
Workbench UI: `/mvp/audit/llm-workbench`.

## 4. Replay & comparison

```bash
# Replay the last run deterministically (no LLM)
curl -s -X POST localhost:8000/api/audit-llm/replay -H 'content-type: application/json' \
  -d '{"record": <previous result>, "live": false}'

# Compare two results (e.g. two prompts, or dry-run vs live)
curl -s -X POST localhost:8000/api/audit-llm/compare -H 'content-type: application/json' \
  -d '{"a": <result A>, "b": <result B>}'
```

Backed by `modules/audit_intelligence/llm/llm_evaluation.py` (`replay`, `compare`).
The workbench "Replay (dry-run)" button calls `/api/audit-llm/replay`.

## 5. Grounding & hallucination / citation validation

```bash
curl -s -X POST localhost:8000/api/audit-llm/validate-grounding -H 'content-type: application/json' \
  -d '{"answer": "...", "evidence": [ ... ]}'
```

- RAG grounding gate refuses without evidence (`NO_EVIDENCE_MESSAGE`).
- `llm_evaluation.validate_grounding` / `validate_citations` check lexical
  grounding + `[E#]` citation alignment.

## 6. Benchmarking & token metrics

```bash
# Dry-run benchmark (no model)
curl -s -X POST localhost:8000/api/audit-llm/benchmark -H 'content-type: application/json' -d '{"dry_run":true}'
# Live benchmark on the matching laptop (16 or 20 GB)
PYTHONPATH=. python scripts/run_audit_llm_benchmark.py --profile local_16gb_safe --mode live
```

Reports land under `reports/audit_llm_benchmarks/`. See the 16/20 GB guide.

## 7. Add a prompt test (recipe)

1. **Add the prompt** to `config/audit_llm_prompt_library.yaml` with the required
   fields (`prompt_id`, `category`, `query_type`, `token_profile`, `system_prompt`,
   `user_prompt_template`, `local_16gb_supported`, `local_20gb_supported`).
2. **Validate loading:** `PYTHONPATH=. pytest tests/test_audit_llm_workbench.py -q`
   (the loader validates required fields + valid query/token profiles).
3. **Add a test** in `tests/` that calls `execution_service.execute(...)` with a
   dry-run profile (`worst_case_enterprise_dry_run`) so it runs with **no model**,
   and asserts `execution_mode == "dry_run"` + `deterministic_result` present.
4. For RAG paths, mock the provider + evidence (see `tests/test_rag_answer_validation.py`)
   and assert `mode`, citations, and refusal behavior.

## 8. Test commands

```bash
PYTHONPATH=. pytest tests/test_audit_llm_workbench.py tests/test_audit_llm_evaluation.py \
  tests/test_rag_answer_validation.py -q
```

## Related
- [`../developer-manual/DEVELOPER_MANUAL.md`](DEVELOPER_MANUAL.md) · [`../testing/TESTING_GUIDE.md`](../testing/TESTING_GUIDE.md) · [`../runbooks/LLM_PROMPT_FAILURE_RUNBOOK.md`](../runbooks/LLM_PROMPT_FAILURE_RUNBOOK.md)
