"""Enterprise audit scheduling & readiness engine.

Produces dynamic, deterministic audit calendars across every framework and
application so the Audit Prep "Upcoming Audits" module behaves like a real
banking audit-readiness war-room rather than a static list.

Concepts
--------
* **Quarterly frameworks** — baseline / SDLC frameworks audited every quarter
  (OS Baselining, DB Baselining, Nginx Baselining, AppSec, VAPT, Hardening).
* **Annual frameworks** — regulator-driven cycles (PCI DSS, DPSC, ITDRM,
  CSITE, ITPP).
* Each audit carries application, framework, auditor, scope, type, start &
  end dates, evidence submission deadline, readiness %, missing controls,
  pending evidence, blockers, owners, escalation route.
* Baselining history records the last 3-4 quarterly closures per framework.
* KPI drill-down datasets are built once per request and made available to
  the dashboard so the top counters (Draft / Submitted / Re-upload / Approval
  Rate / Avg Review / Rejection / Pending Aging) become clickable hyperlinks.

The engine is intentionally pure-Python and seeded deterministically so the
demo stays stable between page loads. No external state is required.
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import Any, Iterable


TODAY = date(2026, 5, 28)

# ---------------------------------------------------------------------------
# Static catalogues (kept local to avoid circular imports)
# ---------------------------------------------------------------------------

QUARTERLY_FRAMEWORKS: dict[str, dict[str, Any]] = {
    "OS Baselining": {
        "auditor_pool": ["Internal Audit — Infra", "Deloitte ITGC"],
        "audit_type": "Quarterly Hardening Review",
        "scope_hint": "CIS L2 baseline · SSHd · patch · sudoers",
        "applications": ["Net Banking", "Mobile Banking", "Treasury", "Loan System", "Wealth Portal", "API Gateway"],
    },
    "DB Baselining": {
        "auditor_pool": ["Internal Audit — DBA", "PwC ITGC"],
        "audit_type": "Quarterly Hardening Review",
        "scope_hint": "TDE · DAM · privilege review · backup integrity",
        "applications": ["Wealth Portal", "UPI", "Payments", "Treasury", "CBS Oracle", "Loan System"],
    },
    "Nginx Baselining": {
        "auditor_pool": ["Internal Audit — AppSec", "EY ITGC"],
        "audit_type": "Quarterly Hardening Review",
        "scope_hint": "TLS · HSTS · WAF · rate-limit · ModSecurity CRS",
        "applications": ["API Gateway", "Internet Banking", "Mobile Banking", "Net Banking", "Card Platform"],
    },
    "AppSec": {
        "auditor_pool": ["Internal Audit — AppSec", "KPMG SDLC"],
        "audit_type": "Quarterly AppSec Validation",
        "scope_hint": "SAST · DAST · SCA · secrets · OAuth scope",
        "applications": ["Mobile Banking", "Loan System", "Wealth Portal", "Net Banking", "API Gateway"],
    },
    "VAPT": {
        "auditor_pool": ["EY VAPT", "Internal Red Team"],
        "audit_type": "Quarterly Vulnerability Management",
        "scope_hint": "Internal/External VA · retest · pen test closure",
        "applications": ["UPI", "Internet Banking", "Wealth Portal", "Net Banking", "Payments"],
    },
    "Hardening Reviews": {
        "auditor_pool": ["Internal Audit — Infra", "PwC ITGC"],
        "audit_type": "Quarterly Hardening Review",
        "scope_hint": "Cross-stack baseline · container runtime · CMDB drift",
        "applications": ["CBS Oracle", "Treasury", "Card Platform", "API Gateway", "CRM"],
    },
}

ANNUAL_FRAMEWORKS: dict[str, dict[str, Any]] = {
    "PCI DSS": {
        "auditor_pool": ["Deloitte — PCI QSA"],
        "audit_type": "Annual PCI Assessment",
        "scope_hint": "CDE · MFA · firewall · log review · ASV scan",
        "applications": ["Net Banking", "Payments", "Internet Banking", "Card Platform"],
        "month_anchor": (9, 15),
    },
    "DPSC": {
        "auditor_pool": ["KPMG — DPSC Audit"],
        "audit_type": "Annual DPSC Compliance",
        "scope_hint": "Privileged access · DB audit logs · tokenization",
        "applications": ["Treasury", "UPI", "Payments", "Wealth Portal"],
        "month_anchor": (7, 8),
    },
    "ITDRM": {
        "auditor_pool": ["EY — DR Audit"],
        "audit_type": "Annual DR & Resilience Audit",
        "scope_hint": "BCM · DR drill · backup encryption · RPO/RTO",
        "applications": ["CBS Oracle", "Treasury", "Net Banking", "Payments"],
        "month_anchor": (11, 10),
    },
    "CSITE": {
        "auditor_pool": ["Internal Audit — SOC", "Deloitte CSITE"],
        "audit_type": "Annual CSITE Inspection",
        "scope_hint": "SOC monitoring · SIEM · threat intel · IR",
        "applications": ["Net Banking", "Internet Banking", "Mobile Banking", "UPI"],
        "month_anchor": (8, 20),
    },
    "ITPP": {
        "auditor_pool": ["Internal Audit — ITGC"],
        "audit_type": "Annual ITGC / ITPP Audit",
        "scope_hint": "Change · incident · capacity · availability · DR",
        "applications": ["CBS Oracle", "All Apps", "Treasury", "Payments"],
        "month_anchor": (9, 10),
    },
}

APP_OWNERS = {
    "Net Banking": "R. Mehta",
    "Mobile Banking": "A. Sharma",
    "UPI": "P. Nair",
    "Treasury": "S. Banerjee",
    "Loan System": "V. Rao",
    "Payments": "A. Sharma",
    "Wealth Portal": "V. Rao",
    "Internet Banking": "R. Mehta",
    "Card Platform": "A. Sharma",
    "CRM": "M. D'Souza",
    "API Gateway": "P. Nair",
    "CBS Oracle": "S. Banerjee",
    "All Apps": "Compliance Office",
}

ESCALATION_ROUTES = ["None", "App Owner", "CISO Office", "DBA Lead", "Compliance Head"]


# ---------------------------------------------------------------------------
# Quarter math
# ---------------------------------------------------------------------------

# User-specified custom quarter calendar:
#   Q1: 1 Apr → 30 Jun
#   Q2: 1 Jul → 30 Sep
#   Q3: 1 Oct → 31 Dec
#   Q4: 1 Jan → 31 Mar
QUARTER_DEFS = [
    (1, 4, 1, 6, 30, "Q1"),
    (2, 7, 1, 9, 30, "Q2"),
    (3, 10, 1, 12, 31, "Q3"),
    (4, 1, 1, 3, 31, "Q4"),
]


def quarter_window(today: date, offset: int) -> tuple[date, date, str, int]:
    """Return (start, end, label, fiscal_year) for `offset` quarters ahead of today.

    offset = 0 → the quarter that contains today.
    """
    # Find current quarter
    base_idx = 0
    base_year = today.year
    for idx, (qn, sm, sd, em, ed, label) in enumerate(QUARTER_DEFS):
        sy = base_year if qn != 4 else base_year
        ey = base_year if qn != 4 else base_year
        start = date(sy, sm, sd)
        end = date(ey, em, ed)
        if start <= today <= end:
            base_idx = idx
            break
    target_index = (base_idx + offset) % 4
    cycles = (base_idx + offset) // 4
    target_year = base_year + cycles
    qn, sm, sd, em, ed, label = QUARTER_DEFS[target_index]
    # Q4 spans Jan–Mar of the calendar year following Apr-start fiscal year
    if qn == 4:
        target_year += 1
    start = date(target_year, sm, sd)
    end = date(target_year, em, ed)
    return start, end, f"{label} {target_year}", target_year


# ---------------------------------------------------------------------------
# Deterministic hash → numeric range
# ---------------------------------------------------------------------------


def _seed_int(*parts: Any) -> int:
    blob = "::".join(str(p) for p in parts).encode("utf-8")
    return int(hashlib.md5(blob).hexdigest(), 16)


def _range(seed: int, low: int, high: int) -> int:
    return low + (seed % max(high - low + 1, 1))


# ---------------------------------------------------------------------------
# Per-audit synthesizer
# ---------------------------------------------------------------------------


def _framework_total_controls(framework: str) -> int:
    """Approximate total controls per framework (catalog-driven, fallback safe)."""
    try:
        from app.framework_catalog import FRAMEWORK_CATALOG

        controls = FRAMEWORK_CATALOG.get(framework) or []
        if controls:
            return len(controls)
    except Exception:
        pass
    return 24


def _framework_reusable_controls(framework: str) -> int:
    """Number of theme-overlap reusable controls based on the intelligence engine."""
    try:
        from app.framework_intelligence import (
            build_control_index,
            build_overlap_matrix,
        )

        index = build_control_index()
        matrix = build_overlap_matrix(index)
        reusable_themes = {r["theme_key"] for r in matrix["rows"] if r["reusable"]}
        return sum(
            1
            for c in index
            if c["framework"] == framework
            and any(t in reusable_themes for t in c["themes"])
        )
    except Exception:
        return max(int(_framework_total_controls(framework) * 0.35), 4)


def _build_audit_record(
    framework: str,
    framework_meta: dict[str, Any],
    application: str,
    quarter_offset: int,
    audit_index: int,
    today: date = TODAY,
    annual: bool = False,
) -> dict[str, Any]:
    """Synthesize one audit record."""
    seed = _seed_int(framework, application, quarter_offset, audit_index)
    qstart, qend, qlabel, qyear = quarter_window(today, quarter_offset)
    window = (qend - qstart).days
    if annual:
        anchor = framework_meta.get("month_anchor", (9, 15))
        start = date(qstart.year if anchor[0] >= qstart.month else qstart.year + 1, anchor[0], anchor[1])
        # Push by audit_index weeks for multiple apps within the same framework
        start = start + timedelta(days=(audit_index * 7))
        end_date = start + timedelta(days=14)
    else:
        start_offset = _range(seed, 5, max(window - 15, 6))
        start = qstart + timedelta(days=start_offset)
        end_date = start + timedelta(days=_range(seed >> 3, 4, 8))
    evidence_deadline = start - timedelta(days=_range(seed >> 5, 5, 10))
    days_remaining = (start - today).days

    readiness = _range(seed >> 7, 62, 94)
    # Future quarters: knock 4-10% off readiness
    readiness = max(45, min(96, readiness - quarter_offset * _range(seed >> 9, 2, 5)))
    evidence_completion = max(40, min(99, readiness + _range(seed >> 11, -6, 9)))

    total_controls = _framework_total_controls(framework)
    reusable_controls = min(total_controls, _framework_reusable_controls(framework) // max(1, len(framework_meta.get("applications", [application]))) + _range(seed >> 13, 4, 10))
    pending_controls = max(0, round(total_controls * (100 - readiness) / 100))
    failed_controls = max(0, _range(seed >> 15, 0, 4) if readiness < 80 else 0)
    implemented_controls = max(0, total_controls - pending_controls - failed_controls)

    pending_evidence = max(0, pending_controls * _range(seed >> 17, 1, 3))
    missing_controls = pending_controls + failed_controls
    blockers = min(10, failed_controls + (1 if readiness < 70 else 0) + _range(seed >> 19, 0, 2))

    auditor_pool = framework_meta.get("auditor_pool") or ["Internal Audit"]
    auditor = auditor_pool[_seed_int(application, framework) % len(auditor_pool)]
    owner = APP_OWNERS.get(application, "R. Mehta")
    if readiness < 70 or blockers >= 4:
        escalation = ESCALATION_ROUTES[2 + (seed % 3)]
    elif readiness < 78:
        escalation = "App Owner"
    else:
        escalation = "None"

    audit_id = f"AUD-{framework[:3].upper().replace(' ', '')}-{application[:3].upper().replace(' ', '')}-{qlabel.replace(' ', '')}-{audit_index:02d}"
    return {
        "audit_id": audit_id,
        "framework": framework,
        "application": application,
        "auditor": auditor,
        "audit_type": framework_meta.get("audit_type", "Audit"),
        "audit_scope": framework_meta.get("scope_hint", ""),
        "quarter_label": qlabel,
        "quarter_offset": quarter_offset,
        "annual": annual,
        "start_date": start.isoformat(),
        "end_date": end_date.isoformat(),
        "date": start.isoformat(),  # backward compat for template
        "evidence_deadline": evidence_deadline.isoformat(),
        "days_remaining": days_remaining,
        "readiness_pct": readiness,
        "evidence_completion_pct": evidence_completion,
        "blockers": blockers,
        "missing_controls": missing_controls,
        "pending_evidence": pending_evidence,
        "escalation": escalation,
        "owner": owner,
        "control_breakdown": {
            "implemented": implemented_controls,
            "pending": pending_controls,
            "failed": failed_controls,
            "reusable": reusable_controls,
            "total": total_controls,
        },
        "evidence_reused": min(reusable_controls * _range(seed >> 21, 2, 4), 80),
        "audit_cycle": qlabel,
        "stage": (
            "Closure" if days_remaining < 0
            else "Hot-Stage" if days_remaining <= 14
            else "Active Prep" if days_remaining <= 45
            else "Planning"
        ),
    }


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------


def generate_upcoming_audits(today: date = TODAY) -> list[dict[str, Any]]:
    """Generate every upcoming audit (quarterly + annual) for the rolling year."""
    audits: list[dict[str, Any]] = []
    # Quarterly frameworks: emit audits for current Q (offset=0) + next 2 quarters
    for offset in (0, 1, 2):
        for framework, meta in QUARTERLY_FRAMEWORKS.items():
            apps = meta.get("applications", []) or []
            # rotate apps based on quarter offset so the demo "moves" through them
            rotation = (offset * 2) % max(len(apps), 1)
            chosen = (apps[rotation:] + apps[:rotation])[:3]
            for i, app in enumerate(chosen):
                audits.append(
                    _build_audit_record(framework, meta, app, offset, i, today, annual=False)
                )
    # Annual frameworks: emit each app's annual audit
    for framework, meta in ANNUAL_FRAMEWORKS.items():
        for i, app in enumerate(meta.get("applications", [])):
            offset = 0
            audits.append(
                _build_audit_record(framework, meta, app, offset, i, today, annual=True)
            )
    # Filter out audits already past their end date
    audits = [a for a in audits if a["days_remaining"] >= -7]
    audits.sort(key=lambda a: a["days_remaining"])
    return audits


def generate_baselining_history(today: date = TODAY) -> list[dict[str, Any]]:
    """Past 3 quarterly closures for each quarterly framework."""
    rows: list[dict[str, Any]] = []
    for offset in (-1, -2, -3):
        qstart, qend, qlabel, qyear = quarter_window(today, offset)
        for framework, meta in QUARTERLY_FRAMEWORKS.items():
            apps = meta.get("applications", [])[:3]
            for app in apps:
                seed = _seed_int(framework, app, offset, "hist")
                rows.append({
                    "framework": framework,
                    "application": app,
                    "quarter_label": qlabel,
                    "closed_on": (qend - timedelta(days=_range(seed, 1, 12))).isoformat(),
                    "readiness_pct": _range(seed >> 5, 78, 96),
                    "evidence_count": _range(seed >> 9, 18, 42),
                    "stale_evidence": _range(seed >> 13, 0, 5),
                    "findings": _range(seed >> 17, 0, 4),
                    "auditor": (meta.get("auditor_pool") or ["Internal"])[seed % len(meta.get("auditor_pool") or [1])],
                    "owner": APP_OWNERS.get(app, "R. Mehta"),
                })
    rows.sort(key=lambda r: r["closed_on"], reverse=True)
    return rows[:18]


def generate_audit_calendar(today: date = TODAY, audits: list[dict] | None = None) -> list[dict]:
    """Quarter-grouped calendar buckets for the next 4 quarters."""
    audits = audits if audits is not None else generate_upcoming_audits(today)
    buckets: list[dict[str, Any]] = []
    for offset in (0, 1, 2, 3):
        qstart, qend, qlabel, qyear = quarter_window(today, offset)
        items = [a for a in audits if a["quarter_offset"] == offset]
        avg_readiness = round(sum(a["readiness_pct"] for a in items) / max(len(items), 1), 1)
        bucket = {
            "offset": offset,
            "label": qlabel,
            "start_date": qstart.isoformat(),
            "end_date": qend.isoformat(),
            "audit_count": len(items),
            "avg_readiness_pct": avg_readiness,
            "frameworks_in_scope": sorted({a["framework"] for a in items}),
            "audits": sorted(items, key=lambda a: a["start_date"])[:8],
            "is_current": offset == 0,
        }
        buckets.append(bucket)
    return buckets


def generate_preparation_pipeline(audits: list[dict] | None = None) -> dict[str, Any]:
    """Aggregate counts that fuel the Audit Preparation Pipeline visual."""
    audits = audits if audits is not None else generate_upcoming_audits()
    total_missing = sum(a["missing_controls"] for a in audits)
    total_pending_evidence = sum(a["pending_evidence"] for a in audits)
    total_reusable = sum(a["control_breakdown"]["reusable"] for a in audits)
    total_blockers = sum(a["blockers"] for a in audits)
    owners = {}
    for a in audits:
        owners.setdefault(a["owner"], 0)
        owners[a["owner"]] += a["missing_controls"]
    auditors = {}
    for a in audits:
        auditors.setdefault(a["auditor"], 0)
        auditors[a["auditor"]] += a["pending_evidence"]
    return {
        "controls_pending_review": total_missing,
        "evidence_pending_upload": total_pending_evidence,
        "reusable_evidence_found": total_reusable,
        "auditor_requests": min(total_pending_evidence // 3, 48),
        "blockers": total_blockers,
        "owner_workload": sorted(
            [{"owner": k, "open_controls": v} for k, v in owners.items()],
            key=lambda x: -x["open_controls"],
        )[:8],
        "auditor_workload": sorted(
            [{"auditor": k, "pending_evidence": v} for k, v in auditors.items()],
            key=lambda x: -x["pending_evidence"],
        )[:6],
    }


# ---------------------------------------------------------------------------
# Filter awareness
# ---------------------------------------------------------------------------


def _value_active(val: str | None) -> bool:
    return bool(val) and not str(val).startswith("All ")


def filter_audits(audits: list[dict], filters: dict[str, str] | None) -> list[dict]:
    if not filters:
        return audits
    out = []
    for a in audits:
        ok = True
        for key in ("framework", "application", "owner"):
            v = filters.get(key, "")
            if _value_active(v) and a.get(key) != v:
                ok = False
                break
        if not ok:
            continue
        risk = filters.get("risk", "")
        if _value_active(risk):
            mapped = "Critical" if a["readiness_pct"] < 65 else "High" if a["readiness_pct"] < 78 else "Medium"
            if mapped != risk:
                continue
        status = filters.get("status", "")
        if _value_active(status):
            stage = a.get("stage", "")
            if status.lower() not in stage.lower() and status != a.get("escalation"):
                continue
        out.append(a)
    return out


# ---------------------------------------------------------------------------
# KPI drill-down datasets (for the clickable counter strip)
# ---------------------------------------------------------------------------


_DRILL_REASONS_REJECT = [
    "Evidence outside scope window — re-upload for current quarter.",
    "PII redaction required before auditor share.",
    "Missing approver sign-off — needs reviewer chain.",
    "Hash mismatch with control register — re-export.",
    "Framework mapping incorrect — clarify control ID.",
    "Mock screenshot — requires production export.",
]


def _audits_to_observations(audits: list[dict]) -> list[dict]:
    """Project audits to per-control observations for KPI drill-downs."""
    rows: list[dict] = []
    for a in audits:
        cb = a["control_breakdown"]
        for i in range(cb["pending"]):
            seed = _seed_int(a["audit_id"], "pending", i)
            rows.append({
                "observation_id": f"OBS-{a['audit_id'][-7:]}-P{i + 1:02d}",
                "framework": a["framework"],
                "application": a["application"],
                "control": f"{a['framework'][:3].upper()}-CTRL-{(seed % 30) + 1:02d}",
                "owner": a["owner"],
                "draft_age_days": _range(seed, 1, 28),
                "status": "Draft",
                "submitted_on": "",
                "due_date": a["evidence_deadline"],
                "auditor": a["auditor"],
                "framework_audit": a["audit_id"],
                "reason": "Pending app-owner upload to close gap before audit.",
            })
        for i in range(min(2, cb["failed"])):
            seed = _seed_int(a["audit_id"], "fail", i)
            rows.append({
                "observation_id": f"OBS-{a['audit_id'][-7:]}-F{i + 1:02d}",
                "framework": a["framework"],
                "application": a["application"],
                "control": f"{a['framework'][:3].upper()}-CTRL-{(seed % 30) + 1:02d}",
                "owner": a["owner"],
                "draft_age_days": _range(seed, 5, 18),
                "status": "Re-upload Requested",
                "submitted_on": (TODAY - timedelta(days=_range(seed >> 3, 2, 9))).isoformat(),
                "due_date": a["evidence_deadline"],
                "auditor": a["auditor"],
                "framework_audit": a["audit_id"],
                "reason": _DRILL_REASONS_REJECT[seed % len(_DRILL_REASONS_REJECT)],
            })
        # synthesize submitted/approved evidence per audit
        approved_count = max(0, cb["implemented"] // 4)
        for i in range(min(approved_count, 2)):
            seed = _seed_int(a["audit_id"], "appr", i)
            rows.append({
                "observation_id": f"OBS-{a['audit_id'][-7:]}-A{i + 1:02d}",
                "framework": a["framework"],
                "application": a["application"],
                "control": f"{a['framework'][:3].upper()}-CTRL-{(seed % 30) + 1:02d}",
                "owner": a["owner"],
                "draft_age_days": 0,
                "status": "Approved",
                "submitted_on": (TODAY - timedelta(days=_range(seed, 1, 15))).isoformat(),
                "review_days": round(1 + (seed % 6) * 0.4, 1),
                "due_date": a["evidence_deadline"],
                "auditor": a["auditor"],
                "framework_audit": a["audit_id"],
            })
        # one submitted-but-not-yet-reviewed row
        if cb["implemented"] > 0:
            seed = _seed_int(a["audit_id"], "sub")
            rows.append({
                "observation_id": f"OBS-{a['audit_id'][-7:]}-S01",
                "framework": a["framework"],
                "application": a["application"],
                "control": f"{a['framework'][:3].upper()}-CTRL-{(seed % 30) + 1:02d}",
                "owner": a["owner"],
                "draft_age_days": 0,
                "status": "Submitted",
                "submitted_on": (TODAY - timedelta(days=_range(seed, 1, 12))).isoformat(),
                "review_days": round(1 + (seed % 9) * 0.5, 1),
                "due_date": a["evidence_deadline"],
                "auditor": a["auditor"],
                "framework_audit": a["audit_id"],
            })
    return rows


def build_kpi_drilldowns(audits: list[dict] | None = None) -> dict[str, Any]:
    """Return drill-down datasets keyed by KPI metric."""
    audits = audits if audits is not None else generate_upcoming_audits()
    obs = _audits_to_observations(audits)

    drafts = [o for o in obs if o["status"] == "Draft"]
    submitted = [o for o in obs if o["status"] == "Submitted"]
    reupload = [o for o in obs if o["status"] == "Re-upload Requested"]
    approved = [o for o in obs if o["status"] == "Approved"]
    total_reviewed = approved + reupload
    approval_rate = round(
        len(approved) / max(len(total_reviewed), 1) * 100, 1
    ) if total_reviewed else 0.0
    review_days = [o["review_days"] for o in obs if "review_days" in o]
    avg_review_days = round(sum(review_days) / max(len(review_days), 1), 1) if review_days else 0.0
    rejection_rate = round(
        len(reupload) / max(len(total_reviewed), 1) * 100, 1
    ) if total_reviewed else 0.0
    # Aging buckets
    aging_buckets = {"0-3d": 0, "4-7d": 0, "8-14d": 0, "15-30d": 0, "30+d": 0}
    for d in drafts:
        age = d["draft_age_days"]
        if age <= 3:
            aging_buckets["0-3d"] += 1
        elif age <= 7:
            aging_buckets["4-7d"] += 1
        elif age <= 14:
            aging_buckets["8-14d"] += 1
        elif age <= 30:
            aging_buckets["15-30d"] += 1
        else:
            aging_buckets["30+d"] += 1

    # Auditor turnaround by framework
    fw_review: dict[str, list[float]] = {}
    for o in obs:
        if "review_days" in o:
            fw_review.setdefault(o["framework"], []).append(o["review_days"])
    fw_review_avg = [
        {"framework": k, "avg_days": round(sum(v) / max(len(v), 1), 2), "samples": len(v)}
        for k, v in fw_review.items()
    ]
    fw_review_avg.sort(key=lambda x: -x["avg_days"])

    # Rejection by framework
    fw_reject: dict[str, int] = {}
    fw_total: dict[str, int] = {}
    for o in total_reviewed:
        fw_total.setdefault(o["framework"], 0)
        fw_total[o["framework"]] += 1
        if o["status"] == "Re-upload Requested":
            fw_reject.setdefault(o["framework"], 0)
            fw_reject[o["framework"]] += 1
    fw_reject_breakdown = [
        {
            "framework": fw,
            "rejections": fw_reject.get(fw, 0),
            "total": fw_total.get(fw, 0),
            "rate_pct": round(fw_reject.get(fw, 0) / max(fw_total.get(fw, 0), 1) * 100, 1),
        }
        for fw in sorted(fw_total)
    ]
    fw_reject_breakdown.sort(key=lambda x: -x["rate_pct"])

    auditor_perf: dict[str, list[float]] = {}
    for o in obs:
        if "review_days" in o:
            auditor_perf.setdefault(o["auditor"], []).append(o["review_days"])
    auditor_perf_rows = [
        {
            "auditor": k,
            "avg_days": round(sum(v) / max(len(v), 1), 2),
            "samples": len(v),
            "sla_breaches": sum(1 for d in v if d > 5),
        }
        for k, v in auditor_perf.items()
    ]
    auditor_perf_rows.sort(key=lambda x: -x["avg_days"])

    return {
        "draft": {
            "title": "Draft Observations",
            "count": len(drafts),
            "subtitle": "Observations still in App Owner draft state",
            "columns": ["Observation", "Framework", "Application", "Control", "Owner", "Draft Age", "Due Date"],
            "rows": [
                [d["observation_id"], d["framework"], d["application"], d["control"], d["owner"], f"{d['draft_age_days']}d", d["due_date"]]
                for d in drafts[:40]
            ],
        },
        "submitted": {
            "title": "Submitted Evidence",
            "count": len(submitted),
            "subtitle": "Evidence submitted and awaiting auditor review",
            "columns": ["Observation", "Submitted On", "Framework", "Application", "Auditor", "Audit ID"],
            "rows": [
                [s["observation_id"], s["submitted_on"], s["framework"], s["application"], s["auditor"], s["framework_audit"]]
                for s in submitted[:40]
            ],
        },
        "reupload": {
            "title": "Re-upload Requested",
            "count": len(reupload),
            "subtitle": "Auditor rejected evidence awaiting App Owner re-upload",
            "columns": ["Observation", "Reason", "Framework", "Application", "Owner", "Due Date"],
            "rows": [
                [r["observation_id"], r.get("reason", ""), r["framework"], r["application"], r["owner"], r["due_date"]]
                for r in reupload[:40]
            ],
        },
        "approval_rate": {
            "title": f"Approval Rate · {approval_rate}%",
            "count": len(approved),
            "subtitle": "Approved observations vs total reviewed",
            "columns": ["Observation", "Framework", "Application", "Auditor", "Submitted On", "Review Time"],
            "rows": [
                [a["observation_id"], a["framework"], a["application"], a["auditor"], a["submitted_on"], f"{a.get('review_days', '—')}d"]
                for a in approved[:40]
            ],
            "framework_breakdown": fw_review_avg,
            "auditor_breakdown": auditor_perf_rows,
        },
        "avg_review_time": {
            "title": f"Avg Review Time · {avg_review_days}d",
            "count": len(review_days),
            "subtitle": "Auditor turnaround analytics",
            "columns": ["Framework", "Avg Days", "Samples"],
            "rows": [[r["framework"], r["avg_days"], r["samples"]] for r in fw_review_avg],
            "auditor_breakdown": auditor_perf_rows,
            "delayed_reviews": [
                {
                    "observation_id": o["observation_id"],
                    "framework": o["framework"],
                    "application": o["application"],
                    "auditor": o["auditor"],
                    "review_days": o["review_days"],
                }
                for o in obs
                if o.get("review_days", 0) > 5
            ][:25],
        },
        "rejection_trend": {
            "title": f"Rejection Trend · {rejection_rate}%",
            "count": len(reupload),
            "subtitle": "Common failure patterns by framework",
            "columns": ["Framework", "Rejections", "Total Reviewed", "Rate %"],
            "rows": [
                [r["framework"], r["rejections"], r["total"], f"{r['rate_pct']}%"]
                for r in fw_reject_breakdown
            ],
            "common_reasons": [
                {"reason": reason, "count": sum(1 for o in reupload if o.get("reason") == reason)}
                for reason in _DRILL_REASONS_REJECT
            ],
            "examples": [
                [o["observation_id"], o.get("reason", ""), o["framework"], o["application"], o["owner"]]
                for o in reupload[:25]
            ],
        },
        "pending_aging": {
            "title": f"Pending Aging · {len(drafts)} items",
            "count": len(drafts),
            "subtitle": "Draft observations grouped by aging bucket",
            "columns": ["Bucket", "Count"],
            "rows": [[k, v] for k, v in aging_buckets.items()],
            "overdue": [
                [d["observation_id"], d["framework"], d["application"], d["owner"], f"{d['draft_age_days']}d", d["due_date"]]
                for d in drafts
                if d["draft_age_days"] > 14
            ][:25],
        },
    }


# ---------------------------------------------------------------------------
# Single-audit drill (for clickable rows)
# ---------------------------------------------------------------------------


def get_audit_detail(audit_id: str, audits: list[dict] | None = None) -> dict[str, Any]:
    audits = audits if audits is not None else generate_upcoming_audits()
    target = next((a for a in audits if a["audit_id"] == audit_id), None)
    if not target:
        return {"ok": False, "error": f"Audit {audit_id} not found"}
    obs = _audits_to_observations([target])
    drafts = [o for o in obs if o["status"] == "Draft"]
    submitted = [o for o in obs if o["status"] == "Submitted"]
    reupload = [o for o in obs if o["status"] == "Re-upload Requested"]
    approved = [o for o in obs if o["status"] == "Approved"]
    blockers = [
        {
            "title": f"{target['framework']} {o['control']}",
            "application": o["application"],
            "owner": o["owner"],
            "reason": o.get("reason", "Pending evidence"),
            "due_date": o["due_date"],
        }
        for o in (reupload + drafts[:5])
    ][:8]
    return {
        "ok": True,
        "audit": target,
        "controls": target["control_breakdown"],
        "drafts": drafts[:15],
        "submitted": submitted[:15],
        "reupload": reupload[:15],
        "approved": approved[:15],
        "blockers": blockers,
        "evidence_reused": target.get("evidence_reused", 0),
        "framework_total_controls": target["control_breakdown"]["total"],
    }


# ---------------------------------------------------------------------------
# Top-level façade
# ---------------------------------------------------------------------------


def build_audit_operations(role: str = "owner", filters: dict | None = None) -> dict[str, Any]:
    audits = generate_upcoming_audits()
    filtered = filter_audits(audits, filters or {})
    calendar = generate_audit_calendar(audits=filtered or audits)
    pipeline = generate_preparation_pipeline(filtered or audits)
    baselining = generate_baselining_history()
    kpi_drilldowns = build_kpi_drilldowns(filtered or audits)
    quarterly_frameworks = list(QUARTERLY_FRAMEWORKS.keys())
    annual_frameworks = list(ANNUAL_FRAMEWORKS.keys())
    summary = {
        "total_upcoming": len(filtered),
        "frameworks_in_scope": sorted({a["framework"] for a in filtered}),
        "applications_in_scope": sorted({a["application"] for a in filtered}),
        "quarterly_frameworks": quarterly_frameworks,
        "annual_frameworks": annual_frameworks,
        "this_quarter": {
            "label": calendar[0]["label"],
            "audit_count": calendar[0]["audit_count"],
            "avg_readiness_pct": calendar[0]["avg_readiness_pct"],
        },
    }
    return {
        "upcoming_audits": filtered,
        "all_upcoming_audits": audits,
        "calendar": calendar,
        "pipeline": pipeline,
        "baselining_history": baselining,
        "kpi_drilldowns": kpi_drilldowns,
        "summary": summary,
    }
