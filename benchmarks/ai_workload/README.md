# ECS AI Workload Benchmark Runner (Maximum Token Budgeting)

This runner is tuned for one purpose: measure **maximum realistic token usage**
per enterprise governance request for budgeting.

It reuses existing ECS components only:

- `ecs_platform.rag.answer` (existing RAG pipeline)
- provider token usage via `generate_with_metadata` (existing instrumentation)
- `ecs_platform.llm_engine.metrics_logger` outputs (`rag_metrics.csv/jsonl`)
- optional existing ingestion flow via `sync_all` (`run_sync_once=true`)

## Usage

```bash
python benchmarks/ai_workload/benchmark_runner.py
python benchmarks/ai_workload/benchmark_runner.py --config path/to/config.json
```

## Optional Config Keys

```json
{
  "role": "cio",
  "user": "benchmark-runner",
  "top_k": 5,
  "concurrency": 1,
  "max_requests_per_minute": 3,
  "run_sync_once": false,
  "output_dir": "benchmarks/output",
  "report_name": "maximum_token_budget_report.md"
}
```

## Benchmark Method

- Executes a **small sequential set** of enterprise board/regulator prompts.
- Prompts span multiple frameworks in a single request to trigger realistic
  worst-case retrieval and synthesis.
- Retrieval depth is increased per prompt (`top_k`) while preserving the
  existing ECS retrieval path.
- No artificial prompt padding or fabricated evidence is used.

## Outputs

The runner continues to produce:

- `benchmarks/output/ai_workload_requests.jsonl`
- `benchmarks/output/rag_metrics.csv`
- `benchmarks/output/rag_metrics.jsonl`

And additionally generates:

- `benchmarks/output/maximum_token_budget_report.md`

The report includes measured maxima and throughput projections at
`3 requests/minute`:

- maximum input/output/total tokens
- maximum retrieved documents/chunks/citations/prompt size
- tokens per request/minute/hour/day/month
- prompt list and rationale
- explanation of evidence size vs prompt token behavior

---

# Enterprise Benchmark — Optimum Token Settings & Timeout Resilience

The enterprise benchmark (`scripts/run_enterprise_benchmark` →
`benchmarks/ai_workload/enterprise_runner.py`) measures a realistic **Pan-India**
future-state workload. This section explains the generation/context/timeout settings
and the **staged optimization** workflow used to find the largest realistic prompt
that completes **without timing out** on the 16 GB workstation.

## Why the 512 output cap happened

Earlier runs reported exactly `output_tokens = 512`. That was the provider's built-in
output cap (`num_predict` fallback = 512), not a measured model limit. It has been made
configurable: the provider now resolves `num_predict` by precedence
**env `ECS_LLM_MAX_TOKENS` → benchmark config → `config/llm.yaml` → provider fallback (512)**.
Production defaults are unchanged (no env / no benchmark config ⇒ still 512).

## Why full 32K / 2048 / full Pan-India timed out

With `num_ctx = 32768`, `num_predict = 2048` and the **full** Pan-India context
(≈ 337,930 chars / ~84,482 estimated input tokens), the request exceeded the HTTP/model
timeout on the 16 GB box and failed with:

```text
RAG error: LLM request failed: timed out
```

A larger context window + larger output budget + a very large prompt all increase
prompt-eval and generation time. The previous "success" with `input_tokens = 16,384` /
`output_tokens = 512` simply ran under the old caps — it was not proof that the full
setting is achievable on this hardware.

## Why staged optimization is needed

The goal is **not** the largest theoretical prompt — it is the **largest realistic prompt
and output that completes successfully**. So the benchmark supports named **candidate
settings**, each a coherent bundle of `num_ctx`, `num_predict`, `timeout_seconds`, and
`pan_india_context_scale`. You run them from smallest to largest and stop at the largest
that completes. The Pan-India context is scaled by **reducing rows per block** (never
mid-text truncation), so every block stays a complete, realistic enterprise sample.

Candidates ship in `benchmarks/config/enterprise_workload_config.json` under
`benchmark_optimization.candidate_settings`:

| label                | num_ctx | num_predict | timeout (s) | context scale | ~modeled input chars / est tokens |
| -------------------- | ------- | ----------- | ----------- | ------------- | --------------------------------- |
| `safe_16k_512`       | 16,384  | 512         | 180         | 0.25          | ~124,380 / ~31,095                |
| `balanced_24k_1024`  | 24,576  | 1,024       | 300         | 0.50          | ~213,928 / ~53,482                |
| `extended_32k_2048`  | 32,768  | 2,048       | 600         | 0.75          | larger, closer to full            |

> Candidates are **never auto-run**. Nothing changes unless you pass
> `--optimization-candidate <label>`.

## How to run safe / balanced / extended

Run from the repo root on the 16 GB workstation (Docker stack + Ollama up):

```bash
# 1) Safe — should complete comfortably; establishes a floor.
PYTHONPATH=. python3 -m scripts.run_enterprise_benchmark \
  --profiles complete_compliance \
  --optimization-candidate safe_16k_512 \
  --max-rpm 3

# 2) Balanced — middle ground.
PYTHONPATH=. python3 -m scripts.run_enterprise_benchmark \
  --profiles complete_compliance \
  --optimization-candidate balanced_24k_1024 \
  --max-rpm 3

# 3) Extended — pushes context/output; may time out on constrained hardware.
PYTHONPATH=. python3 -m scripts.run_enterprise_benchmark \
  --profiles complete_compliance \
  --optimization-candidate extended_32k_2048 \
  --max-rpm 3
```

Choosing the candidate applies that candidate's `num_ctx`, `num_predict`,
`timeout_seconds`, and `pan_india_context_scale`, then runs the selected
profiles/categories as usual. You can target any profile/category (e.g.
`--profiles pie_board_enterprise_audit_pack`); use `--list` to see the catalog.

To tune a candidate, edit `candidate_settings` in the config — no Python changes needed.

## How to read the results

Startup logs (`benchmarks/output/enterprise_run.log`) print:

```
Optimization candidate: balanced_24k_1024
Configured num_ctx / num_predict / timeout_seconds
Effective num_ctx / num_predict / timeout_seconds (+ source)
Pan-India context scale
Model name / Provider
```

Every CSV row (`benchmarks/output/enterprise_requests.csv`) now carries the
self-describing settings alongside the measured values:

- `optimization_candidate`, `pan_india_context_scale`
- `modeled_context_chars`, `modeled_context_est_tokens` (MODELED, not measured)
- `configured_num_ctx` / `effective_num_ctx`
- `configured_num_predict` / `effective_num_predict`
- `configured_timeout_seconds` / `effective_timeout_seconds`
- measured `input_tokens`, `output_tokens`, `total_tokens`, latencies

`enterprise_report.json` / `enterprise_summary.json` carry the same under
`meta.generation_config` plus a `meta.benchmark_optimization` outcome:

```text
status_note: "Candidate failed: timed out after 300 seconds (1/1 request(s) timed out)"
status_note: "ok (1/1 succeeded)"
```

**Timed-out runs are reported as failures and are never converted into measured token
values.** `input_tokens` / `output_tokens` for a failed request stay at their measured
(typically 0) values.

## Interpreting safe / balanced / extended for Finance

- The **largest candidate that reports `ok`** is the defensible per-request token
  envelope to use for capacity planning and ROI — its **measured** `input_tokens`,
  `output_tokens`, `total_tokens` and `llm_latency_ms` are the inputs to budgeting.
- A candidate that reports **timed out** does **not** establish a token number; it only
  tells you that setting is not achievable on the current hardware/timeout. Either raise
  the candidate's `timeout_seconds`, lower `num_ctx` / `num_predict`, or reduce
  `pan_india_context_scale`, then re-run.
- `pan_india_context_scale` and `modeled_context_*` describe the **modeled future-state
  input volume** (clearly labelled MODELED). The LLM tokenizer remains the source of
  truth for the **measured** `input_tokens` at run time.

## Timeout configurability

The Ollama HTTP/model timeout is resolved by precedence
**env `ECS_LLM_TIMEOUT_SECONDS` → benchmark config (`ollama.timeout_seconds` or a
candidate's `timeout_seconds`) → existing provider/`config/llm.yaml` default**.
Production sets neither override, so its timeout is unchanged — the benchmark only
supplies a larger timeout through config for the duration of a benchmark run.
