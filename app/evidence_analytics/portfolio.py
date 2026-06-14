"""Evidence Portfolio Analytics (Capability F, Phase 5.5).

Deterministic, non-LLM portfolio roll-ups for auditor/leadership personas
(application owner, functional head, vertical head, CIO). Computes measurable ROI
signals from existing evidence + observation metadata:

  * evidence_count, coverage_pct (mapped to a control/framework),
  * reuse_pct (evidence serving >1 control/framework),
  * staleness_pct (older than stale_after_days),
  * approval_sla_pct (approved within approval_sla_days of submit),
  * observation_count / observations_ready (closure-ready),
  * closure_forecast_days (deterministic: remaining blockers * days_per_blocker).

NEW FLAG: EVIDENCE_PORTFOLIO_ENABLED (default off). Read-only, fail-safe.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from app.evidence_analytics._common import age_days, flag_enabled, load_policy, merge_block
from app.evidence_analytics.models import PortfolioView

_DEFAULTS = {
    "stale_after_days": 90,
    "approval_sla_days": 14,
    "days_per_blocker": 7,
    "personas": ["application_owner", "functional_head", "vertical_head", "cio"],
}


def portfolio_enabled() -> bool:
    return flag_enabled("EVIDENCE_PORTFOLIO_ENABLED", "portfolio_enabled")


def _policy() -> dict[str, Any]:
    return merge_block(_DEFAULTS, {"portfolio": load_policy().get("portfolio", {})}, "portfolio")


def _pct(numer: int, denom: int) -> float:
    return round(100.0 * numer / denom, 1) if denom else 0.0


def _is_reused(row: Mapping[str, Any]) -> bool:
    if row.get("reused") is not None:
        return bool(row.get("reused"))
    controls = row.get("submitted_controls") or row.get("controls") or []
    frameworks = row.get("frameworks") or []
    if isinstance(controls, (list, tuple, set)) and len(controls) > 1:
        return True
    if isinstance(frameworks, (list, tuple, set)) and len(frameworks) > 1:
        return True
    return False


def _is_mapped(row: Mapping[str, Any]) -> bool:
    return bool(row.get("control") or row.get("control_id")
                or row.get("submitted_controls") or row.get("controls")
                or row.get("framework"))


def _is_stale(row: Mapping[str, Any], stale_after: float, now: datetime) -> bool:
    for key in ("collected_timestamp", "collected_at", "upload_date",
                "uploaded_at", "created_at", "timestamp"):
        if row.get(key):
            d = age_days(row.get(key), now=now)
            if d is not None:
                return d > stale_after
    return False


def _within_sla(row: Mapping[str, Any], sla_days: float) -> bool | None:
    submitted = row.get("submitted_at") or row.get("submitted_timestamp")
    approved = row.get("approved_at") or row.get("approved_timestamp")
    status = str(row.get("approval_status") or row.get("status") or "").lower()
    if status not in ("approved", "approve", "accepted"):
        return None
    from app.evidence_analytics._common import parse_dt
    s, a = parse_dt(submitted), parse_dt(approved)
    if s is None or a is None:
        return True  # approved but no timing data — count as met (neutral)
    return (a - s).total_seconds() / 86400.0 <= sla_days


def build_portfolio(persona: str, evidence_items: Sequence[Mapping[str, Any]] | None = None,
                    observations: Sequence[Mapping[str, Any]] | None = None, *,
                    scope_label: str = "", now: datetime | None = None,
                    force: bool = False) -> PortfolioView:
    """Compute a portfolio roll-up for a persona/scope. Never raises."""
    if not force and not portfolio_enabled():
        return PortfolioView(persona=persona, scope_label=scope_label, enabled=False,
                             note="portfolio disabled (EVIDENCE_PORTFOLIO_ENABLED=false)")
    try:
        now = now or datetime.now(timezone.utc)
        policy = _policy()
        stale_after = float(policy.get("stale_after_days", 90))
        sla_days = float(policy.get("approval_sla_days", 14))
        days_per_blocker = float(policy.get("days_per_blocker", 7))

        rows = [r for r in (evidence_items or []) if isinstance(r, Mapping)]
        obs = [o for o in (observations or []) if isinstance(o, Mapping)]
        n = len(rows)

        mapped = sum(1 for r in rows if _is_mapped(r))
        reused = sum(1 for r in rows if _is_reused(r))
        stale = sum(1 for r in rows if _is_stale(r, stale_after, now))
        sla_results = [_within_sla(r, sla_days) for r in rows]
        sla_eligible = [x for x in sla_results if x is not None]
        sla_met = sum(1 for x in sla_eligible if x)

        # Closure readiness reuses the 5.4 readiness engine (forced) when available.
        ready = 0
        remaining_blockers = 0
        try:
            from app.evidence_intel.readiness import assess_closure_readiness
            for o in obs:
                a = assess_closure_readiness(o, o.get("evidence_items"), now=now, force=True)
                if not a.blocking:
                    ready += 1
                remaining_blockers += len(a.blocking)
        except Exception:  # noqa: BLE001
            ready = 0
            remaining_blockers = 0

        forecast = round(remaining_blockers * days_per_blocker, 1)

        return PortfolioView(
            persona=persona, scope_label=scope_label, enabled=True,
            evidence_count=n,
            coverage_pct=_pct(mapped, n),
            reuse_pct=_pct(reused, n),
            staleness_pct=_pct(stale, n),
            approval_sla_pct=_pct(sla_met, len(sla_eligible)) if sla_eligible else 0.0,
            observation_count=len(obs),
            observations_ready=ready,
            closure_forecast_days=forecast)
    except Exception as exc:  # noqa: BLE001 - fail safe
        return PortfolioView(persona=persona, scope_label=scope_label, enabled=False,
                             note=f"portfolio error (ignored): {type(exc).__name__}")
