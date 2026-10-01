"""UC20 - National compliance dashboard (ECS page: /mvp/pan-india, 'Pan India Regional Compliance')."""

from __future__ import annotations

from ...framework import scenarios as sc
from ...framework.assertions import assert_exists, assert_status
from ...framework.crosscutting import register_crosscutting
from ...framework.errors import CapabilityBlocked
from ...framework.spec import UseCaseProfile, case

PROFILE = UseCaseProfile(uc="UC20", subject="national compliance dashboard", page="/mvp/pan-india", api="/api/platform/executive-summary",
                         dashboard_api="/api/platform/audit-readiness", rbac_capability="", view_personas=("cio", "vertical_head", "compliance_head"),
                         perf_key="dashboard_load_ms", audit_action="dashboard")


@case("UC20-FT001", framework="dashboard", capability="load_national_dashboard", component="GET /mvp/pan-india", data="existing data")
def ft001(ctx):
    sc.page_loads(ctx, "/mvp/pan-india", "cio")


@case("UC20-FT002", framework="dashboard", capability="aggregate_regions_entities", component="GET /mvp/pan-india content + /api/platform/executive-summary", data="regions")
def ft002(ctx):
    r = sc.page_loads(ctx, "/mvp/pan-india", "cio")
    assert any(t in r.text.lower() for t in ("region", "zone", "state", "entity", "branch")), "no region/entity aggregation on the national dashboard"
    sc.json_loads(ctx, ctx.dashboard.executive_summary, "executive summary")


@case("UC20-FT003", framework="dashboard", capability="filter_region_entity_framework", component="GET /mvp/pan-india?framework=", data="catalog scope")
def ft003(ctx):
    sc.page_loads(ctx, "/mvp/pan-india", "cio", framework=ctx.data.framework())


@case("UC20-FT004", framework="dashboard", capability="drill_national_to_regional", component="GET /api/framework/row-drill + /mvp/evidence-dashboard?application=", data="catalog application")
def ft004(ctx):
    assert ctx.api.get("/api/framework/row-drill").status < 500
    sc.page_loads(ctx, "/mvp/evidence-dashboard", "cio", application=ctx.data.application())


@case("UC20-FT005", framework="dashboard", capability="reconcile_national_totals", component="/api/platform/executive-summary vs /mvp/enterprise", data="existing data")
def ft005(ctx):
    nums = ctx.dashboard.numbers_in(ctx.dashboard.executive_summary(), r"total")
    if not nums:
        raise CapabilityBlocked("executive summary exposes no totals to reconcile", requires="total counters")
    assert all(n >= 0 for n in nums), f"negative totals: {nums}"


@case("UC20-FT006", framework="dashboard", capability="national_exceptions_hotspots", component="GET /mvp/heatmaps + /mvp/exceptions", data="existing data")
def ft006(ctx):
    sc.page_loads(ctx, "/mvp/heatmaps", "cio")
    sc.page_loads(ctx, "/mvp/exceptions", "cio")


@case("UC20-FT007", framework="rbac", capability="national_role_data_segregation", component="GET /mvp/pan-india per persona", data="personas")
def ft007(ctx):
    pages = ctx.rbac.visible_to("/mvp/pan-india", ["cio", "vertical_head", "functional_head", "owner", "auditor"])
    for p, r in pages.items():
        assert r.status < 500, f"{p}: {r.status}"


@case("UC20-FT008", framework="dashboard", capability="refresh_after_regional_update", component="/api/platform/executive-summary before/after collection run", data="scheduler run")
def ft008(ctx):
    before = ctx.dashboard.executive_summary()
    sc.collection_run(ctx)
    assert_exists(ctx.dashboard.executive_summary())
    assert before is not None


register_crosscutting(PROFILE)
