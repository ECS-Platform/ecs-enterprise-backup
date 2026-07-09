# ECS Benchmark Calibration Guide

`benchmarks/capacity/calibration.py` compares **observed** telemetry (from a real
run) to the model **estimate** and recommends adjusted constants — **without**
changing anything automatically.

## Input (observed JSON; any subset)
```json
{
  "observed_cpu_cores": 1.2,
  "observed_ram_mib": 900,
  "observed_runtime_s": 4.5,
  "observed_files_uploaded": 320,
  "observed_evidence_size_kb": 300,
  "observed_prompt_tokens": 1800,
  "observed_connector_count": 19,
  "observed_db_query_count": 900
}
```
Capture these with [`RuntimeTelemetry`](RUNTIME_TELEMETRY_GUIDE.md) + your run's
activity counts.

## Output (per metric)
- `old_estimate`, `observed`, `calibration_factor` (observed ÷ estimate)
- `constant` + `current_constant` + `recommended_new_constant`
- `confidence` (medium / low / very_low — single-sample capped at medium)
- `notes` + an `overall_calibration_factor`

## CLI
```bash
python scripts/benchmark_capacity.py --calibrate reports/sample_observed.json --profile phase1
```
Prints the calibration report JSON. Nothing is written or applied.

## Applying (explicit, manual)
```python
from benchmarks.capacity import SizingConstants, estimate_capacity, get_profile
c = SizingConstants.from_overrides({"cpu_ms_per_api_request": 1371.4})  # from the report
est = estimate_capacity(get_profile("phase1"), constants=c,
                        measured_tokens={"avg_total_tokens": 1800})
```

## Guidance
- **Average several runs** before applying — one observation is indicative only.
- Large factors usually mean a workload-mix mismatch (investigate before trusting).
- Update profile fields (e.g. `avg_evidence_size_kb`) and pass `measured_tokens`
  for the most accurate calibration.

## Related
- [`RUNTIME_TELEMETRY_GUIDE.md`](RUNTIME_TELEMETRY_GUIDE.md)
- [`ADVANCED_INFRASTRUCTURE_BENCHMARK_GUIDE.md`](ADVANCED_INFRASTRUCTURE_BENCHMARK_GUIDE.md)
