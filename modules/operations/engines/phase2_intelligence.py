"""Phase-2 evidence intelligence — completeness, reuse gates, quality, summaries, leadership.

Reuses existing ECS services (repository, SHA-256 duplicates, reuse scoring,
LLM provider abstraction, Common Controls validation). No second RAG/LLM pipeline
and no application-specific collectors.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from modules.audit_intelligence.services.evidence_reuse_service import STALE_AFTER_DAYS
from modules.operations.engines import evidence_repository as ops_repo
from modules.operations.engines.common_controls_catalog import by_slug
from modules.operations.engines.phase2_reusability import (
    ApplicationProfile,
    list_application_profiles,
    load_application_portfolio,
    phase2_control_slugs,
    select_technologies_for_control,
)

PHASE2_CONTROLS_DEFAULT = (
    "encryption-at-rest",
    "encryption-in-transit",
    "secure-configuration",
    "identity-privileged-access",
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value: str) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:  # noqa: BLE001
        return None


def _is_stale(collected_at: str, *, now: datetime | None = None, stale_days: int = STALE_AFTER_DAYS) -> bool:
    dt = _parse_ts(collected_at)
    if dt is None:
        return False
    return ((now or _now()) - dt) > timedelta(days=int(stale_days))


def required_bindings(
    *,
    portfolio: dict[str, Any] | None = None,
    application_ids: list[str] | None = None,
    control_slugs: list[str] | None = None,
) -> list[dict[str, str]]:
    """Required Phase-2 evidence bindings from portfolio config (deterministic)."""
    data = portfolio or load_application_portfolio()
    apps = list_application_profiles(data)
    if application_ids is not None:
        want = set(application_ids)
        apps = [a for a in apps if a.id in want]
    controls = list(control_slugs) if control_slugs is not None else phase2_control_slugs(data)
    out: list[dict[str, str]] = []
    for app in apps:
        for slug in controls:
            ctrl = by_slug(slug)
            for tech in select_technologies_for_control(app, slug, portfolio=data):
                out.append(
                    {
                        "application_id": app.id,
                        "application": app.display_name,
                        "environment": app.environment,
                        "asset_id": app.asset_for_technology(tech),
                        "technology": tech,
                        "control_slug": slug,
                        "control_id": ctrl.control_id if ctrl else f"CC-{slug.upper().replace('-', '_')}",
                    }
                )
    return out


def _ops_phase2_records() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rec in ops_repo.evidence_repository:
        meta = dict(rec.get("metadata") or {})
        if meta.get("collection_source") != "CommonControls" and rec.get("source_connector") != "common_controls":
            continue
        if meta.get("phase") != "phase2" and not meta.get("application_id"):
            # Allow Phase-2 stamped rows even if phase key absent (legacy stamps).
            if not meta.get("common_control_slug"):
                continue
        rows.append(rec)
    return rows


def _match_record(binding: dict[str, str], rec: dict[str, Any]) -> bool:
    meta = dict(rec.get("metadata") or {})
    app = str(meta.get("application") or (rec.get("application_tags") or [""])[0] or "")
    slug = str(meta.get("common_control_slug") or "")
    tech = str(meta.get("technology") or "")
    return (
        app == binding["application"]
        and slug == binding["control_slug"]
        and tech == binding["technology"]
    )


def assess_completeness(
    *,
    portfolio: dict[str, Any] | None = None,
    application_ids: list[str] | None = None,
    control_slugs: list[str] | None = None,
    now: datetime | None = None,
    stale_days: int = STALE_AFTER_DAYS,
) -> dict[str, Any]:
    """Compare required bindings vs available evidence → COMPLETE/MISSING/STALE."""
    bindings = required_bindings(
        portfolio=portfolio, application_ids=application_ids, control_slugs=control_slugs
    )
    records = _ops_phase2_records()
    clock = now or _now()
    results: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for binding in bindings:
        matches = [r for r in records if _match_record(binding, r)]
        if not matches:
            row = {**binding, "status": "MISSING", "evidence_id": "", "reason": "No evidence for binding"}
            results.append(row)
            missing.append(row)
            continue
        # Prefer newest by uploaded_at
        matches.sort(key=lambda r: str(r.get("uploaded_at") or ""), reverse=True)
        rec = matches[0]
        meta = dict(rec.get("metadata") or {})
        collected = str(rec.get("uploaded_at") or meta.get("collected_at") or "")
        verdict = str(meta.get("validation_verdict") or "").upper()
        if _is_stale(collected, now=clock, stale_days=stale_days):
            status = "STALE"
            reason = f"Evidence older than {stale_days} days"
            missing.append({**binding, "status": status, "evidence_id": rec.get("evidence_id", ""), "reason": reason})
        elif verdict in {"FAIL", "WARNING"}:
            status = "MISSING"
            reason = f"Validation {verdict or 'unknown'} — requirement not satisfied"
            missing.append({**binding, "status": status, "evidence_id": rec.get("evidence_id", ""), "reason": reason})
        else:
            status = "COMPLETE"
            reason = "Current evidence present with acceptable validation"
        results.append(
            {
                **binding,
                "status": status,
                "evidence_id": rec.get("evidence_id", ""),
                "verdict": verdict or "PASS",
                "collected_at": collected,
                "reason": reason,
            }
        )
    complete = sum(1 for r in results if r["status"] == "COMPLETE")
    return {
        "ok": True,
        "total_bindings": len(bindings),
        "complete": complete,
        "missing": sum(1 for r in results if r["status"] == "MISSING"),
        "stale": sum(1 for r in results if r["status"] == "STALE"),
        "status": "COMPLETE" if not missing else ("STALE" if all(r["status"] == "STALE" for r in missing) else "MISSING"),
        "bindings": results,
        "missing_requirements": missing,
    }


def assess_reuse_eligibility(
    candidate: Mapping[str, Any],
    requirement: Mapping[str, Any],
    *,
    now: datetime | None = None,
    stale_days: int = STALE_AFTER_DAYS,
) -> dict[str, Any]:
    """Gate reuse suggestions: SHA-256 exact match or scored similarity with applicability rules.

    Similarity alone never implies compliance equivalence.
    """
    clock = now or _now()
    cand_meta = dict(candidate.get("metadata") or {})
    req_meta = dict(requirement.get("metadata") or requirement)
    cand_hash = str(candidate.get("sha256") or cand_meta.get("content_sha256") or "")
    req_hash = str(requirement.get("sha256") or req_meta.get("content_sha256") or "")
    reasons: list[str] = []

    exact = bool(cand_hash and req_hash and cand_hash == req_hash)
    if exact:
        reasons.append("exact_sha256_match")

    # Applicability gates
    same_control = (
        str(cand_meta.get("common_control_slug") or candidate.get("control") or "")
        == str(req_meta.get("common_control_slug") or requirement.get("control_slug") or requirement.get("control") or "")
    )
    same_app = str(cand_meta.get("application") or "") == str(
        req_meta.get("application") or requirement.get("application") or ""
    )
    env_ok = str(cand_meta.get("environment") or "") == str(
        req_meta.get("environment") or requirement.get("environment") or cand_meta.get("environment") or ""
    )
    collected = str(candidate.get("uploaded_at") or cand_meta.get("collected_at") or "")
    fresh = not _is_stale(collected, now=clock, stale_days=stale_days)
    verdict = str(cand_meta.get("validation_verdict") or "").upper()
    validation_ok = verdict in {"", "PASS"}

    similarity_score = 0.0
    try:
        from app.evidence_intel.reuse import score_reuse

        scored = score_reuse(dict(requirement), dict(candidate), now=clock, force=True)
        similarity_score = float(getattr(scored, "score", 0.0) or 0.0)
        reasons.append(f"similarity_score={similarity_score:.1f}")
    except Exception:  # noqa: BLE001
        reasons.append("similarity_unavailable")

    applicable = same_control and env_ok and fresh and validation_ok
    # Cross-app reuse is suggestion-only and never compliance-equivalent.
    eligible = exact or (applicable and same_app and similarity_score >= 40.0)
    compliance_equivalent = exact and applicable and same_app and validation_ok

    if not same_control:
        reasons.append("control_mismatch")
    if not fresh:
        reasons.append("stale_candidate")
    if not validation_ok:
        reasons.append(f"validation_{verdict or 'unknown'}")
    if same_app:
        reasons.append("same_application")
    else:
        reasons.append("cross_application_not_compliance_equivalent")

    return {
        "ok": True,
        "eligible": bool(eligible),
        "exact_duplicate": exact,
        "compliance_equivalent": bool(compliance_equivalent),
        "similarity_score": similarity_score,
        "same_control": same_control,
        "same_application": same_app,
        "fresh": fresh,
        "reasons": reasons,
        "note": "Similarity alone never implies compliance equivalence.",
    }


def score_evidence_quality(record: Mapping[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Deterministic quality score from metadata completeness, freshness, validation, integrity, source."""
    clock = now or _now()
    meta = dict(record.get("metadata") or {})
    components: dict[str, Any] = {}
    reasons: list[str] = []

    required_meta = ("application", "environment", "asset_id", "technology", "common_control_slug", "validation_verdict")
    present = sum(1 for k in required_meta if meta.get(k) or (k == "application" and (record.get("application_tags") or [None])[0]))
    meta_score = round(100.0 * present / len(required_meta), 1)
    components["metadata_completeness"] = meta_score
    reasons.append(f"metadata {present}/{len(required_meta)} fields")

    collected = str(record.get("uploaded_at") or meta.get("collected_at") or "")
    if not collected:
        fresh_score = 40.0
        reasons.append("missing_collected_at")
    elif _is_stale(collected, now=clock):
        fresh_score = 25.0
        reasons.append("stale_evidence")
    else:
        fresh_score = 100.0
        reasons.append("fresh_evidence")
    components["freshness"] = fresh_score

    verdict = str(meta.get("validation_verdict") or "").upper()
    if verdict == "PASS":
        val_score = 100.0
    elif verdict == "WARNING":
        val_score = 60.0
    elif verdict == "FAIL":
        val_score = 20.0
    else:
        val_score = 50.0
    components["validation_result"] = val_score
    reasons.append(f"validation={verdict or 'UNKNOWN'}")

    sha = str(record.get("sha256") or meta.get("content_sha256") or "")
    integrity_ok = bool(sha) and bool(record.get("integrity_valid", True))
    integrity_score = 100.0 if integrity_ok else 30.0
    components["integrity_hash"] = integrity_score
    reasons.append("hash_present" if sha else "hash_missing")

    source = str(record.get("source_connector") or meta.get("collection_source") or "manual")
    authority = {
        "common_controls": 90.0,
        "CommonControls": 90.0,
        "PREDEFINED_QUERY": 85.0,
        "mock_evidence": 70.0,
        "manual": 50.0,
    }.get(source, 60.0)
    components["source_authority"] = authority
    reasons.append(f"source={source}")

    weights = {
        "metadata_completeness": 0.25,
        "freshness": 0.20,
        "validation_result": 0.25,
        "integrity_hash": 0.15,
        "source_authority": 0.15,
    }
    score = round(sum(float(components[k]) * w for k, w in weights.items()), 1)
    if score >= 80:
        rating = "GREEN"
    elif score >= 55:
        rating = "AMBER"
    else:
        rating = "RED"
    return {
        "ok": True,
        "score": score,
        "rating": rating,
        "components": components,
        "reasons": reasons,
        "weights": weights,
    }


def summarize_evidence(record: Mapping[str, Any], *, force_fallback: bool = False) -> dict[str, Any]:
    """Provider-independent summary with deterministic fallback when LLM unavailable."""
    meta = dict(record.get("metadata") or {})
    evidence_id = str(record.get("evidence_id") or "")
    application = str(meta.get("application") or (record.get("application_tags") or ["—"])[0])
    environment = str(meta.get("environment") or "—")
    technology = str(meta.get("technology") or "—")
    control = str(meta.get("common_control") or meta.get("common_control_slug") or record.get("control") or "—")
    verdict = str(meta.get("validation_verdict") or "UNKNOWN")
    asset = str(meta.get("asset_id") or "—")
    sha = str(record.get("sha256") or meta.get("content_sha256") or "")[:12]

    template = (
        f"Evidence {evidence_id} for {control} on application {application} "
        f"(env={environment}, asset={asset}, technology={technology}). "
        f"Validation={verdict}. Integrity hash prefix={sha or 'n/a'}."
    )

    if force_fallback:
        return {"ok": True, "mode": "fallback", "summary": template, "provider": None}

    try:
        from ecs_platform.llm_engine.provider import get_provider

        provider = get_provider()
        if not getattr(provider, "configured", lambda: False)():
            return {"ok": True, "mode": "fallback", "summary": template, "provider": type(provider).__name__}
        prompt = (
            "Summarize this compliance evidence in 2 sentences. "
            "Reference only the provided metadata; do not invent findings.\n"
            f"{template}"
        )
        text = provider.generate(prompt)  # type: ignore[attr-defined]
        if not text or not str(text).strip():
            return {"ok": True, "mode": "fallback", "summary": template, "provider": type(provider).__name__}
        return {
            "ok": True,
            "mode": "llm",
            "summary": str(text).strip(),
            "provider": type(provider).__name__,
            "authoritative_refs": {
                "evidence_id": evidence_id,
                "application": application,
                "control": control,
                "technology": technology,
                "validation_verdict": verdict,
            },
        }
    except Exception:  # noqa: BLE001
        return {"ok": True, "mode": "fallback", "summary": template, "provider": None}


def list_phase2_evidence(
    *,
    application: str = "",
    control_slug: str = "",
    technology: str = "",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Filterable Phase-2 evidence rows for CEQ/dashboard (metadata visibility)."""
    rows: list[dict[str, Any]] = []
    for rec in _ops_phase2_records():
        meta = dict(rec.get("metadata") or {})
        app = str(meta.get("application") or (rec.get("application_tags") or [""])[0] or "")
        slug = str(meta.get("common_control_slug") or "")
        tech = str(meta.get("technology") or "")
        if application and app != application:
            continue
        if control_slug and slug != control_slug:
            continue
        if technology and tech != technology:
            continue
        rows.append(
            {
                "evidence_id": rec.get("evidence_id"),
                "application": app,
                "environment": meta.get("environment"),
                "asset_id": meta.get("asset_id"),
                "technology": tech,
                "control_slug": slug,
                "control_id": rec.get("control") or meta.get("common_control_id"),
                "validation_verdict": meta.get("validation_verdict"),
                "sha256": rec.get("sha256") or meta.get("content_sha256"),
                "uploaded_at": rec.get("uploaded_at"),
                "scheduler_run_id": meta.get("scheduler_run_id"),
            }
        )
    rows.sort(key=lambda r: str(r.get("uploaded_at") or ""), reverse=True)
    return rows[: max(0, int(limit or 0))]


def build_leadership_aggregation(
    *,
    portfolio: dict[str, Any] | None = None,
    application_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Leadership roll-up: coverage, completeness, validation, reuse counts."""
    completeness = assess_completeness(portfolio=portfolio, application_ids=application_ids)
    evidence = list_phase2_evidence(limit=500)
    by_app: dict[str, dict[str, Any]] = {}
    for row in completeness["bindings"]:
        app = row["application"]
        bucket = by_app.setdefault(
            app,
            {
                "application": app,
                "complete": 0,
                "missing": 0,
                "stale": 0,
                "pass": 0,
                "fail": 0,
                "review": 0,
                "controls": set(),
            },
        )
        status = row["status"]
        if status == "COMPLETE":
            bucket["complete"] += 1
        elif status == "STALE":
            bucket["stale"] += 1
        else:
            bucket["missing"] += 1
        verdict = str(row.get("verdict") or "").upper()
        if verdict == "PASS":
            bucket["pass"] += 1
        elif verdict == "FAIL":
            bucket["fail"] += 1
        elif verdict in {"WARNING", "REVIEW"}:
            bucket["review"] += 1
        bucket["controls"].add(row["control_slug"])

    # Exact duplicate reuse count via SHA-256 collisions among Phase-2 evidence
    hashes: dict[str, list[str]] = {}
    for row in evidence:
        h = str(row.get("sha256") or "")
        if h:
            hashes.setdefault(h, []).append(str(row.get("evidence_id") or ""))
    reuse_groups = {h: ids for h, ids in hashes.items() if len(ids) > 1}

    apps_out = []
    for app, bucket in sorted(by_app.items()):
        apps_out.append(
            {
                "application": app,
                "complete": bucket["complete"],
                "missing": bucket["missing"],
                "stale": bucket["stale"],
                "pass": bucket["pass"],
                "fail": bucket["fail"],
                "review": bucket["review"],
                "control_count": len(bucket["controls"]),
            }
        )
    return {
        "ok": True,
        "totals": {
            "bindings": completeness["total_bindings"],
            "complete": completeness["complete"],
            "missing": completeness["missing"],
            "stale": completeness["stale"],
            "evidence_rows": len(evidence),
            "reuse_groups": len(reuse_groups),
            "reuse_evidence_ids": sum(len(v) for v in reuse_groups.values()),
        },
        "applications": apps_out,
        "missing_requirements": completeness["missing_requirements"][:50],
    }
