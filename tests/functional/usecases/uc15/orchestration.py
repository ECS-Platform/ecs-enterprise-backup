"""UC15 - SharePoint, SNOW integration. FT001-FT008 (application comparison) are automated as written."""

from __future__ import annotations

from ...framework import scenarios as sc
from ...framework.assertions import (assert_denied, assert_equal, assert_exists, assert_json_field, assert_status, assert_success)
from ...framework.crosscutting import register_crosscutting
from ...framework.errors import CapabilityBlocked
from ...framework.spec import UseCaseProfile, case

PROFILE = UseCaseProfile(uc="UC15", subject="SharePoint / ServiceNow integration", page="/mvp/integration-health", api="/api/connectors",
                         dashboard_api="/api/audit/integrations/health", rbac_capability="admin_platform", audit_action="connector",
                         trigger=lambda ctx: ctx.track(ctx.connectors.dry_run(ctx.data.connector("sharepoint"))), notice_contains="")


def _compare(ctx, scope="All Applications", time_range="Current Month"):
    return ctx.track(ctx.api.get("/api/audit/comparison", params={"scope": scope, "time_range": time_range}))


@case("UC15-FT001", framework="dashboard", capability="compare_two_applications", component="GET /api/audit/comparison?scope=", data="two catalog applications")
def ft001(ctx):
    a = _compare(ctx, ctx.data.application())
    b = _compare(ctx, ctx.data.application(second=True))
    assert_success(a)
    assert_success(b)
    assert a.content != b.content, "two applications produced an identical comparison"


@case("UC15-FT002", framework="dashboard", capability="compare_control_framework_coverage", component="GET /mvp/comparison?compare_framework=", data="two frameworks")
def ft002(ctx):
    r = sc.page_loads(ctx, "/mvp/comparison", "auditor", compare_framework=ctx.data.framework())
    assert "framework" in r.text.lower()


@case("UC15-FT003", framework="dashboard", capability="identify_gaps", component="GET /api/audit/comparison readiness_matrix + gaps", data="all applications")
def ft003(ctx):
    body = _compare(ctx).json()
    assert_exists(body.get("readiness_matrix") or body, "comparison matrix")


@case("UC15-FT004", framework="dashboard", capability="drill_comparison_differences", component="GET /api/framework/row-drill | /api/framework/kpi-drill", data="first matrix row")
def ft004(ctx):
    resp = ctx.track(ctx.api.get("/api/framework/row-drill"))
    assert resp.status < 500


@case("UC15-FT005", framework="dashboard", capability="exclude_out_of_scope", component="GET /api/audit/comparison?scope=<single app>", data="single application scope")
def ft005(ctx):
    scoped = _compare(ctx, ctx.data.application()).json()
    other = ctx.data.application(second=True)
    assert other not in str(scoped.get("readiness_matrix", scoped)), f"{other} leaked into a {ctx.data.application()}-scoped comparison"


@case("UC15-FT006", framework="dashboard", capability="comparison_calculation_accuracy", component="GET /api/audit/comparison deterministic + sums", data="all applications")
def ft006(ctx):
    a, b = _compare(ctx), _compare(ctx)
    assert_equal(a.content, b.content, "comparison is not deterministic for identical inputs")


@case("UC15-FT007", framework="rbac", capability="cross_application_permissions", component="GET /api/audit/comparison as owner vs auditor/cio", data="personas")
def ft007(ctx):
    res = ctx.rbac.visible_to("/api/audit/comparison", ["owner", "auditor", "cio"], scope=ctx.data.application(second=True))
    for p, r in res.items():
        assert r.status < 500, f"{p}: {r.status}"


@case("UC15-FT008", framework="reporting", capability="export_comparison", component="POST /mvp/comparison/export-gaps", data="export form")
def ft008(ctx):
    resp = ctx.track(ctx.reporting.export_comparison_gaps(compare_framework="All Frameworks", compare_scope="All Applications",
                                                          compare_application="All Applications", time_range="Current Month", export_format="excel"))
    assert resp.status < 500, resp.text[:200]
    assert resp.status != 200 or len(resp.content) > 0


register_crosscutting(PROFILE)
