"""Control-evaluation service — REST facade over the Common-Control rule engine.

Backs ``POST /api/control-evaluation``. Thin translation layer only: request
validation + shaping the response the API contract promises (control,
technology, PQ/evidence reference, expected/actual, verdict, reason, evidence
id, framework mappings). All evaluation logic lives in
``common_control_evaluation_engine`` / ``common_control_onboarding`` /
``common_control_report_engine``.
"""

from __future__ import annotations

from typing import Any

from modules.operations.engines.common_control_evaluation_engine import ControlEvaluation, Executor
from modules.operations.engines.common_control_onboarding import evaluate_application
from modules.operations.engines.common_control_report_engine import build_implementation_report
from modules.operations.engines.common_control_rule_engine import load_rule_pack


def _shape_result(ev: ControlEvaluation) -> dict[str, Any]:
    frameworks = sorted({m.get("framework_name") for m in ev.framework_mappings if m.get("framework_name")})
    return {
        "control": ev.control,
        "control_id": ev.control_id,
        "control_name": ev.control_name,
        "technology": ev.technology,
        "asset_id": ev.asset_id,
        "application": ev.application,
        "environment": ev.environment,
        "verdict": ev.verdict,
        "reason": ev.reason,
        "predefined_query_ids": list(ev.predefined_query_ids),
        "frameworks": frameworks,
        "framework_mappings": list(ev.framework_mappings),
        "rule_results": [
            {
                "rule_id": o.rule_id,
                "predefined_query_id": o.predefined_query_id,
                "evidence_field": o.evidence_field,
                "operator": o.operator,
                "expected_value": o.expected_value,
                "actual_value": o.actual_value,
                "status": o.status,
                "reason": o.reason,
                "reason_code": o.reason_code,
                "evidence_id": o.evidence_id,
            }
            for o in ev.rule_outcomes
        ],
    }


def evaluate_control_request(payload: dict[str, Any], *, executor: Executor | None = None) -> dict[str, Any]:
    """Handle a ``POST /api/control-evaluation`` request body.

    Body fields (all optional except ``application_id``):
      * ``application_id`` — required; resolves against the existing
        application/CMDB portfolio (see ``common_control_onboarding``).
      * ``control`` — a single common-control slug, or a list of slugs, to
        restrict evaluation to (default: every control in the rule pack).
      * ``asset_id`` — restrict evaluation to one asset of the application.
      * ``user`` — attributed to the underlying PQ executions (default "api").
      * ``persist`` — when true, persist collected evidence via the existing
        predefined-query evidence pipeline (default false = preview only).

    ``executor`` is a keyword-only, non-request parameter: it exists purely so
    tests/offline callers can stub out predefined-query execution instead of
    hitting real connectors. The FastAPI route never passes it, so production
    calls always go through the real engine (default: preview, not persisted).
    """
    application_id = str(payload.get("application_id") or payload.get("application") or "").strip()
    if not application_id:
        return {"ok": False, "error": "application_id is required", "error_type": "missing_application_id"}

    control_filter = payload.get("control")
    if isinstance(control_filter, str) and control_filter.strip():
        controls = [control_filter.strip()]
    elif isinstance(control_filter, (list, tuple)):
        controls = [str(c).strip() for c in control_filter if str(c).strip()]
    else:
        controls = None

    asset_filter = str(payload.get("asset_id") or "").strip()
    user = str(payload.get("user") or "api")
    persist = bool(payload.get("persist") or False)
    rp = load_rule_pack()

    profile, evaluations, assets_summary = evaluate_application(
        application_id,
        controls=controls,
        user=user,
        persist=persist,
        executor=executor,
        asset_id=asset_filter,
        pack=rp,
    )
    if profile is None:
        from modules.operations.engines.phase2_reusability import list_application_profiles

        return {
            "ok": False,
            "error": f"Unknown application '{application_id}'",
            "error_type": "unknown_application",
            "known_applications": sorted(p.id for p in list_application_profiles()),
        }
    if asset_filter and asset_filter not in assets_summary:
        return {
            "ok": False,
            "error": f"Unknown asset '{asset_filter}' for application '{application_id}'",
            "error_type": "unknown_asset",
        }

    report = build_implementation_report(
        evaluations, application=profile["application"], environment=profile["environment"]
    )

    return {
        "ok": True,
        "application_id": profile["application_id"],
        "application": profile["application"],
        "environment": profile["environment"],
        "assets": list(assets_summary.values()),
        "results": [_shape_result(ev) for ev in evaluations],
        # Aggregated per-control-slug rows + raw per-instance rows, in the same
        # shape ``common_control_onboarding.onboard_application`` already
        # returns — lets the same onboarding-results UI render either report.
        "controls": report["controls"],
        "evaluation_detail": report["evaluation_detail"],
        "coverage_pct": report["coverage_pct"],
        "implemented": [r["control"] for r in report["implemented"]],
        "not_implemented": [r["control"] for r in report["not_implemented"]],
        "partial": [r["control"] for r in report["partial"]],
        "unknown": [r["control"] for r in report["unknown"]],
        "not_applicable": [r["control"] for r in report["not_applicable"]],
        "frameworks": report["frameworks"],
    }
