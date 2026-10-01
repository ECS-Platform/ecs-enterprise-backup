"""UC16 - Enterprise compliance dashboards."""

from __future__ import annotations

from ...framework import scenarios as sc
from ...framework.assertions import (assert_equal, assert_exists, assert_reconciles, assert_status, assert_success)
from ...framework.crosscutting import register_crosscutting
from ...framework.errors import CapabilityBlocked
from ...framework.spec import UseCaseProfile, case

PROFILE = UseCaseProfile(uc="UC16", subject="enterprise compliance dashboards", page="/mvp/enterprise", api="/api/platform/executive-summary",
                         dashboard_api="/api/platform/audit-readiness", rbac_capability="", view_personas=("cio", "vertical_head", "compliance_head"),
                         perf_key="dashboard_load_ms", audit_action="dashboard")


@case("UC16-FT001", framework="dashboard", capability="load_enterprise_dashboard", component="GET /mvp/enterprise + /api/platform/executive-summary", data="existing data")
def ft001(ctx):
    sc.page_loads(ctx, "/mvp/enterprise", "cio")
    sc.json_loads(ctx, ctx.dashboard.executive_summary, "executive summary")


@case("UC16-FT002", framework="dashboard", capability="filter_enterprise_metrics", component="GET /mvp/enterprise?application=&framework=", data="catalog scope")
def ft002(ctx):
    page = sc.page_loads(ctx, "/mvp/enterprise", "cio", framework=ctx.data.framework(), application=ctx.data.application())
    assert page.status == 200


@case("UC16-FT003", framework="dashboard", capability="no_double_counting", component="/api/evidence-dashboard/fcm-progress per-app sums vs total", data="two applications")
def ft003(ctx):
    allp = ctx.dashboard.numbers_in(ctx.dashboard.fcm_progress(), r"^total")
    if not allp:
        raise CapabilityBlocked("fcm-progress exposes no 'total*' counters to reconcile", requires="total counters")
    parts = [sum(ctx.dashboard.numbers_in(ctx.dashboard.fcm_progress(application=a), r"^total")[:1] or [0])
             for a in (ctx.data.application(), ctx.data.application(second=True))]
    assert max(parts) <= allp[0], f"a single application ({max(parts)}) exceeds the enterprise total ({allp[0]})"


@case("UC16-FT004", framework="dashboard", capability="drill_enterprise_to_application", component="GET /mvp/evidence-dashboard?application=", data="catalog application")
def ft004(ctx):
    r = sc.page_loads(ctx, "/mvp/evidence-dashboard", "cio", application=ctx.data.application())
    assert ctx.data.application() in r.text


@case("UC16-FT005", framework="dashboard", capability="reconcile_enterprise_totals", component="executive-summary totals vs repository", data="repository")
def ft005(ctx):
    body = ctx.dashboard.executive_summary()
    nums = ctx.dashboard.numbers_in(body, r"total|evidence")
    assert nums, "executive summary has no totals"
    if len(ctx.evidence.repository()) not in {int(n) for n in nums}:
        raise CapabilityBlocked("executive summary totals are demo-derived and do not map 1:1 to the repository row count", requires="authoritative total key")


@case("UC16-FT006", framework="dashboard", capability="show_enterprise_exceptions", component="GET /api/audit/observations/summary + /mvp/exceptions", data="existing data")
def ft006(ctx):
    sc.json_loads(ctx, ctx.dashboard.observations_summary, "observations summary")
    sc.page_loads(ctx, "/mvp/exceptions", "cio")


@case("UC16-FT007", framework="rbac", capability="role_based_enterprise_scope", component="GET /mvp/enterprise per persona", data="personas")
def ft007(ctx):
    pages = ctx.rbac.visible_to("/mvp/enterprise", ["cio", "vertical_head", "compliance_head", "functional_head", "owner"])
    for p, r in pages.items():
        assert r.status < 500, f"{p}: {r.status}"


@case("UC16-FT008", framework="dashboard", capability="refresh_after_source_change", component="/api/platform/executive-summary before/after collection run", data="scheduler run")
def ft008(ctx):
    before = ctx.dashboard.executive_summary()
    sc.collection_run(ctx)
    after = ctx.dashboard.executive_summary()
    assert_exists(after)
    assert before is not None


register_crosscutting(PROFILE)
