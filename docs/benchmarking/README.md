# ECS Benchmarking Documentation

Guides for the ECS **Infrastructure Benchmark Workbench** (GCP capacity, CPU, RAM,
database, object storage, network, cost) plus the existing LLM/prompt benchmarks.

> Estimates are from documented assumptions × scenario profiles — not
> measurements. Calibrate constants (and cost rates) from real runs before spend.

## Guides

| Guide | Covers |
|-------|--------|
| [`INFRASTRUCTURE_BENCHMARK_GUIDE.md`](INFRASTRUCTURE_BENCHMARK_GUIDE.md) | **Umbrella guide** — methodology, all sections (CPU/RAM/DB/storage/network/cost), GCP sizing, profiles, interpretation, limitations |
| [`GCP_CAPACITY_BENCHMARK_GUIDE.md`](GCP_CAPACITY_BENCHMARK_GUIDE.md) | Capacity-sizing companion — GKE / Cloud SQL / pgvector / GCS / logging focus |

The umbrella guide contains the CPU, RAM, Object Storage, Database, Network, GCP
Sizing, Cost, Methodology, Profiles, and Interpretation sections (one document,
cross-referenced) so guidance stays in sync rather than duplicated across files.

## Where each PART is documented

| Topic | Section |
|-------|---------|
| CPU benchmark | INFRASTRUCTURE_BENCHMARK_GUIDE §1, §6 (`benchmarks/capacity/workload.py`) |
| RAM benchmark | INFRASTRUCTURE_BENCHMARK_GUIDE §1, §6 (`workload.py`) |
| Database benchmark | INFRASTRUCTURE_BENCHMARK_GUIDE §1, §6 (`sizing.py`, `storage.py`) |
| Object storage benchmark | INFRASTRUCTURE_BENCHMARK_GUIDE §1, §6 (`storage.py`) |
| Network benchmark | INFRASTRUCTURE_BENCHMARK_GUIDE §1, §6 (`network.py`) |
| Connector / DB Agent benchmark | `network.py` (per-connector + DB Agent) |
| Cost estimation | INFRASTRUCTURE_BENCHMARK_GUIDE §6 (`cost.py`) |
| Capacity planning | GCP_CAPACITY_BENCHMARK_GUIDE |
| GCP sizing | INFRASTRUCTURE_BENCHMARK_GUIDE §7 + [`../deployment/GCP_DEPLOYMENT_GUIDE.md`](../deployment/GCP_DEPLOYMENT_GUIDE.md) |
| Benchmark methodology | INFRASTRUCTURE_BENCHMARK_GUIDE §2 |
| Benchmark profiles | INFRASTRUCTURE_BENCHMARK_GUIDE §8 |
| Interpretation | INFRASTRUCTURE_BENCHMARK_GUIDE §6 |

## LLM / prompt benchmarks (existing)

- [`../benchmarks/audit_llm_16gb_20gb_testing_guide.md`](../benchmarks/audit_llm_16gb_20gb_testing_guide.md)
- [`../benchmarks/audit_llm_local_benchmark_plan.md`](../benchmarks/audit_llm_local_benchmark_plan.md)
- [`../benchmarks/ECS_LOCAL_LLM_TESTING_GUIDE.md`](../benchmarks/ECS_LOCAL_LLM_TESTING_GUIDE.md)
- [`../developer-manual/PROMPT_TESTING_GUIDE.md`](../developer-manual/PROMPT_TESTING_GUIDE.md)

## Run

```bash
python scripts/benchmark_capacity.py --all
python scripts/benchmark_capacity.py --profile enterprise --cost
```
