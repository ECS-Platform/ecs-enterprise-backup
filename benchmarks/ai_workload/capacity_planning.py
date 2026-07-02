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

from dataclasses import asdict, dataclass, field
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


# =========================================================================== #
# WORST-CASE ENTERPRISE CAPACITY MODEL
# --------------------------------------------------------------------------- #
# Consolidated here (from the former standalone worst_case_model.py) so there is
# ONE capacity-planning framework. It REUSES the demand/storage arithmetic of
# ``plan()`` above and ``CapacityAssumptions``; it performs NO measurement and NO
# token counting of its own. Every output is tagged with one of four strictly
# separated provenance tiers so a projection is never read as a measured result:
#
#   MEASURED_BASELINE  — observed in the benchmark (passed in; never invented here)
#   WORST_CASE         — measured worst-case envelope x documented headroom
#   PROJECTED_CAPACITY — production demand x worst-case per-request tokens
#   FORECAST           — Years 1..N growth applied to the projection
# =========================================================================== #

TIER_MEASURED = "MEASURED_BASELINE"
TIER_WORST_CASE = "WORST_CASE"
TIER_PROJECTED = "PROJECTED_CAPACITY"
TIER_FORECAST = "FORECAST"


@dataclass
class WorstCaseAssumptions:
    """Worst-case scaling + multi-year growth inputs. All ESTIMATED, not measured.

    Defaults encode the documented parameter grid. They are applied ONLY to
    WORST_CASE / PROJECTED / FORECAST tiers — never to the measured baseline.
    """

    # ---- Sensitivity grid (configurable benchmark parameters) ----
    top_k_grid: list[int] = field(default_factory=lambda: [5, 10, 20, 30, 40])
    chunk_size_grid: list[int] = field(default_factory=lambda: [256, 512, 768, 1024])
    output_token_grid: list[int] = field(default_factory=lambda: [256, 512, 768, 1024])
    system_prompt_growth_grid: list[float] = field(default_factory=lambda: [0.0, 0.10, 0.20, 0.30])
    framework_scope_grid: list[str] = field(
        default_factory=lambda: ["single_framework", "multiple_frameworks", "enterprise_cross_framework"])

    # Framework-scope context multipliers (relative retrieved-context volume).
    framework_scope_multipliers: dict[str, float] = field(default_factory=lambda: {
        "single_framework": 1.0,
        "multiple_frameworks": 2.5,
        "enterprise_cross_framework": 6.0,
    })

    # Reference point for proportional scaling of measured worst-case input tokens.
    reference_top_k: int = 40
    reference_chunk_size: int = 768          # nomic-embed-text chunking (vectorstore.yaml)
    reference_output_tokens: int = 2048      # config/llm.yaml max_output_tokens

    # ---- Worst-case per-request envelope multipliers (vs measured peak) ----
    worst_case_input_headroom: float = 1.25   # +25% input headroom for larger estate
    worst_case_output_headroom: float = 1.00  # output capped by model max_output_tokens
    worst_case_latency_headroom: float = 1.30 # +30% latency under load/large context

    # ---- Multi-year growth model ----
    forecast_years: int = 5
    evidence_files_per_control_per_framework_per_year: int = 2
    baseline_controls: int = 200
    baseline_frameworks: int = 6
    applications_added_per_year: int = 10
    baseline_applications: int = 50
    annual_demand_growth_rate: float = 0.20   # +20%/yr requests (adoption)
    annual_token_growth_rate: float = 0.10    # +10%/yr worst-case tokens per request

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "WorstCaseAssumptions":
        data = data or {}
        known = {k: data[k] for k in data if k in cls.__dataclass_fields__}
        return cls(**known)


def worst_case_envelope(measured: dict[str, Any], wc: WorstCaseAssumptions) -> dict[str, Any]:
    """Worst-case per-request envelope from MEASURED worst-case values + headroom.

    ``measured`` keys (all from existing reporting/statistics; missing -> 0):
      max_input_tokens, max_output_tokens, max_total_tokens, max_prompt_size_chars,
      max_retrieved_context_chars, max_retrieved_documents, max_retrieved_chunks,
      max_end_to_end_ms
    """
    m_in = _f(measured.get("max_input_tokens"))
    m_out = _f(measured.get("max_output_tokens"))
    m_total = _f(measured.get("max_total_tokens")) or (m_in + m_out)
    m_lat = _f(measured.get("max_end_to_end_ms"))

    wc_in = m_in * wc.worst_case_input_headroom
    wc_out = m_out * wc.worst_case_output_headroom
    wc_total = wc_in + wc_out if (wc_in or wc_out) else m_total * wc.worst_case_input_headroom
    wc_lat = m_lat * wc.worst_case_latency_headroom

    return {
        "tier": TIER_WORST_CASE,
        "measured_worst_case": {
            "tier": TIER_MEASURED,
            "max_input_tokens": round(m_in, 2),
            "max_output_tokens": round(m_out, 2),
            "max_total_tokens": round(m_total, 2),
            "max_prompt_size_chars": _f(measured.get("max_prompt_size_chars")),
            "max_retrieved_context_chars": _f(measured.get("max_retrieved_context_chars")),
            "max_retrieved_documents": _f(measured.get("max_retrieved_documents")),
            "max_retrieved_chunks": _f(measured.get("max_retrieved_chunks")),
            "max_end_to_end_ms": round(m_lat, 2),
            "_basis": "Observed maxima from the worst-case benchmark run (existing instrumentation).",
        },
        "worst_case_scaled": {
            "max_realistic_input_tokens": round(wc_in, 2),
            "max_realistic_output_tokens": round(wc_out, 2),
            "max_realistic_total_tokens": round(wc_total, 2),
            "worst_case_latency_ms": round(wc_lat, 2),
            "_basis": (
                "Measured worst-case x documented headroom multipliers "
                f"(input x{wc.worst_case_input_headroom}, output x{wc.worst_case_output_headroom}, "
                f"latency x{wc.worst_case_latency_headroom}) to bound a larger realistic estate. ESTIMATED."
            ),
        },
    }


def sensitivity_sweep(measured: dict[str, Any], wc: WorstCaseAssumptions) -> dict[str, Any]:
    """Project worst-case tokens across each documented parameter axis (arithmetic only).

    Each axis is varied independently around the measured worst-case figure, scaled
    by the lever that physically drives size. ESTIMATED sensitivity, not measurement.
    """
    base_in = _f(measured.get("max_input_tokens"))
    base_out = _f(measured.get("max_output_tokens"))
    base_sys = _f(measured.get("max_system_prompt_tokens")) or _f(measured.get("system_prompt_tokens"))

    def axis(points: list, scale_fn) -> list[dict[str, Any]]:
        return [{"value": p, "estimated_input_tokens": round(scale_fn(p), 2)} for p in points]

    top_k_axis = axis(
        wc.top_k_grid,
        lambda k: base_in * (k / wc.reference_top_k) if wc.reference_top_k else base_in,
    )
    chunk_axis = axis(
        wc.chunk_size_grid,
        lambda c: base_in * (c / wc.reference_chunk_size) if wc.reference_chunk_size else base_in,
    )
    output_axis = [
        {"value": o, "estimated_output_tokens": round(min(_f(o), base_out or _f(o)) if base_out else _f(o), 2)}
        for o in wc.output_token_grid
    ]
    sys_axis = [
        {"value_pct": round(g * 100, 1), "estimated_input_tokens": round(base_in + base_sys * g, 2)}
        for g in wc.system_prompt_growth_grid
    ]
    scope_axis = [
        {"value": scope,
         "estimated_input_tokens": round(base_in * wc.framework_scope_multipliers.get(scope, 1.0), 2)}
        for scope in wc.framework_scope_grid
    ]

    return {
        "tier": TIER_PROJECTED,
        "_basis": "Independent one-axis-at-a-time scaling of MEASURED worst-case tokens. ESTIMATED sensitivity, not measured.",
        "reference_point": {
            "measured_max_input_tokens": round(base_in, 2),
            "measured_max_output_tokens": round(base_out, 2),
            "reference_top_k": wc.reference_top_k,
            "reference_chunk_size": wc.reference_chunk_size,
        },
        "retrieval_depth_top_k": top_k_axis,
        "chunk_size": chunk_axis,
        "output_token_limit": output_axis,
        "system_prompt_growth": sys_axis,
        "framework_scope": scope_axis,
    }


def repository_growth(wc: WorstCaseAssumptions) -> dict[str, Any]:
    """Evidence-file / portfolio growth from the documented growth rule (ESTIMATED).

    Rule: N new evidence files / control / framework / year, with the app portfolio
    growing by ``applications_added_per_year``.
    """
    years = []
    cumulative_files = 0
    apps = wc.baseline_applications
    for y in range(0, wc.forecast_years + 1):
        if y == 0:
            new_files = 0
        else:
            apps = wc.baseline_applications + wc.applications_added_per_year * y
            new_files = (wc.evidence_files_per_control_per_framework_per_year
                         * wc.baseline_controls * wc.baseline_frameworks
                         * (apps / wc.baseline_applications if wc.baseline_applications else 1))
        cumulative_files += new_files
        years.append({
            "year": y,
            "applications": apps,
            "new_evidence_files": round(new_files, 0),
            "cumulative_evidence_files": round(cumulative_files, 0),
        })
    return {
        "tier": TIER_FORECAST,
        "_basis": (f"Documented rule: {wc.evidence_files_per_control_per_framework_per_year} evidence files "
                   f"/ control / framework / year, {wc.baseline_controls} controls x {wc.baseline_frameworks} "
                   f"frameworks, +{wc.applications_added_per_year} apps/year. ESTIMATED."),
        "years": years,
    }


def _worst_case_budget(total_tokens_per_request: float, input_tokens: float,
                       output_tokens: float, demand: CapacityAssumptions) -> dict[str, Any]:
    """Monthly/annual worst-case token + cost budget at a per-request envelope.

    Reuses the SAME demand arithmetic as ``plan()`` (no duplicate demand math).
    """
    planned = plan({
        "avg_total_tokens": total_tokens_per_request,
        "peak_total_tokens": total_tokens_per_request,
        "avg_input_tokens": input_tokens,
        "avg_output_tokens": output_tokens,
        "avg_end_to_end_ms": 0.0,
        "p95_end_to_end_ms": 0.0,
    }, demand)
    proj = planned["projected"]
    return {
        "requests_per_month": proj["requests"]["per_month"],
        "requests_per_year": proj["requests"]["per_year"],
        "monthly_total_tokens": proj["tokens"]["monthly_total_tokens"],
        "yearly_total_tokens": proj["tokens"]["yearly_total_tokens"],
        "monthly_total_cost": proj["cost_inputs"]["monthly_total_cost"],
        "yearly_total_cost": proj["cost_inputs"]["yearly_total_cost"],
    }


def multi_year_forecast(envelope: dict[str, Any], wc: WorstCaseAssumptions,
                        demand: CapacityAssumptions) -> dict[str, Any]:
    """Years 0..N worst-case token + cost budget under compounding growth.

    Year 0 = current worst-case scaled envelope at current demand. Each subsequent
    year compounds demand growth and per-request token drift, reusing ``plan()``.
    """
    scaled = envelope["worst_case_scaled"]
    base_in = _f(scaled.get("max_realistic_input_tokens"))
    base_out = _f(scaled.get("max_realistic_output_tokens"))
    base_total = _f(scaled.get("max_realistic_total_tokens")) or (base_in + base_out)

    years = []
    for y in range(0, wc.forecast_years + 1):
        demand_factor = (1.0 + wc.annual_demand_growth_rate) ** y
        token_factor = (1.0 + wc.annual_token_growth_rate) ** y
        in_y = base_in * token_factor
        out_y = base_out * token_factor
        total_y = base_total * token_factor
        demand_y = CapacityAssumptions.from_dict({
            **demand.to_dict(),
            "concurrent_users": int(round(demand.concurrent_users * demand_factor)),
        })
        budget = _worst_case_budget(total_y, in_y, out_y, demand_y)
        years.append({
            "year": y,
            "tier": TIER_FORECAST if y > 0 else TIER_PROJECTED,
            "demand_growth_factor": round(demand_factor, 4),
            "token_growth_factor": round(token_factor, 4),
            "worst_case_input_tokens_per_request": round(in_y, 2),
            "worst_case_output_tokens_per_request": round(out_y, 2),
            "worst_case_total_tokens_per_request": round(total_y, 2),
            "concurrent_users": demand_y.concurrent_users,
            **budget,
        })

    last = years[-1] if years else {}
    return {
        "tier": TIER_FORECAST,
        "_basis": (f"Year 0 = worst-case scaled envelope at current demand (PROJECTED). "
                   f"Years 1..{wc.forecast_years} compound demand +{wc.annual_demand_growth_rate*100:.0f}%/yr "
                   f"and per-request tokens +{wc.annual_token_growth_rate*100:.0f}%/yr. FORECAST."),
        "years": years,
        "final_year_worst_case_budget": {
            "year": last.get("year"),
            "yearly_total_tokens": last.get("yearly_total_tokens"),
            "yearly_total_cost": last.get("yearly_total_cost"),
        },
        "cumulative_forecast": {
            "total_tokens": round(sum(_f(yr.get("yearly_total_tokens")) for yr in years), 0),
            "total_cost": round(sum(_f(yr.get("yearly_total_cost")) for yr in years), 4),
            "_note": "Cost is zero unless cost_per_1k_*_tokens demand assumptions are provided.",
        },
    }


def worst_case_plan(measured_worst_case: dict[str, Any], demand: CapacityAssumptions,
                    wc: WorstCaseAssumptions) -> dict[str, Any]:
    """Full worst-case capacity-planning bundle with four strictly-separated tiers:
    measured_baseline / worst_case / projected_capacity / forecast.
    """
    envelope = worst_case_envelope(measured_worst_case, wc)
    sweep = sensitivity_sweep(measured_worst_case, wc)
    growth = repository_growth(wc)
    forecast = multi_year_forecast(envelope, wc, demand)

    scaled = envelope["worst_case_scaled"]
    headline = {
        "tier": TIER_WORST_CASE,
        "maximum_realistic_input_tokens": scaled["max_realistic_input_tokens"],
        "maximum_realistic_output_tokens": scaled["max_realistic_output_tokens"],
        "maximum_realistic_total_tokens": scaled["max_realistic_total_tokens"],
        "worst_case_prompt_size_chars": envelope["measured_worst_case"]["max_prompt_size_chars"],
        "worst_case_context_chars": envelope["measured_worst_case"]["max_retrieved_context_chars"],
        "worst_case_retrieval_documents": envelope["measured_worst_case"]["max_retrieved_documents"],
        "worst_case_response_tokens": scaled["max_realistic_output_tokens"],
        "worst_case_latency_ms": scaled["worst_case_latency_ms"],
    }

    return {
        "tiers": {
            TIER_MEASURED: "Observed via existing ECS instrumentation during the benchmark.",
            TIER_WORST_CASE: "Measured worst-case x documented headroom (ESTIMATED upper bound).",
            TIER_PROJECTED: "Production demand x worst-case per-request tokens (ESTIMATED).",
            TIER_FORECAST: "Years 1..N growth applied to the projection (FORECAST).",
        },
        "worst_case_headline": headline,
        "envelope": envelope,
        "sensitivity": sweep,
        "repository_growth": growth,
        "forecast": forecast,
        "assumptions": {
            "demand": demand.to_dict(),
            "worst_case": wc.to_dict(),
        },
    }


# =========================================================================== #
# PAN-INDIA ENTERPRISE TOKEN MODEL + NEEV WEIGHTED-TPM VALIDATION
# --------------------------------------------------------------------------- #
# Extends THIS capacity-planning framework (no new framework). Computes the Neev
# weighted token-per-minute figure from configurable inputs and validates it
# against both the MEASURED current runtime and the MODELED Pan-India future state.
# Strict provenance: three tiers are kept separate and never mixed:
#
#   MEASURED_CURRENT  — tokens actually measured by ECS instrumentation today.
#   PAN_INDIA_MODELED — modeled future-state context volume + target output.
#   NEEV_TARGET       — the capacity-planning assumption submitted to Finance.
#
# Formula (output weighting factor and peak RPM both configurable):
#   TPM = (input_tokens + output_weighting_factor * output_tokens) * peak_rpm
# =========================================================================== #

TIER_MEASURED_CURRENT = "MEASURED_CURRENT"
TIER_PAN_INDIA_MODELED = "PAN_INDIA_MODELED"
TIER_NEEV_TARGET = "NEEV_TARGET"

# Defaults for the Neev formula (configurable via PanIndiaAssumptions / config).
DEFAULT_OUTPUT_WEIGHTING_FACTOR = 9
DEFAULT_PEAK_REQUESTS_PER_MINUTE = 3


def weighted_tpm_calculation(input_tokens: float, output_tokens: float,
                             output_weighting_factor: float = DEFAULT_OUTPUT_WEIGHTING_FACTOR,
                             peak_requests_per_minute: float = DEFAULT_PEAK_REQUESTS_PER_MINUTE
                             ) -> dict[str, Any]:
    """Neev weighted tokens-per-minute for one per-request token envelope.

    ``TPM = (input + weight * output) * peak_rpm``. Both ``output_weighting_factor``
    and ``peak_requests_per_minute`` are configurable. Pure arithmetic; no provenance
    assumed here (the caller stamps the tier).
    """
    in_t = _f(input_tokens)
    out_t = _f(output_tokens)
    weight = _f(output_weighting_factor)
    peak = _f(peak_requests_per_minute)
    weighted_per_request = in_t + weight * out_t
    tpm = weighted_per_request * peak
    return {
        "input_tokens": round(in_t, 2),
        "output_tokens": round(out_t, 2),
        "output_weighting_factor": weight,
        "peak_requests_per_minute": peak,
        "weighted_tokens_per_request": round(weighted_per_request, 2),
        "tokens_per_minute": round(tpm, 2),
        "formula": "(input_tokens + output_weighting_factor * output_tokens) * peak_requests_per_minute",
    }


def pan_india_token_model(measured: dict[str, Any], pia: Any) -> dict[str, Any]:
    """Pan-India token model: MEASURED current vs MODELED future-state vs NEEV target.

    ``measured`` keys (from existing reporting/statistics; missing -> 0):
      max_input_tokens, max_output_tokens, avg_input_tokens, avg_output_tokens,
      modeled_context_estimated_tokens (estimate of the modeled context volume).

    ``pia`` is a PanIndiaAssumptions instance (duck-typed: only attributes are read)
    carrying the configurable target tokens + Neev formula inputs.
    """
    weight = getattr(pia, "output_weighting_factor", DEFAULT_OUTPUT_WEIGHTING_FACTOR)
    peak = getattr(pia, "peak_requests_per_minute", DEFAULT_PEAK_REQUESTS_PER_MINUTE)
    target_in = _f(getattr(pia, "target_input_tokens", 125000))
    target_out = _f(getattr(pia, "target_output_tokens", 50000))

    # --- MEASURED CURRENT: actual tokens from today's small repository ---
    cur_in = _f(measured.get("max_input_tokens"))
    cur_out = _f(measured.get("max_output_tokens"))
    measured_current = {
        "tier": TIER_MEASURED_CURRENT,
        "measured_max_input_tokens": round(cur_in, 2),
        "measured_max_output_tokens": round(cur_out, 2),
        "measured_avg_input_tokens": round(_f(measured.get("avg_input_tokens")), 2),
        "measured_avg_output_tokens": round(_f(measured.get("avg_output_tokens")), 2),
        "weighted_tpm": weighted_tpm_calculation(cur_in, cur_out, weight, peak),
        "_basis": "Tokens MEASURED by existing ECS instrumentation on the current repository.",
    }

    # --- PAN-INDIA MODELED: modeled input context volume + target output band ---
    # Modeled input = measured input + modeled context estimate (the future-state
    # retrieval volume the generator represents). Output is the configured target
    # (the local model may cap actual output far below this — see output gap below).
    modeled_ctx_tokens = _f(measured.get("modeled_context_estimated_tokens"))
    modeled_in = cur_in + modeled_ctx_tokens if modeled_ctx_tokens else max(cur_in, target_in)
    pan_india_modeled = {
        "tier": TIER_PAN_INDIA_MODELED,
        "modeled_input_tokens": round(modeled_in, 2),
        "modeled_context_estimated_tokens": round(modeled_ctx_tokens, 2),
        "modeled_output_requirement_tokens": round(target_out, 2),
        "weighted_tpm": weighted_tpm_calculation(modeled_in, target_out, weight, peak),
        "input_token_target_band": [
            getattr(pia, "input_token_target_low", 75000),
            getattr(pia, "input_token_target_high", 125000),
        ],
        "output_token_target_band": [
            getattr(pia, "output_token_target_low", 25000),
            getattr(pia, "output_token_target_high", 50000),
        ],
        "_basis": ("MODELED future-state: measured input + modeled Pan-India context estimate; "
                   "output is the configured enterprise requirement (NOT measured). "
                   "Input token estimate is chars/chars_per_token; actual tokens are MEASURED at run time."),
    }

    # --- NEEV TARGET: the capacity-planning assumption submitted to Finance ---
    neev_target = {
        "tier": TIER_NEEV_TARGET,
        "target_input_tokens": round(target_in, 2),
        "target_output_tokens": round(target_out, 2),
        "weighted_tpm": weighted_tpm_calculation(target_in, target_out, weight, peak),
        "_basis": "Capacity-planning ASSUMPTION submitted to Neev/Finance (not measured).",
    }

    return {
        "tiers": {
            TIER_MEASURED_CURRENT: "Tokens measured today via ECS instrumentation.",
            TIER_PAN_INDIA_MODELED: "Modeled future-state input volume + target output (estimate).",
            TIER_NEEV_TARGET: "Capacity-planning assumption submitted to Finance.",
        },
        "measured_current": measured_current,
        "pan_india_modeled": pan_india_modeled,
        "neev_target": neev_target,
    }


def neev_formula_validation(token_model: dict[str, Any], pia: Any,
                            current_tpm_assumption: float = 1_725_000.0) -> dict[str, Any]:
    """Validate the Neev weighted-TPM against the originally estimated assumption.

    Recomputes TPM from the NEEV target tier and compares it to the manually
    estimated ``current_tpm_assumption`` (default 1.725M). Also reports whether the
    MODELED future-state reaches the target bands, and the output-capability gap.
    """
    weight = getattr(pia, "output_weighting_factor", DEFAULT_OUTPUT_WEIGHTING_FACTOR)
    peak = getattr(pia, "peak_requests_per_minute", DEFAULT_PEAK_REQUESTS_PER_MINUTE)

    neev = token_model["neev_target"]
    modeled = token_model["pan_india_modeled"]
    measured = token_model["measured_current"]

    recalculated_tpm = _f(neev["weighted_tpm"]["tokens_per_minute"])
    delta = recalculated_tpm - _f(current_tpm_assumption)

    in_band = modeled["input_token_target_band"]
    out_band = modeled["output_token_target_band"]
    modeled_in = _f(modeled["modeled_input_tokens"])
    modeled_out = _f(modeled["modeled_output_requirement_tokens"])

    return {
        "formula": "(input_tokens + output_weighting_factor * output_tokens) * peak_requests_per_minute",
        "output_weighting_factor": weight,
        "peak_requests_per_minute": peak,
        "original_estimated_tpm_assumption": round(_f(current_tpm_assumption), 2),
        "benchmark_recalculated_tpm_neev_target": round(recalculated_tpm, 2),
        "delta_tpm_vs_assumption": round(delta, 2),
        "delta_pct_vs_assumption": (round(delta / _f(current_tpm_assumption) * 100, 2)
                                    if _f(current_tpm_assumption) else None),
        "assumption_supported_by_benchmark": bool(abs(delta) <= 0.01 * _f(current_tpm_assumption))
        if _f(current_tpm_assumption) else None,
        "target_band_check": {
            "modeled_input_in_band": in_band[0] <= modeled_in <= in_band[1] if len(in_band) == 2 else None,
            "modeled_input_tokens": round(modeled_in, 2),
            "input_target_band": in_band,
            "output_requirement_in_band": out_band[0] <= modeled_out <= out_band[1] if len(out_band) == 2 else None,
            "output_requirement_tokens": round(modeled_out, 2),
            "output_target_band": out_band,
        },
        "measured_vs_target_tpm": {
            "measured_current_tpm": _f(measured["weighted_tpm"]["tokens_per_minute"]),
            "neev_target_tpm": recalculated_tpm,
            "_note": "Measured current TPM is far below target because today's repository is small; "
                     "the Pan-India modeled tier bridges current measurement to the target assumption.",
        },
        "_basis": "Recomputes the Neev formula from configurable inputs and compares to the "
                  "original manually-estimated 1.725M TPM assumption. MEASURED / MODELED / TARGET kept separate.",
    }


def pan_india_plan(measured: dict[str, Any], pia: Any,
                   current_tpm_assumption: float = 1_725_000.0) -> dict[str, Any]:
    """Full Pan-India capacity bundle: token model + Neev formula validation.

    Bundles ``pan_india_token_model`` + ``neev_formula_validation`` under one block
    with the configurable assumptions echoed for auditability.
    """
    token_model = pan_india_token_model(measured, pia)
    validation = neev_formula_validation(token_model, pia, current_tpm_assumption)
    return {
        "tiers": token_model["tiers"],
        "token_model": token_model,
        "neev_formula_validation": validation,
        "assumptions": pia.to_dict() if hasattr(pia, "to_dict") else {},
    }
