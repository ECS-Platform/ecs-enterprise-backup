"""Navigation aggregator routes — additive UX consolidation (no logic changes).

These routes render a lightweight "horizontal tabs" shell (mvp_tab_aggregator.html)
that groups several EXISTING ECS pages under one left-nav item. Each tab embeds the
existing page (via iframe with ?embed=1) so all underlying routes, templates, and
behaviour are reused unchanged and remain reachable by their original direct URLs.

Added groups (see docs/archive/ECS_NAVIGATION_REGROUPING_REPORT.md):
  * Administration -> Evidence               (/mvp/admin/evidence)
  * Administration -> Application Management  (/mvp/admin/application-management)
  * AI SDLC Governance -> Phases             (/mvp/ai-sdlc/phases)

No authentication, RBAC, benchmark, or business logic is modified here.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import HTMLResponse

from app import ecs_state
from modules.shared.services.enterprise_context import enterprise_widgets_context


def _agg_ctx(role: str, user: str, page_module: str, agg: dict, notice: str = "") -> dict:
    ctx = {
        "frameworks": ecs_state.frameworks.keys(),
        "role": role,
        "user": user,
        "notice": notice,
        "scheduler_data": ecs_state.scheduler_data,
        "rejected_controls": ecs_state.rejected_controls,
        "applications": ecs_state.onboarded_applications,
        "agg": agg,
    }
    ctx.update(enterprise_widgets_context(role, page_module=page_module, user=user))
    try:
        from app.auth.demo import demo_mode

        ctx["demo_mode"] = demo_mode()
    except Exception:  # noqa: BLE001
        ctx["demo_mode"] = False
    return ctx


def register_nav_aggregator_routes(app, templates):
    # ---- Administration -> Evidence --------------------------------------------
    @app.get("/mvp/admin/evidence", response_class=HTMLResponse)
    def mvp_admin_evidence(request: Request, role: str = "owner", user: str = "User", notice: str = ""):
        agg = {
            "title": "Evidence",
            "subtitle": "Scheduling, bulk upload, reuse, and completeness of evidence.",
            "badge": "Administration",
            "tabs": [
                {"id": "scheduler", "label": "Scheduler", "url": "/mvp/scheduler"},
                {"id": "upload", "label": "Bulk Upload", "url": "/mvp/upload"},
                {"id": "reuse", "label": "Evidence Reuse", "url": "/mvp/reuse"},
                {"id": "completeness", "label": "Completeness", "url": "/mvp/completeness"},
            ],
        }
        ctx = _agg_ctx(role, user, "admin_evidence", agg, notice)
        return templates.TemplateResponse(request, "mvp_tab_aggregator.html", ctx)

    # ---- Administration -> Application Management -------------------------------
    @app.get("/mvp/admin/application-management", response_class=HTMLResponse)
    def mvp_admin_application_management(request: Request, role: str = "owner", user: str = "User", notice: str = ""):
        agg = {
            "title": "Application Management",
            "subtitle": "Onboard applications, review the inventory, and compare applications.",
            "badge": "Administration",
            "tabs": [
                {"id": "onboarding", "label": "Application Onboarding", "url": "/mvp/onboarding"},
                {"id": "inventory", "label": "Application Inventory", "url": "/mvp/platform/inventory"},
                {"id": "comparison", "label": "App Comparison", "url": "/mvp/comparison"},
            ],
        }
        ctx = _agg_ctx(role, user, "admin_application_management", agg, notice)
        return templates.TemplateResponse(request, "mvp_tab_aggregator.html", ctx)

    # ---- AI SDLC Governance -> Phases ------------------------------------------
    @app.get("/mvp/ai-sdlc/phases", response_class=HTMLResponse)
    def mvp_ai_sdlc_phases(request: Request, role: str = "cio", user: str = "CIO", notice: str = ""):
        agg = {
            "title": "AI SDLC Phases",
            "subtitle": "Stage-wise governance workspaces: Requirements through Go-Live.",
            "badge": "AI SDLC Governance",
            "tabs": [
                {"id": "requirements", "label": "Requirements", "url": "/mvp/ai-sdlc/requirements"},
                {"id": "design", "label": "Design", "url": "/mvp/ai-sdlc/design"},
                {"id": "development", "label": "Development", "url": "/mvp/ai-sdlc/development"},
                {"id": "testing", "label": "Testing", "url": "/mvp/ai-sdlc/testing"},
                {"id": "golive", "label": "Go-Live", "url": "/mvp/ai-sdlc/golive"},
            ],
        }
        ctx = _agg_ctx(role, user, "ai_sdlc_phases", agg, notice)
        return templates.TemplateResponse(request, "mvp_tab_aggregator.html", ctx)
