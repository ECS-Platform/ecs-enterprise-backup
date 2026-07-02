"""Neev capacity projection + variance for the ECS Neev validation benchmark.

Pure standard library. Turns MEASURED (or ESTIMATED, in dry-run) per-request token
values into the Neev calculator outputs and compares them to the current planning
TARGET (125,000 input / 50,000 output, 9x output weighting, 3 RPM).

Label discipline (never mixed):
  MEASURED  - actual benchmark token instrumentation result.
  MODELED   - derived from measured benchmark data (e.g. weighted tokens).
  PROJECTED - future usage derived from measured/modeled values (daily/monthly/annual).
  TARGET    - existing planning assumption (125K / 50K / 9x / 3 RPM).
  ESTIMATED - used only where a measurement is unavailable (e.g. dry-run input tokens).

This module does NOT try to prove the current assumption; it evaluates whether the
assumption is realistic versus measured ECS prompt token shape.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class NeevAssumptions:
    """Configurable Neev calculator assumptions. Output weighting + TARGET planning
    values match the current Neev assumption; the rest are budgeting inputs."""

    output_weighting_factor: int = 9
    peak_rpm_options: tuple[int, ...] = (1, 2, 3, 5)
    target_peak_rpm: int = 3
    # Throughput assumptions for daily/monthly/annual PROJECTED volumes.
    requests_per_day: int = 400
    working_days_per_month: int = 22
    working_months_per_year: int = 12
    # Recommended-budget headroom on top of the measured realistic peak.
    headroom_factor: float = 0.25
    # TARGET planning assumption under test.
    target_input_tokens: int = 125000
    target_output_tokens: int = 50000

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["peak_rpm_options"] = list(self.peak_rpm_options)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "NeevAssumptions":
        data = data or {}
        known = {k: data[k] for k in data if k in cls.__dataclass_fields__}
        if "peak_rpm_options" in known and known["peak_rpm_options"] is not None:
            known["peak_rpm_options"] = tuple(int(x) for x in known["peak_rpm_options"])
        return cls(**known)


def weighted_tokens_per_request(input_tokens: int, output_tokens: int,
                                weighting: int = 9) -> int:
    """Neev weighted tokens = input + weighting x output. MODELED from measured tokens."""
    return int(round(int(input_tokens) + int(weighting) * int(output_tokens)))


def peak_tpm(weighted_per_request: int, rpm: int) -> int:
    """Peak tokens-per-minute = weighted tokens/request x peak RPM."""
    return int(round(int(weighted_per_request) * int(rpm)))


def variance_percent(measured: float | None, target: float | None) -> float | None:
    """(measured - target) / target * 100. Negative => measured below target (target
    is over-tokenized / conservative); positive => measured above target."""
    if measured is None or target in (None, 0):
        return None
    return round((float(measured) - float(target)) / float(target) * 100.0, 2)


def classify_variance(input_var: float | None, output_var: float | None,
                      *, realistic_band: float = 15.0) -> str:
    """Conclude whether the current TARGET looks realistic / conservative /
    over-tokenized / under-estimated, given input & output variance percentages.

    Convention: variance is (measured - target)/target. Strongly negative means the
    target is far ABOVE measured (over-tokenized). Positive beyond the band means
    measured exceeds target (under-estimated)."""
    if input_var is None and output_var is None:
        return "indeterminate (no measured tokens available; dry-run or all timed out)"
    vin = input_var if input_var is not None else 0.0
    vout = output_var if output_var is not None else 0.0
    worst = max(vin, vout)        # most likely to be under-estimated
    most_neg = min(vin, vout)     # most likely to be over-tokenized

    if worst > realistic_band:
        return ("UNDER-ESTIMATED: measured ECS tokens exceed the current planning "
                "assumption; the assumption should be raised")
    if most_neg < -50.0:
        return ("OVER-TOKENIZED: the current planning assumption is far above measured "
                "ECS workload tokens (significant over-provisioning)")
    if most_neg < -realistic_band:
        return ("CONSERVATIVE: the current planning assumption sits safely above measured "
                "ECS workload tokens (headroom built in, mildly over-tokenized)")
    return ("REALISTIC: the current planning assumption is in line with measured ECS "
            "workload tokens (within +/- {:.0f}%)".format(realistic_band))


def project_request(input_tokens: int, output_tokens: int,
                    assumptions: NeevAssumptions) -> dict[str, Any]:
    """Full Neev calculator output for one request's measured tokens. PROJECTED volumes
    use the configurable throughput assumptions and the weighted token model."""
    w = weighted_tokens_per_request(input_tokens, output_tokens,
                                    assumptions.output_weighting_factor)
    tpm = {f"peak_tpm_{rpm}_rpm": peak_tpm(w, rpm) for rpm in assumptions.peak_rpm_options}

    daily = w * assumptions.requests_per_day
    monthly = daily * assumptions.working_days_per_month
    annual = monthly * assumptions.working_months_per_year
    return {
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "weighted_tokens_per_request": w,           # MODELED
        **tpm,                                        # MODELED (peak TPM @ each RPM)
        "daily_tokens": int(daily),                  # PROJECTED
        "monthly_tokens": int(monthly),              # PROJECTED
        "annual_tokens": int(annual),                # PROJECTED
        "monthly_billion_tokens": round(monthly / 1e9, 6),
        "annual_billion_tokens": round(annual / 1e9, 6),
    }


def compare_to_target(input_tokens: int, output_tokens: int,
                      assumptions: NeevAssumptions) -> dict[str, Any]:
    """Variance of measured tokens vs the current TARGET planning assumption."""
    w_measured = weighted_tokens_per_request(
        input_tokens, output_tokens, assumptions.output_weighting_factor)
    w_target = weighted_tokens_per_request(
        assumptions.target_input_tokens, assumptions.target_output_tokens,
        assumptions.output_weighting_factor)
    tpm_measured = peak_tpm(w_measured, assumptions.target_peak_rpm)
    tpm_target = peak_tpm(w_target, assumptions.target_peak_rpm)

    in_var = variance_percent(input_tokens, assumptions.target_input_tokens)
    out_var = variance_percent(output_tokens, assumptions.target_output_tokens)
    return {
        "target_input_tokens": assumptions.target_input_tokens,        # TARGET
        "target_output_tokens": assumptions.target_output_tokens,      # TARGET
        "target_weighted_tokens_per_request": w_target,                # TARGET
        "target_peak_tpm_3_rpm": tpm_target,                           # TARGET
        "measured_weighted_tokens_per_request": w_measured,            # MODELED
        "measured_peak_tpm_3_rpm": tpm_measured,                       # MODELED
        "input_variance_percent": in_var,
        "output_variance_percent": out_var,
        "weighted_token_variance_percent": variance_percent(w_measured, w_target),
        "peak_tpm_variance_percent": variance_percent(tpm_measured, tpm_target),
        "conclusion": classify_variance(in_var, out_var),
    }


def recommend_budget(peak_input_tokens: int, peak_output_tokens: int,
                     assumptions: NeevAssumptions) -> dict[str, Any]:
    """Three budgeting values:

    A. Measured realistic peak  - the largest successful realistic benchmark result.
    B. Recommended Neev value   - measured peak + headroom (default 25%).
    C. Current planning compare - recommended vs the 125K / 50K TARGET.
    """
    hf = 1.0 + float(assumptions.headroom_factor)
    rec_in = int(math.ceil(peak_input_tokens * hf))
    rec_out = int(math.ceil(peak_output_tokens * hf))
    rec_weighted = weighted_tokens_per_request(
        rec_in, rec_out, assumptions.output_weighting_factor)
    rec_tpm_3 = peak_tpm(rec_weighted, assumptions.target_peak_rpm)
    return {
        # A. MEASURED realistic peak
        "measured_peak_input_tokens": int(peak_input_tokens),
        "measured_peak_output_tokens": int(peak_output_tokens),
        # B. Recommended Neev value (MODELED: peak + headroom)
        "headroom_factor": assumptions.headroom_factor,
        "recommended_input_tokens": rec_in,
        "recommended_output_tokens": rec_out,
        "recommended_weighted_tokens_per_request": rec_weighted,
        "recommended_peak_tpm_3_rpm": rec_tpm_3,
        # C. Comparison to the current planning TARGET
        "target_input_tokens": assumptions.target_input_tokens,
        "target_output_tokens": assumptions.target_output_tokens,
        "recommended_vs_target_input_percent": variance_percent(
            rec_in, assumptions.target_input_tokens),
        "recommended_vs_target_output_percent": variance_percent(
            rec_out, assumptions.target_output_tokens),
    }
