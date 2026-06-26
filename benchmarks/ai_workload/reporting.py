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
from benchmarks.ai_workload.capacity_planning import CapacityAssumptions

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
    "error",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _provider_model(rows: list[dict[str, Any]]) -> tuple[str, str]:
    for r in rows:
        if r.get("provider") or r.get("model"):
            return str(r.get("provider", "")), str(r.get("model", ""))
    return "", ""


def build_report(rows: list[dict[str, Any]], assumptions: CapacityAssumptions) -> dict[str, Any]:
    """Aggregate per-request rows into the enterprise report structure."""
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
        worst = {
            "profile_key": worst.get("profile_key"),
            "workload": worst.get("workload"),
            "top_k": worst.get("top_k"),
            "input_tokens": worst.get("input_tokens"),
            "output_tokens": worst.get("output_tokens"),
            "total_tokens": worst.get("total_tokens"),
            "prompt_size_chars": worst.get("prompt_size_chars"),
            "retrieved_documents": worst.get("retrieved_documents"),
            "end_to_end_latency_ms": worst.get("end_to_end_latency_ms"),
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

    return {
        "meta": {
            "generated_at": _utc_now(),
            "provider": provider,
            "model": model,
            "total_requests": len(rows),
            "successful_requests": len(ok_rows),
            "failed_requests": len(rows) - len(ok_rows),
            "benchmark": "ECS enterprise AI workload",
            "reuses": "ecs_platform.rag.answer + existing instrumentation (no instrumentation changes)",
        },
        "measured": {
            "statistics": statistics,
            "by_category": category_stats,
            "worst_case_max_tokens": worst,
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
    with summary_path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=True)

    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in _CSV_COLUMNS})

    return {
        "report": str(report_path),
        "summary": str(summary_path),
        "csv": str(csv_path),
    }
