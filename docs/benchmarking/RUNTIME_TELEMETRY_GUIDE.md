# ECS Runtime Telemetry Guide

`benchmarks/capacity/telemetry.py` captures runtime resource usage around a block
of work using **only optional** libraries — degrading gracefully to whatever is
available on the host. No heavy dependency is added.

## What it captures
- CPU: user/system CPU time, CPU percent
- Memory: RSS, peak RSS / high-water mark, optional Python heap (tracemalloc)
- Disk: read/write MiB (if `psutil` io counters available)
- Network: bytes sent/received MiB (if `psutil` available)
- Timing: wall-clock duration + optional per-step markers

## Backends (all optional)
| Backend | Provides | If missing |
|---------|----------|------------|
| `psutil` | CPU%, RSS, disk IO, network | those metrics reported as `None` |
| `resource` (stdlib, Unix) | CPU time, peak RSS | skipped |
| `tracemalloc` (stdlib) | Python heap current/peak | only when `trace_python_heap=True` |

`result["available"]` reports which backends were active.

## Usage
```python
from benchmarks.capacity.telemetry import RuntimeTelemetry

with RuntimeTelemetry("phase1-estimate", trace_python_heap=True) as t:
    ... work ...
    t.add_step("retrieved")
    ... more work ...
data = t.result   # JSON-serializable dict
```

## CLI
```bash
python scripts/benchmark_capacity.py --profile phase1 --telemetry
```
Prints the telemetry JSON before the report. Combine with `--executive` etc.

## Guarantees
- **Never raises** — telemetry failures never mask the measured work.
- **JSON-serializable** output (primitives + `None`).
- Zero hard dependencies; safe on any machine.

## Related
- [`ADVANCED_INFRASTRUCTURE_BENCHMARK_GUIDE.md`](ADVANCED_INFRASTRUCTURE_BENCHMARK_GUIDE.md)
- [`CALIBRATION_GUIDE.md`](CALIBRATION_GUIDE.md) — feed observed telemetry back into the model
