"""ECS navigation framework — breadcrumbs, module labels, drill link resolution."""

from __future__ import annotations

from typing import Any

_MODULE_GROUPS: dict[str, str] = {
    "ai_sdlc_home": "AI SDLC Governance",
    "ai_sdlc_control_tower": "AI SDLC Governance",
    "ai_sdlc_onboarding": "AI SDLC Governance",
    "ai_sdlc_requirements": "AI SDLC Governance",
    "ai_sdlc_design": "AI SDLC Governance",
    "ai_sdlc_development": "AI SDLC Governance",
    "ai_sdlc_testing": "AI SDLC Governance",
    "ai_sdlc_golive": "AI SDLC Governance",
    "ai_sdlc_evidence": "AI SDLC Governance",
    "ai_sdlc_findings": "AI SDLC Governance",
    "ai_sdlc_reports": "AI SDLC Governance",
    "ai_governance": "AI SDLC Governance",
    "sdlc_gates": "AI SDLC Governance",
    "ai_registry": "AI SDLC Governance",
    "governance_quality": "AI SDLC Governance",
    "audit_prep": "Governance",
    "evidence_health": "Governance",
    "reuse": "Governance",
    "lifecycle": "Governance",
    "completeness": "Governance",
    "comparison": "Governance",
    "search": "Governance",
    "evidence_approval": "Governance",
    "enterprise": "Executive Overview",
    "pan_india": "Executive Overview",
    "reports": "Executive Overview",
    "trends": "Executive Overview",
    "demo_overview": "Executive Overview",
    "risk_register": "Enterprise GRC",
    "exceptions_td": "Enterprise GRC",
    "exception_governance": "Enterprise GRC",
    "cmdb": "Enterprise GRC",
    "regulatory_mapping": "Enterprise GRC",
    "executive_heatmaps": "Enterprise GRC",
    "correlation": "Enterprise GRC",
    "governance_analytics": "Enterprise GRC",
}

_SCREEN_LABELS: dict[str, str] = {
    "ai_sdlc_home": "AI SDLC Governance",
    "ai_sdlc_control_tower": "Control Tower",
    "ai_sdlc_onboarding": "Application Onboarding",
    "ai_sdlc_requirements": "Requirements",
    "ai_sdlc_design": "Design",
    "ai_sdlc_development": "Development",
    "ai_sdlc_testing": "Testing",
    "ai_sdlc_golive": "Go-Live",
    "ai_sdlc_evidence": "Evidence Collection",
    "ai_sdlc_findings": "Findings & Remediation",
    "ai_sdlc_reports": "Reports",
    "ai_governance": "AI Governance Posture",
    "sdlc_gates": "SDLC Compliance Gates",
    "ai_registry": "Model & Prompt Registry",
    "governance_quality": "Governance Quality",
    "audit_prep": "Audit Prep",
    "evidence_health": "Evidence Health",
    "reuse": "Evidence Reuse",
    "lifecycle": "Lifecycle",
    "completeness": "Completeness",
    "comparison": "App Comparison",
    "search": "Search",
    "evidence_approval": "Evidence Approval Analytics",
    "enterprise": "Enterprise",
    "pan_india": "Pan India",
    "reports": "Reports",
    "trends": "Trends",
    "demo_overview": "Demo Overview",
    "risk_register": "Risk Register",
    "exceptions_td": "Exceptions / TD",
    "exception_governance": "Exception Governance",
    "cmdb": "CMDB / Assets",
    "regulatory_mapping": "Regulatory Mapping",
    "executive_heatmaps": "Executive Heatmaps",
    "correlation": "Cross-Tool Correlation",
    "governance_analytics": "Governance Analytics",
}

_HOME_BY_ROLE: dict[str, str] = {
    "cio": "/dashboard/cio",
    "owner": "/dashboard",
    "auditor": "/dashboard",
    "vertical_head": "/dashboard/vertical-head",
    "compliance_head": "/dashboard/compliance-head",
    "compliance_officer": "/dashboard/compliance-head",
    "functional_head": "/dashboard/functional-head",
}


def home_href(role: str) -> str:
    return _HOME_BY_ROLE.get(role, "/dashboard/cio")


def build_breadcrumb_trail(
    page_module: str,
    role: str = "cio",
    user: str = "CIO",
    *,
    detail_label: str = "",
    stage_label: str = "",
    release_name: str = "",
) -> list[dict[str, str]]:
    """Build Home > Module > Screen > Detail breadcrumb chain."""
    q = f"role={role}&user={user}"
    crumbs: list[dict[str, str]] = [
        {"label": "Home", "href": f"{home_href(role)}?{q}"},
    ]
    group = _MODULE_GROUPS.get(page_module, "ECS")
    group_href = _group_href(page_module, q)
    if group_href:
        crumbs.append({"label": group, "href": group_href})
    else:
        crumbs.append({"label": group})

    screen = _SCREEN_LABELS.get(page_module, page_module.replace("_", " ").title())
    screen_href = _screen_href(page_module, q)
    if screen_href and not detail_label and not stage_label:
        crumbs.append({"label": screen})
    elif screen_href:
        crumbs.append({"label": screen, "href": screen_href})
    else:
        crumbs.append({"label": screen})

    if stage_label:
        crumbs.append({"label": stage_label})
    elif release_name and page_module == "sdlc_gates":
        crumbs.append({"label": release_name})
    if detail_label:
        crumbs.append({"label": detail_label})

    return crumbs


def _group_href(page_module: str, q: str) -> str:
    if page_module.startswith("ai_sdlc") or page_module in ("ai_governance", "sdlc_gates", "ai_registry", "governance_quality"):
        return f"/mvp/ai-sdlc?{q}"
    if page_module in _MODULE_GROUPS and _MODULE_GROUPS[page_module] == "Governance":
        return f"/mvp/audit-prep?{q}"
    if page_module in _MODULE_GROUPS and _MODULE_GROUPS[page_module] == "Enterprise GRC":
        return f"/mvp/risk-register?{q}"
    if page_module in _MODULE_GROUPS and _MODULE_GROUPS[page_module] == "Executive Overview":
        return f"/mvp/enterprise?{q}"
    return ""


def _screen_href(page_module: str, q: str) -> str:
    routes = {
        "ai_sdlc_home": f"/mvp/ai-sdlc?{q}",
        "ai_sdlc_control_tower": f"/mvp/ai-sdlc/control-tower?{q}",
        "ai_sdlc_onboarding": f"/mvp/ai-sdlc/onboarding?{q}",
        "ai_sdlc_requirements": f"/mvp/ai-sdlc/requirements?{q}",
        "ai_sdlc_design": f"/mvp/ai-sdlc/design?{q}",
        "ai_sdlc_development": f"/mvp/ai-sdlc/development?{q}",
        "ai_sdlc_testing": f"/mvp/ai-sdlc/testing?{q}",
        "ai_sdlc_golive": f"/mvp/ai-sdlc/golive?{q}",
        "ai_sdlc_evidence": f"/mvp/ai-sdlc/evidence?{q}",
        "ai_sdlc_findings": f"/mvp/ai-sdlc/findings?{q}",
        "ai_sdlc_reports": f"/mvp/ai-sdlc/reports?{q}",
        "ai_governance": f"/mvp/ai-governance?{q}",
        "sdlc_gates": f"/mvp/ai-sdlc?{q}",
        "ai_registry": f"/mvp/ai-registry?{q}",
        "governance_quality": f"/mvp/governance-quality?{q}",
        "audit_prep": f"/mvp/audit-prep?{q}",
        "evidence_health": f"/mvp/evidence-health?{q}",
        "reuse": f"/mvp/reuse?{q}",
        "enterprise": f"/mvp/enterprise?{q}",
        "risk_register": f"/mvp/risk-register?{q}",
    }
    return routes.get(page_module, "")


def drill_footer_link(
    kind: str,
    metric: str,
    page_module: str,
    item_id: str = "",
) -> dict[str, str] | None:
    """Context-aware footer link for drill modals — avoids routing loops."""
    if metric in ("models", "models_approved"):
        if kind == "posture" and page_module == "ai_governance":
            return {"href": "/mvp/ai-registry", "text": "Open Model Registry"}
        if kind == "registry" and page_module == "ai_registry":
            if item_id:
                return {"href": f"/mvp/ai-registry", "text": "View in Model Registry"}
            return None
        if kind == "registry":
            return {"href": "/mvp/ai-governance", "text": "Open AI Governance Posture"}
        return {"href": "/mvp/ai-registry", "text": "Open Model Registry"}

    if metric in ("prompts", "prompts_pending") and kind == "posture" and page_module == "ai_governance":
        return {"href": "/mvp/ai-registry", "text": "Open Prompt Registry"}

    if metric == "inventory" and kind == "posture":
        return {"href": "/mvp/ai-registry", "text": "Open Model & Prompt Registry"}

    if metric == "application" and kind == "posture":
        return {"href": "/mvp/ai-registry", "text": "Open Model & Prompt Registry"}

    if kind == "registry" and page_module != "ai_registry":
        return {"href": "/mvp/ai-registry", "text": "Open Model & Prompt Registry"}

    if kind == "posture" and page_module != "ai_governance":
        return {"href": "/mvp/ai-governance", "text": "Open AI Governance Posture"}

    if kind == "sdlc" and page_module != "ai_sdlc_home" and not page_module.startswith("ai_sdlc"):
        return {"href": "/mvp/ai-sdlc", "text": "Open AI SDLC Governance"}

    return None
