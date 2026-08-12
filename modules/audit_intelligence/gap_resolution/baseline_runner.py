"""Baseline runner: exercises each gap scenario through the deterministic
completeness-detection path only — no LLM involved.

Decision rule (mirrors what the existing rule-based engines already do —
`governance_completeness_engine` / `missing_evidence_engine` have no LLM
step, and the connector layer's only safe no-network entry point is
`connector_workbench.dry_run`, which reports readiness, not data):

  * zero connector candidates            -> escalated (no source at all)
  * more than one connector candidate    -> escalated (ambiguous; the
                                             deterministic path has no
                                             tie-breaker/priority logic)
  * exactly one connector candidate      -> walk the scenario's declared
                                             fetch attempts in order, doing
                                             a dry-run readiness check
                                             against the real connector
                                             registry for each; resolved as
                                             soon as an attempt succeeds,
                                             escalated if every attempt in
                                             the scenario fails.

For each scenario this records: task_id, tier, outcome, wall-clock time.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from modules.audit_intelligence.gap_resolution import connector_registry

DEFAULT_RESULTS_JSONL = Path("benchmarks/output/gap_baseline_results.jsonl")
DEFAULT_RESULTS_MD = Path("benchmarks/output/gap_baseline_results.md")


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    """Run one scenario through the deterministic path and return its result."""
    task_id = scenario["id"]
    tier = scenario["tier"]
    candidates: list[str] = scenario.get("connector_candidates", [])
    attempts: list[dict[str, Any]] = scenario.get("fetch_attempts", [])

    start = time.perf_counter()
    reason = ""
    outcome = "escalated"

    if not candidates:
        reason = "no_connector_source"
    elif len(candidates) > 1:
        reason = "ambiguous_source"
    else:
        resolved = False
        for attempt in attempts:
            # Dry-run readiness check only — no network call, no live data.
            connector_registry.dry_run_fetch(attempt["connector"])
            if attempt.get("result") == "success":
                resolved = True
                reason = f"resolved_on_attempt_{attempt['attempt']}"
                break
            reason = attempt.get("reason", "fetch_failed")
        outcome = "resolved" if resolved else "escalated"

    wall_ms = round((time.perf_counter() - start) * 1000, 3)
    expected = scenario.get("expected_outcome_category", "")
    return {
        "task_id": task_id,
        "tier": tier,
        "outcome": outcome,
        "reason": reason,
        "wall_ms": wall_ms,
        "expected_outcome_category": expected,
        "matched_expected": outcome == expected,
        "timestamp": _ts(),
    }


def run_baseline(scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [run_scenario(s) for s in scenarios]


def write_results_jsonl(results: list[dict[str, Any]], path: Path = DEFAULT_RESULTS_JSONL) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps(r, default=str) + "\n")
    return path


def render_markdown_table(results: list[dict[str, Any]]) -> str:
    lines = [
        "| task_id | tier | outcome | time_ms |",
        "|---|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r['task_id']} | {r['tier']} | {r['outcome']} | {r['wall_ms']} |")
    total = len(results)
    matched = sum(1 for r in results if r["matched_expected"])
    resolved = sum(1 for r in results if r["outcome"] == "resolved")
    escalated = total - resolved
    lines.append("")
    lines.append(
        f"**Summary:** {total} scenarios — {resolved} resolved, {escalated} escalated, "
        f"{matched}/{total} matched expected_outcome_category."
    )
    return "\n".join(lines)


def write_results_markdown(results: list[dict[str, Any]], path: Path = DEFAULT_RESULTS_MD) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = render_markdown_table(results)
    path.write_text(f"# Gap Baseline Results\n\n{table}\n", encoding="utf-8")
    return path
