"""Executive reporting center — dynamic filter-aware audit packs."""

from __future__ import annotations

import hashlib

from app import ecs_state
from app.analytics_module import enterprise_dashboard
from app.ecs_state import BANKING_APPLICATIONS
from app.framework_catalog import FRAMEWORK_CATALOG
from app.governance_mock_data import OWNERS

FRAMEWORKS = list(FRAMEWORK_CATALOG.keys())
APPS = BANKING_APPLICATIONS + ["Wealth Portal"]

_REPORT_DEFS = [
    ("pci-audit-pack", "PCI DSS Executive Audit Pack", "PDF", "PCI DSS", "Net Banking", "High", "Audit", "Weekly"),
    ("pci-mobile", "PCI DSS — Mobile Banking CDE Report", "PDF", "PCI DSS", "Mobile Banking", "High", "Audit", "Monthly"),
    ("appsec-sast", "AppSec SAST / DAST Summary", "Excel", "AppSec", "Mobile Banking", "High", "Security", "Weekly"),
    ("vapt-external", "VAPT External Pen Test Closure Report", "PDF", "VAPT", "Net Banking", "Critical", "Security", "Quarterly"),
    ("dpsc-upi", "DPSC UPI Channel Compliance Pack", "PDF", "DPSC", "UPI", "High", "Regulatory", "Monthly"),
    ("csite-soc", "CSITE SOC & SIEM Governance Report", "PDF", "CSITE", "All Applications", "Medium", "Cyber", "Monthly"),
    ("itpp-dr", "ITPP DR Readiness & Drill Summary", "Excel", "ITPP", "Treasury", "High", "Operations", "Quarterly"),
    ("os-baseline", "OS Baselining Hardening Export", "Excel", "OS Baselining", "Net Banking", "Medium", "Infrastructure", "Monthly"),
    ("db-baseline", "DB Baselining TDE Attestation Pack", "PDF", "DB Baselining", "Loan System", "High", "Infrastructure", "Monthly"),
    ("nginx-tls", "Nginx TLS / WAF Configuration Report", "PDF", "Nginx Baselining", "Mobile Banking", "Medium", "Infrastructure", "Monthly"),
    ("enterprise-cio", "CIO Enterprise Governance Pack", "PPT", "Enterprise-wide", "All Applications", "High", "Executive", "Monthly"),
    ("pan-india", "Pan India Regional Compliance Report", "PDF", "Enterprise-wide", "All Applications", "Medium", "Executive", "Monthly"),
    ("rbi-cyber", "RBI Cyber Security Compliance Summary", "PDF", "Enterprise-wide", "All Applications", "High", "Regulatory", "Quarterly"),
    ("framework-coverage", "Cross-Framework Coverage Summary", "Excel", "Enterprise-wide", "All Applications", "Low", "Governance", "On-demand"),
    ("exceptions-td", "Active TD Exceptions Register", "Excel", "PCI DSS", "Payments", "High", "Compliance", "Weekly"),
    ("stale-evidence", "Stale Evidence Aging Report", "Excel", "Enterprise-wide", "All Applications", "Medium", "Audit", "Weekly"),
    ("audit-readiness", "Audit Readiness Scorecard", "PDF", "Enterprise-wide", "All Applications", "High", "Audit", "Weekly"),
    ("remediation-velocity", "Remediation Velocity & SLA Report", "Excel", "VAPT", "Mobile Banking", "High", "Operations", "Monthly"),
    ("integration-health", "Integration Connector Health Export", "Excel", "ITPP", "All Applications", "Medium", "Operations", "Weekly"),
    ("reuse-mapping", "Evidence Reuse Mapping Report", "Excel", "Enterprise-wide", "All Applications", "Low", "Governance", "On-demand"),
    ("loan-pci", "Loan System PCI Scope Report", "PDF", "PCI DSS", "Loan System", "Medium", "Audit", "Quarterly"),
    ("wealth-appsec", "Wealth Portal AppSec Pack", "PDF", "AppSec", "Wealth Portal", "Medium", "Security", "Monthly"),
    ("treasury-itpp", "Treasury Operational Resilience Pack", "PDF", "ITPP", "Treasury", "High", "Operations", "Quarterly"),
    ("payments-dpsc", "Payments DPSC Self-Assessment Export", "PDF", "DPSC", "Payments", "Critical", "Regulatory", "Monthly"),
    ("evidence-approval-summary", "Evidence Approval Summary", "PDF", "Enterprise-wide", "All Applications", "High", "Governance", "Weekly"),
    ("rejection-analysis", "Rejection Analysis Report", "Excel", "Enterprise-wide", "All Applications", "High", "Audit", "Weekly"),
    ("framework-validation", "Framework Validation Report", "PDF", "PCI DSS", "Net Banking", "High", "Audit", "Monthly"),
    ("exception-governance", "Exception Governance Report", "PDF", "Enterprise-wide", "All Applications", "High", "Compliance", "Weekly"),
    ("td-risk-exposure", "TD Risk Exposure Report", "Excel", "VAPT", "Mobile Banking", "Critical", "Compliance", "Monthly"),
    ("evidence-approval-ppt", "Evidence Approval Executive Brief", "PPT", "Enterprise-wide", "All Applications", "High", "Executive", "Monthly"),
]

_STATUSES = ["Generated", "Generated", "Generated", "Pending", "Scheduled", "Generated"]


def _seed(key: str, lo: int, hi: int) -> int:
    h = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)
    return lo + (h % (hi - lo + 1))


def list_reports() -> list[dict]:
    rows = []
    for i, (rid, title, fmt, fw, app, risk, category, schedule) in enumerate(_REPORT_DEFS):
        owner = OWNERS[i % len(OWNERS)]
        status = _STATUSES[i % len(_STATUSES)]
        if schedule == "On-demand":
            status = "Generated" if i % 3 else "Pending"
        rows.append({
            "id": rid,
            "title": title,
            "description": f"Executive {category.lower()} report for {app} — {fw} scope.",
            "format": fmt,
            "frameworks": [fw] if fw != "Enterprise-wide" else FRAMEWORKS[:4],
            "framework": fw,
            "application": app,
            "owner": owner,
            "risk": risk,
            "category": category,
            "schedule": schedule.replace("On-demand", "On Demand"),
            "status": status,
            "generated_at": f"2026-05-{(i % 20) + 1:02d} {8 + (i % 10):02d}:00 UTC",
            "export_formats": ["PDF", "Excel", "PPT"] if fmt == "PPT" else [fmt, "PDF"],
        })
    return rows


def list_scheduled_reports() -> list[dict]:
    return [r for r in list_reports() if r["schedule"] != "On Demand"]


def list_report_observation_rows(role: str = "owner") -> list[dict]:
    """Observation/evidence detail rows for report preview and export."""
    from app.exception_state_engine import get_all_exceptions
    from app.role_filter_scope import apply_role_scope

    rows: list[dict] = []
    for i, exc in enumerate(get_all_exceptions(role)[:40]):
        rows.append({
            "observation_id": exc.get("observation_id", f"OBS-{i:04d}"),
            "observation_title": exc.get("observation_title", exc.get("control", "")),
            "framework": exc.get("framework", "PCI DSS"),
            "application": exc.get("application", "Net Banking"),
            "evidence_id": f"EVD-{exc.get('exception_id', i).replace('EXC-', '')}",
            "evidence_type": "Compensating Control Attestation",
            "evidence_status": exc.get("status", "Pending Review"),
            "owner": exc.get("owner", OWNERS[i % len(OWNERS)]),
            "generated_date": exc.get("submitted_at", "2026-05-20 10:00 UTC"),
        })
    stats = ecs_state.build_evidence_analytics()
    for j, fw in enumerate(stats.get("framework_stats", [])[:12]):
        for k in range(min(2, fw.get("pending", 0) + 1)):
            app = APPS[(j + k) % len(APPS)]
            rows.append({
                "observation_id": f"OBS-{fw['name'][:4].upper().replace(' ', '')}-{j:03d}{k}",
                "observation_title": f"{fw['name']} control evidence gap",
                "framework": fw["name"],
                "application": app,
                "evidence_id": f"EVD-{fw['name'][:6].replace(' ', '')}-{j}{k}",
                "evidence_type": "Policy / Config Export",
                "evidence_status": "Submitted" if k == 0 else "Approved",
                "owner": OWNERS[(j + k) % len(OWNERS)],
                "generated_date": f"2026-05-{(j + k) % 20 + 1:02d} 09:00 UTC",
            })
    return apply_role_scope(rows, role)


def list_report_history() -> list[dict]:
    from app import ecs_state

    hist = []
    for r in list_reports():
        hist.append({
            **r,
            "run_id": f"RUN-{r['id'][:6].upper()}-{_seed(r['id'], 100, 999)}",
            "status": "Downloaded" if r["status"] == "Generated" else r["status"],
            "downloaded_by": r["owner"],
            "source": "catalog",
        })
    for exp in ecs_state.export_history[:25]:
        hist.insert(0, {
            "id": exp.get("export_id"),
            "title": exp.get("title", "Gap Analysis Export"),
            "format": exp.get("format", "Excel"),
            "framework": exp.get("framework", "Enterprise-wide"),
            "application": exp.get("application", "All Applications"),
            "generated_at": exp.get("timestamp"),
            "status": exp.get("status", "Generated"),
            "downloaded_by": exp.get("generated_by"),
            "run_id": exp.get("export_id"),
            "download_path": exp.get("download_path"),
            "filters_used": exp.get("filters_used", {}),
            "source": "dynamic_export",
            "category": exp.get("category", "Gap Analysis"),
        })
    return hist


def _report_filename(report: dict | None, report_id: str, fmt: str) -> str:
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y_%m_%d")
    fw = (report or {}).get("framework", "Enterprise").replace(" ", "_")
    app = (report or {}).get("application", "AllApps").replace(" ", "")
    if app == "AllApplications":
        app = "AllApps"
    ext = {"pdf": "pdf", "excel": "xlsx", "csv": "csv"}.get(fmt, "txt")
    slug = report_id.replace("-", "_")[:24]
    return f"{fw}_{app}_{slug}_{ts}.{ext}"


def generate_report_export(
    report_id: str,
    fmt: str = "pdf",
    *,
    role: str = "owner",
    user: str = "User",
    framework: str = "",
    application: str = "",
) -> tuple[bytes, str, str]:
    """Generate filter-aware PDF / Excel / CSV report bytes."""
    report = next((r for r in list_reports() if r["id"] == report_id), None)
    ent = enterprise_dashboard()
    stats = ent["analytics"]
    fmt = (fmt or "pdf").lower()
    title = report["title"] if report else report_id
    fw = framework or (report.get("framework") if report else "Enterprise-wide")
    app = application or (report.get("application") if report else "All Applications")

    from app.exception_state_engine import get_all_exceptions
    exc_count = len(get_all_exceptions(role))

    filename = _report_filename(report, report_id, fmt)
    if fmt == "csv":
        import csv, io
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["ECS Executive Report"])
        w.writerow(["Report", title])
        w.writerow(["Report ID", report_id])
        w.writerow(["Generated By", user])
        w.writerow(["Framework", fw])
        w.writerow(["Application", app])
        w.writerow(["Compliance %", stats["overall_compliance_pct"]])
        w.writerow(["Approved", stats["totals"]["approved"]])
        w.writerow(["Pending", stats["totals"]["pending"]])
        w.writerow(["Rejected", stats["totals"]["rejected"]])
        w.writerow(["Active Exceptions", exc_count])
        w.writerow([])
        w.writerow(["Framework", "Compliance %", "Approved", "Total"])
        for fws in stats.get("framework_stats", []):
            if fw == "Enterprise-wide" or fws["name"] == fw:
                w.writerow([fws["name"], fws["compliance_pct"], fws["approved"], fws["total"]])
        return buf.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8", filename

    if fmt == "excel":
        from app.gap_export_engine import _spreadsheet_xml
        payload = {
            "meta": {"generated_at": filename, "framework": fw, "application": app, "time_range": "Current"},
            "executive_summary": [{
                "framework": fw,
                "application": app,
                "readiness_pct": stats["overall_compliance_pct"],
                "open_findings": stats["totals"]["pending"],
                "failed_controls": stats["totals"]["rejected"],
                "critical_gaps": exc_count,
                "risk_trend": "Stable",
                "audit_readiness": stats["overall_compliance_pct"],
                "gap_severity_summary": title,
            }],
            "gap_details": [],
        }
        return _spreadsheet_xml(payload), "application/vnd.ms-excel", filename

    from app.gap_export_engine import _build_pdf
    payload = {
        "meta": {
            "generated_at": filename,
            "framework": fw,
            "application": app,
            "time_range": "Current",
            "generated_by": user,
            "scope": title,
        },
        "executive_summary": [{
            "framework": fw,
            "application": app,
            "readiness_pct": stats["overall_compliance_pct"],
            "open_findings": stats["totals"]["pending"],
            "failed_controls": stats["totals"]["rejected"],
            "critical_gaps": exc_count,
            "risk_trend": "Stable",
            "audit_readiness": stats["overall_compliance_pct"],
            "gap_severity_summary": title,
        }],
        "gap_details": [],
        "audit_impact": {"report_id": report_id, "role": role},
    }
    return _build_pdf(payload), "application/pdf", filename


def generate_report_content(report_id: str) -> str:
    ent = enterprise_dashboard()
    stats = ent["analytics"]
    report = next((r for r in list_reports() if r["id"] == report_id), None)
    title = report["title"] if report else report_id
    lines = [
        "ECS EXECUTIVE REGULATORY REPORT (DEMO EXPORT)",
        f"Report: {title}",
        f"Report ID: {report_id}",
        "=" * 60,
        f"Enterprise Compliance: {stats['overall_compliance_pct']}%",
        f"Approved: {stats['totals']['approved']} / {stats['totals']['total']}",
        f"Pending: {stats['totals']['pending']}",
        f"Rejected: {stats['totals']['rejected']}",
        "",
        "Framework Summary:",
    ]
    for fw in stats["framework_stats"]:
        lines.append(
            f"  - {fw['name']}: {fw['compliance_pct']}% ({fw['approved']}/{fw['total']} approved)"
        )
    lines.append("")
    lines.append("Pan India National Score: {}%".format(ent["national_score"]))
    for r in ent.get("regions", []):
        lines.append(f"  - {r.get('region', r.get('zone', 'Region'))}: {r.get('score', 0)}%")
    lines.append("")
    lines.append("End of audit-ready export.")
    return "\n".join(lines)
