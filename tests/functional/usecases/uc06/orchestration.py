"""UC06 - Evidence completeness detection.

NOTE (workbook): FT001-FT008 of this sheet describe predefined-query behaviour (not completeness); automated as written. See docs/functional-test-framework.md (workbook alignment).
"""

from __future__ import annotations

from ...framework import scenarios as sc
from ...framework.assertions import (assert_audit_record, assert_equal, assert_exists, assert_record_count, assert_status, assert_success)
from ...framework.crosscutting import register_crosscutting
from ...framework.errors import CapabilityBlocked
from ...framework.spec import UseCaseProfile, case

PROFILE = UseCaseProfile(uc="UC06", subject="evidence completeness detection", page="/mvp/completeness", api="/api/evidence/completeness",
                         dashboard_api="/api/evidence-reuse/readiness", rbac_capability="upload_evidence", audit_action="upload")

_QUERY_PAGE = "/mvp/predefined-queries"


def _first_control_id(ctx) -> str:
    """A real predefined-query control id taken from the ECS catalogue page (links to /api/predefined-queries/{control_id})."""
    import re

    html = ctx.api.get(_QUERY_PAGE).text
    m = re.search(r"/api/predefined-queries/([A-Za-z0-9_.\-]+)", html)
    if not m:
        raise CapabilityBlocked("no predefined query control id discoverable from the catalogue page", requires="predefined query catalogue")
    return m.group(1)


@case("UC06-FT001", framework="search", capability="run_predefined_query", component="GET /api/predefined-queries/{control_id}", data="first catalogue control")
def ft001(ctx):
    cid = _first_control_id(ctx)
    resp = ctx.track(ctx.api.get(f"/api/predefined-queries/{cid}"))
    assert_success(resp)
    assert_exists(resp.json())


@case("UC06-FT002", framework="search", capability="query_parameter_validation", component="GET /api/predefined-queries/{control_id} (missing/invalid)",
      data="invalid control id")
def ft002(ctx):
    resp = ctx.track(ctx.api.get("/api/predefined-queries/%20"))
    assert resp.status < 500 and "Traceback" not in resp.text, f"unhandled error {resp.status}"
    resp2 = ctx.track(ctx.api.get("/api/predefined-queries/NOT-A-REAL-CONTROL-ZZ"))
    assert resp2.status < 500 and "Traceback" not in resp2.text
    if resp2.status == 200 and resp2.is_json:
        assert not _has_rows(resp2.json()), "misleading result set returned for an unknown control"


def _has_rows(body) -> bool:
    if isinstance(body, dict):
        return any(_has_rows(v) for k, v in body.items() if k in ("rows", "results", "queries", "items", "data")) or \
            any(isinstance(v, list) and v for k, v in body.items() if k in ("rows", "results", "queries", "items"))
    return bool(body) if isinstance(body, list) else False


@case("UC06-FT003", framework="reporting", capability="deterministic_query_results", component="GET /api/predefined-queries/{control_id} x2",
      data="first catalogue control")
def ft003(ctx):
    cid = _first_control_id(ctx)
    a = ctx.api.get(f"/api/predefined-queries/{cid}")
    b = ctx.api.get(f"/api/predefined-queries/{cid}")
    assert_equal(a.content, b.content, "repeating the same predefined query changed the result")


@case("UC06-FT004", framework="compliance", capability="application_framework_scope", component="GET /api/evidence/completeness?framework=&application=",
      data="catalog.default_framework / default_application")
def ft004(ctx):
    all_scope = ctx.dashboard.completeness()
    scoped = ctx.dashboard.completeness(framework=ctx.data.framework(), application=ctx.data.application())
    assert_exists(all_scope)
    assert_exists(scoped)
    assert ctx.data.framework().lower() in str(scoped).lower() or ctx.data.application().lower() in str(scoped).lower(), \
        "scoped completeness response does not reflect the requested scope"


@case("UC06-FT005", framework="search", capability="open_evidence_from_results", component="GET /api/evidence/search -> GET /evidence/{id}",
      data="uploaded evidence")
def ft005(ctx):
    f, _, row = sc.upload_and_locate(ctx)
    hits = ctx.evidence.search(q=f.name.rsplit(".", 1)[0])
    target = (hits or [row])[0]
    eid = target.get("evidence_id") or row["evidence_id"]
    assert_status(ctx.evidence.get(eid), 200)


@case("UC06-FT006", framework="api", capability="no_result_behavior", component="GET /api/evidence/search?q=<no match>", data="improbable token")
def ft006(ctx):
    token = "zzzz-no-such-evidence-" + ctx.data.unique("nr")
    resp = ctx.track(ctx.api.get("/api/evidence/search", params={"q": token}))
    assert_success(resp)
    assert_record_count(ctx.evidence.search(q=token), expected=0, msg="no-match search must return an empty result, not an error or filler")


@case("UC06-FT007", framework="search", capability="protect_query_definition", component="mutating verbs on /api/predefined-queries/{control_id}",
      data="PUT/DELETE probes")
def ft007(ctx):
    ctx.security.require_enabled()
    cid = _first_control_id(ctx)
    for verb in ("PUT", "PATCH", "DELETE"):
        resp = ctx.track(ctx.api.request(verb, f"/api/predefined-queries/{cid}", json={"query": "DROP"}))
        assert resp.status in (404, 405, 401, 403), f"{verb} on a predefined query returned {resp.status}"
    assert_status(ctx.api.get(f"/api/predefined-queries/{cid}"), 200)


@case("UC06-FT008", framework="audit", capability="audit_query_execution", component="audit trail after predefined query run", data="first catalogue control")
def ft008(ctx):
    cid = _first_control_id(ctx)
    resp = ctx.track(ctx.api.get(f"/api/predefined-queries/{cid}"))
    if not ctx.db.enabled:
        raise CapabilityBlocked("query-execution audit rows are only verifiable in audit_log (database access required)", requires="PostgreSQL access")
    ctx.audit.verify(request_id=resp.request_id)


register_crosscutting(PROFILE)
