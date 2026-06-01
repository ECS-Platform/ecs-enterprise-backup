"""Shared ECS demo state and helpers (single source of truth for MVP modules)."""

from app.framework_catalog import (
    FRAMEWORK_CATALOG,
    PCI_DSS_MOCK_EVIDENCES,
    build_legacy_frameworks,
    catalog_stats,
    get_all_evidence_records,
    get_evidence_lookup,
    get_framework_controls,
)

frameworks = build_legacy_frameworks()

BANKING_APPLICATIONS = [
    "Net Banking",
    "Mobile Banking",
    "Mobile Banking Edge",
    "Internet Banking",
    "Retail Banking",
    "Core Banking",
    "CBS Oracle",
    "UPI",
    "Payments",
    "Payment Switch",
    "Card Platform",
    "Treasury",
    "Wealth Portal",
    "API Gateway",
    "Loan System",
    "Loan Origination",
    "Digital Lending",
    "Customer Onboarding",
    "AML Engine",
    "Fraud Monitoring",
]

PAN_INDIA_REGIONS = [
    {"region": "North", "score": 86.8, "branches": 1240, "applications": 6, "observations_open": 38, "stale_evidence": 14, "failed_controls": 9, "audit_readiness_pct": 84.2},
    {"region": "South", "score": 91.2, "branches": 1580, "applications": 6, "observations_open": 22, "stale_evidence": 8, "failed_controls": 5, "audit_readiness_pct": 89.5},
    {"region": "East", "score": 82.4, "branches": 980, "applications": 5, "observations_open": 47, "stale_evidence": 19, "failed_controls": 12, "audit_readiness_pct": 79.8},
    {"region": "West", "score": 71.6, "branches": 1320, "applications": 6, "observations_open": 56, "stale_evidence": 24, "failed_controls": 16, "audit_readiness_pct": 68.9},
    {"region": "Central", "score": 78.9, "branches": 1105, "applications": 6, "observations_open": 41, "stale_evidence": 17, "failed_controls": 11, "audit_readiness_pct": 76.3},
]

PAN_INDIA_BRANCH_TOTAL = sum(r["branches"] for r in PAN_INDIA_REGIONS)

LIFECYCLE_STATUSES = [
    "Draft",
    "Submitted",
    "Under Review",
    "Approved",
    "Rejected",
    "Closed",
]

submitted_controls = {}
approved_controls = {}
rejected_controls = {}
escalated_controls = {}
clarification_controls = {}
cancelled_drafts = set()
owner_comments = {}
submitted_meta = {}
owner_drafts = {}
evidence_views = {}
itpp_drill_log: list[dict] = []
grc_action_log: dict = {}
exception_registry: dict[str, dict] = {}
evidence_approval_trail: dict[str, list] = {}
workflow_audit_history: dict[str, list] = {}
missing_evidence_registry: dict[str, dict] = {}
closed_observations: dict[str, dict] = {}
export_registry: dict[str, dict] = {}
export_history: list[dict] = []
scheduler_failures: list[dict] = []
scheduler_retry_log: list[dict] = []
framework_onboarding_registry: dict[str, dict] = {}
framework_onboarding_gaps: dict[str, list] = {}
dynamic_framework_catalog: dict[str, list] = {}

# Operational workflow outcomes (gap closure, assignments, uploads, mock audits)
operational_closed_gaps: list[str] = []
operational_assignments: list[dict] = []
operational_uploads: list[dict] = []
operational_mock_audits: list[dict] = []
operational_readiness_boost: int = 0

scheduler_data = [
    ("Net Banking", "PCI DSS", "Implemented", "R. Mehta", "2026-05-24 05:30 UTC"),
    ("Mobile Banking", "DPSC", "Partial", "A. Sharma", "2026-05-24 05:32 UTC"),
    ("Payments", "Nginx Baselining", "Implemented", "K. Reddy", "2026-05-24 05:28 UTC"),
    ("UPI", "OS Baselining", "Implemented", "P. Iyer", "2026-05-24 05:35 UTC"),
    ("Treasury", "DB Baselining", "Implemented", "S. Banerjee", "2026-05-23 18:00 UTC"),
    ("Loan System", "CSITE", "In Progress", "M. Joshi", "2026-05-23 22:15 UTC"),
    ("Net Banking", "ITPP", "In Progress", "R. Mehta", "2026-05-24 04:00 UTC"),
    ("Cards & Acquiring", "PCI DSS", "Implemented", "K. Reddy", "2026-05-23 20:10 UTC"),
    ("Wealth Management", "CSITE", "Implemented", "S. Banerjee", "2026-05-22 16:00 UTC"),
]

onboarded_applications = list(BANKING_APPLICATIONS)

_CATALOG = catalog_stats()


def control_key(framework_name: str, control_name: str) -> str:
    from app.framework_catalog import resolve_framework_name
    return f"{resolve_framework_name(framework_name)}::{control_name}"


def control_status(framework_name: str, control_name: str) -> str:
    key = control_key(framework_name, control_name)
    if key in approved_controls:
        return "approved"
    if key in rejected_controls:
        return "rejected"
    if key in submitted_controls:
        return "submitted"
    return "pending"


def lifecycle_status(framework_name: str, control_name: str) -> str:
    key = control_key(framework_name, control_name)
    if key in approved_controls:
        return "Closed"
    if key in rejected_controls:
        return "Rejected"
    if key in submitted_controls:
        return "Under Review"
    return "Draft"


def build_evidence_analytics():
    totals = {
        "total": 0,
        "pending": 0,
        "submitted": 0,
        "approved": 0,
        "rejected": 0,
        "evidence_artifacts": _CATALOG["evidence_count"],
        "control_count": _CATALOG["control_count"],
    }
    framework_stats = []
    evidence_rows = []

    for framework_name, controls in frameworks.items():
        fw = {
            "name": framework_name,
            "total": len(controls),
            "evidence_count": sum(
                len(c["evidences"]) for c in get_framework_controls(framework_name)
            ),
            "pending": 0,
            "submitted": 0,
            "approved": 0,
            "rejected": 0,
        }

        for control_name, evidence_name in controls:
            status = control_status(framework_name, control_name)
            totals["total"] += 1
            totals[status] += 1
            fw[status] += 1

            reject_reason = ""
            if status == "rejected":
                reject_reason = rejected_controls[
                    control_key(framework_name, control_name)
                ]["reason"]

            catalog_ctrl = next(
                (c for c in get_framework_controls(framework_name) if c["control"] == control_name),
                None,
            )
            if catalog_ctrl:
                for ev in catalog_ctrl["evidences"]:
                    evidence_rows.append(
                        {
                            "framework": framework_name,
                            "control": control_name,
                            "evidence": ev["evidence_name"],
                            "evidence_id": ev["evidence_id"],
                            "status": status,
                            "lifecycle": lifecycle_status(framework_name, control_name),
                            "reject_reason": reject_reason,
                            "application": ev["application_name"],
                            "uploaded_by": ev["uploaded_by"],
                            "reviewer": ev["reviewer"],
                            "evidence_status": ev["evidence_status"],
                            "audit_status": ev["audit_status"],
                            "server_name": ev["server_name"],
                            "expiry_date": ev["expiry_date"],
                        }
                    )
            else:
                evidence_rows.append(
                    {
                        "framework": framework_name,
                        "control": control_name,
                        "evidence": evidence_name,
                        "evidence_id": "",
                        "status": status,
                        "lifecycle": lifecycle_status(framework_name, control_name),
                        "reject_reason": reject_reason,
                        "application": "",
                        "uploaded_by": "",
                        "reviewer": "",
                        "evidence_status": "",
                        "audit_status": "",
                        "server_name": "",
                        "expiry_date": "",
                    }
                )

        fw["compliance_pct"] = (
            round((fw["approved"] / fw["total"]) * 100, 1) if fw["total"] else 0.0
        )
        framework_stats.append(fw)

    overall_compliance_pct = (
        round((totals["approved"] / totals["total"]) * 100, 1)
        if totals["total"]
        else 0.0
    )

    return {
        "totals": totals,
        "overall_compliance_pct": overall_compliance_pct,
        "framework_stats": framework_stats,
        "evidence_rows": evidence_rows,
    }
