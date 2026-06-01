"""ECS executive report pages — Framework Adherence, Readiness, Compliance, Evidence, Findings."""

from __future__ import annotations

from app.demo_data_standards import (
    BANKING_APPLICATIONS,
    FRAMEWORKS,
    ensure_drill_rows,
    generate_standard_drill_row,
    pick,
    seed,
    between,
)
from app.framework_catalog import FRAMEWORK_CATALOG

REPORT_TYPES = {
    "framework-adherence": "Framework Adherence Report",
    "framework-readiness": "Framework Readiness Report",
    "application-compliance": "Application Compliance Report",
    "evidence-coverage": "Evidence Coverage Report",
    "findings-remediation": "Findings and Remediation Report",
}


def _cols(keys: list[tuple[str, str]]) -> list[dict]:
    return [{"key": k, "label": lbl, "wrap": k in ("application", "control", "finding")} for k, lbl in keys]


def build_framework_adherence_report() -> dict:
    base = []
    for i, fw in enumerate(FRAMEWORK_CATALOG.keys()):
        s = seed("fw-adh", fw)
        base.append({
            "framework": fw,
            "applications_covered": between(s, 8, 22),
            "controls_implemented": between(s >> 4, 45, 180),
            "coverage_pct": between(s >> 8, 62, 98),
            "owner": pick(s >> 10, ["Compliance Officer", "App Owner", "CISO Delegate"]),
            "status": pick(s >> 12, ["On Track", "At Risk", "Compliant"]),
            "last_updated": f"2026-05-{(i % 20) + 1:02d}",
        })
    rows = ensure_drill_rows(base, 25, metric="framework-adherence")
    return {
        "title": REPORT_TYPES["framework-adherence"],
        "subtitle": "Framework coverage across banking applications — controls implemented and adherence %",
        "columns": _cols([
            ("framework", "Framework"), ("applications_covered", "Applications Covered"),
            ("controls_implemented", "Controls Implemented"), ("coverage_pct", "Coverage %"),
            ("owner", "Owner"), ("status", "Status"), ("last_updated", "Last Updated"),
        ]),
        "rows": rows,
    }


def build_framework_readiness_report() -> dict:
    phases = [
        "Requirement Readiness", "Controlled Design Readiness", "Controlled Development Readiness",
        "Controlled Testing Readiness", "Go-Live Readiness",
    ]
    base = []
    for i, fw in enumerate(FRAMEWORK_CATALOG.keys()):
        s = seed("fw-rdy", fw)
        row = {"framework": fw, "application": pick(s, BANKING_APPLICATIONS), "owner": pick(s >> 2, ["App Owner", "Release Manager"])}
        for j, phase in enumerate(phases):
            row[phase.lower().replace(" ", "_")] = f"{between(s >> (j + 4), 55, 98)}%"
        row["last_updated"] = f"2026-05-{(i % 20) + 1:02d}"
        base.append(row)
    rows = ensure_drill_rows(base, 25, metric="framework-readiness")
    return {
        "title": REPORT_TYPES["framework-readiness"],
        "subtitle": "SDLC and go-live readiness gates by framework",
        "columns": _cols([
            ("framework", "Framework"), ("application", "Application"),
            ("requirement_readiness", "Requirement Readiness"),
            ("controlled_design_readiness", "Controlled Design Readiness"),
            ("controlled_development_readiness", "Controlled Development Readiness"),
            ("controlled_testing_readiness", "Controlled Testing Readiness"),
            ("go_live_readiness", "Go-Live Readiness"),
            ("owner", "Owner"), ("last_updated", "Last Updated"),
        ]),
        "rows": rows,
    }


def build_application_compliance_report() -> dict:
    base = []
    for i, app in enumerate(BANKING_APPLICATIONS):
        for j, fw in enumerate(FRAMEWORKS[:3]):
            s = seed("app-comp", app, fw, j)
            base.append({
                "application": app,
                "framework": fw,
                "control_coverage": f"{between(s, 55, 98)}%",
                "findings": between(s >> 4, 0, 14),
                "risk": pick(s >> 6, ["Critical", "High", "Medium", "Low"]),
                "owner": pick(s >> 8, ["R. Mehta", "A. Sharma", "K. Reddy"]),
                "status": pick(s >> 10, ["Compliant", "Partial", "Gap Identified"]),
                "last_updated": f"2026-05-{(i + j) % 20 + 1:02d}",
            })
    rows = ensure_drill_rows(base[:30], 25, metric="application-compliance")
    return {
        "title": REPORT_TYPES["application-compliance"],
        "subtitle": "Application × framework compliance posture",
        "columns": _cols([
            ("application", "Application"), ("framework", "Framework"),
            ("control_coverage", "Control Coverage"), ("findings", "Findings"),
            ("risk", "Risk"), ("owner", "Owner"), ("status", "Status"), ("last_updated", "Last Updated"),
        ]),
        "rows": rows,
    }


def build_evidence_coverage_report() -> dict:
    base = []
    for i in range(30):
        row = generate_standard_drill_row(i, metric="evidence-coverage")
        row["evidence_submitted"] = row.pop("evidence_count")
        row["evidence_pending"] = between(seed("ev-pend", i), 0, 6)
        base.append(row)
    rows = ensure_drill_rows(base, 25, metric="evidence-coverage")
    return {
        "title": REPORT_TYPES["evidence-coverage"],
        "subtitle": "Evidence submission and pending gaps by application and framework",
        "columns": _cols([
            ("application", "Application"), ("framework", "Framework"),
            ("domain", "Domain"), ("control", "Control"),
            ("evidence_submitted", "Evidence Submitted"), ("evidence_pending", "Evidence Pending"),
            ("owner", "Owner"), ("status", "Status"), ("last_updated", "Last Updated"),
        ]),
        "rows": rows,
    }


def build_findings_remediation_report() -> dict:
    base = []
    for i in range(30):
        row = generate_standard_drill_row(i, metric="findings-remediation")
        base.append({
            "finding": row["finding"],
            "severity": row["risk"],
            "framework": row["framework"],
            "application": row["application"],
            "owner": row["owner"],
            "due_date": f"2026-06-{(i % 25) + 1:02d}",
            "status": row["status"],
            "control": row["control"],
            "last_updated": row["last_updated"],
        })
    rows = ensure_drill_rows(base, 25, metric="findings-remediation")
    return {
        "title": REPORT_TYPES["findings-remediation"],
        "subtitle": "Open findings with severity, ownership, and remediation due dates",
        "columns": _cols([
            ("finding", "Finding"), ("severity", "Severity"), ("framework", "Framework"),
            ("application", "Application"), ("owner", "Owner"), ("due_date", "Due Date"),
            ("status", "Status"), ("control", "Control"),
        ]),
        "rows": rows,
    }


def build_report(report_type: str) -> dict | None:
    builders = {
        "framework-adherence": build_framework_adherence_report,
        "framework-readiness": build_framework_readiness_report,
        "application-compliance": build_application_compliance_report,
        "evidence-coverage": build_evidence_coverage_report,
        "findings-remediation": build_findings_remediation_report,
    }
    fn = builders.get(report_type)
    return fn() if fn else None


def report_type_for_catalog_id(report_id: str) -> str | None:
    mapping = {
        "framework-coverage": "framework-adherence",
        "framework-validation": "framework-adherence",
        "audit-readiness": "framework-readiness",
        "enterprise-cio": "framework-readiness",
        "pci-audit-pack": "application-compliance",
        "appsec-sast": "application-compliance",
        "stale-evidence": "evidence-coverage",
        "evidence-approval-summary": "evidence-coverage",
        "vapt-external": "findings-remediation",
        "remediation-velocity": "findings-remediation",
        "rejection-analysis": "findings-remediation",
    }
    return mapping.get(report_id, "application-compliance")
