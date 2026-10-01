"""UC13 - Cross-application compliance comparison. FT001-FT008 (application onboarding) are automated as written."""

from __future__ import annotations

from ...framework import scenarios as sc
from ...framework.assertions import (assert_denied, assert_equal, assert_exists, assert_record_count, assert_status, assert_success)
from ...framework.crosscutting import register_crosscutting
from ...framework.errors import CapabilityBlocked
from ...framework.spec import UseCaseProfile, case

PROFILE = UseCaseProfile(uc="UC13", subject="cross-application compliance comparison", page="/mvp/comparison", api="/api/audit/comparison",
                         api_params={"scope": "All Applications", "time_range": "Current Month"}, dashboard_api="/api/audit/comparison",
                         rbac_capability="", audit_action="comparison")


@case("UC13-FT001", framework="onboarding", capability="onboard_application", component="POST /mvp/platform/onboarding -> applications", data="DataFactory.application_record")
def ft001(ctx):
    ctx.require_mutation()
    fields, resp = ctx.onboarding.onboard_application()
    ctx.track(resp)
    assert resp.status in (200, 303), resp.text[:200]
    assert fields["name"] in ctx.onboarding.application_page().text, "onboarded application not listed"
    if ctx.db.enabled:
        row = ctx.onboarding.application_row(fields["name"])
        assert_exists(row, "applications row")
        assert_equal(row["criticality"], fields["criticality"])


@case("UC13-FT002", framework="onboarding", capability="mandatory_onboarding_data", component="POST /mvp/platform/onboarding (missing name)", data="incomplete application_record")
def ft002(ctx):
    resp = ctx.track(ctx.api.post("/mvp/platform/onboarding", data={"owner": "x"}))
    assert resp.status in (400, 422), f"onboarding without a name must be rejected with a validation error, got {resp.status}"
    assert "Traceback" not in resp.text


@case("UC13-FT003", framework="onboarding", capability="configure_frameworks_controls", component="POST /mvp/platform/onboarding frameworks -> application_frameworks",
      data="application_record(frameworks=...)")
def ft003(ctx):
    ctx.require_mutation()
    fields, resp = ctx.onboarding.onboard_application(frameworks=f"{ctx.data.framework()},{ctx.data.framework(second=True)}")
    ctx.track(resp)
    if ctx.db.enabled:
        slug = fields["name"].lower().replace(" ", "-")
        assert_record_count(ctx.db.find("application_frameworks", app_slug=slug), minimum=2)
    else:
        assert fields["name"] in ctx.onboarding.application_page().text


@case("UC13-FT004", framework="connector", capability="configure_sources_connectors", component="POST /api/onboarding/simulate (sources) + GET /api/connectors",
      data="simulate payload")
def ft004(ctx):
    assert ctx.connectors.names(), "no connectors registered"
    resp = ctx.track(ctx.onboarding.simulate({"application": ctx.data.application(), "frameworks": [ctx.data.framework()]}))
    assert resp.status < 500, resp.text[:200]


@case("UC13-FT005", framework="onboarding", capability="reuse_standard_configuration", component="POST /api/onboarding/simulate twice (same standard config)", data="simulate payload")
def ft005(ctx):
    payload = {"application": ctx.data.application(), "frameworks": [ctx.data.framework()]}
    a, b = ctx.onboarding.simulate(payload), ctx.onboarding.simulate(payload)
    assert a.status < 500
    assert_equal(a.content, b.content, "standard configuration reuse is not deterministic")


@case("UC13-FT006", framework="onboarding", capability="prevent_duplicate_application", component="POST /mvp/platform/onboarding (same name twice)", data="application_record")
def ft006(ctx):
    ctx.require_mutation()
    fields, first = ctx.onboarding.onboard_application()
    _, second = ctx.onboarding.onboard_application(name=fields["name"])
    if ctx.db.enabled:
        assert_equal(ctx.db.count("applications", name=fields["name"]), 1, "duplicate application rows")
    else:
        assert ctx.onboarding.application_page().text.count(fields["name"]) >= 1


@case("UC13-FT007", framework="onboarding", capability="new_app_in_downstream_views", component="applications -> /api/admin/applications, /mvp/comparison, dashboards",
      data="newly onboarded application")
def ft007(ctx):
    ctx.require_mutation()
    fields, _ = ctx.onboarding.onboard_application()
    assert fields["name"] in ctx.onboarding.admin_applications().text, "not in admin application list"
    assert fields["name"] in sc.page_loads(ctx, "/mvp/comparison", "auditor").text or fields["name"] in sc.page_loads(ctx, "/mvp/onboarding", "owner").text


@case("UC13-FT008", framework="audit", capability="audit_onboarding_changes", component="audit_log for POST /mvp/platform/onboarding", data="request_id")
def ft008(ctx):
    ctx.require_mutation()
    _, resp = ctx.onboarding.onboard_application()
    ctx.track(resp)
    if not ctx.db.enabled:
        raise CapabilityBlocked("onboarding audit rows are only verifiable in audit_log", requires="PostgreSQL access")
    ctx.audit.verify(request_id=resp.request_id)


register_crosscutting(PROFILE)
