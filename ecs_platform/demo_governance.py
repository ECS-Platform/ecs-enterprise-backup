"""Deterministic demo data for the governance (platform) pages.

Used as the fallback for ``ecs_platform.governance`` read functions when the
PostgreSQL repository is unavailable (demo mode, no psycopg2/DB), so the platform
governance pages (scorecard, executive summary, audit readiness, inventory,
control/framework coverage, evidence reuse/lifecycle, scheduler) never show
"Repository unavailable" / psycopg2 and always render realistic content.

Pure standard library.
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import Any

from ecs_platform import demo_evidence

_FRAMEWORKS = [
    "PCI-DSS", "ISO27001", "SOC2", "RBI-CSF", "AI-SDLC", "DPSC", "VAPT", "ITPP",
    "ITDRM", "MBSS", "ASST", "IS-Audit", "CSITE", "OS-Baselining", "DB-Baselining",
    "Middleware-Baselining", "TPRM", "SWIFT-CSP", "DPDP", "AppSec",
]
_CRITICALITY = ["Critical", "High", "Medium", "Low"]
_LIFECYCLE = ["Active", "In Onboarding", "Decommissioning"]
_REVIEW_STATES = ["Collected", "UnderReview", "Approved", "Rejected", "Expired"]
_OWNERS = ["R. Mehta", "A. Sharma", "K. Reddy", "S. Banerjee", "M. D'Souza", "P. Nair", "V. Desai",
           "S. Nair", "N. Iyer", "T. Kapoor", "L. Menon", "J. Patel"]
_BU = [
    "Retail Banking", "Corporate Banking", "Treasury", "Risk & Compliance", "Digital Banking",
    "Operations", "Wealth Management", "Cards & Payments", "Trade Finance", "Technology",
    "Information Security", "Internal Audit",
]
_REGIONS = ["North", "South", "East", "West", "Central"]
_ANCHOR = date(2026, 5, 29)


def _seed(*p: Any) -> int:
    return int(hashlib.md5("::".join(str(x) for x in p).encode()).hexdigest(), 16)


def _pick(s: int, items: list) -> Any:
    return items[s % len(items)]


# ---- applications -----------------------------------------------------------
def _applications() -> list[dict[str, Any]]:
    apps = sorted({r["application"] for r in demo_evidence.all_records()})
    out: list[dict[str, Any]] = []
    for i, name in enumerate(apps):
        s = _seed("gov-app", name)
        out.append({
            "slug": name.lower().replace(" ", "-"),
            "name": name,
            "owner": _pick(s, _OWNERS),
            "business_unit": _pick(s >> 4, _BU),
            "criticality": _pick(s >> 8, _CRITICALITY),
            "environment": "Production",
            "lifecycle_status": _pick(s >> 12, _LIFECYCLE),
            "onboarded_at": (_ANCHOR - timedelta(days=(s % 700) + 30)).strftime("%Y-%m-%d"),
            "evidence_count": 40 + (s % 160),
            "frameworks": ", ".join(sorted({_pick(s >> 16, _FRAMEWORKS), _pick(s >> 20, _FRAMEWORKS)})),
        })
    return out


def list_applications() -> dict[str, Any]:
    apps = _applications()
    by_crit: dict[str, int] = {c: 0 for c in _CRITICALITY}
    by_status: dict[str, int] = {}
    for a in apps:
        by_crit[a["criticality"]] = by_crit.get(a["criticality"], 0) + 1
        by_status[a["lifecycle_status"]] = by_status.get(a["lifecycle_status"], 0) + 1
    return {"ok": True, "demo": True, "applications": apps, "total": len(apps),
            "by_criticality": by_crit, "by_status": by_status}


# ---- control coverage -------------------------------------------------------
def _controls() -> list[dict[str, Any]]:
    domains = ["Access Control", "Cryptography", "Network Security", "Logging & Monitoring",
               "Change Management", "DR & BCP", "Data Protection", "Incident Response"]
    out: list[dict[str, Any]] = []
    for i in range(320):
        s = _seed("gov-ctrl", i)
        fw = _pick(s, _FRAMEWORKS)
        out.append({
            "control_id": f"{fw[:3].upper()}-{i + 1:03d}",
            "name": f"{_pick(s >> 4, domains)} Control {i + 1}",
            "domain": _pick(s >> 4, domains),
            "framework_code": fw,
        })
    return out


def control_coverage() -> dict[str, Any]:
    catalog = _controls()
    rows = []
    covered = 0
    for c in catalog:
        s = _seed("cov", c["control_id"])
        ev = (s % 14)  # ~1/14 are gaps
        apps = 1 + (s >> 4) % 8 if ev else 0
        status = "Covered" if ev > 0 else "Gap"
        if ev > 0:
            covered += 1
        rows.append({**c, "evidence_count": ev, "app_count": apps, "status": status})
    total = len(catalog)
    pct = round(100 * covered / total, 1) if total else 0.0
    return {"ok": True, "demo": True, "controls": rows, "total_controls": total,
            "covered": covered, "gaps": total - covered, "coverage_pct": pct,
            "discovered_controls": []}


def framework_coverage() -> dict[str, Any]:
    rows = []
    for fw in _FRAMEWORKS:
        s = _seed("fwcov", fw)
        exp = 30 + (s % 40)
        cov = int(exp * (0.7 + (s % 25) / 100))
        pct = round(100 * cov / exp, 1) if exp else 0.0
        rows.append({"framework_code": fw, "expected_controls": exp, "covered_controls": cov,
                     "evidence_count": 50 + (s % 250), "coverage_pct": pct})
    overall = round(sum(r["coverage_pct"] for r in rows) / len(rows), 1) if rows else 0.0
    return {"ok": True, "demo": True, "frameworks": rows, "overall_pct": overall}


def evidence_reuse() -> dict[str, Any]:
    total = demo_evidence.counts()["total"]
    total_links = int(total * 2.4)
    mapped = int(total * 0.82)
    saved = max(0, total_links - mapped)
    reuse_pct = round(100 * saved / total_links, 1) if total_links else 0.0
    by_framework = [{"framework_code": fw, "c": 60 + (_seed("rf", fw) % 240)} for fw in _FRAMEWORKS]
    by_control = [{"control_id": f"CTRL-{i:03d}", "c": 10 + (_seed('rc', i) % 40)} for i in range(12)]
    return {
        "ok": True, "demo": True, "total_evidence": total, "control_links": total_links,
        "evidence_with_controls": mapped, "multi_control_evidence": int(total * 0.31),
        "reuse_ratio": round(total_links / mapped, 2) if mapped else 0.0,
        "reuse_savings": saved, "reuse_pct": reuse_pct,
        "correlation_chains": 40, "chain_members": 160, "shared_artifacts": int(total * 0.18),
        "framework_obligations": int(total * 3.1), "crosswalked_evidence": int(total * 0.75),
        "framework_reuse_ratio": 3.1, "framework_ops_saved": int(total * 2.0),
        "by_control": by_control, "by_framework": by_framework,
    }


def evidence_lifecycle(status: str = "", limit: int = 200) -> dict[str, Any]:
    recs = demo_evidence.all_records()
    rows = []
    counts = {s: 0 for s in _REVIEW_STATES}
    for r in recs:
        s = _seed("life", r["uid"])
        st = _pick(s, _REVIEW_STATES)
        counts[st] += 1
        if status and st != status:
            continue
        if len(rows) < limit:
            rows.append({
                "evidence_uid": r["uid"], "source_system": r["source_system"],
                "object_type": r["object_type"], "title": r["title"], "application": r["application"],
                "status": st, "reviewer": _pick(s >> 4, _OWNERS),
                "reviewed_at": r["collection_date"], "valid_until": "",
            })
    total = sum(counts.values())
    approved = counts.get("Approved", 0)
    return {"ok": True, "demo": True, "counts": counts, "rows": rows, "total": total,
            "expired": counts.get("Expired", 0),
            "approval_pct": round(100 * approved / total, 1) if total else 0.0,
            "states": list(_REVIEW_STATES)}


def list_schedules() -> dict[str, Any]:
    rows = []
    for i, src in enumerate(demo_evidence.DEMO_SOURCES):
        s = _seed("sched", src)
        rows.append({
            "id": i + 1, "name": f"{src} Collection", "connector": src.lower(),
            "app_slug": _pick(s, _applications())["slug"],
            "frequency": _pick(s >> 4, ["Hourly", "Daily", "Weekly"]),
            "owner": _pick(s >> 8, _OWNERS), "enabled": bool(s % 5),
            "last_run": (_ANCHOR - timedelta(hours=(s % 24) + 1)).strftime("%Y-%m-%d %H:%M"),
            "last_status": _pick(s >> 12, ["ok", "ok", "ok", "partial"]),
            "next_run": (_ANCHOR + timedelta(hours=(s % 12) + 1)).strftime("%Y-%m-%d %H:%M"),
        })
    return {"ok": True, "demo": True, "schedules": rows, "total": len(rows),
            "enabled": sum(1 for r in rows if r["enabled"]),
            "due": sum(1 for r in rows if r["last_status"] != "ok")}


def crosswalk_matrix() -> dict[str, Any]:
    controls = []
    for c in _controls()[:40]:
        s = _seed("xw", c["control_id"])
        refs = {fw: f"{fw[:3].upper()}-{(s >> i) % 12 + 1}.{(s >> (i + 2)) % 9 + 1}"
                for i, fw in enumerate(_FRAMEWORKS) if (s >> i) % 2}
        if not refs:
            refs = {_FRAMEWORKS[0]: "REF-1.1"}
        controls.append({"control_id": c["control_id"], "name": c["name"],
                         "evidence_count": s % 30, "refs": refs})
    return {"ok": True, "demo": True, "frameworks": list(_FRAMEWORKS), "controls": controls}


def reuse_demonstrations(per_framework: int = 4) -> dict[str, Any]:
    recs = demo_evidence.all_records()
    demos: dict[str, list[dict[str, Any]]] = {}
    for fi, fw in enumerate(_FRAMEWORKS):
        items = []
        for r in recs[fi * 7: fi * 7 + per_framework]:
            s = _seed("demo", r["uid"])
            others = sorted({_pick(s, _FRAMEWORKS), _pick(s >> 4, _FRAMEWORKS), fw})
            items.append({
                "evidence_uid": r["uid"], "source_system": r["source_system"],
                "object_type": r["object_type"], "title": r["title"], "application": r["application"],
                "controls": [f"CTRL-{s % 99:02d}"], "frameworks": others,
                "framework_refs": {o: f"{o[:3].upper()}-{i + 1}.1" for i, o in enumerate(others)},
                "fanout": len(others),
            })
        demos[fw] = items
    return {"ok": True, "demo": True, "frameworks": list(_FRAMEWORKS), "demos": demos,
            "reusable_evidence": len(recs), "max_fanout": len(_FRAMEWORKS),
            "coverage_counts": {fw: 60 + (_seed("cc", fw) % 200) for fw in _FRAMEWORKS}}


def _per_app_readiness() -> list[dict[str, Any]]:
    out = []
    for a in _applications():
        s = _seed("ready", a["slug"])
        c_pct = 60 + (s % 38)
        a_pct = 55 + ((s >> 4) % 42)
        score = round(0.6 * c_pct + 0.4 * a_pct, 1)
        band = "Ready" if score >= 80 else ("At Risk" if score >= 55 else "Not Ready")
        out.append({"application": a["name"], "evidence": a["evidence_count"],
                    "controls": 20 + (s % 60), "approved": int(a["evidence_count"] * a_pct / 100),
                    "coverage_pct": c_pct, "approval_pct": a_pct, "score": score, "band": band})
    return out


def audit_readiness() -> dict[str, Any]:
    cov = control_coverage()
    life = evidence_lifecycle()
    fw = framework_coverage()
    total_reviews = life["total"] or 1
    fresh_pct = round(100 * (total_reviews - life["expired"]) / total_reviews, 1)
    score = round(0.5 * cov["coverage_pct"] + 0.3 * life["approval_pct"] + 0.2 * fresh_pct, 1)
    band = "Ready" if score >= 80 else ("At Risk" if score >= 55 else "Not Ready")
    return {"ok": True, "demo": True, "score": score, "band": band,
            "coverage_pct": cov["coverage_pct"], "approval_pct": life["approval_pct"],
            "fresh_pct": fresh_pct, "frameworks": fw["frameworks"], "per_app": _per_app_readiness(),
            "gaps": cov["gaps"], "expired": life["expired"]}


def executive_summary() -> dict[str, Any]:
    inv = list_applications()
    cov = control_coverage()
    fw = framework_coverage()
    reuse = evidence_reuse()
    ready = audit_readiness()
    counts = demo_evidence.counts()
    return {"ok": True, "demo": True,
            "applications": inv["total"], "by_criticality": inv["by_criticality"],
            "total_evidence": counts["total"], "by_source": counts["by_source"],
            "control_coverage_pct": cov["coverage_pct"], "control_gaps": cov["gaps"],
            "framework_coverage_pct": fw["overall_pct"], "reuse_pct": reuse["reuse_pct"],
            "reuse_savings": reuse["reuse_savings"], "correlation_chains": reuse["correlation_chains"],
            "readiness_score": ready["score"], "readiness_band": ready["band"],
            "frameworks": fw["frameworks"], "top_apps": ready["per_app"][:6]}


def governance_scorecard(role: str = "cio") -> dict[str, Any]:
    from ecs_platform.governance import _ROLE_PRESETS  # reuse presets

    preset = _ROLE_PRESETS.get(role, _ROLE_PRESETS["cio"])
    inv = list_applications()
    cov = control_coverage()
    fw = framework_coverage()
    reuse = evidence_reuse()
    life = evidence_lifecycle()
    ready = audit_readiness()
    counts = demo_evidence.counts()
    lc = life["counts"]
    open_obs = int(lc.get("Collected", 0)) + int(lc.get("UnderReview", 0))
    return {"ok": True, "demo": True, "role": role, "title": preset["title"],
            "subtitle": preset["subtitle"], "focus": preset["focus"],
            "kpis": {
                "applications": inv["total"], "evidence_collected": counts["total"],
                "evidence_reuse_pct": reuse["reuse_pct"], "framework_reuse_ratio": reuse["framework_reuse_ratio"],
                "framework_ops_saved": reuse["framework_ops_saved"],
                "framework_coverage_pct": fw["overall_pct"], "control_coverage_pct": cov["coverage_pct"],
                "open_observations": open_obs, "rejected_evidence": int(lc.get("Rejected", 0)),
                "compliance_score": ready["score"], "compliance_band": ready["band"],
            },
            "by_criticality": inv["by_criticality"], "by_source": counts["by_source"],
            "frameworks": fw["frameworks"], "lifecycle": lc, "per_app": ready["per_app"]}


# ---- supplementary enterprise demo datasets --------------------------------
def _app_names() -> list[str]:
    return [a["name"] for a in _applications()]


def servicenow_tickets(count: int = 80) -> list[dict[str, Any]]:
    apps = _app_names()
    types = ["Change", "Incident", "Problem", "Request"]
    states = ["New", "In Progress", "Awaiting Approval", "Resolved", "Closed"]
    prios = ["P1", "P2", "P3", "P4"]
    out = []
    for i in range(count):
        s = _seed("snow", i)
        out.append({
            "ticket_id": f"INC{100000 + (s % 800000)}", "type": _pick(s, types),
            "title": f"{_pick(s >> 4, apps)} — {_pick(s, types).lower()} #{i + 1}",
            "application": _pick(s >> 4, apps), "framework": _pick(s >> 8, _FRAMEWORKS),
            "state": _pick(s >> 12, states), "priority": _pick(s >> 16, prios),
            "owner": _pick(s >> 20, _OWNERS),
            "opened": (_ANCHOR - timedelta(days=(s % 120))).strftime("%Y-%m-%d"),
        })
    return out


def vapt_findings(count: int = 40) -> list[dict[str, Any]]:
    apps = _app_names()
    sev = ["Critical", "High", "Medium", "Low"]
    titles = ["SQL Injection", "XSS", "Broken Auth", "Sensitive Data Exposure",
              "Misconfiguration", "Outdated Component", "SSRF", "IDOR", "Weak Crypto", "CSRF"]
    stat = ["Open", "In Remediation", "Retest Pending", "Closed"]
    out = []
    for i in range(count):
        s = _seed("vapt", i)
        out.append({
            "finding_id": f"VAPT-{2000 + i}", "title": _pick(s, titles),
            "application": _pick(s >> 4, apps), "severity": _pick(s >> 8, sev),
            "cvss": round(2 + (s % 80) / 10, 1), "status": _pick(s >> 12, stat),
            "owner": _pick(s >> 16, _OWNERS),
            "discovered": (_ANCHOR - timedelta(days=(s % 200))).strftime("%Y-%m-%d"),
        })
    return out


def audit_observations(count: int = 120) -> list[dict[str, Any]]:
    apps = _app_names()
    sev = ["Critical", "High", "Medium", "Low"]
    stat = ["Open", "Submitted", "Under Review", "Accepted", "Closed", "Rejected"]
    cats = ["Access Control", "Change Management", "Logging", "DR/BCP", "Data Protection",
            "Vendor Risk", "Patch Management", "Segregation of Duties"]
    out = []
    for i in range(count):
        s = _seed("obs", i)
        opened = _ANCHOR - timedelta(days=(s % 300))
        out.append({
            "observation_id": f"OBS-{5000 + i}", "category": _pick(s, cats),
            "application": _pick(s >> 4, apps), "framework": _pick(s >> 8, _FRAMEWORKS),
            "severity": _pick(s >> 12, sev), "status": _pick(s >> 16, stat),
            "owner": _pick(s >> 20, _OWNERS), "raised_by": _pick(s >> 22, _OWNERS),
            "opened": opened.strftime("%Y-%m-%d"),
            "due": (opened + timedelta(days=30 + (s % 60))).strftime("%Y-%m-%d"),
        })
    return out


def ai_prompts(count: int = 100) -> list[dict[str, Any]]:
    apps = _app_names()
    stages = ["Requirements", "Design", "Development", "Testing", "Go-Live"]
    stat = ["Approved", "Pending Review", "Flagged", "Remediated"]
    out = []
    for i in range(count):
        s = _seed("aiprompt", i)
        halluc = (s % 9 == 0)
        out.append({
            "prompt_id": f"AIP-{3000 + i}", "application": _pick(s, apps),
            "stage": _pick(s >> 4, stages), "model": _pick(s >> 8, ["GPT-4o", "Claude", "Llama-3", "Gemini"]),
            "status": "Flagged" if halluc else _pick(s >> 12, stat),
            "hallucination": halluc, "risk_score": 10 + (s % 90),
            "reviewer": _pick(s >> 16, _OWNERS),
            "audited": (_ANCHOR - timedelta(days=(s % 90))).strftime("%Y-%m-%d"),
        })
    return out


def regions() -> list[dict[str, Any]]:
    out = []
    for r in _REGIONS:
        s = _seed("region", r)
        out.append({
            "region": r, "applications": 40 + (s % 60),
            "score": 62 + (s % 35), "open_observations": 20 + (s % 120),
            "critical_findings": 2 + (s % 18),
        })
    return out


def coverage_summary() -> dict[str, Any]:
    """Single call returning every threshold dataset (for inventory/coverage reporting)."""
    return {
        "applications": list_applications()["total"],
        "frameworks": len(_FRAMEWORKS),
        "controls": control_coverage()["total_controls"],
        "evidence": demo_evidence.counts()["total"],
        "tickets": len(servicenow_tickets()),
        "vapt_findings": len(vapt_findings()),
        "audit_observations": len(audit_observations()),
        "ai_prompts": len(ai_prompts()),
        "business_units": len(_BU),
        "regions": len(_REGIONS),
        "connectors": len(demo_evidence.DEMO_SOURCES),
    }
