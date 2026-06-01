"""Enterprise evidence health — control/observation linkage, audit trail, framework analytics."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from modules.shared.services.ecs_state import BANKING_APPLICATIONS
from modules.frameworks.engines.framework_catalog import FRAMEWORK_CATALOG, get_all_evidence_records, get_framework_controls
from modules.governance.engines.governance_mock_data import OWNERS, _EVIDENCE_NAMES
from modules.shared.services.role_filter_scope import apply_role_scope

FRAMEWORKS = list(FRAMEWORK_CATALOG.keys())
APPLICATIONS = BANKING_APPLICATIONS + ["Wealth Portal"]
PREFIX = {
    "PCI DSS": "PCI", "DPSC": "DPSC", "AppSec": "APP", "VAPT": "VAPT",
    "OS Baselining": "OS", "DB Baselining": "DB", "Nginx Baselining": "NGX",
    "ITPP": "ITPP", "CSITE": "CSI",
}
ISSUES = ["Stale", "Expired", "Rejected", "Expiring Soon", "Missing Metadata", "Low Confidence", "Failed Validation"]
VALIDATION = ["Approved", "Pending Validation", "Rejected", "Revalidation Required", "Not Submitted"]
OBS_TEMPLATES = [
    "Firewall segmentation evidence outdated.",
    "Exception approval missing.",
    "MFA enrollment report excludes privileged tier.",
    "Pen test critical finding remediation overdue.",
    "Backup restore test log missing validation step.",
    "TLS cipher suite non-compliant with baseline.",
    "SAST gate failure on release branch.",
    "SIEM use-case correlation gap detected.",
    "Database TDE attestation expired.",
    "WAF rule export missing owner attribution.",
]


def _seed(key: str, lo: int, hi: int) -> int:
    h = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)
    return lo + (h % (hi - lo + 1))


def _ts(days_ago: int = 0) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def _ev_id(fw: str, n: int) -> str:
    return f"EVD-{PREFIX.get(fw, 'EV')}-{100 + n}"


def _obs_id(fw: str, n: int) -> str:
    return f"OBS-{PREFIX.get(fw, 'EV')}-{n:03d}"


def _ctrl_id(fw: str, ctrl: dict, idx: int) -> str:
    cid = ctrl.get("control_id") or ""
    if cid:
        return cid.split("—")[0].strip()[:12]
    p = PREFIX.get(fw, "CTL")
    return f"{p}-{idx + 1}.{_seed(f'c-{fw}-{idx}', 1, 9)}"


def _audit_trail(rec: dict) -> list[dict]:
    trail = [{"timestamp": rec.get("uploaded_at", _ts(30)), "action": "Uploaded", "actor": rec.get("owner", OWNERS[0]), "remarks": "Initial submission"}]
    if rec.get("validation_status") == "Approved":
        trail.append({"timestamp": rec.get("last_reviewed", _ts(5)), "action": "Approved", "actor": rec.get("validated_by", "Auditor"), "remarks": "Control evidence accepted"})
    elif rec.get("validation_status") == "Rejected":
        trail.append({"timestamp": rec.get("last_reviewed", _ts(3)), "action": "Rejected", "actor": rec.get("rejected_by", "Auditor"), "remarks": rec.get("rejection_reason", "Incomplete metadata")})
        trail.append({"timestamp": _ts(1), "action": "Resubmitted", "actor": rec.get("owner", OWNERS[0]), "remarks": f"Resubmission #{rec.get('resubmission_count', 1)}"})
    elif rec.get("issue") == "Stale":
        trail.append({"timestamp": _ts(10), "action": "Stale Alert", "actor": "ECS Scheduler", "remarks": "Evidence age exceeds 90-day policy"})
    return trail


def generate_health_records(count: int = 140) -> list[dict]:
    records = []
    catalog = get_all_evidence_records()
    for i in range(count):
        fw = FRAMEWORKS[i % len(FRAMEWORKS)]
        app = APPLICATIONS[i % len(APPLICATIONS)]
        if catalog:
            src = catalog[i % len(catalog)]
            fw = src.get("framework", fw)
            app = src.get("application_name") or src.get("application") or app
        ctrls = get_framework_controls(fw)
        ctrl = ctrls[i % len(ctrls)] if ctrls else {"control_id": f"{PREFIX.get(fw,'C')}-{i}", "control": f"{fw} Control {i + 1}"}
        issue = ISSUES[i % len(ISSUES)]
        risk = {"Expired": "Critical", "Rejected": "High", "Failed Validation": "High", "Stale": "Medium",
                "Expiring Soon": "High", "Missing Metadata": "High", "Low Confidence": "Medium"}.get(issue, "Low")
        val = {"Stale": "Revalidation Required", "Expired": "Rejected", "Rejected": "Rejected",
               "Expiring Soon": "Pending Validation", "Missing Metadata": "Not Submitted",
               "Low Confidence": "Pending Validation", "Failed Validation": "Rejected"}.get(issue, "Approved")
        score = max(28, 96 - _seed(str(i), 5, 68))
        if risk == "Critical":
            score = min(score, 35)
        elif risk == "High":
            score = min(score, 58)
        obs_idx = i % len(OBS_TEMPLATES)
        eid = _ev_id(fw, i)
        if catalog and i < len(catalog):
            eid = catalog[i % len(catalog)].get("evidence_id", eid)
        name = _EVIDENCE_NAMES[i % len(_EVIDENCE_NAMES)]
        if catalog:
            name = catalog[i % len(catalog)].get("evidence_name", name)
        owner = OWNERS[i % len(OWNERS)]
        rec = {
            "evidence_id": eid,
            "evidence_name": name,
            "framework": fw,
            "application": app,
            "control_id": _ctrl_id(fw, ctrl, i),
            "control_name": ctrl.get("control", ctrl.get("control_id", f"{fw} control"))[:60],
            "observation_id": _obs_id(fw, obs_idx + 1 + (i % 40)),
            "observation_summary": OBS_TEMPLATES[obs_idx],
            "owner": owner,
            "issue": issue,
            "risk": risk,
            "health_score": score,
            "validation_status": val,
            "last_reviewed": _ts(_seed(f"rev-{i}", 1, 45)),
            "expiry_status": "Expired" if issue == "Expired" else ("Expiring Soon" if issue == "Expiring Soon" else "Valid"),
            "expiry_date": f"2026-0{6 + (i % 3)}-{(i % 25) + 1:02d}",
            "uploaded_at": _ts(_seed(f"up-{i}", 10, 120)),
            "validated_by": "Auditor — Priya N." if val == "Approved" else "",
            "rejected_by": "Auditor — James K." if val == "Rejected" else "",
            "rejection_reason": "Evidence incomplete — missing attachment metadata" if val == "Rejected" else "",
            "resubmission_count": i % 3 if val == "Rejected" else 0,
            "missing_metadata": issue in ("Missing Metadata", "Low Confidence"),
            "rejection_count": 1 if issue == "Rejected" else 0,
            "linked_incidents": [f"INC-2026-{_seed(f'inc-{i}', 1000, 9999)}"] if risk in ("Critical", "High") else [],
            "remediation_status": "Open" if risk in ("Critical", "High") else ("In Progress" if issue == "Stale" else "Closed"),
        }
        rec["audit_trail"] = _audit_trail(rec)
        records.append(rec)
    return records


def _framework_health(rows: list[dict]) -> list[dict]:
    out = []
    for fw in FRAMEWORKS:
        fw_rows = [r for r in rows if r["framework"] == fw]
        if not fw_rows:
            continue
        approved = len([r for r in fw_rows if r["validation_status"] == "Approved"])
        out.append({
            "framework": fw,
            "total": len(fw_rows),
            "stale": len([r for r in fw_rows if r["issue"] == "Stale"]),
            "expired": len([r for r in fw_rows if r["issue"] == "Expired"]),
            "rejected": len([r for r in fw_rows if r["issue"] == "Rejected"]),
            "high_risk": len([r for r in fw_rows if r["risk"] in ("Critical", "High")]),
            "mapped_controls": len({r["control_id"] for r in fw_rows}),
            "linked_observations": len({r["observation_id"] for r in fw_rows}),
            "health_score": round(sum(r["health_score"] for r in fw_rows) / max(len(fw_rows), 1), 1),
            "approval_pct": round(approved / max(len(fw_rows), 1) * 100, 1),
        })
    return out


def build_evidence_health_view(role: str = "owner") -> dict:
    all_rows = generate_health_records(140)
    scoped = apply_role_scope(all_rows, role)
    scoped.sort(key=lambda x: {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}[x["risk"]])

    categories = {
        "stale": [r for r in scoped if r["issue"] == "Stale"],
        "expired": [r for r in scoped if r["issue"] == "Expired"],
        "rejected": [r for r in scoped if r["issue"] == "Rejected"],
        "incomplete": [r for r in scoped if r["issue"] in ("Missing Metadata", "Low Confidence")],
        "risky": [r for r in scoped if r["risk"] in ("Critical", "High")],
        "failed": [r for r in scoped if r["issue"] == "Failed Validation"],
    }
    fw_breakdown = _framework_health(scoped)
    app_breakdown = []
    for app in APPLICATIONS:
        app_rows = [r for r in scoped if r["application"] == app]
        if not app_rows:
            continue
        app_breakdown.append({
            "application": app,
            "issues": len(app_rows),
            "avg_score": round(sum(r["health_score"] for r in app_rows) / max(len(app_rows), 1), 1),
            "owner": OWNERS[hash(app) % len(OWNERS)],
            "open_observations": len({r["observation_id"] for r in app_rows}),
        })
    owner_breakdown = []
    for owner in OWNERS:
        o_rows = [r for r in scoped if r["owner"] == owner]
        owner_breakdown.append({
            "owner": owner,
            "queue_size": len(o_rows) or _seed(owner, 2, 8),
            "rejections": sum(r.get("rejection_count", 0) for r in o_rows),
            "critical": sum(1 for r in o_rows if r["risk"] == "Critical"),
        })
    rejection_trends = [
        {"month": "Jan", "rejections": 12, "rate_pct": 8.2},
        {"month": "Feb", "rejections": 9, "rate_pct": 6.1},
        {"month": "Mar", "rejections": 14, "rate_pct": 9.4},
        {"month": "Apr", "rejections": 7, "rate_pct": 4.8},
        {"month": "May", "rejections": 11, "rate_pct": 7.3},
    ]
    stale_aging = [
        {"label": "0-30d", "value": len(categories["stale"]) // 2 + 2, "tone": "teal"},
        {"label": "31-60d", "value": len(categories["stale"]) // 3 + 1, "tone": "orange"},
        {"label": "61-90d", "value": max(1, len(categories["stale"]) // 4), "tone": "red"},
        {"label": "90+d", "value": max(1, len(categories["stale"]) // 5), "tone": "red"},
    ]
    avg_score = round(sum(r["health_score"] for r in scoped[:60]) / max(len(scoped[:60]), 1), 1)
    missing_ctrl = len([r for r in scoped if r["validation_status"] == "Not Submitted"])
    with_obs = len([r for r in scoped if r.get("observation_id")])
    return {
        "kpis": [
            {"label": "Health Score", "value": f"{avg_score}%", "tone": "success"},
            {"label": "Controls Missing Evidence", "value": missing_ctrl, "tone": "danger"},
            {"label": "Evidence w/ Open Observations", "value": with_obs, "tone": "warning"},
            {"label": "High-Risk Failures", "value": len(categories["risky"]), "tone": "danger"},
            {"label": "Expiring Evidence", "value": len([r for r in scoped if r["issue"] == "Expiring Soon"]), "tone": "info"},
            {"label": "Rejected Evidence", "value": len(categories["rejected"]), "tone": "danger"},
            {"label": "Revalidated Evidence", "value": len([r for r in scoped if r["validation_status"] == "Revalidation Required"]), "tone": "primary"},
            {"label": "Stale Evidence", "value": len(categories["stale"]), "tone": "warning"},
        ],
        "risk_distribution": [
            {"label": "Critical", "count": sum(1 for r in scoped if r["risk"] == "Critical"), "class": "risk-critical"},
            {"label": "High", "count": sum(1 for r in scoped if r["risk"] == "High"), "class": "risk-high"},
            {"label": "Medium", "count": sum(1 for r in scoped if r["risk"] == "Medium"), "class": "risk-medium"},
            {"label": "Low", "count": sum(1 for r in scoped if r["risk"] == "Low"), "class": "risk-low"},
        ],
        "rows": scoped,
        "categories": categories,
        "framework_breakdown": fw_breakdown,
        "application_breakdown": app_breakdown,
        "owner_breakdown": owner_breakdown,
        "rejection_trends": rejection_trends,
        "stale_aging": stale_aging,
        "role": role,
    }
