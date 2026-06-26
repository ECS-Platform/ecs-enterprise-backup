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
