# ECS Executive Capacity Planner Guide

`benchmarks/capacity/executive.py` produces an executive-level capacity summary
across profiles: headline sizing, cost, top-5 lists, and phase-wise sizing.

## Report contents
- **Recommended sizing table:** GKE nodes, replicas, pod requests/limits, Cloud
  SQL tier, GCS year-1/year-5, monthly + 5-year cost — per profile.
- **Phase-wise sizing:** Demo · Phase 1 (NB/MB/Payments) · 100 apps · 500 apps ·
  2000 apps.
- **Top 5 bottlenecks** · **Top 5 risks** · **Top 5 cost optimizations**
  (derived from the largest profile's estimate).

## Outputs
- Markdown (`executive.md`), JSON (`executive.json`), CSV (`executive.csv`),
  and an optional **dependency-free HTML dashboard** (`executive.html`).

## CLI
```bash
python scripts/benchmark_capacity.py --all --executive           # MD/JSON/CSV
python scripts/benchmark_capacity.py --all --executive --html    # + HTML dashboard
python scripts/benchmark_capacity.py --profile phase1 --executive --dry-run  # print only
```
Written to `--out` (default `reports/capacity_benchmarks/`). `--dry-run` prints
the Markdown without writing files.

## Interpreting
- Treat cost figures as **directional** (illustrative rates) until quoted.
- Use the top-5 lists to drive the sizing conversation (where to invest, what to
  de-risk, where to save).
- Phase-wise rows map to the ECS rollout plan for board/leadership review.

## API
```python
from benchmarks.capacity import estimate_capacity, list_profiles, get_profile, executive
ests = [estimate_capacity(get_profile(k)) for k in list_profiles()]
md = executive.to_markdown(ests)
executive.write_executive(ests, "reports/capacity_benchmarks", html=True)
```

## Related
- [`ADVANCED_INFRASTRUCTURE_BENCHMARK_GUIDE.md`](ADVANCED_INFRASTRUCTURE_BENCHMARK_GUIDE.md)
- [`INFRASTRUCTURE_BENCHMARK_GUIDE.md`](INFRASTRUCTURE_BENCHMARK_GUIDE.md)
- [`GCP_CAPACITY_BENCHMARK_GUIDE.md`](GCP_CAPACITY_BENCHMARK_GUIDE.md)
