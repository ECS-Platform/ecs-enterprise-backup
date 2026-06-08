"""Framework table row drilldown — detail + related records."""

from __future__ import annotations

from typing import Any

from modules.shared.utils.demo_data_standards import ensure_drill_rows, generate_standard_drill_row, pick, seed, between
from modules.frameworks.engines.framework_catalog import get_framework_controls
from modules.governance.engines.governance_relational_model import get_framework_graph
from modules.frameworks.engines.framework_workflow_engine import _fw_apps

STANDARD_COLUMNS = [
    "application", "framework", "domain", "control", "finding",
    "evidence", "owner", "status", "risk", "last_updated",
]

AUDIT_ACTIONS = [
    "Evidence submitted", "Control validated", "Observation raised",
    "Finding remediated", "Exception approved", "Audit closure",
]


def _norm(text: str) -> str:
    return "".join(ch.lower() for ch in str(text or "") if ch.isalnum())


def _resolve_control(controls: list[dict[str, Any]], control_ref: str) -> dict[str, Any] | None:
    if not controls:
        return None
    ref = (control_ref or "").strip()
    if not ref:
        return None
    for c in controls:
        if c.get("control_id") == ref:
            return c
    refn = _norm(ref)
    for c in controls:
        cid = str(c.get("control_id", ""))
        cname = str(c.get("control", ""))
        if _norm(cid) == refn or _norm(cname) == refn:
            return c
        if refn and (_norm(cid).startswith(refn) or refn in _norm(cname)):
            return c
    return None


def _related_rows(framework: str, application: str, prefix: str, n: int = 12) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(n):
        row = generate_standard_drill_row(i, metric=f"{framework}:{prefix}", application=application)
        row["framework"] = framework
        row["application"] = application
        if prefix == "audit":
            row["finding"] = pick(seed("audit", i), AUDIT_ACTIONS)
            row["status"] = "Recorded"
        rows.append(row)
    return rows


def drill_framework_row(framework: str, row_type: str, row_id: str) -> dict[str, Any]:
    fw = framework.strip()
    row_type = (row_type or "application").strip().lower()
    row_id = (row_id or "").strip()
    controls = get_framework_controls(fw)
    apps = list(_fw_apps(fw, controls))
    application = row_id if row_id in apps or row_type == "application" else (apps[0] if apps else "Net Banking")

    detail: dict[str, Any] = {
        "application": application,
        "framework": fw,
        "row_type": row_type,
        "row_id": row_id,
        "owner": pick(seed(fw, row_id), ["R. Mehta", "A. Sharma", "S. Banerjee", "P. Nair"]),
        "status": pick(seed(row_id, fw), ["Open", "In Remediation", "Approved", "Pending Review"]),
        "risk": pick(seed(row_id), ["Critical", "High", "Medium", "Low"]),
        "readiness_pct": f"{between(seed(fw, row_id), 68, 94)}%",
        "controls_in_scope": len(controls),
        "open_findings": between(seed(row_id, "f"), 1, 12),
    }

    if row_type == "control":
        resolved_control = _resolve_control(controls, row_id)
        resolved_control_id = resolved_control.get("control_id", row_id) if resolved_control else row_id
        detail["control"] = resolved_control.get("control", row_id) if resolved_control else row_id
        detail["control_id"] = resolved_control_id
        graph = get_framework_graph(fw)
        catalog_row = resolved_control or next((c for c in controls if c.get("control_id") == row_id), None)
        control_graph_rows = [c for c in graph.get("controls", []) if c.get("control_id") == resolved_control_id]
        findings = [f for f in graph.get("findings", []) if f.get("linked_control") == resolved_control_id]
        related_evidence_rows = []
        for ev in (catalog_row.get("evidences", []) if catalog_row else []):
            related_evidence_rows.append(ev.get("evidence_name", "—"))
        mapped_apps = sorted({
            *(ev.get("application_name", "") for ev in (catalog_row.get("evidences", []) if catalog_row else [])),
            *(c.get("application", "") for c in control_graph_rows),
        })
        mapped_apps = [a for a in mapped_apps if a]
        evidence_count = len(catalog_row.get("evidences", [])) if catalog_row else 0
        domain = (control_graph_rows[0].get("domain") if control_graph_rows else "Governance")
        validation = (control_graph_rows[0].get("validation") if control_graph_rows else "PENDING")
        status = "Approved" if validation == "PASS" else ("Failed" if validation == "FAIL" else "Pending")
        detail.update({
            "control_name": catalog_row.get("control", resolved_control_id) if catalog_row else resolved_control_id,
            "framework": fw,
            "domain": domain,
            "objective": f"Demonstrate {domain.lower()} control effectiveness for {fw} audit scope.",
            "implementation_guidance": "Implement policy, enforce technical guardrails, and capture auditor-verifiable evidence.",
            "required_evidence": ", ".join(ev.get("evidence_name", "") for ev in (catalog_row.get("evidences", []) if catalog_row else [])[:3]) or "Control evidence package",
            "mapped_applications": ", ".join(mapped_apps) if mapped_apps else application,
            "related_evidence": ", ".join(related_evidence_rows[:5]) or "—",
            "related_findings": ", ".join(f.get("finding_id", "—") for f in findings[:5]) or "—",
            "evidence_count": evidence_count,
            "finding_count": len(findings),
            "status": status,
        })
    elif row_type == "finding":
        detail["finding_id"] = row_id
        detail["finding"] = row_id

    primary = _related_rows(fw, application, row_type, 8)
    related_controls = _related_rows(fw, application, "control", 6)
    related_evidence = _related_rows(fw, application, "evidence", 6)
    related_findings = _related_rows(fw, application, "finding", 6)
    related_audit = _related_rows(fw, application, "audit", 6)
    related_mappings = _related_rows(fw, application, "mapping", 4)

    all_rows = primary + related_controls + related_evidence + related_findings
    rows = ensure_drill_rows(all_rows, 25, metric=f"{fw}:row:{row_type}")

    sections = {
        "related_controls": ensure_drill_rows(related_controls, 10, metric="ctrl"),
        "related_evidence": ensure_drill_rows(related_evidence, 10, metric="evd"),
        "related_findings": ensure_drill_rows(related_findings, 10, metric="fnd"),
        "related_audit_history": ensure_drill_rows(related_audit, 10, metric="aud"),
        "related_framework_mappings": ensure_drill_rows(related_mappings, 10, metric="map"),
    }

    for r in rows:
        for c in STANDARD_COLUMNS:
            r.setdefault(c, "—")

    title = f"{row_type.replace('_', ' ').title()}: {row_id or application} — {fw}"
    return {
        "ok": True,
        "title": title,
        "detail": detail,
        "rows": rows,
        "columns": STANDARD_COLUMNS,
        "sections": sections,
    }
