"""Executive dashboard aggregation (Milestone 6).

Builds read-only, deterministic executive views by aggregating the M1-M3 layers:
technology/control/framework mapping, the asset inventory, evidence runs, the
evidence repository, validation, and observations. Returns plain dicts for the UI
(no new chart library — the templates render with the existing Bootstrap/ecs-*
components).

Nothing here executes anything or touches secrets; it summarizes existing state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from modules.audit_intelligence.engines import evidence_orchestrator as orch
from modules.audit_intelligence.engines import evidence_repository as repo
from modules.audit_intelligence.engines import observation_generation as obs
from modules.audit_intelligence.engines import technology_control_mapping as mapping
from modules.audit_intelligence.services import asset_service


def _pct(part: int, whole: int) -> float:
    return round((part / whole) * 100, 1) if whole else 0.0


# --------------------------------------------------------------------------- #
# Individual dashboard sections
# --------------------------------------------------------------------------- #
def technology_coverage() -> dict[str, Any]:
    """Which technologies have controls / executable controls."""
    techs = mapping.list_technologies()
    with_exec = [t for t in techs if t.executable_control_count > 0]
    return {
        "total_technologies": len(techs),
        "with_executable_controls": len(with_exec),
        "coverage_percent": _pct(len(with_exec), len(techs)),
        "rows": [
            {
                "technology": t.name,
                "controls": t.control_count,
                "executable": t.executable_control_count,
                "frameworks": t.framework_count,
            }
            for t in techs
        ],
    }


def control_coverage() -> dict[str, Any]:
    controls = mapping.all_controls()
    executable = [c for c in controls if c.executable]
    return {
        "total_controls": len(controls),
        "executable_controls": len(executable),
        "coverage_percent": _pct(len(executable), len(controls)),
    }


def framework_readiness() -> dict[str, Any]:
    """Per-framework readiness = evidence-backed compliance from the repository.

    Uses stored evidence verdicts where present; otherwise reports the framework's
    control footprint (0% collected) so gaps are visible.
    """
    frameworks = mapping.list_frameworks()
    rows = []
    for f in frameworks:
        items = repo.search(framework=f.name, latest_only=True)
        passed = sum(1 for a in items if a.verdict == "PASS")
        failed = sum(1 for a in items if a.verdict == "FAIL")
        assessed = sum(1 for a in items if a.verdict in ("PASS", "FAIL", "WARNING"))
        rows.append(
            {
                "framework": f.name,
                "controls": f.control_count,
                "technologies": f.technology_count,
                "evidence_collected": len(items),
                "passed": passed,
                "failed": failed,
                "readiness_percent": _pct(passed, assessed) if assessed else 0.0,
            }
        )
    rows.sort(key=lambda r: (-r["readiness_percent"], r["framework"].lower()))
    return {"frameworks": len(frameworks), "rows": rows}


def asset_coverage() -> dict[str, Any]:
    assets = asset_service.discover_assets(include_docker_compose=True, include_enterprise_grc=True)
    cov = asset_service.coverage_summary(assets)
    return {
        "total_assets": cov["total_assets"],
        "identified": cov["identified_assets"],
        "in_catalog": cov["assets_in_query_catalog"],
        "identification_percent": round(cov["identification_rate"] * 100, 1),
        "by_environment": cov["by_environment"],
        "by_criticality": cov["by_criticality"],
    }


def evidence_coverage() -> dict[str, Any]:
    stats = repo.stats()
    return {
        "evidence_keys": stats["evidence_keys"],
        "total_versions": stats["total_versions"],
        "by_verdict": stats["by_verdict"],
        "by_technology": stats["by_technology"],
    }


def collection_progress() -> dict[str, Any]:
    """Progress across all evidence runs (completed vs total records)."""
    runs = orch.list_runs()
    total = completed = failed = 0
    for r in runs:
        s = r.summary()
        total += s["total"]
        completed += s["completed"]
        failed += s["failed"]
    return {
        "runs": len(runs),
        "controls_total": total,
        "controls_completed": completed,
        "controls_failed": failed,
        "progress_percent": _pct(completed, total),
        "recent_runs": [
            {"run_id": r.run_id, "scope": f"{r.scope_kind}:{r.scope_value}",
             "status": r.status, "summary": r.summary()}
            for r in runs[:8]
        ],
    }


def validation_summary() -> dict[str, Any]:
    """Aggregate verdicts across all stored evidence."""
    items = repo.all_latest()
    by_verdict: dict[str, int] = {}
    for a in items:
        by_verdict[a.verdict or "Unassessed"] = by_verdict.get(a.verdict or "Unassessed", 0) + 1
    passed = by_verdict.get("PASS", 0)
    failed = by_verdict.get("FAIL", 0)
    warned = by_verdict.get("WARNING", 0)
    assessed = passed + failed + warned
    return {
        "total_evidence": len(items),
        "by_verdict": by_verdict,
        "compliance_percent": round(((passed + 0.5 * warned) / assessed) * 100, 1) if assessed else 0.0,
    }


def open_observations() -> dict[str, Any]:
    return obs.summary()


def risk_summary() -> dict[str, Any]:
    """Risk = open observations weighted by severity."""
    observations = obs.list_observations()
    weights = {"Critical": 5, "High": 3, "Medium": 2, "Low": 1, "Informational": 0}
    open_states = {"Draft", "Submitted", "Approved"}
    score = 0
    by_sev: dict[str, int] = {}
    for o in observations:
        if o.status in open_states:
            score += weights.get(o.severity, 1)
            by_sev[o.severity] = by_sev.get(o.severity, 0) + 1
    if score >= 15:
        band = "High"
    elif score >= 6:
        band = "Medium"
    elif score > 0:
        band = "Low"
    else:
        band = "Minimal"
    return {"risk_score": score, "risk_band": band, "open_by_severity": by_sev}


def evidence_freshness(stale_days: int = 30) -> dict[str, Any]:
    """How fresh the collected evidence is (based on collection timestamps)."""
    items = repo.all_latest()
    now = datetime.now(timezone.utc)
    fresh = stale = 0
    oldest = ""
    newest = ""
    for a in items:
        try:
            ts = datetime.fromisoformat(a.collected_at)
        except (ValueError, TypeError):
            continue
        age_days = (now - ts).days
        if age_days > stale_days:
            stale += 1
        else:
            fresh += 1
        if not oldest or a.collected_at < oldest:
            oldest = a.collected_at
        if not newest or a.collected_at > newest:
            newest = a.collected_at
    total = len(items)
    return {
        "total_evidence": total,
        "fresh": fresh,
        "stale": stale,
        "stale_days_threshold": stale_days,
        "fresh_percent": _pct(fresh, total),
        "oldest": oldest,
        "newest": newest,
    }


# --------------------------------------------------------------------------- #
# Composite executive view
# --------------------------------------------------------------------------- #
def executive_readiness() -> dict[str, Any]:
    """Single composite payload powering the Executive Readiness dashboard."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "technology_coverage": technology_coverage(),
        "control_coverage": control_coverage(),
        "framework_readiness": framework_readiness(),
        "asset_coverage": asset_coverage(),
        "evidence_coverage": evidence_coverage(),
        "collection_progress": collection_progress(),
        "validation_summary": validation_summary(),
        "open_observations": open_observations(),
        "risk_summary": risk_summary(),
        "evidence_freshness": evidence_freshness(),
    }
