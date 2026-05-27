"""Shared template context for enterprise MVP pages."""

from app.audit_trail import (
    get_approval_history,
    get_audit_trail,
    get_notifications,
    get_recent_activity,
)
from app.demo_metrics import (
    HEALTH_METRICS,
    REUSE_METRICS,
    SCHEDULER_METRICS,
    enterprise_kpis,
    onboarding_progress,
    overdue_and_stale_alerts,
    role_dashboard_metrics,
)
from app.framework_catalog import catalog_stats
from app import ecs_state
from app.demo_metrics import display_framework_maturity
from app.analytics_module import completeness_report
from app.nav_counter_engine import build_nav_counters
from app.chatbot_engine import get_chat_history, get_chat_structured
from app.control_validation_engine import build_governance_analytics, build_control_validations, validation_summary
from app.governance_intelligence import build_contextual_trends, enrich_governance_analytics
from app.itpp_module import build_itpp_operational_view
from app.workflow_module import build_leadership_queue, work_queue_summary
from app.module_capabilities import get_module_capability, module_counter_rows
from app.module_workspace import build_module_workspace
from app.role_permissions import permission_ctx
from app.evidence_workflow_engine import build_workflow_context


def enterprise_widgets_context(role: str = "", page_module: str = "", framework: str = "", user: str = "", analytics_filters: dict | None = None):
    stats = ecs_state.build_evidence_analytics()
    nav_counters = build_nav_counters(role)
    ctx = {
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
        ctx["nav_module"] = page_module
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
    if role in ("cio", "vertical_head", "compliance_head", "functional_head"):
        ctx["leadership_queue"] = build_leadership_queue(role, limit=20)
        titles = {
            "cio": "CIO Executive Escalations & Approvals",
            "vertical_head": "Vertical Head — Pending Reviews",
            "compliance_head": "Compliance Head — Cross-Framework Gaps",
            "functional_head": "Functional Head — Unresolved Observations",
        }
        ctx["leadership_title"] = titles.get(role, "Executive Workflow Queue")
    if role:
        ctx.update(permission_ctx(role))
        ctx["evidence_workflow"] = build_workflow_context(role)
    return ctx
