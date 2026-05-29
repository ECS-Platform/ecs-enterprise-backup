"""AI & SDLC Governance — additive routes (demo module, mock data only)."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse

from app import ecs_state
from app.enterprise_context import enterprise_widgets_context
from app.role_permissions import permission_ctx
from app.ai_sdlc_governance_service import (
    posture_drill,
    posture_view,
    registry_drill,
    registry_view,
    sdlc_drill,
    sdlc_gates_view,
    sdlc_stage_view,
)


def _ctx(role: str, user: str, page_module: str, **extra):
    ctx = {
        "frameworks": ecs_state.frameworks.keys(),
        "role": role,
        "user": user,
        "response": extra.pop("response", ""),
        "notice": extra.pop("notice", ""),
        "scheduler_data": ecs_state.scheduler_data,
        "rejected_controls": ecs_state.rejected_controls,
        "applications": ecs_state.onboarded_applications,
        "nav_module": page_module,
    }
    ctx.update(enterprise_widgets_context(role, page_module=page_module, user=user))
    ctx.update(permission_ctx(role))
    ctx.update(extra)
    return ctx


def register_ai_sdlc_routes(app, templates):
    @app.get("/mvp/ai-governance", response_class=HTMLResponse)
    def mvp_ai_governance(request: Request, role: str = "cio", user: str = "CIO", notice: str = ""):
        view = posture_view()
        ctx = _ctx(role, user, "ai_governance", ai_view=view, module_view={"kpis": view["kpis"]})
        return templates.TemplateResponse(request, "mvp_ai_governance_posture.html", ctx)

    @app.get("/mvp/sdlc-gates", response_class=HTMLResponse)
    def mvp_sdlc_gates(request: Request, role: str = "cio", user: str = "CIO", release: str = "", notice: str = ""):
        view = sdlc_gates_view(release)
        ctx = _ctx(role, user, "sdlc_gates", sdlc_view=view, module_view={"kpis": view["kpis"]}, release_id=release or view["release"]["id"])
        return templates.TemplateResponse(request, "mvp_sdlc_gates.html", ctx)

    @app.get("/mvp/sdlc-gates/{stage_key}", response_class=HTMLResponse)
    def mvp_sdlc_gate_stage(request: Request, stage_key: str, role: str = "cio", user: str = "CIO", release: str = "", notice: str = ""):
        view = sdlc_stage_view(stage_key, release)
        ctx = _ctx(role, user, "sdlc_gates", stage_view=view, release_id=release or view["release"]["id"])
        return templates.TemplateResponse(request, "mvp_sdlc_gate_stage.html", ctx)

    @app.get("/mvp/ai-registry", response_class=HTMLResponse)
    def mvp_ai_registry(request: Request, role: str = "cio", user: str = "CIO", notice: str = ""):
        view = registry_view()
        ctx = _ctx(role, user, "ai_registry", registry_view=view, module_view={"kpis": view["kpis"]})
        return templates.TemplateResponse(request, "mvp_ai_registry.html", ctx)

    @app.get("/api/ai-sdlc/posture/drill")
    def api_ai_posture_drill(metric: str = "", item_id: str = ""):
        return JSONResponse({"ok": True, "payload": posture_drill(metric, item_id)})

    @app.get("/api/ai-sdlc/registry/drill")
    def api_ai_registry_drill(section: str = "", item_id: str = ""):
        return JSONResponse({"ok": True, "payload": registry_drill(section, item_id)})

    @app.get("/api/ai-sdlc/sdlc/drill")
    def api_sdlc_drill(metric: str = "", release: str = "", stage: str = "", item_id: str = ""):
        return JSONResponse({"ok": True, "payload": sdlc_drill(metric, release, stage, item_id)})

    @app.get("/api/ai-sdlc/sdlc/stage")
    def api_sdlc_stage(stage: str = "", release: str = ""):
        if not stage:
            return JSONResponse({"ok": False, "errors": ["stage required"]})
        return JSONResponse({"ok": True, "data": sdlc_stage_view(stage, release)})

    @app.get("/api/ai-sdlc/posture")
    def api_ai_posture():
        return JSONResponse({"ok": True, "data": posture_view()})

    @app.get("/api/ai-sdlc/sdlc")
    def api_sdlc_gates(release: str = ""):
        return JSONResponse({"ok": True, "data": sdlc_gates_view(release)})

    @app.get("/api/ai-sdlc/registry")
    def api_ai_registry():
        return JSONResponse({"ok": True, "data": registry_view()})
