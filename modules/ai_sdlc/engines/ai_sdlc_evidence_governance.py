"""Evidence Viewer governance summary — approval, finding, and package metadata."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from modules.shared.utils.demo_data_standards import between, pick, seed

ANCHOR = datetime(2026, 5, 29)


def _fmt_date(d: str) -> str:
    if not d:
        return "—"
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%Y-%m-%d %H:%M UTC"):
        try:
            return datetime.strptime(d[:10] if fmt == "%Y-%m-%d" else d, fmt).strftime("%d-%b-%Y")
        except ValueError:
            continue
    return d


def build_evidence_governance_summary(item: dict[str, Any]) -> dict[str, str | int]:
    """Derive Evidence Viewer summary fields from workflow item state."""
    item_key = item.get("evidence_id") or item.get("activity_id") or item.get("document_name", "")
    s = seed("ev-gov", item_key)
    status = item.get("status") or item.get("evidence_status") or "Pending"
    hist = item.get("approval_history") or []
    approve = next((h for h in reversed(hist) if h.get("action") == "Approve"), None)

    if status == "Approved":
        approved_by = approve["actor"] if approve else pick(s, ["Security Reviewer", "Compliance Officer", "Internal Audit"])
        approval_date = _fmt_date(
            (approve or {}).get("timestamp", "")[:10] or item.get("approval_date") or "2026-05-15"
        )
        finding_status = item.get("finding_status") or pick(s >> 2, ["Remediated", "Closed", "Accepted"])
        remediation_date = _fmt_date(item.get("remediation_date") or "2026-05-22")
        controls_covered = int(item.get("controls_covered") or between(s >> 4, 3, 6))
        evidence_package = item.get("evidence_package") or (
            "Complete" if item.get("files") else "Partial"
        )
    elif status in ("In Review", "Needs Rework"):
        approved_by = "—"
        approval_date = "—"
        finding_status = item.get("finding_status") or "Open"
        remediation_date = "—"
        controls_covered = int(item.get("controls_covered") or between(s >> 4, 1, 3))
        evidence_package = "Partial"
    else:
        approved_by = "—"
        approval_date = "—"
        finding_status = item.get("finding_status") or pick(s >> 2, ["Open", "In Remediation"])
        remediation_date = "—"
        controls_covered = int(item.get("controls_covered") or between(s >> 4, 1, 2))
        evidence_package = "Incomplete"

    return {
        "evidence_status": status,
        "approved_by": approved_by,
        "approval_date": approval_date,
        "finding_status": finding_status,
        "remediation_date": remediation_date,
        "controls_covered": controls_covered,
        "evidence_package": evidence_package,
    }


def attach_evidence_governance_summary(item: dict[str, Any]) -> dict[str, Any]:
    """Return item copy with governance summary fields attached."""
    summary = build_evidence_governance_summary(item)
    out = {**item, **summary, "governance_summary": summary}
    return out
