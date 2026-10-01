"""UC17 - Automated regulatory reporting."""

from __future__ import annotations

import re

from ...framework import scenarios as sc
from ...framework.assertions import (assert_equal, assert_exists, assert_report_value, assert_status, assert_success, assert_traceability)
from ...framework.crosscutting import register_crosscutting
from ...framework.errors import CapabilityBlocked
from ...framework.spec import UseCaseProfile, case

PROFILE = UseCaseProfile(uc="UC17", subject="automated regulatory reporting", page="/mvp/reports", api="/audit/package/export",
                         dashboard_api="/api/platform/audit-readiness", rbac_capability="", perf_key="report_generation_ms", audit_action="report")


def _report_id(ctx) -> str:
    """A real downloadable report id from the report catalogue page (links to /mvp/reports/download/{report_id})."""
    m = re.search(r"/mvp/reports/download/([A-Za-z0-9_.\-]+)", ctx.reporting.catalog().text)
    if not m:
        raise CapabilityBlocked("no downloadable report id discoverable on /mvp/reports", requires="report catalogue")
    return m.group(1)


@case("UC17-FT001", framework="reporting", capability="generate_report", component="GET /mvp/reports/view/{type} + /mvp/reports/download/{id}", data="first catalogue report")
def ft001(ctx):
    resp = ctx.track(ctx.reporting.download(_report_id(ctx), "csv"))
    assert_status(resp, 200)
    assert len(resp.content) > 0, "generated report is empty"


@case("UC17-FT002", framework="reporting", capability="populate_from_ecs_data", component="report content vs GET /evidence/repository", data="uploaded evidence")
def ft002(ctx):
    f, _, row = sc.upload_and_locate(ctx)
    resp = ctx.track(ctx.reporting.download(_report_id(ctx), "csv"))
    assert_status(resp, 200)
    assert ctx.data.framework() in resp.text or ctx.data.application() in resp.text, "report not populated with ECS framework/application data"


@case("UC17-FT003", framework="reporting", capability="evidence_traceability_in_report", component="/audit/package/generate -> package manifest", data="repository evidence")
def ft003(ctx):
    resp = ctx.track(ctx.reporting.generate_audit_package())
    assert_status(resp, 200)
    body = resp.json()
    assert_exists(body.get("package_name"), "package name")
    assert any(k in str(body).lower() for k in ("evidence", "control", "framework")), "package carries no evidence/control references"


@case("UC17-FT004", framework="reporting", capability="reporting_period_applied", component="GET /api/audit/comparison?time_range= / report period filter", data="DataFactory.reporting_period")
def ft004(ctx):
    month = ctx.api.get("/api/audit/comparison", params={"time_range": "Current Month"})
    year = ctx.api.get("/api/audit/comparison", params={"time_range": "Last 12 Months"})
    assert month.status < 500 and year.status < 500
    assert month.content != year.content, "changing the reporting period did not change the report data"


@case("UC17-FT005", framework="reporting", capability="incomplete_reporting_data", component="download with scope that has no evidence", data="unknown application")
def ft005(ctx):
    resp = ctx.track(ctx.reporting.download(_report_id(ctx), "csv", application="zz-no-such-application"))
    assert resp.status < 500 and "Traceback" not in resp.text, "incomplete data must produce a controlled report/error"


@case("UC17-FT006", framework="reporting", capability="deterministic_reproduction", component="GET /mvp/reports/download/{id} x2", data="first catalogue report")
def ft006(ctx):
    assert ctx.reporting.deterministic(_report_id(ctx), "csv"), "two downloads of the same report differ"


@case("UC17-FT007", framework="reporting", capability="export_report", component="GET /mvp/reports/download/{id}?format=pdf|csv|excel", data="formats")
def ft007(ctx):
    rid = _report_id(ctx)
    ok = 0
    for fmt in ("pdf", "csv", "excel"):
        r = ctx.reporting.download(rid, fmt)
        assert r.status < 500, f"{fmt}: {r.status}"
        ok += int(r.status == 200 and len(r.content) > 0)
    assert ok >= 1, "no export format produced a file"


@case("UC17-FT008", framework="audit", capability="audit_report_generation", component="audit_log for report download", data="request_id")
def ft008(ctx):
    resp = ctx.track(ctx.reporting.download(_report_id(ctx), "csv"))
    if not ctx.db.enabled:
        raise CapabilityBlocked("report generation audit rows are only verifiable in audit_log", requires="PostgreSQL access")
    ctx.audit.verify(request_id=resp.request_id)


register_crosscutting(PROFILE)
