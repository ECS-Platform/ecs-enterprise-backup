"""Role-based data visibility for ECS mock datasets — all modules, all personas."""

from __future__ import annotations

from modules.shared.services.ecs_state import BANKING_APPLICATIONS
from modules.governance.engines.governance_mock_data import OWNERS

ROLE_APPLICATIONS: dict[str, list[str] | None] = {
    "owner": ["Net Banking", "Mobile Banking", "Payments"],
    "auditor": None,
    "cio": None,
    "vertical_head": ["Net Banking", "Mobile Banking", "UPI", "Payments", "Treasury"],
    "compliance_head": None,
    "compliance_officer": None,
    "functional_head": ["Treasury", "Loan System", "Payments"],
    "admin": None,
}

ROLE_BUSINESS_UNITS: dict[str, list[str] | None] = {
    "vertical_head": ["Retail Banking", "Digital Banking", "Digital Payments", "Payments"],
    "functional_head": ["Treasury", "Retail Lending", "Payments"],
    "owner": ["Retail Banking", "Digital Banking", "Payments"],
}

ROLE_FRAMEWORKS: dict[str, list[str] | None] = {
    "compliance_head": ["PCI DSS", "DPSC", "VAPT", "AppSec", "CSITE", "ITPP"],
    "compliance_officer": ["PCI DSS", "DPSC", "VAPT", "AppSec", "CSITE", "ITPP"],
    "auditor": None,
    "owner": None,
    "cio": None,
}


def normalize_role(role: str) -> str:
    return role.replace("compliance_officer", "compliance_head")


def apps_for_role(role: str) -> list[str] | None:
    return ROLE_APPLICATIONS.get(normalize_role(role), ROLE_APPLICATIONS.get(role))


def _row_app(row: dict) -> str:
    return row.get("application") or row.get("app") or row.get("name") or ""


def _row_owner(row: dict) -> str:
    return row.get("owner") or ""


def apply_role_scope(rows: list[dict], role: str, *, app_key: str = "application") -> list[dict]:
    """Filter rows to role-visible applications. Auditors/CIO see all."""
    role = normalize_role(role)
    allowed = apps_for_role(role)
    if allowed is None:
        return list(rows)
    out = []
    for r in rows:
        app = r.get(app_key) or _row_app(r)
        if not app or app in ("All Applications", "Enterprise-wide"):
            out.append(r)
        elif app in allowed:
            out.append(r)
        elif any(a in app for a in allowed):
            out.append(r)
    return out or rows[: max(4, len(rows) // 4)]


def scope_reuse_for_role(data: dict, role: str) -> dict:
    """Owner sees owned-app mappings; auditor emphasizes pending approval queue."""
    role = normalize_role(role)
    rows = apply_role_scope(data.get("rows", []), role)
    pending = [r for r in rows if r.get("status") != "Approved"]
    if role == "auditor":
        pending = [r for r in rows if r.get("status") in ("Pending Review", "Candidate", "Rejected")]
    candidates = apply_role_scope(data.get("candidates", []), role)
    workbench = apply_role_scope(data.get("workbench", []), role)
    return {
        **data,
        "rows": rows,
        "pending_rows": pending or rows[:8],
        "candidates": candidates,
        "workbench": workbench,
    }


def scope_reports_for_role(rows: list[dict], role: str) -> list[dict]:
    role = normalize_role(role)
    scoped = apply_role_scope(rows, role)
    if role == "compliance_head":
        reg = ROLE_FRAMEWORKS["compliance_head"]
        scoped = [r for r in scoped if r.get("framework") in reg or r.get("framework") == "Enterprise-wide"]
    if role == "auditor":
        scoped = [r for r in scoped if "audit" in r.get("title", "").lower() or r.get("category") == "Audit"]
        if len(scoped) < 4:
            scoped = rows
    return scoped or rows


def owner_label_for_role(role: str) -> str | None:
    mapping = {
        "owner": "R. Mehta",
        "vertical_head": None,
        "functional_head": "S. Banerjee",
    }
    return mapping.get(normalize_role(role))
