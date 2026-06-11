"""ECS governance / management analytics on top of the evidence repository.

Every public function degrades gracefully: if PostgreSQL is unreachable it
returns a structured ``{"ok": False, "error": ...}`` payload instead of raising,
so the dashboards never 500. All returns are JSON-serializable (to_jsonable).
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ecs_platform.ingestion import to_jsonable
from ecs_platform.repository import EvidenceRepository, RepositoryError

_GOV_SCHEMA = Path(__file__).resolve().parent / "repository" / "governance_schema.sql"

_CRITICALITY = ("Critical", "High", "Medium", "Low")
_LIFECYCLE = ("Onboarding", "Active", "Decommissioned")
_REVIEW_STATES = ("Collected", "UnderReview", "Approved", "Rejected", "Expired")
_FREQ_HOURS = {"Hourly": 1, "Daily": 24, "Weekly": 168, "Monthly": 720}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return s or "app"


class _Repo:
    """Context manager yielding a connected EvidenceRepository (or raising RepositoryError)."""

    def __enter__(self):
        self.repo = EvidenceRepository()
        self.repo.connect()
        return self.repo

    def __exit__(self, *exc):
        self.repo.close()


def init_governance_schema() -> dict[str, Any]:
    try:
        sql = _GOV_SCHEMA.read_text(encoding="utf-8")
        with _Repo() as repo:
            with repo.connect().cursor() as cur:
                cur.execute(sql)
        return {"ok": True}
    except RepositoryError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def _rows(cur) -> list[dict[str, Any]]:
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


# --------------------------------------------------------------------------
# 1. Application onboarding
# --------------------------------------------------------------------------
def onboard_application(data: dict[str, Any], *, actor: str = "system", role: str = "owner") -> dict[str, Any]:
    slug = _slugify(data.get("slug") or data.get("name", ""))
    frameworks = data.get("frameworks") or []
    if isinstance(frameworks, str):
        frameworks = [f.strip() for f in frameworks.split(",") if f.strip()]
    try:
        with _Repo() as repo:
            with repo.connect().cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO applications (slug, name, description, owner, owner_email,
                        business_unit, criticality, environment, lifecycle_status, tech_stack, hosting)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (slug) DO UPDATE SET
                        name=EXCLUDED.name, description=EXCLUDED.description, owner=EXCLUDED.owner,
                        owner_email=EXCLUDED.owner_email, business_unit=EXCLUDED.business_unit,
                        criticality=EXCLUDED.criticality, environment=EXCLUDED.environment,
                        lifecycle_status=EXCLUDED.lifecycle_status, tech_stack=EXCLUDED.tech_stack,
                        hosting=EXCLUDED.hosting, updated_at=now()
                    """,
                    (slug, data.get("name", slug), data.get("description", ""), data.get("owner", ""),
                     data.get("owner_email", ""), data.get("business_unit", ""),
                     data.get("criticality", "Medium"), data.get("environment", "Production"),
                     data.get("lifecycle_status", "Active"), data.get("tech_stack", ""),
                     data.get("hosting", "")),
                )
                for fw in frameworks:
                    cur.execute(
                        "INSERT INTO application_frameworks (app_slug, framework_code) VALUES (%s,%s) "
                        "ON CONFLICT DO NOTHING", (slug, fw))
            repo.record_audit(actor, "application.onboard", role=role, resource=slug,
                              detail={"name": data.get("name", slug), "frameworks": frameworks})
        return {"ok": True, "slug": slug}
    except RepositoryError as exc:
        return {"ok": False, "error": str(exc)}


# --------------------------------------------------------------------------
# 2. Application inventory
# --------------------------------------------------------------------------
def list_applications() -> dict[str, Any]:
    try:
        with _Repo() as repo:
            with repo.connect().cursor() as cur:
                cur.execute(
                    """
                    SELECT a.slug, a.name, a.owner, a.business_unit, a.criticality, a.environment,
                           a.lifecycle_status, a.onboarded_at,
                           COALESCE(e.cnt,0) AS evidence_count,
                           COALESCE(f.frameworks,'') AS frameworks
                    FROM applications a
                    LEFT JOIN (SELECT application, count(*) cnt FROM evidence GROUP BY application) e
                           ON e.application = a.slug
                    LEFT JOIN (SELECT app_slug, string_agg(framework_code, ', ' ORDER BY framework_code) frameworks
                               FROM application_frameworks GROUP BY app_slug) f ON f.app_slug = a.slug
                    ORDER BY
                      CASE a.criticality WHEN 'Critical' THEN 0 WHEN 'High' THEN 1
                                         WHEN 'Medium' THEN 2 ELSE 3 END, a.name
                    """)
                apps = _rows(cur)
            by_crit: dict[str, int] = {c: 0 for c in _CRITICALITY}
            by_status: dict[str, int] = {}
            for a in apps:
                by_crit[a["criticality"]] = by_crit.get(a["criticality"], 0) + 1
                by_status[a["lifecycle_status"]] = by_status.get(a["lifecycle_status"], 0) + 1
        return to_jsonable({"ok": True, "applications": apps, "total": len(apps),
                            "by_criticality": by_crit, "by_status": by_status})
    except RepositoryError as exc:
        return {"ok": False, "error": str(exc), "applications": []}


def application_detail(slug: str) -> dict[str, Any]:
    try:
        with _Repo() as repo:
            with repo.connect().cursor() as cur:
                cur.execute("SELECT * FROM applications WHERE slug=%s", (slug,))
                rows = _rows(cur)
                app = rows[0] if rows else None
                cur.execute("SELECT framework_code FROM application_frameworks WHERE app_slug=%s", (slug,))
                fws = [r[0] for r in cur.fetchall()]
            evidence = repo.search_evidence(application=slug, limit=500)
        return to_jsonable({"ok": True, "application": app, "frameworks": fws,
                            "evidence": evidence, "evidence_count": len(evidence)})
    except RepositoryError as exc:
        return {"ok": False, "error": str(exc)}


# --------------------------------------------------------------------------
# 3. Evidence reuse
# --------------------------------------------------------------------------
def evidence_reuse() -> dict[str, Any]:
    try:
        with _Repo() as repo, repo.connect().cursor() as cur:
            cur.execute("SELECT count(*) FROM evidence")
            total = cur.fetchone()[0]
            # control links + multi-control reuse
            cur.execute("SELECT count(*) FROM evidence_control_map")
            total_links = cur.fetchone()[0]
            cur.execute("SELECT count(DISTINCT evidence_id) FROM evidence_control_map")
            mapped = cur.fetchone()[0]
            cur.execute(
                "SELECT count(*) FROM (SELECT evidence_id FROM evidence_control_map "
                "GROUP BY evidence_id HAVING count(*) > 1) t")
            multi_control = cur.fetchone()[0]
            # per-control reuse (how many evidence support each control)
            cur.execute(
                "SELECT control_id, count(*) c FROM evidence_control_map GROUP BY 1 ORDER BY 2 DESC")
            by_control = _rows(cur)
            # cross-source reuse via correlation chains
            cur.execute("SELECT count(*) FROM correlation_groups")
            chains = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM correlation_members")
            chain_members = cur.fetchone()[0]
            # duplicate artifacts reused across applications (same content_hash, >1 app)
            cur.execute(
                "SELECT count(*) FROM (SELECT content_hash FROM evidence "
                "GROUP BY content_hash HAVING count(DISTINCT application) > 1) t")
            shared_artifacts = cur.fetchone()[0]
            cur.execute(
                "SELECT framework_code, count(*) c FROM evidence_framework_map GROUP BY 1 ORDER BY 2 DESC")
            by_framework = _rows(cur)
        reuse_ratio = round(total_links / mapped, 2) if mapped else 0.0
        # reuse rate: share of control links beyond first unique = saved collection effort
        saved = max(0, total_links - mapped)
        reuse_pct = round(100 * saved / total_links, 1) if total_links else 0.0
        return to_jsonable({
            "ok": True, "total_evidence": total, "control_links": total_links,
            "evidence_with_controls": mapped, "multi_control_evidence": multi_control,
            "reuse_ratio": reuse_ratio, "reuse_savings": saved, "reuse_pct": reuse_pct,
            "correlation_chains": chains, "chain_members": chain_members,
            "shared_artifacts": shared_artifacts,
            "by_control": by_control, "by_framework": by_framework,
        })
    except RepositoryError as exc:
        return {"ok": False, "error": str(exc), "by_control": [], "by_framework": []}


# --------------------------------------------------------------------------
# 4. Control coverage
# --------------------------------------------------------------------------
def control_coverage() -> dict[str, Any]:
    try:
        with _Repo() as repo, repo.connect().cursor() as cur:
            cur.execute("SELECT control_id, name, domain, framework_code FROM control_catalog ORDER BY control_id")
            catalog = _rows(cur)
            cur.execute(
                """
                SELECT m.control_id, count(DISTINCT m.evidence_id) AS evidence_count,
                       count(DISTINCT e.application) AS app_count
                FROM evidence_control_map m JOIN evidence e ON e.id = m.evidence_id
                GROUP BY m.control_id
                """)
            stats = {r["control_id"]: r for r in _rows(cur)}
        rows = []
        covered = 0
        for c in catalog:
            s = stats.get(c["control_id"], {})
            ev = int(s.get("evidence_count", 0) or 0)
            apps = int(s.get("app_count", 0) or 0)
            status = "Covered" if ev > 0 else "Gap"
            if ev > 0:
                covered += 1
            rows.append({**c, "evidence_count": ev, "app_count": apps, "status": status})
        total = len(catalog)
        # controls that have evidence but are not in the catalog (discovered)
        extra = sorted(set(stats) - {c["control_id"] for c in catalog})
        pct = round(100 * covered / total, 1) if total else 0.0
        return to_jsonable({
            "ok": True, "controls": rows, "total_controls": total, "covered": covered,
            "gaps": total - covered, "coverage_pct": pct, "discovered_controls": extra,
        })
    except RepositoryError as exc:
        return {"ok": False, "error": str(exc), "controls": []}


# --------------------------------------------------------------------------
# 5. Framework coverage
# --------------------------------------------------------------------------
def framework_coverage() -> dict[str, Any]:
    """Coverage per framework, rolled up through the control catalog taxonomy.

    Evidence is attributed to a framework via control_catalog.framework_code (a
    single clean taxonomy) rather than the connectors' raw sub-codes, so the
    dashboard shows SOC2/ISO27001/PCI-DSS/RBI-CSF rather than CC7/CC8/A.14.
    """
    try:
        with _Repo() as repo, repo.connect().cursor() as cur:
            cur.execute(
                """
                SELECT cc.framework_code,
                       count(DISTINCT cc.control_id) AS expected,
                       count(DISTINCT cc.control_id) FILTER (WHERE m.evidence_id IS NOT NULL) AS covered,
                       count(DISTINCT m.evidence_id) AS evidence_count
                FROM control_catalog cc
                LEFT JOIN evidence_control_map m ON m.control_id = cc.control_id
                WHERE cc.framework_code IS NOT NULL AND cc.framework_code <> ''
                GROUP BY cc.framework_code
                ORDER BY cc.framework_code
                """)
            data = _rows(cur)
        rows = []
        for r in data:
            exp = int(r["expected"] or 0)
            cov = int(r["covered"] or 0)
            pct = round(100 * cov / exp, 1) if exp else 0.0
            rows.append({"framework_code": r["framework_code"], "expected_controls": exp,
                         "covered_controls": cov, "evidence_count": int(r["evidence_count"] or 0),
                         "coverage_pct": pct})
        overall = round(sum(r["coverage_pct"] for r in rows) / len(rows), 1) if rows else 0.0
        return to_jsonable({"ok": True, "frameworks": rows, "overall_pct": overall})
    except RepositoryError as exc:
        return {"ok": False, "error": str(exc), "frameworks": []}


# --------------------------------------------------------------------------
# 6. Scheduler
# --------------------------------------------------------------------------
def list_schedules() -> dict[str, Any]:
    try:
        with _Repo() as repo, repo.connect().cursor() as cur:
            cur.execute(
                "SELECT id, name, connector, app_slug, frequency, owner, enabled, last_run, "
                "last_status, next_run FROM collection_schedules ORDER BY next_run NULLS LAST, id")
            rows = _rows(cur)
        now = _now()
        due = sum(1 for r in rows if r.get("next_run") and r["next_run"] <= now)
        enabled = sum(1 for r in rows if r.get("enabled"))
        return to_jsonable({"ok": True, "schedules": rows, "total": len(rows),
                            "enabled": enabled, "due": due})
    except RepositoryError as exc:
        return {"ok": False, "error": str(exc), "schedules": []}


def upsert_schedule(name: str, *, connector: str = "", app_slug: str = "", frequency: str = "Daily",
                    owner: str = "", actor: str = "system") -> dict[str, Any]:
    hrs = _FREQ_HOURS.get(frequency, 24)
    nxt = _now() + timedelta(hours=hrs)
    try:
        with _Repo() as repo:
            with repo.connect().cursor() as cur:
                cur.execute(
                    "INSERT INTO collection_schedules (name, connector, app_slug, frequency, owner, next_run) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (name, connector, app_slug, frequency, owner, nxt))
            repo.record_audit(actor, "schedule.create", resource=name,
                              detail={"connector": connector, "frequency": frequency})
        return {"ok": True}
    except RepositoryError as exc:
        return {"ok": False, "error": str(exc)}


# --------------------------------------------------------------------------
# 7. Evidence lifecycle
# --------------------------------------------------------------------------
def evidence_lifecycle(status: str = "", limit: int = 200) -> dict[str, Any]:
    try:
        with _Repo() as repo, repo.connect().cursor() as cur:
            # ensure every evidence row has a review row (default Collected)
            cur.execute(
                "INSERT INTO evidence_reviews (evidence_uid) "
                "SELECT evidence_uid FROM evidence ON CONFLICT DO NOTHING")
            cur.execute(
                "SELECT status, count(*) c FROM evidence_reviews GROUP BY 1")
            counts = {r["status"]: int(r["c"]) for r in _rows(cur)}
            clause = "WHERE r.status = %s" if status else ""
            params: list[Any] = [status] if status else []
            params.append(limit)
            cur.execute(
                f"""
                SELECT e.evidence_uid, e.source_system, e.object_type, e.title, e.application,
                       r.status, r.reviewer, r.reviewed_at, r.valid_until
                FROM evidence_reviews r JOIN evidence e ON e.evidence_uid = r.evidence_uid
                {clause}
                ORDER BY e.collected_timestamp DESC LIMIT %s
                """, params)
            rows = _rows(cur)
            # freshness: evidence past valid_until
            cur.execute("SELECT count(*) FROM evidence_reviews WHERE valid_until IS NOT NULL AND valid_until < now()")
            expired = cur.fetchone()[0]
        ordered = {s: counts.get(s, 0) for s in _REVIEW_STATES}
        total = sum(ordered.values())
        approved = ordered.get("Approved", 0)
        approval_pct = round(100 * approved / total, 1) if total else 0.0
        return to_jsonable({"ok": True, "counts": ordered, "rows": rows, "total": total,
                            "expired": expired, "approval_pct": approval_pct, "states": list(_REVIEW_STATES)})
    except RepositoryError as exc:
        return {"ok": False, "error": str(exc), "counts": {}, "rows": []}


def set_review_status(evidence_uid: str, status: str, *, reviewer: str = "system",
                      note: str = "", valid_days: int = 0, actor: str = "system") -> dict[str, Any]:
    if status not in _REVIEW_STATES:
        return {"ok": False, "error": f"invalid status: {status}"}
    valid_until = _now() + timedelta(days=valid_days) if valid_days else None
    try:
        with _Repo() as repo:
            with repo.connect().cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO evidence_reviews (evidence_uid, status, reviewer, note, reviewed_at, valid_until)
                    VALUES (%s,%s,%s,%s,now(),%s)
                    ON CONFLICT (evidence_uid) DO UPDATE SET status=EXCLUDED.status,
                        reviewer=EXCLUDED.reviewer, note=EXCLUDED.note, reviewed_at=now(),
                        valid_until=COALESCE(EXCLUDED.valid_until, evidence_reviews.valid_until),
                        updated_at=now()
                    """, (evidence_uid, status, reviewer, note, valid_until))
            repo.record_audit(actor, "evidence.review", resource=evidence_uid,
                              detail={"status": status, "note": note})
        return {"ok": True}
    except RepositoryError as exc:
        return {"ok": False, "error": str(exc)}


# --------------------------------------------------------------------------
# 8. Audit readiness
# --------------------------------------------------------------------------
def audit_readiness() -> dict[str, Any]:
    """Composite readiness = 50% control coverage + 30% approved evidence + 20% freshness."""
    cov = control_coverage()
    life = evidence_lifecycle()
    fw = framework_coverage()
    if not cov.get("ok") or not life.get("ok"):
        return {"ok": False, "error": cov.get("error") or life.get("error"), "frameworks": []}

    coverage_pct = cov.get("coverage_pct", 0.0)
    approval_pct = life.get("approval_pct", 0.0)
    total_reviews = life.get("total", 0) or 1
    fresh_pct = round(100 * (total_reviews - life.get("expired", 0)) / total_reviews, 1)
    score = round(0.5 * coverage_pct + 0.3 * approval_pct + 0.2 * fresh_pct, 1)

    def band(s: float) -> str:
        return "Ready" if s >= 80 else ("At Risk" if s >= 55 else "Not Ready")

    # per-application readiness
    try:
        with _Repo() as repo, repo.connect().cursor() as cur:
            cur.execute(
                """
                SELECT e.application,
                       count(DISTINCT e.id) AS evidence,
                       count(DISTINCT m.control_id) AS controls,
                       count(DISTINCT r.evidence_uid) FILTER (WHERE r.status='Approved') AS approved
                FROM evidence e
                LEFT JOIN evidence_control_map m ON m.evidence_id = e.id
                LEFT JOIN evidence_reviews r ON r.evidence_uid = e.evidence_uid
                WHERE e.application <> ''
                GROUP BY e.application ORDER BY e.application
                """)
            app_rows = _rows(cur)
    except RepositoryError as exc:
        return {"ok": False, "error": str(exc), "frameworks": []}

    catalog_total = cov.get("total_controls", 0) or 1
    per_app = []
    for a in app_rows:
        c_pct = round(100 * int(a["controls"] or 0) / catalog_total, 1)
        ev = int(a["evidence"] or 0)
        appr = int(a["approved"] or 0)
        a_pct = round(100 * appr / ev, 1) if ev else 0.0
        s = round(0.6 * c_pct + 0.4 * a_pct, 1)
        per_app.append({"application": a["application"], "evidence": ev, "controls": int(a["controls"] or 0),
                        "approved": appr, "coverage_pct": c_pct, "approval_pct": a_pct,
                        "score": s, "band": band(s)})

    return to_jsonable({
        "ok": True, "score": score, "band": band(score),
        "coverage_pct": coverage_pct, "approval_pct": approval_pct, "fresh_pct": fresh_pct,
        "frameworks": fw.get("frameworks", []), "per_app": per_app,
        "gaps": cov.get("gaps", 0), "expired": life.get("expired", 0),
    })


# --------------------------------------------------------------------------
# 9. Executive summary
# --------------------------------------------------------------------------
def executive_summary() -> dict[str, Any]:
    inv = list_applications()
    cov = control_coverage()
    fw = framework_coverage()
    reuse = evidence_reuse()
    ready = audit_readiness()
    try:
        with _Repo() as repo:
            counts = repo.counts()
    except RepositoryError as exc:
        return {"ok": False, "error": str(exc)}
    return to_jsonable({
        "ok": True,
        "applications": inv.get("total", 0),
        "by_criticality": inv.get("by_criticality", {}),
        "total_evidence": counts.get("total", 0),
        "by_source": counts.get("by_source", {}),
        "control_coverage_pct": cov.get("coverage_pct", 0.0),
        "control_gaps": cov.get("gaps", 0),
        "framework_coverage_pct": fw.get("overall_pct", 0.0),
        "reuse_pct": reuse.get("reuse_pct", 0.0),
        "reuse_savings": reuse.get("reuse_savings", 0),
        "correlation_chains": reuse.get("correlation_chains", 0),
        "readiness_score": ready.get("score", 0.0),
        "readiness_band": ready.get("band", "Unknown"),
        "frameworks": fw.get("frameworks", []),
        "top_apps": (ready.get("per_app") or [])[:6],
    })


# --------------------------------------------------------------------------
# 10. Repository-aware assistant (no LLM key required)
# --------------------------------------------------------------------------
def governance_qa(question: str) -> dict[str, Any]:
    q = (question or "").lower()
    try:
        if any(w in q for w in ("ready", "audit", "readiness")):
            r = audit_readiness()
            return {"ok": True, "answer": (
                f"Audit readiness is {r.get('score')}% ({r.get('band')}). "
                f"Control coverage {r.get('coverage_pct')}%, approved evidence {r.get('approval_pct')}%, "
                f"freshness {r.get('fresh_pct')}%. Open control gaps: {r.get('gaps')}."), "data": r}
        if "reuse" in q:
            r = evidence_reuse()
            return {"ok": True, "answer": (
                f"Evidence reuse is {r.get('reuse_pct')}% ({r.get('reuse_savings')} collection operations saved). "
                f"{r.get('correlation_chains')} correlation chains link evidence across tools."), "data": r}
        if "framework" in q:
            r = framework_coverage()
            top = ", ".join(f"{x['framework_code']} {x['coverage_pct']}%" for x in r.get("frameworks", [])[:5])
            return {"ok": True, "answer": f"Framework coverage (overall {r.get('overall_pct')}%): {top}", "data": r}
        if any(w in q for w in ("control", "coverage", "gap")):
            r = control_coverage()
            return {"ok": True, "answer": (
                f"Control coverage is {r.get('coverage_pct')}% — {r.get('covered')}/{r.get('total_controls')} "
                f"controls have evidence, {r.get('gaps')} gaps remain."), "data": r}
        if any(w in q for w in ("application", "app", "inventory", "portfolio")):
            r = list_applications()
            return {"ok": True, "answer": (
                f"{r.get('total')} applications onboarded. By criticality: "
                + ", ".join(f"{k} {v}" for k, v in r.get("by_criticality", {}).items() if v)), "data": r}
        r = executive_summary()
        return {"ok": True, "answer": (
            f"ECS tracks {r.get('applications')} applications and {r.get('total_evidence')} evidence records. "
            f"Readiness {r.get('readiness_score')}% ({r.get('readiness_band')}), control coverage "
            f"{r.get('control_coverage_pct')}%, framework coverage {r.get('framework_coverage_pct')}%."), "data": r}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "answer": "Repository not reachable."}
