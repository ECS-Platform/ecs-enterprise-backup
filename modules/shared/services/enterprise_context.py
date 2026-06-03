"""Shared template context for enterprise MVP pages."""

from modules.shared.services.audit_trail import (
    get_approval_history,
    get_audit_trail,
    get_notifications,
    get_recent_activity,
)
from modules.executive_overview.engines.demo_metrics import (
    HEALTH_METRICS,
    REUSE_METRICS,
    SCHEDULER_METRICS,
    enterprise_kpis,
    onboarding_progress,
    overdue_and_stale_alerts,
    role_dashboard_metrics,
)
from modules.frameworks.engines.framework_catalog import catalog_stats
from app import ecs_state
from modules.executive_overview.engines.demo_metrics import display_framework_maturity
from modules.governance.engines.analytics_module import completeness_report
from modules.shared.services.nav_counter_engine import build_nav_counters
from modules.shared.services.chatbot_engine import get_chat_history, get_chat_structured
from modules.frameworks.engines.control_validation_engine import build_governance_analytics, build_control_validations, validation_summary
from modules.governance.engines.governance_intelligence import build_contextual_trends, enrich_governance_analytics
from modules.frameworks.engines.itpp_module import build_itpp_operational_view
from modules.governance.engines.workflow_module import (
    build_leadership_queue,
    build_pending_approvals_queue,
    work_queue_summary,
)
from modules.shared.services.module_capabilities import get_module_capability, module_counter_rows
from modules.shared.services.module_workspace import build_module_workspace
from modules.shared.services.role_permissions import permission_ctx
from modules.shared.services.evidence_workflow_engine import build_workflow_context
from modules.shared.services.persona_display import resolve_persona_context


def enterprise_widgets_context(role: str = "", page_module: str = "", framework: str = "", user: str = "", analytics_filters: dict | None = None):
    stats = ecs_state.build_evidence_analytics()
    nav_counters = build_nav_counters(role)
    ctx = {
        "nav_module": page_module or "",
        "catalog_stats": catalog_stats(),
        "role_metrics": role_dashboard_metrics(role) if role else {},
        "notifications": get_notifications(),
        "recent_activity": get_recent_activity(),
        "approval_history": get_approval_history(10),
        "audit_trail": get_audit_trail(15),
        "kpis": enterprise_kpis(),
        "health_metrics": HEALTH_METRICS,
        "reuse_metrics": REUSE_METRICS,
        "scheduler_metrics": SCHEDULER_METRICS,
        "framework_maturity": display_framework_maturity(stats["framework_stats"]),
        "alerts": overdue_and_stale_alerts(),
        "onboarding_progress": onboarding_progress(),
        "completeness": completeness_report(),
        "nav_counters": nav_counters,
        "work_queue_summary": work_queue_summary(),
        "show_framework_workflow": False,
        "chat_history": get_chat_history(user, role) if user and role else [],
        "chat_response_html": get_chat_structured(user, role) if user and role else "",
        "governance_analytics": enrich_governance_analytics(build_governance_analytics(), build_contextual_trends(analytics_filters)),
    }
    if page_module:
        ctx["module_view"] = get_module_capability(page_module, role, analytics_filters)
        ctx["workspace"] = build_module_workspace(page_module, role)
        ctx["show_mvp_notifications"] = True
    if framework:
        ctx["control_validations"] = build_control_validations(framework, limit=24)
        ctx["validation_summary"] = validation_summary(framework)
        if framework == "ITPP":
            ctx["itpp_operational"] = build_itpp_operational_view(role)
        # Workflow queue only inside dedicated drill-down tabs — not on framework landing
        ctx["show_framework_workflow"] = False
    if role in ("cio", "vertical_head", "compliance_head", "compliance_officer", "functional_head", "security_officer"):
        ctx["leadership_queue"] = build_leadership_queue(role, limit=20)
        titles = {
            "cio": "CIO Executive Escalations & Approvals",
            "vertical_head": "Vertical Head — Pending Reviews",
            "compliance_head": "Compliance Head — Cross-Framework Gaps",
            "functional_head": "Functional Head — Unresolved Observations",
        }
        ctx["leadership_title"] = titles.get(role, "Executive Workflow Queue")
    if role in ("cio", "vertical_head", "compliance_head", "compliance_officer", "auditor", "security_officer"):
        ctx["pending_approvals_queue"] = build_pending_approvals_queue(role, limit=25)
        pending_titles = {
            "cio": "CIO Pending Approvals",
            "vertical_head": "Vertical Head — Approval Queue",
            "compliance_head": "Compliance — Pending Sign-offs",
            "compliance_officer": "Compliance — Pending Sign-offs",
            "security_officer": "Security — Pending Sign-offs",
            "auditor": "Auditor — Evidence Pending Approval",
        }
        ctx["pending_approvals_title"] = pending_titles.get(role, "Pending Approvals")
    if role:
        ctx.update(permission_ctx(role))
        ctx["persona"] = resolve_persona_context(role, user)
        if framework:
            from modules.frameworks.engines.framework_workflow_engine import build_framework_workflow_context
            ctx["evidence_workflow"] = build_framework_workflow_context(framework, role)
        else:
            ctx["evidence_workflow"] = build_workflow_context(role)
    elif user:
        ctx["persona"] = resolve_persona_context("", user)
    return ctx
