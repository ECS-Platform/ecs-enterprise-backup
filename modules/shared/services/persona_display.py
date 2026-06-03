"""Persona display labels — sidebar branding, user profile, and dashboard tabs."""

from __future__ import annotations

PERSONA_BY_ROLE: dict[str, dict[str, str]] = {
    "cio": {
        "display_name": "R. Khanna",
        "role_title": "Chief Information Officer",
        "role_short": "CIO",
        "platform_label": "ECS Platform",
    },
    "owner": {
        "display_name": "R. Sharma",
        "role_title": "Application Owner",
        "role_short": "Application Owner",
        "platform_label": "ECS Platform",
    },
    "auditor": {
        "display_name": "A. Banerjee",
        "role_title": "Lead Auditor",
        "role_short": "Auditor",
        "platform_label": "ECS Platform",
    },
    "vertical_head": {
        "display_name": "K. Reddy",
        "role_title": "Vertical Head",
        "role_short": "Vertical Head",
        "platform_label": "ECS Platform",
    },
    "compliance_head": {
        "display_name": "P. Mehta",
        "role_title": "Compliance Officer",
        "role_short": "Compliance Officer",
        "platform_label": "ECS Platform",
    },
    "compliance_officer": {
        "display_name": "P. Mehta",
        "role_title": "Compliance Officer",
        "role_short": "Compliance Officer",
        "platform_label": "ECS Platform",
    },
    "functional_head": {
        "display_name": "V. Nair",
        "role_title": "Functional Head",
        "role_short": "Functional Head",
        "platform_label": "ECS Platform",
    },
    "security_officer": {
        "display_name": "M. Kapoor",
        "role_title": "Security Officer",
        "role_short": "Security Officer",
        "platform_label": "ECS Platform",
    },
    "operations_owner": {
        "display_name": "D. Iyer",
        "role_title": "Operations Owner",
        "role_short": "Operations Owner",
        "platform_label": "ECS Platform",
    },
    "ai_governance_owner": {
        "display_name": "N. Chatterjee",
        "role_title": "AI Governance Owner",
        "role_short": "AI Governance Owner",
        "platform_label": "ECS Platform",
    },
    "ai_sdlc_owner": {
        "display_name": "L. Menon",
        "role_title": "AI SDLC Owner",
        "role_short": "AI SDLC Owner",
        "platform_label": "ECS Platform",
    },
    "framework_owner": {
        "display_name": "J. Patel",
        "role_title": "Framework Owner",
        "role_short": "Framework Owner",
        "platform_label": "ECS Platform",
    },
}

MODULE_TABS: dict[str, list[dict[str, str]]] = {
    "executive_overview": [
        {"id": "tab-overview", "label": "Overview"},
        {"id": "tab-risk", "label": "Risk"},
        {"id": "tab-evidence", "label": "Evidence"},
        {"id": "tab-compliance", "label": "Compliance"},
        {"id": "tab-analytics", "label": "Analytics"},
    ],
    "enterprise_grc": [
        {"id": "tab-overview", "label": "Overview"},
        {"id": "tab-risk", "label": "Risk"},
        {"id": "tab-evidence", "label": "Evidence"},
        {"id": "tab-compliance", "label": "Compliance"},
        {"id": "tab-analytics", "label": "Analytics"},
    ],
    "ai_sdlc": [
        {"id": "tab-overview", "label": "Overview"},
        {"id": "tab-applications", "label": "Applications"},
        {"id": "tab-evidence", "label": "Evidence"},
        {"id": "tab-compliance", "label": "Compliance"},
        {"id": "tab-analytics", "label": "Analytics"},
    ],
}

PERSONA_TABS: dict[str, list[dict[str, str]]] = {
    "cio": [
        {"id": "tab-overview", "label": "Overview"},
        {"id": "tab-approvals", "label": "Approvals"},
        {"id": "tab-escalations", "label": "Escalations"},
        {"id": "tab-analytics", "label": "Analytics"},
    ],
    "vertical_head": [
        {"id": "tab-overview", "label": "Overview"},
        {"id": "tab-applications", "label": "Applications"},
        {"id": "tab-evidence", "label": "Evidence"},
        {"id": "tab-frameworks", "label": "Frameworks"},
        {"id": "tab-approvals", "label": "Approvals"},
    ],
    "auditor": [
        {"id": "tab-overview", "label": "Overview"},
        {"id": "tab-observations", "label": "Observations"},
        {"id": "tab-evidence", "label": "Evidence Review"},
        {"id": "tab-pending", "label": "Pending Approval"},
        {"id": "tab-reports", "label": "Reports"},
    ],
    "owner": [
        {"id": "tab-overview", "label": "Overview"},
        {"id": "tab-controls", "label": "Controls"},
        {"id": "tab-evidence", "label": "Evidence"},
        {"id": "tab-findings", "label": "Findings"},
        {"id": "tab-remediation", "label": "Remediation"},
    ],
    "compliance_head": [
        {"id": "tab-overview", "label": "Overview"},
        {"id": "tab-frameworks", "label": "Frameworks"},
        {"id": "tab-mapping", "label": "Control Mapping"},
        {"id": "tab-gaps", "label": "Gaps"},
        {"id": "tab-reports", "label": "Reports"},
    ],
    "compliance_officer": [
        {"id": "tab-overview", "label": "Overview"},
        {"id": "tab-frameworks", "label": "Frameworks"},
        {"id": "tab-mapping", "label": "Control Mapping"},
        {"id": "tab-gaps", "label": "Gaps"},
        {"id": "tab-reports", "label": "Reports"},
    ],
    "functional_head": [
        {"id": "tab-overview", "label": "Overview"},
        {"id": "tab-applications", "label": "Applications"},
        {"id": "tab-evidence", "label": "Evidence"},
        {"id": "tab-frameworks", "label": "Frameworks"},
        {"id": "tab-approvals", "label": "Approvals"},
    ],
    "security_officer": [
        {"id": "tab-overview", "label": "Overview"},
        {"id": "tab-risk", "label": "Risk"},
        {"id": "tab-evidence", "label": "Evidence"},
        {"id": "tab-compliance", "label": "Compliance"},
        {"id": "tab-reports", "label": "Reports"},
    ],
    "operations_owner": [
        {"id": "tab-overview", "label": "Overview"},
        {"id": "tab-scheduler", "label": "Scheduler"},
        {"id": "tab-integrations", "label": "Integrations"},
        {"id": "tab-onboarding", "label": "Onboarding"},
        {"id": "tab-analytics", "label": "Analytics"},
    ],
    "ai_governance_owner": [
        {"id": "tab-overview", "label": "Overview"},
        {"id": "tab-posture", "label": "Posture"},
        {"id": "tab-registry", "label": "Registry"},
        {"id": "tab-evidence", "label": "Evidence"},
        {"id": "tab-reports", "label": "Reports"},
    ],
    "ai_sdlc_owner": [
        {"id": "tab-overview", "label": "Overview"},
        {"id": "tab-applications", "label": "Applications"},
        {"id": "tab-evidence", "label": "Evidence"},
        {"id": "tab-compliance", "label": "Compliance"},
        {"id": "tab-analytics", "label": "Analytics"},
    ],
    "framework_owner": [
        {"id": "tab-overview", "label": "Overview"},
        {"id": "tab-frameworks", "label": "Frameworks"},
        {"id": "tab-controls", "label": "Controls"},
        {"id": "tab-evidence", "label": "Evidence"},
        {"id": "tab-reports", "label": "Reports"},
    ],
}

_DEFAULT = {
    "display_name": "ECS User",
    "role_title": "Enterprise User",
    "role_short": "User",
    "platform_label": "ECS Platform",
}


def resolve_persona_context(role: str = "", user: str = "") -> dict:
    """Return sidebar branding, profile display, and dashboard tab config."""
    key = (role or "").strip().lower()
    base = dict(PERSONA_BY_ROLE.get(key, _DEFAULT))
    base["role_key"] = key
    base["user_login"] = user or ""
    base["sidebar_brand"] = base["platform_label"]
    base["sidebar_role_line"] = f"Role: {base['role_short']}"
    base["tabs"] = list(PERSONA_TABS.get(key, PERSONA_TABS.get("cio", [])))
    return base


def module_tabs(module_key: str) -> list[dict[str, str]]:
    return list(MODULE_TABS.get(module_key, MODULE_TABS.get("executive_overview", [])))


def role_title(role: str) -> str:
    return PERSONA_BY_ROLE.get((role or "").lower(), _DEFAULT)["role_title"]


def display_name(role: str) -> str:
    return PERSONA_BY_ROLE.get((role or "").lower(), _DEFAULT)["display_name"]
