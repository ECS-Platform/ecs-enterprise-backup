"""Unified demo overview KPI drill API."""

from __future__ import annotations

from modules.shared.utils.demo_data_standards import DRILL_COLUMNS, ensure_drill_rows, generate_standard_drill_row
from modules.shared.services.ecs_mock_engine import (
    build_demo_overview,
    generate_baselining_drift,
    generate_evidence_lineage,
    generate_servicenow_tickets,
    generate_vapt_findings,
    list_banking_applications,
    list_frameworks_catalog,
)


def _rows_from_apps() -> list[dict]:
    return [
        {
            "application": a["application"],
            "framework": f"{a['framework_count']} frameworks",
            "domain": a.get("vertical", "Digital Banking"),
            "control": f"CTRL-{a['application'][:3].upper()}-01",
            "owner": a["owner"],
            "status": "In Scope",
            "risk": a.get("criticality", "Medium"),
            "evidence": f"{a['evidence_count']} records",
            "finding": f"{a['pending_observations']} open observations",
            "date": "2026-05-24",
        }
        for a in list_banking_applications()
    ]


def drill_demo_kpi(metric: str) -> dict:
    metric = (metric or "").lower()
    base: list[dict] = []

    if metric == "applications":
        base = _rows_from_apps()
    elif metric in ("frameworks", "controls"):
        for f in list_frameworks_catalog():
            base.append({
                "application": "Enterprise-wide",
                "framework": f["framework"],
                "domain": f.get("category", "Compliance"),
                "control": f"{f['control_count']} controls",
                "owner": "Compliance Officer",
                "status": "Active",
                "risk": "Medium" if f["readiness_pct"] >= 75 else "High",
                "evidence": f"{f['evidence_count']} artefacts",
                "finding": f"{f['readiness_pct']}% readiness",
                "date": "2026-05-24",
            })
    elif metric == "tickets":
        for t in generate_servicenow_tickets()[:40]:
            base.append({
                "application": t.get("application", "—"),
                "framework": t.get("framework", "—"),
                "domain": t.get("type", "Incident"),
                "control": "—",
                "owner": t.get("owner", "—"),
                "status": t.get("state", "Open"),
                "risk": t.get("priority", "Medium"),
                "evidence": t.get("ticket_id", "—"),
                "finding": t.get("title", "")[:80],
                "date": t.get("opened_at", "2026-05-24")[:10],
            })
    elif metric == "vapt":
        for f in generate_vapt_findings()["findings"]:
            base.append({
                "application": f.get("application", "—"),
                "framework": "VAPT",
                "domain": "Application Security",
                "control": f.get("finding_id", "—"),
                "owner": f.get("owner", "AppSec Lead"),
                "status": f.get("status", "Open"),
                "risk": f.get("severity", "High"),
                "evidence": f"VAPT-{f.get('finding_id', '')}",
                "finding": f.get("title", "")[:80],
                "date": "2026-05-24",
            })
    elif metric == "drift":
        drift = generate_baselining_drift()
        for d in drift.get("by_application", []):
            base.append({
                "application": d.get("application", "—"),
                "framework": d.get("framework", "OS Baselining"),
                "domain": d.get("category", "Baselining"),
                "control": d.get("control", "Baseline drift"),
                "owner": d.get("remediation_owner", "Infra Lead"),
                "status": "Open",
                "risk": d.get("severity", "High"),
                "evidence": f"DRF-{d.get('drift_count', 0)}",
                "finding": f"{d.get('drift_count', 0)} drift items",
                "date": str(d.get("remediation_eta", "2026-05-24"))[:10],
            })
    elif metric == "evidence":
        for e in generate_evidence_lineage(limit=40):
            base.append({
                "application": e.get("application", "—"),
                "framework": e.get("original_framework", "—"),
                "domain": "Evidence",
                "control": "—",
                "owner": e.get("owner", "App Owner"),
                "status": "Linked",
                "risk": "Low",
                "evidence": e.get("evidence_name", e.get("evidence_id", "—")),
                "finding": f"{len(e.get('linked_frameworks', []))} linked FW",
                "date": "2026-05-24",
            })
    elif metric == "hallucinations":
        overview = build_demo_overview()
        for h in overview.get("ai_governance", {}).get("hallucinations", []):
            base.append({
                "application": h.get("application", "AI Assistant"),
                "framework": "AI Governance",
                "domain": "Model Risk",
                "control": h.get("alert_id", "—"),
                "owner": h.get("user", "—"),
                "status": h.get("status", "Open"),
                "risk": "High",
                "evidence": h.get("model", "—"),
                "finding": h.get("fabrication_signal", "Hallucination")[:80],
                "date": str(h.get("timestamp", "2026-05-24"))[:10],
            })
    else:
        base = [generate_standard_drill_row(i, metric=metric) for i in range(25)]

    rows = ensure_drill_rows(base, 25, metric=metric)
    return {"ok": True, "title": metric.replace("_", " ").title(), "rows": rows, "columns": DRILL_COLUMNS}
