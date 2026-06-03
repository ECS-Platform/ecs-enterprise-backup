"""Reports module drilldowns — catalog, exports, and reporting health explainability."""

from __future__ import annotations

from typing import Any

from modules.executive_overview.engines.reports_analytics_engine import build_reports_overview


def _metric_trace(
    *,
    title: str,
    numerator: int,
    denominator: int,
    result: str,
    narrative: str,
    frameworks: list[str],
    applications: list[str],
) -> dict[str, Any]:
    return {
        "metric_name": title,
        "display_value": result,
        "calculation_formula": {
            "implemented_controls": numerator,
            "applicable_controls": denominator,
            "numerator_label": "Matching Records",
            "denominator_label": "Total in Scope",
            "formula_text": narrative.split(".")[0],
            "result": result,
            "narrative": narrative,
        },
        "contributing_applications": applications[:8],
        "contributing_frameworks": frameworks[:8],
        "justification": narrative,
    }


def drill_reports_kpi(metric: str, role: str = "cio", count: int = 0) -> dict[str, Any]:
    overview = build_reports_overview(role)
    m = (metric or "").lower().replace("-", "_").replace(" ", "_")
    counts = overview["counts"]

    if "available" in m:
        rows = [
            {
                "report_name": r["title"],
                "framework": r["framework"],
                "application": r["application"],
                "frequency": r["schedule"],
                "format": r["format"],
                "owner": r["owner"],
            }
            for r in overview["catalog"]
        ]
        trace = _metric_trace(
            title="Available Reports",
            numerator=len(rows),
            denominator=len(rows),
            result=str(len(rows)),
            narrative=f"Available Reports = count of report catalog entries ({len(rows)} definitions).",
            frameworks=sorted({r["framework"] for r in overview["catalog"]})[:8],
            applications=sorted({r["application"] for r in overview["catalog"]})[:8],
        )
        return {
            "ok": True,
            "title": "Available Reports — Report Catalog",
            "metric_trace": trace,
            "rows": rows,
            "columns": ["report_name", "framework", "application", "frequency", "format", "owner"],
            "detail": {"count": len(rows), "catalog_size": counts["available"]},
        }

    if "generated" in m and "pending" not in m:
        rows = overview["generated_records"]
        trace = _metric_trace(
            title="Generated Reports",
            numerator=len(rows),
            denominator=counts["available"],
            result=str(len(rows)),
            narrative=f"Generated Reports = {len(rows)} successful generation/download records in export history.",
            frameworks=sorted({r["framework"] for r in rows})[:8],
            applications=sorted({r["application"] for r in rows})[:8],
        )
        return {
            "ok": True,
            "title": "Generated Reports",
            "metric_trace": trace,
            "rows": rows,
            "columns": ["report_name", "generated_date", "generated_by", "file_size", "format", "framework", "application"],
            "detail": {"count": len(rows)},
        }

    if "scheduled" in m:
        rows = overview["scheduled_records"]
        trace = _metric_trace(
            title="Scheduled Reports",
            numerator=len(rows),
            denominator=counts["available"],
            result=str(len(rows)),
            narrative=f"Scheduled Reports = {len(rows)} catalog entries with recurring export schedules (non On Demand).",
            frameworks=sorted({r["framework"] for r in rows})[:8],
            applications=sorted({r["application"] for r in rows})[:8],
        )
        return {
            "ok": True,
            "title": "Scheduled Reports",
            "metric_trace": trace,
            "rows": rows,
            "columns": ["report_name", "next_run", "schedule_frequency", "owner", "status", "framework"],
            "detail": {"count": len(rows)},
        }

    if "pending" in m:
        rows = overview["pending_records"]
        trace = _metric_trace(
            title="Pending Reports",
            numerator=len(rows),
            denominator=counts["generated"] + len(rows),
            result=str(len(rows)),
            narrative=f"Pending Reports = {len(rows)} queued generation requests awaiting export completion.",
            frameworks=sorted({r["framework"] for r in rows})[:8],
            applications=sorted({r["application"] for r in rows})[:8],
        )
        return {
            "ok": True,
            "title": "Pending Reports",
            "metric_trace": trace,
            "rows": rows,
            "columns": ["report_name", "requestor", "queue_position", "eta", "framework", "application", "format"],
            "detail": {"count": len(rows)},
        }

    if "failed" in m:
        rows = overview["failed_records"]
        trace = _metric_trace(
            title="Failed Reports",
            numerator=len(rows),
            denominator=counts["generated"] + len(rows),
            result=str(len(rows)),
            narrative=f"Failed Reports = {len(rows)} export runs that terminated with errors.",
            frameworks=sorted({r["framework"] for r in rows})[:8],
            applications=sorted({r["application"] for r in rows})[:8],
        )
        return {
            "ok": True,
            "title": "Failed Reports",
            "metric_trace": trace,
            "rows": rows,
            "columns": ["report_name", "failed_at", "error", "requestor", "framework", "application", "format"],
            "detail": {"count": len(rows)},
        }

    if "success" in m:
        gen = counts["generated"]
        pend = counts["pending"]
        fail = counts["failed"]
        total = gen + pend + fail
        rate = round(gen * 100 / max(total, 1), 1)
        trace = _metric_trace(
            title="Export Success Rate",
            numerator=gen,
            denominator=total,
            result=f"{rate}%",
            narrative=f"Success Rate = {gen} generated ÷ ({gen} + {pend} pending + {fail} failed) × 100 = {rate}%.",
            frameworks=sorted({r["framework"] for r in overview["catalog"]})[:6],
            applications=sorted({r["application"] for r in overview["catalog"]})[:6],
        )
        return {
            "ok": True,
            "title": "Export Success Rate",
            "metric_trace": trace,
            "rows": overview["generated_records"][:25],
            "columns": ["report_name", "generated_date", "generated_by", "format", "framework", "status"],
            "detail": {"generated": gen, "pending": pend, "failed": fail, "success_rate_pct": rate},
        }

    return drill_reports_kpi("available_reports", role, count)


def drill_reports_chart(chart: str, element: str, role: str = "cio", count: int = 0) -> dict[str, Any]:
    overview = build_reports_overview(role)
    chart_l = (chart or "").lower()
    if "distribution" in chart_l or element.upper() in ("PDF", "EXCEL", "ZIP"):
        fmt = element.replace(" Evidence Packs", "").upper()
        rows = [r for r in overview["catalog"] if fmt in (r.get("format", "").upper(), "PDF") or "evidence" in r["title"].lower()]
        body = drill_reports_kpi("available_reports", role, count)
        body["title"] = f"Export Distribution — {element}"
        body["rows"] = [
            {"report_name": r["title"], "format": r["format"], "framework": r["framework"], "application": r["application"], "owner": r["owner"]}
            for r in (rows or overview["catalog"][:15])
        ]
        return body
    if "generation" in chart_l or "trend" in chart_l:
        body = drill_reports_kpi("generated_reports", role, count)
        body["title"] = f"Report Generation — {element}"
        return body
    if "download" in chart_l:
        body = drill_reports_kpi("generated_reports", role, count)
        body["title"] = f"Top Downloaded — {element}"
        body["rows"] = overview["top_downloaded"]
        body["columns"] = ["report_name", "downloads", "format", "framework", "last_download"]
        return body
    return drill_reports_kpi(element or chart, role, count)
