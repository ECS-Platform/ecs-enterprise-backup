"""Calibration mode for the ECS infrastructure benchmark (PART 4).

Takes OBSERVED telemetry (from a real benchmark run, e.g. captured via
``telemetry.RuntimeTelemetry``) and compares it to the model's ESTIMATE, producing
per-metric calibration factors and RECOMMENDED adjusted constants — WITHOUT
overwriting anything unless the caller explicitly applies them.

Input (any subset; missing keys are skipped):
  observed_cpu_cores, observed_ram_mib, observed_runtime_s, observed_files_uploaded,
  observed_evidence_size_kb, observed_prompt_tokens, observed_connector_count,
  observed_db_query_count

Output: a calibration report with, per metric: old estimate, observed value,
calibration factor, recommended new constant, confidence, and notes.
"""

from __future__ import annotations

from typing import Any

from benchmarks.capacity.profiles import CapacityProfile
from benchmarks.capacity.sizing import SizingConstants


def _round(x: Any, n: int = 4) -> Any:
    try:
        return round(float(x), n)
    except (TypeError, ValueError):
        return None


def _confidence(factor: float | None) -> str:
    """Confidence in the recommendation from how far the factor is from 1.0.

    A single observation can't be high-confidence; closeness to the model is a
    proxy for agreement, but we cap at 'medium' (one sample).
    """
    if factor is None:
        return "none"
    dev = abs(factor - 1.0)
    if dev <= 0.15:
        return "medium"      # model already close; small adjustment
    if dev <= 0.5:
        return "low"         # meaningful gap; adjust but gather more samples
    return "very_low"        # large gap; likely workload mismatch — investigate


def _entry(metric: str, old: float, observed: float, *,
           constant: str, current_constant: float, note: str = "") -> dict[str, Any]:
    factor = (observed / old) if old else None
    recommended = (current_constant * factor) if (factor is not None) else None
    return {
        "metric": metric,
        "old_estimate": _round(old),
        "observed": _round(observed),
        "calibration_factor": _round(factor),
        "constant": constant,
        "current_constant": _round(current_constant),
        "recommended_new_constant": _round(recommended),
        "confidence": _confidence(factor),
        "notes": note or "Single-sample calibration; average several runs before applying.",
    }


def calibrate(profile: CapacityProfile, observed: dict[str, Any],
              estimate: dict[str, Any] | None = None,
              constants: SizingConstants | None = None) -> dict[str, Any]:
    """Compare observed telemetry to the estimate; recommend adjusted constants.

    ``estimate`` (optional) is a prior ``estimate_capacity`` result; if absent it
    is computed. Never raises; never mutates constants.
    """
    from benchmarks.capacity.sizing import estimate_capacity

    c = constants or SizingConstants()
    est = estimate or estimate_capacity(profile, constants=c)
    entries: list[dict[str, Any]] = []

    gke = est.get("gke_compute", {})
    ram = est.get("ram_breakdown", {}) or {}

    # CPU: peak cores.
    if observed.get("observed_cpu_cores") is not None:
        old = float(gke.get("peak_cores") or 0)
        entries.append(_entry(
            "peak_cpu_cores", old, float(observed["observed_cpu_cores"]),
            constant="cpu_ms_per_api_request", current_constant=c.cpu_ms_per_api_request,
            note="Scales the dominant API CPU-ms constant; verify workload mix."))

    # RAM: peak MiB.
    if observed.get("observed_ram_mib") is not None:
        old = float(ram.get("peak_total_mib") or gke.get("peak_ram_mib") or 0)
        entries.append(_entry(
            "peak_ram_mib", old, float(observed["observed_ram_mib"]),
            constant="ram_mib_per_api_request", current_constant=c.ram_mib_per_api_request))

    # Runtime: wall-clock vs a nominal expectation (no model runtime -> factor only).
    if observed.get("observed_runtime_s") is not None:
        entries.append({
            "metric": "runtime_s", "observed": _round(observed["observed_runtime_s"]),
            "old_estimate": None, "calibration_factor": None,
            "constant": "(informational)", "confidence": "none",
            "notes": "Recorded for trend tracking; no model runtime baseline to calibrate against."})

    # Evidence size.
    if observed.get("observed_evidence_size_kb") is not None:
        old = float(profile.avg_evidence_size_kb)
        entries.append(_entry(
            "avg_evidence_size_kb", old, float(observed["observed_evidence_size_kb"]),
            constant="profile.avg_evidence_size_kb", current_constant=old,
            note="Update the profile's avg_evidence_size_kb for storage/network accuracy."))

    # Prompt tokens.
    if observed.get("observed_prompt_tokens") is not None:
        old = float((est.get("token_feed") or {}).get("total") or 0)
        entries.append(_entry(
            "prompt_tokens", old, float(observed["observed_prompt_tokens"]),
            constant="measured_tokens.avg_total_tokens", current_constant=old,
            note="Pass measured_tokens to estimate_capacity for exact prompt sizing."))

    # Connector count.
    if observed.get("observed_connector_count") is not None:
        old = float((est.get("connector_benchmark") or {}).get("connector_count") or 0)
        entries.append(_entry(
            "connector_count", old, float(observed["observed_connector_count"]),
            constant="(registry-derived)", current_constant=old,
            note="Connector set comes from the live registry; large gaps imply "
                 "adapters enabled/disabled vs assumption."))

    # DB query count.
    if observed.get("observed_db_query_count") is not None:
        old = float((est.get("db_agent_benchmark") or {}).get("queries_per_day") or 0)
        entries.append(_entry(
            "db_queries_per_day", old, float(observed["observed_db_query_count"]),
            constant="(activity-derived)", current_constant=old,
            note="Adjust connector_runs_per_day / scheduler_jobs_per_day in the profile."))

    # Files uploaded.
    if observed.get("observed_files_uploaded") is not None:
        old = float((est.get("object_storage_detail") or {}).get("file_counts", {}).get("per_day") or 0)
        entries.append(_entry(
            "files_per_day", old, float(observed["observed_files_uploaded"]),
            constant="evidence_per_connector_run", current_constant=5.0,
            note="Scales assumed evidence objects per connector run."))

    factors = [e["calibration_factor"] for e in entries if e.get("calibration_factor") is not None]
    overall = _round(sum(factors) / len(factors)) if factors else None

    return {
        "profile": profile.key,
        "calibration": entries,
        "overall_calibration_factor": overall,
        "applied": False,
        "how_to_apply": "Pass the recommended constants to SizingConstants.from_overrides(...) "
                        "(and measured_tokens / updated profile fields) — nothing is changed "
                        "automatically.",
        "_meta": {
            "kind": "calibration_report",
            "provenance": "Compares OBSERVED telemetry to the model ESTIMATE. Single "
                          "observations are indicative; average multiple runs before applying.",
        },
    }
