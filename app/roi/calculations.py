"""ROI core calculations — deterministic, non-LLM.

Every output is a pure function of RoiInputs + Assumptions. No randomness, no time
dependence, no I/O. The same inputs always produce the same outputs (audit-friendly).

Formulas (all assumptions configurable in config/roi.yaml):

  observations_total      = observations_closed + observations_prevented
  email_hours_saved       = observations_total * emails_per_observation
                            * email_reduction_pct * hours_per_email
  observation_hours_saved = observations_closed * hours_per_observation
                            * observation_effort_reduction_pct
  prevention_hours_saved  = observations_prevented * hours_per_observation
  reuse_hours_saved       = evidence_reused * reuse_hours_saved_each
  audit_hours_saved       = audits_completed * hours_per_audit
                            * audit_effort_reduction_pct
  framework_hours_saved   = frameworks_onboarded * hours_per_framework_onboarding
                            * framework_onboarding_reduction_pct
  hours_saved             = sum of the above
  days_saved              = hours_saved / 8
  emails_avoided          = observations_total * emails_per_observation
                            * email_reduction_pct
  fte_equivalent          = hours_saved / working_hours_per_fte_year
  cost_savings            = hours_saved * cost_per_hour
  investment              = applications_onboarded * cost_per_app_per_year
  net_value               = cost_savings - investment
  roi_pct                 = (net_value / investment) * 100      (0 if investment 0)
  risk_reduction_pct      = min(max_reduction, apps * per_app_reduction_pct * 100)
"""

from __future__ import annotations

from app.roi.assumptions import Assumptions
from app.roi.models import RoiInputs, RoiResult, Mode, format_inr

_HOURS_PER_DAY = 8.0


def _round(x: float, n: int = 1) -> float:
    try:
        return round(float(x), n)
    except (TypeError, ValueError):
        return 0.0


def email_hours_saved(obs_total: float, a: Assumptions) -> float:
    return (obs_total * a.emails_per_observation * a.email_reduction_pct
            * a.hours_per_email)


def emails_avoided(obs_total: float, a: Assumptions) -> float:
    return obs_total * a.emails_per_observation * a.email_reduction_pct


def observation_hours_saved(obs_closed: float, a: Assumptions) -> float:
    return obs_closed * a.hours_per_observation * a.observation_effort_reduction_pct


def prevention_hours_saved(obs_prevented: float, a: Assumptions) -> float:
    return obs_prevented * a.hours_per_observation


def reuse_hours_saved(evidence_reused: float, a: Assumptions) -> float:
    return evidence_reused * a.reuse_hours_saved_each


def audit_hours_saved(audits: float, a: Assumptions) -> float:
    return audits * a.hours_per_audit * a.audit_effort_reduction_pct


def framework_hours_saved(frameworks: float, a: Assumptions) -> float:
    return (frameworks * a.hours_per_framework_onboarding
            * a.framework_onboarding_reduction_pct)


def risk_reduction_pct(applications: float, a: Assumptions) -> float:
    return min(a.max_reduction_pct, applications * a.per_app_reduction_pct * 100.0)


def calculate_roi(inputs: RoiInputs, a: Assumptions, *,
                  mode: str = Mode.PROJECTED.value) -> RoiResult:
    """Compute the full ROI result for the given inputs. Never raises."""
    try:
        obs_total = inputs.observations_closed + inputs.observations_prevented

        h_email = email_hours_saved(obs_total, a)
        h_obs = observation_hours_saved(inputs.observations_closed, a)
        h_prev = prevention_hours_saved(inputs.observations_prevented, a)
        h_reuse = reuse_hours_saved(inputs.evidence_reused, a)
        h_audit = audit_hours_saved(inputs.audits_completed, a)
        h_fw = framework_hours_saved(inputs.frameworks_onboarded, a)

        hours = h_email + h_obs + h_prev + h_reuse + h_audit + h_fw
        days = hours / _HOURS_PER_DAY if _HOURS_PER_DAY else 0.0
        mails = emails_avoided(obs_total, a)
        fte = hours / a.working_hours_per_fte_year if a.working_hours_per_fte_year else 0.0

        # Cost savings: anchored to the configured ₹/25-apps baseline (board-credible),
        # taking the higher of the activity-hours value and the anchor so detailed
        # operational savings are never under-counted. Both are configurable.
        activity_cost = hours * a.cost_per_hour
        anchor_cost = inputs.applications_onboarded * a.baseline_cost_per_app()
        cost = max(activity_cost, anchor_cost)
        investment = inputs.applications_onboarded * a.cost_per_app_per_year
        net = cost - investment
        roi = (net / investment * 100.0) if investment else 0.0
        risk = risk_reduction_pct(inputs.applications_onboarded, a)

        return RoiResult(
            mode=mode, enabled=True, applications=int(inputs.applications_onboarded),
            hours_saved=_round(hours), days_saved=_round(days),
            emails_avoided=_round(mails), fte_equivalent=_round(fte, 2),
            cost_savings=_round(cost, 0), investment=_round(investment, 0),
            net_value=_round(net, 0), risk_reduction_pct=_round(risk, 1),
            roi_pct=_round(roi, 1),
            cost_savings_display=format_inr(cost, symbol=a.symbol, lakh=a.lakh, crore=a.crore),
            net_value_display=format_inr(net, symbol=a.symbol, lakh=a.lakh, crore=a.crore),
        )
    except Exception as exc:  # noqa: BLE001 - fail safe
        return RoiResult(mode=mode, enabled=False,
                         note=f"roi calc error (ignored): {type(exc).__name__}")


def projected_inputs_for_apps(applications: int, a: Assumptions) -> RoiInputs:
    """Derive projected activity volumes from app count using assumptions.

    Deterministic mapping used for projected mode & storyboard screens.
    """
    apps = max(0, int(applications))
    obs_total = apps * a.observations_per_application
    prevented = obs_total * a.observation_prevention_pct
    closed = obs_total - prevented
    # Evidence: ~ one artifact per observation closed, reused reuse_factor times.
    submitted = closed
    reused = submitted * a.evidence_reuse_factor
    # Frameworks scale with portfolio (cap at configured framework list length or 6).
    frameworks = min(len(a.frameworks) or 6, max(1, apps // 100 + 1)) if apps else 0
    # One audit cycle per ~50 apps.
    audits = apps / 50.0
    return RoiInputs(
        applications_onboarded=apps,
        frameworks_onboarded=int(frameworks),
        observations_closed=closed,
        observations_prevented=prevented,
        evidence_submitted=submitted,
        evidence_approved=submitted,
        evidence_reused=reused,
        audits_completed=audits,
    )


def calculate_projected(applications: int, a: Assumptions) -> RoiResult:
    return calculate_roi(projected_inputs_for_apps(applications, a), a,
                         mode=Mode.PROJECTED.value)
