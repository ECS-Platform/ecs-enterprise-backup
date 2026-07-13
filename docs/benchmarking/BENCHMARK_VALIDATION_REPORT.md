# ECS Benchmark — Validation Report

Record of validation runs for the Infrastructure Benchmark Workbench documentation
closure. Re-run these commands after any benchmark change.

## Environment

| Item | Value |
|------|-------|
| Repository | `ecs-enterprise-backup` (local: `/Users/nikhil/Documents/ECS`) |
| Branch | `cursor/predefined-queries-module` |
| Python | 3.12 |
| Date | 2026-07-13 |

## Commands run

### 1. Compile check
```bash
python3 -m compileall benchmarks/capacity scripts tests
```
**Result:** exit 0 — all modules compile cleanly.

### 2. Unit / integration tests
```bash
PYTHONPATH=. python3 -m pytest tests/test_capacity_benchmark.py
```
**Result:** **67 passed** in ~0.15s.

> **PYTHONPATH note:** Tests import `benchmarks.capacity` from the repo root.
> Always prefix with `PYTHONPATH=.` (or `export PYTHONPATH=.` in your shell) when
> running pytest from the repository root. Without it, imports may fail depending
> on install state.

### 3. CLI dry-run (sanity)
```bash
python3 scripts/benchmark_capacity.py --all --dry-run
```
**Result:** summary table printed for all 12 profiles; no files written.

### 4. Report generation validation
```bash
python3 scripts/benchmark_capacity.py --profile phase1 --executive --telemetry
python3 scripts/benchmark_capacity.py --profile enterprise --kubernetes --stress --executive --html
python3 scripts/benchmark_capacity.py --all --executive --html
```
**Result:** all flags accepted; estimates computed; executive + section reports
written to `reports/capacity_benchmarks/` (runtime artifacts, not committed).

Validated formats:
- `capacity.json`, `capacity.md`, `capacity.csv`
- `capacity_{cpu,ram,storage,database,network,cost,executive}.md`
- `executive.md`, `executive.json`, `executive.csv`, `executive.html`

### 5. Programmatic report validation
```python
from benchmarks.capacity import estimate_capacity, get_profile, list_profiles
from benchmarks.capacity import report as rpt, executive as ex
ests = [estimate_capacity(get_profile(k)) for k in list_profiles()]
assert rpt.to_json(ests) and rpt.to_markdown(ests) and rpt.to_csv(ests)
assert ex.to_json(ests) and ex.to_markdown(ests) and ex.to_csv(ests) and ex.to_html(ests)
for name in rpt.SECTION_REPORTS:
    fn = rpt.SECTION_REPORTS[name]
    assert fn(ests)
```
**Result:** all report formats generate; 12 profiles; 18 estimate sections.

### 6. Documentation link validation
```bash
python3 - <<'EOF'
import re, os, glob
bad = []
for d in glob.glob("docs/benchmarking/*.md"):
    base = os.path.dirname(d)
    for m in re.finditer(r'\[[^\]]+\]\(([^)]+)\)', open(d).read()):
        t = m.group(1).split('#')[0].strip()
        if not t or t.startswith(('http', 'mailto')): continue
        if not os.path.exists(os.path.normpath(os.path.join(base, t))):
            bad.append((os.path.basename(d), t))
print("BROKEN:", bad) if bad else print("all links OK")
EOF
```
**Result:** all internal links in `docs/benchmarking/*.md` resolve.

### 7. CLI help / flag inventory
```bash
python3 scripts/benchmark_capacity.py --help
python3 scripts/benchmark_capacity.py --list
```
**Result:** 19 flags present (`--profile`, `--all`, `--list`, `--dry-run`, `--out`,
`--basename`, `--cpu`, `--ram`, `--database`, `--network`, `--storage`, `--cost`,
`--telemetry`, `--kubernetes`, `--stress`, `--stress-scenario`, `--calibrate`,
`--executive`, `--html`). 12 profiles listed.

## Coverage summary

| Area | Validated |
|------|-----------|
| `benchmarks/capacity/` (14 modules) | ✅ compile + tests |
| `scripts/benchmark_capacity.py` | ✅ CLI flags + dry-run |
| `tests/test_capacity_benchmark.py` | ✅ 67 tests |
| JSON / MD / CSV / HTML reports | ✅ generate |
| Executive reports | ✅ MD/JSON/CSV/HTML |
| Section reports (7) | ✅ generate |
| Documentation links | ✅ resolve |
| Benchmark logic | unchanged (docs-only task) |

## Known limitations (post-validation)

- All sizing figures remain **estimates** until calibrated (see [`CALIBRATION_GUIDE.md`](CALIBRATION_GUIDE.md)).
- Generated `reports/capacity_benchmarks/` is excluded from commits per convention.
- Cost rates are illustrative — not validated against live GCP billing.

## Reproducibility commands (quick reference)

```bash
python3 scripts/benchmark_capacity.py --help
python3 scripts/benchmark_capacity.py --list
python3 scripts/benchmark_capacity.py --profile phase1 --executive --telemetry
python3 scripts/benchmark_capacity.py --profile enterprise --kubernetes --stress --executive --html
python3 scripts/benchmark_capacity.py --all --executive --html
python3 -m compileall benchmarks/capacity scripts tests
PYTHONPATH=. python3 -m pytest tests/test_capacity_benchmark.py
open reports/capacity_benchmarks/executive.html
```

## Related
- [`BENCHMARK_REPRODUCIBILITY_GUIDE.md`](BENCHMARK_REPRODUCIBILITY_GUIDE.md) · [`BENCHMARK_MATURITY_ASSESSMENT.md`](BENCHMARK_MATURITY_ASSESSMENT.md) · [`BENCHMARK_METHODOLOGY.md`](BENCHMARK_METHODOLOGY.md)
