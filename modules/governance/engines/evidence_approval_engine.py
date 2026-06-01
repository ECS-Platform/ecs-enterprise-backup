"""Evidence approval analytics — approved/rejected/pending/stale governance dashboard."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from app import ecs_state
from modules.shared.services.ecs_state import BANKING_APPLICATIONS
from modules.frameworks.engines.framework_catalog import FRAMEWORK_CATALOG, get_all_evidence_records, get_framework_controls
from modules.governance.engines.governance_mock_data import OWNERS
from modules.shared.services.role_filter_scope import apply_role_scope

FRAMEWORKS = list(FRAMEWORK_CATALOG.keys())
APPLICATIONS = BANKING_APPLICATIONS + ["Wealth Portal"]
REVIEWERS = ["Auditor — Priya N.", "Auditor — James K.", "Compliance Head", "CISO Office", "QSA Reviewer"]
REJECTION_REASONS = [
    "Evidence incomplete — missing attachment metadata",
    "Stale evidence — export older than 90 days",
    "Control mapping mismatch — wrong PCI requirement cited",
    "Screenshot lacks timestamp and system identifier",
    "Firewall export missing rule owner attribution",
    "Pen test report missing executive attestation",
    "MFA enrollment report excludes privileged tier",
    "Backup test log missing restore validation step",
]

STATUSES = ["Approved", "Rejected", "Pending Validation", "Stale", "Expired"]


def _seed(key: str, lo: int, hi: int) -> int:
    h = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)
    return lo + (h % (hi - lo + 1))


def _ts(days_ago: int = 0) -> str:
    from datetime import timedelta
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def _quality_score(evidence_name: str, status: str) -> dict:
    s = _seed(evidence_name + status, 62, 98)
    return {
        "quality_score": s,
        "completeness": "Complete" if s >= 85 else ("Partial" if s >= 70 else "Incomplete"),
        "freshness": "Good" if s >= 80 else ("Aging" if s >= 65 else "Stale"),
        "metadata_quality": "Complete" if s >= 75 else "Incomplete",
        "control_match": "Valid" if s >= 70 else "Review Required",
        "attachment_validity": "Valid" if status != "Rejected" else "Invalid",
    }


def generate_approval_records(count: int = 180) -> list[dict]:
    records = []
    catalog = get_all_evidence_records()
    for i in range(count):
        src = catalog[i % len(catalog)] if catalog else {}
        fw = FRAMEWORKS[i % len(FRAMEWORKS)]
        app = APPLICATIONS[i % len(APPLICATIONS)]
        if src:
            fw = src.get("framework", fw)
            app = src.get("application", app) or app
        ctrls = get_framework_controls(fw)
        ctrl = ctrls[i % len(ctrls)] if ctrls else {"control_id": f"C-{i}", "control": f"Control {i}"}
        status_roll = i % 10
        if status_roll < 6:
            status = "Approved"
        elif status_roll < 8:
            status = "Pending Validation"
        elif status_roll == 8:
            status = "Rejected"
        elif status_roll == 9:
            status = "Stale"
        else:
            status = "Expired"
        ev_name = src.get("evidence_name") or f"{fw} Evidence Pack — {app} ({i + 1})"
        ev_id = src.get("evidence_id") or f"EV-{fw[:3].upper()}-{i + 1:04d}"
        owner = OWNERS[i % len(OWNERS)]
        submitted_by = f"{owner} (App Owner)"
        quality = _quality_score(ev_name, status)
        rec = {
            "evidence_id": ev_id,
            "framework": fw,
            "application": app,
            "control": ctrl["control"],
            "control_id": ctrl.get("control_id", ""),
            "evidence_name": ev_name,
            "submitted_by": submitted_by,
            "owner": owner,
            "submitted_at": _ts(_seed(str(i), 1, 45)),
            "status": status,
            "risk": ["Critical", "High", "Medium", "Low"][_seed(f"risk-{i}", 0, 3)],
            **quality,
        }
        if status == "Approved":
            rec["approved_by"] = REVIEWERS[i % len(REVIEWERS)]
            rec["approval_date"] = _ts(_seed(str(i), 0, 20))
            rec["validation_days"] = _seed(f"val-{i}", 1, 8)
        elif status == "Rejected":
            rec["rejected_by"] = REVIEWERS[(i + 1) % len(REVIEWERS)]
            rec["rejection_date"] = _ts(_seed(str(i), 0, 15))
            rec["rejection_reason"] = REJECTION_REASONS[i % len(REJECTION_REASONS)]
            rec["resubmission_status"] = "Pending Resubmission" if i % 2 == 0 else "Resubmitted"
        elif status == "Pending Validation":
            rec["reviewer"] = REVIEWERS[i % len(REVIEWERS)]
            rec["sla_remaining_days"] = _seed(f"sla-{i}", 1, 14)
            rec["priority"] = rec["risk"]
        records.append(rec)
    return records


def _merge_live_state(records: list[dict]) -> list[dict]:
    """Overlay ecs_state approved/rejected/submitted controls."""
    for key, info in ecs_state.approved_controls.items():
        fw, ctrl = key.split("::", 1)
        records.append({
            "evidence_id": f"LIVE-APP-{len(records)}",
            "framework": fw, "application": APPLICATIONS[hash(key) % len(APPLICATIONS)],
            "control": ctrl, "control_id": ctrl[:8],
            "evidence_name": f"Live approved — {ctrl[:40]}",
            "submitted_by": info.get("owner", OWNERS[0]), "owner": info.get("owner", OWNERS[0]),
            "approved_by": info.get("auditor", "Auditor"), "approval_date": info.get("approved_at", _ts(2)),
            "status": "Approved", "risk": "Medium", **_quality_score(ctrl, "Approved"),
            "submitted_at": _ts(5), "validation_days": 3,
        })
    for key, info in ecs_state.rejected_controls.items():
        fw, ctrl = key.split("::", 1)
        records.append({
            "evidence_id": f"LIVE-REJ-{len(records)}",
            "framework": fw, "application": APPLICATIONS[hash(key) % len(APPLICATIONS)],
            "control": ctrl, "evidence_name": f"Live rejected — {ctrl[:40]}",
            "submitted_by": OWNERS[hash(key) % len(OWNERS)], "owner": OWNERS[hash(key) % len(OWNERS)],
            "rejected_by": info.get("auditor", "Auditor"), "rejection_date": _ts(1),
            "rejection_reason": info.get("reason", "Rejected"), "status": "Rejected",
            "resubmission_status": "Pending Resubmission", "risk": "High",
            **_quality_score(ctrl, "Rejected"), "submitted_at": _ts(8),
        })
    return records


def build_evidence_approval_view(role: str = "owner") -> dict:
    all_records = _merge_live_state(generate_approval_records(180))
    scoped = apply_role_scope(all_records, role)

    approved = [r for r in scoped if r["status"] == "Approved"]
    rejected = [r for r in scoped if r["status"] == "Rejected"]
    pending = [r for r in scoped if r["status"] == "Pending Validation"]
    stale = [r for r in scoped if r["status"] in ("Stale", "Expired")]
    total_submitted = len(scoped)
    approval_rate = round(len(approved) / max(total_submitted, 1) * 100, 1)
    rejection_rate = round(len(rejected) / max(total_submitted, 1) * 100, 1)
    avg_val = round(sum(r.get("validation_days", 4) for r in approved) / max(len(approved), 1), 1)

    fw_analytics = []
    for fw in FRAMEWORKS:
        fw_rows = [r for r in scoped if r["framework"] == fw]
        if not fw_rows:
            continue
        fw_analytics.append({
            "framework": fw,
            "approved": len([r for r in fw_rows if r["status"] == "Approved"]),
            "rejected": len([r for r in fw_rows if r["status"] == "Rejected"]),
            "pending": len([r for r in fw_rows if r["status"] == "Pending Validation"]),
            "approval_pct": round(len([r for r in fw_rows if r["status"] == "Approved"]) / max(len(fw_rows), 1) * 100, 1),
        })

    app_analytics = []
    for app in APPLICATIONS:
        app_rows = [r for r in scoped if r["application"] == app]
        if not app_rows:
            continue
        app_analytics.append({
            "application": app,
            "approved": len([r for r in app_rows if r["status"] == "Approved"]),
            "rejected": len([r for r in app_rows if r["status"] == "Rejected"]),
            "pending": len([r for r in app_rows if r["status"] == "Pending Validation"]),
            "maturity_pct": round(len([r for r in app_rows if r["status"] == "Approved"]) / max(len(app_rows), 1) * 100, 1),
        })

    reviewer_load = {}
    for r in pending + approved[:30]:
        rev = r.get("reviewer") or r.get("approved_by") or "Unassigned"
        reviewer_load[rev] = reviewer_load.get(rev, 0) + 1
    reviewer_bars = [{"label": k[:18], "value": v, "tone": "navy"} for k, v in sorted(reviewer_load.items(), key=lambda x: -x[1])[:8]]

    months = ["Jan", "Feb", "Mar", "Apr", "May"]
    approval_trend = [{"label": m, "value": 78 + i * 3 + _seed(m, 0, 8), "suffix": "%", "tone": "teal"} for i, m in enumerate(months)]
    rejection_trend = [{"label": m, "value": 14 - i + _seed(m + "r", 0, 4), "suffix": "", "tone": "orange"} for i, m in enumerate(months)]
    stale_aging = [
        {"label": "0-30d", "value": len(stale) // 2 + 3, "tone": "teal"},
        {"label": "31-60d", "value": len(stale) // 3 + 2, "tone": "orange"},
        {"label": "61-90d", "value": len(stale) // 4 + 1, "tone": "red"},
        {"label": "90+d", "value": max(1, len(stale) // 5), "tone": "red"},
    ]

    audit_trail = []
    for r in (approved[:5] + rejected[:3]):
        audit_trail.append({
            "evidence_id": r["evidence_id"], "evidence_name": r["evidence_name"][:45],
            "action": "Approved" if r["status"] == "Approved" else "Rejected",
            "actor": r.get("approved_by") or r.get("rejected_by", "—"),
            "timestamp": r.get("approval_date") or r.get("rejection_date", _ts(1)),
            "remarks": r.get("rejection_reason", "Validation passed — control evidence accepted."),
            "framework": r["framework"], "application": r["application"],
        })

    role_summary = _role_summary(role, scoped, approved, rejected, pending, stale)

    return {
        "kpis": [
            {"label": "Total Evidence Submitted", "value": total_submitted, "tone": "primary"},
            {"label": "Approved Evidence", "value": len(approved), "tone": "success"},
            {"label": "Rejected Evidence", "value": len(rejected), "tone": "danger"},
            {"label": "Pending Validation", "value": len(pending), "tone": "warning"},
            {"label": "Approval Success %", "value": f"{approval_rate}%", "tone": "success"},
            {"label": "Rejection Rate %", "value": f"{rejection_rate}%", "tone": "danger"},
            {"label": "Avg Validation Time", "value": f"{avg_val}d", "tone": "info"},
            {"label": "Stale Evidence Count", "value": len(stale), "tone": "warning"},
        ],
        "approved_rows": approved,
        "rejected_rows": rejected,
        "pending_rows": pending,
        "stale_rows": stale,
        "quality_samples": scoped[:12],
        "framework_analytics": fw_analytics,
        "application_analytics": app_analytics,
        "approval_trend": approval_trend,
        "rejection_trend": rejection_trend,
        "framework_approval_bars": [{"label": f["framework"][:12], "value": f["approval_pct"], "suffix": "%", "tone": "navy"} for f in fw_analytics[:9]],
        "application_maturity_bars": [{"label": a["application"][:14], "value": a["maturity_pct"], "suffix": "%", "tone": "teal"} for a in app_analytics[:8]],
        "reviewer_workload": reviewer_bars,
        "stale_aging": stale_aging,
        "audit_trail": audit_trail,
        "role_summary": role_summary,
        "rows": scoped[:40],
        "role": role,
    }


def _role_summary(role: str, scoped, approved, rejected, pending, stale) -> str:
    if role == "owner":
        return f"Your applications: {len(scoped)} evidence submissions — {len(approved)} approved, {len(rejected)} rejected, {len(pending)} awaiting validation."
    if role == "auditor":
        return f"Validation queue: {len(pending)} pending reviews — {len(rejected)} rejections this cycle, {len(stale)} stale evidence alerts."
    if role == "vertical_head":
        return f"BU-wide approval maturity: {round(len(approved)/max(len(scoped),1)*100,1)}% — monitor {len(pending)} pending validations across vertical apps."
    if role == "cio":
        return f"Enterprise evidence governance: {len(approved)} approved of {len(scoped)} submitted — framework acceptance trending upward."
    if role in ("compliance_head", "compliance_officer"):
        return f"Framework compliance validation: {len(pending)} items in SLA window — {len(rejected)} rejections require remediation follow-up."
    return f"Evidence approval posture: {len(approved)} approved, {len(rejected)} rejected, {len(pending)} pending."
