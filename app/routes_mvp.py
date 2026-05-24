"""Additive MVP routes — does not replace existing ECS routes."""

from urllib.parse import quote

from fastapi import File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse

from app import ecs_state
from app.analytics_module import (
    application_comparison,
    audit_preparation_checklist,
    completeness_report,
    compliance_trends,
    enterprise_dashboard,
    lifecycle_timeline,
)
from app.evidence_repository import (
    evidence_repository,
    get_health_dashboard,
    get_reuse_graph,
    get_summaries,
    register_upload,
    upload_tracker,
)
from app.integrations_module import get_integration_dashboard, simulate_sync
from app.reporting_module import generate_report_content, list_reports
from app.scheduler_module import get_scheduler_dashboard, run_scheduled_pull
from app.search_module import build_search_discovery, search_evidences
from app.enterprise_context import enterprise_widgets_context
from app.demo_metrics import REUSE_METRICS


def _base_ctx(role: str, user: str, response: str = "", notice: str = "", page_module: str = ""):
    ctx = {
        "frameworks": ecs_state.frameworks.keys(),
        "role": role,
        "user": user,
        "response": response,
        "notice": notice,
        "scheduler_data": ecs_state.scheduler_data,
        "rejected_controls": ecs_state.rejected_controls,
        "applications": ecs_state.onboarded_applications,
    }
    ctx.update(enterprise_widgets_context(role, page_module=page_module, user=user))
    ctx["module_view"] = ctx.get("module_view") or {}
    ctx["reuse_metrics"] = REUSE_METRICS
    return ctx


def _module_redirect(module: str, role: str, user: str, notice: str) -> RedirectResponse:
    paths = {
        "scheduler": "/mvp/scheduler",
        "upload": "/mvp/upload",
        "evidence_health": "/mvp/evidence-health",
        "search": "/mvp/search",
        "completeness": "/mvp/completeness",
        "reuse": "/mvp/reuse",
        "lifecycle": "/mvp/lifecycle",
        "comparison": "/mvp/comparison",
        "integrations": "/mvp/integrations",
        "enterprise": "/mvp/enterprise",
        "pan_india": "/mvp/pan-india",
        "reports": "/mvp/reports",
        "audit_prep": "/mvp/audit-prep",
        "trends": "/mvp/trends",
        "onboarding": "/mvp/onboarding",
        "risk_register": "/mvp/risk-register",
        "exceptions_td": "/mvp/exceptions",
        "cmdb": "/mvp/cmdb",
        "regulatory_mapping": "/mvp/regulatory",
        "executive_heatmaps": "/mvp/heatmaps",
        "integrations_hub": "/mvp/integrations-hub",
        "correlation": "/mvp/correlation",
        "governance_analytics": "/mvp/governance-analytics",
    }
    base = paths.get(module, "/dashboard")
    return RedirectResponse(url=f"{base}?role={role}&user={user}&notice={quote(notice)}", status_code=303)


def chat_redirect(role: str, user: str, response: str, framework_name: str = ""):
    encoded = quote(response)
    routes = {
        "cio": f"/dashboard/cio?role={role}&user={user}&response={encoded}",
        "vertical_head": f"/dashboard/vertical-head?role={role}&user={user}&response={encoded}",
        "compliance_head": f"/dashboard/compliance-head?role={role}&user={user}&response={encoded}",
        "compliance_officer": f"/dashboard/compliance-head?role=compliance_head&user={user}&response={encoded}",
        "functional_head": f"/dashboard/functional-head?role={role}&user={user}&response={encoded}",
    }
    if role in routes:
        return RedirectResponse(url=routes[role], status_code=303)
    if framework_name:
        return RedirectResponse(
            url=f"/framework/{framework_name}?role={role}&user={user}&response={encoded}",
            status_code=303,
        )
    return RedirectResponse(
        url=f"/dashboard?role={role}&user={user}&response={encoded}",
        status_code=303,
    )


def register_mvp_routes(app, templates):
    @app.get("/dashboard/vertical-head", response_class=HTMLResponse)
    def vertical_head_dashboard(request: Request, role: str = "vertical_head", user: str = "VerticalHead", response: str = ""):
        ctx = _base_ctx(role, user, response)
        ctx["analytics"] = ecs_state.build_evidence_analytics()
        ctx["enterprise"] = enterprise_dashboard()
        ctx["comparison"] = application_comparison()
        return templates.TemplateResponse(request, "dashboard_vertical_head.html", ctx)

    @app.get("/dashboard/compliance-head", response_class=HTMLResponse)
    def compliance_head_dashboard(request: Request, role: str = "compliance_head", user: str = "ComplianceHead", response: str = ""):
        ctx = _base_ctx(role, user, response)
        ctx["analytics"] = ecs_state.build_evidence_analytics()
        ctx["completeness"] = completeness_report()
        ctx["enterprise"] = enterprise_dashboard()
        return templates.TemplateResponse(request, "dashboard_compliance_head.html", ctx)

    @app.get("/dashboard/functional-head", response_class=HTMLResponse)
    def functional_head_dashboard(request: Request, role: str = "functional_head", user: str = "FunctionalHead", response: str = ""):
        ctx = _base_ctx(role, user, response)
        ctx["analytics"] = ecs_state.build_evidence_analytics()
        ctx["enterprise"] = enterprise_dashboard()
        ctx["comparison"] = application_comparison()
        ctx["onboarding"] = ctx["onboarding_progress"]
        return templates.TemplateResponse(request, "dashboard_functional_head.html", ctx)

    @app.get("/mvp/scheduler", response_class=HTMLResponse)
    def mvp_scheduler(request: Request, role: str = "owner", user: str = "User", response: str = "", notice: str = ""):
        ctx = _base_ctx(role, user, response, notice, page_module="scheduler")
        ctx["scheduler"] = get_scheduler_dashboard()
        return templates.TemplateResponse(request, "mvp_scheduler.html", ctx)

    @app.post("/mvp/scheduler/run")
    def mvp_scheduler_run(role: str = Form(...), user: str = Form(...)):
        result = run_scheduled_pull()
        notice = quote(f"Scheduler pull complete at {result['timestamp']}. Added {result['added']} items.")
        return RedirectResponse(url=f"/mvp/scheduler?role={role}&user={user}&notice={notice}", status_code=303)

    @app.get("/mvp/upload", response_class=HTMLResponse)
    def mvp_upload_page(request: Request, role: str = "owner", user: str = "User", response: str = "", notice: str = ""):
        ctx = _base_ctx(role, user, response, notice, page_module="upload")
        ctx["uploads"] = list(reversed(evidence_repository[-15:]))
        ctx["tracker"] = list(reversed(upload_tracker[-10:]))
        return templates.TemplateResponse(request, "mvp_bulk_upload.html", ctx)

    @app.post("/mvp/upload/bulk")
    async def mvp_bulk_upload(
        role: str = Form(...),
        user: str = Form(...),
        framework: str = Form(""),
        application: str = Form("Net Banking"),
        files: list[UploadFile] = File(...),
    ):
        count = 0
        for f in files:
            content = await f.read()
            register_upload(f.filename, content, user, framework, application)
            count += 1
        notice = quote(f"Bulk upload complete: {count} file(s) with metadata tags applied.")
        return RedirectResponse(url=f"/mvp/upload?role={role}&user={user}&notice={notice}", status_code=303)

    @app.get("/mvp/evidence-health", response_class=HTMLResponse)
    def mvp_evidence_health(request: Request, role: str = "owner", user: str = "User", response: str = ""):
        ctx = _base_ctx(role, user, response, page_module="evidence_health")
        ctx["health"] = get_health_dashboard()
        ctx["summaries"] = get_summaries()
        return templates.TemplateResponse(request, "mvp_evidence_health.html", ctx)

    @app.get("/mvp/search", response_class=HTMLResponse)
    def mvp_search(
        request: Request,
        role: str = "owner",
        user: str = "User",
        q: str = "",
        framework: str = "",
        application: str = "",
        owner: str = "",
        status: str = "",
        response: str = "",
    ):
        ctx = _base_ctx(role, user, response, page_module="search")
        discovery = build_search_discovery(q, framework, application, owner, status)
        ctx["discovery"] = discovery
        ctx["results"] = discovery["results"]
        ctx["semantic_matches"] = discovery["semantic_matches"]
        ctx["reuse_suggestions"] = discovery["reuse_suggestions"]
        ctx["related_evidences"] = discovery["related_evidences"]
        ctx["q"] = q
        ctx["framework"] = framework
        ctx["application"] = application
        ctx["owner"] = owner
        ctx["status"] = status
        return templates.TemplateResponse(request, "mvp_search.html", ctx)

    @app.get("/mvp/completeness", response_class=HTMLResponse)
    def mvp_completeness(request: Request, role: str = "auditor", user: str = "Auditor", response: str = ""):
        ctx = _base_ctx(role, user, response, page_module="completeness")
        ctx["completeness"] = completeness_report()
        return templates.TemplateResponse(request, "mvp_completeness.html", ctx)

    @app.get("/mvp/reuse", response_class=HTMLResponse)
    def mvp_reuse(request: Request, role: str = "owner", user: str = "User", response: str = ""):
        ctx = _base_ctx(role, user, response, page_module="reuse")
        ctx["reuse"] = get_reuse_graph()
        return templates.TemplateResponse(request, "mvp_reuse.html", ctx)

    @app.get("/mvp/onboarding", response_class=HTMLResponse)
    def mvp_onboarding(request: Request, role: str = "cio", user: str = "CIO", response: str = "", notice: str = ""):
        ctx = _base_ctx(role, user, response, notice, page_module="onboarding")
        ctx["onboarded"] = ecs_state.onboarded_applications
        return templates.TemplateResponse(request, "mvp_onboarding.html", ctx)

    @app.post("/mvp/onboarding")
    def mvp_onboarding_add(application: str = Form(...), role: str = Form(...), user: str = Form(...)):
        app_name = application.strip()
        if app_name and app_name not in ecs_state.onboarded_applications:
            ecs_state.onboarded_applications.append(app_name)
        notice = quote(f"Application onboarded: {app_name}")
        return RedirectResponse(url=f"/mvp/onboarding?role={role}&user={user}&notice={notice}", status_code=303)

    @app.get("/mvp/lifecycle", response_class=HTMLResponse)
    def mvp_lifecycle(request: Request, role: str = "owner", user: str = "User", response: str = ""):
        ctx = _base_ctx(role, user, response, page_module="lifecycle")
        ctx["timeline"] = lifecycle_timeline()
        ctx["statuses"] = ecs_state.LIFECYCLE_STATUSES
        ctx["rows"] = ecs_state.build_evidence_analytics()["evidence_rows"]
        return templates.TemplateResponse(request, "mvp_lifecycle.html", ctx)

    @app.get("/mvp/comparison", response_class=HTMLResponse)
    def mvp_comparison(request: Request, role: str = "cio", user: str = "CIO", response: str = ""):
        ctx = _base_ctx(role, user, response, page_module="comparison")
        ctx["comparison"] = application_comparison()
        return templates.TemplateResponse(request, "mvp_comparison.html", ctx)

    @app.get("/mvp/integrations", response_class=HTMLResponse)
    def mvp_integrations(request: Request, role: str = "owner", user: str = "User", response: str = "", notice: str = ""):
        ctx = _base_ctx(role, user, response, notice, page_module="integrations")
        ctx["integrations"] = get_integration_dashboard()
        return templates.TemplateResponse(request, "mvp_integrations.html", ctx)

    @app.post("/mvp/integrations/sync")
    def mvp_integrations_sync(connector: str = Form(...), role: str = Form(...), user: str = Form(...)):
        simulate_sync(connector)
        notice = quote(f"Sync simulated for {connector}")
        return RedirectResponse(url=f"/mvp/integrations?role={role}&user={user}&notice={notice}", status_code=303)

    @app.get("/mvp/enterprise", response_class=HTMLResponse)
    def mvp_enterprise(request: Request, role: str = "cio", user: str = "CIO", response: str = ""):
        ctx = _base_ctx(role, user, response, page_module="enterprise")
        ctx["enterprise"] = enterprise_dashboard()
        return templates.TemplateResponse(request, "mvp_enterprise.html", ctx)

    @app.get("/mvp/pan-india", response_class=HTMLResponse)
    def mvp_pan_india(request: Request, role: str = "cio", user: str = "CIO", response: str = ""):
        ctx = _base_ctx(role, user, response, page_module="pan_india")
        ctx["enterprise"] = enterprise_dashboard()
        ctx["regions"] = ecs_state.PAN_INDIA_REGIONS
        return templates.TemplateResponse(request, "mvp_pan_india.html", ctx)

    @app.get("/mvp/reports", response_class=HTMLResponse)
    def mvp_reports(request: Request, role: str = "compliance_head", user: str = "ComplianceHead", response: str = ""):
        ctx = _base_ctx(role, user, response, page_module="reports")
        ctx["reports"] = list_reports()
        return templates.TemplateResponse(request, "mvp_reports.html", ctx)

    @app.get("/mvp/reports/download/{report_id}")
    def mvp_report_download(report_id: str):
        content = generate_report_content(report_id)
        return PlainTextResponse(content, media_type="text/plain", headers={
            "Content-Disposition": f'attachment; filename="{report_id}-ecs-report.txt"'
        })

    @app.get("/mvp/audit-prep", response_class=HTMLResponse)
    def mvp_audit_prep(request: Request, role: str = "auditor", user: str = "Auditor", response: str = ""):
        ctx = _base_ctx(role, user, response, page_module="audit_prep")
        ctx["prep"] = audit_preparation_checklist()
        return templates.TemplateResponse(request, "mvp_audit_prep.html", ctx)

    @app.get("/mvp/trends", response_class=HTMLResponse)
    def mvp_trends(request: Request, role: str = "cio", user: str = "CIO", response: str = ""):
        ctx = _base_ctx(role, user, response, page_module="trends")
        ctx["trends"] = compliance_trends()
        ctx["analytics"] = ecs_state.build_evidence_analytics()
        return templates.TemplateResponse(request, "mvp_trends.html", ctx)

    @app.get("/mvp/risk-register", response_class=HTMLResponse)
    def mvp_risk_register(request: Request, role: str = "owner", user: str = "User", notice: str = ""):
        return templates.TemplateResponse(request, "mvp_risk_register.html", _base_ctx(role, user, notice=notice, page_module="risk_register"))

    @app.get("/mvp/exceptions", response_class=HTMLResponse)
    def mvp_exceptions(request: Request, role: str = "owner", user: str = "User", notice: str = ""):
        return templates.TemplateResponse(request, "mvp_exceptions.html", _base_ctx(role, user, notice=notice, page_module="exceptions_td"))

    @app.get("/mvp/cmdb", response_class=HTMLResponse)
    def mvp_cmdb(request: Request, role: str = "owner", user: str = "User", notice: str = ""):
        return templates.TemplateResponse(request, "mvp_cmdb.html", _base_ctx(role, user, notice=notice, page_module="cmdb"))

    @app.get("/mvp/regulatory", response_class=HTMLResponse)
    def mvp_regulatory(request: Request, role: str = "compliance_head", user: str = "ComplianceHead", notice: str = ""):
        return templates.TemplateResponse(request, "mvp_regulatory.html", _base_ctx(role, user, notice=notice, page_module="regulatory_mapping"))

    @app.get("/mvp/heatmaps", response_class=HTMLResponse)
    def mvp_heatmaps(request: Request, role: str = "cio", user: str = "CIO", notice: str = ""):
        return templates.TemplateResponse(request, "mvp_heatmaps.html", _base_ctx(role, user, notice=notice, page_module="executive_heatmaps"))

    @app.get("/mvp/integrations-hub", response_class=HTMLResponse)
    def mvp_integrations_hub(request: Request, role: str = "owner", user: str = "User", notice: str = ""):
        return templates.TemplateResponse(request, "mvp_integrations_hub.html", _base_ctx(role, user, notice=notice, page_module="integrations_hub"))

    @app.post("/mvp/integrations-hub/sync")
    def mvp_integrations_hub_sync(connector: str = Form(...), role: str = Form(...), user: str = Form(...)):
        from app.integrations_module import simulate_sync
        simulate_sync(connector)
        notice = quote(f"Integrations Hub sync complete for {connector}")
        return RedirectResponse(url=f"/mvp/integrations-hub?role={role}&user={user}&notice={notice}", status_code=303)

    @app.get("/mvp/correlation", response_class=HTMLResponse)
    def mvp_correlation(request: Request, role: str = "owner", user: str = "User", notice: str = ""):
        return templates.TemplateResponse(request, "mvp_correlation.html", _base_ctx(role, user, notice=notice, page_module="correlation"))

    @app.get("/mvp/governance-analytics", response_class=HTMLResponse)
    def mvp_governance_analytics(request: Request, role: str = "cio", user: str = "CIO", notice: str = ""):
        return templates.TemplateResponse(request, "mvp_governance_analytics.html", _base_ctx(role, user, notice=notice, page_module="governance_analytics"))

    @app.post("/mvp/grc/action")
    def mvp_grc_action(
        module: str = Form(...),
        action: str = Form(...),
        role: str = Form(...),
        user: str = Form(...),
        item_id: str = Form(""),
    ):
        from app.enterprise_grc import execute_grc_action
        notice = execute_grc_action(module, action, item_id, user, role)
        return _module_redirect(module, role, user, notice)

    @app.post("/mvp/module/action")
    def mvp_module_action(
        module: str = Form(...),
        action: str = Form(...),
        role: str = Form(...),
        user: str = Form(...),
        item_id: str = Form(""),
    ):
        from app.audit_trail import log_event

        label = action.replace("_", " ").title()
        log_event(f"Module: {label}", user, "", item_id, f"{module} capability action")
        if module == "scheduler" and action == "run_now":
            run_scheduled_pull()
        if module == "integrations" and action == "sync_now" and item_id:
            simulate_sync(item_id)
        if module == "integrations_hub":
            from app.integrations_module import simulate_sync as hub_sync, test_connection, retry_failed_sync
            if action == "sync_now" and item_id:
                hub_sync(item_id)
            elif action == "test_connection" and item_id:
                notice = test_connection(item_id)
                return _module_redirect(module, role, user, notice)
            elif action == "retry_failed_sync" and item_id:
                notice = retry_failed_sync(item_id)
                return _module_redirect(module, role, user, notice)
        if module in ("risk_register", "exceptions_td", "cmdb", "regulatory_mapping", "executive_heatmaps", "correlation", "governance_analytics"):
            from app.enterprise_grc import execute_grc_action
            notice = execute_grc_action(module, action, item_id, user, role)
            return _module_redirect(module, role, user, notice)
        notice = f"{label} completed" + (f" for {item_id}" if item_id else "") + "."
        return _module_redirect(module, role, user, notice)

    @app.post("/mvp/chat")
    def mvp_chat(
        query: str = Form(...),
        role: str = Form(...),
        user: str = Form(...),
        framework_name: str = Form(""),
        return_url: str = Form("/dashboard"),
    ):
        from app.main import chatbot_answer

        response = chatbot_answer(query, role=role, user=user, framework_hint=framework_name)
        encoded = quote(response)
        sep = "&" if "?" in return_url else "?"
        return RedirectResponse(url=f"{return_url}{sep}response={encoded}", status_code=303)
