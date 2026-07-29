"""Phase 2 Evidence Completeness Detection (backend service).

Computes per-control completeness for an application × framework using:

* **Expected controls** — Framework Control Master (FCM) YAML
* **Persisted evidence** — PostgreSQL ``evidence`` / ``evidence_control_map`` /
  ``evidence_reviews`` (plus optional catalog/crosswalk enrichment)

Does not compute Audit Readiness scores and does not touch UI/routes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from ecs_platform.ingestion import to_jsonable
from ecs_platform.repository import EvidenceRepository, RepositoryError

STATUS_COMPLETE = "COMPLETE"
STATUS_PARTIAL = "PARTIAL"
STATUS_MISSING = "MISSING"

_APPROVED = frozenset({"approved", "accepted"})
_EXPIRED_STATUSES = frozenset({"expired"})


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _resolve_fcm_framework(framework: str, fcm_repo) -> tuple[str, dict[str, Any]]:
    """Return (framework_id, framework_doc) or raise ValueError."""
    raw = _norm(framework)
    if not raw:
        raise ValueError("framework is required")
    fw_id = fcm_repo.resolve_framework_id(
        raw.lower().replace(" ", "_").replace("-", "_")
    )
    doc = fcm_repo.get_framework(fw_id)
    if not doc:
        # Try display-name match
        for summary in fcm_repo.list_framework_summaries():
            names = {
                _norm(summary.get("id")).lower(),
                _norm(summary.get("code")).lower(),
                _norm(summary.get("name")).lower(),
                _norm(summary.get("display_name")).lower(),
            }
            if raw.lower() in names or raw.lower().replace(" ", "_") in names:
                fw_id = str(summary.get("id") or fw_id)
                doc = fcm_repo.get_framework(fw_id)
                break
    if not doc:
        raise ValueError(f"Unknown framework: {framework}")
    return str((doc.get("framework") or {}).get("id") or fw_id), doc


def _expected_controls_from_fcm(doc: dict[str, Any]) -> list[dict[str, str]]:
    """Build the expected-control list from an FCM framework document."""
    rows: list[dict[str, str]] = []
    for control in doc.get("controls") or []:
        cid = _norm(control.get("id"))
        if not cid:
            continue
        rows.append(
            {
                "control_id": cid,
                "control_title": _norm(control.get("title")) or cid,
                "domain": _norm(control.get("domain")),
            }
        )
    return rows


def _expected_controls_from_catalog(
    repo: EvidenceRepository,
    framework_code: str,
) -> list[dict[str, str]]:
    """Expected controls from ``control_catalog`` + ``control_framework_crosswalk``.

    Used when the selected framework is present in Audit Readiness coverage but
    has no FCM YAML document (e.g. ISO27001 / SOC2).
    """
    code = _norm(framework_code)
    if not code:
        return []
    by_id: dict[str, dict[str, str]] = {}
    with repo.connect().cursor() as cur:
        cur.execute(
            """
            SELECT control_id, COALESCE(name, control_id), COALESCE(domain, '')
            FROM control_catalog
            WHERE framework_code = %s
            ORDER BY control_id
            """,
            (code,),
        )
        for cid, name, domain in cur.fetchall():
            key = _norm(cid)
            if key:
                by_id[key] = {
                    "control_id": key,
                    "control_title": _norm(name) or key,
                    "domain": _norm(domain),
                }
        try:
            cur.execute(
                """
                SELECT DISTINCT cfw.control_id,
                       COALESCE(c.name, cfw.control_id),
                       COALESCE(c.domain, '')
                FROM control_framework_crosswalk cfw
                LEFT JOIN control_catalog c ON c.control_id = cfw.control_id
                WHERE cfw.framework_code = %s
                ORDER BY 1
                """,
                (code,),
            )
            for cid, name, domain in cur.fetchall():
                key = _norm(cid)
                if key and key not in by_id:
                    by_id[key] = {
                        "control_id": key,
                        "control_title": _norm(name) or key,
                        "domain": _norm(domain),
                    }
        except Exception:  # noqa: BLE001 - crosswalk optional
            pass
    return [by_id[k] for k in sorted(by_id)]


def _is_expired(review_status: str, valid_until: Any, *, now: datetime) -> bool:
    if _norm(review_status).lower() in _EXPIRED_STATUSES:
        return True
    if valid_until is None:
        return False
    try:
        if isinstance(valid_until, datetime):
            vu = valid_until
        else:
            vu = datetime.fromisoformat(str(valid_until).replace("Z", "+00:00"))
        if vu.tzinfo is None:
            vu = vu.replace(tzinfo=timezone.utc)
        return vu < now
    except Exception:  # noqa: BLE001
        return False


def _classify_evidence_rows(
    rows: list[dict[str, Any]],
    *,
    now: Optional[datetime] = None,
) -> tuple[str, dict[str, Any]]:
    """Classify a control from its persisted evidence rows.

    COMPLETE — at least one approved/accepted and not expired
    PARTIAL  — evidence exists but none qualify as COMPLETE
    MISSING  — no evidence rows
    """
    if not rows:
        return STATUS_MISSING, {
            "evidence_count": 0,
            "evidence_uids": [],
            "review_statuses": [],
            "best_review_status": "",
        }

    clock = now or _utc_now()
    uids: list[str] = []
    statuses: list[str] = []
    complete = False
    for row in rows:
        uid = _norm(row.get("evidence_uid"))
        if uid:
            uids.append(uid)
        status = _norm(row.get("review_status") or "Collected")
        statuses.append(status)
        expired = _is_expired(status, row.get("valid_until"), now=clock)
        if status.lower() in _APPROVED and not expired:
            complete = True

    unique_uids = list(dict.fromkeys(uids))
    detail = {
        "evidence_count": len(unique_uids),
        "evidence_uids": unique_uids,
        "review_statuses": statuses,
        "best_review_status": (
            next((s for s in statuses if s.lower() in _APPROVED), statuses[0])
            if statuses
            else ""
        ),
    }
    return (STATUS_COMPLETE if complete else STATUS_PARTIAL), detail


def _reason_for(status: str, detail: dict[str, Any]) -> str:
    """Human-readable reason for the completeness table."""
    if status == STATUS_COMPLETE:
        return "Approved evidence exists"
    if status == STATUS_MISSING:
        return "No evidence found"
    blob = " ".join(
        [str(detail.get("best_review_status") or "")]
        + [str(s) for s in (detail.get("review_statuses") or [])]
    ).lower()
    if "expired" in blob:
        return "Evidence expired"
    if "reject" in blob:
        return "Evidence rejected"
    return "Pending review"


def _fetch_evidence_by_control(
    repo: EvidenceRepository,
    *,
    application: str,
    control_ids: Iterable[str],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str]]:
    """Load persisted evidence for an application keyed by control_id.

    Matches ``evidence_control_map.control_id`` and
    ``evidence.metadata->>'fcm_control_id'``. Review state comes from
    ``evidence_reviews`` (default ``Collected`` when absent).

    Also soft-reads ``control_catalog`` (display names) and touches
    ``control_framework_crosswalk`` so governance schema usage is explicit.
    Returns ``(by_control, catalog_names)``.
    """
    ids = sorted({_norm(c) for c in control_ids if _norm(c)})
    out: dict[str, list[dict[str, Any]]] = {cid: [] for cid in ids}
    catalog_names: dict[str, str] = {}
    if not ids:
        return out, catalog_names

    with repo.connect().cursor() as cur:
        cur.execute(
            """
            SELECT e.evidence_uid,
                   e.application,
                   m.control_id AS mapped_control_id,
                   COALESCE(e.metadata->>'fcm_control_id', '') AS fcm_control_id,
                   COALESCE(r.status, 'Collected') AS review_status,
                   r.valid_until
            FROM evidence e
            JOIN evidence_control_map m ON m.evidence_id = e.id
            LEFT JOIN evidence_reviews r ON r.evidence_uid = e.evidence_uid
            WHERE e.application = %s
              AND (
                    m.control_id = ANY(%s)
                 OR COALESCE(e.metadata->>'fcm_control_id', '') = ANY(%s)
              )
            """,
            (application, ids, ids),
        )
        cols = [c[0] for c in cur.description]
        for raw in cur.fetchall():
            row = dict(zip(cols, raw))
            targets = {
                _norm(row.get("mapped_control_id")),
                _norm(row.get("fcm_control_id")),
            }
            for cid in targets:
                if cid in out:
                    out[cid].append(row)

        # Soft enrichment — absent governance seed must not fail completeness.
        try:
            cur.execute(
                "SELECT control_id, name FROM control_catalog WHERE control_id = ANY(%s)",
                (ids,),
            )
            catalog_names = {str(r[0]): str(r[1]) for r in cur.fetchall()}
        except Exception:  # noqa: BLE001
            catalog_names = {}
        try:
            cur.execute(
                "SELECT DISTINCT control_id FROM control_framework_crosswalk "
                "WHERE control_id = ANY(%s)",
                (ids,),
            )
            cur.fetchall()
        except Exception:  # noqa: BLE001
            pass

    return out, catalog_names


def compute_evidence_completeness(
    application: str,
    framework: str,
    *,
    repo: Optional[EvidenceRepository] = None,
    fcm_repo: Any = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Compute Evidence Completeness for one application × framework.

    Expected controls prefer FCM YAML; when the framework is known only via
    Audit Readiness / ``control_catalog`` (e.g. ISO27001), catalog + crosswalk
    rows are used. Returns ``{"ok": False, "error": ...}`` on hard failures.
    """
    app = _norm(application)
    if not app:
        return to_jsonable({"ok": False, "error": "application is required"})

    own_repo = repo is None
    db = repo or EvidenceRepository()
    fw_id = _norm(framework)
    fw_display = fw_id
    expected: list[dict[str, str]] = []
    source = "fcm"

    try:
        if fcm_repo is None:
            from modules.frameworks.repositories.framework_control_repository import (
                get_framework_control_repository,
            )

            fcm_repo = get_framework_control_repository()
        try:
            fw_id, doc = _resolve_fcm_framework(framework, fcm_repo)
            expected = _expected_controls_from_fcm(doc)
            fw_meta = doc.get("framework") or {}
            # Prefer acronym (code) for display consistency with the dropdown.
            fw_display = (
                _norm(fw_meta.get("code"))
                or _norm(fw_meta.get("name"))
                or _norm(fw_meta.get("display_name"))
                or fw_id
            )
            source = "fcm"
        except ValueError:
            expected = _expected_controls_from_catalog(db, framework)
            fw_id = _norm(framework)
            fw_display = fw_id
            source = "control_catalog"
            if not expected:
                return to_jsonable(
                    {
                        "ok": False,
                        "error": (
                            f"Unknown framework: {framework} "
                            "(not in FCM and no control_catalog rows)"
                        ),
                    }
                )
    except RepositoryError as exc:
        if own_repo:
            try:
                db.close()
            except Exception:  # noqa: BLE001
                pass
        return to_jsonable({"ok": False, "error": str(exc)})
    except Exception as exc:  # noqa: BLE001
        if own_repo:
            try:
                db.close()
            except Exception:  # noqa: BLE001
                pass
        return to_jsonable({"ok": False, "error": f"framework load failed: {exc}"})

    if not expected:
        if own_repo:
            try:
                db.close()
            except Exception:  # noqa: BLE001
                pass
        return to_jsonable(
            {
                "ok": True,
                "application": app,
                "framework": fw_display,
                "framework_id": fw_id,
                "source": source,
                "summary": {
                    "total_controls": 0,
                    "complete": 0,
                    "partial": 0,
                    "missing": 0,
                    "completeness_pct": 0.0,
                },
                "controls": [],
            }
        )

    control_ids = [c["control_id"] for c in expected]
    catalog_names: dict[str, str] = {}
    try:
        by_control, catalog_names = _fetch_evidence_by_control(
            db, application=app, control_ids=control_ids
        )
    except RepositoryError as exc:
        return to_jsonable({"ok": False, "error": str(exc)})
    except Exception as exc:  # noqa: BLE001
        return to_jsonable({"ok": False, "error": str(exc)})
    finally:
        if own_repo:
            try:
                db.close()
            except Exception:  # noqa: BLE001
                pass

    clock = now or _utc_now()
    controls_out: list[dict[str, Any]] = []
    complete = partial = missing = 0

    for ctrl in expected:
        cid = ctrl["control_id"]
        status, detail = _classify_evidence_rows(by_control.get(cid) or [], now=clock)
        if status == STATUS_COMPLETE:
            complete += 1
        elif status == STATUS_PARTIAL:
            partial += 1
        else:
            missing += 1
        title = ctrl["control_title"]
        if catalog_names.get(cid) and not ctrl["control_title"]:
            title = str(catalog_names[cid])
        controls_out.append(
            {
                "control_id": cid,
                "control_title": title,
                "domain": ctrl.get("domain") or "",
                "status": status,
                "reason": _reason_for(status, detail),
                "evidence_count": detail["evidence_count"],
                "evidence_uids": detail["evidence_uids"],
                "review_status": detail["best_review_status"],
                "review_statuses": detail["review_statuses"],
            }
        )

    total = len(controls_out)
    pct = round(100.0 * complete / total, 1) if total else 0.0

    return to_jsonable(
        {
            "ok": True,
            "application": app,
            "framework": fw_display,
            "framework_id": fw_id,
            "source": source,
            "summary": {
                "total_controls": total,
                "complete": complete,
                "partial": partial,
                "missing": missing,
                "completeness_pct": pct,
            },
            "controls": controls_out,
        }
    )
