"""Chatbot deep-link builder — role-aware MVP URLs with filter context."""

from __future__ import annotations

from urllib.parse import quote

MODULE_PATHS = {
    "evidence_health": "/mvp/evidence-health",
    "evidence_approval": "/mvp/evidence-approval",
    "exceptions": "/mvp/exceptions",
    "exception_governance": "/mvp/exception-governance",
    "search": "/mvp/search",
    "audit_prep": "/mvp/audit-prep",
    "completeness": "/mvp/completeness",
    "lifecycle": "/mvp/lifecycle",
    "reports": "/mvp/reports",
    "integrations_hub": "/mvp/integrations-hub",
    "integrations": "/mvp/integrations",
    "governance_analytics": "/mvp/governance-analytics",
    "enterprise": "/mvp/enterprise",
    "risk_register": "/mvp/risk-register",
    "reuse": "/mvp/reuse",
    "comparison": "/mvp/comparison",
    "pan_india": "/mvp/pan-india",
    "correlation": "/mvp/correlation",
    "scheduler": "/mvp/scheduler",
    "upload": "/mvp/upload",
    "onboarding": "/mvp/onboarding",
    "framework_admin": "/mvp/framework-admin",
    "trends": "/mvp/trends",
    "cmdb": "/mvp/cmdb",
    "regulatory": "/mvp/regulatory",
    "heatmaps": "/mvp/heatmaps",
}

ROLE_DASHBOARDS = {
    "cio": "/dashboard/cio",
    "vertical_head": "/dashboard/vertical-head",
    "compliance_head": "/dashboard/compliance-head",
    "compliance_officer": "/dashboard/compliance-head",
    "functional_head": "/dashboard/functional-head",
    "admin": "/dashboard",
    "owner": "/dashboard",
    "auditor": "/dashboard",
}


def mvp_url(
    module: str,
    role: str,
    user: str,
    *,
    framework: str = "",
    application: str = "",
    status: str = "",
    filter_issue: str = "",
    highlight: str = "",
    observation_id: str = "",
    evidence_id: str = "",
    tab: str = "",
    extra: dict | None = None,
) -> str:
    """Build a deep link into an MVP module preserving role and filters."""
    path = MODULE_PATHS.get(module, f"/mvp/{module.replace('_', '-')}")
    params: list[str] = [f"role={quote(role)}", f"user={quote(user)}"]
    if framework and framework not in ("Enterprise-wide", "All Frameworks"):
        params.append(f"framework={quote(framework)}")
    if application and application not in ("All Applications", ""):
        params.append(f"application={quote(application)}")
    if status:
        params.append(f"status={quote(status)}")
    if filter_issue:
        params.append(f"filter_issue={quote(filter_issue)}")
    if highlight:
        params.append(f"highlight={quote(highlight)}")
    if observation_id:
        params.append(f"observation_id={quote(observation_id)}")
    if evidence_id:
        params.append(f"evidence_id={quote(evidence_id)}")
    if tab:
        params.append(f"tab={quote(tab)}")
    if extra:
        for k, v in extra.items():
            if v:
                params.append(f"{k}={quote(str(v))}")
    return f"{path}?{'&'.join(params)}"


def framework_url(framework: str, role: str, user: str) -> str:
    slug = framework.replace(" ", "%20")
    return f"/framework/{slug}?role={quote(role)}&user={quote(user)}"


def link_html(label: str, url: str, btn_class: str = "btn-link btn-sm p-0") -> str:
    safe_label = label.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")
    safe_url = url.replace('"', "&quot;")
    return f'<a href="{safe_url}" class="{btn_class}">{safe_label}</a>'


def evidence_health_link(
    role: str,
    user: str,
    *,
    filter_issue: str = "",
    framework: str = "",
    application: str = "",
    evidence_id: str = "",
    label: str = "Open Evidence Health",
) -> str:
    url = mvp_url(
        "evidence_health", role, user,
        framework=framework, application=application,
        filter_issue=filter_issue, highlight=evidence_id,
    )
    return link_html(label, url, "btn btn-outline-primary btn-sm")


def action_link(action: str, role: str, user: str, ctx: dict | None = None) -> str:
    """Map contextual chatbot action to a working deep link."""
    ctx = ctx or {}
    fw = ctx.get("framework", "")
    app = ctx.get("application", "")
    mapping = {
        "view_evidence": mvp_url("evidence_health", role, user, framework=fw, application=app, tab="queue"),
        "open_observation": mvp_url("search", role, user, framework=fw, application=app, tab="findings"),
        "review_connector": mvp_url("integrations_hub", role, user),
        "raise_exception": mvp_url("exceptions", role, user, framework=fw, application=app),
        "trigger_remediation": mvp_url("audit_prep", role, user, framework=fw, application=app, tab="gaps"),
        "notify_owner": mvp_url("onboarding", role, user, application=app),
        "assign_owner": f"/mvp/workflow/assign-owner?role={quote(role)}&user={quote(user)}&framework={quote(fw)}&return_module=audit_prep",
        "request_reupload": mvp_url("audit_prep", role, user, framework=fw, application=app, tab="queue"),
        "escalate_observation": mvp_url("audit_prep", role, user, framework=fw, application=app, tab="gaps"),
        "evidence_approval": mvp_url("evidence_approval", role, user, framework=fw, application=app),
        "upload_missing": mvp_url("completeness", role, user, framework=fw, application=app, tab="uploads"),
    }
    if action == "upload_missing" and role == "auditor":
        return mapping["request_reupload"]
    return mapping.get(action, mvp_url("enterprise", role, user))
