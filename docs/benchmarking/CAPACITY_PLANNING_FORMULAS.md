# ECS Benchmark — Capacity Planning Formulas

Consolidated formulas used by the Infrastructure Benchmark Workbench, with simple
worked examples. Source of truth: `benchmarks/capacity/sizing.py` and module
constants.

> Assumption values and confidence levels:
> [`BENCHMARK_ASSUMPTIONS_AND_LIMITATIONS.md`](BENCHMARK_ASSUMPTIONS_AND_LIMITATIONS.md).

## Notation

| Symbol | Meaning |
|--------|---------|
| `p` | `CapacityProfile` fields |
| `c` | `SizingConstants` fields |
| `GiB` | 1024³ bytes |

---

## CPU estimation

**Daily CPU-ms per class:**
```
api_cpu_ms    = p.api_requests_per_day    × c.cpu_ms_per_api_request
conn_cpu_ms   = p.connector_runs_per_day  × c.cpu_ms_per_connector_run
sched_cpu_ms  = p.scheduler_jobs_per_day  × c.cpu_ms_per_scheduler_job
prompt_cpu_ms = p.prompt_runs_per_day     × c.cpu_ms_per_prompt_run
total_cpu_ms  = api + conn + sched + prompt
```

**Average and peak cores (working hours):**
```
work_seconds = c.working_hours_per_day × 3600
avg_cores    = (total_cpu_ms / 1000) / work_seconds
peak_cores   = avg_cores × c.peak_to_average_factor    # default ×3
```

**Detailed breakdown** (`workload.cpu_breakdown`): same pattern for 31 operation
classes with `WorkloadConstants` per-op CPU-ms.

---

## RAM estimation

**Coarse peak RAM** (`sizing._gke_compute`):
```
peak_rps     = (p.api_requests_per_day / work_seconds) × peak_to_average_factor
req_ram_mib  = peak_rps × c.ram_mib_per_api_request
peak_ram_mib = req_ram_mib + c.ram_mib_per_prompt_run
```

**Detailed** (`workload.ram_breakdown`): per-consumer peak MiB summed to
`peak_total_mib` and `high_water_mark_mib`.

---

## GKE replica count

```
usable_cpu_per_pod = (c.pod_cpu_request_ms / 1000) × c.target_cpu_utilization   # 0.6
replicas_for_cpu   = peak_cores / usable_cpu_per_pod
recommended_replicas = max(c.min_replicas, int(replicas_for_cpu) + 1)           # min 2
```

---

## Node count

```
total_cpu_cores = replicas × (c.pod_cpu_request_ms / 1000)
total_ram_gib   = replicas × (c.pod_ram_request_mib / 1024)
alloc_cpu       = c.node_vcpu × c.node_allocatable_factor      # 4 × 0.75 = 3
alloc_ram       = c.node_ram_gib × c.node_allocatable_factor  # 16 × 0.75 = 12
nodes           = max(2, int(max(total_cpu/alloc_cpu, total_ram/alloc_ram)) + 1)
```

---

## Pod request / limit sizing

Defaults from `SizingConstants` (not derived per profile in coarse model):
```
cpu_request  = 500m    cpu_limit  = 1000m
ram_request  = 1024Mi  ram_limit  = 2048Mi
```
`kubernetes.recommend()` flags when `ram_breakdown.peak_total_mib / replicas > request`.

---

## Cloud SQL tier sizing

```
idx = 1 + c.pg_index_overhead_factor    # 1.35

control_bytes      = p.total_controls() × c.bytes_per_control_row × idx
evidence_meta      = p.total_evidences() × c.bytes_per_evidence_meta_row × idx
vector_bytes       = chunks × (dims × 4 × 1.3)
yearly_growth      = observations + prompt_history + benchmark_results + new_vectors
year1_gib          = (base + yearly_growth) / GiB

Tier thresholds (_cloud_sql_tier):
  ≤ 20 GiB  → db-custom-2-7680
  ≤ 100 GiB → db-custom-4-15360
  ≤ 500 GiB → db-custom-8-30720
  else      → db-custom-16-61440
```

---

## PostgreSQL metadata growth

```
obs_year       = p.apps × c.observations_per_app_per_year
prompt_rows/yr = p.prompt_runs_per_day × 22 × 12
bench_rows/yr  = 52 × 50    # weekly × ~50 prompts
growth/year    = (obs + prompt + bench) × bytes_per_row × idx
year5          = base + growth × p.retention_years
```

---

## PGVector growth

```
vec_bytes/chunk = embedding_dimensions × 4 × vector_index_overhead_factor   # 768×4×1.3
total_chunks    = p.total_evidences() × chunks_per_evidence               # ×4
new_chunks/yr   = (apps × new_evidence_per_app_per_month × 12) × chunks_per_evidence
```

---

## Object storage growth

```
evidence_bytes     = p.total_evidences() × p.avg_evidence_size_kb × 1024
version_bytes/yr   = evidence_bytes × (p.evidence_versions_per_year - 1)
new_evidence/yr    = apps × new_evidence_per_app_per_month × 12 × avg_evidence_size_kb × 1024
reports/yr         = apps × reports_per_app_per_month × 12 × audit_report_mb × MiB
log_archive/yr     = logging.total_bytes_per_year × log_export_fraction
year1_gib          = (evidence + growth_components) / GiB
year5_gib          = (evidence + growth × retention_years) / GiB
```

**Retention, compression, lifecycle** (`storage.object_storage_detail`):
```
after_dedup   = raw_gib × (1 - dedup_ratio)
after_compress = after_dedup × compression_ratio
retention_y   = after_compress × cumulative_growth_factor(y)
lifecycle: Nearline 30d / Coldline 90d / Archive 365d
```

---

## Network bandwidth

```
per_connector/day = runs × payload_kb / 1024 / 1024   # from _CONNECTOR_PROFILE
cross_cloud       = sum(payload for connectors where cross_cloud=True)
total_egress/mo   = (connector + evidence + api + object_storage) × 30
```

---

## Logging volume

```
per_day = Σ (activity_count × logs_per_unit × bytes_per_log)
per_year = per_day × 365
```

Classes: application, connector, scheduler, llm_execution, audit_trail.

---

## Cost

**Monthly components** (`cost.estimate_cost`):
```
compute_month  = nodes × (vcpu × $0.031 + ram_gib × $0.0042) × 730 hrs
sql_month      = (sql_vcpu × $0.0413 + sql_ram × $0.007) × 730 + storage × $0.17) × HA_mult
gcs_month      = gcs_gib × blended_tier_rate   # 40% std / 25% nearline / 20% cold / 15% archive
logging_month  = logs_gib_month × $0.50
network_month  = egress_gib_month × $0.12
monthly_total  = compute + sql + gcs + logging + monitoring + network + LB
annual_total   = monthly_total × 12
```

**5-year projection:**
```
for year 1..5:
  storage_factor = 1 + 0.6 × (year - 1)
  yr_monthly = fixed(compute, sql, monitoring, LB)
             + variable(storage, logging, egress) × storage_factor
five_year_total = Σ (yr_monthly × 12)
```

---

## Worked example — `phase1` profile

**Inputs:** 3 apps, 5,000 API req/day, 50 connector runs/day, 30 prompt runs/day,
20 scheduler jobs/day, avg evidence 200 KB, retention 5 years.

**CPU:**
```
total_cpu_ms = 5000×40 + 50×800 + 20×200 + 30×1500 = 200,000 + 40,000 + 4,000 + 45,000 = 289,000 ms
avg_cores    = 289,000/1000 / (9×3600) = 0.0089
peak_cores   = 0.0089 × 3 = 0.027 → rounds to 0.035
replicas     = max(2, int(0.035 / (0.5×0.6)) + 1) = max(2, 1) = 2
```

**Nodes:**
```
total_cpu = 2 × 0.5 = 1.0 core; alloc = 3 → nodes_for_cpu = 0.33
total_ram = 2 × 1.0 = 2 GiB; alloc = 12 → nodes_for_ram = 0.17
nodes     = max(2, int(0.33) + 1) = 2
```

**Cloud SQL:** year-1 ≈ 0.12 GiB → `db-custom-2-7680`

**GCS:** year-1 ≈ 2.67 GiB, year-5 ≈ 12.80 GiB (evidence + versions + growth × 5y)

**Cost:** monthly ≈ $559 (illustrative); 5-year ≈ $33,625

Reproduce: `python3 scripts/benchmark_capacity.py --profile phase1 --dry-run`

## Related
- [`BENCHMARK_CALCULATION_TRACEABILITY.md`](BENCHMARK_CALCULATION_TRACEABILITY.md) · [`BENCHMARK_EXECUTIVE_REPORT_EXPLANATION.md`](BENCHMARK_EXECUTIVE_REPORT_EXPLANATION.md) · [`CALIBRATION_GUIDE.md`](CALIBRATION_GUIDE.md)
