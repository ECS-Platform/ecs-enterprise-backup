"""Enterprise gap analysis export — filter-aware PDF / Excel / CSV generation."""

from __future__ import annotations

import csv
import hashlib
import io
import uuid
from datetime import datetime, timezone
from typing import Any
from xml.sax.saxutils import escape as xml_escape

from app import ecs_state
from app.comparison_engine import ALL_FRAMEWORKS, COMPARISON_APPS, build_readiness_matrix
from app.role_filter_scope import apply_role_scope

PREFIX = {
    "PCI DSS": "PCI", "DPSC": "DPSC", "AppSec": "APPSEC", "VAPT": "VAPT",
    "OS Baselining": "OSB", "DB Baselining": "DB", "Nginx Baselining": "NGX",
    "ITPP": "ITPP", "CSITE": "CSI",
}
GAP_TYPES = ["Missing Evidence", "Failed Control", "Stale Evidence", "Readiness Gap", "SLA Breach"]
CONTROL_IDS = {
    "PCI DSS": ["PCI-10.6", "PCI-7.2", "PCI-8.3"],
    "DPSC": ["DPSC-4.1", "DP-C-04"],
    "AppSec": ["APPSEC-12", "AS-C-04"],
    "VAPT": ["VAPT-9", "VP-C-03"],
    "OS Baselining": ["OSB-14", "OS-C-01"],
    "DB Baselining": ["DB-C-01"],
    "Nginx Baselining": ["NGX-C-01"],
    "ITPP": ["IT-C-03"],
    "CSITE": ["CS-C-03"],
}


def _seed(key: str, lo: int, hi: int) -> int:
    h = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)
    return lo + (h % (hi - lo + 1))


def _period_label(time_range: str) -> str:
    mapping = {
        "Current Month": "2026_05",
        "Quarterly": "Q2_2026",
        "Yearly": "FY_2026",
        "Last Audit Cycle": "AuditCycle_2026",
    }
    return mapping.get(time_range, "2026_05")


def build_export_filename(
    framework: str,
    application: str,
    time_range: str,
    fmt: str,
) -> str:
    fw = framework.replace(" ", "_") if framework and framework != "All Frameworks" else "Enterprise"
    app = application.replace(" ", "") if application and application != "All Applications" else "GapAnalysis"
    period = _period_label(time_range)
    ext = {"excel": "xlsx", "csv": "csv", "pdf": "pdf"}.get(fmt, "xlsx")
    return f"{fw}_{app}_Gap_Report_{period}.{ext}"


def _filter_matrix(
    matrix: list[dict],
    framework: str,
    application: str,
) -> list[dict]:
    rows = matrix
    if framework and framework != "All Frameworks":
        rows = [r for r in rows if r["framework"] == framework]
    if application and application != "All Applications":
        rows = [r for r in rows if r["application"] == application]
    return rows


def _executive_summary(matrix: list[dict]) -> list[dict]:
    summaries = []
    for r in matrix:
        critical = r["readiness_pct"] < 60 or r["failed_controls"] >= 5
        summaries.append({
            "framework": r["framework"],
            "application": r["application"],
            "readiness_pct": r["readiness_pct"],
            "open_findings": r["open_findings"],
            "failed_controls": r["failed_controls"],
            "critical_gaps": max(0, r["open_gaps"] if "open_gaps" in r else r["failed_controls"] + (r["open_findings"] // 3)),
            "risk_trend": r["trend"],
            "audit_readiness": min(98, r.get("audit_maturity", r["readiness_pct"])),
            "gap_severity_summary": (
                "Critical" if critical else ("Major" if r["readiness_pct"] < 75 else "Moderate")
            ),
        })
    return summaries


def _gap_detail_rows(matrix: list[dict], time_range: str) -> list[dict]:
    from app.missing_evidence_engine import get_all_missing_evidence

    details: list[dict] = []
    seen: set[str] = set()

    for rec in get_all_missing_evidence("auditor"):
        key = rec["observation_id"]
        if key in seen:
            continue
        seen.add(key)
        match = any(
            r["framework"] == rec["framework"] and r["application"] == rec["application"]
            for r in matrix
        )
        if not matrix or match:
            details.append({
                "observation_id": rec["observation_id"],
                "application": rec["application"],
                "framework": rec["framework"],
                "control_id": rec["control_id"],
                "control_description": rec["control_description"],
                "gap_type": "Missing Evidence",
                "severity": rec["observation_severity"],
                "missing_evidence": rec["missing_evidence"],
                "risk": rec["risk"],
                "owner": rec.get("remediation_owner", rec.get("owner", "—")),
                "due_date": rec["due_date"],
                "remediation_status": rec["status"],
            })

    for i, r in enumerate(matrix):
        if r["readiness_pct"] >= 88 and r["failed_controls"] == 0 and r["stale_evidence"] == 0:
            continue
        cid = CONTROL_IDS.get(r["framework"], [f"{PREFIX.get(r['framework'], 'C')}-01"])[i % 3]
        oid = f"OBS-{PREFIX.get(r['framework'], 'GAP')}-{1000 + i}"
        if oid in seen:
            continue
        seen.add(oid)
        gap_type = "Failed Control" if r["failed_controls"] else (
            "Stale Evidence" if r["stale_evidence"] else "Readiness Gap"
        )
        details.append({
            "observation_id": oid,
            "application": r["application"],
            "framework": r["framework"],
            "control_id": cid,
            "control_description": f"{r['framework']} control validation — {time_range} posture",
            "gap_type": gap_type,
            "severity": "Critical" if r["readiness_pct"] < 55 else (
                "Major" if r["readiness_pct"] < 70 else "Medium"
            ),
            "missing_evidence": f"{gap_type} — {r['failed_controls']} failed / {r['stale_evidence']} stale",
            "risk": r["risk"],
            "owner": r.get("owner", "—"),
            "due_date": f"2026-0{6 + (i % 2)}-{(5 + (i % 20)):02d}",
            "remediation_status": "Open" if r["readiness_pct"] < 80 else "In Progress",
        })
    return details


def _failed_controls_section(matrix: list[dict]) -> dict:
    failed, rejected, stale, overdue = [], [], [], []
    for i, r in enumerate(matrix):
        if r["failed_controls"]:
            failed.append({
                "control_id": CONTROL_IDS.get(r["framework"], ["C-01"])[0],
                "application": r["application"],
                "framework": r["framework"],
                "issue": f"{r['failed_controls']} control(s) failed validation",
            })
        if r["stale_evidence"]:
            stale.append({
                "application": r["application"],
                "framework": r["framework"],
                "issue": f"{r['stale_evidence']} stale evidence item(s)",
            })
        if r["sla_breaches"]:
            overdue.append({
                "application": r["application"],
                "framework": r["framework"],
                "issue": f"{r['sla_breaches']} SLA breach(es)",
            })
        if r["readiness_pct"] < 65 and i % 2 == 0:
            rejected.append({
                "application": r["application"],
                "framework": r["framework"],
                "issue": "Rejected evidence — prior submission lacked attestation",
            })
    return {
        "failed_controls": failed,
        "rejected_evidence": rejected,
        "stale_evidence": stale,
        "overdue_remediations": overdue,
    }


def _audit_impact_section(matrix: list[dict], gap_details: list[dict]) -> dict:
    critical = [g for g in gap_details if g["severity"] in ("Critical", "Major")]
    blocked_apps = sorted({g["application"] for g in critical})
    fw_risk: dict[str, int] = {}
    for g in critical:
        fw_risk[g["framework"]] = fw_risk.get(g["framework"], 0) + 1
    high_risk_fws = sorted(fw_risk.items(), key=lambda x: -x[1])[:5]
    closure_blocked = len([g for g in gap_details if g["gap_type"] == "Missing Evidence" and g["severity"] == "Critical"])
    return {
        "audit_closure_impact": f"{closure_blocked} observation(s) blocked pending evidence",
        "risk_escalation": f"{len(critical)} high-severity gaps require executive attention",
        "applications_blocked": ", ".join(blocked_apps[:6]) or "None",
        "high_risk_frameworks": ", ".join(f"{fw} ({n})" for fw, n in high_risk_fws) or "None",
        "avg_readiness": round(sum(r["readiness_pct"] for r in matrix) / max(len(matrix), 1), 1),
    }


def build_gap_export_payload(
    *,
    framework: str = "All Frameworks",
    scope: str = "All Applications",
    time_range: str = "Current Month",
    application: str = "All Applications",
    role: str = "owner",
    include_executive: bool = True,
    include_observations: bool = True,
    include_failed: bool = True,
    include_missing: bool = True,
    include_audit_impact: bool = True,
) -> dict[str, Any]:
    matrix = apply_role_scope(
        build_readiness_matrix(scope, time_range),
        role,
    )
    matrix = _filter_matrix(matrix, framework, application)
    gap_details = _gap_detail_rows(matrix, time_range)
    if framework != "All Frameworks":
        gap_details = [g for g in gap_details if g["framework"] == framework]
    if application != "All Applications":
        gap_details = [g for g in gap_details if g["application"] == application]

    payload = {
        "meta": {
            "title": "ECS Gap Analysis Export",
            "framework": framework,
            "application": application,
            "scope": scope,
            "time_range": time_range,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "record_count": len(gap_details),
        },
        "filters_applied": {
            "framework": framework,
            "application": application,
            "scope": scope,
            "time_range": time_range,
        },
    }
    if include_executive:
        payload["executive_summary"] = _executive_summary(matrix)
    if include_observations or include_missing:
        payload["gap_details"] = gap_details
    if include_failed:
        payload["failed_controls"] = _failed_controls_section(matrix)
    if include_audit_impact:
        payload["audit_impact"] = _audit_impact_section(matrix, gap_details)
    return payload


def record_export(
    *,
    user: str,
    role: str,
    fmt: str,
    filename: str,
    payload: dict,
    content_bytes: bytes,
    content_type: str,
) -> dict:
    export_id = f"EXP-{uuid.uuid4().hex[:10].upper()}"
    meta = payload["meta"]
    entry = {
        "export_id": export_id,
        "title": f"Gap Analysis — {meta['framework']} / {meta['application']}",
        "format": fmt.upper(),
        "filename": filename,
        "generated_by": user,
        "role": role,
        "timestamp": meta["generated_at"],
        "filters_used": payload["filters_applied"],
        "status": "Generated",
        "record_count": meta["record_count"],
        "category": "Gap Analysis",
        "framework": meta["framework"],
        "application": meta["application"],
        "download_path": f"/mvp/exports/download/{export_id}",
        "preview_path": f"/mvp/exports/preview/{export_id}",
    }
    ecs_state.export_registry[export_id] = {
        **entry,
        "content_bytes": content_bytes,
        "content_type": content_type,
        "payload": payload,
    }
    ecs_state.export_history.insert(0, entry)
    ecs_state.export_history[:] = ecs_state.export_history[:50]
    return entry


def _rows_to_csv(rows: list[dict], headers: list[str]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore")
    w.writeheader()
    for row in rows:
        w.writerow({h: row.get(h, "") for h in headers})
    return buf.getvalue()


def _spreadsheet_xml(payload: dict) -> bytes:
    meta = payload["meta"]
    parts = [
        '<?xml version="1.0"?>',
        '<?mso-application progid="Excel.Sheet"?>',
        '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" '
        'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">',
        '<Styles><Style ss:ID="hdr"><Font ss:Bold="1"/><Interior ss:Color="#1e3a5f" ss:Pattern="Solid"/>'
        '<Font ss:Color="#FFFFFF"/></Style></Styles>',
    ]

    def sheet(name: str, headers: list[str], rows: list[dict]) -> None:
        parts.append(f'<Worksheet ss:Name="{xml_escape(name[:31])}"><Table>')
        parts.append("<Row>")
        for h in headers:
            parts.append(f'<Cell ss:StyleID="hdr"><Data ss:Type="String">{xml_escape(h)}</Data></Cell>')
        parts.append("</Row>")
        for row in rows:
            parts.append("<Row>")
            for h in headers:
                val = str(row.get(h, ""))
                parts.append(f'<Cell><Data ss:Type="String">{xml_escape(val)}</Data></Cell>')
            parts.append("</Row>")
        parts.append("</Table></Worksheet>")

    parts.append('<Worksheet ss:Name="Cover"><Table><Row><Cell><Data ss:Type="String">ECS ENTERPRISE GAP ANALYSIS</Data></Cell></Row>')
    for k, v in meta.items():
        parts.append(f"<Row><Cell><Data ss:Type=\"String\">{xml_escape(str(k))}: {xml_escape(str(v))}</Data></Cell></Row>")
    parts.append("</Table></Worksheet>")

    if payload.get("executive_summary"):
        sheet("Executive Summary", [
            "framework", "application", "readiness_pct", "open_findings", "failed_controls",
            "critical_gaps", "risk_trend", "audit_readiness", "gap_severity_summary",
        ], payload["executive_summary"])

    if payload.get("gap_details"):
        sheet("Gap Details", [
            "observation_id", "application", "framework", "control_id", "control_description",
            "gap_type", "severity", "missing_evidence", "risk", "owner", "due_date", "remediation_status",
        ], payload["gap_details"])

    fc = payload.get("failed_controls", {})
    if fc:
        combined = []
        for label, key in [
            ("Failed Control", "failed_controls"),
            ("Rejected Evidence", "rejected_evidence"),
            ("Stale Evidence", "stale_evidence"),
            ("Overdue Remediation", "overdue_remediations"),
        ]:
            for item in fc.get(key, []):
                combined.append({**item, "category": label})
        if combined:
            sheet("Failed Controls", ["category", "framework", "application", "control_id", "issue"], combined)

    if payload.get("audit_impact"):
        ai = payload["audit_impact"]
        sheet("Audit Impact", ["metric", "value"], [
            {"metric": k.replace("_", " ").title(), "value": str(v)} for k, v in ai.items()
        ])

    parts.append("</Workbook>")
    return "\n".join(parts).encode("utf-8")


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_pdf(payload: dict) -> bytes:
    meta = payload["meta"]
    lines = [
        "ECS ENTERPRISE GAP ANALYSIS REPORT",
        "=" * 52,
        f"Framework: {meta['framework']}",
        f"Application: {meta['application']}",
        f"Scope: {meta['scope']} | Period: {meta['time_range']}",
        f"Generated: {meta['generated_at']}",
        "",
        "EXECUTIVE SUMMARY",
        "-" * 40,
    ]
    for s in (payload.get("executive_summary") or [])[:15]:
        lines.append(
            f"  {s['application']} / {s['framework']}: {s['readiness_pct']}% readiness | "
            f"{s['open_findings']} findings | {s['failed_controls']} failed | {s['gap_severity_summary']}"
        )
    lines.extend(["", "GAP DETAILS", "-" * 40])
    for g in (payload.get("gap_details") or [])[:25]:
        lines.append(
            f"  {g['observation_id']} | {g['application']} | {g['control_id']} | "
            f"{g['severity']} | {str(g['missing_evidence'])[:50]}"
        )
    ai = payload.get("audit_impact") or {}
    if ai:
        lines.extend(["", "AUDIT IMPACT", "-" * 40])
        for k, v in ai.items():
            lines.append(f"  {k.replace('_', ' ').title()}: {v}")

    stream_parts = ["BT", "/F1 9 Tf", "40 760 Td", "14 TL"]
    for line in lines[:90]:
        stream_parts.append(f"({_pdf_escape(line[:110])}) '")
    stream_parts.append("ET")
    stream = "\n".join(stream_parts).encode("latin-1", errors="replace")

    chunks: list[bytes] = []
    offsets: list[int] = [0]

    def add(obj: bytes) -> None:
        offsets.append(sum(len(c) for c in chunks) + len(b"%PDF-1.4\n"))
        chunks.append(obj)

    add(b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n")
    add(b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n")
    add(
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R"
        b"/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    )
    add(f"4 0 obj<</Length {len(stream)}>>stream\n".encode() + stream + b"\nendstream endobj\n")
    add(b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n")

    body = b"%PDF-1.4\n" + b"".join(chunks)
    xref_start = len(body)
    xref = b"xref\n0 6\n0000000000 65535 f \n"
    for off in offsets[1:]:
        xref += f"{off:010d} 00000 n \n".encode()
    trailer = b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n" + str(xref_start).encode() + b"\n%%EOF"
    return body + xref + trailer


def _build_csv(payload: dict) -> bytes:
    buf = io.StringIO()
    meta = payload["meta"]
    buf.write(f"ECS Gap Analysis Export,{meta['generated_at']}\n")
    buf.write(f"Framework,{meta['framework']}\nApplication,{meta['application']}\n\n")

    if payload.get("executive_summary"):
        buf.write("EXECUTIVE SUMMARY\n")
        headers = [
            "framework", "application", "readiness_pct", "open_findings", "failed_controls",
            "critical_gaps", "risk_trend", "audit_readiness", "gap_severity_summary",
        ]
        buf.write(_rows_to_csv(payload["executive_summary"], headers))
        buf.write("\n")

    if payload.get("gap_details"):
        buf.write("GAP DETAILS\n")
        headers = [
            "observation_id", "application", "framework", "control_id", "control_description",
            "gap_type", "severity", "missing_evidence", "risk", "owner", "due_date", "remediation_status",
        ]
        buf.write(_rows_to_csv(payload["gap_details"], headers))
    return buf.getvalue().encode("utf-8-sig")


def generate_gap_export_file(payload: dict, fmt: str) -> tuple[bytes, str, str]:
    fmt = (fmt or "excel").lower()
    meta = payload["meta"]
    filename = build_export_filename(
        meta["framework"], meta["application"], meta["time_range"], fmt,
    )
    if fmt == "csv":
        return _build_csv(payload), "text/csv; charset=utf-8", filename
    if fmt == "pdf":
        return _build_pdf(payload), "application/pdf", filename
    # Excel — SpreadsheetML (opens in Excel; saved with .xlsx extension per naming spec)
    return (
        _spreadsheet_xml(payload),
        "application/vnd.ms-excel",
        filename,
    )


def build_html_preview(payload: dict) -> str:
    meta = payload["meta"]
    html = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        "<title>Gap Analysis Preview</title>",
        "<style>body{font-family:Segoe UI,Arial,sans-serif;margin:0;color:#0f172a;background:#f8fafc}",
        ".hdr{background:linear-gradient(135deg,#1e3a5f,#2563eb);color:#fff;padding:20px 24px}",
        ".hdr h1{margin:0;font-size:1.35rem}.hdr p{margin:6px 0 0;opacity:.9;font-size:13px}",
        ".body{padding:24px;max-width:100%;overflow-x:hidden}h2{font-size:1rem;color:#1e3a5f;margin-top:20px}",
        ".ecs-table-scroll{max-width:100%;overflow-x:auto}",
        "table.ecs-executive-table,table{border-collapse:collapse;width:100%;max-width:100%;table-layout:fixed;font-size:11px;margin:12px 0;background:#fff}",
        "table th,table td{border:1px solid #cbd5e1;padding:3px 5px;text-align:left;white-space:normal;word-break:break-word;overflow-wrap:anywhere;vertical-align:top}",
        "table thead th{position:sticky;top:0;background:#1e3a5f;color:#fff;z-index:1;font-size:10px;text-transform:uppercase}",
        ".kpi{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0}",
        ".kpi span{background:#fff;border:1px solid #e2e8f0;border-radius:6px;padding:8px 12px;font-size:12px}</style></head><body>",
        "<div class='hdr'><h1>ECS Enterprise Gap Analysis</h1>",
        f"<p>{meta['framework']} · {meta['application']} · {meta['time_range']} · {meta['generated_at']}</p></div>",
        "<div class='body'>",
    ]
    if payload.get("executive_summary"):
        html.append("<h2>Executive Summary</h2><div class='ecs-table-scroll'><table class='ecs-executive-table'><tr>")
        keys = list(payload["executive_summary"][0].keys()) if payload["executive_summary"] else []
        html.append("".join(f"<th>{k}</th>" for k in keys) + "</tr>")
        for row in payload["executive_summary"][:20]:
            html.append("<tr>" + "".join(f"<td>{row.get(k,'')}</td>" for k in keys) + "</tr>")
        html.append("</table></div>")
    if payload.get("gap_details"):
        html.append("<h2>Gap Details</h2><div class='ecs-table-scroll'><table class='ecs-executive-table'><tr>")
        keys = list(payload["gap_details"][0].keys()) if payload["gap_details"] else []
        html.append("".join(f"<th>{k}</th>" for k in keys) + "</tr>")
        for row in payload["gap_details"][:40]:
            html.append("<tr>" + "".join(f"<td>{row.get(k,'')}</td>" for k in keys) + "</tr>")
        html.append("</table></div>")
    ai = payload.get("audit_impact")
    if ai:
        html.append("<h2>Audit Impact</h2><ul>")
        for k, v in ai.items():
            html.append(f"<li><strong>{k.replace('_',' ').title()}:</strong> {v}</li>")
        html.append("</ul>")
    html.append("</div></body></html>")
    return "".join(html)
