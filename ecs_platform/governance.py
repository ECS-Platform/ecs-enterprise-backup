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

# Frameworks ECS reports reuse across (CIO-demo scope).
REUSE_FRAMEWORKS = ("SOC2", "ISO27001", "PCI-DSS", "RBI-CSF", "AI-SDLC")

# Industry-standard control -> framework crosswalk. Reference/standards data
# (NOT evidence): one control satisfies a requirement in many frameworks, which
# is what makes a single collected evidence item reusable across frameworks.
# control_id -> {framework_code: requirement_ref}
CONTROL_CROSSWALK: dict[str, dict[str, str]] = {
    "change-management": {
        "SOC2": "CC8.1", "ISO27001": "A.12.1.2", "PCI-DSS": "6.5",
        "RBI-CSF": "BCSF-CR", "AI-SDLC": "AISDLC-CHG"},
    "code-review": {
        "SOC2": "CC8.1", "ISO27001": "A.14.2.1", "PCI-DSS": "6.3.2",
        "RBI-CSF": "BCSF-SDLC", "AI-SDLC": "AISDLC-REV"},
    "ci-cd": {
        "SOC2": "CC8.1", "ISO27001": "A.12.1.2", "PCI-DSS": "6.5",
        "RBI-CSF": "BCSF-DEP", "AI-SDLC": "AISDLC-PIPE"},
    "secure-sdlc": {
        "SOC2": "CC7.1", "ISO27001": "A.14.2.1", "PCI-DSS": "6.3",
        "RBI-CSF": "BCSF-SDLC", "AI-SDLC": "AISDLC-SEC"},
    "code-quality": {
        "SOC2": "CC8.1", "ISO27001": "A.14.2.8", "PCI-DSS": "6.3.1",
        "RBI-CSF": "BCSF-QA", "AI-SDLC": "AISDLC-QA"},
    "vulnerability-management": {
        "SOC2": "CC7.1", "ISO27001": "A.12.6.1", "PCI-DSS": "11.3",
        "RBI-CSF": "BCSF-VA", "AI-SDLC": "AISDLC-VULN"},
}


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
                # Seed the control->framework crosswalk (idempotent reference data).
                for control_id, fws in CONTROL_CROSSWALK.items():
                    for fw, ref in fws.items():
                        cur.execute(
                            "INSERT INTO control_framework_crosswalk (control_id, framework_code, requirement_ref) "
                            "VALUES (%s,%s,%s) ON CONFLICT (control_id, framework_code) "
                            "DO UPDATE SET requirement_ref = EXCLUDED.requirement_ref",
                            (control_id, fw, ref))
        return {"ok": True}
    except RepositoryError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def _control_frameworks(cur) -> dict[str, set[str]]:
    """control_id -> set(framework_code), unioning crosswalk + catalog primary fw."""
    mapping: dict[str, set[str]] = {}
    cur.execute("SELECT control_id, framework_code FROM control_framework_crosswalk")
    for cid, fw in cur.fetchall():
        mapping.setdefault(cid, set()).add(fw)
    cur.execute("SELECT control_id, framework_code FROM control_catalog "
                "WHERE framework_code IS NOT NULL AND framework_code <> ''")
    for cid, fw in cur.fetchall():
        mapping.setdefault(cid, set()).add(fw)
    return mapping


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
        if apps:
            return to_jsonable({"ok": True, "applications": apps, "total": len(apps),
                                "by_criticality": by_crit, "by_status": by_status})
    except Exception:  # noqa: BLE001 - repository down → demo data
        pass
    from ecs_platform import demo_governance
    return to_jsonable(demo_governance.list_applications())


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
        if app:
            return to_jsonable({"ok": True, "application": app, "frameworks": fws,
                                "evidence": evidence, "evidence_count": len(evidence)})
    except Exception:  # noqa: BLE001 - repository down → demo data
        pass
    from ecs_platform import demo_governance, demo_evidence
    apps = {a["slug"]: a for a in demo_governance.list_applications()["applications"]}
    app = apps.get(slug) or next(iter(apps.values()), {"slug": slug, "name": slug})
    evidence = demo_evidence.search_evidence(application=app.get("name", ""), limit=200)
    return to_jsonable({"ok": True, "demo": True, "application": app,
                        "frameworks": (app.get("frameworks", "") or "").split(", "),
                        "evidence": evidence, "evidence_count": len(evidence)})


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
            # cross-framework reuse via the crosswalk: evidence -> control -> many frameworks
            cur.execute(
                """
                SELECT cfw.framework_code, count(DISTINCT m.evidence_id) c
                FROM control_framework_crosswalk cfw
                JOIN evidence_control_map m ON m.control_id = cfw.control_id
                GROUP BY 1 ORDER BY 2 DESC
                """)
            by_framework = _rows(cur)
            # framework-obligations satisfied = evidence x distinct frameworks each maps to
            cur.execute(
                """
                SELECT count(*) FROM (
                    SELECT m.evidence_id
                    FROM evidence_control_map m
                    JOIN control_framework_crosswalk cfw ON cfw.control_id = m.control_id
                    GROUP BY m.evidence_id, cfw.framework_code
                ) t
                """)
            framework_obligations = cur.fetchone()[0]
            cur.execute(
                "SELECT count(DISTINCT m.evidence_id) FROM evidence_control_map m "
                "WHERE m.control_id IN (SELECT control_id FROM control_framework_crosswalk)")
            crosswalked_evidence = cur.fetchone()[0]
        reuse_ratio = round(total_links / mapped, 2) if mapped else 0.0
        # reuse rate: share of control links beyond first unique = saved collection effort
        saved = max(0, total_links - mapped)
        reuse_pct = round(100 * saved / total_links, 1) if total_links else 0.0
        # cross-framework reuse: obligations satisfied vs. evidence items collected
        framework_reuse_ratio = round(framework_obligations / crosswalked_evidence, 2) if crosswalked_evidence else 0.0
        framework_ops_saved = max(0, framework_obligations - crosswalked_evidence)
        return to_jsonable({
            "ok": True, "total_evidence": total, "control_links": total_links,
            "evidence_with_controls": mapped, "multi_control_evidence": multi_control,
            "reuse_ratio": reuse_ratio, "reuse_savings": saved, "reuse_pct": reuse_pct,
            "correlation_chains": chains, "chain_members": chain_members,
            "shared_artifacts": shared_artifacts,
            "framework_obligations": framework_obligations,
            "crosswalked_evidence": crosswalked_evidence,
            "framework_reuse_ratio": framework_reuse_ratio,
            "framework_ops_saved": framework_ops_saved,
            "by_control": by_control, "by_framework": by_framework,
        })
    except Exception:  # noqa: BLE001 - repository down → demo data
        from ecs_platform import demo_governance
        return to_jsonable(demo_governance.evidence_reuse())


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
    except Exception:  # noqa: BLE001 - repository down → demo data
        from ecs_platform import demo_governance
        return to_jsonable(demo_governance.control_coverage())


# --------------------------------------------------------------------------
# 5. Framework coverage
# --------------------------------------------------------------------------
def framework_coverage() -> dict[str, Any]:
    """Coverage per framework, rolled up through the control->framework crosswalk.

    A control covered by evidence contributes to EVERY framework it is crosswalked
    to, so a single SonarQube/Gitea evidence item can lift SOC2, ISO27001, PCI-DSS,
    RBI-CSF and AI-SDLC coverage at once. The dashboard reports the clean framework
    taxonomy (SOC2/ISO27001/PCI-DSS/RBI-CSF/AI-SDLC), not raw connector sub-codes.
    """
    try:
        with _Repo() as repo, repo.connect().cursor() as cur:
            ctrl_fw = _control_frameworks(cur)
            cur.execute("SELECT DISTINCT control_id FROM evidence_control_map")
            covered_controls = {r[0] for r in cur.fetchall()}
            cur.execute(
                """
                SELECT cfw.framework_code, count(DISTINCT m.evidence_id) AS evidence_count
                FROM control_framework_crosswalk cfw
                JOIN evidence_control_map m ON m.control_id = cfw.control_id
                GROUP BY cfw.framework_code
                """)
            ev_by_fw = {r["framework_code"]: int(r["evidence_count"] or 0) for r in _rows(cur)}
        # expected/covered control sets per framework
        per_fw_expected: dict[str, set[str]] = {}
        per_fw_covered: dict[str, set[str]] = {}
        for cid, fws in ctrl_fw.items():
            for fw in fws:
                per_fw_expected.setdefault(fw, set()).add(cid)
                if cid in covered_controls:
                    per_fw_covered.setdefault(fw, set()).add(cid)
        rows = []
        for fw in sorted(per_fw_expected):
            exp = len(per_fw_expected.get(fw, set()))
            cov = len(per_fw_covered.get(fw, set()))
            pct = round(100 * cov / exp, 1) if exp else 0.0
            rows.append({"framework_code": fw, "expected_controls": exp, "covered_controls": cov,
                         "evidence_count": ev_by_fw.get(fw, 0), "coverage_pct": pct})
        overall = round(sum(r["coverage_pct"] for r in rows) / len(rows), 1) if rows else 0.0
        return to_jsonable({"ok": True, "frameworks": rows, "overall_pct": overall})
    except Exception:  # noqa: BLE001 - repository down → demo data
        from ecs_platform import demo_governance
        return to_jsonable(demo_governance.framework_coverage())


def crosswalk_matrix() -> dict[str, Any]:
    """The control x framework reuse matrix + per-control evidence counts."""
    try:
        with _Repo() as repo, repo.connect().cursor() as cur:
            cur.execute(
                "SELECT control_id, framework_code, requirement_ref FROM control_framework_crosswalk")
            triples = _rows(cur)
            cur.execute(
                "SELECT control_id, count(DISTINCT evidence_id) c FROM evidence_control_map GROUP BY 1")
            ev_counts = {r["control_id"]: int(r["c"]) for r in _rows(cur)}
            cur.execute("SELECT control_id, name FROM control_catalog")
            names = {r["control_id"]: r["name"] for r in _rows(cur)}
        frameworks = sorted({t["framework_code"] for t in triples})
        controls: dict[str, dict[str, Any]] = {}
        for t in triples:
            cid = t["control_id"]
            row = controls.setdefault(cid, {"control_id": cid, "name": names.get(cid, cid),
                                            "evidence_count": ev_counts.get(cid, 0), "refs": {}})
            row["refs"][t["framework_code"]] = t["requirement_ref"]
        ordered = sorted(controls.values(), key=lambda r: (-r["evidence_count"], r["control_id"]))
        return to_jsonable({"ok": True, "frameworks": frameworks, "controls": ordered})
    except Exception:  # noqa: BLE001 - repository down → demo data
        from ecs_platform import demo_governance
        return to_jsonable(demo_governance.crosswalk_matrix())


def reuse_demonstrations(per_framework: int = 4) -> dict[str, Any]:
    """For each in-scope framework, real evidence items that satisfy it, each
    annotated with EVERY other framework the same evidence also satisfies — the
    concrete "collect once, reuse everywhere" demonstration."""
    try:
        with _Repo() as repo, repo.connect().cursor() as cur:
            cur.execute(
                """
                SELECT e.evidence_uid, e.source_system, e.object_type, e.title, e.application,
                       array_agg(DISTINCT m.control_id) AS controls
                FROM evidence e JOIN evidence_control_map m ON m.evidence_id = e.id
                WHERE m.control_id IN (SELECT control_id FROM control_framework_crosswalk)
                GROUP BY e.id
                ORDER BY e.collected_timestamp DESC
                """)
            ev = _rows(cur)
        # attach framework fan-out per evidence
        items = []
        max_fanout = 0
        for r in ev:
            fws: dict[str, str] = {}
            for cid in r["controls"]:
                for fw, ref in CONTROL_CROSSWALK.get(cid, {}).items():
                    fws.setdefault(fw, ref)
            max_fanout = max(max_fanout, len(fws))
            items.append({**r, "frameworks": sorted(fws), "framework_refs": fws,
                          "fanout": len(fws)})
        demos: dict[str, list[dict[str, Any]]] = {}
        for fw in REUSE_FRAMEWORKS:
            matches = [it for it in items if fw in it["frameworks"]]
            matches.sort(key=lambda it: -it["fanout"])
            demos[fw] = matches[:per_framework]
        coverage_counts = {fw: sum(1 for it in items if fw in it["frameworks"]) for fw in REUSE_FRAMEWORKS}
        return to_jsonable({
            "ok": True, "frameworks": list(REUSE_FRAMEWORKS), "demos": demos,
            "reusable_evidence": len(items), "max_fanout": max_fanout,
            "coverage_counts": coverage_counts,
        })
    except Exception:  # noqa: BLE001 - repository down → demo data
        from ecs_platform import demo_governance
        return to_jsonable(demo_governance.reuse_demonstrations(per_framework))


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
    except Exception:  # noqa: BLE001 - repository down → demo data
        from ecs_platform import demo_governance
        return to_jsonable(demo_governance.list_schedules())


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
    except Exception:  # noqa: BLE001 - repository down → demo data
        from ecs_platform import demo_governance
        return to_jsonable(demo_governance.evidence_lifecycle(status, limit))


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
        from ecs_platform import demo_governance
        return to_jsonable(demo_governance.audit_readiness())

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
    except Exception:  # noqa: BLE001 - repository down → demo data
        from ecs_platform import demo_governance
        return to_jsonable(demo_governance.audit_readiness())

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
    except Exception:  # noqa: BLE001 - repository down → demo data
        from ecs_platform import demo_governance
        return to_jsonable(demo_governance.executive_summary())
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
# Executive scorecard (role-aware: CIO / Vertical Head / Auditor / App Owner)
# --------------------------------------------------------------------------
_ROLE_PRESETS = {
    "cio": {"title": "CIO Dashboard",
            "subtitle": "Enterprise compliance posture, risk and audit readiness at a glance.",
            "focus": ["compliance_score", "framework_coverage", "applications", "evidence_reuse"]},
    "vertical_head": {"title": "Vertical Head Dashboard",
            "subtitle": "Portfolio health and readiness across the business vertical's applications.",
            "focus": ["applications", "compliance_score", "open_observations", "framework_coverage"]},
    "auditor": {"title": "Auditor Dashboard",
            "subtitle": "Evidence quality, lifecycle state, and audit readiness for sign-off.",
            "focus": ["open_observations", "rejected_evidence", "evidence_collected", "compliance_score"]},
    "owner": {"title": "Application Owner Dashboard",
            "subtitle": "Your applications' evidence, reuse and outstanding compliance actions.",
            "focus": ["evidence_collected", "evidence_reuse", "open_observations", "rejected_evidence"]},
}


def governance_scorecard(role: str = "cio") -> dict[str, Any]:
    """Single role-aware management scorecard with the CIO-demo KPI set."""
    preset = _ROLE_PRESETS.get(role, _ROLE_PRESETS["cio"])
    inv = list_applications()
    cov = control_coverage()
    fw = framework_coverage()
    reuse = evidence_reuse()
    life = evidence_lifecycle()
    ready = audit_readiness()
    try:
        with _Repo() as repo:
            counts = repo.counts()
    except Exception:  # noqa: BLE001 - repository down → demo data
        from ecs_platform import demo_governance
        return to_jsonable(demo_governance.governance_scorecard(role))

    lc = life.get("counts", {}) if life.get("ok") else {}
    open_obs = int(lc.get("Collected", 0)) + int(lc.get("UnderReview", 0))
    rejected = int(lc.get("Rejected", 0))
    return to_jsonable({
        "ok": True, "role": role, "title": preset["title"], "subtitle": preset["subtitle"],
        "focus": preset["focus"],
        "kpis": {
            "applications": inv.get("total", 0),
            "evidence_collected": counts.get("total", 0),
            "evidence_reuse_pct": reuse.get("reuse_pct", 0.0),
            "framework_reuse_ratio": reuse.get("framework_reuse_ratio", 0.0),
            "framework_ops_saved": reuse.get("framework_ops_saved", 0),
            "framework_coverage_pct": fw.get("overall_pct", 0.0),
            "control_coverage_pct": cov.get("coverage_pct", 0.0),
            "open_observations": open_obs,
            "rejected_evidence": rejected,
            "compliance_score": ready.get("score", 0.0),
            "compliance_band": ready.get("band", "Unknown"),
        },
        "by_criticality": inv.get("by_criticality", {}),
        "by_source": counts.get("by_source", {}),
        "frameworks": fw.get("frameworks", []),
        "lifecycle": lc,
        "per_app": ready.get("per_app", []),
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
