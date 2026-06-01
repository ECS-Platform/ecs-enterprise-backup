"""Framework coverage & readiness engine for Governance → Completeness."""

from __future__ import annotations

import hashlib

from app.framework_catalog import FRAMEWORK_CATALOG
from app.operations_catalog import BANKING_APPLICATIONS, FRAMEWORK_CONTROLS, OWNERS, owner_for

ALL_FRAMEWORKS = list(FRAMEWORK_CATALOG.keys())

COMPLETENESS_APPS = [
    "Net Banking", "Mobile Banking", "Treasury", "Payments",
    "Loan Origination", "Wealth Portal", "Core Banking", "Payments Hub",
    "UPI", "Corporate Banking", "Trade Finance", "AML Engine",
]

_TRENDS = ["Improving", "Stable", "Declining"]
_EVIDENCE_STATUS = ["Healthy", "Partial", "Stale"]


def _seed(key: str) -> int:
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)


def _detail_row(app: str, fw: str) -> dict:
    s = _seed(f"complete|{app}|{fw}")
    total = 140 + (s % 90)
    readiness = min(98, 52 + (s % 44))
    risk = None
    if fw == "VAPT" and app == "Net Banking":
        readiness = 76
        risk = "High"
    if fw == "AppSec" and app == "Mobile Banking":
        readiness = 92
    if fw == "OS Baselining" and app == "Treasury":
        readiness = 84
    if fw == "PCI DSS" and app in ("Net Banking", "Mobile Banking"):
        readiness = max(readiness, 78)
    implemented = int(total * readiness / 100)
    pending = max(0, int((total - implemented) * 0.55))
    gaps = max(0, total - implemented - pending)
    failed = s % 6 if readiness < 80 else s % 3
    if risk is None:
        risk = "Critical" if readiness < 55 else ("High" if readiness < 70 else ("Medium" if readiness < 85 else "Low"))
    trend = _TRENDS[s % 3]
    if readiness < 60:
        trend = "Declining"
    evidence = _EVIDENCE_STATUS[s % 3]
    controls = FRAMEWORK_CONTROLS.get(fw, [f"{fw[:3]}-01"])
    return {
        "application": app,
        "framework": fw,
        "readiness_pct": readiness,
        "readiness_label": f"{fw} Readiness",
        "total_controls": total,
        "implemented": implemented,
        "pending": pending,
        "open_gaps": gaps,
        "failed_controls": failed,
        "evidence_status": evidence,
        "status": evidence,
        "trend": trend,
        "risk": risk,
        "owner": owner_for(app),
        "control_scope": f"{implemented} / {total} controls validated",
        "context_label": f"{app} · {fw}",
        "sample_control": controls[s % len(controls)],
    }


def build_detail_rows() -> list[dict]:
    rows = []
    for app in COMPLETENESS_APPS:
        for fw in ALL_FRAMEWORKS:
            rows.append(_detail_row(app, fw))
    return rows


def build_framework_summaries(detail_rows: list[dict]) -> list[dict]:
    by_fw: dict[str, list[dict]] = {}
    for r in detail_rows:
        by_fw.setdefault(r["framework"], []).append(r)
    summaries = []
    for fw, items in by_fw.items():
        apps = sorted({r["application"] for r in items})
        total_ctrl = sum(r["total_controls"] for r in items)
        approved = sum(r["implemented"] for r in items)
        missing = sum(r["open_gaps"] + r["pending"] for r in items)
        avg = round(sum(r["readiness_pct"] for r in items) / len(items), 1)
        audit_risk = "High" if avg < 65 else ("Medium" if avg < 80 else "Low")
        summaries.append({
            "framework": fw,
            "applications_covered": ", ".join(apps[:3]) + ("…" if len(apps) > 3 else ""),
            "applications_list": apps,
            "avg_readiness": avg,
            "controls_approved": approved,
            "total_controls": total_ctrl,
            "approved_display": f"{approved}/{total_ctrl}",
            "missing_controls": missing,
            "audit_risk": audit_risk,
            "maturity_label": f"{avg}% control implementation maturity",
            "scope_label": f"{fw} · {len(apps)} applications",
        })
    return summaries


def build_gap_rows(detail_rows: list[dict]) -> list[dict]:
    gaps = []
    for r in detail_rows:
        if r["open_gaps"] <= 0 and r["pending"] <= 0:
            continue
        gaps.append({
            "framework": r["framework"],
            "control": r["sample_control"],
            "application": r["application"],
            "evidence": f"{r['framework']} evidence — {r['sample_control']}",
            "owner": r["owner"],
            "priority": r["risk"],
            "risk": r["risk"],
        })
    return gaps


def aggregate_kpis(detail_rows: list[dict], framework: str = "All Frameworks") -> list[dict]:
    rows = detail_rows if framework == "All Frameworks" else [r for r in detail_rows if r["framework"] == framework]
    if not rows:
        rows = detail_rows
    apps = sorted({r["application"] for r in rows})
    fws = sorted({r["framework"] for r in rows})
    total = sum(r["total_controls"] for r in rows)
    impl = sum(r["implemented"] for r in rows)
    maturity = round(impl / max(total, 1) * 100, 1)
    audit = round(sum(r["readiness_pct"] for r in rows) / max(len(rows), 1), 1)
    missing = sum(r["open_gaps"] + r["pending"] for r in rows)
    incomplete = [a for a in apps if any(r["readiness_pct"] < 80 for r in rows if r["application"] == a)]
    fw_scope = framework if framework != "All Frameworks" else ", ".join(fws[:3]) + ("…" if len(fws) > 3 else "")
    return [
        {"label": "Framework Scope", "value": fw_scope, "hint": f"{len(apps)} applications covered", "tone": "primary"},
        {"label": "Overall Control Maturity", "value": f"{maturity}%", "hint": f"({impl} / {total} controls implemented)", "tone": "success" if maturity >= 70 else "warning"},
        {"label": "Audit Readiness", "value": f"{audit}%", "hint": "Across selected applications", "tone": "info"},
        {"label": "Missing Controls", "value": missing, "hint": f"Across {len(fws)} framework(s)", "tone": "danger"},
        {"label": "Incomplete Applications", "value": len(incomplete), "hint": ", ".join(incomplete[:3]) + ("…" if len(incomplete) > 3 else ""), "tone": "warning"},
    ]


def build_completeness_dashboard(
    framework: str = "All Frameworks",
    application: str = "All Applications",
    risk: str = "All Risk",
    role: str = "owner",
) -> dict:
    from app.missing_evidence_engine import compute_completeness_pct, compute_upload_kpis, get_all_missing_evidence

    detail = build_detail_rows()
    if framework != "All Frameworks":
        detail = [r for r in detail if r["framework"] == framework]
    if application != "All Applications":
        detail = [r for r in detail if r["application"] == application]
    if risk != "All Risk":
        if risk == "High":
            detail = [r for r in detail if r["risk"] in ("High", "Critical")]
        else:
            detail = [r for r in detail if r["risk"] == risk]
    base_detail = detail if detail else build_detail_rows()
    summaries = build_framework_summaries(base_detail)
    if framework != "All Frameworks":
        summaries = [s for s in summaries if s["framework"] == framework]
    missing_rows = get_all_missing_evidence(role)
    if framework != "All Frameworks":
        missing_rows = [r for r in missing_rows if r["framework"] == framework]
    if application != "All Applications":
        missing_rows = [r for r in missing_rows if r["application"] == application]
    if risk != "All Risk":
        if risk == "High":
            missing_rows = [r for r in missing_rows if r["risk"] in ("High", "Critical")]
        else:
            missing_rows = [r for r in missing_rows if r["risk"] == risk]
    dynamic_pct = compute_completeness_pct(missing_rows, base_detail)
    kpis = aggregate_kpis(base_detail, framework)
    for k in kpis:
        if k["label"] == "Audit Readiness":
            k["value"] = f"{dynamic_pct}%"
            k["hint"] = "Derived from evidence uploads, approvals, and missing controls"
        if k["label"] == "Missing Controls":
            k["value"] = len(missing_rows)
            k["hint"] = f"{len(missing_rows)} mandatory evidence gaps (observation-linked)"
    return {
        "detail_rows": base_detail,
        "framework_summaries": summaries,
        "gap_rows": build_gap_rows(base_detail),
        "missing_evidence_rows": missing_rows,
        "upload_kpis": compute_upload_kpis(missing_rows),
        "completeness_pct": dynamic_pct,
        "kpis": kpis,
    }


def build_completeness_dataset(role: str = "owner") -> dict:
    from app.missing_evidence_engine import compute_upload_kpis, get_all_missing_evidence

    detail = build_detail_rows()
    missing = get_all_missing_evidence(role)
    return {
        "detail_rows": detail,
        "missing_evidence_rows": missing,
        "upload_kpis": compute_upload_kpis(missing),
    }
