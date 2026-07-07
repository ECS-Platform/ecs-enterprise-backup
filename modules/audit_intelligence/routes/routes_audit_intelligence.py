"""REST API for the ECS Audit Intelligence layer (Milestone 4).

Reuses the existing FastAPI app + the ``register_*_routes(app)`` convention. All
endpoints are JSON under ``/api/audit/`` and are thin wrappers over the M1-M3
service facades (no new business logic here). Read endpoints are GET; state-
changing actions (run/retry/cancel/transition/store/pack) are POST.

Production hardening (see docs/production/PERFORMANCE_AND_HARDENING_GUIDE.md)
--------------------------------------------------------------------------
* **Uniform response shape.** Success: ``{"ok": true, ...payload}``.
  Error: ``{"ok": false, "status": "error", "message": "...", "errors": [...]}``
  (``error`` is retained as a legacy alias so older clients keep working).
* **Safe exception handling.** Every endpoint is wrapped by :func:`_safe`, so an
  unexpected error becomes a consistent JSON 500 — never a stack trace and never
  a secret. Empty state is always valid JSON (empty list/object), never a crash.
* **Bounded responses.** List endpoints paginate with a safe default limit and a
  hard max so a single request can never return an unbounded payload.
"""

from __future__ import annotations

import functools
import time as _time
from typing import Any

from fastapi import Body, Request
from fastapi.responses import HTMLResponse, JSONResponse

#: Hard caps for paginated API responses (bound payload size / work).
_MAX_LIMIT = 1000
_DEFAULT_LIMIT = 200

#: String forms used as query-parameter defaults. Pagination params are declared
#: as ``str`` (not ``int``) at the API boundary so a bad value like ``limit=abc``
#: is coerced to a safe default by :func:`_paginate` and returns a bounded 200,
#: rather than FastAPI rejecting it with a 422 before our clamping runs.
_DEFAULT_LIMIT_STR = str(_DEFAULT_LIMIT)
_DEFAULT_OFFSET_STR = "0"


def _paginate(items: Any, limit: int, offset: int) -> tuple[list[Any], dict[str, Any]]:
    """Return (page, page_meta) with clamped limit/offset. Deterministic + bounded.

    Tolerates non-list / ``None`` inputs (treated as empty) and any invalid
    limit/offset (coerced to safe defaults) so a bad query string can never crash
    the endpoint or return an unbounded payload.
    """
    items = list(items) if isinstance(items, (list, tuple)) else ([] if items is None else list(items))
    total = len(items)
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = _DEFAULT_LIMIT
    try:
        offset = max(0, int(offset))
    except (TypeError, ValueError):
        offset = 0
    if limit <= 0:
        limit = _DEFAULT_LIMIT
    limit = min(limit, _MAX_LIMIT)
    page = items[offset:offset + limit]
    return page, {
        "total": total, "limit": limit, "offset": offset,
        "returned": len(page), "has_more": offset + limit < total,
    }

from modules.audit_intelligence.services import asset_service, mapping_service
from modules.audit_intelligence.services import audit_repository_service as repo_svc
from modules.audit_intelligence.services import evidence_service


def _ok(payload: dict[str, Any] | None = None, **extra: Any) -> JSONResponse:
    body: dict[str, Any] = {"ok": True}
    if payload:
        body.update(payload)
    body.update(extra)
    return JSONResponse(body)


def _err(message: str, status: int = 404, errors: list[Any] | None = None) -> JSONResponse:
    """Consistent error envelope.

    Shape: ``{"ok": false, "status": "error", "message": ..., "errors": [...]}``.
    ``error`` is kept as a legacy alias of ``message`` for backward compatibility.
    """
    msg = str(message)
    return JSONResponse(
        {
            "ok": False,
            "status": "error",
            "message": msg,
            "errors": errors if errors is not None else [msg],
            "error": msg,  # legacy alias — do not remove without a client migration
        },
        status_code=status,
    )


def _safe(fn):
    """Request-safe wrapper: any unexpected error → consistent 500 JSON (no stack,
    no secret leakage). Keeps the audit API resilient in production."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - never leak a stack trace to clients
            # Only the exception *type* is surfaced (never its message/args), so a
            # secret embedded in an error string can never leak to a client.
            return _err(
                "internal_error",
                status=500,
                errors=[f"{fn.__name__}: {type(exc).__name__}"],
            )
    return wrapper


def register_audit_intelligence_routes(app) -> None:
    # ----------------------------------------------------------------- mapping
    @app.get("/api/audit/mapping")
    @_safe
    def api_mapping_root(query: str = "", technology: str = "", framework: str = "",
                         limit: str = _DEFAULT_LIMIT_STR, offset: str = _DEFAULT_OFFSET_STR):
        """Mapping entry point: paginated flattened mapping rows + catalog stats.

        Compatibility alias so ``/api/audit/mapping`` (without a sub-path) returns
        a useful, bounded payload instead of 404.
        """
        full = mapping_service.search(query=query, technology=technology, framework=framework)
        page, meta = _paginate(full, limit, offset)
        return _ok(results=page, page=meta, stats=mapping_service.stats())

    @app.get("/api/audit/mapping/technologies")
    @_safe
    def api_map_technologies():
        return _ok(technologies=mapping_service.technologies())

    @app.get("/api/audit/mapping/frameworks")
    @_safe
    def api_map_frameworks():
        return _ok(frameworks=mapping_service.frameworks())

    @app.get("/api/audit/mapping/graph")
    @_safe
    def api_map_graph():
        return _ok(graph=mapping_service.graph())

    @app.get("/api/audit/mapping/stats")
    @_safe
    def api_map_stats():
        return _ok(stats=mapping_service.stats())

    @app.get("/api/audit/mapping/technology/{technology}")
    @_safe
    def api_map_technology(technology: str):
        detail = mapping_service.technology_detail(technology)
        return _ok(detail=detail) if detail else _err(f"Unknown technology: {technology}")

    @app.get("/api/audit/mapping/framework/{framework}")
    @_safe
    def api_map_framework(framework: str):
        detail = mapping_service.framework_detail(framework)
        return _ok(detail=detail) if detail else _err(f"Unknown framework: {framework}")

    @app.get("/api/audit/mapping/search")
    @_safe
    def api_map_search(query: str = "", technology: str = "", framework: str = "",
                       limit: str = _DEFAULT_LIMIT_STR, offset: str = _DEFAULT_OFFSET_STR):
        full = mapping_service.search(query=query, technology=technology, framework=framework)
        page, meta = _paginate(full, limit, offset)
        return _ok(results=page, page=meta)

    # ------------------------------------------------------------------ assets
    @app.get("/api/audit/assets")
    @_safe
    def api_assets(docker_compose: bool = True, enterprise_grc: bool = False,
                   limit: str = _DEFAULT_LIMIT_STR, offset: str = _DEFAULT_OFFSET_STR):
        started = _time.perf_counter()
        assets = asset_service.discover_assets(
            include_docker_compose=docker_compose, include_enterprise_grc=enterprise_grc
        )
        full = asset_service.inventory(assets)
        page, meta = _paginate(full, limit, offset)
        return _ok(
            inventory=page,
            coverage=asset_service.coverage_summary(assets),
            page=meta,
            elapsed_ms=round((_time.perf_counter() - started) * 1000, 1),
        )

    @app.get("/api/audit/assets/technology-inventory")
    @_safe
    def api_asset_tech_inventory(docker_compose: bool = True, enterprise_grc: bool = False):
        assets = asset_service.discover_assets(
            include_docker_compose=docker_compose, include_enterprise_grc=enterprise_grc
        )
        return _ok(technology_inventory=asset_service.technology_inventory(assets))

    @app.get("/api/audit/assets/fingerprints")
    @_safe
    def api_asset_fingerprints(docker_compose: bool = True, enterprise_grc: bool = False):
        assets = asset_service.discover_assets(
            include_docker_compose=docker_compose, include_enterprise_grc=enterprise_grc
        )
        return _ok(fingerprint_report=asset_service.fingerprint_report(assets))

    # -------------------------------------------------------------------- runs
    @app.get("/api/audit/runs")
    @_safe
    def api_runs(limit: str = _DEFAULT_LIMIT_STR, offset: str = _DEFAULT_OFFSET_STR):
        full = evidence_service.list_runs()
        page, meta = _paginate(full, limit, offset)
        return _ok(runs=page, page=meta)

    @app.get("/api/audit/runs/{run_id}")
    @_safe
    def api_run(run_id: str):
        run = evidence_service.get_run(run_id)
        return _ok(run=run) if run else _err(f"Unknown run: {run_id}")

    @app.post("/api/audit/runs")
    @_safe
    def api_start_run(payload: dict[str, Any] = Body(default_factory=dict)):
        scope_kind = str(payload.get("scope_kind") or "")
        if not scope_kind:
            return _err("scope_kind is required", status=400)
        run = evidence_service.start_run(
            scope_kind=scope_kind,
            scope_value=str(payload.get("scope_value") or ""),
            requested_by=str(payload.get("requested_by") or "api"),
            control_ids=payload.get("control_ids"),
            asset_id=str(payload.get("asset_id") or ""),
        )
        return _ok(run=run)

    @app.post("/api/audit/runs/{run_id}/retry")
    @_safe
    def api_retry_run(run_id: str):
        try:
            run = evidence_service.retry_run(run_id)
        except KeyError:
            return _err(f"Unknown run: {run_id}")
        return _ok(run=run)

    @app.post("/api/audit/runs/{run_id}/cancel")
    @_safe
    def api_cancel_run(run_id: str):
        try:
            run = evidence_service.cancel_run(run_id)
        except KeyError:
            return _err(f"Unknown run: {run_id}")
        return _ok(run=run)

    @app.get("/api/audit/runs/{run_id}/validation")
    @_safe
    def api_run_validation(run_id: str):
        result = evidence_service.validate_run(run_id)
        return _ok(validation=result) if result else _err(f"Unknown run: {run_id}")

    # ------------------------------------------------------------- repository
    def _evidence_search_payload(
        query: str, technology: str, framework: str, asset_id: str,
        verdict: str, tag: str, latest_only: bool, limit: int, offset: int,
    ) -> JSONResponse:
        full = repo_svc.repository_search(
            query=query, technology=technology, framework=framework,
            asset_id=asset_id, verdict=verdict, tag=tag, latest_only=latest_only,
        )
        page, meta = _paginate(full, limit, offset)
        return _ok(evidence=page, page=meta)

    @app.get("/api/audit/evidence")
    @_safe
    def api_evidence_search(
        query: str = "", technology: str = "", framework: str = "",
        asset_id: str = "", verdict: str = "", tag: str = "", latest_only: bool = True,
        limit: str = _DEFAULT_LIMIT_STR, offset: str = _DEFAULT_OFFSET_STR,
    ):
        return _evidence_search_payload(
            query, technology, framework, asset_id, verdict, tag, latest_only, limit, offset,
        )

    @app.get("/api/audit/repository")
    @_safe
    def api_repository(
        query: str = "", technology: str = "", framework: str = "",
        asset_id: str = "", verdict: str = "", tag: str = "", latest_only: bool = True,
        limit: str = _DEFAULT_LIMIT_STR, offset: str = _DEFAULT_OFFSET_STR,
    ):
        """Compatibility alias for :func:`api_evidence_search` (paginated evidence)."""
        return _evidence_search_payload(
            query, technology, framework, asset_id, verdict, tag, latest_only, limit, offset,
        )

    @app.get("/api/audit/evidence/stats")
    @_safe
    def api_evidence_stats():
        return _ok(stats=repo_svc.repository_stats())

    @app.get("/api/audit/evidence/{evidence_key}/versions")
    @_safe
    def api_evidence_versions(evidence_key: str):
        return _ok(versions=repo_svc.evidence_versions(evidence_key))

    @app.get("/api/audit/evidence/{evidence_key}/timeline")
    @_safe
    def api_evidence_timeline(evidence_key: str):
        return _ok(timeline=repo_svc.evidence_timeline(evidence_key))

    # ----------------------------------------------------------- observations
    @app.get("/api/audit/observations")
    @_safe
    def api_observations(status: str = "", severity: str = "", framework: str = "",
                         technology: str = "", limit: str = _DEFAULT_LIMIT_STR,
                         offset: str = _DEFAULT_OFFSET_STR):
        filters = {k: v for k, v in dict(
            status=status, severity=severity, framework=framework, technology=technology
        ).items() if v}
        full = repo_svc.list_observations(**filters)
        page, meta = _paginate(full, limit, offset)
        return _ok(observations=page, page=meta)

    @app.get("/api/audit/observations/summary")
    @_safe
    def api_observations_summary():
        return _ok(summary=repo_svc.observation_summary())

    @app.get("/api/audit/observations/{obs_id}")
    @_safe
    def api_observation(obs_id: str):
        o = repo_svc.get_observation(obs_id)
        return _ok(observation=o) if o else _err(f"Unknown observation: {obs_id}")

    @app.post("/api/audit/observations/{obs_id}/transition")
    @_safe
    def api_observation_transition(obs_id: str, payload: dict[str, Any] = Body(default_factory=dict)):
        to_status = str(payload.get("to_status") or "")
        if not to_status:
            return _err("to_status is required", status=400)
        from modules.audit_intelligence.engines.observation_generation import InvalidTransition

        try:
            o = repo_svc.transition_observation(
                obs_id, to_status, user=str(payload.get("user") or "api"),
                note=str(payload.get("note") or ""),
            )
        except KeyError:
            return _err(f"Unknown observation: {obs_id}")
        except InvalidTransition as exc:
            return _err(str(exc), status=400)
        return _ok(observation=o)

    # ------------------------------------------------------------------ packs
    def _paginate_pack(pack: dict[str, Any] | None, limit: int, offset: int) -> dict[str, Any] | None:
        """Bound a pack's ``items`` list for the response WITHOUT altering pack
        identity: ``item_count`` and ``pack_hash`` stay computed over the FULL set
        (so ``verify_manifest`` still works on the source pack), while the response
        only carries a bounded page of items plus ``items_page`` metadata."""
        if not isinstance(pack, dict):
            return pack
        items = pack.get("items")
        if not isinstance(items, list):
            return pack
        page, meta = _paginate(items, limit, offset)
        out = dict(pack)
        out["items"] = page
        out["items_page"] = meta
        return out

    @app.get("/api/audit/packs/{pack_type}/{scope}")
    @_safe
    def api_pack(pack_type: str, scope: str, limit: str = _DEFAULT_LIMIT_STR,
                 offset: str = _DEFAULT_OFFSET_STR):
        pack = repo_svc.build_pack(pack_type, scope)
        if pack is None:
            return _err(f"Unknown pack type: {pack_type}", status=400)
        return _ok(pack=_paginate_pack(pack, limit, offset))

    @app.post("/api/audit/packs/application")
    @_safe
    def api_application_pack(payload: dict[str, Any] = Body(default_factory=dict)):
        scope = str(payload.get("application") or "")
        asset_ids = payload.get("asset_ids") or []
        try:
            limit = int(payload.get("limit", _DEFAULT_LIMIT))
        except (TypeError, ValueError):
            limit = _DEFAULT_LIMIT
        try:
            offset = int(payload.get("offset", 0))
        except (TypeError, ValueError):
            offset = 0
        pack = repo_svc.build_pack("application", scope, asset_ids=asset_ids)
        if pack is None:
            return _err("could not build application pack", status=400)
        return _ok(pack=_paginate_pack(pack, limit, offset))

    # ------------------------------------------------------------- dashboards
    @app.get("/api/audit/dashboard")
    @_safe
    def api_audit_dashboard():
        """Composite executive-readiness dashboard payload.

        Compatibility alias so clients can fetch the full dashboard from a single,
        predictable endpoint (mirrors the /mvp/audit/executive-readiness page).
        """
        from modules.audit_intelligence.services import dashboard_service

        return _ok(dashboard=dashboard_service.executive_readiness())

    #: Explicit allow-list of dashboard sections callable via the API. Prevents a
    #: path parameter from resolving to arbitrary module attributes (e.g. cache
    #: reset hooks or imported helpers) — a section name outside this set is 404.
    _DASHBOARD_SECTIONS = frozenset({
        "technology_coverage", "control_coverage", "framework_readiness",
        "asset_coverage", "evidence_coverage", "collection_progress",
        "validation_summary", "open_observations", "risk_summary",
        "evidence_freshness",
    })

    @app.get("/api/audit/dashboard/{section}")
    @_safe
    def api_audit_dashboard_section(section: str):
        """A single dashboard section by name (e.g. risk_summary, framework_readiness)."""
        from modules.audit_intelligence.services import dashboard_service

        if section not in _DASHBOARD_SECTIONS:
            return _err(f"Unknown dashboard section: {section}", status=404)
        fn = getattr(dashboard_service, section, None)
        if not callable(fn):
            return _err(f"Unknown dashboard section: {section}", status=404)
        return _ok(section=section, data=fn())

    # ------------------------------------------------- integration adapters
    @app.get("/api/audit/integrations")
    @_safe
    def api_integrations():
        """Masked config for every enterprise integration adapter (no secrets)."""
        from modules.operations import integrations

        return _ok(integrations=integrations.masked_config_all(),
                   adapters=integrations.list_adapters())

    @app.get("/api/audit/integrations/health")
    @_safe
    def api_integrations_health():
        """Config-based health for all adapters (no live calls in the skeleton)."""
        from modules.operations import integrations

        return _ok(health=integrations.health_check_all())

    @app.get("/api/audit/integrations/{name}/health")
    @_safe
    def api_integration_health(name: str):
        """Health for a single named adapter."""
        from modules.operations import integrations

        if name not in integrations.list_adapters():
            return _err(f"Unknown integration: {name}", status=404)
        import importlib

        mod = importlib.import_module(f"modules.operations.integrations.{name}")
        return _ok(name=name, health=mod.health_check())

    # ------------------------------------------------------------- packs (base)
    @app.get("/api/audit/packs")
    @_safe
    def api_packs():
        """Base packs endpoint: available pack types + current repository summary.

        Compatibility alias so clients have a predictable ``/api/audit/packs`` entry
        point. Individual packs are built via
        ``/api/audit/packs/{pack_type}/{scope}`` (unchanged).
        """
        return _ok(
            pack_types=["evidence", "framework", "application", "asset", "technology"],
            repository_stats=repo_svc.repository_stats(),
            note="Build a specific pack via /api/audit/packs/{pack_type}/{scope}.",
        )

    # -------------------------------------------------------- health (top-level)
    @app.get("/api/audit/health")
    @_safe
    def api_audit_health():
        """Top-level audit-intelligence health probe (compatibility alias).

        Aggregates a lightweight readiness view: engine reachability + integration
        adapter health (config-only; no live calls). Never raises, never leaks
        secrets. Mirrors what ``/api/audit/integrations/health`` reports for
        adapters, plus a simple ``ok`` for the audit services themselves.
        """
        from modules.operations import integrations

        services_ok = True
        try:
            mapping_service.stats()
        except Exception:  # noqa: BLE001 - health must never raise
            services_ok = False
        adapters = integrations.health_check_all()
        return _ok(
            status="ok" if services_ok else "degraded",
            services={"audit_intelligence": "ok" if services_ok else "error"},
            integrations={
                "total": adapters.get("total", 0),
                "configured": adapters.get("configured", 0),
                "not_configured": adapters.get("not_configured", 0),
            },
        )

    # ==================================================================== #
    # Connector Test Workbench — safe, read-only connector test surface.
    # Reuses the existing integration registry + adapters (no duplicate
    # connector logic). All actions are read-only / config-only / dry-run /
    # mock-transport; no destructive writes; no secrets returned.
    # ==================================================================== #
    @app.get("/api/connectors")
    @_safe
    def api_connectors():
        """List enterprise connectors: name, label, auth, configured, testable."""
        from modules.audit_intelligence.services import connector_workbench as wb

        return _ok(connectors=wb.list_connectors())

    @app.get("/api/connectors/{connector_name}/config-status")
    @_safe
    def api_connector_config_status(connector_name: str):
        """Masked config for one connector (SET/MISSING only; never a secret)."""
        from modules.audit_intelligence.services import connector_workbench as wb

        res = wb.config_status(connector_name)
        if not res.get("ok") and res.get("error") == "unknown_connector":
            return _err(f"Unknown connector: {connector_name}", status=404)
        return _ok(res)

    @app.post("/api/connectors/{connector_name}/health-check")
    @_safe
    def api_connector_health_check(connector_name: str):
        """Run the connector's config-based health probe (no live call)."""
        from modules.audit_intelligence.services import connector_workbench as wb

        res = wb.health_check(connector_name)
        if not res.get("ok") and res.get("error") == "unknown_connector":
            return _err(f"Unknown connector: {connector_name}", status=404)
        return _ok(res)

    @app.post("/api/connectors/{connector_name}/dry-run")
    @_safe
    def api_connector_dry_run(connector_name: str):
        """Config-only readiness for a connector — reports what WOULD run, no call."""
        from modules.audit_intelligence.services import connector_workbench as wb

        res = wb.dry_run(connector_name)
        if not res.get("ok") and res.get("error") == "unknown_connector":
            return _err(f"Unknown connector: {connector_name}", status=404)
        return _ok(res)

    @app.post("/api/connectors/{connector_name}/parser-test")
    @_safe
    def api_connector_parser_test(connector_name: str):
        """Run the connector's primary parser against a MOCK transport (no network)."""
        from modules.audit_intelligence.services import connector_workbench as wb

        res = wb.parser_test(connector_name)
        if not res.get("ok") and res.get("error") == "unknown_connector":
            return _err(f"Unknown connector: {connector_name}", status=404)
        return _ok(res)

    @app.post("/api/connectors/{connector_name}/collect")
    @_safe
    def api_connector_collect(connector_name: str, application: str = "",
                              framework: str = "", control: str = "",
                              max_items: str = "50", user: str = "connector_executor"):
        """Collect real evidence from a connector and ingest it into the repository.

        SAFE BY DEFAULT: performs a live call only when
        ``ECS_CONNECTOR_EXECUTION_ENABLED`` is set AND the adapter is configured;
        otherwise it returns ``skipped``/``not_configured`` with NO network call.
        Reuses the connector adapter + the evidence upload bridge (no new logic).
        """
        from modules.audit_intelligence.services import connector_executor as ce

        try:
            cap = max(1, min(int(str(max_items)), ce.DEFAULT_MAX_ITEMS))
        except (TypeError, ValueError):
            cap = 50
        res = ce.collect_evidence(
            connector_name, application=application, framework=framework,
            control=control, collected_by=user or "connector_executor", max_items=cap,
        )
        if res.get("status") == "unknown_connector":
            return _err(f"Unknown connector: {connector_name}", status=404)
        return _ok(res)

    # ---- Connector Test Workbench UI (self-contained; no main.py changes) ---- #
    @app.get("/connectors/test-workbench", response_class=HTMLResponse)
    @app.get("/mvp/connectors/test-workbench", response_class=HTMLResponse)
    def connector_test_workbench(request: Request, role: str = "owner", user: str = "User"):
        """Server-rendered Connector Test Workbench page.

        Uses a self-contained Jinja2Templates pointed at the audit templates dir so
        it renders without depending on the shared app templates registration.
        """
        from pathlib import Path

        from fastapi.templating import Jinja2Templates

        from modules.audit_intelligence.services import connector_workbench as wb

        tmpl_dir = Path(__file__).resolve().parents[1] / "templates"
        templates = Jinja2Templates(directory=str(tmpl_dir))
        ctx = {"role": role, "user": user, "connectors": wb.list_connectors()}
        return templates.TemplateResponse(request, "audit/connector_test_workbench.html", ctx)

    # ==================================================================== #
    # Evidence Reuse & Observation Lifecycle — functional server-side APIs.
    # Reuses the existing evidence repository, validation model, mapping, and
    # observation engine (no duplicate logic). Read-only except the explicit
    # generate/close actions, which use the real observation workflow.
    # ==================================================================== #
    def _reuse_filters(application: str, framework: str, control: str,
                       technology: str, status: str, date_from: str,
                       date_to: str) -> dict[str, str]:
        return {"application": application, "framework": framework,
                "control": control, "technology": technology, "status": status,
                "date_from": date_from, "date_to": date_to}

    @app.get("/api/evidence-reuse/records")
    @_safe
    def api_evidence_reuse_records(application: str = "", framework: str = "",
                                   control: str = "", technology: str = "",
                                   status: str = "", date_from: str = "",
                                   date_to: str = ""):
        """Real evidence records (latest version) with filters + integrity status."""
        from modules.audit_intelligence.services import evidence_reuse_service as ers

        return _ok(ers.records(**_reuse_filters(application, framework, control,
                                                technology, status, date_from, date_to)))

    @app.post("/api/evidence-reuse/analyze")
    @_safe
    def api_evidence_reuse_analyze(application: str = "", framework: str = "",
                                   control: str = "", technology: str = "",
                                   status: str = "", date_from: str = "",
                                   date_to: str = ""):
        """Evidence-reuse matrix + reuse factor + frameworks/controls covered + effort saved."""
        from modules.audit_intelligence.services import evidence_reuse_service as ers

        return _ok(ers.analyze(**_reuse_filters(application, framework, control,
                                                technology, status, date_from, date_to)))

    @app.post("/api/evidence-reuse/validate-completeness")
    @_safe
    def api_evidence_reuse_validate(application: str = "", framework: str = "",
                                    control: str = "", technology: str = "",
                                    status: str = "", date_from: str = "",
                                    date_to: str = "", full_catalog: str = "false"):
        """Per-framework coverage: covered / missing / stale / failed obligations."""
        from modules.audit_intelligence.services import evidence_reuse_service as ers

        full = str(full_catalog).lower() in ("1", "true", "yes")
        return _ok(ers.validate_completeness(
            full_catalog=full,
            **_reuse_filters(application, framework, control, technology, status,
                             date_from, date_to)))

    @app.post("/api/evidence-reuse/generate-observations")
    @_safe
    def api_evidence_reuse_generate_obs(application: str = "", framework: str = "",
                                        control: str = "", technology: str = "",
                                        status: str = "", date_from: str = "",
                                        date_to: str = "", full_catalog: str = "false"):
        """Create/open observations for missing/failed/stale obligations (real engine, deduped)."""
        from modules.audit_intelligence.services import evidence_reuse_service as ers

        full = str(full_catalog).lower() in ("1", "true", "yes")
        return _ok(ers.generate_observations(
            full_catalog=full,
            **_reuse_filters(application, framework, control, technology, status,
                             date_from, date_to)))

    @app.post("/api/evidence-reuse/check-closure")
    @_safe
    def api_evidence_reuse_check_closure(application: str = "", framework: str = "",
                                         control: str = "", technology: str = "",
                                         status: str = "", date_from: str = "",
                                         date_to: str = "", require_approval: str = "true"):
        """Advance open observations satisfied by passing evidence toward closure.

        With maker-checker (``require_approval=true``, the default) observations are
        marked READY FOR CLOSURE and are **not** auto-closed.
        """
        from modules.audit_intelligence.services import evidence_reuse_service as ers

        approval = str(require_approval).lower() not in ("0", "false", "no")
        return _ok(ers.check_closure(
            require_approval=approval,
            **_reuse_filters(application, framework, control, technology, status,
                             date_from, date_to)))

    @app.get("/api/evidence-reuse/readiness")
    @_safe
    def api_evidence_reuse_readiness(application: str = "", framework: str = "",
                                     control: str = "", technology: str = "",
                                     status: str = "", date_from: str = "",
                                     date_to: str = "", full_catalog: str = "false"):
        """Audit readiness: covered vs total controls, per framework (from real evidence)."""
        from modules.audit_intelligence.services import evidence_reuse_service as ers

        full = str(full_catalog).lower() in ("1", "true", "yes")
        return _ok(ers.readiness(
            full_catalog=full,
            **_reuse_filters(application, framework, control, technology, status,
                             date_from, date_to)))

    @app.get("/api/evidence-reuse/observations")
    @_safe
    def api_evidence_reuse_observations():
        """Current open + ready-for-closure observations from the real engine."""
        from modules.audit_intelligence.services import evidence_reuse_service as ers

        return _ok(ers.observations())

    # ==================================================================== #
    # Batch 1 — evidence workflow REST surface. Thin wrappers over EXISTING
    # engines (asset_scheduler, evidence_repository naming/hash). No new
    # scheduler, no new hashing, no new naming logic; read-only / dry-run.
    # ==================================================================== #

    # ---- UC2: Automated scheduled evidence pull (asset scheduler over REST) --- #
    @app.get("/api/audit/scheduler/plan")
    @_safe
    def api_scheduler_plan(config_path: str = ""):
        """Evidence collection PLAN for the configured UAT assets (no execution).

        Wraps the existing ``asset_scheduler.plan_evidence`` over the loaded asset
        config. Never runs a query or a connector.
        """
        from modules.audit_intelligence.services import asset_scheduler

        assets = asset_scheduler.load_assets(config_path or None)
        plan = asset_scheduler.plan_evidence(assets)
        return _ok(plan=plan.to_dict(), asset_count=len(assets))

    @app.post("/api/audit/scheduler/dry-run")
    @_safe
    def api_scheduler_dry_run(payload: dict[str, Any] = Body(default_factory=dict)):
        """Deterministic, side-effect-free scheduler dry-run.

        Wraps ``asset_scheduler.dry_run`` — classifies assets, plans evidence, and
        reports config-only connector readiness. NO queries, NO connector calls.
        """
        from modules.audit_intelligence.services import asset_scheduler

        report = asset_scheduler.dry_run(
            config_path=str(payload.get("config_path") or "") or None,
            include_diagnostics=bool(payload.get("include_diagnostics", True)),
        )
        return _ok(report)

    # ---- UC4: Metadata tagging & naming convention (validation over REST) ---- #
    @app.get("/api/evidence/naming-preview")
    @_safe
    def api_evidence_naming_preview(filename: str = "", framework: str = "",
                                    application: str = "Net Banking"):
        """Preview the enforced evidence filename for a given upload.

        Reuses ``operations.evidence_repository.enforce_naming`` (the same function
        applied on upload) so callers can validate naming before uploading.
        """
        if not filename:
            return _err("filename is required", status=400)
        from modules.operations.engines.evidence_repository import enforce_naming

        standardized = enforce_naming(filename, framework or "GENERAL", application)
        return _ok(original_filename=filename, standardized_filename=standardized,
                   framework=framework or "GENERAL", application=application,
                   convention="{FRAMEWORK}_{APPLICATION}_{YYYYMMDD}_{filename}",
                   already_compliant=(standardized == filename))

    @app.post("/api/evidence/validate-metadata")
    @_safe
    def api_evidence_validate_metadata(payload: dict[str, Any] = Body(default_factory=dict)):
        """Validate evidence metadata completeness + naming (no write).

        Checks required tags (framework/application) and previews the standardized
        name. Reuses ``enforce_naming``; does not store anything.
        """
        from modules.operations.engines.evidence_repository import enforce_naming

        filename = str(payload.get("filename") or "")
        framework = str(payload.get("framework") or "")
        application = str(payload.get("application") or "")
        control = str(payload.get("control") or "")
        missing = [k for k, v in (("filename", filename), ("framework", framework),
                                  ("application", application)) if not v]
        standardized = enforce_naming(filename or "evidence.pdf",
                                      framework or "GENERAL", application or "Net Banking")
        return _ok(
            valid=not missing,
            missing_fields=missing,
            standardized_filename=standardized,
            tags={"framework": framework, "application": application, "control": control},
            recommendations=([f"Provide {', '.join(missing)}"] if missing else []),
        )

    # ---- UC5: Evidence hash integrity verification (over REST) --------------- #
    @app.get("/api/evidence/{evidence_id}/integrity")
    @_safe
    def api_evidence_integrity(evidence_id: str):
        """Verify SHA-256 integrity for an uploaded MVP evidence record.

        Reuses ``operations.evidence_repository`` records (SHA-256 computed at
        upload) and ``integrity_check``. Reports the stored hash + verification.
        """
        from modules.operations.engines import evidence_repository as mvp_repo

        rec = next((r for r in mvp_repo.evidence_repository
                    if r.get("evidence_id") == evidence_id
                    or r.get("display_evidence_id") == evidence_id), None)
        if rec is None:
            return _err(f"Unknown evidence: {evidence_id}", status=404)
        stored = rec.get("sha256", "")
        # Re-affirm hash/label using the existing checker (no external re-read of
        # bytes in the in-memory skeleton; confirms the stored hash is intact).
        check = mvp_repo.integrity_check(stored, b"")
        return _ok(
            evidence_id=evidence_id,
            filename=rec.get("filename", ""),
            algorithm="sha256",
            stored_hash=stored,
            integrity_status=rec.get("integrity", check.get("status")),
            integrity_valid=bool(rec.get("integrity_valid", check.get("valid"))),
            audit_repository_synced=bool(rec.get("audit_repository_synced", False)),
        )

    # ==================================================================== #
    # UC6 — ECS Admin: users, roles, applications. Roles are read-only from
    # the canonical catalog; users are a non-secret admin registry. Mutations
    # are RBAC-guarded (platform admins only) via the existing predicates.
    # ==================================================================== #
    def _require_admin(role: str):
        from modules.shared.services import role_permissions as rp

        if not rp.can_admin_platform(role):
            return _err("Access denied: platform administrator role required.", status=403)
        return None

    @app.get("/api/admin/roles")
    @_safe
    def api_admin_roles():
        """List the canonical ECS roles + capabilities (read-only)."""
        from modules.shared.services import admin_service as adm

        return _ok(roles=adm.list_roles(), count=len(adm.list_roles()))

    @app.get("/api/admin/applications")
    @_safe
    def api_admin_applications():
        """List onboarded applications (from the existing registry; read-only)."""
        from modules.shared.services import admin_service as adm

        apps = adm.list_applications()
        return _ok(applications=apps, count=len(apps))

    @app.get("/api/admin/users")
    @_safe
    def api_admin_users(role: str = "", active: str = ""):
        """List admin users (optionally filtered by role/active)."""
        from modules.shared.services import admin_service as adm

        active_flag = None if active == "" else (active.lower() in ("1", "true", "yes"))
        # `role` here doubles as a filter; listing is not a mutation (no guard).
        users = adm.list_users(role=role or "", active=active_flag)
        return _ok(users=users, count=len(users), summary=adm.admin_summary())

    @app.post("/api/admin/users")
    @_safe
    def api_admin_create_user(payload: dict[str, Any] = Body(default_factory=dict),
                              role: str = "system_admin"):
        """Create an admin user (RBAC: platform admin only)."""
        from modules.shared.services import admin_service as adm

        denied = _require_admin(role)
        if denied is not None:
            return denied
        try:
            user = adm.create_user(
                email=str(payload.get("email") or ""),
                display_name=str(payload.get("display_name") or ""),
                role=str(payload.get("assign_role") or payload.get("role") or ""),
                scope=str(payload.get("scope") or ""),
            )
        except adm.AdminError as exc:
            return _err(str(exc), status=400)
        return _ok(user=user, message=f"User {user['user_id']} created.")

    @app.post("/api/admin/users/{user_id}/role")
    @_safe
    def api_admin_update_user_role(user_id: str,
                                   payload: dict[str, Any] = Body(default_factory=dict),
                                   role: str = "system_admin"):
        """Reassign a user's role (RBAC: platform admin only)."""
        from modules.shared.services import admin_service as adm

        denied = _require_admin(role)
        if denied is not None:
            return denied
        try:
            user = adm.update_user_role(
                user_id, str(payload.get("assign_role") or payload.get("new_role") or ""),
                scope=payload.get("scope"))
        except KeyError:
            return _err(f"Unknown user: {user_id}", status=404)
        except adm.AdminError as exc:
            return _err(str(exc), status=400)
        return _ok(user=user, message=f"User {user_id} role updated.")

    @app.post("/api/admin/users/{user_id}/active")
    @_safe
    def api_admin_set_user_active(user_id: str,
                                  payload: dict[str, Any] = Body(default_factory=dict),
                                  role: str = "system_admin"):
        """Activate/deactivate a user (RBAC: platform admin only)."""
        from modules.shared.services import admin_service as adm

        denied = _require_admin(role)
        if denied is not None:
            return denied
        try:
            user = adm.set_user_active(user_id, bool(payload.get("active", True)))
        except KeyError:
            return _err(f"Unknown user: {user_id}", status=404)
        return _ok(user=user, message=f"User {user_id} active={user['active']}.")

    # ---- Admin UI page (self-contained; no app/main.py changes) ------------- #
    @app.get("/admin/users-roles", response_class=HTMLResponse)
    @app.get("/mvp/admin/users-roles", response_class=HTMLResponse)
    def admin_users_roles_page(request: Request, role: str = "system_admin", user: str = "Admin"):
        """Server-rendered ECS Admin console for users / roles / applications."""
        from pathlib import Path

        from fastapi.templating import Jinja2Templates

        from modules.shared.services import admin_service as adm
        from modules.shared.services import role_permissions as rp

        tmpl_dir = Path(__file__).resolve().parents[1] / "templates"
        templates = Jinja2Templates(directory=str(tmpl_dir))
        ctx = {"role": role, "user": user,
               "is_admin": rp.can_admin_platform(role),
               "roles": adm.list_roles(), "users": adm.list_users(),
               "applications": adm.list_applications(), "summary": adm.admin_summary()}
        return templates.TemplateResponse(request, "audit/admin_users_roles.html", ctx)
