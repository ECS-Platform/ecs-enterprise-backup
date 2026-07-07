"""RAM-aware benchmark runner + evidence export for audit LLM prompts.

Runs prompts (single / by category / all) under a RAM profile in dry-run or
actual-LLM mode, capturing per-prompt token estimate, latency, success/failure,
fallback usage, and memory warnings. Exports Markdown + JSON evidence under
``reports/audit_llm_benchmarks/``.

Reuses the execution service (which reuses the existing provider). Dry-run mode
requires no model/network and is safe on any machine (including 8 GB).
"""

from __future__ import annotations

import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from modules.audit_intelligence.llm import execution_service, prompt_library

_REPO_ROOT = Path(__file__).resolve().parents[3]
_REPORT_DIR = _REPO_ROOT / "reports" / "audit_llm_benchmarks"

#: Deterministic sample inputs so a benchmark run is reproducible offline.
_SAMPLE_INPUTS: dict[str, str] = {
    "observation_count": "How many observations are open in Net Banking?",
    "high_risk_observation_summary": "How many high-risk observations are open across all frameworks, and summarize the business impact?",
    "framework_gap_analysis": "Which framework has the highest evidence gap?",
    "csite_closure_probability": "What are the chances my C-SITE observations will not be raised on Net Banking this year?",
    "executive_compliance_summary": "Generate an executive summary of current audit readiness.",
}
_DEFAULT_SAMPLE = "Summarize the current audit posture for Net Banking."


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _machine_profile(ram_profile: str) -> dict[str, Any]:
    prof = prompt_library.get_profile(ram_profile) or {}
    return {
        "ram_profile": ram_profile,
        "ram_profile_label": prof.get("label", ram_profile),
        "declared_ram_gb": prof.get("ram_gb"),
        "host_platform": platform.platform(),
        "host_python": platform.python_version(),
    }


def run_benchmark(
    *,
    prompt_ids: list[str] | None = None,
    category: str = "",
    all_prompts: bool = False,
    ram_profile: str = "local_16gb_safe",
    token_profile: str = "",
    dry_run: bool = True,
    quality_notes: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run a benchmark and return a structured report (does not write files).

    Selection precedence: explicit ``prompt_ids`` > ``category`` > ``all_prompts``.
    ``dry_run=True`` forces token-estimate-only (no LLM); otherwise the RAM
    profile's execution_mode applies (a dry-run profile is always no-LLM).
    """
    quality_notes = quality_notes or {}

    # Resolve the prompt selection.
    if prompt_ids:
        selected = [prompt_library.get_prompt(p) for p in prompt_ids]
        selected = [p for p in selected if p]
    elif category:
        selected = prompt_library.list_prompts(category=category)
    elif all_prompts:
        selected = prompt_library.list_prompts()
    else:
        selected = prompt_library.list_prompts()[:5]  # default: a small representative set

    profile = prompt_library.get_profile(ram_profile) or {}
    force_dry = dry_run or str(profile.get("execution_mode", "llm")) == "dry_run"

    results: list[dict[str, Any]] = []
    for prompt in selected:
        pid = prompt.get("prompt_id", "")
        tp = token_profile or prompt.get("token_profile", "medium_8k")
        sample = _SAMPLE_INPUTS.get(pid, _DEFAULT_SAMPLE)

        # In forced dry-run, run under the dry-run RAM profile so no LLM is called.
        effective_ram = "worst_case_enterprise_dry_run" if force_dry else ram_profile
        try:
            r = execution_service.execute(
                prompt_id=pid, user_query=sample, ram_profile=effective_ram,
                token_profile=tp, use_rag=not force_dry,
            )
            te = r.get("token_estimate", {})
            results.append({
                "prompt_id": pid,
                "category": prompt.get("category", ""),
                "query_type": prompt.get("query_type", ""),
                "token_profile": tp,
                "estimated_input_tokens": te.get("input_tokens", 0),
                "estimated_output_tokens": te.get("output_tokens", 0),
                "total_estimated_tokens": te.get("total_tokens", 0),
                "context_budget": te.get("context_budget", 0),
                "fits_context": te.get("fits_context", True),
                "latency_ms": r.get("latency_ms", 0.0),
                "success": not r.get("fallback_used", False) or force_dry,
                "fallback_used": r.get("fallback_used", False),
                "error_reason": r.get("provider_status", {}).get("error", ""),
                "provider_status": r.get("provider_status", {}),
                "deterministic_result_count": r.get("deterministic_result", {}).get("count", 0),
                "memory_warning": "; ".join(w for w in r.get("warnings", []) if "memory" in w.lower() or "swap" in w.lower()),
                "warnings": r.get("warnings", []),
                "output_quality_notes": quality_notes.get(pid, ""),
                "ram_profile_used": effective_ram,
            })
        except Exception as exc:  # noqa: BLE001 - a bad prompt must not abort the run
            results.append({
                "prompt_id": pid, "category": prompt.get("category", ""),
                "success": False, "fallback_used": True,
                "error_reason": type(exc).__name__, "latency_ms": 0.0,
            })

    summary = {
        "prompts_run": len(results),
        "succeeded": sum(1 for r in results if r.get("success")),
        "fallback": sum(1 for r in results if r.get("fallback_used")),
        "total_estimated_tokens": sum(int(r.get("total_estimated_tokens", 0) or 0) for r in results),
        "max_estimated_tokens": max((int(r.get("total_estimated_tokens", 0) or 0) for r in results), default=0),
    }

    return {
        "timestamp": _now_iso(),
        "machine_profile": _machine_profile(ram_profile),
        "ram_profile": ram_profile,
        "requested_dry_run": dry_run,
        "effective_mode": "dry_run" if force_dry else "llm",
        "provider": (results[0].get("provider_status", {}) if results else {}),
        "results": results,
        "summary": summary,
        "reproducibility": {
            "deterministic_samples": True,
            "note": "Samples are fixed per prompt_id; token estimates are deterministic (chars/4).",
        },
    }


# --------------------------------------------------------------------------- #
# Evidence export
# --------------------------------------------------------------------------- #
def _report_stem(ram_profile: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"audit_llm_benchmark_{ram_profile}_{ts}"


def export_report(report: dict[str, Any], *, formats: tuple[str, ...] = ("md", "json"),
                  out_dir: Path | None = None) -> dict[str, str]:
    """Write the benchmark report as Markdown and/or JSON. Returns written paths."""
    out_dir = out_dir or _REPORT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = _report_stem(report.get("ram_profile", "profile"))
    written: dict[str, str] = {}

    if "json" in formats:
        p = out_dir / f"{stem}.json"
        p.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        written["json"] = str(p)

    if "md" in formats:
        p = out_dir / f"{stem}.md"
        p.write_text(render_markdown(report), encoding="utf-8")
        written["md"] = str(p)

    return written


def render_markdown(report: dict[str, Any]) -> str:
    mp = report.get("machine_profile", {})
    prov = report.get("provider", {}) or {}
    s = report.get("summary", {})
    lines = [
        "# ECS Audit LLM Benchmark Report",
        "",
        f"- **Timestamp:** {report.get('timestamp', '')}",
        f"- **Machine profile:** {mp.get('ram_profile_label', '')} "
        f"(declared {mp.get('declared_ram_gb', '?')} GB)",
        f"- **Host:** {mp.get('host_platform', '')} · Python {mp.get('host_python', '')}",
        f"- **RAM profile:** {report.get('ram_profile', '')} · "
        f"**Mode:** {report.get('effective_mode', '')}",
        f"- **Provider:** {prov.get('provider', 'n/a')} · model {prov.get('model', 'n/a')} · "
        f"configured={prov.get('configured', False)}",
        f"- **Summary:** {s.get('prompts_run', 0)} prompt(s), {s.get('succeeded', 0)} ok, "
        f"{s.get('fallback', 0)} fallback; max ~{s.get('max_estimated_tokens', 0)} tokens.",
        "",
        "| prompt_id | category | query_type | token_profile | in | out | total | fits | latency ms | success | fallback | det_count | memory_warning |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in report.get("results", []):
        lines.append(
            f"| {r.get('prompt_id','')} | {r.get('category','')} | {r.get('query_type','')} "
            f"| {r.get('token_profile','')} | {r.get('estimated_input_tokens',0)} "
            f"| {r.get('estimated_output_tokens',0)} | {r.get('total_estimated_tokens',0)} "
            f"| {r.get('fits_context',True)} | {r.get('latency_ms',0)} | {r.get('success',False)} "
            f"| {r.get('fallback_used',False)} | {r.get('deterministic_result_count',0)} "
            f"| {(r.get('memory_warning','') or '')[:40]} |"
        )
    lines += [
        "",
        "## Reproducibility",
        f"- {report.get('reproducibility', {}).get('note', '')}",
        "",
        "## Quality notes",
    ]
    any_notes = False
    for r in report.get("results", []):
        if r.get("output_quality_notes"):
            any_notes = True
            lines.append(f"- **{r['prompt_id']}**: {r['output_quality_notes']}")
    if not any_notes:
        lines.append("- (Add qualitative output notes after reviewing LLM responses.)")
    return "\n".join(lines) + "\n"
