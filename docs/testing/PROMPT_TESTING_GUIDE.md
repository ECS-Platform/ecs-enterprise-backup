# ECS Prompt Testing Guide

**Status:** Current · **Owner:** Audit Intelligence / LLM
**Scope:** How to test ECS audit prompts — execution, benchmarking, replay,
comparison, grounding and hallucination checks, and the metrics they produce.

> Grounded in repository inspection. Sources:
> `modules/audit_intelligence/llm/` (`prompt_library.py`, `execution_service.py`,
> `benchmark_runner.py`, `llm_evaluation.py`, `token_estimator.py`,
> `query_classifier.py`, `deterministic_router.py`, `context_builder.py`),
> `modules/audit_intelligence/routes/routes_audit_llm.py`,
> `config/audit_llm_prompt_library.yaml`,
> `config/audit_llm_benchmark_profiles.yaml`,
> `scripts/run_audit_llm_benchmark.py`. Tests:
> `tests/test_audit_llm_workbench.py`, `tests/test_audit_llm_evaluation.py`.

This guide is about **prompt testing**. For the underlying model/provider stack
(Ollama, Gemini, provider abstraction) see
[`docs/ai-sdlc/ECS_LOCAL_LLM_DEVELOPER_GUIDE.md`](../ai-sdlc/ECS_LOCAL_LLM_DEVELOPER_GUIDE.md).
For the RAM-profile benchmark plan see
[`docs/benchmarks/audit_llm_16gb_20gb_testing_guide.md`](../benchmarks/audit_llm_16gb_20gb_testing_guide.md).

---

## 1. What "prompt testing" means in ECS

Every audit prompt lives in the **prompt library**
(`config/audit_llm_prompt_library.yaml`, 40 prompts). A prompt is *tested* by
running it through the same pipeline the workbench uses and asserting on the
result and its metrics:

```
classify → route (deterministic context) → build context (+ optional RAG)
        → token-estimate → execute (LLM or deterministic fallback)
        → evaluate (grounding + citations)
```

All of this is **offline-safe**: with no local model running, execution returns
the deterministic result (never crashes), and `--dry-run` benchmarks make **no**
LLM call at all. That is why prompt tests run in CI on an 8 GB machine.

Key modules:

| Stage | Module | Entry point |
|---|---|---|
| Classify | `llm/query_classifier.py` | `classify()`, `extract_entities()` |
| Route | `llm/deterministic_router.py` | `PROMPT_ROUTES`, `build_deterministic_context()` |
| Context | `llm/context_builder.py` | `build_context()` |
| Token estimate | `llm/token_estimator.py` | `estimate_prompt()`, `ram_profile_compatibility()` |
| Execute | `llm/execution_service.py` | `execute()` |
| Benchmark | `llm/benchmark_runner.py` | `run_benchmark()`, `export_report()` |
| Evaluate | `llm/llm_evaluation.py` | `evaluate()`, `validate_grounding()`, `validate_citations()`, `replay()`, `compare()` |

---

## 2. Prompt templates & required JSON (input format)

A prompt template declares which variables it needs via `input_variables`. Example
(from `config/audit_llm_prompt_library.yaml`):

```yaml
- prompt_id: observation_count
  category: observations
  query_type: deterministic          # deterministic | llm_assisted | hybrid
  input_variables: [application, framework, status]
  required_context: [observations]
  user_prompt_template: |
    Summarize this observation count result for {application_or_all}:
    {deterministic_result}
  token_profile: small_4k            # small_4k|medium_8k|large_16k|extended_20k|worst_case_enterprise_dry_run
  risk_level: low
  applicable_frameworks: [ALL]
```

To **execute** a prompt you supply a JSON body to `POST /api/audit-llm/query`.
The `input_variables` object binds to the template placeholders:

```json
{
  "prompt_id": "observation_count",
  "query": "How many open observations for Payments under RBI?",
  "input_variables": { "application": "Payments", "framework": "RBI", "status": "open" },
  "ram_profile": "local_16gb_safe",
  "use_rag": true
}
```

Response (shape from `execution_service.execute`): a dict containing at least
`prompt_id`, `query_type`, the assembled prompt, the `token_estimate`, the
`answer`/`response`, `source_references`, and (for `llm_assisted`) `confidence`,
`assumptions`, `limitations`. `deterministic` prompts never let the model change a
number/id/status — it only rephrases the computed result.

> `query_type` policy: `deterministic` = answered from DB/query logic (LLM may only
> summarize); `llm_assisted` = analytical/predictive, **must** carry confidence +
> assumptions + limitations; `hybrid` = deterministic result + LLM explanation.

---

## 3. Executing prompt tests

### 3.1 Via REST (the workbench surface)

All endpoints are registered by `register_audit_llm_routes(app)` and are exercised
in `tests/test_audit_llm_workbench.py`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/audit-llm/prompts` | List/filter the library (`category`, `query_type`, `ram_profile`) |
| GET | `/api/audit-llm/prompts/{prompt_id}` | One prompt definition |
| GET | `/api/audit-llm/profiles` | RAM + token profiles |
| POST | `/api/audit-llm/classify` | Classify a natural-language query |
| POST | `/api/audit-llm/token-estimate` | Token estimate + RAM compatibility |
| POST | `/api/audit-llm/query` | Full prompt lifecycle (execute) |
| POST | `/api/audit-llm/benchmark` | Run a benchmark, return report JSON |
| GET | `/api/audit-llm/benchmark/results` | List prior JSON reports |
| POST | `/api/audit-llm/benchmark/export` | Run + write MD/JSON reports |
| POST | `/api/audit-llm/replay` | Replay a stored execution record |
| POST | `/api/audit-llm/compare` | Diff two execution results |
| POST | `/api/audit-llm/validate-grounding` | Grounding + citation validation |

UI: `GET /mvp/audit/llm-workbench` (`routes_audit_ui.py::ui_llm_workbench`).

### 3.2 Via Python (in a test)

```python
from modules.audit_intelligence.llm import execution_service as ex

result = ex.execute(
    prompt_id="observation_count",
    user_query="open observations for Payments",
    input_variables={"application": "Payments", "status": "open"},
    ram_profile="local_16gb_safe",
    use_rag=False,          # deterministic-only, fully offline
)
assert result["prompt_id"] == "observation_count"
assert "token_estimate" in result
```

### 3.3 Via the pytest suite

```bash
pytest tests/test_audit_llm_workbench.py tests/test_audit_llm_evaluation.py -q
```

These validate: the 40-prompt library, the 3 RAM / 5 token profiles, classifier
(deterministic / llm_assisted / hybrid), entity extraction, the deterministic
router, the token estimator (16 GB / 20 GB rules), `execute()` (dry-run / fallback
/ scaffold), the benchmark runner + export, every core `/api/audit-llm/*`
endpoint, the workbench UI render, and a **no-secrets-in-config** guard.

---

## 4. Benchmark datasets & benchmark execution

The "dataset" for prompt benchmarking is the **prompt library filtered by
category / ids / RAM profile**, run under a **benchmark profile**
(`config/audit_llm_benchmark_profiles.yaml`): 5 token profiles (`small_4k` →
`worst_case_enterprise_dry_run`) and 3 RAM profiles (`local_16gb_safe`,
`local_20gb_extended`, `worst_case_enterprise_dry_run`).

### 4.1 CLI

```bash
# Dry-run (no LLM call; safe anywhere incl. 8 GB) — token estimates only:
python scripts/run_audit_llm_benchmark.py --profile local_16gb_safe --mode dry_run

# Live (requires a configured local provider; falls back if unavailable):
python scripts/run_audit_llm_benchmark.py --profile local_20gb_extended --mode live

# Scope selection (equivalent legacy flags shown):
python scripts/run_audit_llm_benchmark.py --category executive --dry-run --json
python scripts/run_audit_llm_benchmark.py --prompt observation_count --execute
```

Reports (Markdown + JSON) are written to `reports/audit_llm_benchmarks/`.
`--mode dry_run` == `--dry-run` (default); `--mode live` == `--execute`.

### 4.2 REST

```json
POST /api/audit-llm/benchmark
{ "category": "executive", "ram_profile": "local_16gb_safe", "dry_run": true }
```

`POST /api/audit-llm/benchmark/export` additionally writes the MD/JSON evidence;
`GET /api/audit-llm/benchmark/results?limit=20` lists prior runs.

### 4.3 Adding a benchmark "dataset"

There is no separate dataset file to author — add or tag prompts in
`config/audit_llm_prompt_library.yaml` (give them a `category` and a
`token_profile`), then benchmark that `--category`. For **RAG retrieval** IR
metrics (recall/precision/MRR/NDCG) the golden set is
`benchmarks/config/rag_golden_set.json`, evaluated by
`ecs_platform/llm_engine/retrieval_metrics.py` (see
`tests/test_retrieval_metrics.py`).

---

## 5. Replay

Replay re-runs a previously captured execution record so you can reproduce a
result deterministically (dry-run by default — no LLM call).

```json
POST /api/audit-llm/replay
{ "record": { "prompt_id": "observation_count", "assembled_prompt": "…", "input_variables": {…} },
  "live": false }
```

Python: `llm_evaluation.replay(record, live=False)`. Covered by
`tests/test_audit_llm_evaluation.py`.

---

## 6. Comparison

Compare two execution results (e.g. two models, two profiles, or before/after a
prompt edit). The diff reports token delta, source-reference differences,
assumptions differences, and response similarity (Jaccard).

```json
POST /api/audit-llm/compare
{ "a": { "response": "…", "token_estimate": {…}, "source_references": ["E1"] },
  "b": { "response": "…", "token_estimate": {…}, "source_references": ["E1","E2"] } }
```

Python: `llm_evaluation.compare(a, b)`.

---

## 7. Grounding & hallucination testing

Grounding is the core anti-hallucination check: the answer must be supported by
the supplied evidence/deterministic context, and any `[E#]` citations must resolve.

```json
POST /api/audit-llm/validate-grounding
{ "answer": "Payments has 3 open observations [E1].",
  "evidence_context": { "E1": "Payments: 3 open observations" },
  "assembled_prompt": "…" }
```

`llm_evaluation.validate_grounding()` scores lexical support of the answer against
the evidence context; `validate_citations()` checks that every `[E#]` referenced
exists in the context. `evaluate()` combines both. The **platform** RAG path adds
a hard guard: `ecs_platform/rag.py` **refuses to answer without evidence**
(`refuse_without_evidence`), which is the runtime hallucination safeguard for the
`/api/platform/assistant` stack (see `tests/test_rag_answer_validation.py`).

Testing patterns (from `tests/test_audit_llm_evaluation.py`):

- **Grounded answer** → grounding passes, citations resolve.
- **Unsupported claim** → grounding flags the ungrounded sentence.
- **Empty / missing evidence** → refuse / low grounding, never a fabricated answer.
- **Dangling `[E#]`** → citation validation fails.

---

## 8. Performance metrics (latency, token counts) & success criteria

| Metric | Where it comes from |
|---|---|
| **Token counts** (prompt / context / expected output / total) | `token_estimator.estimate_prompt()`; `chars_per_token` from `config/audit_llm_benchmark_profiles.yaml` |
| **RAM-profile fit** | `token_estimator.ram_profile_compatibility()` (does the estimate fit the 16 GB / 20 GB budget?) |
| **Latency** (live mode) | `benchmark_runner.run_benchmark()` records per-prompt timing when `--execute` |
| **Grounding score / citation validity** | `llm_evaluation.evaluate()` |
| **Retrieval quality** (RAG) | `retrieval_metrics.evaluate()` (recall@k, precision, MRR, NDCG) |

Suggested **success criteria** for a prompt to be "test-passing":

1. It loads and validates in the library (has a template + `query_type` + profile).
2. `execute()` returns a result offline (deterministic fallback works — no crash).
3. Token estimate **fits** the target RAM profile (`ram_profile_compatibility` ok).
4. For `llm_assisted` prompts: the result carries **confidence + assumptions +
   limitations** (policy enforced).
5. Grounding validation passes on a known grounded example, and **fails** on a
   known unsupported example (both directions asserted).
6. Benchmarks run clean in `--dry-run` (CI) and produce a report.

---

## 9. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `execute()` returns deterministic answer even in live mode | No local provider configured/reachable. Start Ollama, set `ECS_LLM_PROVIDER=ollama`; check `GET /api/platform/rag/llm`. |
| Grounding always "unsupported" | The evidence context passed is empty or doesn't lexically overlap the answer — supply the real `evidence_context`/`assembled_prompt`. |
| Token estimate exceeds RAM profile | Reduce `expected_output_tokens` / `max_context_chunks`, or use a larger profile (`local_20gb_extended`). |
| Citation validation fails | The answer references an `[E#]` id not present in `evidence_context`. |
| Benchmark "live" is slow / times out | Expected for large local models; use `--dry-run` in CI, raise `ECS_LLM_TIMEOUT_SECONDS` for live. |

---

## 10. Folder / file locations

- Prompt library (data): `config/audit_llm_prompt_library.yaml`
- Benchmark profiles (data): `config/audit_llm_benchmark_profiles.yaml`
- Prompt/LLM services: `modules/audit_intelligence/llm/`
- REST routes: `modules/audit_intelligence/routes/routes_audit_llm.py`
- Workbench UI: `modules/audit_intelligence/routes/routes_audit_ui.py` +
  `templates/audit/llm_workbench.html`
- Benchmark CLI: `scripts/run_audit_llm_benchmark.py`
- Reports output: `reports/audit_llm_benchmarks/`
- Prompt inventory (reference): `docs/audit-intelligence/audit_llm_prompt_inventory.md`
- Tests: `tests/test_audit_llm_workbench.py`, `tests/test_audit_llm_evaluation.py`,
  `tests/test_retrieval_metrics.py`, `tests/test_rag_answer_validation.py`

---

## 11. Related documentation

- Local LLM Developer Guide: `docs/ai-sdlc/ECS_LOCAL_LLM_DEVELOPER_GUIDE.md`
- Prompt workbench design: `docs/workbenches/audit_llm_prompt_workbench_design.md`
- 16 GB / 20 GB benchmark plan: `docs/benchmarks/audit_llm_16gb_20gb_testing_guide.md`
- Prompt inventory: `docs/audit-intelligence/audit_llm_prompt_inventory.md`
- Connector Test Workbench (separate, connector-side): `docs/connectors/connector_test_workbench_design.md`
