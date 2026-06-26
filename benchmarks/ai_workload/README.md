# ECS AI Workload Benchmark Runner

Lightweight runner that reuses existing ECS components without duplicating logic:

- `ecs_platform.rag.answer` for the RAG execution path
- Existing provider abstraction and per-request instrumentation already in ECS
- `ecs_platform.ingestion.sync_all` for optional one-time pre-run sync

## Files

- Runner: `benchmarks/ai_workload/benchmark_runner.py`
- Request-level output (when executed): `benchmarks/output/ai_workload_requests.jsonl`

## Usage

Default run:

```bash
python benchmarks/ai_workload/benchmark_runner.py
```

Run with optional JSON config:

```bash
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
  "output_dir": "benchmarks/output"
}
```

## Assessment Set

The runner executes these assessments sequentially:

1. RBI C-SITE Readiness
2. PCI DSS Readiness
3. DPSC Readiness
4. ITGRC Readiness
5. CMDB Readiness
6. VAPT Readiness
7. Enterprise Consolidated Readiness Assessment
