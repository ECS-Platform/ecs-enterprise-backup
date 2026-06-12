"""ECS governance / management capabilities (built on the evidence repository).

Application onboarding & inventory, evidence reuse, control & framework coverage,
scheduler, evidence lifecycle, audit readiness, executive summary, and a
repository-aware assistant. All heavy imports are lazy and every read degrades
gracefully when the database is unavailable.
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app import ecs_state


def register_governance_routes(app, templates):
    def _frameworks():
        try:
            return list(ecs_state.frameworks.keys())
        except Exception:  # noqa: BLE001
            return []

    def _ctx(request, role, user, nav_module, notice="", **extra):
        ctx = {"request": request, "role": role, "user": user, "notice": notice,
                "frameworks": _frameworks(), "nav_module": nav_module}
        ctx.update(extra)
        return ctx

    def _redirect(dest, role, user, notice):
        sep = "&" if "?" in dest else "?"
        return RedirectResponse(url=f"{dest}{sep}role={role}&user={quote(user)}&notice={quote(notice)}",
                                status_code=303)

    # ---------------------------------------------------------------- 1+2. Onboarding & inventory
    @app.get("/mvp/platform/onboarding", response_class=HTMLResponse)
    def gov_onboarding(request: Request, role: str = "owner", user: str = "AppOwner", notice: str = ""):
        from ecs_platform.governance import list_applications

        inv = list_applications()
        ctx = _ctx(request, role, user, "gov_onboarding", notice,
                   inv=inv, frameworks_catalog=_frameworks())
        return templates.TemplateResponse(request=request, name="gov_app_onboarding.html", context=ctx)

    @app.post("/mvp/platform/onboarding")
    def gov_onboarding_submit(
        role: str = Form("owner"), user: str = Form("AppOwner"),
        name: str = Form(...), description: str = Form(""), owner: str = Form(""),
        owner_email: str = Form(""), business_unit: str = Form(""),
        criticality: str = Form("Medium"), environment: str = Form("Production"),
        lifecycle_status: str = Form("Active"), tech_stack: str = Form(""),
        hosting: str = Form(""), frameworks: str = Form(""),
    ):
        from ecs_platform.governance import onboard_application

        res = onboard_application({
            "name": name, "description": description, "owner": owner, "owner_email": owner_email,
            "business_unit": business_unit, "criticality": criticality, "environment": environment,
            "lifecycle_status": lifecycle_status, "tech_stack": tech_stack, "hosting": hosting,
            "frameworks": frameworks,
        }, actor=user, role=role)
        notice = (f"Onboarded application '{name}' ({res['slug']})." if res.get("ok")
                  else f"Onboarding failed: {res.get('error')}")
        return _redirect("/mvp/platform/inventory", role, user, notice)

    @app.get("/mvp/platform/inventory", response_class=HTMLResponse)
    def gov_inventory(request: Request, role: str = "owner", user: str = "AppOwner", notice: str = ""):
        from ecs_platform.governance import list_applications

        inv = list_applications()
        ctx = _ctx(request, role, user, "gov_inventory", notice, inv=inv)
        return templates.TemplateResponse(request=request, name="gov_app_inventory.html", context=ctx)

    @app.get("/mvp/platform/application/{slug}", response_class=HTMLResponse)
    def gov_application_detail(request: Request, slug: str, role: str = "owner",
                              user: str = "AppOwner", notice: str = ""):
        from ecs_platform.governance import application_detail

        detail = application_detail(slug)
        ctx = _ctx(request, role, user, "gov_inventory", notice, detail=detail, slug=slug)
        return templates.TemplateResponse(request=request, name="gov_app_detail.html", context=ctx)

    # ---------------------------------------------------------------- 3. Evidence reuse
    @app.get("/mvp/platform/evidence-reuse", response_class=HTMLResponse)
    def gov_reuse(request: Request, role: str = "compliance_head", user: str = "Compliance", notice: str = ""):
        from ecs_platform.governance import crosswalk_matrix, evidence_reuse, reuse_demonstrations

        data = evidence_reuse()
        matrix = crosswalk_matrix()
        demos = reuse_demonstrations()
        ctx = _ctx(request, role, user, "gov_reuse", notice, data=data, matrix=matrix, demos=demos)
        return templates.TemplateResponse(request=request, name="gov_evidence_reuse.html", context=ctx)

    # ---------------------------------------------------------------- Phase 2: role scorecard
    @app.get("/mvp/platform/scorecard", response_class=HTMLResponse)
    def gov_scorecard(request: Request, role: str = "cio", user: str = "CIO", notice: str = ""):
        from ecs_platform.governance import governance_scorecard

        data = governance_scorecard(role)
        ctx = _ctx(request, role, user, "gov_scorecard", notice, data=data)
        return templates.TemplateResponse(request=request, name="gov_scorecard.html", context=ctx)

    # ---------------------------------------------------------------- 4. Control coverage
    @app.get("/mvp/platform/control-coverage", response_class=HTMLResponse)
    def gov_control_coverage(request: Request, role: str = "compliance_head", user: str = "Compliance", notice: str = ""):
        from ecs_platform.governance import control_coverage

        data = control_coverage()
        ctx = _ctx(request, role, user, "gov_control_coverage", notice, data=data)
        return templates.TemplateResponse(request=request, name="gov_control_coverage.html", context=ctx)

    # ---------------------------------------------------------------- 5. Framework coverage
    @app.get("/mvp/platform/framework-coverage", response_class=HTMLResponse)
    def gov_framework_coverage(request: Request, role: str = "compliance_head", user: str = "Compliance", notice: str = ""):
        from ecs_platform.governance import framework_coverage

        data = framework_coverage()
        ctx = _ctx(request, role, user, "gov_framework_coverage", notice, data=data)
        return templates.TemplateResponse(request=request, name="gov_framework_coverage.html", context=ctx)

    # ---------------------------------------------------------------- 6. Scheduler
    @app.get("/mvp/platform/scheduler", response_class=HTMLResponse)
    def gov_scheduler(request: Request, role: str = "compliance_head", user: str = "Compliance", notice: str = ""):
        from ecs_platform.governance import list_schedules

        data = list_schedules()
        ctx = _ctx(request, role, user, "gov_scheduler", notice, data=data,
                   connectors=["gitea", "sonarqube", "jenkins", "github", "jira", "confluence", "figma"])
        return templates.TemplateResponse(request=request, name="gov_scheduler.html", context=ctx)

    @app.post("/mvp/platform/scheduler")
    def gov_scheduler_create(role: str = Form("compliance_head"), user: str = Form("Compliance"),
                            name: str = Form(...), connector: str = Form(""), app_slug: str = Form(""),
                            frequency: str = Form("Daily"), owner: str = Form("")):
        from ecs_platform.governance import upsert_schedule

        res = upsert_schedule(name, connector=connector, app_slug=app_slug, frequency=frequency,
                              owner=owner or user, actor=user)
        notice = f"Schedule '{name}' created." if res.get("ok") else f"Failed: {res.get('error')}"
        return _redirect("/mvp/platform/scheduler", role, user, notice)

    # ---------------------------------------------------------------- 7. Evidence lifecycle
    @app.get("/mvp/platform/evidence-lifecycle", response_class=HTMLResponse)
    def gov_lifecycle(request: Request, role: str = "auditor", user: str = "Auditor",
                      status: str = "", notice: str = ""):
        from ecs_platform.governance import evidence_lifecycle

        data = evidence_lifecycle(status=status)
        ctx = _ctx(request, role, user, "gov_lifecycle", notice, data=data, status=status)
        return templates.TemplateResponse(request=request, name="gov_evidence_lifecycle.html", context=ctx)

    @app.post("/mvp/platform/evidence-lifecycle/review")
    def gov_lifecycle_review(role: str = Form("auditor"), user: str = Form("Auditor"),
                            evidence_uid: str = Form(...), status: str = Form(...),
                            note: str = Form(""), valid_days: int = Form(0)):
        from ecs_platform.governance import set_review_status

        res = set_review_status(evidence_uid, status, reviewer=user, note=note,
                                valid_days=valid_days, actor=user)
        notice = (f"{evidence_uid[:12]}… → {status}" if res.get("ok") else f"Failed: {res.get('error')}")
        return _redirect("/mvp/platform/evidence-lifecycle", role, user, notice)

    # ---------------------------------------------------------------- 8. Audit readiness
    @app.get("/mvp/platform/audit-readiness", response_class=HTMLResponse)
    def gov_audit_readiness(request: Request, role: str = "auditor", user: str = "Auditor", notice: str = ""):
        from ecs_platform.governance import audit_readiness

        data = audit_readiness()
        ctx = _ctx(request, role, user, "gov_audit_readiness", notice, data=data)
        return templates.TemplateResponse(request=request, name="gov_audit_readiness.html", context=ctx)

    # ---------------------------------------------------------------- 9. Executive summary
    @app.get("/mvp/platform/executive-summary", response_class=HTMLResponse)
    def gov_executive_summary(request: Request, role: str = "cio", user: str = "CIO", notice: str = ""):
        from ecs_platform.governance import executive_summary

        data = executive_summary()
        ctx = _ctx(request, role, user, "gov_exec_summary", notice, data=data)
        return templates.TemplateResponse(request=request, name="gov_executive_summary.html", context=ctx)

    # ---------------------------------------------------------------- 10. Assistant (LLM-RAG)
    @app.get("/mvp/platform/assistant", response_class=HTMLResponse)
    def gov_assistant(request: Request, role: str = "cio", user: str = "CIO",
                      q: str = "", notice: str = ""):
        from ecs_platform.governance import governance_qa
        from ecs_platform.rag import EXAMPLE_QUERIES, answer as rag_answer, rag_status

        status = rag_status()
        answer = None
        if q:
            res = rag_answer(q, role=role, user=user)
            # Fall back to the deterministic keyword assistant for the prose answer
            # when no LLM key is configured, but keep RAG citations/diagnostics.
            if res.get("mode") in ("fallback", "error") or not res.get("grounded"):
                kw = governance_qa(q)
                res["answer"] = kw.get("answer", res.get("answer", ""))
                res.setdefault("fallback_used", True)
            answer = res
        ctx = _ctx(request, role, user, "gov_assistant", notice, q=q, answer=answer,
                   status=status, examples=EXAMPLE_QUERIES)
        return templates.TemplateResponse(request=request, name="gov_assistant.html", context=ctx)

    @app.post("/mvp/platform/assistant/reindex")
    def gov_assistant_reindex(role: str = Form("cio"), user: str = Form("CIO")):
        from ecs_platform.rag import reindex_evidence

        res = reindex_evidence()
        notice = (f"Indexed {res.get('chunks_indexed', 0)} chunks from {res.get('evidence', 0)} evidence "
                  f"records + {res.get('governance_docs', 0)} governance docs."
                  if res.get("ok") else f"Re-index failed: {res.get('error')}")
        return _redirect("/mvp/ai-assistant", role, user, notice)

    # ---------------------------------------------------------------- AI Assistant (dedicated page)
    def _filter_options():
        """Application + framework filter dropdown options from the live repository."""
        apps: list[str] = []
        fws: list[str] = []
        try:
            from ecs_platform.governance import REUSE_FRAMEWORKS

            fws = list(REUSE_FRAMEWORKS)
        except Exception:  # noqa: BLE001
            pass
        try:
            from ecs_platform.repository import EvidenceRepository

            with EvidenceRepository() as repo:
                apps = repo.distinct_values().get("applications", [])
        except Exception:  # noqa: BLE001
            pass
        return apps, fws

    @app.get("/mvp/ai-assistant", response_class=HTMLResponse)
    def ai_assistant(request: Request, role: str = "cio", user: str = "CIO", q: str = "",
                     application: str = "", framework: str = "", notice: str = ""):
        from ecs_platform.governance import governance_qa
        from ecs_platform.rag import EXAMPLE_QUERIES, answer as rag_answer, rag_status

        status = rag_status()
        apps, fws = _filter_options()
        answer = None
        if q:
            res = rag_answer(q, role=role, user=user, application=application, framework=framework)
            if res.get("mode") in ("fallback", "error") or not res.get("grounded"):
                res["answer"] = governance_qa(q).get("answer", res.get("answer", ""))
                res.setdefault("fallback_used", True)
            answer = res
        ctx = _ctx(request, role, user, "ai_assistant", notice, q=q, answer=answer, status=status,
                   examples=EXAMPLE_QUERIES, apps=apps, fw_options=fws,
                   selected={"application": application, "framework": framework})
        return templates.TemplateResponse(request=request, name="ai_assistant.html", context=ctx)

    @app.post("/mvp/ai-assistant/reindex")
    def ai_assistant_reindex(role: str = Form("cio"), user: str = Form("CIO")):
        from ecs_platform.rag import reindex_evidence

        res = reindex_evidence()
        notice = (f"Indexed {res.get('chunks_indexed', 0)} chunks from {res.get('evidence', 0)} evidence "
                  f"records + {res.get('governance_docs', 0)} governance docs."
                  if res.get("ok") else f"Re-index failed: {res.get('error')}")
        return _redirect("/mvp/ai-assistant", role, user, notice)

    # ---------------------------------------------------------------- JSON APIs
    @app.get("/api/platform/inventory")
    def api_inventory():
        from ecs_platform.governance import list_applications
        return JSONResponse(list_applications())

    @app.get("/api/platform/evidence-reuse")
    def api_reuse():
        from ecs_platform.governance import evidence_reuse
        return JSONResponse(evidence_reuse())

    @app.get("/api/platform/reuse-demonstrations")
    def api_reuse_demos():
        from ecs_platform.governance import reuse_demonstrations
        return JSONResponse(reuse_demonstrations())

    @app.get("/api/platform/crosswalk")
    def api_crosswalk():
        from ecs_platform.governance import crosswalk_matrix
        return JSONResponse(crosswalk_matrix())

    @app.get("/api/platform/scorecard")
    def api_scorecard(role: str = "cio"):
        from ecs_platform.governance import governance_scorecard
        return JSONResponse(governance_scorecard(role))

    @app.get("/api/platform/control-coverage")
    def api_control_coverage():
        from ecs_platform.governance import control_coverage
        return JSONResponse(control_coverage())

    @app.get("/api/platform/framework-coverage")
    def api_framework_coverage():
        from ecs_platform.governance import framework_coverage
        return JSONResponse(framework_coverage())

    @app.get("/api/platform/audit-readiness")
    def api_audit_readiness():
        from ecs_platform.governance import audit_readiness
        return JSONResponse(audit_readiness())

    @app.get("/api/platform/executive-summary")
    def api_executive_summary():
        from ecs_platform.governance import executive_summary
        return JSONResponse(executive_summary())

    @app.get("/api/platform/assistant")
    def api_assistant(q: str = "", role: str = "cio", user: str = "User",
                      application: str = "", framework: str = ""):
        from ecs_platform.governance import governance_qa
        from ecs_platform.rag import answer as rag_answer

        if not q:
            return JSONResponse({"ok": False, "error": "q is required"}, status_code=400)
        res = rag_answer(q, role=role, user=user, application=application, framework=framework)
        if res.get("mode") in ("fallback", "error") or not res.get("grounded"):
            res["keyword_answer"] = governance_qa(q).get("answer", "")
        return JSONResponse(res)

    @app.get("/api/platform/rag/status")
    def api_rag_status():
        from ecs_platform.rag import rag_status
        return JSONResponse(rag_status())

    @app.get("/api/platform/rag/gemini")
    def api_rag_gemini():
        from ecs_platform.rag import gemini_connectivity
        return JSONResponse(gemini_connectivity())

    @app.post("/api/platform/rag/reindex")
    def api_rag_reindex():
        from ecs_platform.rag import reindex_evidence
        return JSONResponse(reindex_evidence())
