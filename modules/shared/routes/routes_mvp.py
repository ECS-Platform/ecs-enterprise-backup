"""Additive MVP routes — does not replace existing ECS routes."""

from urllib.parse import quote

from fastapi import File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response

from app import ecs_state
from modules.governance.engines.analytics_module import (
    application_comparison,
    audit_preparation_checklist,
    completeness_report,
    compliance_trends,
    enterprise_dashboard,
    lifecycle_timeline,
)
from modules.operations.engines.evidence_repository import (
    evidence_repository,
    get_health_dashboard,
    get_reuse_graph,
    get_summaries,
    register_upload,
    upload_tracker,
)
from modules.operations.engines.integrations_module import get_integration_dashboard, simulate_sync
from modules.executive_overview.engines.reporting_module import generate_report_content, generate_report_export, list_reports
from modules.operations.engines.scheduler_module import get_scheduler_dashboard, run_scheduled_pull, retry_failed_observation
from modules.governance.engines.search_module import build_search_discovery, search_evidences
from modules.shared.services.enterprise_context import enterprise_widgets_context
from modules.executive_overview.engines.demo_metrics import REUSE_METRICS


def _safe_count(value) -> int:
    """Parse a count query param that the UI may send as a formatted KPI value.

    KPI cards bind data-*-count to their *displayed* value (e.g. "94.5%", "12 days",
    "3.2d", "45,000"). Declaring the query param as ``int`` makes FastAPI reject these
    with HTTP 422 before the route body (and its fallback) can run. Accept the raw
    string and extract the leading numeric portion, defaulting to 0.
    """
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    import re
    m = re.search(r"\d+(?:\.\d+)?", str(value).replace(",", ""))
    return int(float(m.group(0))) if m else 0


def _base_ctx(role: str, user: str, response: str = "", notice: str = "", page_module: str = "", analytics_filters: dict | None = None):
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
    ctx.update(enterprise_widgets_context(role, page_module=page_module, user=user, analytics_filters=analytics_filters))
    ctx["module_view"] = ctx.get("module_view") or {}
    ctx["reuse_metrics"] = REUSE_METRICS
    # Executive demo dark theme activates only when the global DEMO_MODE flag is on.
    try:
        from app.auth.demo import demo_mode
        ctx["demo_mode"] = demo_mode()
    except Exception:  # noqa: BLE001
        ctx["demo_mode"] = False
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
        "framework_admin": "/mvp/framework-admin",
        "framework_loader": "/mvp/framework-loader",
        "demo_overview": "/mvp/demo-overview",
        "risk_register": "/mvp/risk-register",
        "exceptions_td": "/mvp/exceptions",
        "cmdb": "/mvp/cmdb",
        "regulatory_mapping": "/mvp/regulatory",
        "executive_heatmaps": "/mvp/heatmaps",
        "integrations_hub": "/mvp/integrations-hub",
        "correlation": "/mvp/correlation",
        "governance_analytics": "/mvp/governance-analytics",
        "evidence_approval": "/mvp/evidence-approval",
        "exception_governance": "/mvp/exception-governance",
        "ai_ops_assistant": "/mvp/ai-ops-assistant",
        "predefined_queries": "/mvp/predefined-queries",
        "roi": "/mvp/roi",
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
        from app.auth.page_guard import guard_page
        deny = guard_page(request, "dashboard.vertical", fallback_role=role, user=user,
                          home=f"/dashboard?role={role}&user={user}", page_label="Vertical Head dashboard")
        if deny:
            return deny
        ctx = _base_ctx(role, user, response)
        ctx["analytics"] = ecs_state.build_evidence_analytics()
        ctx["enterprise"] = enterprise_dashboard()
        ctx["comparison"] = application_comparison()
        return templates.TemplateResponse(request, "dashboard_vertical_head.html", ctx)

    @app.get("/dashboard/compliance-head", response_class=HTMLResponse)
    def compliance_head_dashboard(request: Request, role: str = "compliance_head", user: str = "ComplianceHead", response: str = ""):
        from app.auth.page_guard import guard_page
        # Shared landing page: compliance officers and security officers both use it
        # (login routes security_officer here). Any-of avoids an RBAC catalog change.
        deny = guard_page(request, ["dashboard.compliance", "dashboard.security"],
                          fallback_role=role, user=user,
                          home=f"/dashboard?role={role}&user={user}", page_label="Compliance dashboard")
        if deny:
            return deny
        ctx = _base_ctx(role, user, response)
        ctx["analytics"] = ecs_state.build_evidence_analytics()
        ctx["completeness"] = completeness_report()
        ctx["enterprise"] = enterprise_dashboard()
        return templates.TemplateResponse(request, "dashboard_compliance_head.html", ctx)

    @app.get("/dashboard/functional-head", response_class=HTMLResponse)
    def functional_head_dashboard(request: Request, role: str = "functional_head", user: str = "FunctionalHead", response: str = ""):
        from app.auth.page_guard import guard_page
        deny = guard_page(request, "dashboard.functional", fallback_role=role, user=user,
                          home=f"/dashboard?role={role}&user={user}", page_label="Functional Head dashboard")
        if deny:
            return deny
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

    @app.get("/mvp/ai-ops-assistant", response_class=HTMLResponse)
    def mvp_ai_ops_assistant(request: Request, role: str = "cio", user: str = "cio@bank.com", response: str = "", notice: str = ""):
        from urllib.parse import unquote

        ctx = _base_ctx(role, user, unquote(response) if response else "", notice, page_module="ai_ops_assistant")
        return templates.TemplateResponse(request, "mvp_ai_ops_assistant.html", ctx)

    @app.get("/mvp/predefined-queries", response_class=HTMLResponse)
    def mvp_predefined_queries(
        request: Request,
        role: str = "owner",
        user: str = "User",
        response: str = "",
        notice: str = "",
        q: str = "",
        framework: str = "All Frameworks",
        page: int = 1,
        sort: str = "control_id",
        dir: str = "asc",
    ):
        from modules.operations.engines.predefined_queries_engine import get_predefined_queries_dashboard

        ctx = _base_ctx(role, user, response, notice, page_module="predefined_queries")
        ctx["module_view"] = get_predefined_queries_dashboard(
            search=q,
            framework=framework,
            page=page,
            per_page=10,
            sort_by=sort,
            sort_dir=dir,
        )
        ctx["module_view"]["purpose"] = "Predefined Queries — centralized catalog of control queries loaded from the ECS Query Driven Control Library."
        ctx["module_view"]["module"] = "predefined_queries"
        ctx["module_view"]["role"] = role
        return templates.TemplateResponse(request, "mvp_predefined_queries.html", ctx)

    @app.get("/mvp/predefined-queries/detail", response_class=HTMLResponse)
    def mvp_predefined_query_detail(
        request: Request,
        control_id: str = "",
        role: str = "owner",
        user: str = "User",
        notice: str = "",
    ):
        from modules.operations.engines.predefined_queries_engine import (
            derive_runtime_state,
            get_control_by_id,
            prepare_execution,
        )

        ctx = _base_ctx(role, user, "", notice, page_module="predefined_queries")
        control = get_control_by_id(control_id) if control_id else None
        if not control:
            ctx["control"] = {"control_id": control_id or "—", "control_name": "Not Found"}
            ctx["error_message"] = "Control not found in the predefined query library."
            ctx["execution_prep"] = {"ok": False}
            ctx["runtime"] = derive_runtime_state(None)
        else:
            ctx["control"] = control
            ctx["error_message"] = ""
            ctx["execution_prep"] = prepare_execution(control_id, user)
            # Trustability: the banner is derived from durable runtime signals,
            # not the (possibly stale) URL notice. A successful run clears the
            # stale notice so SUCCESS can never appear next to a failure/connector
            # warning.
            runtime = derive_runtime_state(control)
            ctx["runtime"] = runtime
            if runtime["suppress_notice"]:
                ctx["notice"] = ""
        return templates.TemplateResponse(request, "mvp_predefined_query_detail.html", ctx)

    @app.post("/mvp/predefined-queries/prepare", response_class=JSONResponse)
    def mvp_predefined_query_prepare(
        control_id: str = Form(""),
        role: str = Form("owner"),
        user: str = Form("User"),
    ):
        from modules.operations.engines.predefined_queries_engine import prepare_execution

        result = prepare_execution(control_id, user)
        return JSONResponse(result)

    @app.post("/mvp/predefined-queries/run")
    def mvp_predefined_query_run(
        control_id: str = Form(""),
        role: str = Form("owner"),
        user: str = Form("User"),
        return_to: str = Form("detail"),
    ):
        from modules.operations.engines.predefined_queries_engine import run_predefined_query

        try:
            outcome = run_predefined_query(control_id, user)
        except Exception as exc:  # noqa: BLE001 — never surface a 500 / stack trace to the demo
            outcome = {
                "ok": False,
                "error": "Query execution failed",
                "error_type": "unexpected_error",
                "reason": str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__,
                "action": "Review the connector configuration and try again.",
            }
        if outcome.get("ok"):
            notice = outcome.get("message", "Query executed successfully")
        else:
            # Build a graceful, single-line notice: "Query Execution Failed — Reason … Action …"
            parts = [outcome.get("error") or "Query Execution Failed"]
            if outcome.get("reason"):
                parts.append(f"Reason: {outcome['reason']}")
            if outcome.get("action"):
                parts.append(f"Action: {outcome['action']}")
            notice = " — ".join(parts)
        dest = (
            f"/mvp/predefined-queries?role={role}&user={user}&notice={quote(notice)}"
            if return_to == "catalog"
            else f"/mvp/predefined-queries/detail?control_id={quote(control_id)}&role={role}&user={user}&notice={quote(notice)}"
        )
        return RedirectResponse(url=dest, status_code=303)

    @app.get("/mvp/evidence-story", response_class=HTMLResponse)
    def mvp_evidence_reuse_story(request: Request, role: str = "owner", user: str = "User"):
        """Phase-1 value chain: Query -> Evidence -> Reuse -> Readiness -> Observations."""
        from modules.operations.engines.evidence_reuse_story_engine import (
            build_evidence_reuse_story,
        )

        ctx = _base_ctx(role, user, page_module="evidence_story")
        ctx["story"] = build_evidence_reuse_story()
        return templates.TemplateResponse(request, "mvp_evidence_reuse_story.html", ctx)

    @app.get("/api/demo/kpi-drill")
    def api_demo_kpi_drill(metric: str = ""):
        from modules.executive_overview.engines.demo_kpi_drill_engine import drill_demo_kpi
        from modules.shared.services.drilldown_engine import _fallback_body

        try:
            body = drill_demo_kpi(metric or "applications")
            if not isinstance(body, dict) or not body.get("ok", True) or not body.get("rows"):
                raise ValueError("empty demo drill")
        except Exception:  # noqa: BLE001 - never 500 a drill
            body = _fallback_body(scope="kpi", page="demo", metric=metric, label=metric,
                                  count=0, framework="", role="cio")
        return JSONResponse(body)

    @app.get("/mvp/reports/view/{report_type}", response_class=HTMLResponse)
    def mvp_report_view(request: Request, report_type: str, role: str = "cio", user: str = "cio@bank.com"):
        from modules.executive_overview.engines.ecs_reports_engine import build_report

        report = build_report(report_type)
        if not report:
            return RedirectResponse(url=f"/mvp/reports?role={role}&user={user}&notice=Unknown%20report", status_code=303)
        ctx = _base_ctx(role, user, page_module="reports")
        ctx["report"] = report
        return templates.TemplateResponse(request, "mvp_ecs_report.html", ctx)

    @app.get("/mvp/roi", response_class=HTMLResponse)
    def mvp_roi_center(request: Request, role: str = "cio", user: str = "cio@bank.com", response: str = "", notice: str = "", scenario: str = ""):
        """Executive ROI & Value Realization Center (deterministic, read-only)."""
        from app.roi import build_roi_center, roi_enabled

        ctx = _base_ctx(role, user, response, notice, page_module="roi")
        ctx["nav_module"] = "roi"
        ctx["roi_enabled"] = roi_enabled()
        # force=True so the page renders fully in demos even before the flag is set;
        # the master flag still controls nav visibility / availability messaging.
        # Scenario chooses which model is active on initial render; all three are
        # also emitted in the payload so the UI toggle can switch instantly.
        ctx["roi"] = build_roi_center(force=True, scenario=(scenario or None))
        return templates.TemplateResponse(request, "mvp_roi_center.html", ctx)

    @app.get("/mvp/ai-ops-assistant/summary/{mode}", response_class=HTMLResponse)
    def mvp_ai_ops_summary(request: Request, mode: str, scenario: str = "net_banking", role: str = "cio", user: str = "cio@bank.com"):
        from modules.operations.engines.ai_ops_summary_engine import build_summary_page

        page = build_summary_page(mode, scenario, role)
        if not page:
            return RedirectResponse(url=f"/mvp/ai-ops-assistant?role={role}&user={user}", status_code=303)
        ctx = _base_ctx(role, user, page_module="ai_ops_assistant")
        ctx["page"] = page
        return templates.TemplateResponse(request, "mvp_ai_ops_summary.html", ctx)

    @app.get("/api/module-kpi/drill")
    def api_module_kpi_drill(module: str = "", metric: str = "", role: str = "cio", count: str = ""):
        from modules.shared.drilldowns.module_kpi_drill_engine import drill_module_kpi
        from modules.shared.services.drilldown_engine import _fallback_body

        count = _safe_count(count)
        try:
            body = drill_module_kpi(module or "operations", metric, role)
            # Predefined Queries returns authoritative, KPI-specific rows (with
            # honest empty-states). Bypass the generic count-padding / fallback
            # so its drilldowns are never fabricated or unrelated.
            if (module or "") == "predefined_queries" and isinstance(body, dict) and body.get("ok"):
                return JSONResponse(body)
            if count:
                from modules.shared.utils.demo_data_standards import ensure_drill_rows
                from modules.shared.drilldowns.ecs_universal_drill_engine import _target_rows

                target = _target_rows(count)
                body["rows"] = ensure_drill_rows(body.get("rows", []), target, metric=metric or module)
                body["trace_count"] = count
                body["row_count"] = len(body["rows"])
            if not isinstance(body, dict) or not body.get("ok", True) or not body.get("rows"):
                raise ValueError("empty module drill")
        except Exception:  # noqa: BLE001 - never 500 a drill
            body = _fallback_body(scope="kpi", page=module, metric=metric, label=metric,
                                  count=count, framework="", role=role)
        return JSONResponse(body)

    @app.get("/api/ecs/universal-drill")
    def api_ecs_universal_drill(
        scope: str = "kpi",
        page: str = "",
        metric: str = "",
        chart: str = "",
        element: str = "",
        type: str = "",
        id: str = "",
        count: str = "",
        role: str = "cio",
        framework: str = "",
        label: str = "",
        application: str = "",
        readiness_pct: str = "",
    ):
        from modules.shared.services.drilldown_engine import drill_metric

        count = _safe_count(count)
        try:
            body = drill_metric(
                scope,
                page=page,
                metric=metric,
                chart=chart,
                element=element,
                row_type=type,
                row_id=id,
                count=count,
                role=role,
                framework=framework,
                label=label,
                application=application,
                readiness_pct=readiness_pct,
            )
        except Exception:  # noqa: BLE001 - last-resort guard; never 500 a drill
            from modules.shared.services.drilldown_engine import _fallback_body
            body = _fallback_body(scope=scope, page=page, metric=metric or chart,
                                  label=label or element or id, count=count,
                                  framework=framework, role=role)
        return JSONResponse(body)

    @app.get("/api/ecs/workflow-drill")
    def api_ecs_workflow_drill(metric: str = "", count: str = "", role: str = "cio"):
        from modules.shared.services.drilldown_engine import _fallback_body, drill_workflow

        count = _safe_count(count)
        try:
            body = drill_workflow(role, metric or "workflow", count)
            if not isinstance(body, dict) or not body.get("ok", True) or not body.get("rows"):
                raise ValueError("empty workflow drill")
        except Exception:  # noqa: BLE001 - never 500 a drill
            body = _fallback_body(scope="workflow", page="enterprise", metric=metric,
                                  label=metric, count=count, framework="", role=role)
        return JSONResponse(body)

    @app.post("/mvp/scheduler/run")
    def mvp_scheduler_run(role: str = Form(...), user: str = Form(...)):
        try:
            from modules.shared.services.ecs_logging import log_scheduler
            log_scheduler("Manual evidence collection run triggered", user=user)
        except Exception:
            pass
        result = run_scheduled_pull(user=user)
        notice = (
            f"Evidence collection completed — {result['observations_scanned']} observations scanned, "
            f"{result['new_findings']} new findings detected."
        )
        return RedirectResponse(
            url=f"/mvp/scheduler?role={role}&user={user}&notice={quote(notice)}&toast=scheduler_ok",
            status_code=303,
        )

    @app.post("/mvp/scheduler/retry")
    def mvp_scheduler_retry(
        role: str = Form(...),
        user: str = Form(...),
        failure_id: str = Form(...),
    ):
        result = retry_failed_observation(failure_id, user)
        toast = "scheduler_retry_ok" if result["ok"] else "scheduler_retry_fail"
        return RedirectResponse(
            url=f"/mvp/scheduler?role={role}&user={user}&notice={quote(result['message'])}&toast={toast}",
            status_code=303,
        )

    @app.post("/mvp/scheduler/pause")
    def mvp_scheduler_pause(role: str = Form(...), user: str = Form(...)):
        from modules.operations.engines.scheduler_module import pause_scheduler
        notice = quote(pause_scheduler(user))
        return RedirectResponse(url=f"/mvp/scheduler?role={role}&user={user}&notice={notice}", status_code=303)

    @app.post("/mvp/scheduler/resume")
    def mvp_scheduler_resume(role: str = Form(...), user: str = Form(...)):
        from modules.operations.engines.scheduler_module import resume_scheduler
        notice = quote(resume_scheduler(user))
        return RedirectResponse(url=f"/mvp/scheduler?role={role}&user={user}&notice={notice}", status_code=303)

    @app.get("/mvp/upload", response_class=HTMLResponse)
    def mvp_upload_page(
        request: Request,
        role: str = "owner",
        user: str = "User",
        response: str = "",
        notice: str = "",
        framework: str = "",
        application: str = "",
        control: str = "",
    ):
        from modules.shared.services.role_permissions import guard_upload

        deny = guard_upload(role, user, "/mvp/completeness")
        if deny:
            return deny
        ctx = _base_ctx(role, user, response, notice, page_module="upload")
        ctx["uploads"] = list(reversed(evidence_repository[-15:]))
        ctx["tracker"] = list(reversed(upload_tracker[-10:]))
        ctx["upload_prefill"] = {"framework": framework, "application": application, "control": control}
        return templates.TemplateResponse(request, "mvp_bulk_upload.html", ctx)

    @app.post("/mvp/upload/bulk")
    async def mvp_bulk_upload(
        role: str = Form(...),
        user: str = Form(...),
        framework: str = Form(""),
        application: str = Form("Net Banking"),
        files: list[UploadFile] = File(...),
    ):
        from modules.shared.services.role_permissions import guard_upload

        deny = guard_upload(role, user, "/mvp/completeness")
        if deny:
            return deny
        count = 0
        for f in files:
            content = await f.read()
            register_upload(f.filename, content, user, framework, application)
            count += 1
        notice = quote(f"Bulk upload complete: {count} file(s) with metadata tags applied.")
        return RedirectResponse(url=f"/mvp/upload?role={role}&user={user}&notice={notice}", status_code=303)

    @app.get("/mvp/evidence-health", response_class=HTMLResponse)
    def mvp_evidence_health(
        request: Request,
        role: str = "owner",
        user: str = "User",
        response: str = "",
        framework: str = "",
        application: str = "",
        status: str = "",
        filter_issue: str = "",
        highlight: str = "",
        observation_id: str = "",
        tab: str = "",
    ):
        ctx = _base_ctx(role, user, response, page_module="evidence_health")
        ctx["health"] = get_health_dashboard()
        ctx["summaries"] = get_summaries()
        ctx["health_deep_link"] = {
            "framework": framework,
            "application": application,
            "status": status,
            "filter_issue": filter_issue,
            "highlight": highlight,
            "observation_id": observation_id,
            "tab": tab,
        }
        if tab and ctx.get("workspace"):
            ctx["workspace"]["default_tab"] = tab
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
    def mvp_completeness(request: Request, role: str = "auditor", user: str = "Auditor", response: str = "", notice: str = ""):
        ctx = _base_ctx(role, user, response, notice, page_module="completeness")
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
    async def mvp_onboarding_add(request: Request, role: str = Form(...), user: str = Form(...)):
        form = await request.form()
        app_name = (form.get("application") or form.get("application_name") or "").strip()
        if app_name and app_name not in ecs_state.onboarded_applications:
            ecs_state.onboarded_applications.append(app_name)
        notice = quote(f"Application registered: {app_name}")
        return RedirectResponse(url=f"/mvp/onboarding?role={role}&user={user}&notice={notice}", status_code=303)

    @app.post("/api/onboarding/simulate")
    async def api_onboarding_simulate(request: Request):
        from app.auth.mutation_guard import guard_mutation
        from modules.operations.engines.onboarding_engine import simulate_onboarding

        try:
            payload = await request.json()
        except Exception:
            payload = {}
        deny = guard_mutation(request, "can_manage_framework_onboarding",
                              fallback_role=payload.get("role", "cio"), response="json")
        if deny:
            return deny
        result = simulate_onboarding(payload)
        return JSONResponse(result)

    @app.post("/api/onboarding/export")
    async def api_onboarding_export(request: Request):
        from app.auth.mutation_guard import guard_mutation
        from modules.operations.engines.onboarding_engine import export_onboarding_summary, simulate_onboarding

        try:
            payload = await request.json()
        except Exception:
            payload = {}
        deny = guard_mutation(request, "can_manage_framework_onboarding",
                              fallback_role=payload.get("role", "cio"), response="json")
        if deny:
            return deny
        result = payload.get("result") or simulate_onboarding(payload)
        app_name = result.get("metadata", {}).get("application_name", "application")
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in app_name)
        content = export_onboarding_summary(result)
        return PlainTextResponse(
            content,
            headers={"Content-Disposition": f'attachment; filename="ecs-onboarding-{safe_name}.txt"'},
        )

    @app.get("/mvp/framework-loader", response_class=HTMLResponse)
    def mvp_framework_loader(
        request: Request,
        role: str = "cio",
        user: str = "User",
        notice: str = "",
        framework_id: str = "",
    ):
        from modules.frameworks.engines.framework_loader_service import build_loader_dashboard
        from modules.shared.services.role_permissions import can_manage_frameworks

        ctx = _base_ctx(role, user, notice=notice, page_module="framework_loader")
        ctx["loader"] = build_loader_dashboard(role, framework_id)
        ctx["can_manage"] = can_manage_frameworks(role)
        return templates.TemplateResponse(request, "framework_loader.html", ctx)

    @app.post("/mvp/framework-loader/upload")
    async def mvp_framework_loader_upload(request: Request):
        from modules.frameworks.engines.framework_loader_service import submit_upload

        form = await request.form()
        role = form.get("role", "cio")
        user = form.get("user", "User")
        framework_name = form.get("framework_name", "").strip()
        framework_type = form.get("framework_type", "Security Baseline").strip()
        framework_owner = form.get("framework_owner", "").strip()
        if not framework_name:
            return JSONResponse(
                {"ok": False, "errors": ["Framework name is required."]},
                status_code=400,
            )
        upload = form.get("control_file")
        content = await upload.read() if upload and hasattr(upload, "read") else b""
        filename = (
            upload.filename
            if upload and hasattr(upload, "filename") and upload.filename
            else f"{framework_name}-upload.csv"
        )
        result = submit_upload(
            framework_name,
            framework_type,
            framework_owner,
            filename,
            content,
            user,
            role,
        )
        if not result.get("ok"):
            return JSONResponse(result, status_code=400)
        return JSONResponse(
            {
                "ok": True,
                "framework_id": result["framework_id"],
                "framework_name": framework_name,
                "warnings": result.get("warnings", []),
            }
        )

    @app.get("/mvp/demo-overview", response_class=HTMLResponse)
    def mvp_demo_overview(
        request: Request,
        role: str = "cio",
        user: str = "CIO",
        framework: str = "",
        application: str = "",
        owner: str = "",
        notice: str = "",
    ):
        from modules.shared.services.ecs_mock_engine import build_demo_overview

        ctx = _base_ctx(role, user, notice=notice, page_module="demo_overview")
        ctx["demo_overview"] = build_demo_overview()
        ctx["demo_filters"] = {
            "framework": framework,
            "application": application,
            "owner": owner,
        }
        return templates.TemplateResponse(request, "mvp_demo_overview.html", ctx)

    @app.get("/api/demo/status")
    def api_demo_status():
        from modules.shared.services.ecs_mock_engine import DEMO_MODE, DEMO_ANCHOR_DATE

        return JSONResponse({
            "ok": True,
            "demo_mode": DEMO_MODE,
            "anchor_date": DEMO_ANCHOR_DATE.isoformat(),
        })

    @app.get("/api/demo/overview")
    def api_demo_overview():
        from modules.shared.services.ecs_mock_engine import build_demo_overview

        return JSONResponse({"ok": True, "data": build_demo_overview()})

    @app.get("/api/demo/banking-applications")
    def api_demo_banking_applications():
        from modules.shared.services.ecs_mock_engine import list_banking_applications

        return JSONResponse({"ok": True, "rows": list_banking_applications()})

    @app.get("/api/demo/frameworks")
    def api_demo_frameworks():
        from modules.shared.services.ecs_mock_engine import list_frameworks_catalog

        return JSONResponse({"ok": True, "rows": list_frameworks_catalog()})

    @app.get("/api/demo/servicenow")
    def api_demo_servicenow(limit: int = 60, type: str = ""):
        from modules.shared.services.ecs_mock_engine import generate_servicenow_tickets

        rows = generate_servicenow_tickets(count=limit)
        if type:
            rows = [r for r in rows if r["type"] == type.upper()]
        return JSONResponse({"ok": True, "rows": rows})

    @app.get("/api/demo/ai-governance")
    def api_demo_ai_governance():
        from modules.shared.services.ecs_mock_engine import generate_ai_governance

        return JSONResponse({"ok": True, "data": generate_ai_governance()})

    @app.get("/api/demo/prompt-audit")
    def api_demo_prompt_audit(limit: int = 80):
        from modules.shared.services.ecs_mock_engine import generate_prompt_audit

        return JSONResponse({"ok": True, "rows": generate_prompt_audit(count=limit)})

    @app.get("/api/demo/hallucinations")
    def api_demo_hallucinations():
        from modules.shared.services.ecs_mock_engine import generate_hallucination_alerts

        return JSONResponse({"ok": True, "rows": generate_hallucination_alerts()})

    @app.get("/api/demo/token-usage")
    def api_demo_token_usage():
        from modules.shared.services.ecs_mock_engine import generate_token_usage

        return JSONResponse({"ok": True, "data": generate_token_usage()})

    @app.get("/api/demo/audit-history")
    def api_demo_audit_history(years: int = 5):
        from modules.shared.services.ecs_mock_engine import generate_audit_history, summarize_audit_history

        rows = generate_audit_history(years=years)
        return JSONResponse({
            "ok": True,
            "rows": rows,
            "summary": summarize_audit_history(rows),
        })

    @app.get("/api/demo/risk-heatmap")
    def api_demo_risk_heatmap():
        from modules.shared.services.ecs_mock_engine import build_risk_heatmap

        return JSONResponse({"ok": True, "data": build_risk_heatmap()})

    @app.get("/api/demo/drift")
    def api_demo_drift():
        from modules.shared.services.ecs_mock_engine import generate_baselining_drift

        return JSONResponse({"ok": True, "data": generate_baselining_drift()})

    @app.get("/api/demo/evidence-lineage")
    def api_demo_evidence_lineage(limit: int = 25):
        from modules.shared.services.ecs_mock_engine import generate_evidence_lineage

        return JSONResponse({"ok": True, "rows": generate_evidence_lineage(limit=limit)})

    @app.get("/api/demo/vapt")
    def api_demo_vapt():
        from modules.shared.services.ecs_mock_engine import generate_vapt_findings

        return JSONResponse({"ok": True, "data": generate_vapt_findings()})

    @app.get("/api/demo/cio-executive")
    def api_demo_cio_executive():
        from modules.shared.services.ecs_mock_engine import generate_cio_executive

        return JSONResponse({"ok": True, "data": generate_cio_executive()})

    @app.get("/api/audit-prep/kpi-drill")
    def api_audit_prep_kpi_drill(metric: str = ""):
        from modules.governance.engines.audit_schedule_engine import build_kpi_drilldowns

        valid = ("draft", "submitted", "reupload", "approval_rate",
                 "avg_review_time", "rejection_trend", "pending_aging",
                 "controls_pending_review", "evidence_pending_upload", "reusable_evidence_found",
                 "auditor_requests", "blockers")
        if metric not in valid:
            return JSONResponse(
                {"ok": False, "error": f"Unknown metric '{metric}'. Expected one of {valid}."},
                status_code=400,
            )
        drilldowns = build_kpi_drilldowns()
        return JSONResponse({"ok": True, "metric": metric, "drill": drilldowns[metric]})

    @app.get("/api/audit-prep/audit-detail")
    def api_audit_prep_audit_detail(audit_id: str = ""):
        from modules.governance.engines.audit_schedule_engine import get_audit_detail

        if not audit_id:
            return JSONResponse(
                {"ok": False, "error": "audit_id query parameter is required."},
                status_code=400,
            )
        result = get_audit_detail(audit_id)
        return JSONResponse(result, status_code=200 if result.get("ok") else 404)

    @app.get("/api/audit-prep/upcoming")
    def api_audit_prep_upcoming(
        framework: str = "",
        application: str = "",
        risk: str = "",
        status: str = "",
        owner: str = "",
    ):
        from modules.governance.engines.audit_schedule_engine import build_audit_operations

        ops = build_audit_operations("auditor", {
            "framework": framework, "application": application,
            "risk": risk, "status": status, "owner": owner,
        })
        return JSONResponse({
            "ok": True,
            "summary": ops["summary"],
            "upcoming": ops["upcoming_audits"],
            "calendar": ops["calendar"],
            "pipeline": ops["pipeline"],
        })

    @app.get("/api/framework-loader/control-drill")
    def api_framework_loader_control_drill(theme: str = ""):
        from modules.frameworks.engines.framework_intelligence import drill_theme

        if not theme:
            return JSONResponse(
                {"ok": False, "error": "theme query parameter is required."},
                status_code=400,
            )
        result = drill_theme(theme)
        return JSONResponse(result, status_code=200 if result.get("ok") else 404)

    @app.get("/api/framework-loader/application-scan")
    def api_framework_loader_application_scan():
        from modules.frameworks.engines.framework_intelligence import (
            build_application_scan,
            build_control_index,
        )

        return JSONResponse(
            {"ok": True, "rows": build_application_scan(build_control_index())}
        )

    @app.post("/mvp/framework-loader/activate")
    async def mvp_framework_loader_activate(
        framework_id: str = Form(...),
        role: str = Form("cio"),
        user: str = Form("User"),
    ):
        from modules.frameworks.engines.framework_loader_service import activate_framework

        result = activate_framework(framework_id, user, role)
        message = (
            result.get("messages", ["Framework activated."])[-1]
            if result.get("ok")
            else result.get("message", "Activation failed.")
        )
        return RedirectResponse(
            url=(
                f"/mvp/framework-loader?role={role}&user={quote(user)}"
                f"&framework_id={quote(framework_id)}"
                f"&notice={quote(message)}"
            ),
            status_code=303,
        )

    @app.get("/mvp/framework-admin", response_class=HTMLResponse)
    def mvp_framework_admin(
        request: Request,
        role: str = "cio",
        user: str = "CIO",
        notice: str = "",
        wizard: str = "",
        framework_id: str = "",
        toast: str = "",
    ):
        from modules.frameworks.engines.framework_onboarding_engine import build_admin_dashboard, get_onboarding_record
        from modules.shared.services.role_permissions import can_manage_frameworks, deny_redirect

        if not can_manage_frameworks(role) and role not in ("auditor", "owner"):
            return deny_redirect(role, user, "/dashboard", "Framework administration requires Admin, CIO, or Compliance Head access.")
        ctx = _base_ctx(role, user, notice=notice, page_module="framework_admin")
        ctx["admin"] = build_admin_dashboard(role)
        ctx["show_wizard"] = wizard == "1" and can_manage_frameworks(role)
        sel = get_onboarding_record(framework_id) if framework_id else None
        if sel:
            ctx["selected_framework"] = {
                "framework_id": sel["framework_id"],
                "framework_name": sel["framework_name"],
                "lifecycle_state": sel.get("lifecycle_state"),
                "analysis": sel.get("analysis", {}),
                "mapping_matrix": sel.get("mapping_matrix", []),
                "gaps": sel.get("gaps", []),
                "controls": sel.get("controls", [])[:50],
            }
        else:
            ctx["selected_framework"] = None
        ctx["toast"] = toast
        ctx["categories"] = ["Security", "Audit", "Regulatory", "Infra", "Risk"]
        return templates.TemplateResponse(request, "mvp_framework_admin.html", ctx)

    @app.post("/api/framework-onboarding/import")
    async def api_framework_onboarding_import(request: Request):
        from modules.frameworks.engines.framework_onboarding_engine import run_onboarding_pipeline
        from modules.shared.services.role_permissions import can_manage_frameworks

        form = await request.form()
        role = form.get("role", "cio")
        user = form.get("user", "User")
        if not can_manage_frameworks(role):
            return JSONResponse({"ok": False, "errors": ["Permission denied."]}, status_code=403)
        upload = form.get("control_file")
        content = await upload.read() if upload and hasattr(upload, "read") else b""
        filename = upload.filename if upload and hasattr(upload, "filename") else "controls.csv"
        details = {
            "framework_name": form.get("framework_name", ""),
            "version": form.get("version", ""),
            "regulator": form.get("regulator", ""),
            "effective_date": form.get("effective_date", ""),
            "category": form.get("category", "Security"),
        }
        result = run_onboarding_pipeline(details, content, filename, user, role)
        if not result.get("ok"):
            return JSONResponse(result, status_code=400)
        return JSONResponse({
            "ok": True,
            "framework_id": result["framework_id"],
            "record": {
                "framework_id": result["framework_id"],
                "framework_name": result["record"]["framework_name"],
                "analysis": result["record"]["analysis"],
                "lifecycle_state": result["record"]["lifecycle_state"],
                "controls_count": len(result["record"]["controls"]),
                "controls": result["record"]["controls"][:50],
                "mapping_matrix": result["record"]["mapping_matrix"][:20],
                "gaps_count": len(result["record"]["gaps"]),
                "warnings": result.get("warnings", []),
            },
        })

    @app.post("/api/framework-onboarding/lifecycle")
    async def api_framework_onboarding_lifecycle(request: Request):
        from app.auth.mutation_guard import guard_mutation
        from modules.frameworks.engines.framework_onboarding_engine import advance_lifecycle

        body = await request.json()
        deny = guard_mutation(request, "can_manage_framework_onboarding",
                              fallback_role=body.get("role", "cio"), response="json")
        if deny:
            return deny
        msg = advance_lifecycle(body.get("framework_id", ""), body.get("action", ""), body.get("user", "User"), body.get("role", "cio"))
        return JSONResponse({"ok": True, "message": msg})

    @app.post("/api/framework-onboarding/reuse-decision")
    async def api_framework_reuse_decision(request: Request):
        from app.auth.mutation_guard import guard_mutation
        from modules.frameworks.engines.framework_onboarding_engine import apply_evidence_reuse

        body = await request.json()
        deny = guard_mutation(request, "can_reuse_evidence_decision",
                              fallback_role=body.get("role", "owner"), response="json")
        if deny:
            return deny
        msg = apply_evidence_reuse(
            body.get("framework_id", ""), body.get("control_id", ""),
            body.get("decision", "reuse"), body.get("user", "User"), body.get("role", "owner"),
        )
        return JSONResponse({"ok": True, "message": msg})

    @app.get("/api/framework-onboarding/{framework_id}")
    def api_framework_onboarding_get(framework_id: str):
        from modules.frameworks.engines.framework_onboarding_engine import get_onboarding_record
        rec = get_onboarding_record(framework_id)
        if not rec:
            return JSONResponse({"ok": False, "error": "Not found"}, status_code=404)
        return JSONResponse({"ok": True, "record": rec})

    @app.get("/mvp/framework-admin/export/{framework_id}")
    def mvp_framework_export(framework_id: str, format: str = "pdf", role: str = "cio", user: str = "User"):
        from modules.frameworks.engines.framework_onboarding_engine import export_onboarding_analysis
        try:
            content, media_type, filename = export_onboarding_analysis(framework_id, format)
            return Response(content=content, media_type=media_type, headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            })
        except ValueError as e:
            return PlainTextResponse(str(e), status_code=404)

    @app.get("/mvp/lifecycle", response_class=HTMLResponse)
    def mvp_lifecycle(request: Request, role: str = "owner", user: str = "User", response: str = ""):
        ctx = _base_ctx(role, user, response, page_module="lifecycle")
        ctx["timeline"] = lifecycle_timeline()
        ctx["statuses"] = ecs_state.LIFECYCLE_STATUSES
        ctx["rows"] = ecs_state.build_evidence_analytics()["evidence_rows"]
        return templates.TemplateResponse(request, "mvp_lifecycle.html", ctx)

    @app.get("/mvp/comparison", response_class=HTMLResponse)
    def mvp_comparison(
        request: Request,
        role: str = "cio",
        user: str = "CIO",
        response: str = "",
        notice: str = "",
        export_id: str = "",
    ):
        ctx = _base_ctx(role, user, response, notice, page_module="comparison")
        ctx["comparison"] = application_comparison()
        ctx["export_id"] = export_id
        return templates.TemplateResponse(request, "mvp_comparison.html", ctx)

    @app.post("/mvp/comparison/export-gaps")
    async def mvp_comparison_export_gaps(
        role: str = Form(...),
        user: str = Form(...),
        compare_framework: str = Form("All Frameworks"),
        compare_scope: str = Form("All Applications"),
        compare_application: str = Form("All Applications"),
        time_range: str = Form("Current Month"),
        export_format: str = Form("excel"),
        include_executive: str = Form("on"),
        include_observations: str = Form("on"),
        include_failed: str = Form("on"),
        include_missing: str = Form("on"),
        include_audit_impact: str = Form("on"),
    ):
        from modules.shared.services.audit_trail import log_event
        from modules.governance.engines.gap_export_engine import (
            build_gap_export_payload,
            generate_gap_export_file,
            record_export,
        )

        def _on(val: str) -> bool:
            return val in ("on", "true", "1", "yes")

        payload = build_gap_export_payload(
            framework=compare_framework,
            scope=compare_scope,
            time_range=time_range,
            application=compare_application,
            role=role,
            include_executive=_on(include_executive),
            include_observations=_on(include_observations),
            include_failed=_on(include_failed),
            include_missing=_on(include_missing),
            include_audit_impact=_on(include_audit_impact),
        )
        content, media_type, filename = generate_gap_export_file(payload, export_format)
        entry = record_export(
            user=user,
            role=role,
            fmt=export_format,
            filename=filename,
            payload=payload,
            content_bytes=content,
            content_type=media_type,
        )
        log_event(
            "Gap Analysis Export",
            user,
            compare_framework,
            compare_application,
            f"{filename} — {payload['meta']['record_count']} records",
            role=role,
        )
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Export-Id": entry["export_id"],
                "X-Export-Preview": entry["preview_path"],
            },
        )

    @app.get("/mvp/exports/download/{export_id}")
    def mvp_export_download(export_id: str, user: str = "User"):
        from modules.shared.services.ecs_logging import log_export

        rec = ecs_state.export_registry.get(export_id)
        if not rec:
            return PlainTextResponse("Export not found.", status_code=404)
        try:
            log_export(user, export_id)
        except Exception:
            pass
        return Response(
            content=rec["content_bytes"],
            media_type=rec["content_type"],
            headers={"Content-Disposition": f'attachment; filename="{rec["filename"]}"'},
        )

    @app.get("/mvp/exports/preview/{export_id}", response_class=HTMLResponse)
    def mvp_export_preview(export_id: str):
        from modules.governance.engines.gap_export_engine import build_html_preview

        rec = ecs_state.export_registry.get(export_id)
        if not rec:
            return HTMLResponse("<p>Export not found.</p>", status_code=404)
        payload = rec.get("payload")
        if not payload:
            return HTMLResponse("<p>Preview unavailable for this export.</p>", status_code=404)
        return HTMLResponse(build_html_preview(payload))

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
    def mvp_report_download(
        report_id: str,
        user: str = "User",
        role: str = "owner",
        format: str = "pdf",
        framework: str = "",
        application: str = "",
    ):
        try:
            from modules.shared.services.ecs_logging import log_export
            log_export(user, report_id)
        except Exception:
            pass
        fmt = (format or "pdf").lower()
        if fmt in ("pdf", "excel", "csv", "xlsx"):
            if fmt == "xlsx":
                fmt = "excel"
            content, media_type, filename = generate_report_export(
                report_id, fmt, role=role, user=user, framework=framework, application=application,
            )
            ecs_state.export_history.insert(0, {
                "export_id": report_id,
                "title": report_id,
                "format": fmt.upper(),
                "framework": framework or "Enterprise-wide",
                "application": application or "All Applications",
                "timestamp": filename.split("_")[-1].replace(f".{fmt if fmt != 'excel' else 'xlsx'}", ""),
                "generated_by": user,
                "status": "Generated",
                "download_path": f"/mvp/reports/download/{report_id}?format={fmt}&user={quote(user)}&role={quote(role)}",
            })
            return Response(content=content, media_type=media_type, headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            })
        content = generate_report_content(report_id)
        return PlainTextResponse(content, media_type="text/plain", headers={
            "Content-Disposition": f'attachment; filename="{report_id}-ecs-report.txt"'
        })

    @app.get("/mvp/audit-prep", response_class=HTMLResponse)
    def mvp_audit_prep(
        request: Request,
        role: str = "auditor",
        user: str = "Auditor",
        response: str = "",
        notice: str = "",
        fw_filter: str = "",
        app_filter: str = "",
        risk_filter: str = "",
        status_filter: str = "",
        owner_filter: str = "",
        show_modal: str = "",
    ):
        filters = {
            "framework": fw_filter,
            "application": app_filter,
            "risk": risk_filter,
            "status": status_filter,
            "owner": owner_filter,
        }
        ctx = _base_ctx(role, user, response, notice, page_module="audit_prep", analytics_filters=filters)
        ctx["prep"] = audit_preparation_checklist()
        ctx["audit_filters"] = filters
        ctx["show_modal"] = show_modal
        from modules.governance.engines.audit_prep_data import build_audit_package_preview, build_export_bundle_preview
        ctx["package_preview"] = build_audit_package_preview(filters=filters)
        ctx["export_preview"] = build_export_bundle_preview(filters)
        ctx["mock_audit_frameworks"] = list(__import__("app.governance_relational_model", fromlist=["FRAMEWORK_GRAPHS"]).FRAMEWORK_GRAPHS.keys())
        return templates.TemplateResponse(request, "mvp_audit_prep.html", ctx)

    @app.get("/mvp/workflow/close-gap", response_class=HTMLResponse)
    def workflow_close_gap_get(
        request: Request,
        role: str = "auditor",
        user: str = "Auditor",
        framework: str = "",
        control: str = "",
        return_module: str = "audit_prep",
        notice: str = "",
    ):
        from modules.governance.engines.operational_workflows import build_close_gap_view

        ctx = _base_ctx(role, user, notice=notice, page_module=return_module or "audit_prep")
        ctx.update(build_close_gap_view(framework, control, role, user, return_module))
        return templates.TemplateResponse(request, "mvp_workflow_close_gap.html", ctx)

    @app.post("/mvp/workflow/close-gap")
    def workflow_close_gap_post(
        role: str = Form(...),
        user: str = Form(...),
        framework: str = Form(""),
        control: str = Form(""),
        submit_type: str = Form(...),
        root_cause: str = Form(""),
        remediation_plan: str = Form(""),
        target_date: str = Form(""),
        return_module: str = Form("audit_prep"),
    ):
        from modules.governance.engines.operational_workflows import _return_url, process_close_gap

        notice = process_close_gap(
            framework=framework,
            control=control,
            user=user,
            role=role,
            submit_type=submit_type,
            root_cause=root_cause,
            remediation_plan=remediation_plan,
            target_date=target_date,
        )
        dest = _return_url(role, user, return_module)
        return RedirectResponse(url=f"{dest}&notice={quote(notice)}", status_code=303)

    @app.get("/mvp/workflow/assign-owner", response_class=HTMLResponse)
    def workflow_assign_owner_get(
        request: Request,
        role: str = "auditor",
        user: str = "Auditor",
        framework: str = "",
        control: str = "",
        return_module: str = "audit_prep",
        notice: str = "",
    ):
        from modules.governance.engines.operational_workflows import build_assign_owner_view

        ctx = _base_ctx(role, user, notice=notice, page_module=return_module or "audit_prep")
        ctx.update(build_assign_owner_view(framework, control, role, user, return_module))
        return templates.TemplateResponse(request, "mvp_workflow_assign_owner.html", ctx)

    @app.post("/mvp/workflow/assign-owner")
    def workflow_assign_owner_post(
        request: Request,
        role: str = Form(...),
        user: str = Form(...),
        framework: str = Form(""),
        control: str = Form(""),
        submit_type: str = Form(...),
        team: str = Form("Application Owner"),
        priority: str = Form("High"),
        sla_days: str = Form("5"),
        escalation_level: str = Form("L1"),
        comments: str = Form(""),
        return_module: str = Form("audit_prep"),
    ):
        from app.auth.mutation_guard import guard_mutation
        from modules.governance.engines.operational_workflows import _return_url, process_assign_owner

        deny = guard_mutation(request, "can_assign_owner", fallback_role=role,
                              deny_redirect_to=_return_url(role, user, return_module),
                              role=role, user=user)
        if deny:
            return deny

        notice = process_assign_owner(
            framework=framework,
            control=control,
            user=user,
            role=role,
            submit_type=submit_type,
            team=team,
            priority=priority,
            sla_days=sla_days,
            escalation_level=escalation_level,
            comments=comments,
        )
        dest = _return_url(role, user, return_module)
        return RedirectResponse(url=f"{dest}&notice={quote(notice)}", status_code=303)

    @app.get("/mvp/workflow/upload-missing", response_class=HTMLResponse)
    def workflow_upload_missing_get(
        request: Request,
        role: str = "owner",
        user: str = "User",
        framework: str = "",
        control: str = "",
        observation_id: str = "",
        return_module: str = "audit_prep",
        notice: str = "",
    ):
        from modules.governance.engines.operational_workflows import build_upload_missing_view
        from modules.shared.services.role_permissions import guard_upload

        deny = guard_upload(role, user, f"/mvp/{return_module.replace('_', '-')}")
        if deny:
            return deny
        ctx = _base_ctx(role, user, notice=notice, page_module=return_module or "audit_prep")
        ctx.update(build_upload_missing_view(framework, control, role, user, return_module, observation_id))
        return templates.TemplateResponse(request, "mvp_workflow_upload_missing.html", ctx)

    @app.post("/mvp/workflow/upload-missing")
    async def workflow_upload_missing_post(
        role: str = Form(...),
        user: str = Form(...),
        framework: str = Form(""),
        control: str = Form(""),
        observation_id: str = Form(""),
        submit_type: str = Form(...),
        evidence_comments: str = Form(""),
        mock_filename: str = Form(""),
        evidence_category: str = Form(""),
        remediation_owner: str = Form(""),
        expected_closure: str = Form(""),
        sharepoint_link: str = Form(""),
        servicenow_ticket: str = Form(""),
        jira_remediation: str = Form(""),
        return_module: str = Form("audit_prep"),
        evidence_file: UploadFile | None = File(None),
    ):
        from modules.governance.engines.operational_workflows import _return_url, process_upload_missing
        from modules.shared.services.role_permissions import guard_upload

        deny = guard_upload(role, user, f"/mvp/{return_module.replace('_', '-')}")
        if deny:
            return deny
        fname = mock_filename
        if evidence_file and evidence_file.filename:
            fname = evidence_file.filename
        linked = " · ".join(filter(None, [sharepoint_link, servicenow_ticket, jira_remediation]))
        notice = process_upload_missing(
            framework=framework,
            control=control,
            user=user,
            role=role,
            submit_type=submit_type,
            evidence_comments=evidence_comments,
            linked_source=linked,
            filename=fname,
            observation_id=observation_id,
            evidence_category=evidence_category,
            remediation_owner=remediation_owner,
            expected_closure=expected_closure,
        )
        dest = _return_url(role, user, return_module)
        toast = "uploaded" if submit_type == "submit_review" else ""
        sep = "&" if "?" in dest else "?"
        url = f"{dest}{sep}notice={quote(notice)}"
        if toast:
            url += f"&toast={toast}"
        return RedirectResponse(url=url, status_code=303)

    @app.post("/mvp/exceptions/raise")
    def mvp_raise_exception(
        role: str = Form(...),
        user: str = Form(...),
        framework: str = Form(...),
        application: str = Form("Net Banking"),
        control: str = Form(""),
        control_id: str = Form(""),
        justification: str = Form(...),
        compensating_control: str = Form(""),
        observation_id: str = Form(""),
        evidence_id: str = Form(""),
        td_expiry: str = Form("2026-09-30"),
        residual_risk: str = Form("Medium"),
        return_url: str = Form("/mvp/exceptions"),
    ):
        from modules.governance.engines.exception_state_engine import create_exception
        from modules.shared.services.role_permissions import can_raise_exception, deny_redirect

        if not can_raise_exception(role):
            return deny_redirect(role, user, return_url or "/mvp/exceptions")
        try:
            eid, _ = create_exception(
                framework=framework,
                application=application,
                control=control,
                control_id=control_id,
                justification=justification,
                compensating_control=compensating_control,
                observation_id=observation_id,
                evidence_id=evidence_id,
                td_expiry=td_expiry,
                residual_risk=residual_risk,
                user=user,
                role=role,
                submit=True,
            )
            notice = f"Exception {eid} raised successfully — routed to approver workflow."
            base = return_url or f"/mvp/exceptions?role={quote(role)}&user={quote(user)}"
            sep = "&" if "?" in base else "?"
            return RedirectResponse(
                url=f"{base}{sep}notice={quote(notice)}&toast=exception_ok&exception_id={quote(eid)}",
                status_code=303,
            )
        except Exception:
            base = return_url or f"/mvp/exceptions?role={quote(role)}&user={quote(user)}"
            sep = "&" if "?" in base else "?"
            return RedirectResponse(
                url=f"{base}{sep}notice={quote('Failed to raise exception — please retry or contact admin.')}&toast=exception_fail",
                status_code=303,
            )

    @app.post("/api/exceptions/raise")
    async def api_raise_exception(request: Request):
        from modules.governance.engines.exception_state_engine import create_exception
        from modules.shared.services.role_permissions import can_raise_exception

        body = await request.json()
        role = body.get("role", "owner")
        user = body.get("user", "User")
        if not can_raise_exception(role):
            return JSONResponse({"ok": False, "error": "Permission denied"}, status_code=403)
        try:
            eid, rec = create_exception(
                framework=body.get("framework", "PCI DSS"),
                application=body.get("application", "Net Banking"),
                control=body.get("control", ""),
                control_id=body.get("control_id", ""),
                justification=body.get("justification", "Business justification pending"),
                compensating_control=body.get("compensating_control", ""),
                observation_id=body.get("observation_id", ""),
                evidence_id=body.get("evidence_id", ""),
                td_expiry=body.get("td_expiry", "2026-09-30"),
                residual_risk=body.get("residual_risk", "Medium"),
                user=user,
                role=role,
                submit=True,
            )
            return JSONResponse({"ok": True, "exception_id": eid, "record": rec})
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)

    @app.post("/mvp/workflow/request-reupload")
    def workflow_request_reupload_post(
        role: str = Form(...),
        user: str = Form(...),
        observation_id: str = Form(""),
        framework: str = Form(""),
        control: str = Form(""),
        comments: str = Form(""),
        return_module: str = Form("audit_prep"),
    ):
        from modules.governance.engines.missing_evidence_engine import apply_request_reupload
        from modules.governance.engines.operational_workflows import _return_url
        from modules.shared.services.role_permissions import can_request_reupload, deny_redirect

        if not can_request_reupload(role):
            return deny_redirect(role, user, f"/mvp/{return_module.replace('_', '-')}")
        notice = apply_request_reupload(observation_id, user, role, comments=comments) if observation_id else "Observation ID required."
        dest = _return_url(role, user, return_module)
        return RedirectResponse(url=f"{dest}&notice={quote(notice)}", status_code=303)

    @app.get("/mvp/workflow/mock-audit", response_class=HTMLResponse)
    def workflow_mock_audit_get(
        request: Request,
        role: str = "auditor",
        user: str = "Auditor",
        executed: int = 0,
        return_module: str = "audit_prep",
        notice: str = "",
    ):
        from modules.governance.engines.operational_workflows import build_mock_audit_view

        ctx = _base_ctx(role, user, notice=notice, page_module="audit_prep")
        ctx.update(build_mock_audit_view(role, user, executed=bool(executed), return_module=return_module))
        return templates.TemplateResponse(request, "mvp_workflow_mock_audit.html", ctx)

    @app.post("/mvp/workflow/mock-audit/execute")
    def workflow_mock_audit_execute(
        role: str = Form(...),
        user: str = Form(...),
        return_module: str = Form("audit_prep"),
        framework: str = Form("PCI DSS"),
        applications: str = Form(""),
        auditor: str = Form("Deloitte"),
        audit_cycle: str = Form("Q2 2026"),
    ):
        from modules.governance.engines.operational_workflows import execute_mock_audit

        execute_mock_audit(user, role, framework=framework, applications=applications, auditor=auditor, audit_cycle=audit_cycle)
        return RedirectResponse(
            url=f"/mvp/workflow/mock-audit?role={role}&user={user}&executed=1&return_module={return_module}&notice={quote('Mock audit simulation complete — review summary report below.')}",
            status_code=303,
        )

    @app.post("/mvp/workflow/mock-audit/action")
    def workflow_mock_audit_action(
        role: str = Form(...),
        user: str = Form(...),
        submit_type: str = Form(...),
        return_module: str = Form("audit_prep"),
    ):
        from modules.governance.engines.operational_workflows import _return_url, process_mock_audit_action

        notice = process_mock_audit_action(submit_type, user, role)
        dest = _return_url(role, user, return_module)
        return RedirectResponse(url=f"{dest}&notice={quote(notice)}", status_code=303)

    @app.get("/mvp/workflow/mock-audit/report", response_class=PlainTextResponse)
    def workflow_mock_audit_report(audit_id: str = ""):
        from modules.governance.engines.operational_workflows import generate_mock_audit_report

        return PlainTextResponse(generate_mock_audit_report(audit_id), media_type="text/plain")

    @app.get("/mvp/trends", response_class=HTMLResponse)
    def mvp_trends(
        request: Request,
        role: str = "cio",
        user: str = "CIO",
        response: str = "",
        framework: str = "Enterprise-wide",
        application: str = "All Applications",
        risk_level: str = "All",
        audit_cycle: str = "Q2 2026 Audit Cycle",
        time_period: str = "Last 6 months",
        region: str = "All Regions",
        business_unit: str = "All Units",
    ):
        from modules.governance.engines.governance_intelligence import get_filter_options, parse_analytics_filters

        filters = parse_analytics_filters(
            framework=framework,
            application=application,
            risk_level=risk_level,
            audit_cycle=audit_cycle,
            time_period=time_period,
            region=region,
            business_unit=business_unit,
        )
        ctx = _base_ctx(role, user, response, page_module="trends", analytics_filters=filters)
        ctx["trends"] = compliance_trends(filters)
        ctx["analytics"] = ecs_state.build_evidence_analytics()
        ctx["analytics_filters"] = filters
        ctx["filter_options"] = get_filter_options()
        return templates.TemplateResponse(request, "mvp_trends.html", ctx)

    @app.get("/mvp/api/analytics-intel", response_class=JSONResponse)
    def mvp_api_analytics_intel(
        framework: str = "Enterprise-wide",
        application: str = "All Applications",
        risk_level: str = "All",
        audit_cycle: str = "Q2 2026 Audit Cycle",
        time_period: str = "Last 6 months",
        region: str = "All Regions",
        business_unit: str = "All Units",
    ):
        from modules.governance.engines.governance_intelligence import build_contextual_trends, parse_analytics_filters

        filters = parse_analytics_filters(
            framework=framework,
            application=application,
            risk_level=risk_level,
            audit_cycle=audit_cycle,
            time_period=time_period,
            region=region,
            business_unit=business_unit,
        )
        intel = build_contextual_trends(filters)
        return JSONResponse({
            "intel": intel,
            "kpis": intel["executive_kpis"],
            "scope_summary": intel["scope_summary"],
        })

    @app.get("/api/ecs/filters/options", response_class=JSONResponse)
    def api_ecs_filter_options(role: str = "owner"):
        from modules.shared.utils.global_filter_engine import filter_options

        return JSONResponse(filter_options(role))

    @app.post("/api/ecs/filters/apply", response_class=JSONResponse)
    async def api_ecs_filters_apply(request: Request):
        from modules.shared.utils.global_filter_engine import apply_filters

        body = await request.json()
        module = body.get("module", "")
        role = body.get("role", "owner")
        filters = body.get("filters") or {}
        if not module:
            return JSONResponse({"error": "module required"}, status_code=400)
        return JSONResponse(apply_filters(module, role, filters))

    @app.get("/mvp/risk-register", response_class=HTMLResponse)
    def mvp_risk_register(request: Request, role: str = "owner", user: str = "User", notice: str = ""):
        return templates.TemplateResponse(request, "mvp_risk_register.html", _base_ctx(role, user, notice=notice, page_module="risk_register"))

    @app.get("/mvp/exceptions", response_class=HTMLResponse)
    def mvp_exceptions(request: Request, role: str = "owner", user: str = "User", notice: str = ""):
        return templates.TemplateResponse(request, "mvp_exceptions.html", _base_ctx(role, user, notice=notice, page_module="exceptions_td"))

    @app.get("/mvp/evidence-approval", response_class=HTMLResponse)
    def mvp_evidence_approval(request: Request, role: str = "owner", user: str = "User", notice: str = ""):
        return templates.TemplateResponse(request, "mvp_evidence_approval.html", _base_ctx(role, user, notice=notice, page_module="evidence_approval"))

    @app.get("/mvp/exception-governance", response_class=HTMLResponse)
    def mvp_exception_governance(request: Request, role: str = "owner", user: str = "User", notice: str = ""):
        return templates.TemplateResponse(request, "mvp_exception_governance.html", _base_ctx(role, user, notice=notice, page_module="exception_governance"))

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
        from modules.operations.engines.integrations_module import simulate_sync
        simulate_sync(connector)
        notice = quote(f"Integrations Hub sync complete for {connector}")
        return RedirectResponse(url=f"/mvp/integrations-hub?role={role}&user={user}&notice={notice}", status_code=303)

    @app.get("/mvp/correlation", response_class=HTMLResponse)
    def mvp_correlation(request: Request, role: str = "owner", user: str = "User", notice: str = ""):
        return templates.TemplateResponse(request, "mvp_correlation.html", _base_ctx(role, user, notice=notice, page_module="correlation"))

    @app.get("/mvp/governance-analytics", response_class=HTMLResponse)
    def mvp_governance_analytics(
        request: Request,
        role: str = "cio",
        user: str = "CIO",
        notice: str = "",
        framework: str = "Enterprise-wide",
        application: str = "All Applications",
        risk_level: str = "All",
        audit_cycle: str = "Q2 2026 Audit Cycle",
        time_period: str = "Last 6 months",
        region: str = "All Regions",
        business_unit: str = "All Units",
    ):
        from modules.governance.engines.governance_intelligence import get_filter_options, parse_analytics_filters

        filters = parse_analytics_filters(
            framework=framework,
            application=application,
            risk_level=risk_level,
            audit_cycle=audit_cycle,
            time_period=time_period,
            region=region,
            business_unit=business_unit,
        )
        ctx = _base_ctx(role, user, notice=notice, page_module="governance_analytics", analytics_filters=filters)
        ctx["analytics_filters"] = filters
        ctx["filter_options"] = get_filter_options()
        return templates.TemplateResponse(request, "mvp_governance_analytics.html", ctx)

    @app.post("/mvp/grc/action")
    def mvp_grc_action(
        module: str = Form(...),
        action: str = Form(...),
        role: str = Form(...),
        user: str = Form(...),
        item_id: str = Form(""),
    ):
        from modules.enterprise_grc.engines.enterprise_grc import execute_grc_action
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
        from modules.shared.services.audit_trail import log_event
        from modules.governance.engines.analytics_module import completeness_report

        workflow_actions = {"close_gap", "assign_owner", "assign_gap", "upload_missing", "mock_audit", "request_reupload"}
        if action in workflow_actions:
            from modules.shared.services.role_permissions import action_allowed, guard_upload

            if action == "upload_missing":
                deny = guard_upload(role, user, f"/mvp/{module.replace('_', '-')}")
                if deny:
                    return deny
            elif not action_allowed(role, action):
                from modules.shared.services.role_permissions import deny_redirect
                return deny_redirect(role, user, f"/mvp/{module.replace('_', '-')}")
            framework = ""
            if item_id:
                for m in completeness_report()["missing"]:
                    if m["control"] == item_id:
                        framework = m["framework"]
                        break
            flow_map = {
                "close_gap": "close-gap",
                "assign_owner": "assign-owner",
                "assign_gap": "assign-owner",
                "upload_missing": "upload-missing",
                "mock_audit": "mock-audit",
                "request_reupload": "request-reupload",
            }
            flow = flow_map.get(action)
            if flow:
                q = f"role={quote(role)}&user={quote(user)}&return_module={quote(module)}"
                if item_id:
                    q += f"&control={quote(item_id)}"
                if framework:
                    q += f"&framework={quote(framework)}"
                return RedirectResponse(url=f"/mvp/workflow/{flow}?{q}", status_code=303)

        if module == "audit_prep" and action == "escalate":
            from modules.shared.services.audit_trail import log_event
            log_event("Audit Gap Escalated", user, "", item_id, "Escalated to CISO office from Audit Prep", role=role)
            return RedirectResponse(
                url=f"/mvp/audit-prep?role={role}&user={user}&notice={quote('Gap escalated to CISO office — executive queue updated.')}",
                status_code=303,
            )
        if module == "audit_prep" and action == "generate_package":
            from modules.governance.engines.audit_prep_data import build_audit_package_preview
            from modules.shared.services.audit_trail import log_event
            preview = build_audit_package_preview()
            log_event("Audit Package Generated", user, "", preview["package_name"], preview["auditor_notes"], role=role)
            fq = f"role={role}&user={user}&show_modal=package&notice={quote('Audit package ' + preview['package_name'] + ' generated — review preview below.')}"
            return RedirectResponse(url=f"/mvp/audit-prep?{fq}", status_code=303)
        if module == "audit_prep" and action == "export_pdf":
            from modules.governance.engines.audit_prep_data import build_export_bundle_preview
            from modules.shared.services.audit_trail import log_event
            preview = build_export_bundle_preview()
            log_event("Evidence Bundle Export", user, "", preview["bundle_name"], preview["scope"], role=role)
            fq = f"role={role}&user={user}&show_modal=export&notice={quote('Export bundle ' + preview['bundle_name'] + ' ready for download.')}"
            return RedirectResponse(url=f"/mvp/audit-prep?{fq}", status_code=303)

        label = action.replace("_", " ").title()
        log_event(f"Module: {label}", user, "", item_id, f"{module} capability action")
        if module == "scheduler" and action == "run_now":
            result = run_scheduled_pull(user=user)
            notice = (
                f"Scheduler run completed — {result['observations_scanned']} observations scanned, "
                f"{result['new_findings']} new findings detected."
            )
            return _module_redirect(module, role, user, notice)
        if module == "scheduler" and action == "retry" and item_id:
            result = retry_failed_observation(item_id, user)
            return _module_redirect(module, role, user, result["message"])
        if module == "scheduler" and action == "pause":
            from modules.operations.engines.scheduler_module import pause_scheduler
            notice = pause_scheduler(user)
            return _module_redirect(module, role, user, notice)
        if module == "scheduler" and action == "resume":
            from modules.operations.engines.scheduler_module import resume_scheduler
            notice = resume_scheduler(user)
            return _module_redirect(module, role, user, notice)
        if module == "integrations" and action == "sync_now" and item_id:
            simulate_sync(item_id)
        if module == "integrations_hub":
            from modules.operations.engines.integrations_module import simulate_sync as hub_sync, test_connection, retry_failed_sync
            if action == "sync_now" and item_id:
                hub_sync(item_id)
            elif action == "test_connection" and item_id:
                notice = test_connection(item_id)
                return _module_redirect(module, role, user, notice)
            elif action == "retry_failed_sync" and item_id:
                notice = retry_failed_sync(item_id)
                return _module_redirect(module, role, user, notice)
        if module in ("risk_register", "exceptions_td", "exception_governance", "cmdb", "regulatory_mapping", "executive_heatmaps", "correlation", "governance_analytics", "evidence_approval"):
            from modules.enterprise_grc.engines.enterprise_grc import execute_grc_action
            notice = execute_grc_action(module, action, item_id, user, role)
            return _module_redirect(module, role, user, notice)
        if module == "reports" and action in ("export_pdf", "export_excel", "export_csv") and item_id:
            fmt = "pdf" if action == "export_pdf" else ("csv" if action == "export_csv" else "excel")
            return RedirectResponse(
                url=f"/mvp/reports/download/{item_id}?format={fmt}&role={quote(role)}&user={quote(user)}",
                status_code=303,
            )
        if module == "reports" and action == "generate" and item_id:
            return RedirectResponse(
                url=f"/mvp/reports/download/{item_id}?format=pdf&role={quote(role)}&user={quote(user)}",
                status_code=303,
            )
        if module == "pan_india" and action == "export_regional":
            from modules.shared.services.ecs_state import PAN_INDIA_REGIONS
            import csv, io
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=["region", "score", "branches", "applications", "observations_open", "audit_readiness_pct"])
            w.writeheader()
            rows = PAN_INDIA_REGIONS if not item_id else [r for r in PAN_INDIA_REGIONS if r["region"] == item_id]
            for row in rows:
                w.writerow(row)
            content = buf.getvalue().encode("utf-8-sig")
            fname = f"PanIndia_{item_id or 'AllRegions'}_2026_05.csv"
            return Response(content=content, media_type="text/csv", headers={
                "Content-Disposition": f'attachment; filename="{fname}"',
            })
        if module == "governance_analytics" and action == "export_chart":
            content = (
                "ECS Governance Analytics Export\n"
                f"Generated by: {user}\n"
                f"Module: governance_analytics\n"
                f"Item: {item_id or 'overview'}\n"
                "Metric,Value\nAudit Readiness,78\nOpen Observations,42\nStale Evidence,18\n"
            ).encode("utf-8")
            return Response(content=content, media_type="text/csv", headers={
                "Content-Disposition": 'attachment; filename="governance_analytics_export.csv"',
            })
        if module == "evidence_approval" and action == "export_summary":
            from modules.governance.engines.evidence_approval_engine import build_evidence_approval_view
            dash = build_evidence_approval_view(role)
            lines = ["Evidence Approval Summary Export", f"Generated by: {user}"]
            for kpi in dash.get("kpis", []):
                lines.append(f"{kpi['label']},{kpi['value']}")
            content = "\n".join(lines).encode("utf-8")
            return Response(content=content, media_type="text/csv", headers={
                "Content-Disposition": 'attachment; filename="evidence_approval_summary.csv"',
            })
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
        from modules.shared.services.ecs_logging import log_chatbot

        log_chatbot(user, role, query, framework_name)
        response = chatbot_answer(query, role=role, user=user, framework_hint=framework_name)
        encoded = quote(response)
        sep = "&" if "?" in return_url else "?"
        return RedirectResponse(url=f"{return_url}{sep}response={encoded}", status_code=303)

    @app.post("/mvp/api/chat-response-mode")
    def mvp_chat_response_mode(
        scenario_key: str = Form(...),
        mode: str = Form(...),
        role: str = Form(...),
        user: str = Form(...),
    ):
        from modules.operations.engines.operations_intelligence import OUTAGE_SCENARIOS, _build_summary_html
        from modules.operations.engines.ai_ops_response_modes import render_response_mode

        scenario = OUTAGE_SCENARIOS.get(scenario_key)
        if not scenario or mode not in (
            "business", "technical", "executive", "audit",
            "compliance", "evidence", "incident", "root_cause",
        ):
            return JSONResponse({"ok": False, "error": "invalid scenario or mode"}, status_code=400)
        mode_html = render_response_mode(scenario, mode, scenario_key, role, user)
        shell_html = _build_summary_html(scenario, scenario_key, role, active_mode=mode)
        from modules.shared.services.chatbot_engine import get_chat_structured, set_chat_structured

        existing = get_chat_structured(user, role)
        if existing and "ecsOpsInvestigation" in existing:
            set_chat_structured(user, role, shell_html)
        return JSONResponse({"ok": True, "mode": mode, "html": mode_html, "shell_html": shell_html})

    @app.post("/mvp/api/chat-investigation")
    def mvp_chat_investigation(
        query: str = Form(...),
        role: str = Form(...),
        user: str = Form(...),
    ):
        """Fresh investigation — clear history and return a single Q&A pair."""
        from app.main import chatbot_answer
        from modules.shared.services.chatbot_engine import (
            clear_chat_history,
            clear_chat_structured,
            get_chat_structured,
        )
        from modules.shared.services.ecs_logging import log_chatbot

        log_chatbot(user, role, query, "")
        clear_chat_history(user, role)
        clear_chat_structured(user, role)
        plain = chatbot_answer(query, role=role, user=user)
        html = get_chat_structured(user, role)
        if not html:
            from html import escape

            html = f'<pre class="mb-0 small" style="white-space:pre-wrap;">{escape(plain)}</pre>'
        return JSONResponse({"ok": True, "query": query, "plain": plain, "html": html})

    @app.post("/mvp/api/chat-action")
    def mvp_chat_action(
        action: str = Form(...),
        role: str = Form(...),
        user: str = Form(...),
        scenario: str = Form(""),
    ):
        from modules.shared.services.chatbot_context_engine import execute_quick_action
        from modules.shared.services.chatbot_engine import get_context, record_exchange, set_chat_structured
        from modules.operations.engines.operations_intelligence import OUTAGE_SCENARIOS, _build_summary_html

        ctx = get_context(user, role)
        if scenario:
            ctx["active_outage"] = scenario
        plain, html = execute_quick_action(action, user, role, scenario)
        if scenario and scenario in OUTAGE_SCENARIOS:
            html = _build_summary_html(OUTAGE_SCENARIOS[scenario], scenario, role) + html
        set_chat_structured(user, role, html)
        record_exchange(user, role, f"@chat-action:{action}", plain)
        return {"ok": True, "html": html, "plain": plain, "context": ctx}
