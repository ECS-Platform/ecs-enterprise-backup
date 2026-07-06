"""REST API for the ECS Audit Intelligence layer (Milestone 4).

Reuses the existing FastAPI app + the ``register_*_routes(app)`` convention. All
endpoints are JSON under ``/api/audit/`` and are thin wrappers over the M1-M3
service facades (no new business logic here). Read endpoints are GET; state-
changing actions (run/retry/cancel/transition/store/pack) are POST.

Responses follow the house style: ``{"ok": bool, ...payload}``.
"""

from __future__ import annotations

from typing import Any

from fastapi import Body
from fastapi.responses import JSONResponse

from modules.audit_intelligence.services import asset_service, mapping_service
from modules.audit_intelligence.services import audit_repository_service as repo_svc
from modules.audit_intelligence.services import evidence_service


def _ok(payload: dict[str, Any] | None = None, **extra: Any) -> JSONResponse:
    body: dict[str, Any] = {"ok": True}
    if payload:
        body.update(payload)
    body.update(extra)
    return JSONResponse(body)


def _err(message: str, status: int = 404) -> JSONResponse:
    return JSONResponse({"ok": False, "error": message}, status_code=status)


def register_audit_intelligence_routes(app) -> None:
    # ----------------------------------------------------------------- mapping
    @app.get("/api/audit/mapping/technologies")
    def api_map_technologies():
        return _ok(technologies=mapping_service.technologies())

    @app.get("/api/audit/mapping/frameworks")
    def api_map_frameworks():
        return _ok(frameworks=mapping_service.frameworks())

    @app.get("/api/audit/mapping/graph")
    def api_map_graph():
        return _ok(graph=mapping_service.graph())

    @app.get("/api/audit/mapping/stats")
    def api_map_stats():
        return _ok(stats=mapping_service.stats())

    @app.get("/api/audit/mapping/technology/{technology}")
    def api_map_technology(technology: str):
        detail = mapping_service.technology_detail(technology)
        return _ok(detail=detail) if detail else _err(f"Unknown technology: {technology}")

    @app.get("/api/audit/mapping/framework/{framework}")
    def api_map_framework(framework: str):
        detail = mapping_service.framework_detail(framework)
        return _ok(detail=detail) if detail else _err(f"Unknown framework: {framework}")

    @app.get("/api/audit/mapping/search")
    def api_map_search(query: str = "", technology: str = "", framework: str = ""):
        return _ok(results=mapping_service.search(query=query, technology=technology, framework=framework))

    # ------------------------------------------------------------------ assets
    @app.get("/api/audit/assets")
    def api_assets(docker_compose: bool = True, enterprise_grc: bool = False):
        assets = asset_service.discover_assets(
            include_docker_compose=docker_compose, include_enterprise_grc=enterprise_grc
        )
        return _ok(
            inventory=asset_service.inventory(assets),
            coverage=asset_service.coverage_summary(assets),
        )

    @app.get("/api/audit/assets/technology-inventory")
    def api_asset_tech_inventory(docker_compose: bool = True, enterprise_grc: bool = False):
        assets = asset_service.discover_assets(
            include_docker_compose=docker_compose, include_enterprise_grc=enterprise_grc
        )
        return _ok(technology_inventory=asset_service.technology_inventory(assets))

    @app.get("/api/audit/assets/fingerprints")
    def api_asset_fingerprints(docker_compose: bool = True, enterprise_grc: bool = False):
        assets = asset_service.discover_assets(
            include_docker_compose=docker_compose, include_enterprise_grc=enterprise_grc
        )
        return _ok(fingerprint_report=asset_service.fingerprint_report(assets))

    # -------------------------------------------------------------------- runs
    @app.get("/api/audit/runs")
    def api_runs():
        return _ok(runs=evidence_service.list_runs())

    @app.get("/api/audit/runs/{run_id}")
    def api_run(run_id: str):
        run = evidence_service.get_run(run_id)
        return _ok(run=run) if run else _err(f"Unknown run: {run_id}")

    @app.post("/api/audit/runs")
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
    def api_retry_run(run_id: str):
        try:
            run = evidence_service.retry_run(run_id)
        except KeyError:
            return _err(f"Unknown run: {run_id}")
        return _ok(run=run)

    @app.post("/api/audit/runs/{run_id}/cancel")
    def api_cancel_run(run_id: str):
        try:
            run = evidence_service.cancel_run(run_id)
        except KeyError:
            return _err(f"Unknown run: {run_id}")
        return _ok(run=run)

    @app.get("/api/audit/runs/{run_id}/validation")
    def api_run_validation(run_id: str):
        result = evidence_service.validate_run(run_id)
        return _ok(validation=result) if result else _err(f"Unknown run: {run_id}")

    # ------------------------------------------------------------- repository
    @app.get("/api/audit/evidence")
    def api_evidence_search(
        query: str = "", technology: str = "", framework: str = "",
        asset_id: str = "", verdict: str = "", tag: str = "", latest_only: bool = True,
    ):
        return _ok(evidence=repo_svc.repository_search(
            query=query, technology=technology, framework=framework,
            asset_id=asset_id, verdict=verdict, tag=tag, latest_only=latest_only,
        ))

    @app.get("/api/audit/evidence/stats")
    def api_evidence_stats():
        return _ok(stats=repo_svc.repository_stats())

    @app.get("/api/audit/evidence/{evidence_key}/versions")
    def api_evidence_versions(evidence_key: str):
        return _ok(versions=repo_svc.evidence_versions(evidence_key))

    @app.get("/api/audit/evidence/{evidence_key}/timeline")
    def api_evidence_timeline(evidence_key: str):
        return _ok(timeline=repo_svc.evidence_timeline(evidence_key))

    # ----------------------------------------------------------- observations
    @app.get("/api/audit/observations")
    def api_observations(status: str = "", severity: str = "", framework: str = "", technology: str = ""):
        filters = {k: v for k, v in dict(
            status=status, severity=severity, framework=framework, technology=technology
        ).items() if v}
        return _ok(observations=repo_svc.list_observations(**filters))

    @app.get("/api/audit/observations/summary")
    def api_observations_summary():
        return _ok(summary=repo_svc.observation_summary())

    @app.get("/api/audit/observations/{obs_id}")
    def api_observation(obs_id: str):
        o = repo_svc.get_observation(obs_id)
        return _ok(observation=o) if o else _err(f"Unknown observation: {obs_id}")

    @app.post("/api/audit/observations/{obs_id}/transition")
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
    @app.get("/api/audit/packs/{pack_type}/{scope}")
    def api_pack(pack_type: str, scope: str):
        pack = repo_svc.build_pack(pack_type, scope)
        return _ok(pack=pack) if pack is not None else _err(f"Unknown pack type: {pack_type}", status=400)

    @app.post("/api/audit/packs/application")
    def api_application_pack(payload: dict[str, Any] = Body(default_factory=dict)):
        scope = str(payload.get("application") or "")
        asset_ids = payload.get("asset_ids") or []
        pack = repo_svc.build_pack("application", scope, asset_ids=asset_ids)
        return _ok(pack=pack) if pack is not None else _err("could not build application pack", status=400)
