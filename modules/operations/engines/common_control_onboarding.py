"""Application onboarding -> Common-Control evaluation -> implementation report.

Implements the flow:

    application/CMDB metadata -> environment/assets/technology
        -> applicable existing PQs -> execute -> normalize
        -> evaluate configurable rules -> Common Control verdict
        -> FCM framework mappings -> implementation report

Application/environment/asset/technology identity comes from EXISTING
application metadata — :mod:`modules.operations.engines.phase2_reusability`
(``config/phase2_application_portfolio.yaml``, already the platform's
config-only "CMDB" for this exact onboarding shape — see its
``demo_card_portal`` entry) — or from a caller-supplied list of
:class:`~modules.audit_intelligence.models.Asset` records discovered through
:mod:`modules.audit_intelligence.engines.asset_discovery` (ServiceNow CMDB /
manual import / enterprise GRC). Neither source is duplicated here.

If a target is unreachable, onboarding does not stop or raise: the affected
controls simply come back UNKNOWN with a ``CONNECTIVITY_PENDING`` reason —
onboarding of every other asset/control continues.
"""

from __future__ import annotations

import re
from typing import Any

from modules.operations.engines.common_control_evaluation_engine import (
    ControlEvaluation,
    Executor,
    evaluate_controls_for_assets,
    evaluate_controls_for_technology,
    make_executor,
)
from modules.operations.engines.common_control_report_engine import build_implementation_report
from modules.operations.engines.common_control_rule_engine import (
    REASON_CONNECTIVITY_PENDING,
    RulePack,
    load_rule_pack,
)


def _demo_mode_enabled() -> bool:
    try:
        from app.auth.demo import demo_mode

        return demo_mode()
    except Exception:  # noqa: BLE001 - never let a demo-flag check break onboarding
        return False


def _connectivity_pending_controls(evaluations: list[ControlEvaluation]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ev in evaluations:
        pending = [o for o in ev.rule_outcomes if o.reason_code == REASON_CONNECTIVITY_PENDING]
        if pending:
            out.append(
                {
                    "control": ev.control,
                    "technology": ev.technology,
                    "asset_id": ev.asset_id,
                    "predefined_query_ids": sorted({o.predefined_query_id for o in pending if o.predefined_query_id}),
                }
            )
    return out


def evaluate_application(
    application_id: str,
    *,
    controls: list[str] | None = None,
    user: str = "system",
    executor: Executor | None = None,
    persist: bool = False,
    asset_id: str = "",
    portfolio: dict[str, Any] | None = None,
    pack: RulePack | None = None,
) -> tuple[dict[str, Any] | None, list[ControlEvaluation], dict[str, Any]]:
    """Resolve an application's assets and evaluate the requested controls.

    Returns ``(profile_dict_or_None, evaluations, assets_summary_by_id)``.
    ``profile_dict_or_None`` is ``None`` when ``application_id`` is unknown —
    callers should treat that as the error case; ``evaluations`` is empty in
    that case. Shared by :func:`onboard_application` (full report) and the
    ``POST /api/control-evaluation`` service (which also needs the raw,
    per-rule evaluation objects, not just the aggregated report).
    """
    from modules.audit_intelligence.engines.technology_fingerprint import fingerprint_asset
    from modules.operations.engines.phase2_reusability import (
        list_application_profiles,
        load_application_portfolio,
    )

    data = portfolio or load_application_portfolio()
    profiles = {p.id: p for p in list_application_profiles(data)}
    profile = profiles.get(application_id)
    if profile is None:
        return None, [], {}

    rp = pack or load_rule_pack()
    control_list = controls or rp.controls()
    run_executor = executor or (make_executor(persist=True, scheduled=True) if persist else None)

    evaluations: list[ControlEvaluation] = []
    assets_summary: dict[str, dict[str, str]] = {}
    for asset in profile.assets:
        raw_technology = str(asset.get("technology") or "")
        this_asset_id = str(asset.get("asset_id") or "")
        if not raw_technology or not this_asset_id:
            continue
        if asset_id and this_asset_id != asset_id:
            continue
        # Portfolio config uses adapter-style technology slugs (aurora_mysql,
        # linux_rhel, ...); the predefined-query catalog and rule pack key on
        # the platform's canonical technology labels (Aurora MySQL, Linux,
        # ...) — reuse the existing fingerprinting canonicalizer instead of
        # re-deriving that mapping here.
        technology = fingerprint_asset({"technology": raw_technology}).technology
        assets_summary[this_asset_id] = {"asset_id": this_asset_id, "technology": technology, "technology_raw": raw_technology}
        evaluations.extend(
            evaluate_controls_for_technology(
                control_list,
                technology,
                user=user,
                asset_id=this_asset_id,
                application=profile.display_name,
                environment=profile.environment,
                executor=run_executor,
                pack=rp,
            )
        )

    profile_dict = {
        "application_id": profile.id,
        "application": profile.display_name,
        "environment": profile.environment,
        "cloud": profile.cloud,
    }
    return profile_dict, evaluations, assets_summary


def onboard_application(
    application_id: str,
    *,
    controls: list[str] | None = None,
    user: str = "system",
    executor: Executor | None = None,
    persist: bool = False,
    portfolio: dict[str, Any] | None = None,
    pack: RulePack | None = None,
) -> dict[str, Any]:
    """Run Common-Control evaluation for every asset of one application.

    ``application_id`` resolves against the existing application/CMDB
    portfolio config. Onboarding a brand-new application requires no code
    change — only a new ``applications:`` entry in
    ``config/phase2_application_portfolio.yaml`` (or an equivalent CMDB row),
    matching how the platform already onboards Phase-2 applications.
    """
    profile, evaluations, assets_summary = evaluate_application(
        application_id,
        controls=controls,
        user=user,
        executor=executor,
        persist=persist,
        portfolio=portfolio,
        pack=pack,
    )
    if profile is None:
        from modules.operations.engines.phase2_reusability import list_application_profiles

        return {
            "ok": False,
            "error": f"Unknown application '{application_id}' — not present in the application/CMDB portfolio.",
            "known_applications": sorted(p.id for p in list_application_profiles()),
        }

    report = build_implementation_report(
        evaluations, application=profile["application"], environment=profile["environment"]
    )
    report["ok"] = True
    report["application_id"] = profile["application_id"]
    report["cloud"] = profile["cloud"]
    report["assets"] = list(assets_summary.values())
    report["connectivity_pending"] = _connectivity_pending_controls(evaluations)
    return report


def onboard_assets(
    assets: list[Any],
    *,
    controls: list[str] | None = None,
    application: str = "",
    environment: str = "",
    user: str = "system",
    executor: Executor | None = None,
    persist: bool = False,
    pack: RulePack | None = None,
) -> dict[str, Any]:
    """Run Common-Control evaluation over an arbitrary discovered asset list.

    Use this entry point when assets come from
    :func:`modules.audit_intelligence.engines.asset_discovery.discover`
    (ServiceNow CMDB / manual import / enterprise GRC) instead of the Phase-2
    portfolio config.
    """
    rp = pack or load_rule_pack()
    control_list = controls or rp.controls()
    run_executor = executor or (make_executor(persist=True, scheduled=True) if persist else None)
    evaluations = evaluate_controls_for_assets(control_list, assets, user=user, executor=run_executor, pack=rp)
    report = build_implementation_report(evaluations, application=application, environment=environment)
    report["ok"] = True
    report["assets"] = [
        {
            "asset_id": a.asset_id if hasattr(a, "asset_id") else str(a.get("asset_id") or ""),
            "technology": a.technology if hasattr(a, "technology") else str(a.get("technology") or ""),
        }
        for a in assets
    ]
    report["connectivity_pending"] = _connectivity_pending_controls(evaluations)
    return report


#: Intake-form fields that name a technology, and the asset "role" they map to.
#: ``object_storage_location`` is deliberately excluded — it names a storage
#: backend (S3 / SharePoint / NAS), not a queryable predefined-query target.
_INTAKE_TECHNOLOGY_FIELDS: tuple[tuple[str, str], ...] = (
    ("database_technology", "db"),
    ("middleware_technology", "middleware"),
    ("os_technology", "os"),
)


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "app"


def onboard_from_intake_payload(
    payload: dict[str, Any],
    *,
    controls: list[str] | None = None,
    user: str = "system",
    executor: Executor | None = None,
    persist: bool = False,
    pack: RulePack | None = None,
) -> dict[str, Any]:
    """Evaluate reusable Common Controls from an Application Onboarding intake payload.

    Bridges the *existing* Application Onboarding intake form (see
    ``modules.operations.engines.onboarding_engine.simulate_onboarding`` —
    ``database_technology`` / ``middleware_technology`` / ``os_technology``
    fields, submitted by ``mvp_onboarding.html`` to
    ``POST /api/onboarding/simulate``) into the
    generic asset model :func:`evaluate_controls_for_assets` already
    understands. This is a second, thinner CMDB surface than the Phase-2
    application portfolio (``phase2_reusability.py``) — both already exist in
    the platform for different onboarding entry points; this function reuses
    the intake-form one specifically, since that is the payload the *existing*
    onboarding UI actually submits when app details are entered and onboarding
    starts.

    A technology field that is blank or doesn't canonicalize to a known
    predefined-query technology (see
    :func:`modules.audit_intelligence.engines.technology_fingerprint.fingerprint_asset`)
    is skipped, not guessed — onboarding always completes; it just evaluates
    fewer (or zero) controls when nothing recognizable was submitted.
    """
    from modules.audit_intelligence.engines.technology_fingerprint import fingerprint_asset
    from modules.audit_intelligence.models import Asset

    app_name = str(payload.get("application_name") or payload.get("application") or "").strip() or "New Application"
    environment = str(payload.get("environment") or "").strip()
    app_slug = _slugify(app_name)

    assets: list[Asset] = []
    for field_name, role in _INTAKE_TECHNOLOGY_FIELDS:
        raw_technology = str(payload.get(field_name) or "").strip()
        if not raw_technology:
            continue
        canonical = fingerprint_asset({"technology": raw_technology}).technology
        if not canonical or canonical == "Unknown":
            continue
        assets.append(
            Asset(
                asset_id=f"{app_slug}-{role}",
                technology=canonical,
                application=app_name,
                environment=environment,
                raw={"submitted_technology": raw_technology, "intake_field": field_name},
            )
        )

    rp = pack or load_rule_pack()
    control_list = controls or rp.controls()

    if not assets:
        report = build_implementation_report([], application=app_name, environment=environment)
        report["ok"] = True
        report["application"] = app_name
        report["environment"] = environment
        report["assets"] = []
        report["connectivity_pending"] = []
        report["note"] = "No recognized technology submitted — no reusable Common Controls evaluated."
        return report

    run_executor = executor or (make_executor(persist=True, scheduled=True) if persist else None)
    if run_executor is None and _demo_mode_enabled():
        # Preview-only evaluation (no explicit executor, not persisting) with
        # DEMO_MODE on: use deterministic mock evidence instead of attempting
        # a real database connection that has nothing to connect to in a demo
        # environment (see common_control_demo_fixtures.build_intake_demo_executor).
        # persist=True already takes the make_executor(...) branch above and
        # is untouched — this only replaces the "would otherwise be None"
        # preview path, never live/real-deployment execution.
        from modules.operations.engines.common_control_demo_fixtures import build_intake_demo_executor

        run_executor = build_intake_demo_executor()
    evaluations = evaluate_controls_for_assets(control_list, assets, user=user, executor=run_executor, pack=rp)
    report = build_implementation_report(evaluations, application=app_name, environment=environment)
    report["ok"] = True
    report["application"] = app_name
    report["environment"] = environment
    report["assets"] = [
        {"asset_id": a.asset_id, "technology": a.technology, "submitted_technology": a.raw.get("submitted_technology", "")}
        for a in assets
    ]
    report["connectivity_pending"] = _connectivity_pending_controls(evaluations)
    return report
