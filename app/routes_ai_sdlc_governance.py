"""AI & SDLC Governance — additive routes (demo module, mock data only)."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app import ecs_state
from modules.shared.services.enterprise_context import enterprise_widgets_context
from modules.shared.services.role_permissions import permission_ctx
from modules.ai_sdlc.engines.ecs_sdlc_stage_dashboard import STAGE_KEY_TO_SLUG, resolve_stage_key
from modules.ai_sdlc.engines.ai_sdlc_governance_service import (
    control_tower_view,
    control_tower_tab_view,
    control_tower_readiness_drill,
    control_tower_framework_drill,
    control_tower_work_item,
    evidence_view,
    evidence_viewer_view,
    findings_view,
    landing_view,
    onboarding_view,
    onboarding_run_view,
    onboarding_framework_drill,
    onboarding_application_drill,
    posture_drill,
    posture_view,
    registry_drill,
    registry_view,
    reports_view,
    report_detail_view,
    review_view,
    sdlc_drill,
    sdlc_gates_view,
    sdlc_stage_view,
    stage_worklist_view,
    workflow_action,
)


from modules.shared.services.ecs_nav_framework import build_breadcrumb_trail, drill_footer_link


def _ctx(role: str, user: str, page_module: str, **extra):
    stage_label = extra.pop("stage_label", "")
    release_name = extra.pop("release_name", "")
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
        "breadcrumb_trail": build_breadcrumb_trail(
            page_module, role, user,
            stage_label=stage_label,
            release_name=release_name,
        ),
    }
    ctx.update(enterprise_widgets_context(role, page_module=page_module, user=user))
    ctx.update(permission_ctx(role))
    ctx.update(extra)
    return ctx


def _stage_query(role: str, user: str, release_id: str = "", **extra) -> str:
    from urllib.parse import urlencode
    params = {"role": role, "user": user}
    if release_id:
        params["release"] = release_id
    params.update({k: v for k, v in extra.items() if v})
    return urlencode(params)


_STAGE_ROUTE_MAP = {
    "requirements": ("requirement", "ai_sdlc_requirements"),
    "design": ("design", "ai_sdlc_design"),
    "development": ("development", "ai_sdlc_development"),
    "testing": ("testing", "ai_sdlc_testing"),
    "golive": ("go-live", "ai_sdlc_golive"),
}


def register_ai_sdlc_routes(app, templates):
    @app.get("/mvp/ai-sdlc", response_class=HTMLResponse)
    def mvp_ai_sdlc_home(request: Request, role: str = "cio", user: str = "CIO", notice: str = ""):
        ctx = _ctx(role, user, "ai_sdlc_home", landing_view=landing_view())
        return templates.TemplateResponse(request, "mvp_ai_sdlc_home.html", ctx)

    @app.get("/mvp/ai-sdlc/control-tower", response_class=HTMLResponse)
    def mvp_ai_sdlc_control_tower(request: Request, role: str = "cio", user: str = "CIO", notice: str = ""):
        ctx = _ctx(role, user, "ai_sdlc_control_tower", control_tower=control_tower_view())
        return templates.TemplateResponse(request, "mvp_ai_sdlc_control_tower.html", ctx)

    @app.get("/api/ai-sdlc/control-tower/tab/{tab_id}")
    def api_control_tower_tab(tab_id: str):
        payload = control_tower_tab_view(tab_id)
        if not payload:
            return JSONResponse({"ok": False, "error": "Unknown tab"})
        return JSONResponse({"ok": True, "tab_id": tab_id, "data": payload["data"]})

    @app.get("/api/ai-sdlc/control-tower/drill/readiness")
    def api_ct_readiness_drill(framework: str = "", stage: str = ""):
        if not framework or not stage:
            return JSONResponse({"ok": False, "error": "framework and stage required"})
        return JSONResponse({"ok": True, "data": control_tower_readiness_drill(framework, stage)})

    @app.get("/api/ai-sdlc/control-tower/drill/framework")
    def api_ct_framework_drill(framework: str = "", stage_key: str = ""):
        if not framework or not stage_key:
            return JSONResponse({"ok": False, "error": "framework and stage_key required"})
        return JSONResponse({"ok": True, "data": control_tower_framework_drill(framework, stage_key)})

    @app.get("/api/ai-sdlc/control-tower/work-item/{activity_id}")
    def api_ct_work_item(activity_id: str):
        item = control_tower_work_item(activity_id)
        if not item:
            return JSONResponse({"ok": False, "error": "Work item not found"})
        return JSONResponse({"ok": True, "data": item})

    @app.get("/mvp/ai-sdlc/onboarding", response_class=HTMLResponse)
    def mvp_ai_sdlc_onboarding(request: Request, role: str = "cio", user: str = "CIO", notice: str = ""):
        ctx = _ctx(role, user, "ai_sdlc_onboarding", onboarding_view=onboarding_view())
        return templates.TemplateResponse(request, "mvp_ai_sdlc_onboarding.html", ctx)

    @app.get("/api/ai-sdlc/onboarding/run")
    def api_onboarding_run():
        return JSONResponse({"ok": True, "data": onboarding_run_view()})

    @app.get("/api/ai-sdlc/onboarding/drill/framework")
    def api_onboarding_framework_drill(framework: str = ""):
        if not framework:
            return JSONResponse({"ok": False, "error": "framework required"})
        return JSONResponse({"ok": True, "data": onboarding_framework_drill(framework)})

    @app.get("/api/ai-sdlc/onboarding/drill/application")
    def api_onboarding_application_drill(application: str = ""):
        if not application:
            return JSONResponse({"ok": False, "error": "application required"})
        return JSONResponse({"ok": True, "data": onboarding_application_drill(application)})

    def _stage_worklist_page(stage_slug: str, role: str, user: str):
        mapped = _STAGE_ROUTE_MAP.get(stage_slug)
        if not mapped:
            return None
        stage_key, nav_module = mapped
        wl = stage_worklist_view(stage_key)
        return _ctx(role, user, nav_module, worklist=wl)

    for slug in _STAGE_ROUTE_MAP:
        def _make_handler(s=slug):
            @app.get(f"/mvp/ai-sdlc/{s}", response_class=HTMLResponse)
            def _handler(request: Request, role: str = "cio", user: str = "CIO", notice: str = ""):
                ctx = _stage_worklist_page(s, role, user)
                if ctx is None:
                    return RedirectResponse(f"/mvp/ai-sdlc?{_stage_query(role, user)}")
                return templates.TemplateResponse(request, "mvp_ai_sdlc_worklist.html", ctx)
            return _handler
        _make_handler()

    @app.get("/mvp/ai-sdlc/evidence", response_class=HTMLResponse)
    def mvp_ai_sdlc_evidence(request: Request, role: str = "cio", user: str = "CIO", notice: str = ""):
        ctx = _ctx(role, user, "ai_sdlc_evidence", worklist=evidence_view())
        return templates.TemplateResponse(request, "mvp_ai_sdlc_worklist.html", ctx)

    @app.get("/mvp/ai-sdlc/reports/{report_id}", response_class=HTMLResponse)
    def mvp_ai_sdlc_report_detail(
        request: Request, report_id: str, role: str = "cio", user: str = "CIO", notice: str = "",
    ):
        report = report_detail_view(report_id)
        if not report:
            return RedirectResponse(f"/mvp/ai-sdlc/reports?{_stage_query(role, user)}")
        ctx = _ctx(role, user, "ai_sdlc_reports", report=report, stage_label=report["title"])
        return templates.TemplateResponse(request, "mvp_ai_sdlc_report.html", ctx)

    @app.get("/mvp/ai-sdlc/findings", response_class=HTMLResponse)
    def mvp_ai_sdlc_findings(request: Request, role: str = "cio", user: str = "CIO", notice: str = ""):
        ctx = _ctx(role, user, "ai_sdlc_findings", worklist=findings_view())
        return templates.TemplateResponse(request, "mvp_ai_sdlc_worklist.html", ctx)

    @app.get("/mvp/ai-sdlc/reports", response_class=HTMLResponse)
    def mvp_ai_sdlc_reports(request: Request, role: str = "cio", user: str = "CIO", notice: str = ""):
        ctx = _ctx(role, user, "ai_sdlc_reports", reports_view=reports_view())
        return templates.TemplateResponse(request, "mvp_ai_sdlc_reports.html", ctx)

    @app.get("/mvp/ai-sdlc/evidence/view/{evidence_id}", response_class=HTMLResponse)
    def mvp_ai_sdlc_evidence_viewer(
        request: Request, evidence_id: str, role: str = "cio", user: str = "CIO", notice: str = "",
    ):
        ev = evidence_viewer_view(evidence_id)
        if not ev:
            return RedirectResponse(f"/mvp/ai-sdlc/evidence?{_stage_query(role, user)}")
        ctx = _ctx(role, user, "ai_sdlc_evidence", ev=ev, stage_label=ev.get("document_name", evidence_id))
        return templates.TemplateResponse(request, "mvp_ai_sdlc_evidence_viewer.html", ctx)

    @app.get("/api/ai-sdlc/workflow/review")
    def api_workflow_review(item_id: str = "", item_type: str = ""):
        data = review_view(item_id, item_type)
        if not data:
            return JSONResponse({"ok": False, "error": "Item not found"})
        return JSONResponse({"ok": True, "data": data})

    @app.post("/api/ai-sdlc/workflow/action")
    async def api_workflow_action(request: Request):
        body = await request.json()
        action = (body.get("action") or "").lower()
        actor = body.get("user") or "CIO"
        item_id = body.get("item_id") or ""
        item_type = body.get("item_type") or ""
        if action == "upload":
            result = workflow_action(
                "upload",
                item_id=item_id,
                item_type=item_type,
                actor=actor,
                file_name=body.get("file_name", ""),
                comments=body.get("comments", ""),
                application=body.get("application", ""),
                framework=body.get("framework", ""),
                domain=body.get("domain", ""),
                control_id=body.get("control_id", ""),
                stage=body.get("stage", ""),
                artifact_type=body.get("artifact_type", ""),
            )
        else:
            result = workflow_action(
                action,
                item_id=item_id,
                item_type=item_type,
                actor=actor,
                comments=body.get("comments", ""),
            )
        return JSONResponse(result)

    @app.get("/mvp/sdlc-gates", response_class=HTMLResponse)
    def mvp_sdlc_gates(request: Request, role: str = "cio", user: str = "CIO", release: str = "", notice: str = ""):
        qs = _stage_query(role, user, release)
        return RedirectResponse(f"/mvp/ai-sdlc?{qs}", status_code=302)

    @app.get("/sdlc/{stage_slug}", response_class=HTMLResponse)
    def sdlc_stage_workspace(
        request: Request,
        stage_slug: str,
        role: str = "cio",
        user: str = "CIO",
        release: str = "",
        notice: str = "",
    ):
        target = stage_slug if stage_slug in _STAGE_ROUTE_MAP else STAGE_KEY_TO_SLUG.get(resolve_stage_key(stage_slug) or "", stage_slug)
        if target not in _STAGE_ROUTE_MAP:
            return RedirectResponse(f"/mvp/ai-sdlc?{_stage_query(role, user, release or 'REL-2026-Q2-NB')}")
        qs = _stage_query(role, user, release or "REL-2026-Q2-NB")
        return RedirectResponse(f"/mvp/ai-sdlc/{target}?{qs}", status_code=302)

    @app.get("/mvp/sdlc-gates/{stage_key}", response_class=HTMLResponse)
    def mvp_sdlc_gate_stage(
        request: Request,
        stage_key: str,
        role: str = "cio",
        user: str = "CIO",
        release: str = "",
        notice: str = "",
    ):
        resolved = resolve_stage_key(stage_key) or stage_key
        slug = STAGE_KEY_TO_SLUG.get(resolved, stage_key)
        qs = _stage_query(role, user, release or "REL-2026-Q2-NB")
        tab = request.query_params.get("tab", "")
        if tab:
            qs += f"&tab={tab}"
        return RedirectResponse(f"/mvp/ai-sdlc/{slug}?{qs}", status_code=302)

    @app.get("/mvp/ai-governance", response_class=HTMLResponse)
    def mvp_ai_governance(request: Request, role: str = "cio", user: str = "CIO", notice: str = ""):
        view = posture_view()
        ctx = _ctx(role, user, "ai_governance", ai_view=view, module_view={"kpis": view["kpis"]})
        return templates.TemplateResponse(request, "mvp_ai_governance_posture.html", ctx)

    @app.get("/mvp/ai-registry", response_class=HTMLResponse)
    def mvp_ai_registry(request: Request, role: str = "cio", user: str = "CIO", notice: str = ""):
        view = registry_view()
        ctx = _ctx(role, user, "ai_registry", registry_view=view, module_view={"kpis": view["kpis"]})
        return templates.TemplateResponse(request, "mvp_ai_registry.html", ctx)

    @app.get("/api/ai-sdlc/workflow")
    def api_ai_sdlc_workflow(stage: str = ""):
        from modules.ai_sdlc.engines.ai_sdlc_workflow_engine import build_stage_worklist, build_evidence_collection
        if stage:
            return JSONResponse({"ok": True, "data": build_stage_worklist(stage)})
        return JSONResponse({"ok": True, "data": {"landing": landing_view(), "evidence": build_evidence_collection()}})

    @app.get("/api/ai-sdlc/posture/drill")
    def api_ai_posture_drill(metric: str = "", item_id: str = "", origin_module: str = ""):
        payload = posture_drill(metric, item_id)
        link = drill_footer_link("posture", metric, origin_module, item_id)
        if link:
            payload["footer_link"] = link
        return JSONResponse({"ok": True, "payload": payload})

    @app.get("/api/ai-sdlc/registry/drill")
    def api_ai_registry_drill(section: str = "", item_id: str = "", origin_module: str = ""):
        payload = registry_drill(section, item_id)
        link = drill_footer_link("registry", section, origin_module, item_id)
        if link:
            payload["footer_link"] = link
        return JSONResponse({"ok": True, "payload": payload})

    @app.get("/api/ai-sdlc/sdlc/drill")
    def api_sdlc_drill(
        metric: str = "", release: str = "", stage: str = "", item_id: str = "",
        page: int = 1, severity: str = "", search: str = "",
    ):
        return JSONResponse({
            "ok": True,
            "payload": sdlc_drill(metric, release, stage, item_id, page=page, severity=severity, search=search),
        })

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

    @app.get("/mvp/governance-quality", response_class=HTMLResponse)
    def mvp_governance_quality(request: Request, role: str = "cio", user: str = "CIO"):
        from modules.enterprise_grc.engines.ecs_governance_qa_engine import build_quality_dashboard
        dashboard = build_quality_dashboard()
        ctx = _ctx(role, user, "governance_quality", quality_dashboard=dashboard)
        return templates.TemplateResponse(request, "mvp_governance_quality.html", ctx)

    @app.get("/api/ai-sdlc/governance-quality")
    def api_governance_quality():
        from modules.enterprise_grc.engines.ecs_governance_qa_engine import build_quality_dashboard
        return JSONResponse({"ok": True, "data": build_quality_dashboard()})

    @app.get("/api/ai-sdlc/governance-scan")
    def api_governance_scan():
        from modules.enterprise_grc.engines.ecs_governance_qa_engine import self_heal_governance
        return JSONResponse({"ok": True, "data": self_heal_governance()})
