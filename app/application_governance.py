"""Application-centric governance views per framework."""

from __future__ import annotations

import hashlib

from app import ecs_state
from app.framework_catalog import get_framework_controls
from app.framework_governance_data import get_application_drilldown, get_framework_profile
from app.governance_relational_model import APP_OWNERS, build_relational_view, get_framework_graph


def _owner(app: str) -> str:
    return APP_OWNERS.get(app, "R. Mehta")

GOVERNANCE_APPLICATIONS = [
    "Net Banking",
    "Mobile Banking",
    "UPI",
    "Cards",
    "Card Payments",
    "Core Banking",
    "Oracle Core DB",
    "Payments DB",
    "Treasury DB",
    "UPI Gateway",
    "API Gateway",
    "Mobile Banking Edge",
    "Wealth Portal",
    "Loan System",
    "Internet Banking",
    "Retail Banking",
    "Payments",
    "Treasury",
    "UPI Switch",
    "CBS Oracle",
    "Corporate Banking",
]


def _seed(seed: str, lo: int, hi: int) -> int:
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return lo + (h % (hi - lo + 1))


def _app_controls(framework_name: str, application: str, catalog_controls: list[dict] | None = None) -> list[dict]:
    controls = catalog_controls or get_framework_controls(framework_name)
    rows = []
    for ctrl in controls:
        app_evs = [ev for ev in ctrl.get("evidences", []) if ev.get("application_name") == application]
        if not app_evs:
            continue
        ckey = ecs_state.control_key(framework_name, ctrl["control"])
        rows.append({
            "control": ctrl["control"],
            "control_id": ctrl.get("control_id", ""),
            "evidences": app_evs,
            "ckey": ckey,
            "workflow_status": ecs_state.control_status(framework_name, ctrl["control"]),
            "reject_reason": ecs_state.rejected_controls.get(ckey, {}).get("reason", ""),
        })
    return rows


def build_application_grid(framework_name: str, catalog_controls: list[dict] | None = None) -> list[dict]:
    """Framework-specific application summary from relational governance graph."""
    rel = build_relational_view(framework_name)
    if rel["applications"]:
        cards = []
        for a in rel["applications"]:
            cards.append({
                "name": a["name"],
                "owner": a.get("owner", _owner(a["name"])),
                "implemented": a.get("controls_implemented", 0),
                "pending": a.get("open_findings", 0) + a.get("failed_controls", 0),
                "findings": a.get("open_findings", 0),
                "failed_controls": a.get("failed_controls", 0),
                "expired": a.get("stale_evidence", 0),
                "stale_evidences": a.get("stale_evidence", 0),
                "pending_approvals": a.get("failed_controls", 0),
                "auditor_queue": a.get("open_findings", 0),
                "audit_readiness_pct": a.get("audit_readiness_pct", 0),
                "compliance_pct": a.get("audit_readiness_pct", 0),
                "last_refresh": "2026-05-22",
                "last_validation": "2026-05-22",
                "risk_rating": "High" if a.get("failed_controls", 0) > 1 else ("Medium" if a.get("open_findings", 0) > 2 else "Low"),
                "sla_breaches": a.get("sla_breaches", 0),
                "coverage_pct": a.get("audit_readiness_pct", 0),
                "focus": a.get("focus", ""),
            })
        return cards

    controls = catalog_controls or get_framework_controls(framework_name)
    profile = get_framework_profile(framework_name)
    profile_apps = profile.get("applications", [])

    if profile_apps:
        g = get_framework_graph(framework_name)
        cards = []
        for app_data in profile_apps:
            app = app_data["name"]
            seed = f"{framework_name}::{app}"
            implemented = pending = findings = expired = approvals = 0
            last_refresh = app_data.get("last_validation", "—")
            stale_count = app_data.get("stale_evidences", 0)

            for ctrl in controls:
                ckey = ecs_state.control_key(framework_name, ctrl["control"])
                has_app = any(ev.get("application_name") == app for ev in ctrl.get("evidences", []))
                if not has_app:
                    continue
                if ckey in ecs_state.approved_controls:
                    implemented += 1
                elif ckey in ecs_state.submitted_controls:
                    pending += 1
                    approvals += 1
                elif ckey in ecs_state.rejected_controls:
                    pending += 1
                    findings += 1
                else:
                    pending += 1
                for ev in ctrl.get("evidences", []):
                    if ev.get("application_name") != app:
                        continue
                    if ev.get("evidence_status") == "Expired":
                        expired += 1
                    ts = ev.get("upload_timestamp", "")
                    if ts and (last_refresh == "—" or ts[:10] > last_refresh):
                        last_refresh = ts[:10]

            compliance = app_data.get("compliance_pct", round((implemented / max(implemented + pending, 1)) * 100, 1))
            if implemented + pending > 0:
                live_compliance = round((implemented / (implemented + pending)) * 100, 1)
                compliance = live_compliance if implemented > 0 else compliance

            fc_count = sum(1 for c in g["controls"] if c.get("application") == app and c.get("validation") == "FAIL")
            app_findings = [f for f in g["findings"] if f["application"] == app]

            cards.append({
                "name": app,
                "implemented": implemented or _seed(seed + "impl", 8, 18),
                "pending": pending or app_data.get("pending_approvals", 0),
                "findings": findings or app_data.get("findings", 0) or len(app_findings),
                "failed_controls": fc_count,
                "expired": expired or app_data.get("stale_evidences", 0),
                "stale_evidences": stale_count,
                "pending_approvals": approvals or app_data.get("pending_approvals", 0),
                "auditor_queue": app_data.get("auditor_queue", app_data.get("pending_approvals", 0)),
                "audit_readiness_pct": compliance,
                "compliance_pct": compliance,
                "last_refresh": last_refresh,
                "last_validation": app_data.get("last_validation", last_refresh),
                "risk_rating": app_data.get("risk_rating", "Medium"),
                "sla_breaches": _seed(seed + "sla", 0, 4),
                "coverage_pct": compliance,
                "focus": app_data.get("focus", ""),
            })
        return cards

    # Fallback for frameworks without profile apps
    apps_in_catalog = {
        ev.get("application_name")
        for c in controls
        for ev in c.get("evidences", [])
        if ev.get("application_name")
    }
    app_names = [a for a in GOVERNANCE_APPLICATIONS if a in apps_in_catalog]
    for a in sorted(apps_in_catalog):
        if a not in app_names:
            app_names.append(a)

    cards = []
    for app in app_names:
        seed = f"{framework_name}::{app}"
        implemented = pending = findings = expired = approvals = 0
        last_refresh = "—"
        stale_count = 0
        for ctrl in controls:
            ckey = ecs_state.control_key(framework_name, ctrl["control"])
            has_app = any(ev.get("application_name") == app for ev in ctrl.get("evidences", []))
            if not has_app:
                continue
            if ckey in ecs_state.approved_controls:
                implemented += 1
            elif ckey in ecs_state.submitted_controls:
                pending += 1
                approvals += 1
            elif ckey in ecs_state.rejected_controls:
                pending += 1
                findings += 1
            else:
                pending += 1
            for ev in ctrl.get("evidences", []):
                if ev.get("application_name") != app:
                    continue
                if ev.get("evidence_status") == "Expired":
                    expired += 1
                if ev.get("evidence_status") in ("Expired", "Due for Refresh"):
                    stale_count += 1
                ts = ev.get("upload_timestamp", "")
                if ts and (last_refresh == "—" or ts > last_refresh):
                    last_refresh = ts[:10] if len(ts) >= 10 else ts

        total = max(implemented + pending, 1)
        compliance = round((implemented / total) * 100, 1)
        risk = "Low"
        if findings > 2 or expired > 1:
            risk = "High"
        elif findings > 0 or expired > 0 or pending > 3:
            risk = "Medium"

        cards.append({
            "name": app,
            "implemented": implemented,
            "pending": pending,
            "findings": findings,
            "expired": expired,
            "stale_evidences": stale_count,
            "pending_approvals": approvals,
            "audit_readiness_pct": compliance,
            "compliance_pct": compliance,
            "last_refresh": last_refresh,
            "last_validation": last_refresh,
            "risk_rating": risk,
            "sla_breaches": _seed(seed + "sla", 0, 4),
            "coverage_pct": compliance,
        })
    return cards


def build_application_view(
    framework_name: str,
    application: str,
    catalog_controls: list[dict] | None = None,
) -> dict | None:
    profile_apps = {a["name"] for a in get_framework_profile(framework_name).get("applications", [])}
    if application not in GOVERNANCE_APPLICATIONS and application not in profile_apps and not _app_controls(framework_name, application, catalog_controls):
        return None
    rows = _app_controls(framework_name, application, catalog_controls)
    seed = f"{framework_name}::{application}"
    pending = sum(
        1 for r in rows
        if r["ckey"] in ecs_state.submitted_controls or r["ckey"] in ecs_state.rejected_controls
    )
    drilldown = get_application_drilldown(framework_name, application)
    g = get_framework_graph(framework_name)
    app_findings = [f for f in g["findings"] if f["application"] == application]
    app_failed = [c for c in g["controls"] if c["application"] == application and c.get("validation") == "FAIL"]
    app_controls = [c for c in g["controls"] if c["application"] == application]
    if app_findings or app_failed or app_controls:
        sections = []
        if drilldown and drilldown.get("sections"):
            sections.extend(drilldown["sections"])
        if app_failed:
            sections.append({"title": "Failed Controls", "items": [f"{c['control_id']} — {c['control_name']}: {c.get('auditor_comment', '')}" for c in app_failed]})
        if app_findings:
            sections.append({"title": "Open Findings", "items": [f"{f['finding_id']}: {f['observation']} → {f['linked_control']} ({f['severity']})" for f in app_findings]})
        if app_controls:
            sections.append({"title": "Control Posture", "items": [f"{c['control_id']} {c['control_name']} — {c['workflow']} · Owner: {c['owner']}" for c in app_controls]})
        drilldown = {"sections": sections}
    profile_app = next(
        (a for a in get_framework_profile(framework_name).get("applications", []) if a["name"] == application),
        None,
    )
    return {
        "application": application,
        "framework": framework_name,
        "controls": rows,
        "implemented": sum(1 for r in rows if r["ckey"] in ecs_state.approved_controls) or (profile_app and _seed(seed + "i", 6, 14)),
        "pending": pending or (profile_app and profile_app.get("pending_approvals", 0)),
        "findings": sum(1 for r in rows if r["ckey"] in ecs_state.rejected_controls) or (profile_app and profile_app.get("findings", 0)),
        "expired": sum(
            1 for r in rows for ev in r["evidences"] if ev.get("evidence_status") == "Expired"
        ) or (profile_app and profile_app.get("stale_evidences", 0)),
        "audit_readiness_pct": profile_app["compliance_pct"] if profile_app else _seed(seed + "v", 75, 95),
        "risk_rating": profile_app["risk_rating"] if profile_app else ("High" if pending > 3 else ("Medium" if pending else "Low")),
        "focus": profile_app.get("focus", "") if profile_app else "",
        "drilldown": drilldown,
    }
