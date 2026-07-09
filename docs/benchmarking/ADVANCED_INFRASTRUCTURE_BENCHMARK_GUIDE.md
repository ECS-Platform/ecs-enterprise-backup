# ECS Advanced Infrastructure Benchmark Guide

Advanced extensions to the [Infrastructure Benchmark Workbench](INFRASTRUCTURE_BENCHMARK_GUIDE.md):
**runtime telemetry, Kubernetes/GKE recommendations, stress-testing models,
calibration mode, throughput enhancements (storage / database / AI), and an
executive capacity planner**.

> Additive to the base workbench — existing estimators, CLI, and report formats
> are unchanged. All new sections are best-effort and degrade gracefully.
> Everything remains an **estimate** (documented assumptions × profile), not a
> measurement; calibrate before spend.

## New capabilities

| Capability | Module | Guide |
|-----------|--------|-------|
| Runtime telemetry | `benchmarks/capacity/telemetry.py` | [`RUNTIME_TELEMETRY_GUIDE.md`](RUNTIME_TELEMETRY_GUIDE.md) |
| Kubernetes / GKE recommendations | `kubernetes.py` | [`KUBERNETES_GKE_BENCHMARK_GUIDE.md`](KUBERNETES_GKE_BENCHMARK_GUIDE.md) |
| Stress testing | `stress.py` | [`STRESS_TESTING_GUIDE.md`](STRESS_TESTING_GUIDE.md) |
| Calibration mode | `calibration.py` | [`CALIBRATION_GUIDE.md`](CALIBRATION_GUIDE.md) |
| Storage throughput | `storage.py` (`object_storage_throughput`) | INFRASTRUCTURE guide §6 |
| Database performance | `storage.py` (`db_performance`) | INFRASTRUCTURE guide §6 |
| AI/LLM throughput | `ai.py` | INFRASTRUCTURE guide §7 |
| Executive planner | `executive.py` | [`EXECUTIVE_CAPACITY_PLANNER_GUIDE.md`](EXECUTIVE_CAPACITY_PLANNER_GUIDE.md) |

## New estimate sections

`estimate_capacity()` now also returns (best-effort): `kubernetes`,
`ai_throughput`, and enriches `db_durability` (with `performance`) and
`object_storage_detail` (with `throughput`). Telemetry, stress, calibration, and
the executive report are invoked explicitly (CLI or API).

## CLI (new flags, backward compatible)

```bash
python scripts/benchmark_capacity.py --profile phase1 --telemetry --executive
python scripts/benchmark_capacity.py --profile enterprise --kubernetes --stress
python scripts/benchmark_capacity.py --all --executive --html
python scripts/benchmark_capacity.py --profile enterprise --stress-scenario connector_storm
python scripts/benchmark_capacity.py --calibrate reports/sample_observed.json --profile phase1
```

Existing commands (`--profile`, `--all`, `--dry-run`, `--list`, `--cpu/--ram/...`)
are unchanged.

## Related
- [`INFRASTRUCTURE_BENCHMARK_GUIDE.md`](INFRASTRUCTURE_BENCHMARK_GUIDE.md)
- [`GCP_CAPACITY_BENCHMARK_GUIDE.md`](GCP_CAPACITY_BENCHMARK_GUIDE.md)
- [`README.md`](README.md)
