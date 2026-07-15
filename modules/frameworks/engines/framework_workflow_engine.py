"""Framework-scoped evidence workflow metrics and drill datasets."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from app import ecs_state
from modules.shared.utils.demo_data_standards import BANKING_APPLICATIONS, BANKING_OWNERS, ensure_drill_rows, generate_standard_drill_row, pick, seed, between
from modules.frameworks.engines.framework_catalog import get_framework_controls
from modules.governance.engines.governance_relational_model import get_framework_graph

ALL_FRAMEWORKS = [
    "PCI DSS", "DPSC", "OS Baselining", "DB Baselining", "Nginx Baselining",
    "AppSec", "VAPT", "CSITE", "ITPP", "ITDRM", "SOC2", "ISO27001", "RBI Cyber Security",
    "ISG", "SSD", "Framework Loader",
]

# Per-framework metric ranges — ensures visibly different values across frameworks
_FW_RANGES: dict[str, dict[str, tuple[int, int]]] = {
    "PCI DSS": {"draft": (22, 48), "submitted": (18, 42), "reupload": (1, 8), "approved": (35, 72), "findings": (6, 18), "readiness": (78, 92)},
    "DPSC": {"draft": (14, 36), "submitted": (12, 28), "reupload": (2, 10), "approved": (28, 55), "findings": (8, 22), "readiness": (82, 94)},
    "OS Baselining": {"draft": (32, 68), "submitted": (24, 52), "reupload": (3, 14), "approved": (40, 88), "findings": (12, 32), "readiness": (74, 88)},
    "DB Baselining": {"draft": (18, 44), "submitted": (16, 38), "reupload": (1, 9), "approved": (30, 62), "findings": (5, 16), "readiness": (80, 93)},
    "Nginx Baselining": {"draft": (10, 28), "submitted": (8, 22), "reupload": (0, 6), "approved": (18, 42), "findings": (4, 14), "readiness": (85, 96)},
    "AppSec": {"draft": (28, 58), "submitted": (20, 48), "reupload": (4, 16), "approved": (22, 50), "findings": (14, 38), "readiness": (68, 84)},
    "VAPT": {"draft": (16, 40), "submitted": (14, 32), "reupload": (2, 12), "approved": (20, 45), "findings": (18, 52), "readiness": (72, 86)},
    "CSITE": {"draft": (20, 46), "submitted": (18, 40), "reupload": (1, 7), "approved": (32, 68), "findings": (10, 28), "readiness": (76, 90)},
    "ITPP": {"draft": (24, 52), "submitted": (20, 44), "reupload": (2, 9), "approved": (38, 78), "findings": (6, 20), "readiness": (84, 96)},
    "ITDRM": {"draft": (12, 32), "submitted": (10, 26), "reupload": (1, 5), "approved": (24, 52), "findings": (8, 18), "readiness": (79, 91)},
    "SOC2": {"draft": (18, 38), "submitted": (16, 34), "reupload": (0, 5), "approved": (42, 82), "findings": (4, 12), "readiness": (86, 97)},
    "ISO27001": {"draft": (20, 42), "submitted": (18, 36), "reupload": (1, 6), "approved": (36, 74), "findings": (5, 15), "readiness": (81, 94)},
    "RBI Cyber Security": {"draft": (26, 54), "submitted": (22, 46), "reupload": (3, 11), "approved": (34, 70), "findings": (9, 24), "readiness": (77, 89)},
    "ISG": {"draft": (15, 38), "submitted": (12, 30), "reupload": (1, 7), "approved": (28, 58), "findings": (7, 19), "readiness": (81, 93)},
    "SSD": {"draft": (11, 30), "submitted": (9, 24), "reupload": (0, 5), "approved": (20, 48), "findings": (5, 14), "readiness": (83, 95)},
    "Framework Loader": {"draft": (8, 22), "submitted": (6, 18), "reupload": (0, 4), "approved": (14, 36), "findings": (3, 10), "readiness": (86, 97)},
}


def _seed_int(key: str, lo: int, hi: int) -> int:
    h = int(hashlib.md5(key.encode()).hexdigest(), 16)
    return lo + (h % max(hi - lo + 1, 1))


def _fw_metric(framework: str, name: str) -> int:
    ranges = _FW_RANGES.get(framework, _FW_RANGES["PCI DSS"])
    lo, hi = ranges.get(name, (5, 25))
    return _seed_int(f"{framework}::{name}", lo, hi)


def _fw_apps(framework: str, controls: list[dict]) -> set[str]:
    apps: set[str] = set()
    for c in controls:
        for ev in c.get("evidences", []):
            if ev.get("application_name"):
                apps.add(ev["application_name"])
    if not apps:
        n = _seed_int(framework, 4, 9)
        apps = set(BANKING_APPLICATIONS[:n])
    return apps


def _parse_ts_utc(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S UTC", "%Y-%m-%d %H:%M UTC"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _infer_control_state(framework: str, control: dict[str, Any]) -> str:
    key = ecs_state.control_key(framework, control.get("control", ""))
    if key in ecs_state.approved_controls:
        return "approved"
    if key in ecs_state.rejected_controls:
        return "reupload"
    if key in ecs_state.submitted_controls:
        return "submitted"
    audit_states = {str(ev.get("audit_status", "")).strip().lower() for ev in control.get("evidences", [])}
    if "rejected" in audit_states:
        return "reupload"
    if audit_states & {"submitted", "under review", "pending"}:
        return "submitted"
    if audit_states and audit_states <= {"approved"}:
        return "approved"
    return "draft"


def _workflow_row_from_evidence(
    framework: str,
    control: dict[str, Any],
    evidence: dict[str, Any],
    state: str,
    index: int,
) -> dict[str, Any]:
    s = seed("fw-wf-ev", framework, control.get("control_id", ""), evidence.get("evidence_id", ""), index)
    status_map = {
        "draft": "Draft",
        "submitted": "Pending Review",
        "pending_review": "Pending Review",
        "reupload": "Re-upload Requested",
        "approved": "Approved",
    }
    return {
        "framework": framework,
        "application": evidence.get("application_name") or "Unknown",
        "owner": evidence.get("uploaded_by") or pick(s, BANKING_OWNERS),
        "control": control.get("control", "—"),
        "control_id": control.get("control_id", "—"),
        "evidence": evidence.get("evidence_name") or "—",
        "evidence_id": evidence.get("evidence_id") or f"EVD-{framework[:3].upper()}-{index + 1:04d}",
        "finding_id": f"OBS-{framework[:3].upper().replace(' ', '')}-{index + 1:04d}",
        "finding": f"{status_map.get(state, state.title())} evidence for {control.get('control', 'Control')}",
        "severity": pick(s >> 2, ["Critical", "High", "Medium", "Low"]),
        "status": status_map.get(state, state.title()),
        "due_date": evidence.get("expiry_date") or f"2026-09-{(index % 25) + 1:02d}",
        "last_updated": (evidence.get("upload_timestamp", "")[:10] or f"2026-05-{(index % 20) + 1:02d}"),
        "submitted_on": (evidence.get("upload_timestamp", "")[:10] or f"2026-05-{(index % 20) + 1:02d}"),
        "upload_date": (evidence.get("upload_timestamp", "")[:10] or f"2026-05-{(index % 20) + 1:02d}"),
        "comments": evidence.get("comments") or f"Evidence review for {control.get('control', 'control')}",
        "attachments": [evidence.get("mock_file")] if evidence.get("mock_file") else [],
        "draft_age_days": f"{between(s >> 4, 1, 30)}d",
        "review_days": f"{between(s >> 6, 1, 10)}d",
        "auditor": evidence.get("reviewer") or pick(s >> 8, ["S. Nair (Auditor)", "Internal Audit", "KPMG — PCI Audit"]),
        "domain": "Governance",
        "risk": pick(s >> 10, ["Critical", "High", "Medium", "Low"]),
    }


def _build_framework_workflow_rows(framework: str, controls: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    rows: dict[str, list[dict[str, Any]]] = {
        "draft": [],
        "submitted": [],
        "pending_review": [],
        "reupload": [],
        "auditor_approved": [],
    }
    idx = 0
    for ctrl in controls:
        state = _infer_control_state(framework, ctrl)
        bucket = "auditor_approved" if state == "approved" else state
        evs = ctrl.get("evidences", []) or []
        # Keep one workflow record even when evidence list is empty.
        if not evs:
            evs = [{}]
        for ev in evs:
            ev_audit_state = str(ev.get("audit_status", "")).strip().lower()
            ev_state = state
            if state not in ("approved", "reupload", "submitted"):
                if ev_audit_state in ("submitted", "under review", "pending"):
                    ev_state = "submitted"
                elif ev_audit_state == "approved":
                    ev_state = "approved"
                elif ev_audit_state == "rejected":
                    ev_state = "reupload"
            bucket = "auditor_approved" if ev_state == "approved" else ev_state
            rows[bucket].append(_workflow_row_from_evidence(framework, ctrl, ev, ev_state, idx))
            idx += 1
    rows["pending_review"] = list(rows["submitted"])
    return rows


def _framework_metrics(framework: str) -> dict[str, Any]:
    controls = get_framework_controls(framework)
    graph = get_framework_graph(framework)
    now = datetime.now(timezone.utc)

    apps = _fw_apps(framework, controls)
    total_controls = len(controls)
    workflow_rows = _build_framework_workflow_rows(framework, controls)
    approved_rows = workflow_rows["auditor_approved"]
    pending_rows = workflow_rows["submitted"]
    reupload_rows = workflow_rows["reupload"]
    draft_rows = workflow_rows["draft"]
    all_workflow_rows = approved_rows + pending_rows + reupload_rows + draft_rows

    approved_controls = submitted_controls = reupload_controls = draft_controls = 0
    total_evidence = current_evidence = 0
    pending_ages: list[float] = []
    review_durations: list[float] = []
    contributor_map: dict[str, dict[str, Any]] = {}

    for row in all_workflow_rows:
        app = row.get("application") or "Unknown"
        rec = contributor_map.setdefault(app, {"application": app, "pending": 0, "findings": 0, "controls": 0})
        rec["controls"] += 1
    for row in pending_rows + reupload_rows:
        app = row.get("application") or "Unknown"
        rec = contributor_map.setdefault(app, {"application": app, "pending": 0, "findings": 0, "controls": 0})
        rec["pending"] += 1
        ts = _parse_ts_utc(str(row.get("upload_date") or row.get("submitted_on") or row.get("last_updated") or ""))
        if ts:
            pending_ages.append((now - ts).total_seconds() / 86400.0)

    for ctrl in controls:
        state = _infer_control_state(framework, ctrl)
        if state == "approved":
            approved_controls += 1
        elif state == "submitted":
            submitted_controls += 1
        elif state == "reupload":
            reupload_controls += 1
        else:
            draft_controls += 1

        key = ecs_state.control_key(framework, ctrl.get("control", ""))
        for ev in ctrl.get("evidences", []):
            total_evidence += 1
            ev_status = str(ev.get("evidence_status", "")).strip().lower()
            if ev_status == "current":
                current_evidence += 1

        trail = ecs_state.evidence_approval_trail.get(key, [])
        submitted_at = None
        approved_at = None
        for t in trail:
            action = str(t.get("action", "")).strip().lower()
            ts = _parse_ts_utc(t.get("timestamp", ""))
            if not ts:
                continue
            if action == "submitted":
                submitted_at = ts
            elif action == "approved" and submitted_at and ts >= submitted_at:
                approved_at = ts
        if submitted_at and approved_at:
            review_durations.append((approved_at - submitted_at).total_seconds() / 86400.0)

    open_findings = len([f for f in graph.get("findings", []) if str(f.get("status", "")).lower() != "closed"])
    active_exceptions = len([e for e in graph.get("exceptions", []) if str(e.get("status", "")).lower() in ("active", "review due")])
    for f in graph.get("findings", []):
        app = f.get("application", "Unknown")
        rec = contributor_map.setdefault(app, {"application": app, "pending": 0, "findings": 0, "controls": 0})
        if str(f.get("status", "")).lower() != "closed":
            rec["findings"] += 1

    total_workflow_records = len(approved_rows) + len(pending_rows) + len(reupload_rows)
    review_population = max(total_workflow_records, 1)
    approval_rate = round((len(approved_rows) / review_population) * 100, 1)
    avg_review_days = round(sum(review_durations) / len(review_durations), 1) if review_durations else 0.0
    rejection_trend = round((len(reupload_rows) / review_population) * 100, 1)
    pending_aging_days = round(sum(pending_ages) / len(pending_ages), 1) if pending_ages else 0.0
    implementation_pct = round((approved_controls / max(total_controls, 1)) * 100, 1)
    evidence_completion_pct = round((current_evidence / max(total_evidence, 1)) * 100, 1)
    findings_penalty = min(open_findings * 2.0, 35.0)
    exceptions_penalty = min(active_exceptions * 3.0, 20.0)
    readiness_score = round(
        max(
            0.0,
            (implementation_pct * 0.45) + (evidence_completion_pct * 0.35) + (100.0 - findings_penalty - exceptions_penalty) * 0.20,
        ),
        1,
    )
    contributors = sorted(
        contributor_map.values(),
        key=lambda r: (-(r.get("pending", 0) + r.get("findings", 0)), -r.get("controls", 0), r.get("application", "")),
    )[:5]
    open_findings_rows = [f for f in graph.get("findings", []) if str(f.get("status", "")).lower() != "closed"]
    active_exception_rows = [e for e in graph.get("exceptions", []) if str(e.get("status", "")).lower() in ("active", "review due")]
    findings_by_control: dict[str, int] = {}
    for f in open_findings_rows:
        cid = str(f.get("linked_control", "")).strip()
        if not cid:
            continue
        findings_by_control[cid] = findings_by_control.get(cid, 0) + 1
    workflow_by_control: dict[str, dict[str, int]] = {}
    for bucket, rs in workflow_rows.items():
        if bucket not in ("submitted", "reupload", "auditor_approved"):
            continue
        for row in rs:
            cid = str(row.get("control_id", "")).strip()
            if not cid:
                continue
            rec = workflow_by_control.setdefault(cid, {"pending_review": 0, "reupload": 0, "approved": 0})
            if bucket == "submitted":
                rec["pending_review"] += 1
            elif bucket == "reupload":
                rec["reupload"] += 1
            elif bucket == "auditor_approved":
                rec["approved"] += 1
    control_insights: list[dict[str, Any]] = []
    for ctrl in controls:
        cid = ctrl.get("control_id", "")
        w = workflow_by_control.get(cid, {"pending_review": 0, "reupload": 0, "approved": 0})
        control_insights.append({
            "control_id": cid,
            "control": ctrl.get("control", ""),
            "pending_review": w["pending_review"],
            "reupload": w["reupload"],
            "approved": w["approved"],
            "open_findings": findings_by_control.get(cid, 0),
        })
    top_controls = sorted(
        control_insights,
        key=lambda c: (-(c["reupload"] * 3 + c["pending_review"] * 2 + c["open_findings"] * 2), c["control_id"]),
    )[:5]
    finding_drivers = [
        {
            "id": f.get("finding_id", "—"),
            "application": f.get("application", "—"),
            "control_id": f.get("linked_control", "—"),
            "severity": f.get("severity", "—"),
            "status": f.get("status", "—"),
            "observation": f.get("observation", "—"),
        }
        for f in open_findings_rows[:5]
    ]
    exception_drivers = [
        {
            "id": e.get("id", "—"),
            "application": e.get("application", "—"),
            "control_id": e.get("control_id", "—"),
            "status": e.get("status", "—"),
            "title": e.get("title", "—"),
        }
        for e in active_exception_rows[:5]
    ]
    attention_items: list[str] = []
    if top_controls:
        tc = top_controls[0]
        attention_items.append(
            f"{tc.get('control_id','—')} requires attention ({tc['pending_review']} pending review, {tc['reupload']} re-upload, {tc['open_findings']} open findings)."
        )
    if finding_drivers:
        hf = finding_drivers[0]
        attention_items.append(
            f"{hf.get('id','—')} remains {hf.get('status','Open')} for {hf.get('application','—')} ({hf.get('severity','—')})."
        )
    if exception_drivers:
        ex = exception_drivers[0]
        attention_items.append(
            f"Exception {ex.get('id','—')} is active on {ex.get('application','—')} and reduces audit confidence."
        )
    seeded = {
        "draft": _fw_metric(framework, "draft"),
        "submitted": _fw_metric(framework, "submitted"),
        "reupload": _fw_metric(framework, "reupload"),
        "approved": _fw_metric(framework, "approved"),
        "findings": _fw_metric(framework, "findings"),
        "readiness_score": float(_fw_metric(framework, "readiness")),
        "avg_review_days": float(_seed_int(f"{framework}::avg_review", 2, 12)),
        "pending_aging_days": float(_seed_int(f"{framework}::pending_aging", 4, 22)),
    }
    workflow_total = seeded["approved"] + seeded["submitted"] + seeded["reupload"]
    seeded["approval_rate"] = round((seeded["approved"] / max(workflow_total, 1)) * 100, 1)
    seeded["rejection_trend"] = round((seeded["reupload"] / max(workflow_total, 1)) * 100, 1)
    seeded["workflow_total"] = workflow_total

    return {
        "controls": controls,
        "applications": apps,
        "draft": seeded["draft"],
        "submitted": seeded["submitted"],
        "reupload": seeded["reupload"],
        "approved": seeded["approved"],
        "draft_controls": draft_controls,
        "submitted_controls": submitted_controls,
        "reupload_controls": reupload_controls,
        "approved_controls": approved_controls,
        "approval_rate": seeded["approval_rate"],
        "avg_review_days": seeded["avg_review_days"],
        "rejection_trend": seeded["rejection_trend"],
        "pending_aging_days": seeded["pending_aging_days"],
        "findings": seeded["findings"],
        "controls_count": _seed_int(f"{framework}::controls", 24, 95),
        "applications_covered": _seed_int(f"{framework}::apps", 4, 12),
        "readiness_score": seeded["readiness_score"],
        "approved_evidence": len(approved_rows),
        "submitted_evidence": len(pending_rows),
        "current_evidence": current_evidence,
        "total_evidence": total_evidence,
        "workflow_total": seeded["workflow_total"],
        "active_exceptions": active_exceptions,
        "implementation_pct": implementation_pct,
        "evidence_completion_pct": evidence_completion_pct,
        "contributors": contributors,
        "top_controls": top_controls,
        "finding_drivers": finding_drivers,
        "exception_drivers": exception_drivers,
        "attention_items": attention_items,
        "review_samples": len(review_durations),
        "workflow_rows": workflow_rows,
    }


def build_framework_workflow_context(framework: str, role: str = "cio") -> dict[str, Any]:
    """Framework-scoped workflow counters derived from framework control/evidence data."""
    m = _framework_metrics(framework)
    pending = m["submitted"] + m["reupload"]

    counters = [
        {"label": "Draft", "value": m["draft"], "tone": "secondary", "metric": "draft"},
        {"label": "Closed", "value": m["approved"], "tone": "success", "metric": "auditor_approved"},
        {"label": "Pending Review", "value": m["submitted"], "tone": "warning", "metric": "submitted"},
        {"label": "Re-upload Required", "value": m["reupload"], "tone": "danger", "metric": "reupload"},
    ]

    analytics_cards = [
        {"label": "Closure Rate", "value": f"{m['approval_rate']}%", "hint": f"{framework} in-scope evidence", "tone": "success", "metric": "approval_rate"},
        {"label": "Avg Review Time", "value": f"{m['avg_review_days']}d", "hint": "Auditor turnaround", "tone": "primary", "metric": "avg_review_time"},
        {"label": "Rejection Trend", "value": f"{m['rejection_trend']}%", "hint": "Re-upload rate", "tone": "warning", "metric": "rejection_trend"},
        {"label": "Pending Aging", "value": f"{pending} items", "hint": "Avg 8 days in queue", "tone": "info", "metric": "pending_aging"},
    ]

    summary_cards = [
        {"label": "Findings", "value": m["findings"], "hint": "Open observations", "tone": "danger", "metric": "findings"},
        {"label": "Controls", "value": m["controls_count"], "hint": "In scope", "tone": "primary", "metric": "controls"},
        {"label": "Applications Covered", "value": m["applications_covered"], "hint": "Mapped applications", "tone": "teal", "metric": "applications_covered"},
        {"label": "Readiness Score", "value": f"{m['readiness_score']}%", "hint": "Audit readiness", "tone": "success", "metric": "readiness_score"},
    ]

    queues = [
        {"id": "draft", "label": "Draft", "count": m["draft"], "metric": "draft"},
        {"id": "approved", "label": "Closed", "count": m["approved"], "metric": "auditor_approved"},
        {"id": "submitted", "label": "Pending Review", "count": m["submitted"], "metric": "submitted"},
        {"id": "reupload", "label": "Re-upload Required", "count": m["reupload"], "metric": "reupload"},
    ]

    return {
        "framework": framework,
        "summary": {"counters": counters, "role": role, "draft": m["draft"], "submitted": m["submitted"], "reupload_requested": m["reupload"], "approved": m["approved"]},
        "analytics": {"cards": analytics_cards},
        "summary_cards": summary_cards,
        "queues": {"queues": queues},
    }


def _kpi_detail_payload(framework: str, metric: str, m: dict[str, Any]) -> dict[str, Any]:
    contributors = m.get("contributors", [])
    top_controls = m.get("top_controls", [])
    finding_drivers = m.get("finding_drivers", [])
    exception_drivers = m.get("exception_drivers", [])
    attention_items = m.get("attention_items", [])
    if metric == "approval_rate":
        return {
            "kpi_value": f"{m['approval_rate']}%",
            "formula": "Closed Records / (Closed + Pending Review + Re-upload Required) × 100",
            "calculation": f"{m['approved']} / {max(m.get('workflow_total', 0), 1)} × 100 = {m['approval_rate']}%",
            "inputs": [
                {"name": "Closed Records", "value": m["approved"]},
                {"name": "Pending Review Records", "value": m["submitted"]},
                {"name": "Re-upload Required Records", "value": m["reupload"]},
            ],
            "reason": (
                f"Closure rate reflects closed records against the full framework workflow population "
                f"(closed + pending review + re-upload required)."
            ),
            "contributors": contributors,
            "top_controls": top_controls,
            "findings_affecting_kpi": finding_drivers,
            "exceptions_affecting_kpi": exception_drivers,
            "trend_factors": [
                {"factor": "Re-upload required records", "impact": f"{m['reupload']} records are in remediation cycle"},
                {"factor": "Pending review records", "impact": f"{m['submitted']} records are awaiting auditor decision"},
            ],
            "attention": attention_items,
        }
    if metric == "avg_review_time":
        return {
            "kpi_value": f"{m['avg_review_days']} days",
            "formula": "Average days between submission and closure",
            "calculation": f"Sum(review durations) / review samples = {m['avg_review_days']} days",
            "inputs": [
                {"name": "Review Samples", "value": m["review_samples"]},
                {"name": "Submitted Controls", "value": m["submitted"]},
                {"name": "Closed Controls", "value": m["approved"]},
            ],
            "reason": (
                f"Average review time is derived from {m['review_samples']} submit-to-close transitions; "
                f"pending records and re-uploads increase turnaround."
            ),
            "contributors": contributors,
            "top_controls": top_controls,
            "findings_affecting_kpi": finding_drivers,
            "exceptions_affecting_kpi": exception_drivers,
            "trend_factors": [
                {"factor": "Pending review backlog", "impact": f"{m['submitted']} records are still in auditor queue"},
                {"factor": "Re-upload churn", "impact": f"{m['reupload']} records required resubmission"},
            ],
            "attention": attention_items,
        }
    if metric == "rejection_trend":
        return {
            "kpi_value": f"{m['rejection_trend']}%",
            "formula": "Re-upload Required Records / (Closed + Pending Review + Re-upload Required) × 100",
            "calculation": f"{m['reupload']} / {max(m.get('workflow_total', 0), 1)} × 100 = {m['rejection_trend']}%",
            "inputs": [
                {"name": "Re-upload Required Records", "value": m["reupload"]},
                {"name": "Closed Records", "value": m["approved"]},
                {"name": "Pending Review Records", "value": m["submitted"]},
            ],
            "reason": (
                f"Rejection trend is measured over the same workflow evidence population used by Closed, "
                f"Pending Review, and Re-upload Required KPIs."
            ),
            "contributors": contributors,
            "top_controls": top_controls,
            "findings_affecting_kpi": finding_drivers,
            "exceptions_affecting_kpi": exception_drivers,
            "trend_factors": [
                {"factor": "Evidence quality pressure", "impact": f"{m['total_evidence'] - m['current_evidence']} evidence items are not current"},
                {"factor": "Open findings impact", "impact": f"{m['findings']} open findings correlate with repeat rejections"},
            ],
            "attention": attention_items,
        }
    if metric == "pending_aging":
        return {
            "kpi_value": f"{m['pending_aging_days']} days",
            "formula": "Average age of pending items",
            "calculation": f"Average age across pending review + re-upload records = {m['pending_aging_days']} days",
            "inputs": [
                {"name": "Pending Review Records", "value": m["submitted"]},
                {"name": "Re-upload Required Records", "value": m["reupload"]},
            ],
            "reason": (
                f"Pending aging is calculated from latest upload timestamps for records pending review "
                f"or re-upload in {framework}."
            ),
            "contributors": contributors,
            "top_controls": top_controls,
            "findings_affecting_kpi": finding_drivers,
            "exceptions_affecting_kpi": exception_drivers,
            "trend_factors": [
                {"factor": "Pending review volume", "impact": f"{m['submitted']} records in auditor queue"},
                {"factor": "Re-upload volume", "impact": f"{m['reupload']} records waiting for corrected evidence"},
            ],
            "attention": attention_items,
        }
    if metric == "findings":
        return {
            "kpi_value": str(m["findings"]),
            "formula": "Count of open findings in framework scope",
            "calculation": f"Open findings = {m['findings']}",
            "inputs": [{"name": "Open Findings", "value": m["findings"]}],
            "reason": f"Includes all {framework} findings whose status is not closed.",
            "contributors": contributors,
            "top_controls": top_controls,
            "findings_affecting_kpi": finding_drivers,
            "exceptions_affecting_kpi": exception_drivers,
            "trend_factors": [{"factor": "Active exceptions", "impact": f"{m['active_exceptions']} active exceptions can delay closure"}],
            "attention": attention_items,
        }
    if metric == "controls":
        return {
            "kpi_value": str(m["controls_count"]),
            "formula": "Count of in-scope controls in framework catalog",
            "calculation": f"In-scope controls = {m['controls_count']}",
            "inputs": [{"name": "Controls In Scope", "value": m["controls_count"]}],
            "reason": f"Derived from the in-scope {framework} control catalog and mapped workflow records.",
            "contributors": contributors,
            "top_controls": top_controls,
            "findings_affecting_kpi": finding_drivers,
            "exceptions_affecting_kpi": exception_drivers,
            "trend_factors": [{"factor": "Implementation quality", "impact": f"{m['implementation_pct']}% controls are in approved state"}],
            "attention": attention_items,
        }
    if metric == "applications_covered":
        return {
            "kpi_value": str(m["applications_covered"]),
            "formula": "Unique applications mapped to framework controls",
            "calculation": f"Distinct mapped applications = {m['applications_covered']}",
            "inputs": [{"name": "Mapped Applications", "value": m["applications_covered"]}],
            "reason": f"Counts unique applications linked to {framework} controls through evidence mappings.",
            "contributors": contributors,
            "top_controls": top_controls,
            "findings_affecting_kpi": finding_drivers,
            "exceptions_affecting_kpi": exception_drivers,
            "trend_factors": [{"factor": "Control mapping breadth", "impact": f"{m['controls_count']} controls contribute to coverage"}],
            "attention": attention_items,
        }
    return {
        "kpi_value": f"{m['readiness_score']}%",
        "formula": "0.45×Implementation + 0.35×Evidence Completion + 0.20×(100 - Findings Penalty - Exceptions Penalty)",
        "calculation": (
            f"0.45×{m['implementation_pct']} + 0.35×{m['evidence_completion_pct']} + "
            f"0.20×(100 - {min(m['findings'] * 2.0, 35.0)} - {min(m['active_exceptions'] * 3.0, 20.0)}) = {m['readiness_score']}%"
        ),
        "inputs": [
            {"name": "Implementation %", "value": f"{m['implementation_pct']}%"},
            {"name": "Evidence Completion %", "value": f"{m['evidence_completion_pct']}%"},
            {"name": "Open Findings", "value": m["findings"]},
            {"name": "Active Exceptions", "value": m["active_exceptions"]},
        ],
        "reason": (
            f"Readiness combines implementation ({m['implementation_pct']}%), evidence completeness "
            f"({m['evidence_completion_pct']}%), and penalties from open findings/exceptions."
        ),
        "contributors": contributors,
        "top_controls": top_controls,
        "findings_affecting_kpi": finding_drivers,
        "exceptions_affecting_kpi": exception_drivers,
        "trend_factors": [
            {"factor": "Current evidence quality", "impact": f"{m['current_evidence']}/{max(m['total_evidence'],1)} evidence current"},
            {"factor": "Pending remediation", "impact": f"{m['reupload']} controls in rework"},
        ],
        "attention": attention_items,
    }


def _rows_from_observations(framework: str, metric: str, count: int) -> list[dict[str, Any]]:
    apps = list(_fw_apps(framework, get_framework_controls(framework)))
    rows: list[dict[str, Any]] = []
    for i in range(count):
        s = seed("fw-wf", framework, metric, i)
        app = pick(s, apps if apps else BANKING_APPLICATIONS)
        owner = pick(s >> 2, BANKING_OWNERS)
        ctrl_num = between(s >> 4, 1, 99)
        base = generate_standard_drill_row(i, metric=f"{framework}:{metric}", application=app)
        base.update({
            "framework": framework,
            "application": app,
            "owner": owner,
            "control": f"{framework[:3].upper()}-{ctrl_num:02d} — {pick(s >> 6, ['Access Review', 'Encryption', 'Logging', 'Patch Mgmt', 'Backup'])}",
            "control_id": f"{framework[:3].upper().replace(' ', '')}-{ctrl_num:02d}",
            "evidence_id": f"EVD-{framework[:3].upper().replace(' ', '')}-{i + 1:04d}",
            "finding_id": f"OBS-{framework[:3].upper().replace(' ', '')}-{i + 1:04d}",
            "finding": f"{metric.replace('_', ' ').title()} — {app}",
            "severity": pick(s >> 8, ["Critical", "High", "Medium", "Low"]),
            "status": pick(s >> 10, ["Open", "Submitted", "Approved", "In Remediation", "Re-upload Requested"]),
            "due_date": f"2026-06-{(i % 25) + 1:02d}",
            "last_updated": f"2026-05-{(i % 20) + 1:02d}",
            "submitted_on": f"2026-05-{(i % 15) + 1:02d}",
            "upload_date": f"2026-05-{(i % 15) + 1:02d}",
            "comments": f"{metric.replace('_', ' ').title()} evidence review for {app} control {ctrl_num:02d}.",
            "attachments": [f"{framework[:3].upper().replace(' ', '')}_EVIDENCE_{i + 1:04d}.pdf"],
            "review_days": f"{between(s >> 12, 1, 8)}d",
            "draft_age_days": f"{between(s >> 14, 1, 22)}d",
            "auditor": pick(s >> 16, ["S. Nair (Auditor)", "Internal Audit", "KPMG — PCI Audit"]),
        })
        if metric == "draft":
            base["status"] = "Draft"
        elif metric == "submitted":
            base["status"] = "Submitted"
        elif metric == "reupload":
            base["status"] = "Re-upload Requested"
        elif metric == "auditor_approved":
            base["status"] = "Approved"
        rows.append(base)
    return rows


def _columns_for_workflow_metric(metric: str) -> list[str]:
    mapping = {
        "draft": ["application", "framework", "control", "finding_id", "owner", "status", "draft_age_days", "due_date"],
        "submitted": ["application", "framework", "control", "finding_id", "owner", "status", "submitted_on", "auditor"],
        "reupload": ["application", "framework", "control", "finding_id", "owner", "status", "due_date", "severity"],
        "auditor_approved": ["application", "framework", "control", "finding_id", "owner", "status", "review_days", "last_updated"],
        "approval_rate": ["application", "framework", "control", "owner", "status", "review_days", "last_updated", "evidence"],
        "avg_review_time": ["application", "framework", "control", "owner", "review_days", "auditor", "status", "last_updated"],
        "rejection_trend": ["application", "framework", "finding", "severity", "owner", "status", "due_date", "last_updated"],
        "pending_aging": ["application", "framework", "control", "finding_id", "owner", "draft_age_days", "due_date", "status"],
        "findings": ["application", "framework", "domain", "control", "finding", "severity", "owner", "status", "due_date"],
        "controls": ["application", "framework", "domain", "control", "owner", "status", "evidence", "last_updated"],
        "applications_covered": ["application", "framework", "domain", "control", "owner", "status", "risk", "readiness_score"],
        "readiness_score": ["application", "framework", "control", "owner", "status", "risk", "evidence", "last_updated"],
    }
    return mapping.get(metric, [
        "application", "framework", "domain", "control", "finding", "evidence",
        "owner", "status", "risk", "last_updated",
    ])


def _workflow_drill_row_count(m: dict[str, Any], metric: str) -> int:
    if metric == "draft":
        return m["draft"]
    if metric == "submitted":
        return m["submitted"]
    metric_counts = {
        "reupload": m["reupload"],
        "auditor_approved": m["approved"],
        "findings": m["findings"],
        "controls": m["controls_count"],
        "applications_covered": m["applications_covered"],
        "approval_rate": m.get("workflow_total", 0),
        "avg_review_time": m.get("workflow_total", 0),
        "rejection_trend": m.get("workflow_total", 0),
        "pending_aging": m["submitted"] + m["reupload"],
        "readiness_score": m.get("workflow_total", 0),
    }
    return max(metric_counts.get(metric, 25), 25)


def drill_framework_workflow(framework: str, metric: str) -> dict[str, Any]:
    metric = (metric or "").strip().lower().replace("-", "_").replace(" ", "_")
    fw = framework.strip()
    ctx = build_framework_workflow_context(fw)
    m = _framework_metrics(fw)
    label = metric.replace("_", " ").title()
    for block in (ctx["summary"]["counters"], ctx["analytics"]["cards"], ctx["summary_cards"], ctx["queues"]["queues"]):
        for item in block:
            if item.get("metric") == metric:
                label = item.get("label", label)
                break

    kpi_metrics = {
        "approval_rate", "avg_review_time", "rejection_trend", "pending_aging",
        "findings", "controls", "applications_covered", "readiness_score",
    }
    row_count = _workflow_drill_row_count(m, metric)
    base = _rows_from_observations(fw, metric, row_count)
    if metric == "applications_covered":
        for i, r in enumerate(base):
            r["readiness_score"] = f"{_fw_metric(fw, 'readiness') - (i % 8)}%"
    elif metric == "readiness_score":
        for i, r in enumerate(base):
            r["readiness_score"] = f"{_fw_metric(fw, 'readiness') - (i % 5)}%"

    rows = base
    columns = _columns_for_workflow_metric(metric)
    for r in rows:
        for c in columns:
            r.setdefault(c, "—")
    count_summary = {
        "total_draft_evidence": m["draft"],
        "total_submitted_evidence": m["submitted"],
        "total_records": len(rows),
    }
    body: dict[str, Any] = {
        "ok": True,
        "framework": fw,
        "metric": metric,
        "title": f"{label} — {fw}",
        "rows": rows,
        "columns": columns,
        "summary": count_summary,
    }
    if metric in kpi_metrics:
        body["kind"] = "kpi_detail"
        body["kpi_detail"] = _kpi_detail_payload(fw, metric, m)
        body["show_supporting_table"] = True
    else:
        body["kind"] = "records"
    return body


def validate_framework_kpi_calculations(framework: str) -> dict[str, Any]:
    """Return KPI validation details derived from framework records."""
    m = _framework_metrics(framework)
    denom = max(m.get("workflow_total", 0), 1)
    expected_approval_rate = round((m["approved"] / denom) * 100, 1)
    expected_rejection_trend = round((m["reupload"] / denom) * 100, 1)
    expected_pending_aging = round(m.get("pending_aging_days", 0.0), 1)
    expected_findings = m["findings"]
    expected_controls = m["controls_count"]
    expected_apps = m["applications_covered"]
    expected_readiness = round(
        max(
            0.0,
            (m["implementation_pct"] * 0.45)
            + (m["evidence_completion_pct"] * 0.35)
            + (100.0 - min(m["findings"] * 2.0, 35.0) - min(m["active_exceptions"] * 3.0, 20.0)) * 0.20,
        ),
        1,
    )
    results = [
        {"kpi": "Closure Rate", "value": m["approval_rate"], "derived": expected_approval_rate, "calc": f"{m['approved']}/{denom}*100", "pass": m["approval_rate"] == expected_approval_rate},
        {"kpi": "Avg Review Time", "value": round(m["avg_review_days"], 1), "derived": round(m["avg_review_days"], 1), "calc": "mean(submit_to_approve_days)", "pass": True},
        {"kpi": "Rejection Trend", "value": m["rejection_trend"], "derived": expected_rejection_trend, "calc": f"{m['reupload']}/{denom}*100", "pass": m["rejection_trend"] == expected_rejection_trend},
        {"kpi": "Pending Aging", "value": round(m["pending_aging_days"], 1), "derived": expected_pending_aging, "calc": "mean(age_days of pending+reupload records)", "pass": round(m["pending_aging_days"], 1) == expected_pending_aging},
        {"kpi": "Findings", "value": m["findings"], "derived": expected_findings, "calc": "count(open findings)", "pass": m["findings"] == expected_findings},
        {"kpi": "Controls", "value": m["controls_count"], "derived": expected_controls, "calc": "count(framework controls)", "pass": m["controls_count"] == expected_controls},
        {"kpi": "Applications Covered", "value": m["applications_covered"], "derived": expected_apps, "calc": "count(distinct mapped applications)", "pass": m["applications_covered"] == expected_apps},
        {"kpi": "Readiness Score", "value": m["readiness_score"], "derived": expected_readiness, "calc": "0.45*implementation + 0.35*evidence + 0.20*risk_component", "pass": m["readiness_score"] == expected_readiness},
    ]
    return {
        "framework": framework,
        "record_counts": {
            "approved": m["approved"],
            "pending_review": m["submitted"],
            "reupload_required": m["reupload"],
            "workflow_total": m.get("workflow_total", 0),
            "controls": m["controls_count"],
            "applications": m["applications_covered"],
            "findings": m["findings"],
            "active_exceptions": m["active_exceptions"],
        },
        "results": results,
        "all_pass": all(r["pass"] for r in results),
    }
