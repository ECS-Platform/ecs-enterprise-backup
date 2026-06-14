"""ECS Platform routes: evidence ingestion UI, integration health, evidence explorer.

Wires the ecs_platform package (connectors + repository + relationships + audit)
into the running FastAPI app. All heavy imports are lazy so the rest of the app
is unaffected if platform dependencies (psycopg2/DB) are unavailable.
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app import ecs_state


def register_platform_routes(app, templates):
    def _valid_connectors() -> list[str]:
        """All configured connectors (gitea, jira, github, figma, ...)."""
        try:
            from ecs_platform.ingestion import available_connectors

            return available_connectors()
        except Exception:  # noqa: BLE001
            return ["gitea", "sonarqube", "jenkins"]

    def _frameworks():
        try:
            return list(ecs_state.frameworks.keys())
        except Exception:  # noqa: BLE001
            return []

    @app.get("/mvp/integration-health", response_class=HTMLResponse)
    def integration_health(request: Request, role: str = "admin", user: str = "Admin", notice: str = ""):
        from ecs_platform.ingestion import health_overview

        overview = health_overview()
        ctx = {
            "request": request, "role": role, "user": user, "notice": notice,
            "frameworks": _frameworks(), "nav_module": "integration_health",
            "overview": overview, "connectors": _valid_connectors(),
        }
        return templates.TemplateResponse(request=request, name="platform_integration_health.html", context=ctx)

    @app.get("/mvp/evidence-explorer", response_class=HTMLResponse)
    def evidence_explorer(request: Request, role: str = "admin", user: str = "Admin",
                          application: str = "", source_system: str = "", object_type: str = "",
                          notice: str = ""):
        from ecs_platform.ingestion import list_evidence

        data = list_evidence(application=application, source_system=source_system, object_type=object_type)
        ctx = {
            "request": request, "role": role, "user": user, "notice": notice,
            "frameworks": _frameworks(), "nav_module": "evidence_explorer",
            "data": data,
            "selected": {"application": application, "source_system": source_system, "object_type": object_type},
        }
        return templates.TemplateResponse(request=request, name="platform_evidence_explorer.html", context=ctx)

    @app.post("/mvp/platform/sync/{connector}")
    def platform_sync(connector: str, request: Request, role: str = Form("admin"), user: str = Form("Admin"),
                      redirect: str = Form("/mvp/integration-health")):
        from app.auth.mutation_guard import guard_mutation
        from ecs_platform.ingestion import sync_connector

        deny = guard_mutation(request, "can_admin_platform", fallback_role=role,
                              deny_redirect_to=redirect, role=role, user=user)
        if deny:
            return deny
        if connector not in _valid_connectors():
            notice = f"Unknown connector: {connector}"
        else:
            res = sync_connector(connector, actor=user, role=role)
            if res.get("ok"):
                notice = (f"{connector}: collected {res['collected']}, persisted {res['persisted']}, "
                          f"relationships {res['relationships']}, indexed {res['indexed']}")
                if res.get("warnings"):
                    notice += f" ({'; '.join(res['warnings'])})"
            else:
                notice = f"{connector} sync failed: {res.get('error', 'unknown error')}"
        sep = "&" if "?" in redirect else "?"
        return RedirectResponse(url=f"{redirect}{sep}role={role}&user={quote(user)}&notice={quote(notice)}",
                                status_code=303)

    @app.post("/mvp/platform/sync-all")
    def platform_sync_all(request: Request, role: str = Form("admin"), user: str = Form("Admin")):
        from app.auth.mutation_guard import guard_mutation
        from ecs_platform.ingestion import sync_all

        deny = guard_mutation(request, "can_admin_platform", fallback_role=role,
                              deny_redirect_to="/mvp/integration-health", role=role, user=user)
        if deny:
            return deny
        results = sync_all(actor=user, role=role)
        ok = sum(1 for r in results if r.get("ok"))
        total = sum(r.get("persisted", 0) for r in results)
        notice = f"Synced {ok}/{len(results)} connectors; {total} evidence items persisted."
        return RedirectResponse(url=f"/mvp/integration-health?role={role}&user={quote(user)}&notice={quote(notice)}",
                                status_code=303)

    # ---- Orchestration probes (Kubernetes / Docker / load-balancer) ----
    @app.get("/healthz")
    def healthz():
        """Liveness probe: process is up and serving. Intentionally does no I/O
        so a slow/unreachable dependency never restarts a healthy container."""
        return JSONResponse({"status": "ok"})

    @app.get("/readyz")
    def readyz():
        """Readiness probe: app can serve traffic that needs the evidence repo.
        Returns 200 when the PostgreSQL repository is reachable, else 503. Kept
        lightweight (single connectivity check, no heavy queries or LLM calls)."""
        repo_ok = False
        detail = ""
        try:
            from ecs_platform.repository import EvidenceRepository

            with EvidenceRepository() as repo:
                with repo.connect().cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            repo_ok = True
        except Exception as exc:  # noqa: BLE001 - readiness must never raise
            detail = str(exc)[:200]
        status = 200 if repo_ok else 503
        return JSONResponse(
            {"status": "ready" if repo_ok else "not-ready", "repository_ok": repo_ok, "detail": detail},
            status_code=status,
        )

    # ---- JSON APIs ----
    @app.get("/api/platform/health")
    def api_platform_health():
        from ecs_platform.ingestion import health_overview

        return JSONResponse(health_overview())

    @app.post("/api/platform/sync/{connector}")
    def api_platform_sync(connector: str, request: Request, user: str = "system", role: str = "admin"):
        from app.auth.mutation_guard import guard_mutation
        from ecs_platform.ingestion import sync_connector

        deny = guard_mutation(request, "can_admin_platform", fallback_role=role, response="json")
        if deny:
            return deny
        if connector not in _valid_connectors():
            return JSONResponse({"ok": False, "error": f"unknown connector: {connector}"}, status_code=400)
        return JSONResponse(sync_connector(connector, actor=user, role=role))

    @app.get("/api/platform/evidence")
    def api_platform_evidence(request: Request, application: str = "", source_system: str = "",
                              object_type: str = ""):
        from app.auth.scope import apply_scope
        from ecs_platform.ingestion import list_evidence

        rows = list_evidence(application=application, source_system=source_system,
                             object_type=object_type)
        # Phase 2 Step 3: scope-filter result rows to the principal's assignments
        # (flag-gated; pass-through when off / enterprise). Response schema unchanged.
        if isinstance(rows, list):
            rows = apply_scope(request, rows)
        return JSONResponse(rows)
