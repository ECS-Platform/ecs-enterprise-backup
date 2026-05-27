"""Bank-wide audit readiness command center — relational governance data for Audit Prep."""

from __future__ import annotations

from typing import Any

from app.governance_relational_model import APP_OWNERS, FRAMEWORK_GRAPHS, get_framework_graph

BANKING_APPS = [
    "Net Banking", "Mobile Banking", "UPI", "Treasury", "Loan System",
    "Payments", "Wealth Portal", "Internet Banking", "Card Platform", "CRM",
]

READINESS_THRESHOLD = 75


def _all_frameworks() -> list[str]:
    return list(FRAMEWORK_GRAPHS.keys()) or [
        "PCI DSS", "DPSC", "OS Baselining", "DB Baselining", "Nginx Baselining",
        "AppSec", "VAPT", "CSITE", "ITPP",
    ]


def _build_upcoming_audits() -> list[dict]:
    return [
        {"application": "Net Banking", "framework": "PCI DSS", "auditor": "Deloitte", "audit_scope": "CDE · cardholder data · MFA · firewall", "audit_type": "External Regulator", "date": "2026-06-15", "days_remaining": 22, "readiness_pct": 82, "blockers": 4, "evidence_completion_pct": 88, "escalation": "None", "owner": "R. Mehta"},
        {"application": "Mobile Banking", "framework": "AppSec", "auditor": "Internal Audit", "audit_scope": "SAST · secrets · SDLC gates", "audit_type": "Internal SDLC Audit", "date": "2026-06-08", "days_remaining": 15, "readiness_pct": 74, "blockers": 6, "evidence_completion_pct": 79, "escalation": "App Owner", "owner": "A. Sharma"},
        {"application": "UPI", "framework": "VAPT", "auditor": "EY", "audit_scope": "External pentest · SSRF · WAF validation", "audit_type": "External VAPT Retest", "date": "2026-06-22", "days_remaining": 29, "readiness_pct": 61, "blockers": 8, "evidence_completion_pct": 72, "escalation": "CISO Office", "owner": "P. Nair"},
        {"application": "Treasury", "framework": "DPSC", "auditor": "KPMG", "audit_scope": "Privileged access · PAM · DB audit logs", "audit_type": "External Compliance", "date": "2026-07-08", "days_remaining": 45, "readiness_pct": 91, "blockers": 2, "evidence_completion_pct": 94, "escalation": "None", "owner": "S. Banerjee"},
        {"application": "Internet Banking", "framework": "PCI DSS", "auditor": "Deloitte", "audit_scope": "Req 8.3 MFA · Req 10.6 log review", "audit_type": "External Regulator", "date": "2026-06-28", "days_remaining": 35, "readiness_pct": 78, "blockers": 3, "evidence_completion_pct": 85, "escalation": "None", "owner": "A. Sharma"},
        {"application": "CBS Oracle", "framework": "ITPP", "auditor": "Internal Audit", "audit_scope": "DR restore test · change management CAB", "audit_type": "Internal ITGC", "date": "2026-07-20", "days_remaining": 57, "readiness_pct": 89, "blockers": 2, "evidence_completion_pct": 91, "escalation": "None", "owner": "S. Banerjee"},
        {"application": "Loan System", "framework": "AppSec", "auditor": "Internal Audit", "audit_scope": "Checkmarx SAST · dependency approval", "audit_type": "Internal SDLC Audit", "date": "2026-06-12", "days_remaining": 19, "readiness_pct": 71, "blockers": 5, "evidence_completion_pct": 76, "escalation": "App Owner", "owner": "V. Rao"},
        {"application": "Wealth Portal", "framework": "VAPT", "auditor": "EY", "audit_scope": "DAST · auth bypass · TLS posture", "audit_type": "External VAPT Retest", "date": "2026-07-01", "days_remaining": 38, "readiness_pct": 77, "blockers": 3, "evidence_completion_pct": 83, "escalation": "None", "owner": "V. Rao"},
    ]


def _build_gaps_from_graphs() -> list[dict]:
    gaps = []
    for fw, g in FRAMEWORK_GRAPHS.items():
        for gap in g.get("open_gaps", []):
            ctrl = next((c for c in g["controls"] if c["control_id"] == gap["control_id"]), {})
            gaps.append({
                "application": gap["application"],
                "framework": fw,
                "control_id": gap["control_id"],
                "control_name": ctrl.get("control_name", gap["control_id"]),
                "gap_description": gap["description"],
                "evidence_missing": ctrl.get("evidence_name", "Required evidence not uploaded"),
                "sla": ctrl.get("sla", "At Risk"),
                "sla_days": ctrl.get("sla_days", 0),
                "owner": gap.get("owner", APP_OWNERS.get(gap["application"], "R. Mehta")),
                "days_remaining": max(0, 30 - gap.get("sla_days", ctrl.get("sla_days", 10))),
                "due_date": "2026-06-05",
                "audit_impact": gap.get("risk", "High"),
                "priority": gap.get("risk", "High"),
                "finding_id": gap.get("finding_id", "—"),
                "audit_dependency": f"{fw} audit cycle Q2 2026",
                "status": "Open",
            })
        for ctrl in g.get("controls", []):
            if ctrl.get("validation") == "FAIL":
                gaps.append({
                    "application": ctrl["application"],
                    "framework": fw,
                    "control_id": ctrl["control_id"],
                    "control_name": ctrl["control_name"],
                    "gap_description": ctrl.get("auditor_comment", "Validation failed"),
                    "evidence_missing": ctrl.get("evidence_name", "—"),
                    "sla": ctrl.get("sla", "Breached"),
                    "sla_days": ctrl.get("sla_days", 0),
                    "owner": ctrl.get("owner", APP_OWNERS.get(ctrl["application"], "R. Mehta")),
                    "days_remaining": max(0, 14 - ctrl.get("sla_days", 0)),
                    "due_date": "2026-05-28" if ctrl.get("sla") == "Breached" else "2026-06-10",
                    "audit_impact": "Critical",
                    "priority": "Critical" if ctrl.get("sla") == "Breached" else "High",
                    "finding_id": "—",
                    "audit_dependency": ctrl.get("pending_action", "Audit blocker"),
                    "status": "Failed Validation",
                })
    return gaps


def _build_upload_queue(role: str = "owner") -> list[dict]:
    from app.missing_evidence_engine import get_all_missing_evidence

    return get_all_missing_evidence(role)


def _build_auditor_requests() -> list[dict]:
    return [
        {"request": "Firewall rule export — Net Banking CDE segment", "requested_evidence": "Firewall ACL export Q2-2026", "auditor": "Deloitte", "framework": "PCI DSS", "application": "Net Banking", "linked_control": "PCI-1.2", "due": "2026-05-28", "owner": "R. Mehta", "priority": "Critical", "escalation": "None", "days_overdue": 0},
        {"request": "MFA enforcement screenshot — Internet Banking admin console", "requested_evidence": "MFA policy screenshot + PAM logs", "auditor": "Deloitte", "framework": "PCI DSS", "application": "Internet Banking", "linked_control": "PCI-8.3", "due": "2026-05-30", "owner": "A. Sharma", "priority": "High", "escalation": "App Owner", "days_overdue": 0},
        {"request": "Retest closure evidence — UPI SSRF remediation", "requested_evidence": "Qualys retest report + WAF validation", "auditor": "EY", "framework": "VAPT", "application": "UPI", "linked_control": "VP-C-03", "due": "2026-05-26", "owner": "P. Nair", "priority": "Critical", "escalation": "CISO Office", "days_overdue": 2},
        {"request": "GitHub secret scan clean report — Mobile Banking", "requested_evidence": "Secret rotation proof + clean scan export", "auditor": "Internal Audit", "framework": "AppSec", "application": "Mobile Banking", "linked_control": "AS-C-04", "due": "2026-05-28", "owner": "A. Sharma", "priority": "Critical", "escalation": "App Owner", "days_overdue": 0},
        {"request": "Privileged access review Q2 — Treasury DB", "requested_evidence": "PAM export + DBA attestation", "auditor": "KPMG", "framework": "DPSC", "application": "Treasury", "linked_control": "DP-C-02", "due": "2026-06-02", "owner": "S. Banerjee", "priority": "High", "escalation": "None", "days_overdue": 0},
        {"request": "Restore test report — CBS Oracle DR", "requested_evidence": "Q2 restore test execution report", "auditor": "Internal Audit", "framework": "ITPP", "application": "CBS Oracle", "linked_control": "IT-C-03", "due": "2026-06-10", "owner": "S. Banerjee", "priority": "High", "escalation": "DBA Lead", "days_overdue": 0},
    ]


def _build_evidence_freshness() -> dict:
    stale, expiring, rejected, reuse_expiring = [], [], [], []
    for fw, g in FRAMEWORK_GRAPHS.items():
        for ev in g.get("evidence", []):
            row = {**ev, "framework": fw}
            life = ev.get("lifecycle", "")
            if life == "Expired" or ev.get("validation") == "Failed":
                stale.append(row)
            elif life == "Pending Review":
                expiring.append(row)
            elif life == "Rejected":
                rejected.append(row)
            elif ev.get("reuse_eligible"):
                reuse_expiring.append(row)
    return {
        "stale": stale[:12],
        "expiring": expiring[:10],
        "rejected": rejected[:10],
        "reuse_expiring": reuse_expiring[:8],
        "stale_count": len(stale),
        "expiring_count": len(expiring),
        "rejected_count": len(rejected),
    }


def _build_readiness_by_application() -> list[dict]:
    app_map: dict[str, dict] = {}
    for fw, g in FRAMEWORK_GRAPHS.items():
        for a in g.get("applications", []):
            name = a["name"]
            if name not in app_map:
                app_map[name] = {"application": name, "owner": a.get("owner", APP_OWNERS.get(name, "R. Mehta")), "scores": [], "frameworks": set()}
            app_map[name]["scores"].append(a.get("audit_readiness_pct", 80))
            app_map[name]["frameworks"].add(fw)
    rows = []
    for name, data in app_map.items():
        avg = round(sum(data["scores"]) / max(len(data["scores"]), 1), 1)
        rows.append({
            "application": name,
            "owner": data["owner"],
            "readiness_pct": avg,
            "frameworks": sorted(data["frameworks"]),
            "framework_count": len(data["frameworks"]),
        })
    return sorted(rows, key=lambda x: x["readiness_pct"])


def _build_readiness_by_framework() -> list[dict]:
    rows = []
    for fw, g in FRAMEWORK_GRAPHS.items():
        apps = g.get("applications", [])
        if not apps:
            continue
        avg = round(sum(a.get("audit_readiness_pct", 0) for a in apps) / len(apps), 1)
        gap_count = len(g.get("open_gaps", [])) + sum(1 for c in g.get("controls", []) if c.get("validation") == "FAIL")
        rows.append({"framework": fw, "readiness_pct": avg, "applications": len(apps), "gap_count": gap_count})
    return sorted(rows, key=lambda x: x["readiness_pct"])


def _build_missing_breakdown() -> dict:
    counts: dict[str, int] = {}
    details = []
    for fw, g in FRAMEWORK_GRAPHS.items():
        n = len(g.get("open_gaps", [])) + sum(1 for c in g.get("controls", []) if c.get("validation") in ("FAIL", "WARN"))
        counts[fw] = n
        for gap in g.get("open_gaps", []):
            details.append({
                "framework": fw,
                "application": gap["application"],
                "control_id": gap["control_id"],
                "control_name": gap["control_id"],
                "owner": gap.get("owner", APP_OWNERS.get(gap["application"], "R. Mehta")),
                "due_date": "2026-06-05",
                "evidence_missing": gap["description"],
                "audit_dependency": f"{fw} Q2 2026 audit",
                "priority": gap.get("risk", "High"),
            })
    return {"by_framework": [{"framework": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])], "details": details}


def _build_poor_readiness_contributors() -> list[dict]:
    contrib = []
    for fw, g in FRAMEWORK_GRAPHS.items():
        for a in g.get("applications", []):
            if a.get("audit_readiness_pct", 100) >= READINESS_THRESHOLD:
                continue
            contrib.append({
                "application": a["name"],
                "owner": a.get("owner", APP_OWNERS.get(a["name"], "R. Mehta")),
                "framework": fw,
                "readiness_pct": a.get("audit_readiness_pct", 0),
                "stale_evidence": a.get("stale_evidence", 0),
                "failed_validations": a.get("failed_controls", 0),
                "open_findings": a.get("open_findings", 0),
                "sla_breaches": a.get("sla_breaches", 0),
                "summary": f"{a.get('stale_evidence', 0)} stale · {a.get('failed_controls', 0)} failed · {a.get('open_findings', 0)} findings",
            })
    return sorted(contrib, key=lambda x: x["readiness_pct"])[:10]


def _build_trends() -> list[dict]:
    return [
        {"label": "PCI readiness trend", "framework": "PCI DSS", "application_scope": "Net Banking, Internet Banking", "date_range": "Dec 2025 – May 2026", "series": [{"month": "Dec", "pct": 72}, {"month": "Jan", "pct": 75}, {"month": "Feb", "pct": 78}, {"month": "Mar", "pct": 80}, {"month": "Apr", "pct": 81}, {"month": "May", "pct": 82}]},
        {"label": "AppSec evidence rejection trend", "framework": "AppSec", "application_scope": "Mobile Banking, Loan System", "date_range": "Dec 2025 – May 2026", "series": [{"month": "Dec", "count": 8}, {"month": "Jan", "count": 7}, {"month": "Feb", "count": 6}, {"month": "Mar", "count": 5}, {"month": "Apr", "count": 4}, {"month": "May", "count": 3}]},
        {"label": "VAPT remediation aging (days)", "framework": "VAPT", "application_scope": "UPI, Internet Banking, Net Banking", "date_range": "Dec 2025 – May 2026", "series": [{"month": "Dec", "days": 42}, {"month": "Jan", "days": 38}, {"month": "Feb", "days": 34}, {"month": "Mar", "days": 28}, {"month": "Apr", "days": 22}, {"month": "May", "days": 18}]},
        {"label": "Auditor request backlog", "framework": "All", "application_scope": "Bank-wide", "date_range": "Dec 2025 – May 2026", "series": [{"month": "Dec", "count": 24}, {"month": "Jan", "count": 21}, {"month": "Feb", "count": 18}, {"month": "Mar", "count": 14}, {"month": "Apr", "count": 11}, {"month": "May", "count": 8}]},
        {"label": "Stale evidence reduction", "framework": "All", "application_scope": "Bank-wide", "date_range": "Dec 2025 – May 2026", "series": [{"month": "Dec", "count": 48}, {"month": "Jan", "count": 42}, {"month": "Feb", "count": 36}, {"month": "Mar", "count": 28}, {"month": "Apr", "count": 22}, {"month": "May", "count": 16}]},
        {"label": "UPI readiness improvement", "framework": "VAPT + PCI DSS", "application_scope": "UPI", "date_range": "Dec 2025 – May 2026", "series": [{"month": "Dec", "pct": 52}, {"month": "Jan", "pct": 55}, {"month": "Feb", "pct": 57}, {"month": "Mar", "pct": 59}, {"month": "Apr", "pct": 60}, {"month": "May", "pct": 61}]},
    ]


def _filters_active(filters: dict[str, str] | None) -> bool:
    return bool(filters and any(v and not str(v).startswith("All ") for v in filters.values()))


def _filter_trends(trends: list[dict], filters: dict[str, str] | None) -> list[dict]:
    if not _filters_active(filters):
        return trends
    fw = filters.get("framework", "")
    app = filters.get("application", "")
    out = []
    for t in trends:
        if fw and fw not in t.get("framework", "") and t.get("framework") != "All":
            continue
        if app and app not in t.get("application_scope", ""):
            continue
        out.append(t)
    return out or trends[:2]


def _build_owner_delays(gaps: list[dict], requests: list[dict]) -> list[dict]:
    owners: dict[str, dict] = {}
    for g in gaps:
        o = g.get("owner", "Unassigned")
        if o not in owners:
            owners[o] = {"owner": o, "open_gaps": 0, "overdue_requests": 0, "sla_breaches": 0, "applications": set()}
        owners[o]["open_gaps"] += 1
        owners[o]["applications"].add(g.get("application", ""))
        if g.get("sla") == "Breached":
            owners[o]["sla_breaches"] += 1
    for r in requests:
        o = r.get("owner", "Unassigned")
        if o not in owners:
            owners[o] = {"owner": o, "open_gaps": 0, "overdue_requests": 0, "sla_breaches": 0, "applications": set()}
        if r.get("days_overdue", 0) > 0:
            owners[o]["overdue_requests"] += 1
        owners[o]["applications"].add(r.get("application", ""))
    rows = []
    for data in owners.values():
        delay_score = data["open_gaps"] + data["overdue_requests"] * 2 + data["sla_breaches"]
        if delay_score < 1:
            continue
        rows.append({
            "owner": data["owner"],
            "open_gaps": data["open_gaps"],
            "overdue_requests": data["overdue_requests"],
            "sla_breaches": data["sla_breaches"],
            "applications": ", ".join(sorted(a for a in data["applications"] if a)),
            "delay_score": delay_score,
        })
    return sorted(rows, key=lambda x: -x["delay_score"])[:8]


def _filter_rows(rows: list[dict], filters: dict[str, str] | None) -> list[dict]:
    if not filters:
        return rows
    out = []
    for row in rows:
        ok = True
        for key, val in filters.items():
            if not val or val.startswith("All "):
                continue
            if key == "risk":
                cell = str(row.get("priority", row.get("risk", row.get("audit_impact", ""))))
            elif key == "status":
                cell = str(row.get("status", row.get("escalation", "")))
            else:
                cell = str(row.get(key, ""))
            if val not in cell and cell != val:
                ok = False
                break
        if ok:
            out.append(row)
    return out


def build_audit_prep_view(role: str = "owner", filters: dict[str, str] | None = None) -> dict[str, Any]:
    """Full audit prep command center view — filter-aware."""
    filters = filters or {}
    filters_on = _filters_active(filters)
    readiness_apps = _build_readiness_by_application()
    readiness_fw = _build_readiness_by_framework()
    gaps = _build_gaps_from_graphs()
    uploads = _build_upload_queue(role)
    audits = _build_upcoming_audits()
    requests = _build_auditor_requests()
    missing = _build_missing_breakdown()
    freshness = _build_evidence_freshness()
    contributors = _build_poor_readiness_contributors()
    trends = _filter_trends(_build_trends(), filters)

    f_gaps = _filter_rows(gaps, filters)
    f_uploads = _filter_rows(uploads, filters)
    f_audits = _filter_rows(audits, filters)
    f_requests = _filter_rows(requests, filters)
    f_apps = _filter_rows(readiness_apps, filters)
    f_missing_details = _filter_rows(missing["details"], filters)
    f_contributors = _filter_rows(contributors, filters) if filters_on else contributors
    f_readiness_fw = [f for f in readiness_fw if not filters.get("framework") or f["framework"] == filters["framework"]]

    active_gaps = f_gaps if filters_on else gaps
    active_apps = f_apps if filters_on else readiness_apps
    if filters_on and not active_apps:
        active_apps = []
    weighted = round(sum(a["readiness_pct"] for a in active_apps) / max(len(active_apps), 1), 1) if active_apps else 0
    total_gaps = len(active_gaps)
    app_count = len(set(g["application"] for g in active_gaps)) if active_gaps else 0
    gap_fw_breakdown = {}
    for g in active_gaps:
        gap_fw_breakdown[g["framework"]] = gap_fw_breakdown.get(g["framework"], 0) + 1

    below_threshold = [a for a in active_apps if a["readiness_pct"] < READINESS_THRESHOLD]
    critical_blockers = [g for g in active_gaps if g.get("priority") in ("Critical", "High")][:8]
    overdue_gaps = [g for g in active_gaps if g.get("sla") == "Breached" or g.get("days_remaining", 99) <= 7][:10]
    active_audits = f_audits if filters_on else audits
    active_requests = f_requests if filters_on else requests
    next_audit = min(active_audits, key=lambda x: x["days_remaining"], default=None) if active_audits else None
    owner_delays = _build_owner_delays(active_gaps, active_requests)

    # Filter evidence freshness lists
    def _fresh_filter(items: list[dict]) -> list[dict]:
        if not filters_on:
            return items
        return _filter_rows(items, filters)

    freshness_filtered = {
        **freshness,
        "stale": _fresh_filter(freshness["stale"]),
        "expiring": _fresh_filter(freshness["expiring"]),
        "rejected": _fresh_filter(freshness["rejected"]),
        "reuse_expiring": _fresh_filter(freshness["reuse_expiring"]),
        "stale_count": len(_fresh_filter(freshness["stale"])) if filters_on else freshness["stale_count"],
        "expiring_count": len(_fresh_filter(freshness["expiring"])) if filters_on else freshness["expiring_count"],
        "rejected_count": len(_fresh_filter(freshness["rejected"])) if filters_on else freshness["rejected_count"],
    }

    from app.missing_evidence_engine import compute_upload_kpis

    upload_kpis = compute_upload_kpis(f_uploads if filters_on else uploads)
    submissions = []
    for i, g in enumerate(active_gaps[:12]):
        submissions.append({
            "submission_id": f"SUB-{i + 1:04d}",
            "framework": g["framework"],
            "control": g["control_name"],
            "control_id": g["control_id"],
            "application": g["application"],
            "owner": g["owner"],
            "status": g.get("status", "Pending"),
            "due": "2026-06-05",
        })

    return {
        "kpis": [
            {"label": "Audit Readiness", "value": f"{weighted}%", "hint": "Weighted average across selected applications & frameworks", "tone": "success" if weighted >= READINESS_THRESHOLD else "warning"},
            {"label": "Unresolved Control Gaps", "value": total_gaps, "hint": f"{total_gaps} gaps across {app_count or len(active_apps)} applications", "tone": "danger"},
            {"label": "Upcoming Audits", "value": len(active_audits), "hint": next_audit and f"Next: {next_audit['framework']} · {next_audit['application']} in {next_audit['days_remaining']}d" or "Scheduled audits", "tone": "primary"},
            {"label": "Auditor Requests", "value": len(active_requests), "hint": "Pending evidence requests from auditors", "tone": "warning"},
            {"label": "Stale Evidence", "value": freshness_filtered["stale_count"], "hint": "Evidence freshness risk items", "tone": "danger"},
            {"label": "Below Threshold", "value": len(below_threshold), "hint": f"Applications under {READINESS_THRESHOLD}% readiness", "tone": "danger"},
        ],
        "readiness_label": "Audit readiness across selected applications and frameworks",
        "weighted_readiness_pct": weighted,
        "readiness_by_application": active_apps,
        "readiness_by_framework": f_readiness_fw if filters_on else readiness_fw,
        "missing_controls_breakdown": gap_fw_breakdown,
        "missing_controls_total": total_gaps,
        "missing_control_details": f_missing_details if filters_on else missing["details"],
        "upcoming_audits": active_audits,
        "actionable_gaps": active_gaps,
        "upload_queue": f_uploads if filters_on else uploads,
        "missing_evidence_rows": f_uploads if filters_on else uploads,
        "upload_kpis": upload_kpis,
        "auditor_requests": active_requests,
        "evidence_freshness": freshness_filtered,
        "poor_readiness_contributors": f_contributors if filters_on else contributors,
        "critical_blockers": critical_blockers,
        "below_threshold_apps": below_threshold,
        "overdue_gaps": overdue_gaps,
        "owner_delays": owner_delays,
        "trends": trends,
        "pending_submissions": submissions,
        "next_audit_countdown": next_audit,
        "rows": active_gaps,
        "filters_active": filters_on,
        "active_filter_summary": ", ".join(f"{k}={v}" for k, v in filters.items() if v and not str(v).startswith("All ")) or "All applications & frameworks",
        "remediation_progress": [
            {"control": g["control_name"], "framework": g["framework"], "application": g["application"],
             "owner": g["owner"], "progress_pct": max(10, 100 - g.get("sla_days", 0) * 2),
             "sla_status": "Breached" if g.get("sla") == "Breached" else ("At Risk" if g.get("sla") == "At Risk" else "On Track")}
            for g in active_gaps[:10]
        ],
        "pending_auditor_requests": active_requests,
    }


def build_audit_package_preview(framework: str = "", applications: list[str] | None = None, filters: dict | None = None) -> dict:
    fw = framework or (filters or {}).get("framework") or "PCI DSS"
    apps = applications or ([(filters or {}).get("application")] if (filters or {}).get("application") else None) or ["Net Banking", "Mobile Banking"]
    apps = [a for a in apps if a]
    g = get_framework_graph(fw)
    evidence = g.get("evidence", [])[:8]
    controls = g.get("controls", [])[:12]
    pkg_name = {
        "PCI DSS": "PCI_AUDIT_PACKAGE_Q2.zip",
        "VAPT": "VAPT_RETEST_BUNDLE.zip",
        "AppSec": "APPSEC_EVIDENCE_EXPORT.zip",
    }.get(fw, f"{fw.replace(' ', '_').upper()}_AUDIT_PACKAGE_Q2.zip")
    return {
        "package_name": pkg_name,
        "frameworks": [fw],
        "applications": apps,
        "evidence_count": len(evidence) + 14,
        "controls_covered": len(controls),
        "stale_excluded": 3,
        "pending_approvals": 2,
        "rejected_excluded": 1,
        "auditor_notes": f"Q2 2026 {fw} audit package — validated evidence index for {', '.join(apps)}",
        "manifest": [{"id": e.get("evidence_id", f"EV-{i}"), "name": e.get("name", "Evidence"), "control": e.get("control_id", "—"), "status": e.get("lifecycle", "Approved")} for i, e in enumerate(evidence)],
        "included_controls": [f"{c['control_id']} — {c['control_name']} ({c['application']})" for c in controls[:8]],
        "excluded": ["EV-STALE-001 — Expired firewall export", "EV-REJ-002 — Rejected MFA screenshot"],
        "bundle_files": ["PCI_AUDIT_PACKAGE_Q2.zip", "VAPT_RETEST_BUNDLE.zip", "APPSEC_EVIDENCE_EXPORT.zip"],
        "generated_at": "2026-05-24 06:30 UTC",
    }


def build_export_bundle_preview(filters: dict | None = None) -> dict:
    apps = BANKING_APPS[:6]
    if filters and filters.get("application"):
        apps = [filters["application"]]
    fws = _all_frameworks()[:5]
    if filters and filters.get("framework"):
        fws = [filters["framework"]]
    return {
        "bundle_name": "ECS_EVIDENCE_BUNDLE_Q2_2026.zip",
        "scope": f"Multi-framework export — {', '.join(apps[:3])}{'…' if len(apps) > 3 else ''}",
        "applications": apps,
        "frameworks": fws,
        "evidence_inventory": 156,
        "reuse_mappings": 12,
        "checksum": "sha256:a3f8c2e91b4d7e6f0a1b2c3d4e5f6789",
        "export_timestamp": "2026-05-24 06:35 UTC",
        "control_mappings": 89,
        "pending_approvals": 4,
        "files": ["PCI_AUDIT_PACKAGE_Q2.zip", "VAPT_RETEST_BUNDLE.zip", "APPSEC_EVIDENCE_EXPORT.zip"],
    }
