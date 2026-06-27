"""Enterprise benchmark reporting: statistics + capacity planning output.

Consumes the per-request rows captured by ``enterprise_runner`` (which come from
the EXISTING ECS instrumentation) and emits:

* ``enterprise_report.json``   — full report (statistics, per-category, worst
  case, capacity planning) with Measured / Estimated / Projected kept separate.
* ``enterprise_summary.json``  — condensed headline view.
* ``enterprise_results.csv``   — flat per-request table for spreadsheets.

No ECS or instrumentation changes; pure aggregation over collected rows.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchmarks.ai_workload import capacity_planning
from benchmarks.ai_workload.bench_statistics import summarize
from benchmarks.ai_workload.capacity_planning import CapacityAssumptions, WorstCaseAssumptions

# Metrics measured by the existing ECS instrumentation (ecs_platform.rag.answer).
_MEASURED_METRIC_FIELDS = [
    "retrieved_documents",
    "retrieved_chunks",
    "prompt_size_chars",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "retrieval_latency_ms",
    "prompt_build_latency_ms",
    "llm_latency_ms",
    "end_to_end_latency_ms",
]

# Flat CSV column order (existing schema first, then enterprise additions).
_CSV_COLUMNS = [
    "timestamp",
    "profile_key",
    "workload",
    "category",
    "prompt_class",
    "response_intent",
    "top_k",
    "ok",
    "grounded",
    "mode",
    "provider",
    "model",
    "request_id",
    # MEASURED (existing instrumentation)
    "retrieved_documents",
    "retrieved_chunks",
    "prompt_size_chars",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "retrieval_latency_ms",
    "prompt_build_latency_ms",
    "llm_latency_ms",
    "end_to_end_latency_ms",
    # MEASURED (benchmark-known inputs, no instrumentation change)
    "system_prompt_chars",
    "system_prompt_bytes",
    "user_prompt_chars",
    "user_prompt_bytes",
    # DERIVED (clearly labeled)
    "retrieved_context_chars_derived",
    "prompt_bytes_derived",
    "runner_end_to_end_ms",
    # MODELED (Pan-India future-state context provenance; not measured evidence)
    "modeled_context",
    "modeled_context_chars",
    # DIAGNOSTIC (failures are never silently swallowed)
    "error",
    "error_type",
    "error_message",
    "error_traceback",
]


# Approx chars-per-token for the system-prompt token estimate ONLY (the frozen
# instrumentation reports prompt_size_chars, not a per-segment token split). Used
# solely to seed the worst-case system-prompt growth axis; clearly an estimate.
_CHARS_PER_TOKEN = 4.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _model_output_cap() -> int | None:
    """Best-effort configured LLM output cap (config/llm.yaml max_output_tokens).

    Honors the ECS_LLM_MAX_TOKENS env override, else parses the documented default
    from config/llm.yaml (``${ECS_LLM_MAX_TOKENS:-2048}``). Never raises; returns
    None if it cannot be determined. This lets Finance see the local model's output
    ceiling alongside the target enterprise output requirement.
    """
    import os
    import re

    env = os.environ.get("ECS_LLM_MAX_TOKENS")
    if env and env.strip().isdigit():
        return int(env.strip())
    try:
        text = Path("config/llm.yaml").read_text(encoding="utf-8")
        m = re.search(r"max_output_tokens:\s*\$\{ECS_LLM_MAX_TOKENS:-(\d+)\}", text)
        if m:
            return int(m.group(1))
        m = re.search(r"max_output_tokens:\s*(\d+)", text)
        if m:
            return int(m.group(1))
    except OSError:
        pass
    return None


def _provider_model(rows: list[dict[str, Any]]) -> tuple[str, str]:
    for r in rows:
        if r.get("provider") or r.get("model"):
            return str(r.get("provider", "")), str(r.get("model", ""))
    return "", ""


def _profile_token_snapshot(r: dict[str, Any]) -> dict[str, Any]:
    """Compact identity + token view of a single request row (no new math)."""
    return {
        "profile_key": r.get("profile_key"),
        "workload": r.get("workload"),
        "category": r.get("category"),
        "top_k": r.get("top_k"),
        "input_tokens": r.get("input_tokens"),
        "output_tokens": r.get("output_tokens"),
        "total_tokens": r.get("total_tokens"),
        "prompt_size_chars": r.get("prompt_size_chars"),
        "retrieved_documents": r.get("retrieved_documents"),
        "end_to_end_latency_ms": r.get("end_to_end_latency_ms"),
    }


def _measured_worst_case(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract MEASURED worst-case maxima consumed by capacity_planning.worst_case_plan.

    All values come straight from the benchmark rows (existing instrumentation);
    nothing is invented. ``worst_case``-category rows are preferred when present so
    the envelope reflects the heaviest tier; otherwise all rows are used.
    """
    wc_rows = [r for r in rows if r.get("category") == "worst_case"] or rows

    def mx(field_name: str) -> float:
        s = summarize([r.get(field_name) for r in wc_rows])
        return float(s.maximum) if s.maximum is not None else 0.0

    max_sys_chars = mx("system_prompt_chars")
    return {
        "max_input_tokens": mx("input_tokens"),
        "max_output_tokens": mx("output_tokens"),
        "max_total_tokens": mx("total_tokens"),
        "max_prompt_size_chars": mx("prompt_size_chars"),
        "max_retrieved_context_chars": mx("retrieved_context_chars_derived"),
        "max_retrieved_documents": mx("retrieved_documents"),
        "max_retrieved_chunks": mx("retrieved_chunks"),
        "max_end_to_end_ms": mx("end_to_end_latency_ms"),
        # System-prompt token estimate (chars/4) — seeds the growth axis only.
        "max_system_prompt_tokens": round(max_sys_chars / _CHARS_PER_TOKEN, 2),
        "_source_rows": len(wc_rows),
        "_basis": "Maxima of MEASURED per-request fields (existing instrumentation).",
    }


def build_report(rows: list[dict[str, Any]], assumptions: CapacityAssumptions,
                 *, include_worst_case: bool = False,
                 worst_case_assumptions: WorstCaseAssumptions | None = None,
                 pan_india_assumptions: dict[str, Any] | None = None) -> dict[str, Any]:
    """Aggregate per-request rows into the enterprise report structure.

    When ``include_worst_case`` is True an additive ``worst_case`` section and an
    ``executive_summary`` (maximum realistic token analysis + worst-case budget) are
    appended, keeping Measured / Worst-Case / Projected / Forecast strictly separate.
    Default False -> byte-for-byte the original standard report (backward compatible).

    When any ``pan_india_enterprise``-category rows are present (or
    ``pan_india_assumptions`` are supplied) an additive ``pan_india_capacity_validation``
    section is appended: MEASURED current vs MODELED future-state vs NEEV target, with
    the weighted-TPM recalculation. Strictly separated, never mixed.
    """
    ok_rows = [r for r in rows if r.get("ok")]
    provider, model = _provider_model(rows)

    # Per-metric statistics (min/avg/median/max/P90/P95/P99/stddev).
    statistics = {f: summarize([r.get(f) for r in rows]).to_dict() for f in _MEASURED_METRIC_FIELDS}

    # Per-category token + latency rollup.
    by_category: dict[str, Any] = {}
    for r in rows:
        cat = r.get("category", "uncategorized")
        by_category.setdefault(cat, []).append(r)
    category_stats = {
        cat: {
            "requests": len(crows),
            "total_tokens": summarize([r.get("total_tokens") for r in crows]).to_dict(),
            "end_to_end_latency_ms": summarize([r.get("end_to_end_latency_ms") for r in crows]).to_dict(),
        }
        for cat, crows in by_category.items()
    }

    # Worst-case (maximum total tokens) row — drives infrastructure sizing.
    worst = None
    token_rows = [r for r in rows if isinstance(r.get("total_tokens"), (int, float))]
    if token_rows:
        worst = max(token_rows, key=lambda r: r.get("total_tokens") or 0)
        worst = _profile_token_snapshot(worst)

    # Max-token PROFILES (which workload produced each maximum) — for token-budget
    # approval. Additive; reuses the same rows, no new measurement/token logic.
    def _max_profile_by(metric: str, *, rows_subset: list[dict[str, Any]] | None = None):
        candidates = [r for r in (rows_subset if rows_subset is not None else rows)
                      if isinstance(r.get(metric), (int, float))]
        if not candidates:
            return None
        return _profile_token_snapshot(max(candidates, key=lambda r: r.get(metric) or 0))

    wco_rows = [r for r in rows if r.get("category") == "worst_case_output"]
    max_profiles = {
        "max_input_token_profile": _max_profile_by("input_tokens"),
        "max_output_token_profile": _max_profile_by("output_tokens"),
        "max_total_token_profile": _max_profile_by("total_tokens"),
        # Max realistic OUTPUT among the dedicated long-output tier (when present).
        "max_realistic_output_profile": _max_profile_by("output_tokens", rows_subset=wco_rows),
        "_basis": "Observed maxima per metric; identifies the workload behind each peak.",
    }

    # Capacity planning from measured token + latency stats.
    tot = statistics["total_tokens"]
    inp = statistics["input_tokens"]
    out = statistics["output_tokens"]
    e2e = statistics["end_to_end_latency_ms"]
    measured_for_capacity = {
        "avg_total_tokens": tot["average"],
        "peak_total_tokens": tot["maximum"],
        "avg_input_tokens": inp["average"],
        "avg_output_tokens": out["average"],
        "avg_end_to_end_ms": e2e["average"],
        "p95_end_to_end_ms": e2e["p95"],
    }
    capacity = capacity_planning.plan(measured_for_capacity, assumptions)

    report: dict[str, Any] = {
        "meta": {
            "generated_at": _utc_now(),
            "provider": provider,
            "model": model,
            "total_requests": len(rows),
            "successful_requests": len(ok_rows),
            "failed_requests": len(rows) - len(ok_rows),
            "benchmark_mode": "worst_case" if include_worst_case else "standard",
            "benchmark": "ECS enterprise AI workload",
            "reuses": "ecs_platform.rag.answer + existing instrumentation (no instrumentation changes)",
        },
        "measured": {
            "statistics": statistics,
            "by_category": category_stats,
            "worst_case_max_tokens": worst,
            "max_token_profiles": max_profiles,
            "field_provenance": {
                "from_instrumentation": _MEASURED_METRIC_FIELDS,
                "from_benchmark_inputs": [
                    "system_prompt_chars", "system_prompt_bytes",
                    "user_prompt_chars", "user_prompt_bytes",
                ],
                "derived": {
                    "retrieved_context_chars_derived": "prompt_size_chars - user_prompt_chars (approx; template overhead included)",
                    "prompt_bytes_derived": "approximated by prompt_size_chars (ASCII); exact bytes require capturing the prompt text, which the frozen instrumentation does not expose",
                },
            },
        },
        "capacity_planning": capacity,
        "notes": [
            "Measured = observed via existing ECS instrumentation.",
            "Estimated = single-stream capacity derived from measured latency (concurrency=1).",
            "Projected = production load from operator assumptions x measured tokens.",
            "System/user prompt sizes are measured from the benchmark's own inputs (SYSTEM_PROMPT + question) without modifying instrumentation.",
        ],
    }

    # ---- Diagnostics: surface failures so a broken run is debuggable from the
    # report alone (never silently swallowed). Errors are also in the per-request
    # rows / CSV / enterprise_run.log. ----
    failed_rows = [r for r in rows if not r.get("ok")]
    if failed_rows:
        error_type_counts: dict[str, int] = {}
        for r in failed_rows:
            et = str(r.get("error_type") or "Unknown")
            error_type_counts[et] = error_type_counts.get(et, 0) + 1
        report["diagnostics"] = {
            "failed_requests": len(failed_rows),
            "error_type_counts": error_type_counts,
            "failures": [
                {
                    "profile_key": r.get("profile_key"),
                    "workload": r.get("workload"),
                    "top_k": r.get("top_k"),
                    "mode": r.get("mode"),
                    "error_type": r.get("error_type"),
                    "error_message": r.get("error_message") or r.get("error"),
                    # Keep the report readable: full traceback lives in the JSONL/CSV
                    # and enterprise_run.log; here we keep the last line for triage.
                    "error_traceback_tail": (
                        (r.get("error_traceback") or "").strip().splitlines()[-1]
                        if r.get("error_traceback") else ""
                    ),
                }
                for r in failed_rows
            ],
            "_note": "Full tracebacks are in enterprise_requests.jsonl / enterprise_results.csv / enterprise_run.log.",
        }

    # ---- Additive worst-case layer (single reporting framework; no parallel one) ----
    # When requested, append the worst-case capacity plan + an executive summary.
    # Measured / Worst-Case / Projected / Forecast are kept strictly separate by the
    # provenance tiers that capacity_planning.worst_case_plan stamps on every block.
    if include_worst_case:
        wc = worst_case_assumptions or WorstCaseAssumptions()
        measured_worst_case = _measured_worst_case(rows)
        wc_plan = capacity_planning.worst_case_plan(measured_worst_case, assumptions, wc)
        report["worst_case"] = {
            "measured_baseline": measured_worst_case,
            "capacity_planning": wc_plan,
        }
        report["executive_summary"] = _executive_summary(report, wc_plan)
        report["meta"]["worst_case_requests"] = len(
            [r for r in rows if r.get("category") == "worst_case"])
        report["notes"].extend([
            "Worst-Case = measured worst-case x documented headroom (ESTIMATED upper bound).",
            "Forecast = multi-year growth applied to the projection (FORECAST).",
            "Worst-case projections/forecasts are NEVER presented as measured results.",
        ])

    # ---- Additive Pan-India capacity validation (single capacity framework) ----
    # Appended when there are pan_india_enterprise rows OR explicit assumptions. It
    # keeps MEASURED current / MODELED future-state / NEEV target strictly separate
    # and recalculates the Neev weighted TPM. Standard/worst-case reports without
    # Pan-India rows or assumptions are unchanged (section omitted).
    pie_rows = [r for r in rows if r.get("category") == "pan_india_enterprise"]
    if pie_rows or pan_india_assumptions:
        report["pan_india_capacity_validation"] = _pan_india_section(
            rows, pie_rows, pan_india_assumptions or {})
        report["notes"].extend([
            "Pan-India MEASURED current = tokens measured today (small repository).",
            "Pan-India MODELED = modeled future-state input volume + target output (estimate, not measured).",
            "Pan-India NEEV target = capacity-planning assumption submitted to Finance.",
            "Modeled/target Pan-India values are NEVER presented as measured results.",
        ])

    return report


def _pan_india_section(all_rows: list[dict[str, Any]],
                       pie_rows: list[dict[str, Any]],
                       pan_india_assumptions: dict[str, Any]) -> dict[str, Any]:
    """Build the ``pan_india_capacity_validation`` section (additive).

    Reuses ``capacity_planning.pan_india_plan`` (single capacity framework) for the
    MEASURED/MODELED/NEEV token model + Neev formula validation, and adds the
    max-token PROFILE identification requested for token-budget approval.
    """
    from benchmarks.ai_workload.pan_india_reference_context import (
        PanIndiaAssumptions, context_size_estimate)

    pia = PanIndiaAssumptions.from_dict(pan_india_assumptions)

    # Prefer Pan-India rows for the measured envelope (heaviest modeled-context tier);
    # fall back to all rows if the tier was not run.
    measure_rows = pie_rows or all_rows

    def mx(field_name: str, src: list[dict[str, Any]]) -> float:
        s = summarize([r.get(field_name) for r in src])
        return float(s.maximum) if s.maximum is not None else 0.0

    def avg(field_name: str, src: list[dict[str, Any]]) -> float:
        s = summarize([r.get(field_name) for r in src])
        return float(s.average) if s.average is not None else 0.0

    # MODELED context size estimate (uses the SAME generator + assumptions).
    ctx_estimate = context_size_estimate(pia) if pie_rows else {
        "modeled_context_estimated_tokens": 0,
        "modeled_context_chars": 0,
        "_basis": "No pan_india_enterprise rows in this run; modeled size from assumptions only.",
    }

    measured_for_pan_india = {
        "max_input_tokens": mx("input_tokens", measure_rows),
        "max_output_tokens": mx("output_tokens", measure_rows),
        "avg_input_tokens": avg("input_tokens", measure_rows),
        "avg_output_tokens": avg("output_tokens", measure_rows),
        "modeled_context_estimated_tokens": _f_local(
            ctx_estimate.get("modeled_context_estimated_tokens")),
    }

    plan = capacity_planning.pan_india_plan(measured_for_pan_india, pia)

    # Max-token PROFILES (which workload produced each peak) — measured vs modeled.
    def _max_profile_by(metric: str, src: list[dict[str, Any]]):
        candidates = [r for r in src if isinstance(r.get(metric), (int, float))]
        if not candidates:
            return None
        return _profile_token_snapshot(max(candidates, key=lambda r: r.get(metric) or 0))

    def _max_modeled_weighted_profile(src: list[dict[str, Any]]):
        weight = float(getattr(pia, "output_weighting_factor", 9) or 9)
        candidates = [r for r in src if isinstance(r.get("input_tokens"), (int, float))]
        if not candidates:
            return None

        def weighted(r):
            return _f_local(r.get("input_tokens")) + weight * _f_local(r.get("output_tokens"))

        best = max(candidates, key=weighted)
        snap = _profile_token_snapshot(best)
        snap["weighted_tokens_per_request"] = round(weighted(best), 2)
        snap["output_weighting_factor"] = weight
        return snap

    # MEASURED output cap context (so finance sees the local-model output ceiling).
    measured_max_output = measured_for_pan_india["max_output_tokens"]

    return {
        "purpose": ("Evidence-backed input/output token assumptions for Neev/Finance, "
                    "based on the benchmark rather than a manual estimate. MEASURED current, "
                    "MODELED future-state and NEEV target are kept strictly separate."),
        "modeled_context_estimate": ctx_estimate,
        "token_model": plan["token_model"],
        "neev_formula_validation": plan["neev_formula_validation"],
        "output_token_modelling": {
            "measured_output_tokens": round(measured_max_output, 2),
            "configured_model_output_cap": _model_output_cap(),
            "target_enterprise_output_requirement": getattr(pia, "target_output_tokens", 50000),
            "gap_current_vs_target": round(
                _f_local(getattr(pia, "target_output_tokens", 50000)) - measured_max_output, 2),
            "_note": ("If the local model output is capped (e.g. 512 tokens) the benchmark reports the "
                      "MEASURED output, the configured model cap, the target enterprise requirement and "
                      "the gap. It NEVER claims the model generated the target output."),
        },
        "max_profiles": {
            "max_measured_input_profile": _max_profile_by("input_tokens", measure_rows),
            "max_measured_output_profile": _max_profile_by("output_tokens", measure_rows),
            "max_measured_total_profile": _max_profile_by("total_tokens", measure_rows),
            "max_modeled_input_profile": _max_profile_by("input_tokens", pie_rows) if pie_rows else None,
            "max_modeled_weighted_request_profile": _max_modeled_weighted_profile(pie_rows) if pie_rows else None,
            "_basis": "Observed maxima per metric over Pan-India rows (or all rows if the tier was not run).",
        },
        "assumptions": pia.to_dict(),
        "_provenance": plan["tiers"],
    }


def _f_local(x: Any) -> float:
    try:
        return float(x) if x is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _executive_summary(report: dict[str, Any], wc_plan: dict[str, Any]) -> dict[str, Any]:
    """Maximum-realistic-token analysis + worst-case budget for executive budgeting.

    Pure selection/relabelling over already-computed blocks (no new arithmetic),
    presenting the four provenance tiers side by side for procurement sign-off.
    """
    headline = wc_plan["worst_case_headline"]
    forecast = wc_plan["forecast"]
    base_measured = report["capacity_planning"]["measured"]
    return {
        "purpose": "Maximum realistic enterprise token consumption for LLM procurement, "
                   "token-budget approval, infrastructure sizing and 5-year budgeting.",
        "measured_baseline": {
            "tier": capacity_planning.TIER_MEASURED,
            "avg_total_tokens_per_request": base_measured["avg_total_tokens"],
            "peak_total_tokens_per_request": base_measured["peak_total_tokens"],
        },
        "maximum_realistic_per_request": {
            "tier": capacity_planning.TIER_WORST_CASE,
            "input_tokens": headline["maximum_realistic_input_tokens"],
            "output_tokens": headline["maximum_realistic_output_tokens"],
            "total_tokens": headline["maximum_realistic_total_tokens"],
            "latency_ms": headline["worst_case_latency_ms"],
        },
        "five_year_worst_case_budget": {
            "tier": capacity_planning.TIER_FORECAST,
            **forecast["final_year_worst_case_budget"],
            "cumulative_forecast": forecast["cumulative_forecast"],
        },
        "_basis": "Selection over measured baseline + worst-case envelope + forecast; "
                  "tiers kept separate (see worst_case.capacity_planning.tiers).",
    }


def write_report(report: dict[str, Any], rows: list[dict[str, Any]], out_dir: Path) -> dict[str, str]:
    """Write the three report artifacts. Returns the paths written."""
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "enterprise_report.json"
    summary_path = out_dir / "enterprise_summary.json"
    csv_path = out_dir / "enterprise_results.csv"

    with report_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=True)

    summary = {
        "meta": report["meta"],
        "headline_statistics": {
            "total_tokens": report["measured"]["statistics"]["total_tokens"],
            "input_tokens": report["measured"]["statistics"]["input_tokens"],
            "output_tokens": report["measured"]["statistics"]["output_tokens"],
            "end_to_end_latency_ms": report["measured"]["statistics"]["end_to_end_latency_ms"],
            "retrieval_latency_ms": report["measured"]["statistics"]["retrieval_latency_ms"],
        },
        "worst_case_max_tokens": report["measured"]["worst_case_max_tokens"],
        "capacity_headline": {
            "measured": report["capacity_planning"]["measured"],
            "estimated": report["capacity_planning"]["estimated"],
            "projected_requests": report["capacity_planning"]["projected"]["requests"],
            "projected_tokens": report["capacity_planning"]["projected"]["tokens"],
        },
        "notes": report["notes"],
    }
    # Additive worst-case headline in the same summary (no separate summary file).
    if "worst_case" in report:
        wc_plan = report["worst_case"]["capacity_planning"]
        summary["worst_case_headline"] = wc_plan["worst_case_headline"]
        summary["worst_case_tiers"] = wc_plan["tiers"]
        summary["executive_summary"] = report.get("executive_summary")

    # Additive Pan-India headline in the same summary (no separate summary file).
    if "pan_india_capacity_validation" in report:
        piv = report["pan_india_capacity_validation"]
        summary["pan_india_capacity_validation"] = {
            "token_model": piv["token_model"],
            "neev_formula_validation": piv["neev_formula_validation"],
            "output_token_modelling": piv["output_token_modelling"],
            "max_profiles": piv["max_profiles"],
        }

    with summary_path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=True)

    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in _CSV_COLUMNS})

    paths = {
        "report": str(report_path),
        "summary": str(summary_path),
        "csv": str(csv_path),
    }

    # Additive worst-case forecast CSV (one row per forecast year) — same framework,
    # written only when the report carries a worst-case layer.
    if "worst_case" in report:
        forecast_csv = out_dir / "enterprise_worst_case_forecast.csv"
        cols = [
            "year", "tier", "demand_growth_factor", "token_growth_factor", "concurrent_users",
            "worst_case_input_tokens_per_request", "worst_case_output_tokens_per_request",
            "worst_case_total_tokens_per_request", "requests_per_month", "requests_per_year",
            "monthly_total_tokens", "yearly_total_tokens", "monthly_total_cost", "yearly_total_cost",
        ]
        years = report["worst_case"]["capacity_planning"]["forecast"]["years"]
        with forecast_csv.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            writer.writeheader()
            for yr in years:
                writer.writerow({k: yr.get(k, "") for k in cols})
        paths["worst_case_forecast_csv"] = str(forecast_csv)

    return paths
