"""Common-Control evaluation orchestrator.

Wires the generic rule engine (:mod:`common_control_rule_engine`) to
infrastructure the platform already has — nothing here executes a query,
talks to a connector, or invents a new evidence store:

    application/CMDB metadata (Asset)
        -> technology (existing discovery/fingerprint)
        -> applicable predefined queries (existing predefined_queries_engine)
        -> execution (existing predefined_queries_engine.run_predefined_query)
        -> normalization (predefined_query_normalizer)
        -> rule evaluation (common_control_rule_engine)
        -> Common Control verdict
        -> FCM framework mappings (existing common_controls_service)

A control that has no rule for the resolved technology is NOT_APPLICABLE. A
control whose predefined query could not be reached/executed is UNKNOWN —
never IMPLEMENTED. Nothing here is application-specific; identity (asset_id /
application / environment) is only carried through for reporting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from modules.operations.engines.common_control_rule_engine import (
    ControlRule,
    RuleOutcome,
    RULE_UNKNOWN,
    RulePack,
    control_metadata,
    evaluate_rule,
    load_rule_pack,
    verdict_from_rule_outcomes,
)
from modules.operations.engines.predefined_query_normalizer import (
    NormalizedEvidence,
    normalize_execution_result,
    unavailable_evidence,
)

#: (control_id, technology, user) -> run_predefined_query(control_id, user) result dict.
#: Overridable so evaluation is unit-testable offline without live connectors.
Executor = Callable[[str, str], dict[str, Any]]


@dataclass
class ControlEvaluation:
    """One Common Control's verdict for one (asset/technology) evaluation."""

    control: str
    control_id: str
    control_name: str
    technology: str
    verdict: str
    asset_id: str = ""
    application: str = ""
    environment: str = ""
    rule_outcomes: list[RuleOutcome] = field(default_factory=list)
    predefined_query_ids: list[str] = field(default_factory=list)
    framework_mappings: list[dict[str, Any]] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        frameworks = sorted({m.get("framework_name") for m in self.framework_mappings if m.get("framework_name")})
        return {
            "control": self.control,
            "control_id": self.control_id,
            "control_name": self.control_name,
            "technology": self.technology,
            "asset_id": self.asset_id,
            "application": self.application,
            "environment": self.environment,
            "verdict": self.verdict,
            "reason": self.reason,
            "predefined_query_ids": list(self.predefined_query_ids),
            "rule_outcomes": [o.to_dict() for o in self.rule_outcomes],
            "frameworks": frameworks,
            "framework_mappings": list(self.framework_mappings),
        }


def _default_executor(control_id: str, user: str) -> dict[str, Any]:
    from modules.operations.engines.predefined_queries_engine import run_predefined_query

    return run_predefined_query(control_id, user)


def make_executor(*, persist: bool = False, scheduled: bool = False) -> Executor:
    """Build an executor bound to the existing PQ persistence flags.

    Reuses ``predefined_queries_engine.run_predefined_query``'s own
    ``persist``/``scheduled`` handling (evidence artifact + audit trail) — this
    module never writes evidence itself. Pass the result as ``executor=`` to
    persist evaluation runs (e.g. from onboarding or a scheduler), or omit it
    entirely for ad-hoc/preview evaluation (the default — matches how the rest
    of the platform treats one-off predefined-query calls).
    """
    from modules.operations.engines.predefined_queries_engine import run_predefined_query

    def _run(control_id: str, user: str) -> dict[str, Any]:
        return run_predefined_query(control_id, user, persist=persist, scheduled=scheduled)

    return _run


def _execution_mode_for(control_id: str) -> str:
    from modules.operations.engines.predefined_queries_engine import get_control_by_id

    ctrl = get_control_by_id(control_id) or {}
    return str(ctrl.get("execution_mode") or "")


def _pq_is_executable(control_id: str) -> tuple[bool, str]:
    """Whether the existing PQ catalog can execute this control at all.

    Reuses the platform's own capability assessment (Phase-1 selection,
    connector availability, target configuration) instead of re-deriving it.
    """
    from modules.operations.engines.predefined_queries_engine import (
        get_control_by_id,
        is_live_execution_enabled,
    )

    ctrl = get_control_by_id(control_id)
    if ctrl is None:
        return False, f"Predefined query {control_id} not found in the catalog."
    if not is_live_execution_enabled(ctrl):
        return False, ctrl.get("capability_reason") or "Live execution is not enabled for this control."
    return True, ""


def gather_evidence_for_rule(
    rule: ControlRule,
    *,
    user: str,
    executor: Executor | None = None,
    evidence_cache: dict[str, NormalizedEvidence] | None = None,
) -> NormalizedEvidence:
    """Execute (or reuse a cached execution of) the PQ a rule depends on."""
    run = executor or _default_executor
    cache = evidence_cache if evidence_cache is not None else {}
    cache_key = rule.predefined_query_id
    if cache_key in cache:
        return cache[cache_key]

    if not rule.predefined_query_id:
        ev = unavailable_evidence(
            query_id="",
            technology=rule.technology,
            reason="Rule has no predefined_query_id configured.",
            reason_code="NO_RULES_CONFIGURED",
            status="NOT_CONFIGURED",
        )
        cache[cache_key] = ev
        return ev

    executable, reason = _pq_is_executable(rule.predefined_query_id)
    if not executable:
        ev = unavailable_evidence(query_id=rule.predefined_query_id, technology=rule.technology, reason=reason)
        cache[cache_key] = ev
        return ev

    result = run(rule.predefined_query_id, user)
    ev = normalize_execution_result(
        result,
        query_id=rule.predefined_query_id,
        technology=rule.technology,
        execution_mode=_execution_mode_for(rule.predefined_query_id),
        parse=rule.parse,
    )
    cache[cache_key] = ev
    return ev


def evaluate_common_control(
    control: str,
    technology: str,
    *,
    user: str = "system",
    asset_id: str = "",
    application: str = "",
    environment: str = "",
    executor: Executor | None = None,
    pack: RulePack | None = None,
    evidence_cache: dict[str, NormalizedEvidence] | None = None,
    resolve_frameworks: bool = True,
) -> ControlEvaluation:
    """Evaluate one Common Control for one technology (optionally scoped to an asset)."""
    rp = pack or load_rule_pack()
    meta = control_metadata(control, rp)
    rules = rp.rules_for(control, technology)

    evaln = ControlEvaluation(
        control=control,
        control_id=meta.control_id,
        control_name=meta.name,
        technology=technology,
        verdict="NOT_APPLICABLE",
        asset_id=asset_id,
        application=application,
        environment=environment,
    )

    if not rules:
        evaln.reason = (
            f"No rule configured for control='{control}' + technology='{technology}' — "
            "not applicable to this technology."
        )
        return evaln

    # Share one cache across every rule in *this* control evaluation so a PQ
    # referenced by more than one rule (e.g. one settings query feeding two
    # field checks) only executes once, even when the caller didn't pass a
    # cache of its own.
    cache = evidence_cache if evidence_cache is not None else {}
    evaln.predefined_query_ids = rp.predefined_query_ids(control, technology)
    outcomes = [
        evaluate_rule(
            rule,
            gather_evidence_for_rule(rule, user=user, executor=executor, evidence_cache=cache),
        )
        for rule in rules
    ]
    evaln.rule_outcomes = outcomes
    evaln.verdict = verdict_from_rule_outcomes(outcomes)
    evaln.reason = _summarize(outcomes, evaln.verdict)

    if resolve_frameworks:
        evaln.framework_mappings = _resolve_frameworks(meta)
    return evaln


def _summarize(outcomes: list[RuleOutcome], verdict: str) -> str:
    total = len(outcomes)
    passed = sum(1 for o in outcomes if o.status == "PASS")
    failed = sum(1 for o in outcomes if o.status == "FAIL")
    unknown = sum(1 for o in outcomes if o.status == RULE_UNKNOWN)
    return f"{verdict}: {passed}/{total} rule(s) passed, {failed} failed, {unknown} unknown."


def _resolve_frameworks(meta) -> list[dict[str, Any]]:
    try:
        from modules.frameworks.services.common_controls_service import (
            get_common_controls_service,
            resolve_fcm_references_for_domains,
        )

        legacy = get_common_controls_service()
        if legacy.get_control(meta.slug).get("ok"):
            return legacy.resolve_fcm_references(meta.slug)
        return resolve_fcm_references_for_domains(
            control_id=meta.control_id,
            slug=meta.slug,
            name=meta.name,
            match_domains=meta.match_domains,
        )
    except Exception:  # noqa: BLE001 - framework mapping must never break evaluation
        return []


def evaluate_common_control_for_asset(
    control: str,
    asset: Any,
    *,
    user: str = "system",
    executor: Executor | None = None,
    pack: RulePack | None = None,
    evidence_cache: dict[str, NormalizedEvidence] | None = None,
) -> ControlEvaluation:
    """Evaluate one control for a discovered :class:`~modules.audit_intelligence.models.Asset`."""
    technology = asset.technology if hasattr(asset, "technology") else str(asset.get("technology") or "")
    asset_id = asset.asset_id if hasattr(asset, "asset_id") else str(asset.get("asset_id") or "")
    application = asset.application if hasattr(asset, "application") else str(asset.get("application") or "")
    environment = asset.environment if hasattr(asset, "environment") else str(asset.get("environment") or "")
    return evaluate_common_control(
        control,
        technology,
        user=user,
        asset_id=asset_id,
        application=application,
        environment=environment,
        executor=executor,
        pack=pack,
        evidence_cache=evidence_cache,
    )


def evaluate_controls_for_technology(
    controls: list[str],
    technology: str,
    *,
    user: str = "system",
    asset_id: str = "",
    application: str = "",
    environment: str = "",
    executor: Executor | None = None,
    pack: RulePack | None = None,
) -> list[ControlEvaluation]:
    """Evaluate a *given* set of controls against one technology.

    Unlike :func:`evaluate_all_controls_for_technology`, controls with no rule
    for this technology are still evaluated (and returned as NOT_APPLICABLE)
    instead of being silently dropped — reports built from this need every
    combination to be visible, not just the ones the rule pack happens to
    cover.
    """
    rp = pack or load_rule_pack()
    cache: dict[str, NormalizedEvidence] = {}
    return [
        evaluate_common_control(
            control,
            technology,
            user=user,
            asset_id=asset_id,
            application=application,
            environment=environment,
            executor=executor,
            pack=rp,
            evidence_cache=cache,
        )
        for control in controls
    ]


def evaluate_all_controls_for_technology(
    technology: str,
    *,
    user: str = "system",
    asset_id: str = "",
    application: str = "",
    environment: str = "",
    executor: Executor | None = None,
    pack: RulePack | None = None,
) -> list[ControlEvaluation]:
    """Evaluate every Common Control that has at least one rule for this technology."""
    rp = pack or load_rule_pack()
    return evaluate_controls_for_technology(
        rp.controls_for_technology(technology),
        technology,
        user=user,
        asset_id=asset_id,
        application=application,
        environment=environment,
        executor=executor,
        pack=rp,
    )


def evaluate_controls_for_assets(
    controls: list[str],
    assets: list[Any],
    *,
    user: str = "system",
    executor: Executor | None = None,
    pack: RulePack | None = None,
) -> list[ControlEvaluation]:
    """Evaluate a set of controls across a set of assets (application/CMDB onboarding path).

    Evidence is cached per predefined-query id *within* one asset (a PQ never
    needs to run twice for the same asset) but not across assets, since each
    asset is a distinct target/connection.
    """
    rp = pack or load_rule_pack()
    out: list[ControlEvaluation] = []
    for asset in assets:
        cache: dict[str, NormalizedEvidence] = {}
        for control in controls:
            out.append(
                evaluate_common_control_for_asset(
                    control, asset, user=user, executor=executor, pack=rp, evidence_cache=cache
                )
            )
    return out
