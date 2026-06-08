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


def _standard_row(
    framework: str,
    application: str,
    *,
    domain: str = "Governance",
    control: str = "—",
    finding: str = "—",
    evidence: str = "—",
    owner: str = "—",
    status: str = "—",
    risk: str = "Medium",
    last_updated: str = "—",
    control_id: str = "",
    finding_id: str = "",
) -> dict[str, Any]:
    row = {
        "application": application or "—",
        "framework": framework or "—",
        "domain": domain or "Governance",
        "control": control or "—",
        "finding": finding or "—",
        "evidence": evidence or "—",
        "owner": owner or "—",
        "status": status or "—",
        "risk": risk or "Medium",
        "last_updated": last_updated or "—",
    }
    if control_id:
        row["control_id"] = control_id
    if finding_id:
        row["finding_id"] = finding_id
    return row


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

    graph = get_framework_graph(fw)
    app_meta = next((a for a in graph.get("applications", []) if a.get("name") == application), None)
    selected_owner = app_meta.get("owner") if app_meta else detail.get("owner")
    if selected_owner:
        detail["owner"] = selected_owner

    related_controls = []
    related_evidence = []
    related_findings = []
    related_audit = _related_rows(fw, application, "audit", 4)
    related_mappings = []
    primary = []

    if row_type == "control":
        control_id = detail.get("control_id", row_id)
        graph_controls = [
            c for c in graph.get("controls", [])
            if c.get("control_id") == control_id and (not application or c.get("application") == application)
        ]
        graph_findings = [
            f for f in graph.get("findings", [])
            if f.get("linked_control") == control_id and (not application or f.get("application") == application)
        ]
        for c in graph_controls:
            related_controls.append(_standard_row(
                fw, c.get("application", application),
                domain=c.get("domain", "Governance"),
                control=c.get("control_name", control_id),
                evidence=c.get("evidence_name", "—"),
                owner=c.get("owner", "—"),
                status=c.get("workflow", "—"),
                risk="High" if c.get("validation") == "FAIL" else ("Medium" if c.get("validation") == "WARN" else "Low"),
                last_updated="—",
                control_id=control_id,
            ))
        for f in graph_findings:
            related_findings.append(_standard_row(
                fw, f.get("application", application),
                domain="Governance",
                control=control_id,
                finding=f.get("observation", f.get("finding_id", "—")),
                evidence=f.get("linked_evidence", "—"),
                owner=f.get("owner", "—"),
                status=f.get("status", "Open"),
                risk=f.get("severity", "High"),
                last_updated=f.get("open_since", "—"),
                control_id=control_id,
                finding_id=f.get("finding_id", ""),
            ))
        for c in controls:
            if c.get("control_id") != control_id:
                continue
            for ev in c.get("evidences", []):
                related_evidence.append(_standard_row(
                    fw,
                    ev.get("application_name", application),
                    domain=detail.get("domain", "Governance"),
                    control=detail.get("control_name", control_id),
                    finding="—",
                    evidence=ev.get("evidence_name", "—"),
                    owner=ev.get("uploaded_by", detail.get("owner", "—")),
                    status=ev.get("workflow_status", ev.get("evidence_status", "—")),
                    risk=detail.get("risk", "Medium"),
                    last_updated=ev.get("upload_timestamp", "—"),
                    control_id=control_id,
                ))
        primary = related_findings + related_evidence
    elif row_type == "finding":
        finding = next((f for f in graph.get("findings", []) if f.get("finding_id") == row_id), None)
        if finding:
            detail.update({
                "application": finding.get("application", application),
                "owner": finding.get("owner", detail.get("owner", "—")),
                "control_id": finding.get("linked_control", detail.get("control_id", "—")),
                "status": finding.get("status", detail.get("status", "Open")),
                "risk": finding.get("severity", detail.get("risk", "High")),
            })
            related_findings.append(_standard_row(
                fw,
                finding.get("application", application),
                control=finding.get("linked_control", "—"),
                finding=finding.get("observation", row_id),
                evidence=finding.get("linked_evidence", "—"),
                owner=finding.get("owner", "—"),
                status=finding.get("status", "Open"),
                risk=finding.get("severity", "High"),
                last_updated=finding.get("open_since", "—"),
                control_id=finding.get("linked_control", ""),
                finding_id=row_id,
            ))
            primary = related_findings[:]
        else:
            primary = _related_rows(fw, application, row_type, 8)
    else:
        app_controls = [c for c in graph.get("controls", []) if c.get("application") == application]
        app_findings = [f for f in graph.get("findings", []) if f.get("application") == application]
        for c in app_controls:
            related_controls.append(_standard_row(
                fw, application,
                domain=c.get("domain", "Governance"),
                control=c.get("control_name", c.get("control_id", "—")),
                evidence=c.get("evidence_name", "—"),
                owner=c.get("owner", selected_owner or "—"),
                status=c.get("workflow", "—"),
                risk="High" if c.get("validation") == "FAIL" else ("Medium" if c.get("validation") == "WARN" else "Low"),
                control_id=c.get("control_id", ""),
            ))
        for f in app_findings:
            related_findings.append(_standard_row(
                fw, application,
                control=f.get("linked_control", "—"),
                finding=f.get("observation", f.get("finding_id", "—")),
                evidence=f.get("linked_evidence", "—"),
                owner=f.get("owner", selected_owner or "—"),
                status=f.get("status", "Open"),
                risk=f.get("severity", "High"),
                last_updated=f.get("open_since", "—"),
                control_id=f.get("linked_control", ""),
                finding_id=f.get("finding_id", ""),
            ))
        primary = related_findings + related_controls

    if not primary:
        primary = _related_rows(fw, application, row_type, 8)
    if not related_controls:
        related_controls = _related_rows(fw, application, "control", 6)
    if not related_evidence:
        related_evidence = _related_rows(fw, application, "evidence", 6)
    if not related_findings:
        related_findings = _related_rows(fw, application, "finding", 6)
    if not related_mappings:
        related_mappings = _related_rows(fw, application, "mapping", 4)

    all_rows = primary + related_controls + related_evidence + related_findings
    rows = ensure_drill_rows(all_rows, 25, metric=f"{fw}:row:{row_type}")
    rows = [r for r in rows if r.get("framework") == fw]
    if application:
        rows = [r for r in rows if r.get("application") in (application, "—")]
    if selected_owner:
        rows = [r for r in rows if r.get("owner") in (selected_owner, "—")]

    sections = {
        "related_controls": ensure_drill_rows(related_controls, 10, metric="ctrl"),
        "related_evidence": ensure_drill_rows(related_evidence, 10, metric="evd"),
        "related_findings": ensure_drill_rows(related_findings, 10, metric="fnd"),
        "related_audit_history": ensure_drill_rows(related_audit, 10, metric="aud"),
        "related_framework_mappings": ensure_drill_rows(related_mappings, 10, metric="map"),
    }
    for k, v in list(sections.items()):
        scoped = [r for r in v if r.get("framework") == fw]
        if application:
            scoped = [r for r in scoped if r.get("application") in (application, "—")]
        if selected_owner:
            scoped = [r for r in scoped if r.get("owner") in (selected_owner, "—")]
        sections[k] = scoped

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
