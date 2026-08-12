"""Agentic gap-remediation loop — an LLM (qwen3:8b via the existing Ollama
adapter) drives up to 3 tool-calling iterations per gap scenario, then is
forced to escalate. This is the sequel to the deterministic baseline in
`baseline_runner.py` (untouched); it reuses the same fixture, the same
`connector_registry`, and logs every call through the existing
`LLMCallLogger`.

Tools exposed to the model:
  * check_completeness(evidence_id)         — read-only, what's missing + candidates
  * fetch_from_connector(source, params)     — dry-run only, no network
  * request_human_review(reason)             — terminal, escalates

`OllamaProvider` (ecs_platform.llm_engine.provider) has no native
`tools`/function-calling support today (confirmed: no `tools` key in its
payload, no `tool_calls` parsing) and this module deliberately does not
modify that shared provider — other callers (RAG, ai-ops summaries) depend
on its exact payload shape. Instead the loop uses a ReAct-style prompt: the
system prompt describes the three tools and the model must reply with
exactly one JSON object naming a tool (or `finish`) each turn. This still
runs the real qwen3:8b model over the real Ollama HTTP path
(`generate_with_metadata`), so token counts are Ollama's own
`prompt_eval_count`/`eval_count`, not estimates.

Outcome categories:
  * auto_resolved       — resolved via connector fetch, no failed attempt first
  * resolved_with_retry — resolved via connector fetch after >=1 failed attempt
  * escalated           — the model DID respond: request_human_review,
                           ambiguous/no-connector fetch result, unparseable
                           model output, or the 3-iteration hard cap was hit
                           with no resolution
  * error               — the model never got to respond: an LLMError
                           (connection/DNS/timeout) or other unexpected
                           exception broke the provider call itself. This is
                           an infrastructure failure, not a task outcome, and
                           must never be conflated with "escalated".
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from datetime import datetime, timezone
from typing import Any

from ecs_platform.llm_engine.provider import LLMError
from modules.audit_intelligence.gap_resolution import connector_registry
from modules.audit_intelligence.gap_resolution.llm_call_logger import LLMCallLogger

MAX_ITERATIONS = 3  # hard cap — dev hardware is VRAM-limited, no exceptions

_HISTORY_MAX_CHARS = 1200  # bound on the running transcript appended to each prompt
_TOOL_RESULT_MAX_CHARS = 300  # bound on any single tool result before it's appended

AGENT_SYSTEM_PROMPT = """You are an evidence-gap remediation agent for a bank's \
compliance system. You are given ONE evidence gap to resolve using the tools below. \
You have at most 3 turns total, so act efficiently.

Tools:
1. check_completeness(evidence_id) - read-only: reports which field is missing on \
this evidence record and which connectors could plausibly supply it. Its result for \
THIS task is already given to you below in the first message — you do not need to \
call it again unless you want to re-verify something.
2. fetch_from_connector(source, params) - dry-run only, no live network call: \
attempts to fetch the missing field's value from connector `source`.
3. request_human_review(reason) - ends the task and escalates it to a human, with \
your reason.

Reply with EXACTLY one JSON object and nothing else (no markdown fences, no \
commentary), in one of these forms:
  {"tool": "check_completeness", "args": {"evidence_id": "..."}}
  {"tool": "fetch_from_connector", "args": {"source": "...", "params": {}}}
  {"tool": "request_human_review", "args": {"reason": "..."}}
  {"tool": "finish", "args": {"resolved": true, "summary": "..."}}

Rules — you only get 3 turns total, so do not waste one:
- The check_completeness result is already in your context. Do NOT call \
check_completeness as your first action — go straight to fetch_from_connector (if \
there is exactly one connector candidate) or request_human_review (if there are zero \
or multiple candidates). Calling check_completeness again just burns a turn you don't \
have.
- The moment a fetch_from_connector result has "ok": true, your VERY NEXT action \
must be finish with resolved=true. Do not call fetch_from_connector again after a \
success — that just burns your remaining turns.
- If a fetch fails because of stale/wrong-format data, retry ONCE with different \
params (e.g. a newer format) before giving up.
- If the completeness report shows more than one plausible connector with no declared \
priority, or zero connector candidates, or a fetch reports a conflict, call \
request_human_review immediately — do not keep guessing.
- Every tool result includes a "hint" field telling you the recommended next \
action. Follow it unless you have a clear reason not to."""


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Best-effort extraction of the first top-level JSON object in `text`.

    Local 8B models occasionally wrap JSON in markdown fences or trailing
    prose despite instructions; this scans for a balanced {...} span rather
    than requiring the whole string to be valid JSON.
    """
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    obj = json.loads(candidate)
                except json.JSONDecodeError:
                    return None
                return obj if isinstance(obj, dict) else None
    return None


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def _summarize_tool_result(result: dict[str, Any]) -> str:
    return _truncate(json.dumps(result, default=str), _TOOL_RESULT_MAX_CHARS)


CUDA_CRASH_RETRY_DELAY_SECONDS = 3  # let the crashed llama-server subprocess fully die


def _is_cuda_crash_signature(exc: BaseException) -> bool:
    """Identifies the specific intermittent-crash LLMError signature seen under
    sustained sequential load on this dev machine (RTX 3060 Laptop, 6GB VRAM):
    the llama-server subprocess dies mid-call with a CUDA shared-object init
    failure. This is a known hardware/driver instability, not a stale-process or
    DNS issue (both handled elsewhere) — bounded retry is the appropriate
    response, unlike other LLMError causes which should surface immediately."""
    msg = str(exc)
    return "CUDA error" in msg or "llama-server process has terminated" in msg


def _trim_dry_run(dry: dict[str, Any]) -> dict[str, Any]:
    """Keep only the small, decision-relevant fields from a dry_run response
    (drops masked_config etc.) — this is the "truncate tool output" step."""
    return {
        "ok": dry.get("ok"),
        "configured": dry.get("configured"),
        "would_call": dry.get("would_call"),
    }


# --------------------------------------------------------------------------- #
# Tool implementations
# --------------------------------------------------------------------------- #
def _tool_check_completeness(evidence_id: str, scenario: dict[str, Any]) -> dict[str, Any]:
    evidence = scenario["evidence"]
    field = evidence["missing_field"]
    candidates = connector_registry.candidates_for_field(field)
    if not candidates:
        hint = "No connector covers this field. Call request_human_review now."
    elif len(candidates) > 1:
        hint = (f"{len(candidates)} connectors are plausible with no declared priority. "
                f"Call request_human_review now instead of guessing.")
    else:
        hint = f"Call fetch_from_connector with source='{candidates[0]}' next."
    return {
        "evidence_id": evidence_id or scenario["evidence_id"],
        "control_id": evidence.get("control_id"),
        "application": evidence.get("application"),
        "framework": evidence.get("framework"),
        "missing_field": field,
        "connector_candidates": candidates,
        "candidate_count": len(candidates),
        "hint": hint,
    }


def _tool_fetch_from_connector(
    source: str,
    params: dict[str, Any],
    scenario: dict[str, Any],
    fetch_state: dict[str, int],
) -> dict[str, Any]:
    candidates: list[str] = scenario.get("connector_candidates", [])
    dry = connector_registry.dry_run_fetch(source) if source else {"ok": False}

    if not source or source not in candidates:
        return {
            "ok": False,
            "connector": source,
            "error": "connector_not_applicable_to_field",
            "dry_run": _trim_dry_run(dry),
            "hint": "This connector doesn't cover the field. Call request_human_review now.",
        }

    if len(candidates) > 1:
        # Ambiguous by construction (tier C): no declared priority among
        # candidates, so a dry-run fetch cannot be trusted as authoritative.
        return {
            "ok": False,
            "connector": source,
            "conflict": True,
            "error": "multiple_connectors_plausible_no_authoritative_source",
            "candidates": candidates,
            "dry_run": _trim_dry_run(dry),
            "hint": "Conflicting sources, no authoritative one. Call request_human_review now.",
        }

    # Single-candidate field: ground truth comes from the scenario's scripted
    # fetch_attempts (tier A: one success; tier B: fail then succeed).
    attempts = scenario.get("fetch_attempts", [])
    idx = fetch_state["count"]
    fetch_state["count"] += 1
    if not attempts:
        return {
            "ok": True, "connector": source, "value": "fetched_ok", "dry_run": _trim_dry_run(dry),
            "hint": "Fetch succeeded. Call finish with resolved=true now.",
        }
    attempt = attempts[min(idx, len(attempts) - 1)]
    if attempt.get("result") == "success":
        return {
            "ok": True, "connector": source, "value": "fetched_ok", "dry_run": _trim_dry_run(dry),
            "hint": "Fetch succeeded. Call finish with resolved=true now.",
        }
    attempts_remaining = idx + 1 < len(attempts)
    hint = (
        f"Retry fetch_from_connector on '{source}' with different params (e.g. a newer format)."
        if attempts_remaining
        else "No attempts left. Call request_human_review now."
    )
    return {
        "ok": False,
        "connector": source,
        "error": attempt.get("reason", "fetch_failed"),
        "dry_run": _trim_dry_run(dry),
        "hint": hint,
    }


def _tool_request_human_review(reason: str) -> dict[str, Any]:
    return {"ok": True, "escalated": True, "reason": reason or "unspecified"}


# --------------------------------------------------------------------------- #
# Orchestrator
# --------------------------------------------------------------------------- #
def run_agent_task(
    scenario: dict[str, Any],
    provider: Any,
    logger: LLMCallLogger,
) -> dict[str, Any]:
    """Run one scenario through the agentic loop. Strictly sequential — the
    caller must not invoke this concurrently for multiple scenarios."""
    task_id = scenario["id"]
    tier = scenario["tier"]
    evidence_id = scenario["evidence_id"]
    fetch_state = {"count": 0}
    had_failed_fetch = False
    tool_calls = 0
    tokens_in_total = 0
    tokens_out_total = 0
    cuda_crash_retries = 0
    outcome: str | None = None
    reason = ""
    transcript: list[dict[str, Any]] = []

    # Fold the check_completeness result into the initial context directly —
    # it's a free, deterministic lookup (no LLM call), so the model doesn't
    # need to spend one of its 3 turns asking for it.
    completeness = _tool_check_completeness(evidence_id, scenario)
    history_entries: list[str] = [
        f"Task: resolve the evidence gap for evidence_id={evidence_id}.\n"
        f"[check_completeness result, already available] {_summarize_tool_result(completeness)}"
    ]

    started = time.perf_counter()
    for iteration in range(1, MAX_ITERATIONS + 1):
        history_text = _truncate("\n".join(history_entries), _HISTORY_MAX_CHARS)
        prompt = f"{history_text}\n\nRespond with exactly one JSON object for your next action."

        try:
            content, meta = provider.generate_with_metadata(prompt, system=AGENT_SYSTEM_PROMPT)
        except LLMError as exc:
            if _is_cuda_crash_signature(exc):
                # Known intermittent hardware/driver crash under sustained load —
                # wait for the dead subprocess to fully exit, then retry the
                # identical call exactly once. Any other outcome (success or a
                # second failure) is handled below; this never loops further.
                cuda_crash_retries += 1
                print(f"\n[agent_loop DEBUG] task_id={task_id} iteration={iteration} "
                      f"CUDA crash signature detected, retrying once in "
                      f"{CUDA_CRASH_RETRY_DELAY_SECONDS}s: {exc}", file=sys.stderr)
                time.sleep(CUDA_CRASH_RETRY_DELAY_SECONDS)
                try:
                    content, meta = provider.generate_with_metadata(prompt, system=AGENT_SYSTEM_PROMPT)
                except LLMError as retry_exc:
                    print(f"\n[agent_loop DEBUG] task_id={task_id} iteration={iteration} "
                          f"CUDA crash retry also failed: {type(retry_exc).__name__}: {retry_exc}",
                          file=sys.stderr)
                    traceback.print_exc(file=sys.stderr)
                    logger.record(task_id, tokens_in=0, tokens_out=0)
                    outcome = "error"
                    reason = f"llm_provider_error:{type(retry_exc).__name__}:{retry_exc}"
                    transcript.append({"iteration": iteration, "error": reason, "cuda_crash_retry_failed": True})
                    break
                except Exception as retry_exc:  # noqa: BLE001 - unexpected, non-provider failure
                    print(f"\n[agent_loop DEBUG] task_id={task_id} iteration={iteration} "
                          f"unexpected error on CUDA crash retry: {type(retry_exc).__name__}: {retry_exc}",
                          file=sys.stderr)
                    traceback.print_exc(file=sys.stderr)
                    logger.record(task_id, tokens_in=0, tokens_out=0)
                    outcome = "error"
                    reason = f"unexpected_error:{type(retry_exc).__name__}:{retry_exc}"
                    transcript.append({"iteration": iteration, "error": reason, "cuda_crash_retry_failed": True})
                    break
                # Retry succeeded — content/meta are now set; fall through to
                # normal per-iteration processing below.
            else:
                # The model never answered — this is a provider/connection failure
                # (e.g. DNS, timeout, unreachable Ollama), not a task outcome. Keep
                # it out of "escalated" (which means the model DID respond and
                # either chose to escalate or ran out of turns) so the results
                # table can't silently present a dead connection as a normal run.
                print(f"\n[agent_loop DEBUG] task_id={task_id} iteration={iteration} "
                      f"LLM call raised {type(exc).__name__}: {exc}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                logger.record(task_id, tokens_in=0, tokens_out=0)
                outcome = "error"
                reason = f"llm_provider_error:{type(exc).__name__}:{exc}"
                transcript.append({"iteration": iteration, "error": reason})
                break
        except Exception as exc:  # noqa: BLE001 - unexpected, non-provider failure
            print(f"\n[agent_loop DEBUG] task_id={task_id} iteration={iteration} "
                  f"unexpected {type(exc).__name__}: {exc}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            logger.record(task_id, tokens_in=0, tokens_out=0)
            outcome = "error"
            reason = f"unexpected_error:{type(exc).__name__}:{exc}"
            transcript.append({"iteration": iteration, "error": reason})
            break

        tokens_in = int(meta.get("input_tokens", 0))
        tokens_out = int(meta.get("output_tokens", 0))
        logger.record(task_id, tokens_in=tokens_in, tokens_out=tokens_out)
        tokens_in_total += tokens_in
        tokens_out_total += tokens_out

        action = _extract_json_object(content)
        transcript.append({"iteration": iteration, "raw_response": _truncate(content, 500), "parsed": action})

        if action is None:
            history_entries.append(
                "[System] Your last response was not valid JSON. Respond with exactly "
                "one JSON object matching the tool schema."
            )
            continue

        tool = action.get("tool")
        args = action.get("args") or {}

        if tool == "check_completeness":
            tool_calls += 1
            result = _tool_check_completeness(args.get("evidence_id", evidence_id), scenario)
            history_entries.append(f"[check_completeness result] {_summarize_tool_result(result)}")
            continue

        if tool == "fetch_from_connector":
            tool_calls += 1
            result = _tool_fetch_from_connector(
                str(args.get("source", "")), args.get("params") or {}, scenario, fetch_state
            )
            if not result.get("ok"):
                had_failed_fetch = True
            history_entries.append(f"[fetch_from_connector result] {_summarize_tool_result(result)}")
            continue

        if tool == "request_human_review":
            tool_calls += 1
            reason = str(args.get("reason", "model_requested_human_review"))
            _tool_request_human_review(reason)
            outcome = "escalated"
            break

        if tool == "finish":
            resolved = bool(args.get("resolved"))
            if resolved:
                outcome = "resolved_with_retry" if had_failed_fetch else "auto_resolved"
            else:
                outcome = "escalated"
                reason = str(args.get("summary", "model_finished_unresolved"))
            break

        history_entries.append(
            f"[System] Unknown tool '{tool}'. Valid tools: check_completeness, "
            f"fetch_from_connector, request_human_review, finish."
        )

    if outcome is None:
        outcome = "escalated"
        reason = reason or "max_iterations_exceeded"

    wall_ms = round((time.perf_counter() - started) * 1000, 3)
    return {
        "task_id": task_id,
        "tier": tier,
        "outcome": outcome,
        "reason": reason,
        "tool_calls": tool_calls,
        "iterations_used": len(transcript),
        "tokens_in": tokens_in_total,
        "tokens_out": tokens_out_total,
        "cuda_crash_retries": cuda_crash_retries,
        "wall_ms_dev_hardware": wall_ms,
        "expected_outcome_category": scenario.get("expected_outcome_category", ""),
        "timestamp": _ts(),
        "transcript": transcript,
    }


def run_agent_baseline(
    scenarios: list[dict[str, Any]],
    *,
    provider: Any = None,
    logger: LLMCallLogger | None = None,
) -> list[dict[str, Any]]:
    """Run every scenario through the agentic loop, strictly sequentially —
    one scenario (including all its LLM calls) completes before the next
    starts. No concurrency."""
    if provider is None:
        from ecs_platform.llm_engine.provider import get_provider

        provider = get_provider()
    if logger is None:
        logger = LLMCallLogger()

    results = []
    for scenario in scenarios:
        results.append(run_agent_task(scenario, provider, logger))
    return results


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def render_results_table(results: list[dict[str, Any]]) -> str:
    lines = [
        "| task_id | tier | outcome | tool_calls | tokens_in | tokens_out | time_ms (dev-hardware) |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['task_id']} | {r['tier']} | {r['outcome']} | {r['tool_calls']} | "
            f"{r['tokens_in']} | {r['tokens_out']} | {r['wall_ms_dev_hardware']} |"
        )
    return "\n".join(lines)


def compute_rollup(results: list[dict[str, Any]]) -> dict[str, Any]:
    tiers = sorted({r["tier"] for r in results})
    by_tier: dict[str, dict[str, Any]] = {}
    for tier in tiers:
        tier_results = [r for r in results if r["tier"] == tier]
        n = len(tier_results)
        auto = sum(1 for r in tier_results if r["outcome"] == "auto_resolved")
        retry = sum(1 for r in tier_results if r["outcome"] == "resolved_with_retry")
        esc = sum(1 for r in tier_results if r["outcome"] == "escalated")
        err = sum(1 for r in tier_results if r["outcome"] == "error")
        by_tier[tier] = {
            "n": n,
            "auto_resolved": auto,
            "resolved_with_retry": retry,
            "escalated": esc,
            "error": err,
            "auto_resolve_rate": round(auto / n, 3) if n else 0.0,
        }
    n_total = len(results)
    avg_tokens_in = round(sum(r["tokens_in"] for r in results) / n_total, 1) if n_total else 0.0
    avg_tokens_out = round(sum(r["tokens_out"] for r in results) / n_total, 1) if n_total else 0.0
    avg_tokens_total = round(avg_tokens_in + avg_tokens_out, 1)
    avg_time_ms = round(sum(r["wall_ms_dev_hardware"] for r in results) / n_total, 1) if n_total else 0.0
    cuda_crash_retries_total = sum(r.get("cuda_crash_retries", 0) for r in results)
    return {
        "by_tier": by_tier,
        "total_scenarios": n_total,
        "avg_tokens_in_per_task": avg_tokens_in,
        "avg_tokens_out_per_task": avg_tokens_out,
        "avg_tokens_per_task": avg_tokens_total,
        "avg_time_ms_per_task_dev_hardware": avg_time_ms,
        "cuda_crash_retries_total": cuda_crash_retries_total,
    }


def render_rollup(rollup: dict[str, Any], baseline_comparison: dict[str, Any] | None = None) -> str:
    lines = ["## Rollup", ""]
    lines.append("| tier | n | auto_resolved | resolved_with_retry | escalated | error (infra) | auto-resolve rate |")
    lines.append("|---|---|---|---|---|---|---|")
    for tier, stats in sorted(rollup["by_tier"].items()):
        lines.append(
            f"| {tier} | {stats['n']} | {stats['auto_resolved']} | {stats['resolved_with_retry']} | "
            f"{stats['escalated']} | {stats['error']} | {stats['auto_resolve_rate']:.1%} |"
        )
    lines.append("")
    lines.append(f"- Avg tokens/task: **{rollup['avg_tokens_per_task']}** "
                 f"(in: {rollup['avg_tokens_in_per_task']}, out: {rollup['avg_tokens_out_per_task']}) "
                 f"— hardware-independent")
    lines.append(f"- Avg time/task: **{rollup['avg_time_ms_per_task_dev_hardware']} ms** "
                 f"— dev-hardware wall-clock, not comparable across machines")
    lines.append(f"- CUDA crash retries: **{rollup['cuda_crash_retries_total']}** "
                 f"— infra-stability metric (bounded auto-retry triggers), not a task outcome")

    if baseline_comparison is not None:
        lines.append("")
        lines.append("## Agent vs. deterministic baseline (same scenario subset)")
        lines.append("")
        lines.append("| tier | baseline resolved | baseline escalated | agent resolved (auto+retry) | agent escalated | agent error (infra) |")
        lines.append("|---|---|---|---|---|---|")
        for tier in sorted(baseline_comparison["by_tier"]):
            b = baseline_comparison["by_tier"][tier]
            lines.append(
                f"| {tier} | {b['baseline_resolved']} | {b['baseline_escalated']} | "
                f"{b['agent_resolved']} | {b['agent_escalated']} | {b['agent_error']} |"
            )
        lines.append("")
        lines.append(
            f"**Overall:** baseline resolved {baseline_comparison['baseline_resolved_total']}/"
            f"{baseline_comparison['total']}, agent resolved "
            f"{baseline_comparison['agent_resolved_total']}/{baseline_comparison['total']} "
            f"(of which {baseline_comparison['agent_auto_resolved_total']} auto and "
            f"{baseline_comparison['agent_resolved_with_retry_total']} via retry); "
            f"{baseline_comparison['agent_error_total']} task(s) hit an infra error "
            f"(never got a model response — excluded from the resolved/escalated comparison)."
        )
    return "\n".join(lines)


def compute_baseline_comparison(
    agent_results: list[dict[str, Any]], baseline_results: list[dict[str, Any]]
) -> dict[str, Any]:
    baseline_by_id = {b["task_id"]: b for b in baseline_results}
    tiers = sorted({r["tier"] for r in agent_results})
    by_tier: dict[str, dict[str, int]] = {}
    baseline_resolved_total = 0
    agent_resolved_total = 0
    agent_auto_total = 0
    agent_retry_total = 0
    agent_error_total = 0
    for tier in tiers:
        tier_agent = [r for r in agent_results if r["tier"] == tier]
        b_resolved = 0
        b_escalated = 0
        a_resolved = 0
        a_escalated = 0
        a_error = 0
        for r in tier_agent:
            b = baseline_by_id.get(r["task_id"], {})
            if b.get("outcome") == "resolved":
                b_resolved += 1
            else:
                b_escalated += 1
            if r["outcome"] in ("auto_resolved", "resolved_with_retry"):
                a_resolved += 1
            elif r["outcome"] == "error":
                # Infra failure, not a real task outcome — excluded from both
                # resolved and escalated so it can't be read as "the agent
                # tried and gave up" when it never actually got to try.
                a_error += 1
            else:
                a_escalated += 1
        by_tier[tier] = {
            "baseline_resolved": b_resolved,
            "baseline_escalated": b_escalated,
            "agent_resolved": a_resolved,
            "agent_escalated": a_escalated,
            "agent_error": a_error,
        }
        baseline_resolved_total += b_resolved
        agent_resolved_total += a_resolved
        agent_auto_total += sum(1 for r in tier_agent if r["outcome"] == "auto_resolved")
        agent_retry_total += sum(1 for r in tier_agent if r["outcome"] == "resolved_with_retry")
        agent_error_total += a_error
    return {
        "by_tier": by_tier,
        "total": len(agent_results),
        "baseline_resolved_total": baseline_resolved_total,
        "agent_resolved_total": agent_resolved_total,
        "agent_auto_resolved_total": agent_auto_total,
        "agent_resolved_with_retry_total": agent_retry_total,
        "agent_error_total": agent_error_total,
    }
