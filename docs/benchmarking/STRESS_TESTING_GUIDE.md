# ECS Stress Testing Guide

`benchmarks/capacity/stress.py` **models** adverse load scenarios (no real
external calls) by applying documented multipliers to a profile's baseline
activity and re-running the CPU/RAM/network estimators.

## Scenarios
| Scenario | Models |
|----------|--------|
| `connector_storm` | all connectors firing together (×10 runs) |
| `scheduler_overload` | job surge (×12 jobs) |
| `retry_storm` | mass transient failures (×4 runs + jobs) |
| `dead_letter_growth` | unrecoverable-failure backlog |
| `concurrent_uploads` | evidence upload concurrency (×6) |
| `concurrent_prompts` | prompt-run concurrency (×8) |
| `concurrent_db_queries` | DB Agent query concurrency (×5) |
| `object_storage_burst` | GCS write burst (×8) |
| `large_evidence_burst` | large-file burst (×3 runs, ×8 size) |
| `sim_100/500/1000_connectors` | fixed-scale connector-execution simulation |
| `sim_100/500/1000_db_targets` | fixed-scale database-target simulation |

## Per-scenario output
CPU / RAM / network / storage / queue **impact factors** (stressed ÷ baseline),
the **expected bottleneck**, and a **recommended mitigation**.

## CLI
```bash
python scripts/benchmark_capacity.py --profile enterprise --stress
python scripts/benchmark_capacity.py --profile enterprise --stress-scenario connector_storm
```

## Interpreting
- Impact factor > 1 shows how far a scenario pushes a resource beyond baseline
  peak; use it to set HPA max, worker pool size, and Cloud SQL connection limits.
- Bottleneck + mitigation are the operational actions (rate-limit, backoff,
  circuit-breaker, dedicated pools, PgBouncer, multipart uploads, lifecycle).

## Basis & limits
Multiplier model over baseline activity re-run through the real estimators — a
planning tool, not an executed load test. For measured limits, pair with
[`../testing/ECS_LOAD_TESTING_REFERENCE.md`](../testing/ECS_LOAD_TESTING_REFERENCE.md).

## Related
- [`ADVANCED_INFRASTRUCTURE_BENCHMARK_GUIDE.md`](ADVANCED_INFRASTRUCTURE_BENCHMARK_GUIDE.md)
- [`KUBERNETES_GKE_BENCHMARK_GUIDE.md`](KUBERNETES_GKE_BENCHMARK_GUIDE.md)
