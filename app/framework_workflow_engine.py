"""Framework-scoped evidence workflow metrics and drill datasets."""

from __future__ import annotations

import hashlib
from typing import Any

from app.demo_data_standards import BANKING_APPLICATIONS, BANKING_OWNERS, ensure_drill_rows, generate_standard_drill_row, pick, seed, between
from app.framework_catalog import get_framework_controls

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


def build_framework_workflow_context(framework: str, role: str = "cio") -> dict[str, Any]:
    """Framework-scoped workflow counters — unique per framework."""
    controls = get_framework_controls(framework)
    apps = _fw_apps(framework, controls)
    draft = _fw_metric(framework, "draft")
    submitted = _fw_metric(framework, "submitted")
    reupload = _fw_metric(framework, "reupload")
    approved = _fw_metric(framework, "approved")
    findings = _fw_metric(framework, "findings")
    readiness = _fw_metric(framework, "readiness")
    total_reviewed = max(approved + reupload, 1)
    approval_rate = round(approved / total_reviewed * 100, 1)
    avg_review = round(1.5 + (_seed_int(f"{framework}::review", 0, 100) % 40) / 10, 1)
    rejection_rate = round(reupload / total_reviewed * 100, 1)
    pending = draft + submitted

    is_auditor = role == "auditor"
    counters = (
        [
            {"label": "Pending Review", "value": submitted, "tone": "warning", "metric": "submitted"},
            {"label": "Approved", "value": approved, "tone": "success", "metric": "auditor_approved"},
            {"label": "Rejected", "value": reupload, "tone": "danger", "metric": "reupload"},
        ]
        if is_auditor
        else [
            {"label": "Draft", "value": draft, "tone": "secondary", "metric": "draft"},
            {"label": "Submitted", "value": submitted, "tone": "warning", "metric": "submitted"},
            {"label": "Re-upload Req", "value": reupload, "tone": "danger", "metric": "reupload"},
        ]
    )

    analytics_cards = [
        {"label": "Approval Rate", "value": f"{approval_rate}%", "hint": f"{framework} in-scope evidence", "tone": "success", "metric": "approval_rate"},
        {"label": "Avg Review Time", "value": f"{avg_review}d", "hint": "Auditor turnaround", "tone": "primary", "metric": "avg_review_time"},
        {"label": "Rejection Trend", "value": f"{rejection_rate}%", "hint": "Re-upload rate", "tone": "warning", "metric": "rejection_trend"},
        {"label": "Pending Aging", "value": f"{pending} items", "hint": "Avg 8 days in queue", "tone": "info", "metric": "pending_aging"},
    ]

    summary_cards = [
        {"label": "Findings", "value": findings, "hint": "Open observations", "tone": "danger", "metric": "findings"},
        {"label": "Controls", "value": len(controls), "hint": "In scope", "tone": "primary", "metric": "controls"},
        {"label": "Applications Covered", "value": len(apps), "hint": "Mapped applications", "tone": "teal", "metric": "applications_covered"},
        {"label": "Readiness Score", "value": f"{readiness}%", "hint": "Audit readiness", "tone": "success", "metric": "readiness_score"},
    ]

    queues = [
        {"id": "draft", "label": "Draft Evidence", "count": draft, "metric": "draft"},
        {"id": "submitted", "label": "Submitted Evidence", "count": submitted, "metric": "submitted"},
        {"id": "reupload", "label": "Re-upload Requests", "count": reupload, "metric": "reupload"},
        {"id": "approved", "label": "Auditor Approved", "count": approved, "metric": "auditor_approved"},
    ]

    return {
        "framework": framework,
        "summary": {"counters": counters, "role": role, "draft": draft, "submitted": submitted, "reupload_requested": reupload, "approved": approved},
        "analytics": {"cards": analytics_cards},
        "summary_cards": summary_cards,
        "queues": {"queues": queues},
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
            "finding_id": f"OBS-{framework[:3].upper().replace(' ', '')}-{i + 1:04d}",
            "finding": f"{metric.replace('_', ' ').title()} — {app}",
            "severity": pick(s >> 8, ["Critical", "High", "Medium", "Low"]),
            "status": pick(s >> 10, ["Open", "Submitted", "Approved", "In Remediation", "Re-upload Requested"]),
            "due_date": f"2026-06-{(i % 25) + 1:02d}",
            "last_updated": f"2026-05-{(i % 20) + 1:02d}",
            "submitted_on": f"2026-05-{(i % 15) + 1:02d}",
            "review_days": f"{between(s >> 12, 1, 8)}d",
            "draft_age_days": f"{between(s >> 14, 1, 22)}d",
            "auditor": pick(s >> 16, ["S. Nair (Auditor)", "Internal Audit", "KPMG — PCI Audit"]),
        })
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


def drill_framework_workflow(framework: str, metric: str) -> dict[str, Any]:
    metric = (metric or "").strip().lower().replace("-", "_").replace(" ", "_")
    fw = framework.strip()
    ctx = build_framework_workflow_context(fw)
    label = metric.replace("_", " ").title()
    for block in (ctx["summary"]["counters"], ctx["analytics"]["cards"], ctx["summary_cards"], ctx["queues"]["queues"]):
        for item in block:
            if item.get("metric") == metric:
                label = item.get("label", label)
                break

    base = _rows_from_observations(fw, metric, 12)
    if metric == "applications_covered":
        for i, r in enumerate(base):
            r["readiness_score"] = f"{_fw_metric(fw, 'readiness') - (i % 8)}%"
    elif metric == "readiness_score":
        for i, r in enumerate(base):
            r["readiness_score"] = f"{_fw_metric(fw, 'readiness') - (i % 5)}%"

    rows = ensure_drill_rows(base, 25, metric=f"{fw}:wf:{metric}")
    columns = _columns_for_workflow_metric(metric)
    for r in rows:
        for c in columns:
            r.setdefault(c, "—")
    return {
        "ok": True,
        "framework": fw,
        "metric": metric,
        "title": f"{label} — {fw}",
        "rows": rows,
        "columns": columns,
    }
