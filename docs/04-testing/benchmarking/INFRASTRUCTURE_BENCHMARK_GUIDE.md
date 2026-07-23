# ECS Enterprise Infrastructure Benchmark Guide

The ECS **Infrastructure Benchmark Workbench** estimates the GCP infrastructure
needed to run ECS at a given scale — **CPU, RAM, database, object storage,
network, and cost** — across named scenario profiles (developer laptop → 2000
applications), and recommends GKE / Cloud SQL / GCS / logging sizing.

> **What this is / is not.** Transparent **estimates** from documented per-unit
> assumptions × a scenario profile — **not** measurements and **not** a billing
> quote. Calibrate the constants from real benchmark runs (and replace cost rates
> with a current quote) before any spend decision.
>
> **Reuse (no duplication).** It extends the existing ECS benchmark/token
> framework and reuses the real connector registry:
> - Token sizing: `modules/audit_intelligence/llm/token_estimator.py`
> - LLM/prompt benchmarks (feed MEASURED tokens): `benchmarks/ai_workload/`,
>   `scripts/run_audit_llm_benchmark.py`
> - Connector set: `modules/operations/integrations.list_adapters()`
> - Capacity core: `benchmarks/ai_workload/capacity_planning.py`

**Code:** `benchmarks/capacity/` (`profiles`, `sizing`, `workload`, `storage`,
`network`, `cost`, `report`). **CLI:** `scripts/benchmark_capacity.py`.
**Tests:** `tests/test_capacity_benchmark.py`.

---

## 1. Scope (what it estimates)

| Area | Module | Covers |
|------|--------|--------|
| GKE compute (coarse) | `sizing.py` | peak cores/RAM, pod requests/limits, replicas, node pool |
| **CPU (per-workload)** | `workload.py` | REST/auth/RBAC, connector fetch+parse, evidence normalize/validate/upload, SHA-256, scheduler/retry/DLQ, DB Agent + query, prompt/embedding/vector search, JSON/CSV/Excel/PDF parse, ZIP/compression, report gen, background workers, health checks |
| **RAM (per-consumer)** | `workload.py` | avg/peak/high-water, per-API/connector/worker/prompt/embedding/upload, pools, caches, large objects, concurrent up/downloads |
| **Database + durability** | `sizing.py` + `storage.py` | metadata/evidence/observation/prompt/benchmark/connector/scheduler growth, indexes, partitions, vacuum/autovacuum, checkpoint, WAL, backup/restore, Cloud SQL tier, pgvector storage |
| **Object storage** | `sizing.py` + `storage.py` | files/day-month-year, size distribution (avg/median/p95/max), versions, dedup, compression, SHA-256 overhead, per-content-type, retention 1/3/5/7/10y, lifecycle (Nearline/Coldline/Archive), bucket layout |
| **Network** | `network.py` | AWS↔GCP cross-cloud, connector bandwidth, DB Agent, evidence up/down, object storage, per-SaaS |
| **Connector benchmark** | `network.py` | per-connector latency/bandwidth/payload/CPU/RAM/retry/timeout/normalize/evidence |
| **DB Agent benchmark** | `network.py` | connect/pool/query latency/rows/evidence/normalize/hash/upload/parallel |
| **Cost** | `cost.py` | compute, Cloud SQL, storage, logging, monitoring, network; monthly/annual/5-year + growth curve |

## 2. Methodology

For each profile the workbench computes each area by **pure arithmetic**:
`Σ(activity count × per-unit cost)`, then applies working-hours averaging and a
`peak_to_average_factor` for peaks. Provenance is explicit: **measured** (only if
you pass a real benchmark), **estimated** (per-unit), **projected** (scale ×
per-unit). Outputs are tagged `ESTIMATE`.

Per-unit constants are documented + overridable in each module's `*Constants`
dataclass (`SizingConstants`, `WorkloadConstants`, `DbDurabilityConstants`,
`ObjectStorageConstants`, `NetworkConstants`, `CostRates`).

## 3. Assumptions

- **Scenario drivers** (apps, frameworks, controls/app, evidences/app, daily
  runs, evidence size, retention) live in `benchmarks/capacity/profiles.py`.
- **Per-unit costs** live in the module `*Constants`. Defaults are conservative
  planning values, not measurements.
- Defaults: `e2-standard-4` nodes, 75% node allocatable, `peak_to_average=3`,
  HA floor 2 replicas, pgvector 768-dim float32, 35% DB index overhead.
- **Cost rates** are illustrative GCP-like list prices (`CostRates`) — replace
  with a real quote; excludes committed-use discounts and support.

## 4. How the token benchmark feeds the infra benchmark

Prompt CPU/RAM and DB prompt-history / vector growth depend on token volume:
- **Estimated (default):** a representative audit prompt is measured via
  `token_estimator.estimate_prompt()` (chars/4) — no model, no network.
- **Measured (recommended):** run
  `scripts/run_audit_llm_benchmark.py --profile local_16gb_safe --mode live`,
  then pass observed `avg_input_tokens/avg_output_tokens/avg_total_tokens` as
  `measured_tokens=` to `estimate_capacity(...)`.

## 5. How to run

```bash
# Per profile / all (writes JSON + Markdown + CSV + 7 section reports)
python scripts/benchmark_capacity.py --profile phase1
python scripts/benchmark_capacity.py --profile enterprise
python scripts/benchmark_capacity.py --all

# Print a specific section report to the console
python scripts/benchmark_capacity.py --all --cpu
python scripts/benchmark_capacity.py --all --ram
python scripts/benchmark_capacity.py --all --database
python scripts/benchmark_capacity.py --all --network
python scripts/benchmark_capacity.py --all --storage
python scripts/benchmark_capacity.py --all --cost

# Summary only, write nothing / list profiles
python scripts/benchmark_capacity.py --all --dry-run
python scripts/benchmark_capacity.py --list
```

Outputs (default `reports/capacity_benchmarks/`): `capacity.{json,md,csv}` plus
`capacity_{cpu,ram,storage,database,network,cost,executive}.md`.

## 6. Interpreting the numbers

- **CPU:** `peak_cores` + the per-operation core-hours drive pod/replica sizing.
- **RAM:** `peak_total_gib` + `high_water_mark_mib` size pod memory + pools.
- **Database:** `year_1_total` / `year_N_total` GiB are **metadata + vectors**
  only (evidence files live in GCS); `wal_gib_per_day` + backup/restore size the
  Cloud SQL disk + backup window.
- **Object storage:** dominated by evidence × versions × retention; use the
  lifecycle tiers to cut cost.
- **Network:** watch `cross_cloud_aws_gcp_gib_per_month` (Net Banking on AWS,
  Mobile Banking on GCP) — cross-cloud egress is a direct cost driver.
- **Cost:** `monthly_total` / `annual_total` / `five_year_total` with a growth
  curve; treat as directional until rates are quoted.

## 7. GCP sizing recommendations

Use `recommended_pod` requests/limits, `recommended_replicas`, and
`recommended_nodes` × machine type as starting points; deploy across ≥2 AZs with
an HPA at the target utilization. Cloud SQL: start at `recommended_cloud_sql.tier`
with regional HA + PITR. See
[`../deployment/GCP_DEPLOYMENT_GUIDE.md`](../../03-development/deployment/GCP_DEPLOYMENT_GUIDE.md).

## 8. Benchmark profiles

`laptop` · `pilot` · `demo` · `phase1` (NB/MB/Payments) · `phase2` (15) ·
`apps25` · `apps50` · `enterprise` (100) · `apps250` · `pan-bank` (500) ·
`apps1000` · `large` (2000). Each defines apps/frameworks/controls/evidence,
daily connector/prompt/scheduler/API activity, evidence size, and retention.

## 9. Limitations

- Estimates, not measurements — calibrate constants from real runs.
- Single-region figures; multiply for multi-region/DR.
- Coarse concurrency model (working-hours avg × peak factor); load-test for strict
  SLOs ([`../testing/ECS_LOAD_TESTING_REFERENCE.md`](../testing/ECS_LOAD_TESTING_REFERENCE.md)).
- Cost rates are illustrative; assumes state externalized for horizontal scaling.

## Advanced extensions

Telemetry, Kubernetes/GKE recommendations, stress testing, calibration, throughput
enhancements, and the executive planner are documented in:
- [`ADVANCED_INFRASTRUCTURE_BENCHMARK_GUIDE.md`](ADVANCED_INFRASTRUCTURE_BENCHMARK_GUIDE.md) (umbrella)
- [`RUNTIME_TELEMETRY_GUIDE.md`](RUNTIME_TELEMETRY_GUIDE.md) · [`KUBERNETES_GKE_BENCHMARK_GUIDE.md`](KUBERNETES_GKE_BENCHMARK_GUIDE.md) · [`STRESS_TESTING_GUIDE.md`](STRESS_TESTING_GUIDE.md) · [`CALIBRATION_GUIDE.md`](CALIBRATION_GUIDE.md) · [`EXECUTIVE_CAPACITY_PLANNER_GUIDE.md`](EXECUTIVE_CAPACITY_PLANNER_GUIDE.md)

## Related
- [`GCP_CAPACITY_BENCHMARK_GUIDE.md`](GCP_CAPACITY_BENCHMARK_GUIDE.md) — the capacity-sizing companion (GKE/Cloud SQL/GCS focus)
- [`../deployment/GCP_DEPLOYMENT_GUIDE.md`](../../03-development/deployment/GCP_DEPLOYMENT_GUIDE.md)
- [`../architecture/ENTERPRISE_ARCHITECTURE.md`](../../02-architecture/architecture/ENTERPRISE_ARCHITECTURE.md)
- [`../benchmarks/audit_llm_16gb_20gb_testing_guide.md`](../benchmarks/audit_llm_16gb_20gb_testing_guide.md)
- [`../developer-manual/PROMPT_TESTING_GUIDE.md`](../../03-development/developer-manual/PROMPT_TESTING_GUIDE.md)
