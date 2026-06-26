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

---

# Enterprise AI Workload Benchmark (capacity planning)

The lightweight runner above is the original 7-assessment smoke benchmark. The
**enterprise** benchmark extends it into a capacity-planning-grade suite for Neev
sizing. It reuses the same ECS pipeline and instrumentation — it does not replace
or duplicate anything.

## Components (all reused; only `enterprise_runner.py` is new glue)

| Module | Role | Status |
|--------|------|--------|
| `workload_profiles.py` | 20 realistic enterprise workload scenarios (data only) | existing |
| `enterprise_runner.py` | Orchestrates profiles -> `ecs_platform.rag.answer` -> metrics -> report | **new (integration glue)** |
| `bench_statistics.py` | min / avg / median / max / P90 / P95 / P99 / stddev | existing |
| `capacity_planning.py` | Measured / Estimated / Projected sizing + cost inputs | existing |
| `reporting.py` | Builds `enterprise_report.json` / `enterprise_summary.json` / `enterprise_results.csv` | existing |
| `ecs_platform.rag.answer` | RAG pipeline (retrieval + prompt build + provider call) | existing ECS |
| `ecs_platform.llm_engine.provider.generate_with_metadata` | Token instrumentation | existing ECS |
| `ecs_platform.llm_engine.metrics_logger` | Persists per-request metric rows | existing ECS |

## Workload catalog (20 scenarios)

- **Prompt×Response size matrix (6):** small→small, small→large, medium→medium,
  medium→large, large→small, large→large.
- **Retrieved-context stress (2):** maximum context→normal answer; maximum
  context→maximum detailed assessment (worst-case realistic token consumption).
- **Named enterprise workloads (12):** large multi-document audit, complete
  compliance assessment, enterprise risk assessment, CMDB evidence analysis,
  ServiceNow evidence correlation, RBI C-SITE, PCI DSS, Windows / Linux /
  Database / Middleware baselines, Backup & DR.

Maximum-token scenarios combine the widest realistic retrieval (`top_k=40`) with
the most detailed realistic assessment instruction — no padding or repeated text.

List the catalog (no execution):

```bash
python scripts/run_enterprise_benchmark.py --list
```

## Usage

```bash
# Full 20-scenario suite with defaults / config file
python scripts/run_enterprise_benchmark.py
python scripts/run_enterprise_benchmark.py --config benchmarks/config/enterprise_workload_config.json

# Subset by profile key or category
python scripts/run_enterprise_benchmark.py --profiles maxctx_max,complete_compliance
python scripts/run_enterprise_benchmark.py --categories framework,baseline

# Equivalent module form
python -m benchmarks.ai_workload.enterprise_runner --config benchmarks/config/enterprise_workload_config.json
```

## Config (`benchmarks/config/enterprise_workload_config.json`)

```json
{
  "role": "cio",
  "user": "benchmark-runner",
  "concurrency": 1,
  "max_requests_per_minute": 3,
  "output_dir": "benchmarks/output",
  "run_sync_once": false,
  "reindex_before_run": false,
  "profile_keys": [],
  "categories": [],
  "memory_guard_min_mb": 512,
  "capacity_assumptions": { "concurrent_users": 50, "requests_per_user_per_day": 8, "...": "see capacity_planning.CapacityAssumptions" }
}
```

## Measurements captured per request

- **Retrieval:** retrieved documents, retrieved chunks, retrieval latency.
- **Prompt:** system prompt size (chars/bytes), user prompt size (chars/bytes),
  measured prompt size (chars), input tokens; retrieved-context chars and prompt
  bytes are **derived** and suffixed `_derived`.
- **LLM:** output tokens, total tokens, inference latency, provider, model.
- **Statistics** (per metric): min, average, median, max, P90, P95, P99, stddev.

If the LLM is unavailable the RAG pipeline returns `fallback`/`no_evidence`; the
runner records measured retrieval/prompt fields from the persisted metric row,
leaves token/LLM-latency at their measured values, and continues.

## Capacity planning (Measured / Estimated / Projected — never mixed)

- **Measured:** avg/peak tokens, avg/p95 end-to-end latency (observed).
- **Estimated:** single-stream requests/min & requests/hour from measured latency.
- **Projected:** requests per day/month/year, peak rpm, monthly/yearly tokens,
  storage & vector growth, and cost inputs — operator assumptions × measured tokens.

## Outputs (`benchmarks/output/`)

- `enterprise_requests.jsonl` — one row per request (flushed immediately).
- `enterprise_report.json` — full statistics + per-category + worst-case + capacity.
- `enterprise_summary.json` — condensed headline view.
- `enterprise_results.csv` — flat per-request table for spreadsheets.
- `enterprise_run_meta.json`, `enterprise_run.log` — run status / provenance.
- `rag_metrics.jsonl` / `rag_metrics.csv` — raw rows from the existing instrumentation.

## Memory & rate safety

Single stream (`concurrency=1`), rate-limited by `max_requests_per_minute`, each
result flushed + fsync'd immediately, large objects released and `gc.collect()`
after every request, the final report rebuilt from disk (no in-memory retention),
and a soft memory guard (`memory_guard_min_mb`) that stops gracefully while
preserving all completed results.
