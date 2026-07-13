# ECS GCP Capacity Sizing Report

> **Provenance:** ESTIMATE — documented per-unit assumptions × scenario profile (see `benchmarks/capacity/sizing.py::SizingConstants`). Not a measurement. Calibrate constants from a real benchmark run before committing to spend. See [`docs/benchmarking/GCP_CAPACITY_BENCHMARK_GUIDE.md`](../../docs/benchmarking/GCP_CAPACITY_BENCHMARK_GUIDE.md).

## Recommendation summary

| Profile | Apps | Replicas | GKE nodes | Node type | Cloud SQL | SQL GiB | GCS y1 GiB | GCS y5 GiB | Logs/day GiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| enterprise | 100 | 3 | 2 | e2-standard-4 | db-custom-2-7680 | 20 | 68.7311 | 326.4896 | 0.2426 |

## Enterprise — 100 applications (`enterprise`)

_Enterprise-wide GRC across ~100 applications._

- **Scale:** 100 apps · 10 frameworks · 12000 controls · 15000 evidences · retention 5y
- **Daily activity:** 120,000 API req · 1,200 connector runs · 1,500 prompt runs · 800 scheduler jobs

**GKE compute**

- Peak ~0.756 cores, ~300.4 MiB RAM (peak).
- Pod requests: 500m CPU / 1024Mi RAM (limits 1000m / 2048Mi).
- **3 replicas** on **2 × e2-standard-4** nodes.

**PostgreSQL / pgvector**

- Year 1 ≈ 2.1888 GiB, Year 5 ≈ 9.8349 GiB (vectors now 0.2232 GiB).
- Recommended Cloud SQL: **db-custom-2-7680** (2 vCPU / 7.5 GiB, 20 GiB, zonal (uat) / regional (prod)).

**GCS object storage**

- Year 1 ≈ 68.7311 GiB, Year 5 ≈ 326.4896 GiB.

**Logging (Cloud Logging)**

- ~0.2426 GiB/day, ~88.5544 GiB/year.

