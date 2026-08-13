"""UI pages for the ECS Audit Intelligence layer (Milestone 5 + 6).

Reuses the existing ECS page shell (``partials/mvp_styles.html`` +
``partials/mvp_sidebar.html`` + Bootstrap / ``ecs-*`` classes) and the
``enterprise_widgets_context`` nav highlighting. Each page renders read-only views
built from the M1-M3 service facades; no new styling framework is introduced.

Pages: Executive Readiness (dashboard), Asset Inventory, Technology Inventory,
Technology Mapping, Evidence Runs, Evidence Repository, Observations, Evidence
Packs, Validation Results.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from modules.audit_intelligence.services import asset_service, mapping_service
from modules.audit_intelligence.services import audit_repository_service as repo_svc
from modules.audit_intelligence.services import evidence_service
from modules.audit_intelligence.services import dashboard_service


def _base_ctx(role: str, user: str, nav_module: str) -> dict[str, Any]:
    ctx: dict[str, Any] = {"role": role, "user": user, "nav_module": nav_module}
    try:
        from modules.shared.services.enterprise_context import enterprise_widgets_context

        ctx.update(enterprise_widgets_context(role, page_module=nav_module, user=user))
    except Exception:  # noqa: BLE001 - context helper must never break a page
        pass
    try:
        from app.auth.demo import demo_mode

        ctx["demo_mode"] = demo_mode()
    except Exception:  # noqa: BLE001
        ctx["demo_mode"] = False
    return ctx


def register_audit_ui_routes(app, templates) -> None:
    def render(request: Request, template: str, ctx: dict[str, Any]):
        return templates.TemplateResponse(request, template, ctx)

    # ------------------------------------------------------ Executive Readiness (M6)
    @app.get("/mvp/audit/executive-readiness", response_class=HTMLResponse)
    def ui_exec_readiness(request: Request, role: str = "owner", user: str = "User"):
        ctx = _base_ctx(role, user, "audit_readiness_exec")
        ctx["dash"] = dashboard_service.executive_readiness()
        return render(request, "audit/executive_readiness.html", ctx)

    # ------------------------------------------------------------- Asset Inventory
    @app.get("/mvp/audit/assets", response_class=HTMLResponse)
    def ui_assets(request: Request, role: str = "owner", user: str = "User"):
        assets = asset_service.discover_assets(include_docker_compose=True, include_enterprise_grc=True)
        ctx = _base_ctx(role, user, "audit_assets")
        ctx["inventory"] = asset_service.inventory(assets)
        ctx["coverage"] = asset_service.coverage_summary(assets)
        return render(request, "audit/asset_inventory.html", ctx)

    # -------------------------------------------------------- Technology Inventory
    @app.get("/mvp/audit/technology-inventory", response_class=HTMLResponse)
    def ui_tech_inventory(request: Request, role: str = "owner", user: str = "User"):
        assets = asset_service.discover_assets(include_docker_compose=True, include_enterprise_grc=True)
        ctx = _base_ctx(role, user, "audit_technology")
        ctx["technology_inventory"] = asset_service.technology_inventory(assets)
        ctx["fingerprints"] = asset_service.fingerprint_report(assets)
        return render(request, "audit/technology_inventory.html", ctx)

    # --------------------------------------------------------- Technology Mapping
    @app.get("/mvp/audit/mapping", response_class=HTMLResponse)
    def ui_mapping(request: Request, role: str = "owner", user: str = "User",
                   technology: str = "", framework: str = ""):
        ctx = _base_ctx(role, user, "audit_mapping")
        ctx["stats"] = mapping_service.stats()
        ctx["technologies"] = mapping_service.technologies()
        ctx["frameworks"] = mapping_service.frameworks()
        ctx["rows"] = mapping_service.search(technology=technology, framework=framework)
        ctx["sel_technology"] = technology
        ctx["sel_framework"] = framework
        ctx["filter_options"] = mapping_service.filter_options()
        return render(request, "audit/technology_mapping.html", ctx)

    # ---------------------------------------------------------------- Evidence Runs
    @app.get("/mvp/audit/runs", response_class=HTMLResponse)
    def ui_runs(request: Request, role: str = "owner", user: str = "User", run_id: str = ""):
        ctx = _base_ctx(role, user, "audit_runs")
        ctx["runs"] = evidence_service.list_runs()
        # validate_run() must run first: it mutates the live run's records in place
        # (evidence_service.py) to fold in each control's verdict. get_run() only
        # returns a snapshot, so calling it first would capture records before the
        # verdict is written and every VERDICT cell would render empty.
        ctx["selected_validation"] = evidence_service.validate_run(run_id) if run_id else None
        ctx["selected_run"] = evidence_service.get_run(run_id) if run_id else None
        ctx["scope_frameworks"] = mapping_service.frameworks()
        ctx["scope_technologies"] = mapping_service.technologies()
        ctx["scope_controls"] = mapping_service.controls()
        return render(request, "audit/evidence_runs.html", ctx)

    @app.post("/mvp/audit/runs")
    def ui_start_run(
        role: str = Form("owner"),
        user: str = Form("User"),
        scope_kind: str = Form(...),
        scope_value: str = Form(""),
        return_to: str = Form("audit_runs"),
    ):
        """Start a run from the Evidence Runs panel, then POST-redirect-GET.

        Mirrors the ``/mvp/scheduler/pause|resume`` pattern: plain form fields in,
        303 back to the page so a refresh cannot re-submit the run. The JSON API
        (``POST /api/audit/runs``) stays the machine-facing path.

        ``return_to`` is a fixed key, not a URL, so the caller can never steer the
        redirect off-site; unknown values fall back to the Evidence Runs page.
        """
        evidence_service.start_run(
            scope_kind=scope_kind,
            scope_value=scope_value,
            requested_by=user or "ui",
        )
        targets = {
            "audit_runs": "/mvp/audit/runs",
            "evidence_dashboard": "/mvp/evidence-dashboard",
        }
        base = targets.get(return_to, targets["audit_runs"])
        url = f"{base}?role={quote(role)}&user={quote(user)}"
        if return_to == "evidence_dashboard":
            url += "&tab=collection"
        return RedirectResponse(url=url, status_code=303)

    # ---------------------------------------------------------- Evidence Repository
    @app.get("/mvp/audit/repository", response_class=HTMLResponse)
    def ui_repository(request: Request, role: str = "owner", user: str = "User",
                      technology: str = "", framework: str = "", query: str = ""):
        ctx = _base_ctx(role, user, "audit_repository")
        ctx["evidence"] = repo_svc.repository_search(
            technology=technology, framework=framework, query=query, latest_only=True
        )
        ctx["stats"] = repo_svc.repository_stats()
        ctx["timeline"] = repo_svc.evidence_timeline()[-25:]
        ctx["sel"] = {"technology": technology, "framework": framework, "query": query}
        return render(request, "audit/evidence_repository.html", ctx)

    # --------------------------------------------------------------- Observations
    @app.get("/mvp/audit/observations", response_class=HTMLResponse)
    def ui_observations(request: Request, role: str = "owner", user: str = "User",
                        status: str = "", severity: str = ""):
        ctx = _base_ctx(role, user, "audit_observations")
        filters = {k: v for k, v in dict(status=status, severity=severity).items() if v}
        ctx["observations"] = repo_svc.list_observations(**filters)
        ctx["summary"] = repo_svc.observation_summary()
        ctx["sel"] = {"status": status, "severity": severity}
        return render(request, "audit/observations.html", ctx)

    # -------------------------------------------------------------- Evidence Packs
    @app.get("/mvp/audit/packs", response_class=HTMLResponse)
    def ui_packs(request: Request, role: str = "owner", user: str = "User",
                 pack_type: str = "", scope: str = ""):
        ctx = _base_ctx(role, user, "audit_packs")
        ctx["stats"] = repo_svc.repository_stats()
        ctx["pack"] = repo_svc.build_pack(pack_type, scope) if pack_type and scope else None
        ctx["frameworks"] = mapping_service.frameworks()
        ctx["sel"] = {"pack_type": pack_type, "scope": scope}
        return render(request, "audit/evidence_packs.html", ctx)

    # ------------------------------------------------------------ Validation view
    @app.get("/mvp/audit/validation", response_class=HTMLResponse)
    def ui_validation(request: Request, role: str = "owner", user: str = "User", run_id: str = ""):
        ctx = _base_ctx(role, user, "audit_runs")
        ctx["runs"] = evidence_service.list_runs()
        ctx["validation"] = evidence_service.validate_run(run_id) if run_id else None
        ctx["run_id"] = run_id
        return render(request, "audit/validation_results.html", ctx)

    # ------------------------------------------------------------------ aliases
    # Compatibility aliases: additive canonical paths that delegate to the
    # handlers above. Existing routes are kept unchanged so older links/bookmarks
    # keep working. (See docs/production/PRODUCTION_READINESS_GAP_REGISTER.md.)
    @app.get("/mvp/audit/dashboard", response_class=HTMLResponse)
    def ui_dashboard_alias(request: Request, role: str = "owner", user: str = "User"):
        return ui_exec_readiness(request, role=role, user=user)

    @app.get("/mvp/audit/technology-mapping", response_class=HTMLResponse)
    def ui_technology_mapping_alias(request: Request, role: str = "owner", user: str = "User",
                                    technology: str = "", framework: str = ""):
        return ui_mapping(request, role=role, user=user,
                          technology=technology, framework=framework)

    @app.get("/mvp/audit/evidence-runs", response_class=HTMLResponse)
    def ui_evidence_runs_alias(request: Request, role: str = "owner", user: str = "User",
                               run_id: str = ""):
        return ui_runs(request, role=role, user=user, run_id=run_id)

    @app.get("/mvp/audit/validation-results", response_class=HTMLResponse)
    def ui_validation_results_alias(request: Request, role: str = "owner", user: str = "User",
                                    run_id: str = ""):
        return ui_validation(request, role=role, user=user, run_id=run_id)

    @app.get("/mvp/audit/evidence-packs", response_class=HTMLResponse)
    def ui_evidence_packs_alias(request: Request, role: str = "owner", user: str = "User",
                                pack_type: str = "", scope: str = ""):
        return ui_packs(request, role=role, user=user, pack_type=pack_type, scope=scope)

    # ------------------------------------------------ Audit LLM Prompt Workbench
    @app.get("/mvp/audit/llm-workbench", response_class=HTMLResponse)
    def ui_llm_workbench(request: Request, role: str = "owner", user: str = "User"):
        ctx = _base_ctx(role, user, "audit_llm_workbench")
        try:
            from modules.audit_intelligence.llm import prompt_library as pl

            ctx["prompt_count"] = pl.load_prompt_library().get("count", 0)
            ctx["categories"] = pl.categories()
        except Exception:  # noqa: BLE001 - page must render even if library errors
            ctx["prompt_count"] = 0
            ctx["categories"] = []
        return render(request, "audit/llm_workbench.html", ctx)
