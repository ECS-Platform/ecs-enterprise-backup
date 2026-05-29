"""Drill-down API routes for Risk Register & Governance Analytics demo modules."""

from __future__ import annotations

from fastapi.responses import JSONResponse

from app.grc_demo_service import governance_drill, risk_drill


def register_grc_demo_routes(app):
    @app.get("/api/grc-demo/risk/drill")
    def api_risk_drill(metric: str = "", item_id: str = "", role: str = "owner"):
        return JSONResponse({"ok": True, "payload": risk_drill(metric, item_id, role)})

    @app.get("/api/grc-demo/governance/drill")
    def api_governance_drill(metric: str = "", item_id: str = "", role: str = "cio"):
        return JSONResponse({"ok": True, "payload": governance_drill(metric, item_id, role)})

    @app.get("/api/grc-demo/governance/intel")
    def api_governance_intel(role: str = "cio"):
        from app.grc_demo_service import build_governance_analytics_demo_view

        view = build_governance_analytics_demo_view(role)
        intel = view["intel"]
        return JSONResponse({
            "ok": True,
            "intel": intel,
            "kpis": view["kpis"],
            "scope_summary": intel.get("scope_summary", ""),
            "repeat_failures": view.get("repeat_failures", []),
            "top_risk_applications": view.get("top_risk_applications", []),
        })
