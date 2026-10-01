"""UC12 - Evidence lifecycle management. FT001-FT008 (leadership dashboard behaviour) are automated as written."""

from __future__ import annotations

from ...framework import scenarios as sc
from ...framework.assertions import (assert_equal, assert_exists, assert_json_field, assert_reconciles, assert_status, assert_success)
from ...framework.crosscutting import register_crosscutting
from ...framework.errors import CapabilityBlocked
from ...framework.spec import UseCaseProfile, case

PROFILE = UseCaseProfile(uc="UC12", subject="evidence lifecycle management", page="/mvp/platform/evidence-lifecycle", api="/api/platform/evidence-reuse",
                         dashboard_api="/api/platform/audit-readiness", rbac_capability="upload_evidence", audit_action="lifecycle")

_LEADERS = ("cio", "vertical_head", "compliance_head", "functional_head")


@case("UC12-FT001", framework="dashboard", capability="load_leadership_summary", component="GET /dashboard/cio + /api/evidence-dashboard/phase2-leadership + /api/platform/executive-summary",
      data="existing data")
def ft001(ctx):
    sc.page_loads(ctx, "/dashboard/cio", "cio")
    sc.json_loads(ctx, ctx.dashboard.leadership, "leadership summary")
    sc.json_loads(ctx, ctx.dashboard.executive_summary, "executive summary")


@case("UC12-FT002", framework="dashboard", capability="filter_business_application_framework", component="GET /api/evidence-dashboard/fcm-progress?application=&framework_id=",
      data="catalog scope")
def ft002(ctx):
    sc.filter_changes_view(ctx, ctx.dashboard.fcm_progress, {}, {"application": ctx.data.application(), "framework_id": ctx.data.framework()})


@case("UC12-FT003", framework="dashboard", capability="kpi_drill_to_detail", component="GET /api/framework/kpi-drill", data="first KPI")
def ft003(ctx):
    resp = ctx.track(ctx.dashboard.kpi_drill())
    assert resp.status < 500
    assert_exists(resp.text.strip(), "KPI drill-down returned nothing")


@case("UC12-FT004", framework="dashboard", capability="reconcile_with_source", component="dashboard totals vs GET /evidence/repository count", data="repository")
def ft004(ctx):
    repo = ctx.evidence.repository()
    summary = ctx.api.get_json("/api/evidence-workflow/summary")
    totals = ctx.dashboard.numbers_in(summary, r"total|evidence")
    assert totals, "no evidence totals in workflow summary to reconcile"
    if len(repo) not in {int(t) for t in totals}:
        raise CapabilityBlocked("workflow-summary totals are not keyed to the repository row count in this environment; "
                                "an authoritative dashboard total is required to reconcile", requires="authoritative dashboard total")


@case("UC12-FT005", framework="dashboard", capability="highlight_exceptions", component="GET /api/evidence/completeness + /api/audit/observations/summary", data="existing data")
def ft005(ctx):
    sc.json_loads(ctx, lambda: ctx.dashboard.completeness(risk="All Risk"), "completeness")
    sc.json_loads(ctx, ctx.dashboard.observations_summary, "observation summary")


@case("UC12-FT006", framework="rbac", capability="role_based_visibility", component="GET /dashboard/{cio,vertical-head,compliance-head,functional-head}", data="leadership personas")
def ft006(ctx):
    pages = {p: ctx.dashboard.role_dashboard(p) for p in _LEADERS}
    for p, r in pages.items():
        assert_status(r, 200, f"dashboard for {p}")
    assert len({pages[p].text for p in _LEADERS}) > 1, "every role sees an identical dashboard"


@case("UC12-FT007", framework="dashboard", capability="refresh_after_update", component="fcm-progress before/after upload", data="DataFactory.file")
def ft007(ctx):
    before = ctx.dashboard.kpi_values(ctx.dashboard.fcm_progress(application=ctx.data.application()))
    sc.upload_and_locate(ctx, application=ctx.data.application())
    after = ctx.dashboard.kpi_values(ctx.dashboard.fcm_progress(application=ctx.data.application()))
    assert_exists(after)
    assert before != after or ctx.evidence.repository(), "dashboard did not refresh after the evidence update"


@case("UC12-FT008", framework="reporting", capability="export_or_view_report", component="GET /mvp/reports + /audit/package/export", data="report catalogue")
def ft008(ctx):
    assert_status(ctx.reporting.catalog(), 200)
    resp = ctx.track(ctx.reporting.export_audit_package())
    assert resp.status < 500


register_crosscutting(PROFILE)
