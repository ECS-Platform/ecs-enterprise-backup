"""Capacity-planning calculations for the ECS enterprise AI workload benchmark.

Consumes MEASURED per-request statistics (produced by the existing ECS
instrumentation) plus operator ASSUMPTIONS, and derives ESTIMATED and PROJECTED
figures for Neev infrastructure sizing and cost estimation.

The three categories are kept strictly separate and never mixed:

* measured   — comes only from real benchmark observations.
* estimated  — single-stream capacity derived from measured latency.
* projected  — production load derived from operator assumptions x measured tokens.

Nothing here calls ECS or the LLM; it is pure arithmetic over inputs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class CapacityAssumptions:
    """Operator-supplied planning inputs (NOT measured)."""

    # Demand model
    concurrent_users: int = 50
    requests_per_user_per_day: int = 8
    working_hours_per_day: float = 9.0
    working_days_per_month: int = 22
    months_per_year: int = 12
    peak_to_average_factor: float = 3.0

    # Vector / storage growth model
    embedding_dimensions: int = 768          # nomic-embed-text default (config/vectorstore.yaml)
    bytes_per_dimension: int = 4             # float32
    vector_index_overhead_factor: float = 1.3
    avg_chunk_bytes: int = 1200
    new_chunks_per_day: int = 5000

    # Cost model (currency-neutral; rate per 1,000 tokens)
    cost_per_1k_input_tokens: float = 0.0
    cost_per_1k_output_tokens: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CapacityAssumptions":
        data = data or {}
        known = {k: data[k] for k in data if k in cls.__dataclass_fields__}
        return cls(**known)


def _f(x: Any) -> float:
    try:
        return float(x) if x is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def plan(measured: dict[str, Any], assumptions: CapacityAssumptions) -> dict[str, Any]:
    """Build the capacity-planning section.

    ``measured`` expects keys (any missing treated as 0):
      avg_total_tokens, peak_total_tokens, avg_input_tokens, avg_output_tokens,
      avg_end_to_end_ms, p95_end_to_end_ms
    """
    a = assumptions

    avg_total = _f(measured.get("avg_total_tokens"))
    peak_total = _f(measured.get("peak_total_tokens"))
    avg_in = _f(measured.get("avg_input_tokens"))
    avg_out = _f(measured.get("avg_output_tokens"))
    avg_e2e_ms = _f(measured.get("avg_end_to_end_ms"))
    p95_e2e_ms = _f(measured.get("p95_end_to_end_ms"))

    # --- ESTIMATED: single-stream (concurrency=1) capacity from measured latency ---
    single_stream_rpm = (60000.0 / avg_e2e_ms) if avg_e2e_ms > 0 else None
    single_stream_rph = (single_stream_rpm * 60.0) if single_stream_rpm else None
    p95_single_stream_rpm = (60000.0 / p95_e2e_ms) if p95_e2e_ms > 0 else None

    estimated = {
        "single_stream_requests_per_minute": round(single_stream_rpm, 3) if single_stream_rpm else None,
        "single_stream_requests_per_hour": round(single_stream_rph, 1) if single_stream_rph else None,
        "single_stream_rpm_at_p95_latency": round(p95_single_stream_rpm, 3) if p95_single_stream_rpm else None,
        "_basis": "Derived from measured end-to-end latency at concurrency=1 (the benchmark's supported mode).",
    }

    # --- PROJECTED: production demand from assumptions x measured token cost ---
    daily_requests = a.concurrent_users * a.requests_per_user_per_day
    monthly_requests = daily_requests * a.working_days_per_month
    yearly_requests = monthly_requests * a.months_per_year

    avg_rpm_working = (daily_requests / (a.working_hours_per_day * 60.0)) if a.working_hours_per_day > 0 else None
    peak_rpm = (avg_rpm_working * a.peak_to_average_factor) if avg_rpm_working is not None else None
    avg_rph_working = (daily_requests / a.working_hours_per_day) if a.working_hours_per_day > 0 else None

    monthly_tokens = monthly_requests * avg_total
    yearly_tokens = yearly_requests * avg_total
    monthly_input_tokens = monthly_requests * avg_in
    monthly_output_tokens = monthly_requests * avg_out

    # Vector + content storage growth
    vector_bytes_per_chunk = a.embedding_dimensions * a.bytes_per_dimension * a.vector_index_overhead_factor
    daily_vector_bytes = a.new_chunks_per_day * vector_bytes_per_chunk
    daily_content_bytes = a.new_chunks_per_day * a.avg_chunk_bytes
    daily_storage_bytes = daily_vector_bytes + daily_content_bytes

    def gib(b: float) -> float:
        return round(b / (1024 ** 3), 4)

    # Cost inputs (zero rates by default -> operator supplies real rates)
    monthly_input_cost = (monthly_input_tokens / 1000.0) * a.cost_per_1k_input_tokens
    monthly_output_cost = (monthly_output_tokens / 1000.0) * a.cost_per_1k_output_tokens
    monthly_cost = monthly_input_cost + monthly_output_cost

    projected = {
        "requests": {
            "per_day": daily_requests,
            "per_month": monthly_requests,
            "per_year": yearly_requests,
            "avg_requests_per_minute_working_hours": round(avg_rpm_working, 3) if avg_rpm_working else None,
            "avg_requests_per_hour_working_hours": round(avg_rph_working, 1) if avg_rph_working else None,
            "peak_requests_per_minute": round(peak_rpm, 3) if peak_rpm else None,
        },
        "tokens": {
            "avg_tokens_per_request": round(avg_total, 2),
            "peak_tokens_per_request": round(peak_total, 2),
            "monthly_total_tokens": round(monthly_tokens, 0),
            "yearly_total_tokens": round(yearly_tokens, 0),
            "monthly_input_tokens": round(monthly_input_tokens, 0),
            "monthly_output_tokens": round(monthly_output_tokens, 0),
        },
        "storage_growth": {
            "vector_bytes_per_chunk": round(vector_bytes_per_chunk, 2),
            "daily_vector_growth_gib": gib(daily_vector_bytes),
            "monthly_vector_growth_gib": gib(daily_vector_bytes * a.working_days_per_month),
            "yearly_vector_growth_gib": gib(daily_vector_bytes * a.working_days_per_month * a.months_per_year),
            "daily_content_growth_gib": gib(daily_content_bytes),
            "monthly_total_storage_growth_gib": gib(daily_storage_bytes * a.working_days_per_month),
            "yearly_total_storage_growth_gib": gib(daily_storage_bytes * a.working_days_per_month * a.months_per_year),
        },
        "cost_inputs": {
            "monthly_input_cost": round(monthly_input_cost, 4),
            "monthly_output_cost": round(monthly_output_cost, 4),
            "monthly_total_cost": round(monthly_cost, 4),
            "yearly_total_cost": round(monthly_cost * a.months_per_year, 4),
            "_note": "Cost is zero unless cost_per_1k_*_tokens assumptions are provided.",
        },
        "_basis": "Derived from operator assumptions multiplied by MEASURED average/peak tokens. Not observed.",
    }

    return {
        "measured": {
            "avg_total_tokens": round(avg_total, 2),
            "peak_total_tokens": round(peak_total, 2),
            "avg_input_tokens": round(avg_in, 2),
            "avg_output_tokens": round(avg_out, 2),
            "avg_end_to_end_ms": round(avg_e2e_ms, 2),
            "p95_end_to_end_ms": round(p95_e2e_ms, 2),
            "_basis": "Observed from benchmark execution via existing ECS instrumentation.",
        },
        "estimated": estimated,
        "projected": projected,
        "assumptions": a.to_dict(),
    }
