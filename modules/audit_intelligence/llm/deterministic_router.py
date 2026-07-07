"""Deterministic query router — answers audit questions from ECS data/DB logic.

Reuses EXISTING engines (never re-implements them):
  * governance ``missing_evidence_engine`` — app-centric observation/evidence-gap
    demo data (application, framework, severity, status, owner, due_date), which is
    the richest deterministic source available offline;
  * audit-intelligence ``dashboard_service`` — framework readiness, risk summary,
    evidence freshness/coverage;
  * audit-intelligence ``audit_repository_service`` — pipeline observations,
    repository stats, evidence packs.

Every function returns a structured, JSON-safe result with ``answer_text`` (a
deterministic sentence the LLM may summarize but must not alter), the underlying
counts/rows, ``data_used`` and ``source_references``. Never raises — on any error
it returns an empty-but-valid result so the workbench degrades gracefully.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_OPEN_STATUSES = {"Draft", "Submitted", "Approved", "Open", "Pending Upload",
                  "Awaiting App Owner", "Pending", "Overdue", "In Progress"}


# --------------------------------------------------------------------------- #
# Data access (reused engines; all guarded)
# --------------------------------------------------------------------------- #
def _missing_rows(role: str = "owner") -> list[dict[str, Any]]:
    try:
        from modules.governance.engines.missing_evidence_engine import get_all_missing_evidence

        return list(get_all_missing_evidence(role) or [])
    except Exception:  # noqa: BLE001
        return []


def _dashboard():
    from modules.audit_intelligence.services import dashboard_service

    return dashboard_service


def _repo_service():
    from modules.audit_intelligence.services import audit_repository_service

    return audit_repository_service


def _row_app(r: dict[str, Any]) -> str:
    return str(r.get("application") or "")


def _row_sev(r: dict[str, Any]) -> str:
    return str(r.get("observation_severity") or r.get("severity") or r.get("risk") or "")


def _row_status(r: dict[str, Any]) -> str:
    return str(r.get("status") or "")


def _row_fw(r: dict[str, Any]) -> str:
    return str(r.get("framework") or "")


def _is_open(r: dict[str, Any]) -> bool:
    st = _row_status(r)
    return st in _OPEN_STATUSES or st not in {"Closed", "Remediated", "Uploaded", "Approved & Closed"}


def _result(answer_text: str, *, count: int = 0, rows: list | None = None,
            data_used: list[str] | None = None, source_references: list[str] | None = None,
            **extra: Any) -> dict[str, Any]:
    out = {
        "answer_text": answer_text,
        "count": count,
        "rows": (rows or [])[:100],   # bound payload
        "row_total": len(rows or []),
        "data_used": data_used or [],
        "source_references": source_references or [],
    }
    out.update(extra)
    return out


# --------------------------------------------------------------------------- #
# Deterministic query functions
# --------------------------------------------------------------------------- #
def open_observations_by_application(application: str = "", **_: Any) -> dict[str, Any]:
    rows = [r for r in _missing_rows() if _is_open(r)]
    if application:
        rows = [r for r in rows if _row_app(r).lower() == application.lower()]
    scope = application or "all applications"
    return _result(
        f"There are {len(rows)} open observation(s) for {scope}.",
        count=len(rows), rows=rows,
        data_used=["missing_evidence_engine.get_all_missing_evidence"],
        source_references=["ECS observation/evidence-gap registry"],
    )


def observations_till_date(application: str = "", **_: Any) -> dict[str, Any]:
    rows = _missing_rows()
    if application:
        rows = [r for r in rows if _row_app(r).lower() == application.lower()]
    scope = application or "all applications"
    return _result(
        f"{len(rows)} observation(s) have been recorded to date for {scope}.",
        count=len(rows), rows=rows,
        data_used=["missing_evidence_engine.get_all_missing_evidence"],
        source_references=["ECS observation/evidence-gap registry"],
    )


def high_risk_observations(framework: str = "", **_: Any) -> dict[str, Any]:
    rows = [r for r in _missing_rows()
            if _row_sev(r) in ("Critical", "High", "Major") and _is_open(r)]
    if framework:
        rows = [r for r in rows if framework.lower() in _row_fw(r).lower()]
    by_fw: dict[str, int] = {}
    for r in rows:
        by_fw[_row_fw(r)] = by_fw.get(_row_fw(r), 0) + 1
    scope = f"framework {framework}" if framework else "all frameworks"
    return _result(
        f"There are {len(rows)} open high-risk observation(s) across {scope}.",
        count=len(rows), rows=rows, by_framework=by_fw,
        data_used=["missing_evidence_engine.get_all_missing_evidence"],
        source_references=["ECS observation/evidence-gap registry"],
    )


def observations_by_severity(severity: str = "", **_: Any) -> dict[str, Any]:
    rows = _missing_rows()
    by_sev: dict[str, int] = {}
    for r in rows:
        by_sev[_row_sev(r)] = by_sev.get(_row_sev(r), 0) + 1
    if severity:
        rows = [r for r in rows if _row_sev(r).lower() == severity.lower()]
    return _result(
        f"{len(rows)} observation(s)" + (f" at severity {severity}." if severity
                                         else f" grouped by severity: {by_sev}."),
        count=len(rows), rows=rows, by_severity=by_sev,
        data_used=["missing_evidence_engine.get_all_missing_evidence"],
        source_references=["ECS observation/evidence-gap registry"],
    )


def observations_by_framework(framework: str = "", **_: Any) -> dict[str, Any]:
    rows = _missing_rows()
    by_fw: dict[str, int] = {}
    for r in rows:
        by_fw[_row_fw(r)] = by_fw.get(_row_fw(r), 0) + 1
    if framework:
        rows = [r for r in rows if framework.lower() in _row_fw(r).lower()]
    return _result(
        f"{len(rows)} observation(s)" + (f" for framework {framework}." if framework
                                         else f" grouped by framework: {by_fw}."),
        count=len(rows), rows=rows, by_framework=by_fw,
        data_used=["missing_evidence_engine.get_all_missing_evidence"],
        source_references=["ECS observation/evidence-gap registry"],
    )


def observations_by_status(status: str = "", **_: Any) -> dict[str, Any]:
    rows = _missing_rows()
    by_status: dict[str, int] = {}
    for r in rows:
        by_status[_row_status(r)] = by_status.get(_row_status(r), 0) + 1
    if status:
        rows = [r for r in rows if _row_status(r).lower() == status.lower()]
    return _result(
        f"{len(rows)} observation(s)" + (f" in status {status}." if status
                                         else f" grouped by status: {by_status}."),
        count=len(rows), rows=rows, by_status=by_status,
        data_used=["missing_evidence_engine.get_all_missing_evidence"],
        source_references=["ECS observation/evidence-gap registry"],
    )


def _age_days(due_date: str) -> int | None:
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(due_date, fmt).replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - dt).days
        except (ValueError, TypeError):
            continue
    return None


def aging_observations(min_age_days: int = 90, application: str = "", **_: Any) -> dict[str, Any]:
    rows = []
    for r in _missing_rows():
        if application and _row_app(r).lower() != application.lower():
            continue
        age = _age_days(str(r.get("due_date") or ""))
        if age is not None and age >= int(min_age_days):
            rows.append({**r, "age_days": age})
    return _result(
        f"{len(rows)} observation(s) are older than {min_age_days} days"
        + (f" for {application}." if application else "."),
        count=len(rows), rows=rows, min_age_days=int(min_age_days),
        data_used=["missing_evidence_engine.get_all_missing_evidence (due_date)"],
        source_references=["ECS observation/evidence-gap registry"],
    )


def overdue_observations(application: str = "", **_: Any) -> dict[str, Any]:
    rows = []
    for r in _missing_rows():
        if application and _row_app(r).lower() != application.lower():
            continue
        age = _age_days(str(r.get("due_date") or ""))
        overdue = _row_status(r).lower() == "overdue" or (age is not None and age > 0)
        if overdue:
            rows.append({**r, "age_days": age})
    return _result(
        f"{len(rows)} observation(s) are overdue for closure"
        + (f" for {application}." if application else "."),
        count=len(rows), rows=rows,
        data_used=["missing_evidence_engine.get_all_missing_evidence (due_date/status)"],
        source_references=["ECS observation/evidence-gap registry"],
    )


def repeat_observations(application: str = "", **_: Any) -> dict[str, Any]:
    # Repeat = same (application, control) appearing more than once.
    seen: dict[tuple, int] = {}
    for r in _missing_rows():
        key = (_row_app(r), str(r.get("control_id") or r.get("control") or ""))
        seen[key] = seen.get(key, 0) + 1
    repeats = {f"{a} / {c}": n for (a, c), n in seen.items() if n > 1 and (not application or a.lower() == application.lower())}
    by_app: dict[str, int] = {}
    for (a, _c), n in seen.items():
        if n > 1:
            by_app[a] = by_app.get(a, 0) + 1
    top = sorted(by_app.items(), key=lambda kv: -kv[1])[:5]
    return _result(
        f"{len(repeats)} repeat observation group(s) detected. "
        f"Applications with the most repeats: {top}.",
        count=len(repeats), rows=[{"key": k, "occurrences": v} for k, v in repeats.items()],
        by_application=by_app, top_applications=top,
        data_used=["missing_evidence_engine.get_all_missing_evidence (application+control)"],
        source_references=["ECS observation/evidence-gap registry"],
    )


def closure_trend(**_: Any) -> dict[str, Any]:
    try:
        d = _dashboard().open_observations()
        risk = _dashboard().risk_summary()
        return _result(
            f"Open observations: {d.get('total', 0)} total; risk band "
            f"{risk.get('risk_band', 'n/a')} (score {risk.get('risk_score', 0)}).",
            count=int(d.get("total", 0) or 0),
            by_severity=d.get("by_severity", {}), by_status=d.get("by_status", {}),
            risk_summary=risk,
            data_used=["dashboard_service.open_observations", "dashboard_service.risk_summary"],
            source_references=["ECS audit-intelligence dashboard"],
        )
    except Exception:  # noqa: BLE001
        return _result("Closure/observation summary is not available in this environment.",
                       data_used=[], source_references=[])


def evidence_gaps(application: str = "", framework: str = "", **_: Any) -> dict[str, Any]:
    rows = _missing_rows()
    if application:
        rows = [r for r in rows if _row_app(r).lower() == application.lower()]
    if framework:
        rows = [r for r in rows if framework.lower() in _row_fw(r).lower()]
    by_fw: dict[str, int] = {}
    for r in rows:
        by_fw[_row_fw(r)] = by_fw.get(_row_fw(r), 0) + 1
    top_fw = max(by_fw.items(), key=lambda kv: kv[1])[0] if by_fw else ""
    scope = " / ".join(x for x in (application, framework) if x) or "all scopes"
    return _result(
        f"{len(rows)} evidence gap(s) for {scope}."
        + (f" Highest-gap framework: {top_fw}." if top_fw else ""),
        count=len(rows), rows=rows, by_framework=by_fw, highest_gap_framework=top_fw,
        data_used=["missing_evidence_engine.get_all_missing_evidence"],
        source_references=["ECS observation/evidence-gap registry"],
    )


def framework_highest_gap(**_: Any) -> dict[str, Any]:
    res = evidence_gaps()
    top = res.get("highest_gap_framework", "")
    return _result(
        f"The framework with the highest evidence gap is {top or 'n/a'} "
        f"({res.get('by_framework', {}).get(top, 0)} gaps).",
        count=res.get("by_framework", {}).get(top, 0),
        by_framework=res.get("by_framework", {}), highest_gap_framework=top,
        data_used=res.get("data_used", []), source_references=res.get("source_references", []),
    )


def audit_readiness_score(framework: str = "", **_: Any) -> dict[str, Any]:
    try:
        fr = _dashboard().framework_readiness()
        rows = fr.get("rows", [])
        if framework:
            rows = [r for r in rows if framework.lower() in str(r.get("framework", "")).lower()]
        avg = round(sum(float(r.get("readiness_percent", 0) or 0) for r in rows) / len(rows), 1) if rows else 0.0
        return _result(
            f"Average framework readiness across {len(rows)} framework(s) is {avg}%.",
            count=len(rows), rows=rows, average_readiness_percent=avg,
            data_used=["dashboard_service.framework_readiness"],
            source_references=["ECS audit-intelligence dashboard"],
        )
    except Exception:  # noqa: BLE001
        return _result("Framework readiness is not available in this environment.")


def evidence_completeness(**_: Any) -> dict[str, Any]:
    try:
        cov = _dashboard().evidence_coverage()
        fresh = _dashboard().evidence_freshness()
        return _result(
            f"Evidence keys: {cov.get('evidence_keys', 0)}; fresh {fresh.get('fresh', 0)} / "
            f"stale {fresh.get('stale', 0)} ({fresh.get('fresh_percent', 0)}% fresh).",
            count=int(cov.get("evidence_keys", 0) or 0),
            coverage=cov, freshness=fresh,
            data_used=["dashboard_service.evidence_coverage", "dashboard_service.evidence_freshness"],
            source_references=["ECS audit-intelligence dashboard"],
        )
    except Exception:  # noqa: BLE001
        return _result("Evidence completeness is not available in this environment.")


def stale_evidence(stale_days: int = 30, **_: Any) -> dict[str, Any]:
    try:
        fresh = _dashboard().evidence_freshness(stale_days=int(stale_days))
        return _result(
            f"{fresh.get('stale', 0)} stale evidence item(s) older than {stale_days} days "
            f"(threshold), out of {fresh.get('total_evidence', 0)}.",
            count=int(fresh.get("stale", 0) or 0), freshness=fresh,
            data_used=["dashboard_service.evidence_freshness"],
            source_references=["ECS audit-intelligence dashboard"],
        )
    except Exception:  # noqa: BLE001
        return _result("Stale-evidence detection is not available in this environment.")


def application_comparison(framework: str = "", **_: Any) -> dict[str, Any]:
    rows = _missing_rows()
    by_app: dict[str, int] = {}
    for r in rows:
        if framework and framework.lower() not in _row_fw(r).lower():
            continue
        if _is_open(r):
            by_app[_row_app(r)] = by_app.get(_row_app(r), 0) + 1
    ranked = sorted(by_app.items(), key=lambda kv: -kv[1])
    least_ready = ranked[0][0] if ranked else ""
    return _result(
        f"Open observations by application: {by_app}. "
        f"Least audit-ready (most open): {least_ready or 'n/a'}.",
        count=len(by_app), by_application=by_app, ranking=ranked, least_ready=least_ready,
        data_used=["missing_evidence_engine.get_all_missing_evidence"],
        source_references=["ECS observation/evidence-gap registry"],
    )


def evidence_pack_availability(pack_type: str = "framework", scope: str = "", **_: Any) -> dict[str, Any]:
    try:
        if not scope:
            stats = _repo_service().repository_stats()
            return _result(
                f"Evidence repository holds {stats.get('evidence_keys', 0)} evidence key(s); "
                f"packs can be built by framework/asset/technology/application.",
                count=int(stats.get("evidence_keys", 0) or 0), stats=stats,
                data_used=["audit_repository_service.repository_stats"],
                source_references=["ECS evidence repository"],
            )
        pack = _repo_service().build_pack(pack_type, scope)
        item_count = int((pack or {}).get("item_count", 0) or 0)
        return _result(
            f"{pack_type} pack for '{scope}' contains {item_count} item(s).",
            count=item_count, pack=pack,
            data_used=["audit_repository_service.build_pack"],
            source_references=["ECS evidence packs"],
        )
    except Exception:  # noqa: BLE001
        return _result("Evidence pack availability is not available in this environment.")


def app_owner_pending_actions(owner: str = "", application: str = "", **_: Any) -> dict[str, Any]:
    rows = [r for r in _missing_rows() if _is_open(r)]
    if application:
        rows = [r for r in rows if _row_app(r).lower() == application.lower()]
    by_owner: dict[str, int] = {}
    for r in rows:
        by_owner[str(r.get("owner") or "unassigned")] = by_owner.get(str(r.get("owner") or "unassigned"), 0) + 1
    if owner:
        rows = [r for r in rows if str(r.get("owner") or "").lower() == owner.lower()]
    return _result(
        f"{len(rows)} pending action(s)" + (f" for owner {owner}." if owner
                                            else f" grouped by owner: {by_owner}."),
        count=len(rows), rows=rows, by_owner=by_owner,
        data_used=["missing_evidence_engine.get_all_missing_evidence"],
        source_references=["ECS observation/evidence-gap registry"],
    )


# --------------------------------------------------------------------------- #
# Prompt -> deterministic function mapping (for the execution service)
# --------------------------------------------------------------------------- #
#: Maps a prompt_id (or logical intent) to the deterministic function used to build
#: its ground-truth context. Prompts not listed fall back to a general summary.
PROMPT_ROUTES: dict[str, Any] = {
    "observation_count": open_observations_by_application,
    "high_risk_observation_summary": high_risk_observations,
    "framework_gap_analysis": framework_highest_gap,
    "application_audit_readiness": audit_readiness_score,
    "closure_trend_analysis": closure_trend,
    "delayed_closure_root_cause": overdue_observations,
    "repeat_observation_analysis": repeat_observations,
    "evidence_gap_to_observation_risk": evidence_gaps,
    "cross_application_comparison": application_comparison,
    "application_comparison_summary": application_comparison,
    "stale_evidence_detection_summary": stale_evidence,
    "evidence_pack_summary": evidence_pack_availability,
    "evidence_reuse_recommendation": evidence_pack_availability,
    "app_owner_action_summary": app_owner_pending_actions,
    "closure_probability_by_owner": app_owner_pending_actions,
    "framework_readiness_score_explanation": audit_readiness_score,
    "executive_compliance_summary": audit_readiness_score,
    "board_level_summary": audit_readiness_score,
    "cio_compliance_briefing": audit_readiness_score,
    "enterprise_evidence_gap_summary": evidence_gaps,
    "national_compliance_summary": application_comparison,
    "pan_india_dashboard_summary": application_comparison,
    "csite_closure_probability": closure_trend,
    "observation_non_recurrence_probability": high_risk_observations,
    "audit_escalation_likelihood": high_risk_observations,
    "control_failure_history_summary": repeat_observations,
    "exception_expiry_risk_summary": aging_observations,
    "compliance_trend_forecast": closure_trend,
    "upcoming_audit_preparation": evidence_gaps,
    "regulatory_reporting_summary": audit_readiness_score,
    "service_now_evidence_gap_summary": evidence_gaps,
    "sharepoint_evidence_availability_summary": evidence_completeness,
    "technology_compliance_risk": high_risk_observations,
    "audit_query_answering": open_observations_by_application,
}


def build_deterministic_context(prompt_id: str, entities: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run the deterministic function mapped to a prompt_id with extracted entities.

    Returns the function's structured result (or a general summary). Never raises.
    """
    entities = entities or {}
    fn = PROMPT_ROUTES.get(prompt_id)
    kwargs = {
        "application": entities.get("application", ""),
        "framework": entities.get("framework", ""),
        "severity": entities.get("severity", ""),
        "status": entities.get("status", ""),
        "owner": entities.get("owner", "") if isinstance(entities.get("owner"), str) else "",
        "technology": entities.get("technology", ""),
    }
    try:
        if fn is None:
            return open_observations_by_application(**{"application": kwargs["application"]})
        # Filter kwargs to those the function accepts (all accept **_, so pass all).
        return fn(**kwargs)
    except Exception:  # noqa: BLE001
        return _result("Deterministic context is not available for this query.")
