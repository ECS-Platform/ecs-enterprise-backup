"""Evidence Reuse & Observation Lifecycle — functional server-side service.

This service makes the *Evidence Reuse & Observation Lifecycle* page **execute
real server-side logic** instead of rendering static demo data. It is an
orchestration layer only — it **reuses** the existing engines and does **not**
duplicate evidence, validation, observation, mapping, or query logic:

  * evidence records      -> :mod:`modules.audit_intelligence.engines.evidence_repository`
  * control/framework map -> :mod:`modules.audit_intelligence.engines.technology_control_mapping`
  * observation engine    -> :mod:`modules.audit_intelligence.engines.observation_generation`
  * validation model      -> :class:`modules.audit_intelligence.models.ValidationResult`

Capabilities exposed to the UI/API (all read-only except the explicit
generate/close actions, which use the real observation workflow):

  * ``records``                — real evidence records with filters + integrity.
  * ``analyze``                — evidence-reuse matrix + reuse factor + effort saved.
  * ``validate_completeness``  — which control obligations are covered / missing / stale.
  * ``generate_observations``  — open observations for missing/failed/stale evidence
                                 via the existing observation engine (no duplicates).
  * ``check_closure``          — open observations now satisfied by passing evidence;
                                 advanced to *ready for closure* (never auto-closed
                                 when maker-checker approval is required).
  * ``readiness``              — covered vs total controls, per-framework readiness.
  * ``observations``           — current open + ready-for-closure observations.

Nothing here stores credentials/secrets. When the evidence repository is empty
(fresh process), :func:`ensure_seeded` populates it with the existing
deterministic story evidence via the real repository API, so the functional flow
always operates on genuine repository records rather than a parallel store.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from modules.audit_intelligence.engines import evidence_repository as repo
from modules.audit_intelligence.engines import observation_generation as obs
from modules.audit_intelligence.engines import technology_control_mapping as mapping
from modules.audit_intelligence.models import (
    CONTROL_STATUS_NON_COMPLIANT,
    OBS_STATUS_APPROVED,
    OBS_STATUS_DRAFT,
    OBS_STATUS_SUBMITTED,
    VERDICT_FAIL,
    VERDICT_PASS,
    VERDICT_WARNING,
    ValidationResult,
)

#: Manual evidence-collection effort avoided per reuse (hours). Matches the
#: existing story engine so the two views agree.
HOURS_PER_COLLECTION = 4

#: An evidence artifact older than this is treated as *stale* for readiness /
#: observation purposes.
STALE_AFTER_DAYS = 90

#: Verdicts that mean the control obligation is satisfied by this evidence.
_SATISFIED_VERDICTS = {VERDICT_PASS}
#: Verdicts that mean the obligation is NOT satisfied (opens an observation).
_FAILED_VERDICTS = {VERDICT_FAIL, VERDICT_WARNING}

#: Observation statuses considered "open" (not yet closed/rejected).
_OPEN_OBS_STATES = {OBS_STATUS_DRAFT, OBS_STATUS_SUBMITTED, OBS_STATUS_APPROVED}

#: Tag prefix used to carry an application label on stored evidence (the
#: EvidenceArtifact has no dedicated application field, so we use a tag).
_APP_TAG_PREFIX = "app:"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:  # noqa: BLE001
        return None


def _application_of(artifact_dict: dict[str, Any]) -> str:
    for tag in artifact_dict.get("tags", []):
        if isinstance(tag, str) and tag.startswith(_APP_TAG_PREFIX):
            return tag[len(_APP_TAG_PREFIX):]
    return artifact_dict.get("asset_id", "") or ""


def _is_stale(collected_at: str) -> bool:
    dt = _parse_ts(collected_at)
    if dt is None:
        return False
    return (_now() - dt) > timedelta(days=STALE_AFTER_DAYS)


def _satisfied(verdict: str) -> bool:
    return (verdict or "").upper() in _SATISFIED_VERDICTS


# --------------------------------------------------------------------------- #
# Seeding (fresh process) — uses the REAL repository API only.
# --------------------------------------------------------------------------- #
def ensure_seeded() -> int:
    """If the evidence repository is empty, seed it from the deterministic story
    evidence using the real repository API. Returns the number seeded.

    This does not fabricate a parallel store — it writes genuine
    :class:`EvidenceArtifact` records via ``evidence_repository.store_evidence``
    so every functional action operates on real repository data. Idempotent.
    """
    if repo.all_latest():
        return 0
    try:
        from modules.operations.engines.evidence_reuse_story_engine import (
            build_evidence_reuse_story,
        )

        story = build_evidence_reuse_story()
    except Exception:  # noqa: BLE001
        return 0

    seeded = 0
    for e in story.get("evidence", []):
        verdict = VERDICT_PASS if e.get("satisfied") else VERDICT_FAIL
        control_status = "Compliant" if e.get("satisfied") else CONTROL_STATUS_NON_COMPLIANT
        repo.store_evidence(
            control_id=e.get("control_id", ""),
            content=e.get("result", ""),
            technology=e.get("technology", ""),
            asset_id=e.get("application", ""),
            frameworks=tuple(e.get("frameworks", [])),
            verdict=verdict,
            control_status=control_status,
            evidence_quality=1.0 if e.get("satisfied") else 0.2,
            source=e.get("source", "story-seed"),
            tags=(f"{_APP_TAG_PREFIX}{e.get('application', '')}", "seed:story"),
        )
        seeded += 1
    return seeded


# --------------------------------------------------------------------------- #
# 1. Evidence retrieval (real repository + filters + integrity)
# --------------------------------------------------------------------------- #
def records(
    *,
    application: str = "",
    framework: str = "",
    control: str = "",
    technology: str = "",
    status: str = "",
    date_from: str = "",
    date_to: str = "",
    seed_if_empty: bool = True,
) -> dict[str, Any]:
    """Return real evidence records (latest version each) with the given filters.

    ``status`` matches the evidence verdict (PASS/FAIL/WARNING) case-insensitively.
    ``date_from``/``date_to`` are ISO dates (inclusive) compared to ``collected_at``.
    Each record carries an ``integrity`` block (hash present + verified).
    """
    if seed_if_empty:
        ensure_seeded()

    # Use the repository's own search for the filters it supports natively.
    artifacts = repo.search(
        technology=technology or "",
        framework=framework or "",
        latest_only=True,
    )
    df = _parse_ts(date_from + "T00:00:00+00:00") if date_from else None
    dt_to = _parse_ts(date_to + "T23:59:59+00:00") if date_to else None
    status_l = (status or "").strip().lower()
    control_l = (control or "").strip().lower()
    app_l = (application or "").strip().lower()

    out: list[dict[str, Any]] = []
    for a in artifacts:
        d = a.to_dict()
        app = _application_of(d)
        if control_l and control_l not in d.get("control_id", "").lower():
            continue
        if app_l and app_l not in app.lower():
            continue
        if status_l and status_l != (d.get("verdict", "") or "").lower():
            continue
        collected = _parse_ts(d.get("collected_at", ""))
        if df and collected and collected < df:
            continue
        if dt_to and collected and collected > dt_to:
            continue
        d["application"] = app
        d["stale"] = _is_stale(d.get("collected_at", ""))
        d["satisfied"] = _satisfied(d.get("verdict", ""))
        d["integrity"] = _integrity_of(a)
        out.append(d)

    out.sort(key=lambda r: r.get("collected_at", ""), reverse=True)
    return {"ok": True, "count": len(out), "records": out,
            "filters_applied": {
                "application": application, "framework": framework, "control": control,
                "technology": technology, "status": status,
                "date_from": date_from, "date_to": date_to}}


def _integrity_of(artifact: Any) -> dict[str, Any]:
    """Integrity status for one artifact: hash present + checksum consistency."""
    content_hash = getattr(artifact, "content_hash", "") or ""
    checksum = getattr(artifact, "checksum", "") or ""
    has_hash = bool(content_hash)
    # The repository derives checksum as the first 8 chars of the sha256; a
    # consistent checksum confirms the stored hash/checksum pair is intact.
    consistent = has_hash and content_hash.startswith(checksum) if checksum else has_hash
    return {
        "has_hash": has_hash,
        "algorithm": "sha256" if has_hash else "",
        "content_hash": content_hash,
        "checksum": checksum,
        "verified": bool(has_hash and consistent),
        "status": "verified" if (has_hash and consistent) else ("unverified" if has_hash else "no-hash"),
    }


# --------------------------------------------------------------------------- #
# 2. Evidence reuse analysis
# --------------------------------------------------------------------------- #
def analyze(**filters: str) -> dict[str, Any]:
    """Compute the evidence-reuse matrix + summary over the filtered records.

    Reuse is measured by how many framework obligations a single evidence record
    satisfies. Frameworks come from the evidence's own ``frameworks`` (falling
    back to the control->framework mapping when absent).
    """
    data = records(**filters)
    recs = data["records"]

    rows: list[dict[str, Any]] = []
    frameworks_covered: set[str] = set()
    controls_covered: set[str] = set()
    obligations = 0
    per_evidence: dict[str, int] = {}

    for r in recs:
        fws = r.get("frameworks") or mapping.frameworks_for_control(r.get("control_id", ""))
        controls_covered.add(r.get("control_id", ""))
        for fw in fws:
            obligations += 1
            frameworks_covered.add(fw)
            per_evidence[r["evidence_key"]] = per_evidence.get(r["evidence_key"], 0) + 1
            rows.append({
                "evidence_key": r["evidence_key"],
                "control_id": r.get("control_id", ""),
                "technology": r.get("technology", ""),
                "application": r.get("application", ""),
                "framework": fw,
                "status": "Satisfied" if r.get("satisfied") else "Violation",
                "verdict": r.get("verdict", ""),
            })

    unique_evidence = len(recs)
    collections_saved = max(obligations - unique_evidence, 0)
    top_reused = sorted(per_evidence.items(), key=lambda kv: kv[1], reverse=True)[:5]

    summary = {
        "unique_evidence": unique_evidence,
        "reuse_count": obligations,
        "reuse_factor": round(obligations / unique_evidence, 2) if unique_evidence else 0.0,
        "frameworks_covered": len(frameworks_covered),
        "frameworks_list": sorted(frameworks_covered),
        "controls_covered": len(controls_covered),
        "collections_saved": collections_saved,
        "effort_saved_hours": collections_saved * HOURS_PER_COLLECTION,
        "most_reused": [{"evidence_key": k, "obligations": v} for k, v in top_reused],
    }
    return {"ok": True, "reuse_summary": summary, "reuse_rows": rows,
            "filters_applied": data["filters_applied"]}


# --------------------------------------------------------------------------- #
# 3. Completeness validation + audit readiness
# --------------------------------------------------------------------------- #
def _obligation_scope(recs: list[dict[str, Any]], *,
                      full_catalog: bool = False) -> dict[str, list[str]]:
    """framework -> sorted list of control_ids that are in scope for readiness.

    Two modes:

    * **Evidence-driven (default):** obligations are the controls we actually have
      evidence for, evaluated across each framework that evidence claims. This is
      the meaningful default for the page (no overwhelming catalog-wide gaps).
    * **Full-catalog (``full_catalog=True``):** for each framework present on the
      evidence, expand to every catalog control mapped to that framework (a wider,
      audit-scoping view).
    """
    frameworks: set[str] = set()
    controls_with_evidence: set[str] = set()
    fw_to_evidence_controls: dict[str, set[str]] = {}
    for r in recs:
        cid = r.get("control_id", "")
        controls_with_evidence.add(cid)
        for fw in (r.get("frameworks") or mapping.frameworks_for_control(cid)):
            frameworks.add(fw)
            fw_to_evidence_controls.setdefault(fw, set()).add(cid)

    scope: dict[str, list[str]] = {}
    for fw in sorted(frameworks):
        if full_catalog:
            ctrl_ids = sorted({c.control_id for c in mapping.controls_for_framework(fw)})
            if not ctrl_ids:
                ctrl_ids = sorted(fw_to_evidence_controls.get(fw, set()))
        else:
            ctrl_ids = sorted(fw_to_evidence_controls.get(fw, set()))
        scope[fw] = ctrl_ids
    return scope


def validate_completeness(*, full_catalog: bool = False, **filters: str) -> dict[str, Any]:
    """Report, per framework, which control obligations are covered / missing / stale.

    "Covered" = latest evidence exists for the control AND its verdict is
    satisfied AND it is not stale. Missing/failed/stale are called out so they can
    be turned into observations. By default the scope is evidence-driven; pass
    ``full_catalog=True`` for the wider catalog-scoped view.
    """
    data = records(**filters)
    recs = data["records"]
    by_control = {r.get("control_id", ""): r for r in recs}
    scope = _obligation_scope(recs, full_catalog=full_catalog)

    frameworks_out: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    covered_total = 0
    obligations_total = 0

    for fw, ctrl_ids in scope.items():
        fw_controls: list[dict[str, Any]] = []
        for cid in ctrl_ids:
            obligations_total += 1
            rec = by_control.get(cid)
            if rec is None:
                state, reason = "missing", "No evidence collected for this control."
            elif rec.get("stale"):
                state, reason = "stale", f"Evidence older than {STALE_AFTER_DAYS} days."
            elif rec.get("satisfied"):
                state, reason = "covered", ""
            else:
                state, reason = "failed", "Evidence present but control not satisfied."
            if state == "covered":
                covered_total += 1
            else:
                gaps.append({"framework": fw, "control_id": cid, "state": state,
                             "reason": reason,
                             "evidence_key": (rec or {}).get("evidence_key", ""),
                             "technology": (rec or {}).get("technology", ""),
                             "application": (rec or {}).get("application", "")})
            fw_controls.append({
                "control_id": cid,
                "control_name": _control_name(cid),
                "state": state,
                "reason": reason,
                "evidence_key": (rec or {}).get("evidence_key", ""),
                "verdict": (rec or {}).get("verdict", ""),
            })
        covered = sum(1 for c in fw_controls if c["state"] == "covered")
        frameworks_out.append({
            "framework": fw,
            "covered": covered,
            "total": len(fw_controls),
            "readiness_pct": round(100 * covered / len(fw_controls), 1) if fw_controls else 0.0,
            "controls": fw_controls,
        })

    return {
        "ok": True,
        "complete": len(gaps) == 0,
        "covered_controls": covered_total,
        "total_controls": obligations_total,
        "readiness_pct": round(100 * covered_total / obligations_total, 1) if obligations_total else 0.0,
        "by_framework": frameworks_out,
        "gaps": gaps,
        "gap_count": len(gaps),
        "filters_applied": data["filters_applied"],
    }


def readiness(*, full_catalog: bool = False, **filters: str) -> dict[str, Any]:
    """Audit readiness = covered vs total controls, per framework (from real evidence)."""
    comp = validate_completeness(full_catalog=full_catalog, **filters)
    return {
        "ok": True,
        "covered_controls": comp["covered_controls"],
        "total_controls": comp["total_controls"],
        "readiness_pct": comp["readiness_pct"],
        "by_framework": [{k: v for k, v in fw.items() if k != "controls"}
                         for fw in comp["by_framework"]],
        "gap_count": comp["gap_count"],
        "filters_applied": comp["filters_applied"],
    }


def _control_name(control_id: str) -> str:
    ref = mapping.get_control(control_id)
    return ref.control_name if ref else control_id


# --------------------------------------------------------------------------- #
# 4. Observation creation (uses the REAL observation engine)
# --------------------------------------------------------------------------- #
def _existing_open_for(control_id: str, framework: str) -> Optional[Any]:
    for o in obs.list_observations():
        if o.control_id == control_id and o.status in _OPEN_OBS_STATES:
            if not framework or framework in o.frameworks:
                return o
    return None


def generate_observations(*, full_catalog: bool = False, **filters: str) -> dict[str, Any]:
    """Create/open observations for missing, failed, or stale control obligations.

    Uses :func:`observation_generation.generate_observation` (the real engine and
    store). De-duplicates: an obligation that already has an open observation is
    skipped rather than re-created.
    """
    comp = validate_completeness(full_catalog=full_catalog, **filters)
    created: list[dict[str, Any]] = []
    skipped_existing = 0

    for gap in comp["gaps"]:
        cid = gap["control_id"]
        fw = gap["framework"]
        if _existing_open_for(cid, fw) is not None:
            skipped_existing += 1
            continue
        frameworks = tuple(mapping.frameworks_for_control(cid) or [fw])
        # Missing/stale -> WARNING (needs collection); failed -> FAIL.
        if gap["state"] == "failed":
            verdict, rationale = VERDICT_FAIL, gap["reason"]
        else:
            verdict, rationale = VERDICT_WARNING, gap["reason"]
        vr = ValidationResult(
            control_id=cid,
            technology=gap.get("technology", ""),
            verdict=verdict,
            control_status=CONTROL_STATUS_NON_COMPLIANT,
            evidence_quality=0.0 if gap["state"] == "missing" else 0.2,
            rule_id="reuse.completeness",
            rationale=rationale,
            frameworks=frameworks,
        )
        observation = obs.generate_observation(
            vr,
            owner="",
            evidence_reference=gap.get("evidence_key", ""),
            control_name=_control_name(cid),
        )
        if observation:
            created.append(observation.to_dict())

    return {
        "ok": True,
        "created_count": len(created),
        "created": created,
        "skipped_existing": skipped_existing,
        "gap_count": comp["gap_count"],
    }


# --------------------------------------------------------------------------- #
# 5. Closure eligibility (advance workflow, never auto-close if approval needed)
# --------------------------------------------------------------------------- #
def check_closure(*, require_approval: bool = True, user: str = "system",
                  seed_if_empty: bool = True, **filters: str) -> dict[str, Any]:
    """Advance open observations that are now satisfied by passing evidence.

    An open observation is *closure-eligible* when the latest evidence for its
    control now satisfies it. Such observations are moved toward closure through
    the existing workflow:

      * If ``require_approval`` (maker-checker) is True: advance no further than
        the point where a checker must approve, and mark **READY FOR CLOSURE** —
        the observation is **not** auto-closed.
      * The audit trail (observation ``history``) is preserved by the engine's
        ``transition`` at every step.
    """
    data = records(seed_if_empty=seed_if_empty, **filters)
    satisfied_controls = {r.get("control_id", ""): r for r in data["records"]
                          if r.get("satisfied")}

    ready: list[dict[str, Any]] = []
    closed: list[dict[str, Any]] = []
    not_eligible: list[dict[str, Any]] = []

    for o in obs.list_observations():
        if o.status not in _OPEN_OBS_STATES:
            continue
        rec = satisfied_controls.get(o.control_id)
        if rec is None:
            not_eligible.append({"observation_id": o.observation_id,
                                 "control_id": o.control_id, "status": o.status,
                                 "reason": "No satisfying evidence yet."})
            continue
        try:
            info = _advance_toward_closure(o.observation_id,
                                           require_approval=require_approval, user=user)
        except Exception as exc:  # noqa: BLE001
            not_eligible.append({"observation_id": o.observation_id,
                                 "control_id": o.control_id, "status": o.status,
                                 "reason": f"transition_error: {type(exc).__name__}"})
            continue
        entry = {
            "observation_id": o.observation_id,
            "control_id": o.control_id,
            "control_name": _control_name(o.control_id),
            "evidence_used": rec.get("evidence_key", ""),
            "framework_covered": ", ".join(o.frameworks),
            "status": info["status"],
            "ready_for_closure": info["ready_for_closure"],
        }
        if info["closed"]:
            closed.append(entry)
        else:
            ready.append(entry)

    return {
        "ok": True,
        "require_approval": require_approval,
        "ready_for_closure": ready,
        "ready_count": len(ready),
        "closed": closed,
        "closed_count": len(closed),
        "not_eligible": not_eligible,
    }


def _advance_toward_closure(obs_id: str, *, require_approval: bool,
                            user: str) -> dict[str, Any]:
    """Move an observation through the existing workflow toward closure.

    Workflow: Draft -> Submitted -> Approved -> Remediated -> Closed.
    With maker-checker (require_approval=True) we stop at **Submitted** (a checker
    must Approve), marking the item READY FOR CLOSURE without closing it.
    Without approval gating we complete the chain to Closed.
    """
    from modules.audit_intelligence.models import (
        OBS_STATUS_CLOSED,
        OBS_STATUS_REMEDIATED,
    )

    o = obs.get_observation(obs_id)
    if o is None:
        raise KeyError(obs_id)

    if require_approval:
        # Maker submits; a checker must approve -> mark ready, do NOT close.
        if o.status == OBS_STATUS_DRAFT:
            obs.transition(obs_id, OBS_STATUS_SUBMITTED, user=user,
                           note="Auto-submitted: satisfying evidence detected (awaiting checker approval).")
        o = obs.get_observation(obs_id)
        return {"status": o.status, "ready_for_closure": True, "closed": False}

    # No approval gate: advance fully to Closed.
    order = [OBS_STATUS_DRAFT, OBS_STATUS_SUBMITTED, OBS_STATUS_APPROVED,
             OBS_STATUS_REMEDIATED, OBS_STATUS_CLOSED]
    next_after = {
        OBS_STATUS_DRAFT: OBS_STATUS_SUBMITTED,
        OBS_STATUS_SUBMITTED: OBS_STATUS_APPROVED,
        OBS_STATUS_APPROVED: OBS_STATUS_REMEDIATED,
        OBS_STATUS_REMEDIATED: OBS_STATUS_CLOSED,
    }
    guard = 0
    while o.status in next_after and guard < len(order):
        obs.transition(obs_id, next_after[o.status], user=user,
                       note="Auto-closure: satisfying evidence detected.")
        o = obs.get_observation(obs_id)
        guard += 1
    return {"status": o.status, "ready_for_closure": o.status == OBS_STATUS_CLOSED,
            "closed": o.status == OBS_STATUS_CLOSED}


# --------------------------------------------------------------------------- #
# 6. Observation views
# --------------------------------------------------------------------------- #
def observations() -> dict[str, Any]:
    """Current open + ready-for-closure observations from the real engine."""
    all_obs = [o.to_dict() for o in obs.list_observations()]
    open_obs = [o for o in all_obs if o["status"] in _OPEN_OBS_STATES]
    ready = [o for o in all_obs if o["status"] == OBS_STATUS_SUBMITTED]
    return {
        "ok": True,
        "open": open_obs,
        "open_count": len(open_obs),
        "ready_for_closure": ready,
        "ready_count": len(ready),
        "summary": obs.summary(),
    }


# --------------------------------------------------------------------------- #
# Page context (server-rendered initial state)
# --------------------------------------------------------------------------- #
def page_context(**filters: str) -> dict[str, Any]:
    """Full initial state for the server-rendered page (real data)."""
    ensure_seeded()
    rec = records(**filters)
    ana = analyze(**filters)
    comp = validate_completeness(**filters)
    return {
        "ok": True,
        "records": rec["records"],
        "record_count": rec["count"],
        "reuse_summary": ana["reuse_summary"],
        "reuse_rows": ana["reuse_rows"],
        "readiness": {
            "covered_controls": comp["covered_controls"],
            "total_controls": comp["total_controls"],
            "readiness_pct": comp["readiness_pct"],
            "by_framework": comp["by_framework"],
        },
        "observations": observations(),
        "filters_applied": rec["filters_applied"],
    }
