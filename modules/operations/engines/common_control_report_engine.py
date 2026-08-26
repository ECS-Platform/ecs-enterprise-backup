"""Cross-control, cross-framework implementation report over Common-Control
evaluations produced by :mod:`common_control_evaluation_engine`.

Pure aggregation — no execution, no new evidence, no framework-name
hardcoding. Two things this module refuses to do, by design:

  * Roll a framework up to "compliant" just because some of its mapped
    controls passed — a framework's ``coverage_pct`` is always reported next
    to explicit implemented / not_implemented / partial / unknown counts, and
    the denominator is documented (it is the FCM controls this engine's
    common controls actually map to, not the framework's full control count).
  * Treat "not evaluated for this technology" (NOT_APPLICABLE) the same as
    "evaluated but inconclusive" (UNKNOWN) — they are counted separately so a
    gap in the rule pack is never mistaken for a live connectivity problem.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from modules.operations.engines.common_control_evaluation_engine import ControlEvaluation
from modules.operations.engines.common_control_rule_engine import (
    VERDICT_IMPLEMENTED,
    VERDICT_NOT_APPLICABLE,
    VERDICT_NOT_IMPLEMENTED,
    VERDICT_PARTIAL,
    VERDICT_UNKNOWN,
    aggregate_verdicts,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_control_summary(evaluations: list[ControlEvaluation]) -> list[dict[str, Any]]:
    """One row per common-control slug, rolled up across every technology/asset it saw."""
    by_control: dict[str, list[ControlEvaluation]] = defaultdict(list)
    for ev in evaluations:
        by_control[ev.control].append(ev)

    rows: list[dict[str, Any]] = []
    for control, evals in sorted(by_control.items()):
        verdict = aggregate_verdicts([e.verdict for e in evals])
        rows.append(
            {
                "control": control,
                "control_id": evals[0].control_id,
                "control_name": evals[0].control_name,
                "verdict": verdict,
                "technologies_evaluated": sorted({e.technology for e in evals if e.technology}),
                "assets_evaluated": sorted({e.asset_id for e in evals if e.asset_id}),
                "instance_count": len(evals),
                "implemented_count": sum(1 for e in evals if e.verdict == VERDICT_IMPLEMENTED),
                "not_implemented_count": sum(1 for e in evals if e.verdict == VERDICT_NOT_IMPLEMENTED),
                "partial_count": sum(1 for e in evals if e.verdict == VERDICT_PARTIAL),
                "unknown_count": sum(1 for e in evals if e.verdict == VERDICT_UNKNOWN),
                "not_applicable_count": sum(1 for e in evals if e.verdict == VERDICT_NOT_APPLICABLE),
            }
        )
    return rows


def build_framework_coverage(evaluations: list[ControlEvaluation]) -> list[dict[str, Any]]:
    """Per-framework coverage over the FCM controls this evaluation run actually mapped to.

    ``coverage_pct`` denominator is ``controls_mapped`` — the distinct FCM
    control ids reached by any evaluated common control's framework mapping —
    not the framework's total control count. A framework with 6 controls
    where only 2 are addressable by common controls reports its own
    ``framework_control_count`` alongside so the difference is visible.
    """
    # framework_name -> fcm_control_id -> set of common-control verdicts touching it
    by_fw_control: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    fw_ids: dict[str, str] = {}
    for ev in evaluations:
        if ev.verdict == VERDICT_NOT_APPLICABLE:
            continue
        for mapping in ev.framework_mappings:
            fw_name = str(mapping.get("framework_name") or "")
            fcm_control_id = str(mapping.get("control_id") or "")
            if not fw_name or not fcm_control_id:
                continue
            fw_ids[fw_name] = str(mapping.get("framework_id") or "")
            by_fw_control[fw_name][fcm_control_id].add(ev.verdict)

    total_controls_by_fw = _framework_total_control_counts()

    rows: list[dict[str, Any]] = []
    for fw_name, control_verdicts in sorted(by_fw_control.items()):
        implemented = not_implemented = partial = unknown = 0
        for verdicts in control_verdicts.values():
            rolled = aggregate_verdicts(list(verdicts))
            if rolled == VERDICT_IMPLEMENTED:
                implemented += 1
            elif rolled == VERDICT_NOT_IMPLEMENTED:
                not_implemented += 1
            elif rolled == VERDICT_PARTIAL:
                partial += 1
            else:
                unknown += 1
        mapped = len(control_verdicts)
        rows.append(
            {
                "framework_id": fw_ids.get(fw_name, ""),
                "framework_name": fw_name,
                "controls_mapped": mapped,
                "framework_control_count": total_controls_by_fw.get(fw_name, mapped),
                "implemented": implemented,
                "not_implemented": not_implemented,
                "partial": partial,
                "unknown": unknown,
                "coverage_pct": round((implemented / mapped) * 100, 1) if mapped else 0.0,
                "fully_addressed_by_common_controls": mapped >= total_controls_by_fw.get(fw_name, mapped) and mapped > 0,
            }
        )
    return rows


def _framework_total_control_counts() -> dict[str, int]:
    try:
        from modules.frameworks.repositories.framework_control_repository import (
            get_framework_control_repository,
        )
        from modules.operations.engines.common_controls_catalog import FCM_FRAMEWORK_IDS

        repo = get_framework_control_repository()
        counts: dict[str, int] = {}
        for fw_id in FCM_FRAMEWORK_IDS:
            doc = repo.get_framework(fw_id) or {}
            fw = doc.get("framework") or {}
            name = str(fw.get("name") or fw.get("display_name") or fw_id)
            counts[name] = len(doc.get("controls") or [])
        return counts
    except Exception:  # noqa: BLE001
        return {}


def build_implementation_report(
    evaluations: list[ControlEvaluation],
    *,
    application: str = "",
    environment: str = "",
) -> dict[str, Any]:
    """Full onboarding/implementation report: control rollup + framework coverage."""
    control_rows = build_control_summary(evaluations)
    framework_rows = build_framework_coverage(evaluations)

    implemented = [r for r in control_rows if r["verdict"] == VERDICT_IMPLEMENTED]
    not_implemented = [r for r in control_rows if r["verdict"] == VERDICT_NOT_IMPLEMENTED]
    partial = [r for r in control_rows if r["verdict"] == VERDICT_PARTIAL]
    unknown = [r for r in control_rows if r["verdict"] == VERDICT_UNKNOWN]
    not_applicable = [r for r in control_rows if r["verdict"] == VERDICT_NOT_APPLICABLE]

    applicable_total = len(control_rows) - len(not_applicable)
    coverage_pct = round((len(implemented) / applicable_total) * 100, 1) if applicable_total else 0.0

    return {
        "generated_at": _now(),
        "application": application,
        "environment": environment,
        "controls_evaluated": len(control_rows),
        "coverage_pct": coverage_pct,
        "coverage_denominator": "applicable common controls (NOT_APPLICABLE excluded)",
        "implemented": implemented,
        "not_implemented": not_implemented,
        "partial": partial,
        "unknown": unknown,
        "not_applicable": not_applicable,
        "controls": control_rows,
        "frameworks": framework_rows,
        "evaluation_detail": [e.to_dict() for e in evaluations],
    }
