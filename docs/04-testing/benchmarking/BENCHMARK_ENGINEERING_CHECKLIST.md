# ECS Infrastructure Benchmark — Engineering Checklist

Final engineering closure checklist. `[x]` = implemented + tested + documented in
this repo; `[ ]` = requires production data / external systems (out of the
estimation model's scope).

## Architecture & capacity
- [x] Modular package (`benchmarks/capacity/`) — no duplication, backward compatible
- [x] 12 scenario profiles (laptop → 2000 apps) with phase-wise sizing
- [x] Deterministic, offline, pure-arithmetic estimation core
- [x] Traceability profile→workload→CPU→RAM→storage→DB→network→GKE→cost ([diagram](BENCHMARK_TRACEABILITY.md))

## CPU
- [x] Per-operation CPU model (31 ops) → peak cores (`workload.cpu_breakdown`)
- [x] Coarse GKE compute (`sizing._gke_compute`)
- [ ] Calibrated against production CPU telemetry

## RAM
- [x] Per-consumer RAM + peak + high-water (`workload.ram_breakdown`)
- [ ] Calibrated against production RSS

## Storage — object storage
- [x] Files/day-month-year, size distribution (avg/median/p95/max)
- [x] Versions, dedup, compression, per-content-type, retention 1/3/5/7/10y
- [x] Lifecycle tiers + bucket layout (`storage.object_storage_detail`)
- [x] Throughput: upload/download latency, concurrency, multipart, ops-cost
- [ ] Calibrated against bucket stats

## Database
- [x] Row/vector growth, index overhead, Cloud SQL tier (`sizing._postgres`)
- [x] Durability: WAL/vacuum/checkpoint/backup/restore/partition (`storage.db_durability`)
- [x] Performance: QPS/TPS, pool, slow-query risk, restore-time (`storage.db_performance`)
- [ ] Calibrated against `pg_stat_*` / real sizes

## Networking
- [x] Bandwidth incl. AWS↔GCP cross-cloud (`network.network_bandwidth`)
- [ ] Calibrated against VPC flow logs

## Scheduler
- [x] Scheduler activity in CPU/RAM/queue models + stress (overload/retry/DLQ)
- [ ] Calibrated against real scheduler metrics

## Connector Framework
- [x] Per-connector benchmark (19 adapters) — latency/bandwidth/payload/CPU/RAM/retry/normalize (`network.connector_benchmark`)
- [x] Reuses the live connector registry (no hardcoded list)
- [ ] Calibrated against real connector runs

## Database Agent
- [x] Connect/pool/query/rows/evidence/normalize/hash/upload/parallel (`network.db_agent_benchmark`)
- [ ] Calibrated against real DB Agent execution

## Prompt / AI benchmark
- [x] AI throughput: prompts/tokens/embeddings per sec, concurrency, model notes (`ai.ai_throughput`)
- [x] Reuses existing token estimator + supports `measured_tokens`
- [ ] Live audit-LLM benchmark run for measured tokens/latency

## Telemetry
- [x] `RuntimeTelemetry` (psutil/resource/tracemalloc optional, graceful, JSON)
- [x] Never raises / suppresses; availability reported

## Calibration
- [x] Observed↔estimate comparison → factors + recommended constants + confidence (`calibration.calibrate`)
- [x] Closed-loop improvement workflow documented
- [ ] ≥3 calibration cycles against production telemetry

## Stress testing
- [x] 15 scenarios + impact/bottleneck/mitigation (`stress`)
- [ ] Executed load test to validate modeled limits

## Reports
- [x] JSON, Markdown, CSV, recommendation table, 7 section reports
- [x] Executive report (MD/JSON/CSV/HTML) + committed sample
- [x] Kubernetes + cost sections

## Documentation
- [x] 15 cross-linked guides (infrastructure, advanced, capacity, telemetry, kubernetes, stress, calibration, executive, assumptions, traceability, reproducibility, maturity, checklist, README)
- [x] Every doc links to the core guides; README index updated
- [x] Assumptions catalogued with source/reason/formula/confidence/calibration

## Tests
- [x] 67 tests (`tests/test_capacity_benchmark.py`) — estimators, profiles, reports, CLI, telemetry, k8s, stress, calibration, throughput, AI, executive
- [x] `compileall` clean; deterministic

## Deployment / Operations
- [x] GKE/Cloud SQL/GCS/logging recommendations + deployment guide cross-link
- [x] Reproducibility guide (commands/outputs/config/troubleshooting)
- [ ] Recommendations validated against a real GKE/Cloud SQL deployment

## Monitoring / Logging
- [x] Logging-volume estimate + monitoring cost + cross-link to monitoring guide
- [ ] Wired to Cloud Monitoring for measured inputs

## Runbooks
- [x] Cross-links to `docs/03-development/runbooks/` (degraded readiness, DB, scheduler, etc.)
- [x] Benchmark troubleshooting section

## Related
- [`BENCHMARK_MATURITY_ASSESSMENT.md`](BENCHMARK_MATURITY_ASSESSMENT.md) · [`BENCHMARK_ASSUMPTIONS_AND_LIMITATIONS.md`](BENCHMARK_ASSUMPTIONS_AND_LIMITATIONS.md) · [`BENCHMARK_TRACEABILITY.md`](BENCHMARK_TRACEABILITY.md) · [`README.md`](README.md)
