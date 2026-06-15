
# IMPORTANT: load .env into os.environ BEFORE any other app/* or modules/*
# import so DEMO_MODE / ECS_AUTH_ENABLED are available when authentication,
# RBAC and page guards initialise. Must remain the first import.
from app import env_bootstrap as _env_bootstrap  # noqa: F401  (side-effect: loads .env)

import os
from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import ecs_state
from modules.shared.services.chatbot_enhanced import (
    FALLBACK,
    format_chatbot_response,
    try_enhanced_answer,
    try_framework_definition,
)
from modules.executive_overview.engines.demo_seed import seed_demo_workflow_state
from modules.operations.engines.evidence_repository import refresh_repository_from_frameworks
from modules.frameworks.engines.framework_catalog import (
    catalog_stats,
    get_framework_controls,
    resolve_framework_name,
)
from modules.frameworks.engines.framework_dashboards import build_framework_dashboard
from modules.shared.services.enterprise_context import enterprise_widgets_context
from modules.shared.services.audit_trail import log_event, record_approval, record_rejection
from modules.governance.engines.evidence_review import build_evidence_review, review_url, review_url_for_ev
from app.routes_mvp import register_mvp_routes
from app.evidence_routes import register_evidence_routes
from modules.shared.services.role_permissions import permission_ctx
from modules.shared.services.evidence_workflow_engine import (
    build_workflow_context,
    close_observations_for_control,
    observation_id_for,
    record_transition,
    toast_payload,
)
from modules.governance.engines.workflow_module import (
    build_auditor_review_queue,
    build_closed_observations_queue,
    build_owner_work_queue,
    work_queue_summary,
)

def _workflow_redirect(
    role: str,
    user: str,
    framework_name: str = "",
    return_to: str = "framework",
    notice: str = "",
    toast: str = "",
    obs_id: str = "",
):
    if return_to == "dashboard":
        url = f"/dashboard?role={role}&user={user}"
    elif return_to == "review":
        url = f"/framework/{framework_name}?role={role}&user={user}"
    else:
        url = f"/framework/{framework_name}?role={role}&user={user}"
    if toast:
        url += f"&toast={quote(toast)}"
    if obs_id:
        url += f"&obs_id={quote(obs_id)}"
    if notice:
        url += f"&notice={quote(notice)}"
    return RedirectResponse(url=url, status_code=303)


def _redirect_with_toast(
    role: str,
    user: str,
    dest_url: str,
    action: str,
    *,
    framework: str,
    control: str,
    detail: str = "",
) -> RedirectResponse:
    tp = toast_payload(action, framework=framework, control=control, detail=detail)
    record_transition(ecs_state.control_key(framework, control), action, user, role, tp["body"])
    sep = "&" if "?" in dest_url else "?"
    url = (
        f"{dest_url}{sep}toast={quote(action)}&obs_id={quote(tp['observation_id'])}"
        f"&notice={quote(tp['body'])}"
    )
    return RedirectResponse(url=url, status_code=303)

@asynccontextmanager
async def ecs_lifespan(application: FastAPI):
    from modules.shared.services.ecs_logging import configure_logging, log_platform_ready, mark_startup_complete
    from modules.shared.services import ecs_logging as _ecs_log
    from app.env_bootstrap import ENV_STATUS

    configure_logging()
    # ---- ECS Startup banner: surface demo-mode flags loaded from .env ----
    _ecs_log.info("ECSStartup", "ECS Startup")
    _ecs_log.info("ECSStartup", f"DEMO_MODE={os.environ.get('DEMO_MODE', '')}")
    _ecs_log.info("ECSStartup", f"ECS_AUTH_ENABLED={os.environ.get('ECS_AUTH_ENABLED', '')}")
    _ecs_log.info("ECSStartup",
                  f".env loaded={ENV_STATUS.get('loaded')} via {ENV_STATUS.get('parser')}")
    refresh_repository_from_frameworks(source="startup")
    seed_demo_workflow_state()
    from modules.enterprise_grc.engines.ecs_governance_qa_engine import self_heal_governance
    self_heal_governance()
    from modules.operations.engines.predefined_queries_engine import validate_startup
    from modules.shared.services import ecs_logging

    pq_report = validate_startup()
    for line in pq_report.get("log_lines", []):
        ecs_logging.info("PredefinedQueries", line)

    # Best-effort evidence repository schema init (never blocks startup).
    try:
        from ecs_platform.ingestion import init_repository

        repo_status = init_repository()
        if repo_status.get("ok"):
            ecs_logging.info("ECSPlatform", "Evidence repository schema ready")
            from ecs_platform.governance import init_governance_schema

            gov_status = init_governance_schema()
            if gov_status.get("ok"):
                ecs_logging.info("ECSPlatform", "Governance schema ready")
            else:
                ecs_logging.info("ECSPlatform", f"Governance schema skipped: {gov_status.get('error', '')}")
        else:
            ecs_logging.info("ECSPlatform", f"Evidence repository unavailable: {repo_status.get('error', '')}")
    except Exception as exc:  # noqa: BLE001
        ecs_logging.info("ECSPlatform", f"Evidence repository init skipped: {exc}")

    # Phase 4 Step 3: durable observation hydration (flag-gated, best-effort).
    # Reloads persisted observations into in-memory state so the lifecycle survives
    # restart without any dashboard change. No-op when OBSERVATIONS_DURABLE_ENABLED
    # is off; never blocks startup.
    try:
        from app.observations.store import durable_observations_enabled, hydrate_into_memory

        if durable_observations_enabled():
            n = hydrate_into_memory()
            ecs_logging.info("ECSPlatform", f"Durable observations hydrated: {n} record(s)")
    except Exception as exc:  # noqa: BLE001
        ecs_logging.info("ECSPlatform", f"Observation hydration skipped: {exc}")

    # LLM-RAG startup validation (non-fatal): report whether Gemini is configured
    # and reachable, plus how much of the repository is indexed. Secrets never logged.
    try:
        from ecs_platform.rag import rag_status

        st = rag_status()
        if st.get("provider_configured"):
            ecs_logging.info("ECSPlatform",
                             f"LLM-RAG ready: provider={st['provider']} model={st['model']} "
                             f"vector_chunks={st['vector_count']} indexed={st['indexed_pct']}%")
            # Warm local models in the background so the first query isn't a cold start.
            import threading

            from ecs_platform.rag import warm_models

            threading.Thread(target=warm_models, daemon=True).start()
        else:
            ecs_logging.info("ECSPlatform",
                             "LLM-RAG disabled: provider not configured (assistant uses deterministic fallback)")
    except Exception as exc:  # noqa: BLE001
        ecs_logging.info("ECSPlatform", f"LLM-RAG status check skipped: {exc}")

    mark_startup_complete()
    log_platform_ready(host="127.0.0.1", port=8000)
    yield


app = FastAPI(title="ECS Consolidated Demo V13", lifespan=ecs_lifespan)


@app.middleware("http")
async def _no_cache_html(request, call_next):
    """Force browsers to revalidate dynamic HTML pages.

    Page templates carry inline <style>/<script>, so a cached HTML page keeps
    rendering stale CSS/JS even after a fix is deployed (observed: Chrome showing
    the pre-fix sidebar while Safari showed the corrected layout). Sending
    no-cache on HTML guarantees the browser re-fetches the current markup.
    Static assets under /static keep their own caching (versioned via ?v=).
    """
    response = await call_next(request)
    try:
        ctype = response.headers.get("content-type", "")
        if ctype.startswith("text/html") and not request.url.path.startswith("/static"):
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
    except Exception:
        pass
    return response


app.mount("/static/ecs", StaticFiles(directory="modules/shared/static"), name="ecs_static")

# ---- Phase 1: Authentication foundation (Azure AD / OIDC / JWT) ----
# Installs central auth middleware (pass-through when auth is disabled in config)
# and maps authentication failures to proper HTTP responses. No authorization
# (RBAC) decisions are made here.
from app.auth import register_authentication
from app.auth.errors import AuthenticationError as _AuthError
from fastapi.responses import JSONResponse as _JSONResponse

register_authentication(app)


@app.exception_handler(_AuthError)
async def _auth_exception_handler(request: Request, exc: _AuthError):
    headers = {"WWW-Authenticate": "Bearer"} if exc.http_status == 401 else {}
    return _JSONResponse(
        {"error": "unauthorized", "reason": exc.reason, "detail": exc.detail},
        status_code=exc.http_status,
        headers=headers,
    )

from jinja2 import ChoiceLoader, Environment, FileSystemLoader

_template_dirs = [
    "modules/shared/templates",
    "modules/executive_overview/templates",
    "modules/frameworks/templates",
    "modules/operations/templates",
    "modules/governance/templates",
    "modules/enterprise_grc/templates",
    "modules/ai_sdlc/templates",
    "app/templates",
]
templates = Jinja2Templates(
    env=Environment(loader=ChoiceLoader([FileSystemLoader(d) for d in _template_dirs]))
)
templates.env.globals["review_url"] = review_url
templates.env.globals["review_url_for_ev"] = review_url_for_ev


def asset_ver(rel_path: str) -> str:
    """Cache-busting version token for a static asset (file mtime).

    Static JS/CSS is served without Cache-Control and at an unversioned URL, so
    browsers cache it indefinitely and keep running stale code after a deploy.
    Appending ?v=<mtime> forces a fresh fetch whenever the file changes.
    """
    import os
    candidates = [
        os.path.join("modules/shared/static", rel_path),
        os.path.join("static", rel_path),
        os.path.join("app/static", rel_path),
    ]
    for path in candidates:
        try:
            return str(int(os.path.getmtime(path)))
        except OSError:
            continue
    return "1"


templates.env.globals["asset_ver"] = asset_ver

# Re-export shared state for backward compatibility with existing code paths
PCI_DSS_MOCK_EVIDENCES = ecs_state.PCI_DSS_MOCK_EVIDENCES
frameworks = ecs_state.frameworks
submitted_controls = ecs_state.submitted_controls
approved_controls = ecs_state.approved_controls
rejected_controls = ecs_state.rejected_controls
scheduler_data = ecs_state.scheduler_data
control_key = ecs_state.control_key
control_status = ecs_state.control_status
build_evidence_analytics = ecs_state.build_evidence_analytics


def chatbot_answer(query: str, role: str = "owner", user: str = "User", framework_hint: str = ""):
    q = query.lower()

    fw_hint = framework_hint
    if not fw_hint:
        for name in ecs_state.frameworks:
            if name.lower() in q:
                fw_hint = name
                break

    enhanced = try_enhanced_answer(query, role=role, user=user)
    if enhanced:
        return enhanced

    definition = try_framework_definition(query)
    if definition:
        from modules.shared.services.chatbot_engine import record_exchange
        record_exchange(user, role, query, definition)
        return definition

    if "reject" in q or "rejection" in q or ("reason" in q and "rejected" in q):
        if not ecs_state.rejected_controls:
            return format_chatbot_response(
                "No rejected evidences in the current workflow state.",
                fw_hint,
            )
        lines = []
        for key, info in list(ecs_state.rejected_controls.items())[:8]:
            _framework, control = key.split("::", 1)
            lines.append(f"{control} ({_framework}): {info['reason']}")
        ans = format_chatbot_response(
            "Rejected evidences and reasons — " + " | ".join(lines),
            fw_hint,
        )
        from modules.shared.services.chatbot_engine import record_exchange
        record_exchange(user, role, query, ans)
        return ans

    from modules.shared.services.chatbot_engine import process_query, record_exchange
    clarification = process_query(query, role=role, user=user)
    if clarification:
        return clarification

    ans = format_chatbot_response(FALLBACK, fw_hint)
    record_exchange(user, role, query, ans)
    return ans


@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={},
    )


@app.post("/login")
def login(role: str = Form(...)):
    from modules.shared.services.ecs_logging import log_login

    if role == "cio":
        log_login("cio", "CIO", "CIO dashboard")
        return RedirectResponse(
            url="/dashboard/cio?role=cio&user=CIO",
            status_code=303,
        )
    if role == "vertical_head":
        log_login("vertical_head", "VerticalHead", "Vertical Head dashboard")
        return RedirectResponse(
            url="/dashboard/vertical-head?role=vertical_head&user=VerticalHead",
            status_code=303,
        )
    if role == "compliance_head" or role == "compliance_officer":
        log_login("compliance_head", "ComplianceOfficer", "Compliance Head dashboard")
        return RedirectResponse(
            url="/dashboard/compliance-head?role=compliance_head&user=ComplianceOfficer",
            status_code=303,
        )
    if role == "functional_head":
        log_login("functional_head", "FunctionalHead", "Functional Head dashboard")
        return RedirectResponse(
            url="/dashboard/functional-head?role=functional_head&user=FunctionalHead",
            status_code=303,
        )
    if role == "security_officer":
        log_login("security_officer", "SecurityOfficer", "Security Officer dashboard")
        return RedirectResponse(
            url="/dashboard/compliance-head?role=security_officer&user=SecurityOfficer",
            status_code=303,
        )
    if role == "operations_owner":
        log_login("operations_owner", "OpsOwner", "Operations onboarding")
        return RedirectResponse(
            url="/mvp/onboarding?role=operations_owner&user=OpsOwner",
            status_code=303,
        )
    if role == "ai_governance_owner":
        log_login("ai_governance_owner", "AIGovOwner", "AI governance posture")
        return RedirectResponse(
            url="/mvp/ai-governance?role=ai_governance_owner&user=AIGovOwner",
            status_code=303,
        )
    if role == "ai_sdlc_owner":
        log_login("ai_sdlc_owner", "SDLCOwner", "AI SDLC home")
        return RedirectResponse(
            url="/mvp/ai-sdlc?role=ai_sdlc_owner&user=SDLCOwner",
            status_code=303,
        )
    if role == "framework_owner":
        log_login("framework_owner", "FrameworkOwner", "Framework administration")
        return RedirectResponse(
            url="/mvp/framework-admin?role=framework_owner&user=FrameworkOwner",
            status_code=303,
        )

    user = "AppOwner" if role == "owner" else "Auditor"
    log_login(role, user, "role dashboard")

    return RedirectResponse(
        url=f"/dashboard?role={role}&user={user}",
        status_code=303,
    )


@app.get("/logout")
def logout():
    return RedirectResponse("/", status_code=303)


@app.get("/access-denied", response_class=HTMLResponse)
def access_denied(page: str = "", role: str = "", user: str = "", home: str = "/"):
    """Lightweight, reusable access-denied page (Phase 2 Step 2C).

    Rendered when page authorization denies a browser request. Standalone HTML so it
    never depends on a role-specific template context."""
    from app.auth.page_guard import _access_denied_html

    reason = f"Role '{role or 'unknown'}' is not authorized for '{page or 'this page'}'."
    return HTMLResponse(
        _access_denied_html(user=user, role=role, page=page, reason=reason, home=home or "/"),
        status_code=403,
    )


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    role: str = "owner",
    user: str = "User",
    response: str = "",
    notice: str = "",
):
    from app.auth.scope import apply_scope

    # Phase 2 Step 3: scope-filter the owner work queue to the principal's assigned
    # applications (flag-gated; pass-through when off or for enterprise roles).
    owner_queue = build_owner_work_queue() if role == "owner" else []
    owner_queue = apply_scope(request, owner_queue, fallback_role=role)
    ctx = {
        "frameworks": frameworks.keys(),
        "scheduler_data": scheduler_data,
        "role": role,
        "user": user,
        "response": response,
        "notice": notice,
        "rejected_controls": rejected_controls,
        "owner_work_queue": owner_queue,
        "auditor_review_queue": build_auditor_review_queue() if role == "auditor" else [],
        "closed_observations_queue": build_closed_observations_queue() if role == "auditor" else [],
        "work_queue_summary": work_queue_summary(),
    }
    ctx.update(enterprise_widgets_context(role, user=user))
    ctx.update(permission_ctx(role))
    ctx["evidence_workflow"] = build_workflow_context(role)
    ctx["nav_active"] = "main_dashboard"
    return templates.TemplateResponse(request=request, name="dashboard.html", context=ctx)


@app.get("/dashboard/cio", response_class=HTMLResponse)
def cio_dashboard(
    request: Request,
    role: str = "cio",
    user: str = "CIO",
    response: str = "",
):
    from app.auth.page_guard import guard_page

    deny = guard_page(request, "dashboard.cio", fallback_role=role, user=user,
                      home=f"/dashboard?role={role}&user={user}", page_label="CIO dashboard")
    if deny:
        return deny
    from modules.executive_overview.engines.demo_metrics import display_framework_maturity

    analytics = build_evidence_analytics()
    analytics["framework_stats"] = display_framework_maturity(analytics["framework_stats"])
    ctx = {
        "frameworks": frameworks.keys(),
        "scheduler_data": scheduler_data,
        "role": role,
        "user": user,
        "response": response,
        "analytics": analytics,
        "rejected_controls": rejected_controls,
    }
    ctx.update(enterprise_widgets_context(role, user=user))
    return templates.TemplateResponse(request=request, name="cio_dashboard.html", context=ctx)


@app.post("/chat")
def chat(
    query: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    framework_name: str = Form(""),
):
    response = chatbot_answer(query, role=role, user=user, framework_hint=framework_name)
    from modules.shared.services.ecs_logging import log_chatbot

    log_chatbot(user, role, query, framework_name)
    encoded = quote(response)

    if role == "cio":
        return RedirectResponse(
            url=f"/dashboard/cio?role={role}&user={user}&response={encoded}",
            status_code=303,
        )
    if role == "vertical_head":
        return RedirectResponse(
            url=f"/dashboard/vertical-head?role={role}&user={user}&response={encoded}",
            status_code=303,
        )
    if role == "compliance_head" or role == "compliance_officer":
        return RedirectResponse(
            url=f"/dashboard/compliance-head?role=compliance_head&user={user}&response={encoded}",
            status_code=303,
        )
    if role == "functional_head":
        return RedirectResponse(
            url=f"/dashboard/functional-head?role={role}&user={user}&response={encoded}",
            status_code=303,
        )

    if framework_name:
        return RedirectResponse(
            url=f"/framework/{framework_name}?role={role}&user={user}&response={encoded}",
            status_code=303,
        )

    return RedirectResponse(
        url=f"/dashboard?role={role}&user={user}&response={encoded}",
        status_code=303,
    )


@app.post("/itpp/action")
def itpp_action(
    action: str = Form(...),
    domain: str = Form(""),
    role: str = Form("owner"),
    user: str = Form("User"),
):
    from modules.frameworks.engines.itpp_module import execute_itpp_action

    notice = execute_itpp_action(action, domain, user, role)
    return RedirectResponse(
        url=f"/framework/ITPP?role={role}&user={user}&notice={quote(notice)}",
        status_code=303,
    )


@app.get("/framework/{framework_name}", response_class=HTMLResponse)
def framework_page(
    request: Request,
    framework_name: str,
    role: str = "owner",
    user: str = "User",
    response: str = "",
    notice: str = "",
    itpp_view: str = "",
    itpp_domain: str = "",
    itpp_app: str = "",
    fw_app: str = "",
    fw_tab: str = "applications",
):
    catalog_controls = get_framework_controls(framework_name)
    resolved_fw = resolve_framework_name(framework_name)
    fw_evidence_count = sum(len(c["evidences"]) for c in catalog_controls)

    ctx = {
        "framework_name": framework_name,
        "frameworks": frameworks.keys(),
        "controls": frameworks.get(framework_name, []),
        "framework_catalog_controls": catalog_controls,
        "framework_evidence_count": fw_evidence_count,
        "framework_control_count": len(catalog_controls),
        "catalog_stats": catalog_stats(),
        "fw_dashboard": build_framework_dashboard(resolved_fw, catalog_controls),
        "role": role,
        "user": user,
        "response": response,
        "notice": notice,
        "submitted_controls": submitted_controls,
        "approved_controls": approved_controls,
        "rejected_controls": rejected_controls,
        "itpp_view": itpp_view,
        "itpp_domain": itpp_domain,
        "itpp_app": itpp_app,
        "fw_app": fw_app,
        "fw_tab": fw_tab,
    }
    from modules.frameworks.engines.application_governance import build_application_grid, build_application_view

    ctx["application_grid"] = build_application_grid(framework_name, catalog_controls)
    ctx["application_view"] = build_application_view(framework_name, fw_app, catalog_controls) if fw_app else None
    if framework_name == "ITPP":
        from modules.frameworks.engines.itpp_module import (
            build_itpp_app_view,
            build_itpp_domain_view,
            build_itpp_landing_cards,
        )

        ctx["itpp_landing_cards"] = build_itpp_landing_cards()
        ctx["itpp_domain_view"] = build_itpp_domain_view(itpp_domain) if itpp_domain else None
        ctx["itpp_app_view"] = (
            build_itpp_app_view(itpp_domain, itpp_app, catalog_controls)
            if itpp_domain and itpp_app
            else None
        )
    ctx.update(enterprise_widgets_context(role, page_module="framework", framework=resolved_fw, user=user))
    from modules.shared.services.ecs_logging import log_navigation

    log_navigation(user, role, f"{framework_name} framework dashboard")
    return templates.TemplateResponse(
        request=request,
        name="framework.html",
        context=ctx,
    )


@app.get("/api/framework/kpi-drill")
def api_framework_kpi_drill(framework: str = "", metric: str = ""):
    from fastapi.responses import JSONResponse

    from modules.frameworks.engines.framework_kpi_drill_engine import drill_framework_kpi
    from modules.frameworks.engines.framework_catalog import resolve_framework_name

    fw = resolve_framework_name(framework) if framework else framework
    if not fw or not metric:
        return JSONResponse({"ok": False, "error": "framework and metric required"}, status_code=400)
    return JSONResponse(drill_framework_kpi(fw, metric))


@app.get("/api/framework/workflow-drill")
def api_framework_workflow_drill(framework: str = "", metric: str = ""):
    from fastapi.responses import JSONResponse

    from modules.frameworks.engines.framework_catalog import resolve_framework_name
    from modules.frameworks.engines.framework_workflow_engine import drill_framework_workflow

    fw = resolve_framework_name(framework) if framework else framework
    if not fw or not metric:
        return JSONResponse({"ok": False, "error": "framework and metric required"}, status_code=400)
    return JSONResponse(drill_framework_workflow(fw, metric))


@app.get("/api/framework/row-drill")
def api_framework_row_drill(framework: str = "", type: str = "", id: str = ""):
    from fastapi.responses import JSONResponse

    from modules.frameworks.engines.ecs_row_drill_engine import drill_framework_row
    from modules.frameworks.engines.framework_catalog import resolve_framework_name

    fw = resolve_framework_name(framework) if framework else framework
    if not fw:
        return JSONResponse({"ok": False, "error": "framework required"}, status_code=400)
    return JSONResponse(drill_framework_row(fw, type, id))


@app.get("/api/framework/tab-drill")
def api_framework_tab_drill(framework: str = "", tab: str = ""):
    from fastapi.responses import JSONResponse

    from modules.frameworks.engines.ecs_row_drill_engine import drill_framework_row
    from modules.frameworks.engines.framework_catalog import resolve_framework_name

    fw = resolve_framework_name(framework) if framework else framework
    if not fw or not tab:
        return JSONResponse({"ok": False, "error": "framework and tab required"}, status_code=400)
    tab_map = {
        "applications": ("application", "all"),
        "controls": ("control", "all"),
        "control-library": ("control", "all"),
        "evidence": ("evidence", "repository"),
        "findings": ("finding", "open"),
        "pending": ("pending", "actions"),
        "integrations": ("integration", "hub"),
        "exceptions": ("exception", "register"),
        "reuse": ("reuse", "mapping"),
        "trends": ("trend", "analytics"),
    }
    row_type, row_id = tab_map.get(tab, (tab, "all"))
    return JSONResponse(drill_framework_row(fw, row_type, row_id))


@app.get("/evidence/review", response_class=HTMLResponse)
def evidence_review_page(
    request: Request,
    framework_name: str,
    evidence_id: str,
    role: str = "owner",
    user: str = "User",
    notice: str = "",
    control_name: str = "",
):
    review = build_evidence_review(framework_name, control_name, evidence_id, role, user)
    if not review:
        fw = resolve_framework_name(framework_name)
        review = build_evidence_review(fw, control_name, evidence_id or "EV-SYNTH", role, user)
    ctx = {
        "framework_name": framework_name,
        "frameworks": frameworks.keys(),
        "role": role,
        "user": user,
        "notice": notice,
        "review": review,
        "submitted_controls": submitted_controls,
        "approved_controls": approved_controls,
        "rejected_controls": rejected_controls,
    }
    ctx.update(enterprise_widgets_context(role, framework=resolve_framework_name(framework_name), user=user))
    return templates.TemplateResponse(request, "evidence_review.html", ctx)


@app.post("/evidence/review/close-observation")
def evidence_review_close_observation(
    request: Request,
    framework_name: str = Form(...),
    control_name: str = Form(...),
    evidence_id: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    observation_id: str = Form(""),
):
    from modules.shared.services.role_permissions import guard_auditor_governance

    deny = guard_auditor_governance(role, user, f"/framework/{framework_name}")
    if deny:
        return deny
    key = control_key(framework_name, control_name)
    if key not in approved_controls:
        return _review_redirect(
            framework_name, role, user,
            "Approve evidence before closing the observation.",
            control_name, evidence_id,
        )
    closed = close_observations_for_control(
        framework_name, control_name, "", user, role, auto=False,
    )
    if observation_id and observation_id not in ecs_state.closed_observations:
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        ecs_state.closed_observations[observation_id] = {
            "observation_id": observation_id,
            "closed_by": user,
            "closed_at": ts,
            "detail": "Manually closed by auditor",
        }
        from app.observations.store import persist_close

        persist_close(observation_id, closed_by=user, role=role,
                      detail={"framework": framework_name, "control": control_name})
        closed.append(observation_id)
    obs = observation_id or (closed[0] if closed else "")
    body = f"Observation {obs} closed successfully." if obs else "Observation closed."
    tp = toast_payload("approved", framework=framework_name, control=control_name, observation_id=obs, detail=body)
    from app.audit.workflow import audit_workflow_action

    audit_workflow_action(
        request, "observation.close", resource=obs or key,
        fallback_actor=user, fallback_role=role,
        before_state={"status": "Open"}, after_state={"status": "Closed"},
        detail={"framework": framework_name, "control": control_name,
                "observation_id": obs})
    return _review_redirect(
        framework_name, role, user, body, control_name, evidence_id,
        toast="approved", obs_id=obs or tp["observation_id"],
    )


def _review_redirect(framework_name: str, role: str, user: str, notice: str, control_name: str = "", evidence_id: str = "", toast: str = "", obs_id: str = ""):
    if control_name and evidence_id:
        url = review_url(framework_name, control_name, evidence_id, role, user)
    else:
        url = f"/framework/{framework_name}?role={role}&user={user}"
    if toast:
        url += f"&toast={quote(toast)}"
    if obs_id:
        url += f"&obs_id={quote(obs_id)}"
    if notice:
        url += f"&notice={quote(notice)}"
    return RedirectResponse(url=url, status_code=303)


@app.post("/evidence/review/submit")
def evidence_review_submit(
    request: Request,
    framework_name: str = Form(...),
    control_name: str = Form(...),
    evidence_id: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
):
    from modules.shared.services.role_permissions import guard_submit_to_auditor

    deny = guard_submit_to_auditor(role, user, f"/framework/{framework_name}")
    if deny:
        return deny
    key = control_key(framework_name, control_name)
    _audit_before = {"status": control_status(framework_name, control_name)}
    if key in approved_controls:
        return _review_redirect(framework_name, role, user, "Cannot resubmit: observation is closed.", control_name, evidence_id)
    was_rejected = key in rejected_controls
    if was_rejected:
        from modules.operations.engines.resubmission import can_resubmit_to_auditor

        if not can_resubmit_to_auditor(key):
            return _review_redirect(
                framework_name, role, user,
                "Complete resubmission steps before submitting to Auditor.",
                control_name, evidence_id,
            )
        del rejected_controls[key]
    if key in ecs_state.clarification_controls:
        del ecs_state.clarification_controls[key]
    if key in ecs_state.cancelled_drafts:
        ecs_state.cancelled_drafts.discard(key)
    submitted_controls[key] = "Pending Auditor Review"
    from datetime import datetime, timezone

    ecs_state.submitted_meta[key] = {
        "submitted_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "submitted_by": user,
    }
    if key in ecs_state.owner_drafts:
        del ecs_state.owner_drafts[key]
    log_event(
        "Evidence Submitted",
        user,
        framework_name,
        control_name,
        "Submitted to auditor — Pending Auditor Review",
        evidence_id,
        role=role or "App Owner",
    )
    notice = "Resubmitted to Auditor for review." if was_rejected else "Submitted To Auditor — Pending Auditor Review."
    tp = toast_payload("submitted", framework=framework_name, control=control_name)
    record_transition(key, "submitted", user, role, tp["body"])
    from app.audit.workflow import audit_workflow_action

    audit_workflow_action(
        request, "evidence.submit", resource=key,
        fallback_actor=user, fallback_role=role,
        before_state=_audit_before, after_state={"status": "Pending Auditor Review"},
        detail={"framework": framework_name, "control": control_name,
                "evidence_id": evidence_id, "resubmission": was_rejected})
    return _review_redirect(framework_name, role, user, tp["body"], control_name, evidence_id, toast="submitted", obs_id=tp["observation_id"])


@app.post("/evidence/review/approve")
def evidence_review_approve(
    request: Request,
    framework_name: str = Form(...),
    control_name: str = Form(...),
    evidence_id: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
):
    from modules.shared.services.role_permissions import guard_auditor_governance

    deny = guard_auditor_governance(role, user, f"/framework/{framework_name}")
    if deny:
        return deny
    return approve(
        request,
        control_name=control_name,
        framework_name=framework_name,
        role=role,
        user=user,
        return_to="review",
        evidence_id=evidence_id,
    )


@app.post("/evidence/review/reject")
def evidence_review_reject(
    request: Request,
    framework_name: str = Form(...),
    control_name: str = Form(...),
    evidence_id: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    reject_reason: str = Form(...),
):
    from modules.shared.services.role_permissions import guard_auditor_governance

    deny = guard_auditor_governance(role, user, f"/framework/{framework_name}")
    if deny:
        return deny
    return reject(
        request,
        control_name=control_name,
        framework_name=framework_name,
        role=role,
        user=user,
        reject_reason=reject_reason,
        return_to="review",
        evidence_id=evidence_id,
    )


@app.post("/evidence/review/clarify")
def evidence_review_clarify(
    framework_name: str = Form(...),
    control_name: str = Form(...),
    evidence_id: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    message: str = Form(...),
):
    from modules.shared.services.role_permissions import guard_auditor_governance

    deny = guard_auditor_governance(role, user, f"/framework/{framework_name}")
    if deny:
        return deny
    workflow_clarify(
        control_name=control_name,
        framework_name=framework_name,
        role=role,
        user=user,
        message=message,
    )
    return _review_redirect(framework_name, role, user, "Clarification requested from App Owner.", control_name, evidence_id)


@app.post("/evidence/review/request-reupload")
def evidence_review_request_reupload(
    framework_name: str = Form(...),
    control_name: str = Form(...),
    evidence_id: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    message: str = Form(""),
):
    from datetime import datetime, timezone

    from modules.shared.services.role_permissions import can_request_reupload, deny_redirect

    if not can_request_reupload(role):
        return deny_redirect(role, user, f"/framework/{framework_name}")
    key = control_key(framework_name, control_name)
    if key in submitted_controls:
        del submitted_controls[key]
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    ecs_state.clarification_controls[key] = {
        "message": message or "Auditor has requested re-upload. App Owner to coordinate revised evidence.",
        "requested_by": user,
        "type": "reupload_requested",
        "requested_at": ts,
    }
    log_event(
        "Re-upload Requested by Auditor",
        user,
        framework_name,
        control_name,
        message or "Evidence returned to App Owner queue for re-upload",
        evidence_id,
        role=role or "Auditor",
    )
    tp = toast_payload("reupload", framework=framework_name, control=control_name, detail=message)
    record_transition(key, "reupload", user, role, tp["body"])
    return _review_redirect(
        framework_name, role, user, tp["body"],
        control_name, evidence_id, toast="reupload", obs_id=tp["observation_id"],
    )


@app.post("/evidence/review/reject-internal")
def evidence_review_reject_internal(
    request: Request,
    framework_name: str = Form(...),
    control_name: str = Form(...),
    evidence_id: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    reject_reason: str = Form(...),
):
    from app.auth.mutation_guard import guard_mutation

    deny = guard_mutation(request, "can_upload_evidence", fallback_role=role,
                          deny_redirect_to=f"/framework/{framework_name}", role=role, user=user)
    if deny:
        return deny
    from datetime import datetime, timezone

    reason = reject_reason.strip()
    key = control_key(framework_name, control_name)
    ecs_state.rejected_controls[key] = {
        "reason": reason or "Rejected internally by App Owner — quality review failed.",
        "rejected_by": user,
        "rejected_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "internal": True,
        "resubmission_stage": "owner_review",
    }
    if key in submitted_controls:
        del submitted_controls[key]
    log_event("Rejected Internally", user, framework_name, control_name, reason, evidence_id, role=role)
    return _review_redirect(framework_name, role, user, "Evidence rejected internally.", control_name, evidence_id)


@app.post("/evidence/review/save-draft")
def evidence_review_save_draft(
    framework_name: str = Form(...),
    control_name: str = Form(...),
    evidence_id: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    owner_note: str = Form(""),
):
    from datetime import datetime, timezone

    key = control_key(framework_name, control_name)
    ecs_state.owner_drafts[key] = {
        "saved_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "saved_by": user,
        "note": owner_note.strip(),
    }
    log_event("Draft Saved", user, framework_name, control_name, owner_note[:120] or "Draft saved", evidence_id, role=role)
    return _review_redirect(framework_name, role, user, "Draft saved.", control_name, evidence_id)


@app.post("/evidence/review/cancel")
def evidence_review_cancel(
    framework_name: str = Form(...),
    control_name: str = Form(...),
    evidence_id: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
):
    workflow_cancel(control_name=control_name, framework_name=framework_name, role=role, user=user)
    return RedirectResponse(
        url=f"/framework/{framework_name}?role={role}&user={user}&notice={quote('Draft cancelled.')}",
        status_code=303,
    )


@app.post("/evidence/review/request-resubmission")
def evidence_review_request_resubmission(
    framework_name: str = Form(...),
    control_name: str = Form(...),
    evidence_id: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
):
    from modules.operations.engines.resubmission import advance_stage

    key = control_key(framework_name, control_name)
    advance_stage(key, "team_resubmission")
    log_event("Team Resubmission Requested", user, framework_name, control_name, "Assigned to team for revised upload", evidence_id, role=role or "App Owner")
    return _review_redirect(framework_name, role, user, "Team resubmission requested.", control_name, evidence_id)


@app.post("/evidence/review/upload-revised")
def evidence_review_upload_revised(
    framework_name: str = Form(...),
    control_name: str = Form(...),
    evidence_id: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
):
    from modules.shared.services.role_permissions import guard_upload

    deny = guard_upload(role, user, f"/framework/{framework_name}")
    if deny:
        return deny
    from modules.operations.engines.resubmission import advance_stage

    key = control_key(framework_name, control_name)
    advance_stage(key, "reevaluate")
    log_event("Revised Evidence Uploaded", user, framework_name, control_name, "Revised artefact recorded", evidence_id, role=role or "App Owner")
    return _review_redirect(framework_name, role, user, "Revised evidence uploaded.", control_name, evidence_id)


@app.post("/evidence/review/reevaluate")
def evidence_review_reevaluate(
    framework_name: str = Form(...),
    control_name: str = Form(...),
    evidence_id: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
):
    from modules.operations.engines.resubmission import advance_stage

    key = control_key(framework_name, control_name)
    advance_stage(key, "ready_resubmit")
    log_event("Evidence Re-evaluated", user, framework_name, control_name, "Ready for auditor resubmission", evidence_id, role=role or "App Owner")
    return _review_redirect(framework_name, role, user, "Re-evaluation complete — ready to resubmit to Auditor.", control_name, evidence_id)


@app.post("/submit")
def submit(
    request: Request,
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    return_to: str = Form("framework"),
):
    from modules.shared.services.role_permissions import guard_submit_to_auditor

    deny = guard_submit_to_auditor(role, user, f"/framework/{framework_name}")
    if deny:
        return deny
    key = control_key(framework_name, control_name)
    _audit_before = {"status": control_status(framework_name, control_name)}
    if key in approved_controls:
        notice = "Cannot resubmit: observation is closed and auditor approved."
        return _workflow_redirect(role, user, framework_name, return_to, notice)

    was_rejected = key in rejected_controls
    if was_rejected:
        from modules.operations.engines.resubmission import can_resubmit_to_auditor

        if not can_resubmit_to_auditor(key):
            return _workflow_redirect(
                role, user, framework_name, return_to,
                "Complete resubmission steps before submitting to Auditor.",
            )
        del rejected_controls[key]
    if key in ecs_state.clarification_controls:
        del ecs_state.clarification_controls[key]
    if key in ecs_state.cancelled_drafts:
        ecs_state.cancelled_drafts.discard(key)
    submitted_controls[key] = "Pending Auditor Review"
    from datetime import datetime, timezone

    ecs_state.submitted_meta[key] = {
        "submitted_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "submitted_by": user,
    }
    if key in ecs_state.owner_drafts:
        del ecs_state.owner_drafts[key]
    log_event(
        "Evidence Submitted",
        user,
        framework_name,
        control_name,
        "Submitted to auditor — Pending Auditor Review",
        role=role or "App Owner",
    )

    notice = f"Evidence resubmitted for {control_name}." if was_rejected else f"Submitted {control_name} to auditor review."
    tp = toast_payload("submitted", framework=framework_name, control=control_name)
    record_transition(key, "submitted", user, role, tp["body"])
    from app.audit.workflow import audit_workflow_action

    audit_workflow_action(
        request, "evidence.submit", resource=key,
        fallback_actor=user, fallback_role=role,
        before_state=_audit_before, after_state={"status": "Pending Auditor Review"},
        detail={"framework": framework_name, "control": control_name,
                "resubmission": was_rejected})
    return _workflow_redirect(role, user, framework_name, return_to, tp["body"], toast="submitted", obs_id=tp["observation_id"])


@app.post("/approve")
def approve(
    request: Request,
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    return_to: str = Form("framework"),
    evidence_id: str = Form(""),
):
    from modules.shared.services.role_permissions import guard_auditor_governance

    deny = guard_auditor_governance(role, user, f"/framework/{framework_name}")
    if deny:
        return deny
    key = control_key(framework_name, control_name)
    _audit_before = {"status": control_status(framework_name, control_name)}
    from datetime import datetime, timezone

    approved_controls[key] = {
        "status": "Auditor Approved",
        "approved_by": user,
        "approved_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "note": "Observation Closed — Auditor Approved",
    }
    if key in rejected_controls:
        del rejected_controls[key]
    if key in submitted_controls:
        del submitted_controls[key]
    if key in ecs_state.escalated_controls:
        del ecs_state.escalated_controls[key]
    if key in ecs_state.clarification_controls:
        del ecs_state.clarification_controls[key]
    if key in ecs_state.submitted_meta:
        del ecs_state.submitted_meta[key]
    record_approval(framework_name, control_name, user, "Observation Closed - Auditor Approved")

    closed = close_observations_for_control(framework_name, control_name, "", user, role, auto=True)
    tp = toast_payload("approved", framework=framework_name, control=control_name)
    if closed:
        tp["body"] = f"Observation {closed[0]} closed successfully."
        tp["observation_id"] = closed[0]
    record_transition(key, "approved", user, role, tp["body"])
    from app.audit.workflow import audit_workflow_action

    audit_workflow_action(
        request, "evidence.approve", resource=key,
        fallback_actor=user, fallback_role=role,
        before_state=_audit_before, after_state={"status": "Auditor Approved"},
        detail={"framework": framework_name, "control": control_name,
                "observation_id": tp.get("observation_id", "")})
    if return_to == "review" and evidence_id:
        return _review_redirect(framework_name, role, user, tp["body"], control_name, evidence_id, toast="approved", obs_id=tp["observation_id"])
    return _workflow_redirect(role, user, framework_name, return_to, tp["body"], toast="approved", obs_id=tp["observation_id"])


@app.post("/reject")
def reject(
    request: Request,
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    reject_reason: str = Form(...),
    return_to: str = Form("framework"),
    evidence_id: str = Form(""),
):
    from modules.shared.services.role_permissions import guard_auditor_governance

    deny = guard_auditor_governance(role, user, f"/framework/{framework_name}")
    if deny:
        return deny
    reason = reject_reason.strip()
    key = control_key(framework_name, control_name)
    _audit_before = {"status": control_status(framework_name, control_name)}

    if not reason:
        return _workflow_redirect(role, user, framework_name, return_to, "Reject reason is required.")

    from modules.operations.engines.resubmission import init_rejection

    init_rejection(key, reason, user, internal=False)
    if key in approved_controls:
        del approved_controls[key]
    if key in submitted_controls:
        del submitted_controls[key]
    if key in ecs_state.escalated_controls:
        del ecs_state.escalated_controls[key]
    if key in ecs_state.clarification_controls:
        del ecs_state.clarification_controls[key]
    if key in ecs_state.submitted_meta:
        del ecs_state.submitted_meta[key]
    record_rejection(framework_name, control_name, user, reason)

    tp = toast_payload("rejected", framework=framework_name, control=control_name, detail=reason[:120])
    record_transition(key, "rejected", user, role, reason)
    from app.audit.workflow import audit_workflow_action

    audit_workflow_action(
        request, "evidence.reject", resource=key,
        fallback_actor=user, fallback_role=role,
        before_state=_audit_before, after_state={"status": "Rejected"},
        detail={"framework": framework_name, "control": control_name,
                "reason": reason[:240]})
    if return_to == "review" and evidence_id:
        return _review_redirect(framework_name, role, user, tp["body"], control_name, evidence_id, toast="rejected", obs_id=tp["observation_id"])
    return _workflow_redirect(role, user, framework_name, return_to, tp["body"], toast="rejected", obs_id=tp["observation_id"])


@app.post("/workflow/cancel")
def workflow_cancel(
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
):
    key = control_key(framework_name, control_name)
    if key in approved_controls:
        return _workflow_redirect(role, user, "", "dashboard", "Cannot cancel a closed observation.")
    ecs_state.cancelled_drafts.add(key)
    if key in submitted_controls:
        del submitted_controls[key]
    log_event("Draft Cancelled", user, framework_name, control_name, "Local draft closed by App Owner")
    return _workflow_redirect(role, user, "", "dashboard", f"Draft cancelled for {control_name}.")


@app.post("/workflow/comment")
def workflow_comment(
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    comment: str = Form(...),
):
    key = control_key(framework_name, control_name)
    text = comment.strip()
    if text:
        ecs_state.owner_comments.setdefault(key, []).append({"author": user, "text": text})
        log_event("Owner Comment Added", user, framework_name, control_name, text[:120])
    return _workflow_redirect(role, user, "", "dashboard", "Comment saved to observation record.")


@app.post("/workflow/upload-version")
def workflow_upload_version(
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    evidence_id: str = Form(""),
):
    log_event(
        "Evidence Version Uploaded",
        user,
        framework_name,
        control_name,
        f"New version staged for {evidence_id or control_name}",
        evidence_id,
    )
    return _workflow_redirect(
        role, user, "", "dashboard", f"New evidence version uploaded for {control_name} (demo)."
    )


@app.post("/workflow/escalate")
def workflow_escalate(
    request: Request,
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
):
    from app.auth.mutation_guard import guard_mutation

    deny = guard_mutation(request, "can_escalate", fallback_role=role,
                          deny_redirect_to="/dashboard", role=role, user=user)
    if deny:
        return deny
    key = control_key(framework_name, control_name)
    _audit_before = {"status": control_status(framework_name, control_name)}
    ecs_state.escalated_controls[key] = {
        "escalated_by": user,
        "reason": "Escalated to compliance leadership for high-risk review.",
    }
    log_event("Observation Escalated", user, framework_name, control_name, "Marked high-risk escalation")
    from app.audit.workflow import audit_workflow_action

    audit_workflow_action(
        request, "observation.escalate", resource=key,
        fallback_actor=user, fallback_role=role,
        before_state=_audit_before, after_state={"status": "Escalated"},
        detail={"framework": framework_name, "control": control_name})
    return _workflow_redirect(role, user, "", "dashboard", f"Escalated {control_name} to leadership queue.")


@app.post("/workflow/clarify")
def workflow_clarify(
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    message: str = Form(...),
):
    key = control_key(framework_name, control_name)
    msg = message.strip()
    if key in submitted_controls:
        del submitted_controls[key]
    ecs_state.clarification_controls[key] = {
        "requested_by": user,
        "message": msg,
    }
    if key in ecs_state.escalated_controls:
        del ecs_state.escalated_controls[key]
    if key in ecs_state.submitted_meta:
        del ecs_state.submitted_meta[key]
    log_event("Clarification Requested", user, framework_name, control_name, msg[:120])
    return _workflow_redirect(role, user, "", "dashboard", f"Clarification sent to App Owner for {control_name}.")


@app.post("/workflow/close")
def workflow_close(
    request: Request,
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
):
    return approve(
        request,
        control_name=control_name,
        framework_name=framework_name,
        role=role,
        user=user,
        return_to="dashboard",
    )


@app.post("/workflow/leadership/review")
def workflow_leadership_review(
    request: Request,
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    action: str = Form("review"),
):
    key = control_key(framework_name, control_name)
    dash_routes = {
        "cio": f"/dashboard/cio?role={role}&user={user}",
        "vertical_head": f"/dashboard/vertical-head?role={role}&user={user}",
        "compliance_head": f"/dashboard/compliance-head?role={role}&user={user}",
        "functional_head": f"/dashboard/functional-head?role={role}&user={user}",
    }
    base = dash_routes.get(role, f"/dashboard?role={role}&user={user}")

    if action in ("approve_closure", "approve"):
        return approve(
            request,
            control_name=control_name,
            framework_name=framework_name,
            role=role,
            user=user,
            return_to="dashboard",
        )
    if action == "send_back" or action == "reopen":
        from app.auth.mutation_guard import guard_mutation

        deny = guard_mutation(request, "can_escalate", fallback_role=role,
                              deny_redirect_to=base, role=role, user=user)
        if deny:
            return deny
        rejected_controls[key] = {
            "reason": f"{role} requested remediation — sent back for App Owner action.",
            "rejected_by": user,
        }
        if key in submitted_controls:
            del submitted_controls[key]
        if key in ecs_state.escalated_controls:
            del ecs_state.escalated_controls[key]
        log_event("Leadership Send Back", user, framework_name, control_name, action)
        from app.audit.workflow import audit_workflow_action

        audit_workflow_action(
            request, "observation.reopen", resource=key,
            fallback_actor=user, fallback_role=role,
            before_state={"status": "Closed"}, after_state={"status": "Open"},
            detail={"framework": framework_name, "control": control_name, "action": action})
        from app.observations.store import durable_observations_enabled, persist_reopen
        from modules.shared.services.evidence_workflow_engine import observation_id_for

        if durable_observations_enabled():
            _oid = observation_id_for(framework_name, control_name)
            # Keep durable + in-memory consistent on reopen (memory previously left
            # the closure record in place; we only change this when durability is on).
            if _oid in ecs_state.closed_observations:
                del ecs_state.closed_observations[_oid]
            persist_reopen(_oid, reopened_by=user, role=role,
                           detail={"framework": framework_name, "control": control_name})
        return RedirectResponse(url=f"{base}&notice={quote('Observation sent back to App Owner.')}", status_code=303)
    if action == "escalate_governance":
        from app.auth.mutation_guard import guard_mutation

        deny = guard_mutation(request, "can_escalate", fallback_role=role,
                              deny_redirect_to=base, role=role, user=user)
        if deny:
            return deny
        ecs_state.escalated_controls[key] = {
            "escalated_by": user,
            "reason": "Escalated to enterprise governance board by CIO.",
        }
        log_event("Governance Escalation", user, framework_name, control_name, "CIO escalation")
        return RedirectResponse(url=f"{base}&notice={quote('Escalated to governance board.')}", status_code=303)
    if action == "request_rca":
        ecs_state.clarification_controls[key] = {
            "requested_by": user,
            "message": "CIO requested root cause analysis before closure.",
        }
        if key in submitted_controls:
            del submitted_controls[key]
        log_event("RCA Requested", user, framework_name, control_name, "Executive RCA")
        return RedirectResponse(url=f"{base}&notice={quote('RCA requested from App Owner.')}", status_code=303)

    log_event("Executive Review", user, framework_name, control_name, action)
    return RedirectResponse(url=f"{base}&notice={quote(f'Review logged for {control_name}.')}", status_code=303)


register_mvp_routes(app, templates)
register_evidence_routes(app, templates)

from app.routes_platform import register_platform_routes

register_platform_routes(app, templates)

from app.routes_governance import register_governance_routes

register_governance_routes(app, templates)

from app.routes_ai_sdlc_governance import register_ai_sdlc_routes

register_ai_sdlc_routes(app, templates)

from app.routes_grc_demo import register_grc_demo_routes

register_grc_demo_routes(app)


@app.get("/api/evidence-workflow/summary")
def api_evidence_workflow_summary(role: str = "owner", user: str = "User"):
    from fastapi.responses import JSONResponse

    return JSONResponse(build_workflow_context(role)["summary"])

# Idempotent demo bootstrap for reload / TestClient when lifespan already ran
seed_demo_workflow_state()
