"""ECS Neev validation benchmark — realistic ECS token sizing for Gemini 2.5 Pro budgeting.

PURPOSE
-------
Validate, objectively, whether the current Neev AI capacity-planning assumption
(125,000 input / 50,000 output tokens per request, 9x output weighting, 3 RPM) is
realistic, conservative, over-tokenized, or under-estimated — by MEASURING the real
token shape of realistic ECS assessment prompts.

This is ADDITIVE. It reuses the existing ECS LLM provider abstraction + token
instrumentation (``ecs_platform.llm_engine.provider`` -> ``generate_with_metadata``,
which returns model-reported prompt/eval token counts) and the existing benchmark
statistics helper (``benchmarks.ai_workload.bench_statistics``). It does NOT modify
ECS, the RAG logic, or the existing benchmark runner / reporting / capacity framework.

RUNTIME / TARGET (guardrail)
----------------------------
Local Ollama is used ONLY for engineering benchmark execution. Gemini 2.5 Pro is the
production target. A local Ollama result is an ENGINEERING BENCHMARK; Gemini 2.5 Pro
sizing is a PROJECTION using the MEASURED ECS token shape. This tool never claims that
Gemini 2.5 Pro was measured when it was run locally on Ollama.

MODES
-----
* ``--dry-run``  : build realistic prompts, ESTIMATE input tokens, skip the LLM call,
                   write the prompt-composition report. Runs on an 8 GB workstation with
                   no Docker / Ollama / Postgres / yaml.
* full run       : send each realistic prompt to the local provider and MEASURE input +
                   output tokens and latency. Needs the 16 GB stack (Docker / Ollama /
                   Postgres / PGVector / MinIO).

Label discipline (never mixed): MEASURED / MODELED / PROJECTED / TARGET / ESTIMATED.

Usage:
    python scripts/run_neev_validation_benchmark.py --dry-run
    python scripts/run_neev_validation_benchmark.py --profiles all --max-output-tokens 1024 --timeout-seconds 300
    python scripts/run_neev_validation_benchmark.py --profiles small,full,multi_app
    python scripts/run_neev_validation_benchmark.py --profiles enterprise,large_repository --allow-timeout-evidence
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchmarks.ai_workload import bench_statistics
from benchmarks.ai_workload.neev_capacity_projection import (
    NeevAssumptions, compare_to_target, project_request, recommend_budget,
    weighted_tokens_per_request)
from benchmarks.ai_workload.realistic_neev_validation_profiles import (
    NeevScenario, select_profiles)
from benchmarks.ai_workload.realistic_prompt_factory import build_prompt

# Status / label vocabulary (kept explicit so reports never mix classifications).
STATUS_MEASURED = "MEASURED"
STATUS_NOT_MEASURED = "NOT_MEASURED"   # dry-run: LLM call skipped
STATUS_TIMEOUT = "TIMEOUT"             # full-run: local runtime timed out
STATUS_ERROR = "ERROR"                 # full-run: other provider/runtime error

TARGET_PLATFORM = "Gemini 2.5 Pro (production projection target)"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Per-scenario execution.
# --------------------------------------------------------------------------- #
def _run_scenario(scenario: NeevScenario, *, dry_run: bool, seed: int,
                  chars_per_token: float, provider: Any | None,
                  engine_runtime: str, model_name: str) -> dict[str, Any]:
    """Build the realistic prompt and (unless dry-run) measure tokens via the provider.

    Returns a flat record carrying MEASURED prompt-size metrics, ESTIMATED input tokens,
    and — when the LLM ran successfully — MEASURED input/output tokens + latency."""
    spec = scenario.to_prompt_spec()
    built = build_prompt(spec, seed=seed, chars_per_token=chars_per_token)

    record: dict[str, Any] = {
        "timestamp": _utc_now(),
        "scenario_key": scenario.key,
        "scenario_name": scenario.name,
        "group": scenario.group,
        "engine_runtime": engine_runtime,            # e.g. ollama (ENGINEERING benchmark)
        "model": model_name,
        "target_platform": TARGET_PLATFORM,          # projection target, never measured here
        # scenario scale (METADATA)
        "repository_apps": scenario.repository_apps,
        "apps_selected": scenario.apps_selected,
        "frameworks": scenario.frameworks,
        "controls_per_framework": scenario.controls_per_framework,
        "evidence_files_per_framework": scenario.evidence_files_per_framework,
        "retrieved_evidence_blocks": built["retrieved_evidence_blocks"],
        "output_style": scenario.output_style,
        "output_mode": spec.output_mode,
        "system_prompt_source": built["system_prompt_source"],
        # MEASURED prompt size (exact; no model required)
        "system_prompt_chars": built["system_prompt_chars"],
        "user_prompt_chars": built["user_prompt_chars"],
        "prompt_chars": built["prompt_chars"],
        "prompt_bytes": built["prompt_bytes"],
        "prompt_chars_label": "MEASURED",
        # ESTIMATED input tokens (char-based; planning estimate)
        "estimated_input_tokens": built["estimated_input_tokens"],
        "chars_per_token_basis": built["chars_per_token_basis"],
        # filled by the LLM path
        "measured_input_tokens": None,
        "measured_output_tokens": None,
        "measured_total_tokens": None,
        "llm_latency_ms": None,
        "input_token_label": "ESTIMATED",
        "output_token_label": STATUS_NOT_MEASURED,
        "status": STATUS_NOT_MEASURED,
        "error_message": "",
        # keep the composition for the prompt-composition report
        "_composition": built["composition"],
        "_source_pages_per_file": built["source_pages_per_file"],
        "_source_words_per_page": built["source_words_per_page"],
    }

    if dry_run or provider is None:
        record["status"] = STATUS_NOT_MEASURED
        record["error_message"] = "dry-run: LLM call skipped" if dry_run else "no provider"
        return record

    # Full run: MEASURE via the existing provider instrumentation.
    from ecs_platform.llm_engine.provider import LLMError  # lazy import

    t0 = time.perf_counter()
    try:
        text, meta = provider.generate_with_metadata(
            built["user_prompt"], system=built["system_prompt"])
        wall_ms = int((time.perf_counter() - t0) * 1000)
        in_tok = int(meta.get("input_tokens", 0) or 0)
        out_tok = int(meta.get("output_tokens", 0) or 0)
        record.update({
            "measured_input_tokens": in_tok,
            "measured_output_tokens": out_tok,
            "measured_total_tokens": int(meta.get("total_tokens", in_tok + out_tok) or 0),
            "llm_latency_ms": wall_ms,
            "input_token_label": "MEASURED",
            "output_token_label": "MEASURED",
            "status": STATUS_MEASURED,
            "_response_chars": len(text or ""),
        })
    except LLMError as exc:
        wall_ms = int((time.perf_counter() - t0) * 1000)
        msg = str(exc)
        is_timeout = "timed out" in msg.lower() or "timeout" in msg.lower()
        # Prompt size stays MEASURED; input tokens fall back to ESTIMATED; output is
        # NOT_MEASURED. A timeout is a LOCAL runtime limitation, not an ECS failure.
        record.update({
            "llm_latency_ms": wall_ms,
            "input_token_label": "ESTIMATED",
            "output_token_label": STATUS_NOT_MEASURED,
            "status": STATUS_TIMEOUT if is_timeout else STATUS_ERROR,
            "error_message": (f"{msg} | local runtime limitation (not an ECS architecture "
                              f"failure); prompt was built and tokenized (ESTIMATED), output "
                              f"NOT_MEASURED" if is_timeout else msg),
        })
    except Exception as exc:  # noqa: BLE001 - never abort the suite on one scenario
        wall_ms = int((time.perf_counter() - t0) * 1000)
        record.update({
            "llm_latency_ms": wall_ms,
            "status": STATUS_ERROR,
            "error_message": f"{type(exc).__name__}: {exc}",
        })
    return record


# --------------------------------------------------------------------------- #
# Aggregation.
# --------------------------------------------------------------------------- #
def _aggregate(records: list[dict[str, Any]], assumptions: NeevAssumptions,
               *, allow_timeout_evidence: bool) -> dict[str, Any]:
    measured = [r for r in records if r["status"] == STATUS_MEASURED]
    timed_out = [r for r in records if r["status"] == STATUS_TIMEOUT]
    errored = [r for r in records if r["status"] == STATUS_ERROR]

    in_stats = bench_statistics.summarize([r["measured_input_tokens"] for r in measured]).to_dict()
    out_stats = bench_statistics.summarize([r["measured_output_tokens"] for r in measured]).to_dict()

    agg: dict[str, Any] = {
        "total_scenarios": len(records),
        "measured_scenarios": len(measured),
        "timed_out_scenarios": len(timed_out),
        "errored_scenarios": len(errored),
        "measured_input_token_stats": in_stats,
        "measured_output_token_stats": out_stats,
        "peak": None,
        "recommendation": None,
        "target_comparison": None,
    }

    if measured:
        # Largest successful REALISTIC result = max MODELED weighted tokens/request.
        def _w(r: dict[str, Any]) -> int:
            return weighted_tokens_per_request(
                r["measured_input_tokens"], r["measured_output_tokens"],
                assumptions.output_weighting_factor)

        peak = max(measured, key=_w)
        peak_in = int(peak["measured_input_tokens"])
        peak_out = int(peak["measured_output_tokens"])
        agg["peak"] = {
            "scenario_key": peak["scenario_key"],
            "scenario_name": peak["scenario_name"],
            "measured_input_tokens": peak_in,        # MEASURED
            "measured_output_tokens": peak_out,      # MEASURED
            "weighted_tokens_per_request": _w(peak),  # MODELED
        }
        agg["recommendation"] = recommend_budget(peak_in, peak_out, assumptions)
        agg["target_comparison"] = compare_to_target(peak_in, peak_out, assumptions)

    # Optional ESTIMATED-only context for timed-out scenarios (never MEASURED, never
    # used for the recommended peak). Provides input-token shape where measurement
    # was impossible, clearly labelled ESTIMATED / output NOT_MEASURED.
    if allow_timeout_evidence and timed_out:
        agg["timeout_estimated_evidence"] = [
            {
                "scenario_key": r["scenario_key"],
                "prompt_chars": r["prompt_chars"],           # MEASURED
                "estimated_input_tokens": r["estimated_input_tokens"],  # ESTIMATED
                "output_token_label": STATUS_NOT_MEASURED,
                "note": "timed out on local runtime; not counted as measured",
            }
            for r in timed_out
        ]
    return agg


# --------------------------------------------------------------------------- #
# Report writers.
# --------------------------------------------------------------------------- #
_RESULT_COLUMNS = [
    "timestamp", "scenario_key", "scenario_name", "group", "status",
    "engine_runtime", "model", "target_platform",
    "repository_apps", "apps_selected", "frameworks", "controls_per_framework",
    "evidence_files_per_framework", "retrieved_evidence_blocks", "output_mode",
    "system_prompt_source", "prompt_chars", "prompt_bytes", "prompt_chars_label",
    "estimated_input_tokens", "input_token_label",
    "measured_input_tokens", "measured_output_tokens", "measured_total_tokens",
    "output_token_label", "llm_latency_ms", "error_message",
]


def _write_results_csv(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=_RESULT_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in records:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in _RESULT_COLUMNS})


def _write_results_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _write_composition_csv(path: Path, records: list[dict[str, Any]]) -> None:
    cols = ["scenario_key", "scenario_name", "section", "items", "chars",
            "estimated_tokens", "source_pages_per_file", "source_words_per_page",
            "label"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in records:
            for sec in r.get("_composition", []):
                w.writerow({
                    "scenario_key": r["scenario_key"],
                    "scenario_name": r["scenario_name"],
                    "section": sec["section"],
                    "items": sec["items"],
                    "chars": sec["chars"],                 # MEASURED chars
                    "estimated_tokens": sec["estimated_tokens"],  # ESTIMATED
                    "source_pages_per_file": r.get("_source_pages_per_file", ""),
                    "source_words_per_page": r.get("_source_words_per_page", ""),
                    "label": "MEASURED chars / ESTIMATED tokens",
                })


def _write_projection_csv(path: Path, records: list[dict[str, Any]],
                          assumptions: NeevAssumptions) -> None:
    cols = ["scenario_key", "scenario_name", "status", "token_label",
            "input_tokens", "output_tokens", "weighted_tokens_per_request",
            "peak_tpm_1_rpm", "peak_tpm_2_rpm", "peak_tpm_3_rpm", "peak_tpm_5_rpm",
            "daily_tokens", "monthly_tokens", "annual_tokens",
            "monthly_billion_tokens", "annual_billion_tokens"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in records:
            if r["status"] == STATUS_MEASURED:
                proj = project_request(r["measured_input_tokens"],
                                       r["measured_output_tokens"], assumptions)
                w.writerow({"scenario_key": r["scenario_key"],
                            "scenario_name": r["scenario_name"], "status": r["status"],
                            "token_label": "MEASURED->MODELED/PROJECTED", **proj})
            else:
                # No measured output -> weighted TPM not derivable. Show ESTIMATED input
                # only; never fabricate output/weighted values.
                w.writerow({
                    "scenario_key": r["scenario_key"],
                    "scenario_name": r["scenario_name"], "status": r["status"],
                    "token_label": "ESTIMATED input / output NOT_MEASURED",
                    "input_tokens": r["estimated_input_tokens"],
                    "output_tokens": "", "weighted_tokens_per_request": "",
                    "peak_tpm_1_rpm": "", "peak_tpm_2_rpm": "", "peak_tpm_3_rpm": "",
                    "peak_tpm_5_rpm": "", "daily_tokens": "", "monthly_tokens": "",
                    "annual_tokens": "", "monthly_billion_tokens": "",
                    "annual_billion_tokens": "",
                })


def _fmt(n: Any) -> str:
    if n is None or n == "":
        return "n/a"
    if isinstance(n, float):
        return f"{n:,.4f}" if abs(n) < 1000 else f"{n:,.2f}"
    if isinstance(n, int):
        return f"{n:,}"
    return str(n)


def _write_projection_md(path: Path, agg: dict[str, Any], assumptions: NeevAssumptions,
                         dry_run: bool) -> None:
    lines = ["# ECS Neev Capacity Projection", "",
             f"_Generated: {_utc_now()}_", "",
             "> Local Ollama result = ENGINEERING BENCHMARK. Gemini 2.5 Pro sizing = "
             "PROJECTION using the MEASURED ECS token shape. This report does NOT claim "
             "Gemini 2.5 Pro was measured.", ""]
    a = assumptions
    lines += [
        "## Assumptions (configurable)", "",
        f"- Output weighting factor: **{a.output_weighting_factor}x**",
        f"- Peak RPM options: {', '.join(str(x) for x in a.peak_rpm_options)} (target {a.target_peak_rpm})",
        f"- Requests/day: {a.requests_per_day}; working days/month: {a.working_days_per_month}; "
        f"working months/year: {a.working_months_per_year}",
        f"- Recommended headroom: {int(a.headroom_factor * 100)}%",
        f"- TARGET planning assumption: {a.target_input_tokens:,} input / {a.target_output_tokens:,} output",
        "",
    ]
    if dry_run or not agg.get("peak"):
        lines += [
            "## Status", "",
            "Dry run (or no measured scenarios): output tokens are **NOT_MEASURED**, so "
            "weighted TPM and billion-token projections cannot be derived. Run the full "
            "benchmark on the 16 GB stack to measure output tokens.", "",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
        return

    peak = agg["peak"]
    rec = agg["recommendation"]
    cmp = agg["target_comparison"]
    proj = project_request(peak["measured_input_tokens"], peak["measured_output_tokens"], a)
    lines += [
        "## A. Measured realistic peak (MEASURED)", "",
        f"- Peak scenario: **{peak['scenario_name']}** (`{peak['scenario_key']}`)",
        f"- Measured input tokens: **{_fmt(peak['measured_input_tokens'])}**",
        f"- Measured output tokens: **{_fmt(peak['measured_output_tokens'])}**",
        f"- Weighted tokens/request (MODELED, input + {a.output_weighting_factor}x output): "
        f"**{_fmt(peak['weighted_tokens_per_request'])}**", "",
        "## B. Recommended Neev value (MODELED = measured peak + headroom)", "",
        f"- Recommended input tokens: **{_fmt(rec['recommended_input_tokens'])}** "
        f"(+{int(a.headroom_factor * 100)}%)",
        f"- Recommended output tokens: **{_fmt(rec['recommended_output_tokens'])}** "
        f"(+{int(a.headroom_factor * 100)}%)",
        f"- Recommended weighted tokens/request: **{_fmt(rec['recommended_weighted_tokens_per_request'])}**",
        f"- Recommended peak TPM @ {a.target_peak_rpm} RPM: **{_fmt(rec['recommended_peak_tpm_3_rpm'])}**", "",
        "## C. Comparison to current planning TARGET (125K / 50K)", "",
        f"- Input variance vs target: **{_fmt(cmp['input_variance_percent'])}%**",
        f"- Output variance vs target: **{_fmt(cmp['output_variance_percent'])}%**",
        f"- Weighted-token variance vs target: **{_fmt(cmp['weighted_token_variance_percent'])}%**",
        f"- Peak-TPM variance vs target (@ {a.target_peak_rpm} RPM): **{_fmt(cmp['peak_tpm_variance_percent'])}%**",
        f"- Recommended vs target input: {_fmt(rec['recommended_vs_target_input_percent'])}%; "
        f"output: {_fmt(rec['recommended_vs_target_output_percent'])}%", "",
        f"**Conclusion:** {cmp['conclusion']}", "",
        "## Peak-request PROJECTION (Neev calculator, MEASURED -> PROJECTED)", "",
        f"- Peak TPM @ 1 / 2 / 3 / 5 RPM: {_fmt(proj['peak_tpm_1_rpm'])} / "
        f"{_fmt(proj['peak_tpm_2_rpm'])} / {_fmt(proj['peak_tpm_3_rpm'])} / {_fmt(proj['peak_tpm_5_rpm'])}",
        f"- Daily tokens: {_fmt(proj['daily_tokens'])}",
        f"- Monthly tokens: {_fmt(proj['monthly_tokens'])} "
        f"(**{_fmt(proj['monthly_billion_tokens'])}B**)",
        f"- Annual tokens: {_fmt(proj['annual_tokens'])} "
        f"(**{_fmt(proj['annual_billion_tokens'])}B**)", "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_summary_md(path: Path, records: list[dict[str, Any]], agg: dict[str, Any],
                      assumptions: NeevAssumptions, dry_run: bool,
                      engine_runtime: str, model_name: str) -> None:
    a = assumptions
    lines = ["# ECS Neev Validation Benchmark — Summary", "",
             f"_Generated: {_utc_now()}_", ""]
    lines += [
        "## Purpose", "",
        "This benchmark does not attempt to prove the current assumption. It evaluates "
        "whether the current Neev planning assumption is realistic when compared to "
        "MEASURED ECS workload prompts (the final prompt sent to the LLM after retrieval "
        "and prompt construction).", "",
        "> Runtime: **" + engine_runtime + "** (ENGINEERING benchmark). Target platform: **" +
        TARGET_PLATFORM + "**. A local Ollama result is an engineering benchmark; "
        "Gemini 2.5 Pro sizing is a PROJECTION using the measured ECS token shape — never "
        "a Gemini measurement.", "",
        "## Current Neev assumptions (TARGET)", "",
        f"- Input tokens/request: **{a.target_input_tokens:,}**",
        f"- Output tokens/request: **{a.target_output_tokens:,}**",
        f"- Output weighting: **{a.output_weighting_factor}x**",
        f"- Peak RPM: **{a.target_peak_rpm}**", "",
    ]

    # Measured benchmark results table.
    lines += ["## Measured benchmark results", ""]
    if dry_run:
        lines += ["Dry run: LLM calls were skipped. Input tokens are **ESTIMATED** "
                  "(char-based); output tokens are **NOT_MEASURED**.", ""]
    lines += ["| Scenario | Status | Prompt chars (MEASURED) | Input tokens | Output tokens | Latency ms |",
              "| --- | --- | ---: | ---: | ---: | ---: |"]
    for r in records:
        in_tok = (f"{r['measured_input_tokens']:,} (MEASURED)" if r["status"] == STATUS_MEASURED
                  else f"{r['estimated_input_tokens']:,} (ESTIMATED)")
        out_tok = (f"{r['measured_output_tokens']:,} (MEASURED)" if r["status"] == STATUS_MEASURED
                   else "NOT_MEASURED")
        lines.append(f"| {r['scenario_name']} | {r['status']} | {r['prompt_chars']:,} | "
                     f"{in_tok} | {out_tok} | {_fmt(r['llm_latency_ms'])} |")
    lines.append("")

    # Prompt composition (largest scenario).
    lines += ["## Prompt composition", "",
              "Each prompt is composed of application metadata, framework/control catalog, "
              "RETRIEVED evidence summaries, observation history, VAPT findings, baseline "
              "status, risk exceptions, audit comments, remediation status, and an executive "
              "instruction. Only retrieved context enters the prompt — repository size scales "
              "retrieval metadata, not an evidence dump. See "
              "`prompt_composition_report.csv` for the per-section breakdown.", ""]

    if agg.get("peak"):
        peak = agg["peak"]
        rec = agg["recommendation"]
        cmp = agg["target_comparison"]
        proj = project_request(peak["measured_input_tokens"],
                               peak["measured_output_tokens"], a)
        lines += [
            "## Largest realistic successful workload (MEASURED)", "",
            f"- **{peak['scenario_name']}** (`{peak['scenario_key']}`)",
            f"- Measured input tokens: **{peak['measured_input_tokens']:,}**",
            f"- Measured output tokens: **{peak['measured_output_tokens']:,}**",
            f"- Weighted tokens/request (MODELED): **{peak['weighted_tokens_per_request']:,}**", "",
            "## Recommended budgeting values", "",
            f"- **Recommended input tokens (MODELED):** {rec['recommended_input_tokens']:,} "
            f"(measured peak + {int(a.headroom_factor * 100)}% headroom)",
            f"- **Recommended output tokens (MODELED):** {rec['recommended_output_tokens']:,} "
            f"(measured peak + {int(a.headroom_factor * 100)}% headroom)",
            f"- **Weighted TPM @ 3 RPM (PROJECTED):** {proj['peak_tpm_3_rpm']:,}",
            f"- **Monthly projection:** {proj['monthly_billion_tokens']:.4f}B tokens",
            f"- **Annual projection:** {proj['annual_billion_tokens']:.4f}B tokens", "",
            "## Variance from current 125K / 50K assumption", "",
            f"- input_variance_percent: **{_fmt(cmp['input_variance_percent'])}%**",
            f"- output_variance_percent: **{_fmt(cmp['output_variance_percent'])}%**",
            f"- weighted_token_variance_percent: **{_fmt(cmp['weighted_token_variance_percent'])}%**",
            f"- peak_tpm_variance_percent: **{_fmt(cmp['peak_tpm_variance_percent'])}%**", "",
            "## Conclusion for Finance / EA / CIO", "",
            cmp["conclusion"] + ".", "",
            "Interpretation: a strongly negative variance means the current planning "
            "assumption is well above measured ECS workload tokens (over-tokenized / "
            "conservative). A positive variance beyond the realistic band means measured "
            "ECS tokens exceed the assumption (under-estimated). Use the **recommended** "
            "values above for Gemini 2.5 Pro budgeting; they include headroom and are "
            "projected from the measured ECS token shape, not from the original assumption.",
            "",
        ]
    else:
        lines += [
            "## Largest realistic successful workload", "",
            "No scenario produced MEASURED output tokens (dry run, or all full-run "
            "scenarios timed out / errored). Run the full benchmark on the 16 GB stack to "
            "obtain measured output tokens before drawing a budgeting conclusion.", "",
            "## Conclusion for Finance / EA / CIO", "",
            "Indeterminate without measured output tokens. Prompt sizes (input shape) are "
            "MEASURED in chars and ESTIMATED in tokens; see the prompt-composition report.",
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Orchestration.
# --------------------------------------------------------------------------- #
def _resolve_provider(max_output_tokens: int, timeout_seconds: int) -> tuple[Any, str, str]:
    """Lazily import + configure the existing ECS provider for the full run. Supplies
    the benchmark output cap + timeout via the EXISTING benchmark config hook (does not
    change production defaults). Returns (provider, engine_runtime, model_name)."""
    from ecs_platform.llm_engine.provider import (  # lazy: keeps dry-run dependency-free
        get_provider, set_benchmark_generation_config)

    set_benchmark_generation_config(num_predict=max_output_tokens,
                                    timeout_seconds=timeout_seconds)
    provider = get_provider()
    engine_runtime = type(provider).__name__.replace("Provider", "").lower()
    model_name = getattr(provider, "model", "") or ""
    return provider, engine_runtime, model_name


def run(args: argparse.Namespace) -> int:
    scenarios = select_profiles(
        [s for s in (args.profiles or "all").split(",")] if args.profiles else None)
    assumptions = NeevAssumptions(
        output_weighting_factor=args.output_weighting,
        target_peak_rpm=args.peak_rpm,
        requests_per_day=args.requests_per_day,
        working_days_per_month=args.working_days,
        working_months_per_year=args.working_months,
        headroom_factor=args.headroom,
        target_input_tokens=args.target_input,
        target_output_tokens=args.target_output,
    )
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    provider: Any | None = None
    engine_runtime, model_name = "dry-run", ""
    if not args.dry_run:
        try:
            provider, engine_runtime, model_name = _resolve_provider(
                args.max_output_tokens, args.timeout_seconds)
        except Exception as exc:  # noqa: BLE001 - clear message, no traceback dump
            print(f"ERROR: could not initialize the LLM provider for a full run: {exc}\n"
                  f"Hint: use --dry-run on an 8 GB workstation, or start the 16 GB stack "
                  f"(Docker / Ollama / Postgres / PGVector / MinIO) for a full run.",
                  file=sys.stderr)
            return 2

    mode = "DRY RUN" if args.dry_run else f"FULL RUN ({engine_runtime})"
    print(f"[neev-validation] {mode}: {len(scenarios)} scenario(s); out={out_dir}")
    if not args.dry_run:
        print(f"[neev-validation] engine_runtime={engine_runtime} model={model_name} "
              f"max_output_tokens={args.max_output_tokens} timeout_seconds={args.timeout_seconds} "
              f"| ENGINEERING benchmark; Gemini 2.5 Pro = projection, not measured")

    records: list[dict[str, Any]] = []
    for sc in scenarios:
        rec = _run_scenario(sc, dry_run=args.dry_run, seed=args.seed,
                            chars_per_token=args.chars_per_token, provider=provider,
                            engine_runtime=engine_runtime, model_name=model_name)
        records.append(rec)
        print(f"  - {sc.key:24s} status={rec['status']:<12s} prompt_chars={rec['prompt_chars']:>8,} "
              f"est_in={rec['estimated_input_tokens']:>7,} "
              f"meas_in={_fmt(rec['measured_input_tokens'])} meas_out={_fmt(rec['measured_output_tokens'])}")

    agg = _aggregate(records, assumptions, allow_timeout_evidence=args.allow_timeout_evidence)

    # Write all six artifacts.
    _write_results_csv(out_dir / "neev_validation_results.csv", records)
    _write_composition_csv(out_dir / "prompt_composition_report.csv", records)
    _write_projection_csv(out_dir / "neev_capacity_projection.csv", records, assumptions)
    _write_projection_md(out_dir / "neev_capacity_projection.md", agg, assumptions, args.dry_run)
    _write_summary_md(out_dir / "neev_validation_summary.md", records, agg, assumptions,
                      args.dry_run, engine_runtime, model_name)
    # Strip private (_-prefixed) fields from the JSON record dump.
    public_records = [{k: v for k, v in r.items() if not k.startswith("_")} for r in records]
    _write_results_json(out_dir / "neev_validation_results.json", {
        "generated_at": _utc_now(),
        "mode": "dry_run" if args.dry_run else "full_run",
        "engine_runtime": engine_runtime,
        "model": model_name,
        "target_platform": TARGET_PLATFORM,
        "assumptions": assumptions.to_dict(),
        "label_legend": {
            "MEASURED": "actual benchmark token instrumentation result",
            "MODELED": "derived from measured benchmark data",
            "PROJECTED": "future usage from measured/modeled values",
            "TARGET": "existing planning assumption (125K/50K/9x/3RPM)",
            "ESTIMATED": "used only where measurement is unavailable",
        },
        "results": public_records,
        "aggregate": agg,
    })

    print(f"[neev-validation] wrote 6 artifacts to {out_dir}/")
    if agg.get("peak"):
        cmp = agg["target_comparison"]
        print(f"[neev-validation] conclusion: {cmp['conclusion']}")
    elif not args.dry_run:
        print("[neev-validation] no measured output tokens (timeouts/errors); "
              "see summary for guidance.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="ECS Neev validation benchmark — realistic ECS token sizing for "
                    "Gemini 2.5 Pro budgeting (reuses existing ECS provider instrumentation).")
    p.add_argument("--dry-run", action="store_true",
                   help="Build prompts + ESTIMATE input tokens; skip the LLM call "
                        "(8 GB workstation friendly).")
    p.add_argument("--profiles", type=str, default="all",
                   help="Comma-separated scenario keys / group aliases / 'all'. Groups: "
                        "small, full, multi_app, enterprise, large_repository.")
    p.add_argument("--max-output-tokens", type=int, default=1024,
                   help="Output-token cap supplied to the provider for the full run "
                        "(benchmark config; does not change production defaults).")
    p.add_argument("--timeout-seconds", type=int, default=300,
                   help="HTTP/model timeout (seconds) supplied to the provider for the full run.")
    p.add_argument("--allow-timeout-evidence", action="store_true",
                   help="Include ESTIMATED input-token context for timed-out scenarios "
                        "(never counted as MEASURED; output stays NOT_MEASURED).")
    p.add_argument("--output-dir", type=str, default="benchmark_outputs",
                   help="Directory for the report artifacts (default: benchmark_outputs).")
    p.add_argument("--seed", type=int, default=1234, help="Deterministic prompt seed.")
    p.add_argument("--chars-per-token", type=float, default=4.0,
                   help="Chars/token basis for ESTIMATED input tokens (planning estimate).")
    # Neev calculator assumptions (configurable).
    p.add_argument("--output-weighting", type=int, default=9)
    p.add_argument("--peak-rpm", type=int, default=3)
    p.add_argument("--requests-per-day", type=int, default=400)
    p.add_argument("--working-days", type=int, default=22)
    p.add_argument("--working-months", type=int, default=12)
    p.add_argument("--headroom", type=float, default=0.25)
    p.add_argument("--target-input", type=int, default=125000)
    p.add_argument("--target-output", type=int, default=50000)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
