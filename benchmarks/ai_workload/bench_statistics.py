"""Statistical helpers for the ECS enterprise AI workload benchmark.

Pure standard library. Operates on the per-request metrics captured by the
EXISTING ECS instrumentation (``ecs_platform.rag.answer`` -> ``metrics`` and the
persisted ``rag_metrics.jsonl``). No ECS or instrumentation changes.

Named ``bench_statistics`` (not ``statistics``) to avoid shadowing the stdlib
module for other code in this package.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass
class StatSummary:
    """min / average / median / max / P90 / P95 / P99 / stddev for one metric."""

    count: int
    minimum: float | None
    average: float | None
    median: float | None
    maximum: float | None
    p90: float | None
    p95: float | None
    p99: float | None
    stddev: float | None

    def to_dict(self) -> dict:
        return asdict(self)


def _percentile(sorted_vals: list[float], pct: float) -> float | None:
    """Linear-interpolation percentile (same method as numpy's default)."""
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    rank = (pct / 100.0) * (len(sorted_vals) - 1)
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return float(sorted_vals[int(rank)])
    frac = rank - lo
    return float(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac)


def summarize(values: Iterable) -> StatSummary:
    """Compute the full statistic set over numeric values (ignores non-numbers/None)."""
    nums = [float(v) for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if not nums:
        return StatSummary(0, None, None, None, None, None, None, None, None)
    s = sorted(nums)
    n = len(s)
    mean = sum(s) / n
    if n > 1:
        variance = sum((x - mean) ** 2 for x in s) / (n - 1)  # sample stddev
        std = math.sqrt(variance)
    else:
        std = 0.0
    mid = n // 2
    median = s[mid] if n % 2 == 1 else (s[mid - 1] + s[mid]) / 2.0
    return StatSummary(
        count=n,
        minimum=float(s[0]),
        average=float(mean),
        median=float(median),
        maximum=float(s[-1]),
        p90=_percentile(s, 90),
        p95=_percentile(s, 95),
        p99=_percentile(s, 99),
        stddev=float(std),
    )
