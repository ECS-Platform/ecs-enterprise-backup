# ECS GCP Capacity Benchmark Guide

Estimate the GCP/GKE infrastructure needed to run ECS at a given scale — GKE
compute, Cloud SQL / pgvector, GCS object storage, and Cloud Logging volume —
across named scenario profiles (demo → large enterprise).

> **What this is / is not.** This produces **transparent estimates** from
> documented per-unit assumptions × a scenario profile. It is **not** a
> measurement and **not** a billing quote. Calibrate the constants from a real
> benchmark run before committing to spend.
>
> **Reuse (no duplication).** It extends the existing ECS benchmark/token
> framework and does not reimplement any of it:
> - Token sizing: `modules/audit_intelligence/llm/token_estimator.py`
> - Capacity arithmetic reference: `benchmarks/ai_workload/capacity_planning.py`
>   (`CapacityAssumptions`)
> - LLM benchmark (feeds MEASURED tokens): `scripts/run_audit_llm_benchmark.py`,
>   [`audit_llm_16gb_20gb_testing_guide.md`](../benchmarks/audit_llm_16gb_20gb_testing_guide.md)

Code: `benchmarks/capacity/` (`profiles.py`, `sizing.py`, `report.py`).
CLI: `scripts/benchmark_capacity.py`. Tests: `tests/test_capacity_benchmark.py`.

---

## 1. Methodology

For each scenario profile the estimator computes four sections by pure arithmetic:

1. **GKE compute** — daily CPU-ms = Σ(workload count × per-unit CPU-ms) across API
   requests, connector runs, scheduler jobs, and prompt runs; converted to average
   cores over working hours, then **peak cores** via `peak_to_average_factor`.
   Replicas = peak cores ÷ (pod CPU request × target utilization), floored at the
   HA minimum. Node pool = replicas × pod requests ÷ node allocatable.
2. **PostgreSQL / pgvector** — row counts × per-row bytes × (1 + index overhead);
   vectors = `embedding_dimensions × 4B × 1.3` × chunks. Year-1 and Year-N totals;
   Cloud SQL tier chosen from the projected size.
3. **GCS object storage** — evidence count × avg size, plus yearly growth
   (new evidence, versions, benchmark exports, audit reports, archived logs);
   Year-1 and Year-N (retention) totals.
4. **Logging** — event counts × events-per-unit × bytes-per-event for
   application / connector / scheduler / LLM / audit logs → per-day / -month / -year.

The three provenance ideas from the existing framework are preserved: **measured**
(only if you pass a real benchmark), **estimated** (single-unit costs), and
**projected** (scale × per-unit). Output is tagged `ESTIMATE`.

## 2. Assumptions

- **Per-unit costs** live in `benchmarks/capacity/sizing.py::SizingConstants`
  (CPU-ms/RAM per API request, connector run, scheduler job, prompt run; pod
  baseline/shape; per-row DB bytes; embedding dims; log bytes/event; retention
  factors). Every value is documented and overridable.
- **Scenario drivers** live in `benchmarks/capacity/profiles.py::CapacityProfile`
  (apps, frameworks, controls/app, evidences/app, daily runs, evidence size,
  retention). Tune per engagement.
- Defaults: `e2-standard-4` nodes (4 vCPU / 16 GiB), 75% node allocatable,
  `peak_to_average_factor=3`, HA floor of 2 replicas, pgvector 768-dim float32,
  35% index overhead.

## 3. How the token benchmark feeds the infra benchmark

Prompt CPU/RAM and DB prompt-history/vector growth depend on token volume:

- **Estimated (default):** `sizing._avg_prompt_tokens()` calls
  `token_estimator.estimate_prompt()` on a representative audit prompt (chars/4,
  the same estimator ECS uses everywhere) — no model, no network.
- **Measured (recommended for real sizing):** run the audit-LLM benchmark
  (`scripts/run_audit_llm_benchmark.py --profile local_16gb_safe --mode live`),
  take the observed `avg_input_tokens` / `avg_output_tokens` / `avg_total_tokens`,
  and pass them as `measured_tokens=` to `estimate_capacity(...)`. The report then
  tags `token_feed._source = "measured"`.

## 4. How to run

```bash
# One profile (writes JSON + Markdown + CSV to reports/capacity_benchmarks/)
python scripts/benchmark_capacity.py --profile phase1
python scripts/benchmark_capacity.py --profile enterprise

# All profiles
python scripts/benchmark_capacity.py --all

# Print the summary only, write nothing
python scripts/benchmark_capacity.py --all --dry-run

# Custom output dir / list profiles
python scripts/benchmark_capacity.py --profile phase1 --out reports/capacity
python scripts/benchmark_capacity.py --list
```

Outputs (in `--out`, default `reports/capacity_benchmarks/`):
`capacity.json` (full detail + recommendation table), `capacity.md` (readable
report), `capacity.csv` (one row per profile).

## 5. Interpreting the numbers

- **CPU/RAM:** `peak_cores` / `peak_ram_mib` are the sizing drivers; the
  `recommended_pod` requests/limits and `recommended_replicas` are what you put in
  the Deployment. `daily_cpu_core_hours` breaks demand down by workload class.
- **Replicas / nodes:** replicas satisfy peak cores at the HPA target utilization
  (min 2 for HA); nodes pack replicas onto `e2-standard-4` at 75% allocatable
  (+1 headroom, min 2 for multi-AZ).
- **Cloud SQL:** `year_1_total` / `year_5_total` GiB are **metadata + vectors**
  only — evidence *files* live in GCS, so DB size stays modest. The tier is a
  starting point; validate against real query load.
- **GCS:** dominated by evidence files × versions × retention.
- **Logging:** Cloud Logging **ingestion** volume/day — a direct cost driver;
  `log_export_fraction` models what is archived to GCS.

## 6. GKE sizing recommendations

- Use the `recommended_pod` requests/limits verbatim as a starting point; set an
  HPA to the `target_cpu_utilization` (default 60%).
- Deploy `recommended_replicas` across ≥2 AZs on `recommended_nodes` ×
  `e2-standard-4` (adjust machine type via `SizingConstants.node_vcpu/ram`).
- Run the **LLM-RAG** workload as a separate pool (heavier RAM); the prompt
  per-unit RAM constant reflects that working set.

## 7. Cloud SQL sizing recommendations

- Start at the reported `recommended_cloud_sql.tier`; enable **regional HA** for
  prod/dr and **PITR/backups** for banking retention.
- Enable `pgvector` on the vector DB (or use **AlloyDB**). See
  [`../deployment/GCP_DEPLOYMENT_GUIDE.md`](../deployment/GCP_DEPLOYMENT_GUIDE.md) §4.

## 8. GCS retention assumptions

- Evidence is versioned (`evidence_versions_per_year`) and retained for
  `retention_years` (5–7y in the larger profiles). Enable bucket **versioning**,
  **CMEK**, and a **lifecycle policy** matching your audit retention.

## 9. Limitations

- Estimates, not measurements — accuracy depends on the constants; calibrate from
  a real benchmark before spend decisions.
- Single-region figures; multiply for multi-region/DR replicas + storage.
- Assumes state is externalized (Redis/PostgreSQL) so replicas scale horizontally
  (see the architecture review's R1).
- Cost is intentionally **not** computed (rates are engagement-specific); pair the
  volumes here with current GCP pricing.
- Concurrency model is coarse (working-hours average × peak factor); for strict
  SLOs, load-test with [`../testing/ECS_LOAD_TESTING_REFERENCE.md`](../testing/ECS_LOAD_TESTING_REFERENCE.md).

## Related
- [`../deployment/GCP_DEPLOYMENT_GUIDE.md`](../deployment/GCP_DEPLOYMENT_GUIDE.md)
- [`../architecture/ENTERPRISE_ARCHITECTURE.md`](../architecture/ENTERPRISE_ARCHITECTURE.md)
- [`../benchmarks/audit_llm_16gb_20gb_testing_guide.md`](../benchmarks/audit_llm_16gb_20gb_testing_guide.md)
- [`../developer-manual/PROMPT_TESTING_GUIDE.md`](../developer-manual/PROMPT_TESTING_GUIDE.md)
