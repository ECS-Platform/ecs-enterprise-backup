"""UC19 - Compliance trend & closure."""

from __future__ import annotations

from ...framework import scenarios as sc
from ...framework.assertions import (assert_equal, assert_exists, assert_status, assert_success)
from ...framework.crosscutting import register_crosscutting
from ...framework.errors import CapabilityBlocked
from ...framework.spec import UseCaseProfile, case

PROFILE = UseCaseProfile(uc="UC19", subject="compliance trend and closure", page="/mvp/trends", api="/api/audit/observations/summary",
                         dashboard_api="/api/evidence-reuse/readiness", rbac_capability="", audit_action="observation")


@case("UC19-FT001", framework="dashboard", capability="display_trend", component="GET /mvp/trends", data="existing history")
def ft001(ctx):
    r = sc.page_loads(ctx, "/mvp/trends", "cio")
    assert any(t in r.text.lower() for t in ("trend", "month", "quarter")), "trend page shows no trend content"


@case("UC19-FT002", framework="dashboard", capability="change_time_range", component="GET /mvp/trends?time_range=", data="time ranges")
def ft002(ctx):
    a = sc.page_loads(ctx, "/mvp/trends", "cio", time_range="Current Month")
    b = sc.page_loads(ctx, "/mvp/trends", "cio", time_range="Last 12 Months")
    assert a.status == b.status == 200


@case("UC19-FT003", framework="dashboard", capability="filter_trend", component="GET /mvp/trends?application=&framework=", data="catalog scope")
def ft003(ctx):
    sc.page_loads(ctx, "/mvp/trends", "cio", application=ctx.data.application(), framework=ctx.data.framework())


@case("UC19-FT004", framework="dashboard", capability="historical_calculation_accuracy", component="GET /mvp/trends deterministic for fixed range", data="fixed range")
def ft004(ctx):
    a = ctx.api.get("/mvp/trends", params={"time_range": "Last 12 Months"})
    b = ctx.api.get("/mvp/trends", params={"time_range": "Last 12 Months"})
    assert_equal(a.content, b.content, "historical trend changed between identical requests")


@case("UC19-FT005", framework="dashboard", capability="improving_deteriorating_areas", component="GET /mvp/trends content", data="existing history")
def ft005(ctx):
    r = sc.page_loads(ctx, "/mvp/trends", "cio")
    assert any(t in r.text.lower() for t in ("improv", "deteriorat", "declin", "increase", "decrease", "delta")), "no improving/deteriorating indicators"


@case("UC19-FT006", framework="dashboard", capability="drill_from_trend_point", component="GET /api/framework/kpi-drill (trend KPI)", data="trend point")
def ft006(ctx):
    assert ctx.dashboard.kpi_drill().status < 500


@case("UC19-FT007", framework="dashboard", capability="history_preserved_after_state_change", component="/mvp/trends before/after observation/evidence change", data="DataFactory.file")
def ft007(ctx):
    before = ctx.api.get("/mvp/trends", params={"time_range": "Last 12 Months"}).content
    sc.upload_and_locate(ctx)
    after = ctx.api.get("/mvp/trends", params={"time_range": "Last 12 Months"}).content
    assert before and after, "trend history lost after a current-state change"


@case("UC19-FT008", framework="reporting", capability="export_trend_data", component="trend page export / POST /mvp/comparison/export-gaps", data="export form")
def ft008(ctx):
    resp = ctx.track(ctx.reporting.export_comparison_gaps(compare_framework="All Frameworks", compare_scope="All Applications",
                                                          compare_application="All Applications", time_range="Last 12 Months", export_format="excel"))
    assert resp.status < 500


register_crosscutting(PROFILE)
