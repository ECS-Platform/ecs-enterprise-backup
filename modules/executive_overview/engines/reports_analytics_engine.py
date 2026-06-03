"""Executive Reports analytics — consistent catalog, export, and overview metrics."""

from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import Any

from app import ecs_state
from modules.executive_overview.engines.reporting_module import (
    _REPORT_DEFS,
    list_report_history,
    list_report_observation_rows,
    list_reports,
    list_scheduled_reports,
)
from modules.governance.engines.governance_mock_data import OWNERS

ANCHOR = date(2026, 5, 29)


def _seed(key: str, lo: int, hi: int) -> int:
    h = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)
    return lo + (h % (hi - lo + 1))


def _file_size_kb(report_id: str) -> str:
    kb = _seed(report_id + "size", 420, 8900)
    if kb >= 1024:
        return f"{kb / 1024:.1f} MB"
    return f"{kb} KB"


def _next_run(schedule: str, report_id: str) -> str:
    offsets = {"Weekly": 2, "Monthly": 7, "Quarterly": 21, "On Demand": 0}
    days = offsets.get(schedule, 5)
    if days == 0:
        return "—"
    d = ANCHOR + timedelta(days=days + _seed(report_id, 0, 3))
    return d.strftime("%d-%b-%Y %H:%M UTC")


def list_report_catalog() -> list[dict[str, Any]]:
    """Full audit-ready report catalog — one row per catalog definition."""
    return list_reports()


def list_generated_report_records() -> list[dict[str, Any]]:
    """Reports successfully generated or downloaded."""
    rows: list[dict[str, Any]] = []
    for r in list_reports():
        if r["status"] not in ("Generated", "Downloaded"):
            continue
        rows.append({
            "report_name": r["title"],
            "report_id": r["id"],
            "generated_date": r["generated_at"],
            "generated_by": r["owner"],
            "file_size": _file_size_kb(r["id"]),
            "format": r["format"],
            "framework": r["framework"],
            "application": r["application"],
            "download_path": f"/mvp/reports/download/{r['id']}?format=pdf",
            "status": r["status"],
        })
    for h in list_report_history():
        if h.get("source") == "dynamic_export" and h.get("status") in ("Generated", "Downloaded"):
            rows.append({
                "report_name": h.get("title", h.get("id", "Export")),
                "report_id": h.get("id", h.get("run_id", "")),
                "generated_date": h.get("generated_at", "2026-05-24 10:00 UTC"),
                "generated_by": h.get("downloaded_by", h.get("generated_by", "System")),
                "file_size": _file_size_kb(str(h.get("id", "exp"))),
                "format": h.get("format", "Excel"),
                "framework": h.get("framework", "Enterprise-wide"),
                "application": h.get("application", "All Applications"),
                "download_path": h.get("download_path", ""),
                "status": h.get("status", "Generated"),
            })
    return rows


def list_scheduled_export_records() -> list[dict[str, Any]]:
    """Scheduled report exports with next run."""
    rows = []
    for r in list_scheduled_reports():
        rows.append({
            "report_name": r["title"],
            "report_id": r["id"],
            "next_run": _next_run(r["schedule"], r["id"]),
            "schedule_frequency": r["schedule"],
            "owner": r["owner"],
            "status": "Active" if r["status"] != "Failed" else "Paused",
            "framework": r["framework"],
            "application": r["application"],
            "format": r["format"],
        })
    return rows


def list_pending_export_records() -> list[dict[str, Any]]:
    """Queued / pending report generation requests."""
    pending = [r for r in list_reports() if r["status"] in ("Pending", "Scheduled")]
    rows = []
    for i, r in enumerate(pending):
        eta_hours = 1 + _seed(r["id"] + "eta", 0, 8)
        rows.append({
            "report_name": r["title"],
            "report_id": r["id"],
            "requestor": r["owner"],
            "queue_position": i + 1,
            "eta": f"{eta_hours}h",
            "framework": r["framework"],
            "application": r["application"],
            "format": r["format"],
            "status": r["status"],
        })
    return rows


def list_failed_export_records() -> list[dict[str, Any]]:
    """Failed export runs."""
    rows = []
    for i, (rid, title, fmt, fw, app, *_rest) in enumerate(_REPORT_DEFS):
        if _seed(rid + "fail", 0, 12) != 0:
            continue
        rows.append({
            "report_name": title,
            "report_id": rid,
            "failed_at": f"2026-05-{(i % 18) + 1:02d} {14 + (i % 6):02d}:22 UTC",
            "error": pick_error(rid),
            "requestor": OWNERS[i % len(OWNERS)],
            "framework": fw,
            "application": app,
            "format": fmt,
        })
    return rows


def pick_error(report_id: str) -> str:
    errors = [
        "Template merge timeout — retry scheduled",
        "Evidence repository connector unavailable",
        "Insufficient scope permissions for application filter",
        "PDF renderer exceeded memory threshold",
    ]
    return errors[_seed(report_id + "err", 0, len(errors) - 1)]


def export_format_distribution(catalog: list[dict] | None = None) -> dict[str, int]:
    catalog = catalog or list_report_catalog()
    dist = {"PDF": 0, "Excel": 0, "ZIP Evidence Packs": 0}
    for r in catalog:
        fmt = (r.get("format") or "PDF").upper()
        if fmt in ("PDF", "PPT"):
            dist["PDF"] += 1
        elif fmt == "EXCEL":
            dist["Excel"] += 1
        if "evidence" in r["title"].lower() or "pack" in r["title"].lower():
            dist["ZIP Evidence Packs"] += 1
    dist["ZIP Evidence Packs"] = max(dist["ZIP Evidence Packs"], _seed("zip-packs", 4, 9))
    return dist


def report_generation_trend() -> dict[str, list[dict[str, Any]]]:
    generated = list_generated_report_records()
    base = max(len(generated), 12)
    daily = []
    for i in range(14):
        lbl = f"D{i + 1}"
        daily.append({"label": lbl, "value": max(1, _seed(f"rpt-d-{lbl}", 2, 8) + (base // 20))})
    weekly = [{"label": f"W{i}", "value": max(3, _seed(f"rpt-w-{i}", 8, 24))} for i in range(1, 9)]
    monthly = [
        {"label": "Jan", "value": 18}, {"label": "Feb", "value": 22},
        {"label": "Mar", "value": 26}, {"label": "Apr", "value": 31},
        {"label": "May", "value": len(generated)},
    ]
    return {"daily": daily, "weekly": weekly, "monthly": monthly}


def top_downloaded_reports(limit: int = 8) -> list[dict[str, Any]]:
    hist = list_report_history()
    scored = []
    for h in hist:
        downloads = _seed(h.get("id", "") + "dl", 3, 48)
        scored.append({
            "report_name": h.get("title", h.get("id", "")),
            "downloads": downloads,
            "format": h.get("format", "PDF"),
            "framework": h.get("framework", "Enterprise-wide"),
            "last_download": h.get("generated_at", "2026-05-20"),
        })
    scored.sort(key=lambda x: -x["downloads"])
    return scored[:limit]


def recent_export_activity(limit: int = 12) -> list[dict[str, Any]]:
    rows = []
    for h in list_report_history()[:limit]:
        rows.append({
            "report_name": h.get("title", h.get("id", "")),
            "action": "Downloaded" if h.get("status") == "Downloaded" else "Generated",
            "actor": h.get("downloaded_by", h.get("generated_by", "System")),
            "timestamp": h.get("generated_at", "2026-05-24 09:00 UTC"),
            "format": h.get("format", "PDF"),
            "framework": h.get("framework", "Enterprise-wide"),
            "status": h.get("status", "Generated"),
        })
    for exp in ecs_state.export_history[:6]:
        rows.insert(0, {
            "report_name": exp.get("title", "Gap Analysis Export"),
            "action": "Exported",
            "actor": exp.get("generated_by", "Compliance Officer"),
            "timestamp": exp.get("timestamp", "2026-05-24 11:00 UTC"),
            "format": exp.get("format", "Excel"),
            "framework": exp.get("framework", "Enterprise-wide"),
            "status": exp.get("status", "Generated"),
        })
    return rows[:limit]


def upcoming_scheduled_exports(limit: int = 8) -> list[dict[str, Any]]:
    sched = list_scheduled_export_records()
    sched.sort(key=lambda x: x["next_run"])
    return sched[:limit]


def build_reporting_health_kpis() -> list[dict[str, Any]]:
    catalog = list_report_catalog()
    generated = list_generated_report_records()
    scheduled = list_scheduled_export_records()
    pending = list_pending_export_records()
    failed = list_failed_export_records()

    total_attempts = len(generated) + len(failed) + len(pending)
    success_rate = round(len(generated) * 100 / max(total_attempts, 1), 1)

    return [
        {
            "label": "Available Reports",
            "value": len(catalog),
            "tone": "primary",
            "drill": "available_reports",
            "tooltip": "Audit-ready report definitions in the export catalog.",
        },
        {
            "label": "Generated Reports",
            "value": len(generated),
            "tone": "success",
            "drill": "generated_reports",
            "tooltip": "Successfully generated or downloaded report files.",
        },
        {
            "label": "Scheduled Reports",
            "value": len(scheduled),
            "tone": "info",
            "drill": "scheduled_reports",
            "tooltip": "Active recurring export schedules.",
        },
        {
            "label": "Pending Reports",
            "value": len(pending),
            "tone": "warning",
            "drill": "pending_reports",
            "tooltip": "Reports queued for generation.",
        },
        {
            "label": "Failed Reports",
            "value": len(failed),
            "tone": "danger",
            "drill": "failed_reports",
            "tooltip": "Export runs that did not complete successfully.",
        },
        {
            "label": "Success Rate",
            "value": f"{success_rate}%",
            "tone": "success",
            "drill": "success_rate",
            "tooltip": "Generated ÷ (Generated + Pending + Failed) in the current window.",
        },
    ]


def build_reports_overview(role: str = "cio") -> dict[str, Any]:
    catalog = list_report_catalog()
    generated = list_generated_report_records()
    scheduled = list_scheduled_export_records()
    pending = list_pending_export_records()
    failed = list_failed_export_records()
    kpis = build_reporting_health_kpis()

    return {
        "catalog": catalog,
        "generated_records": generated,
        "scheduled_records": scheduled,
        "pending_records": pending,
        "failed_records": failed,
        "kpis": kpis,
        "export_distribution": export_format_distribution(catalog),
        "generation_trend": report_generation_trend(),
        "top_downloaded": top_downloaded_reports(),
        "recent_activity": recent_export_activity(),
        "upcoming_scheduled": upcoming_scheduled_exports(),
        "observation_rows": list_report_observation_rows(role),
        "history_rows": list_report_history(),
        "counts": {
            "available": len(catalog),
            "generated": len(generated),
            "scheduled": len(scheduled),
            "pending": len(pending),
            "failed": len(failed),
        },
    }
