# ECS Benchmark — Reproducibility Guide

How to reproduce every benchmark output deterministically: commands, expected
outputs, sample reports, CLI options, configuration, profiles, validation, and
troubleshooting.

> The workbench is **deterministic and offline** — same profile + constants ⇒
> same numbers (pure arithmetic; no model/DB/network unless you inject them).

## 1. Prerequisites
- Python 3.12, repo checked out. No extra install needed for estimates.
- Optional for telemetry: `psutil` (stdlib `resource`/`tracemalloc` used if present).

## 2. Commands & expected outputs

| Command | Output |
|---------|--------|
| `python scripts/benchmark_capacity.py --list` | 12 profiles (laptop → large) |
| `python scripts/benchmark_capacity.py --profile phase1` | Console summary + writes `capacity.{json,md,csv}` + 7 section reports to `reports/capacity_benchmarks/` |
| `python scripts/benchmark_capacity.py --all` | Same for all 12 profiles |
| `python scripts/benchmark_capacity.py --all --dry-run` | Prints summary table; **writes nothing** |
| `python scripts/benchmark_capacity.py --profile enterprise --cpu` | Prints CPU report (also `--ram/--database/--network/--storage/--cost`) |
| `python scripts/benchmark_capacity.py --profile enterprise --kubernetes` | Kubernetes/GKE recommendation JSON |
| `python scripts/benchmark_capacity.py --profile enterprise --stress` | All stress scenarios (or `--stress-scenario connector_storm`) |
| `python scripts/benchmark_capacity.py --profile phase1 --telemetry` | Runtime telemetry JSON + report |
| `python scripts/benchmark_capacity.py --all --executive --html` | Executive MD/JSON/CSV + HTML dashboard |
| `python scripts/benchmark_capacity.py --calibrate observed.json --profile phase1` | Calibration report JSON |

## 3. Output files (`--out`, default `reports/capacity_benchmarks/`)
- `capacity.json` — full detail + recommendation table
- `capacity.md` — readable report · `capacity.csv` — one row/profile
- `capacity_{cpu,ram,storage,database,network,cost,executive}.md` — section reports
- `executive.{md,json,csv,html}` — executive planner (with `--executive`)

> Generated reports are runtime artifacts and are **not committed**. A checked-in
> sample lives at [`SAMPLE_EXECUTIVE_CAPACITY_REPORT.md`](SAMPLE_EXECUTIVE_CAPACITY_REPORT.md).

## 4. CLI options
Run `python scripts/benchmark_capacity.py --help`. Flags: `--profile`, `--all`,
`--list`, `--dry-run`, `--out`, `--basename`; section `--cpu/--ram/--database/
--network/--storage/--cost`; advanced `--telemetry/--kubernetes/--stress/
--stress-scenario/--calibrate/--executive/--html`. All are backward-compatible.

## 5. Configuration
- **Profiles:** `benchmarks/capacity/profiles.py` (`CapacityProfile`) — scenario drivers.
- **Constants:** each module's `*Constants` dataclass (see
  [`BENCHMARK_ASSUMPTIONS_AND_LIMITATIONS.md`](BENCHMARK_ASSUMPTIONS_AND_LIMITATIONS.md)).
- **Programmatic overrides:**
  ```python
  from benchmarks.capacity import estimate_capacity, get_profile, SizingConstants
  est = estimate_capacity(get_profile("enterprise"),
                          constants=SizingConstants.from_overrides({"cpu_ms_per_api_request": 55}),
                          measured_tokens={"avg_total_tokens": 1800})
  ```

## 6. Profiles
`laptop` · `demo` · `pilot` · `phase1` (NB/MB/Payments) · `phase2` (15) ·
`apps25` · `apps50` · `enterprise` (100) · `apps250` · `pan-bank` (500) ·
`apps1000` · `large` (2000).

## 7. Validation
```bash
python -m compileall -q benchmarks/capacity scripts tests
PYTHONPATH=. pytest tests/test_capacity_benchmark.py -q
python scripts/benchmark_capacity.py --all --dry-run     # sanity: numbers scale monotonically
```
Expected: compile clean; **67 tests pass**; summary table with increasing
replicas/nodes/storage across profiles.

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Unknown capacity profile 'x'` | bad `--profile` | `--list` for valid keys |
| Telemetry fields `null` | `psutil` not installed | Install `psutil` (optional) or accept degraded metrics |
| Reports not written | `--dry-run` set | omit `--dry-run` |
| Cost seems flat across small profiles | compute + Cloud SQL base + HA floor dominate at small scale | expected; scales at larger profiles |
| Numbers differ from a colleague | different constants/profile edits | diff `*Constants` / profile; estimates are deterministic otherwise |
| `--calibrate` cannot read file | bad JSON path/shape | see [`CALIBRATION_GUIDE.md`](CALIBRATION_GUIDE.md) for the input schema |

## Related
- [`INFRASTRUCTURE_BENCHMARK_GUIDE.md`](INFRASTRUCTURE_BENCHMARK_GUIDE.md) · [`ADVANCED_INFRASTRUCTURE_BENCHMARK_GUIDE.md`](ADVANCED_INFRASTRUCTURE_BENCHMARK_GUIDE.md) · [`CALIBRATION_GUIDE.md`](CALIBRATION_GUIDE.md) · [`BENCHMARK_TRACEABILITY.md`](BENCHMARK_TRACEABILITY.md)
