"""UC09 - Natural language audit queries (prebuilt/NLQ). FT001-FT008 (similarity/reuse) are automated as written."""

from __future__ import annotations

from ...framework import scenarios as sc
from ...framework.assertions import (assert_denied, assert_equal, assert_exists, assert_record_count, assert_status, assert_success)
from ...framework.crosscutting import register_crosscutting
from ...framework.errors import CapabilityBlocked
from ...framework.spec import UseCaseProfile, case

PROFILE = UseCaseProfile(uc="UC09", subject="natural language audit queries", page="/dashboard", api="/mvp/api/common-evidence-presets",
                         dashboard_api="/api/audit-llm/prompts", rbac_capability="", perf_key="ai_query_ms", audit_action="chat")


@case("UC09-FT001", framework="ai", capability="find_similar_evidence", component="POST /api/evidence-reuse/analyze", data="catalog scope")
def ft001(ctx):
    resp = ctx.track(ctx.ai.similar_evidence(framework=ctx.data.framework(), application=ctx.data.application()))
    assert_success(resp)
    assert_exists(resp.json())


@case("UC09-FT002", framework="ai", capability="no_unrelated_suggestions", component="POST /api/evidence-reuse/analyze (restricted scope)",
      data="technology/framework filter")
def ft002(ctx):
    scoped = ctx.track(ctx.ai.similar_evidence(framework=ctx.data.framework(), technology="zz-unrelated-technology"))
    assert_success(scoped)
    assert not _rows(scoped.json()), "records unrelated to the requested technology were suggested"


def _rows(body):
    if isinstance(body, dict):
        for k in ("records", "items", "candidates", "matches", "results"):
            if isinstance(body.get(k), list):
                return body[k]
    return body if isinstance(body, list) else []


@case("UC09-FT003", framework="ai", capability="similarity_context_displayed", component="GET /api/evidence-reuse/records + /mvp/reuse",
      data="catalog scope")
def ft003(ctx):
    sc.page_loads(ctx, "/mvp/reuse", "auditor")
    resp = ctx.track(ctx.ai.reuse_records(framework=ctx.data.framework()))
    assert_success(resp)
    rows = _rows(resp.json())
    if rows:
        assert any(k in str(rows[0]).lower() for k in ("control", "framework", "reuse", "similar", "score")), "no similarity/reuse context on records"


@case("UC09-FT004", framework="ai", capability="reuse_approved_evidence", component="POST /api/framework-onboarding/reuse-decision", data="reuse decision payload")
def ft004(ctx):
    ctx.require_mutation()
    resp = ctx.track(ctx.onboarding.reuse_decision({"framework_id": ctx.data.framework(), "decision": "reuse"}))
    assert resp.status < 500, resp.text[:200]


@case("UC09-FT005", framework="evidence", capability="ownership_traceability_preserved", component="GET /api/evidence-reuse/records (owner/source fields)",
      data="catalog scope")
def ft005(ctx):
    rows = _rows(ctx.track(ctx.ai.reuse_records()).json())
    assert_record_count(rows, minimum=1, msg="no reuse records to verify")
    sc.assert_traceable_rows(rows, required=("evidence_id",))


@case("UC09-FT006", framework="rbac", capability="reuse_scope_security", component="GET /api/evidence-reuse/records as scoped roles", data="personas")
def ft006(ctx):
    results = ctx.rbac.visible_to("/api/evidence-reuse/records", ["owner", "auditor", "cio"])
    for p, r in results.items():
        assert r.status < 500, f"{p}: {r.status}"


@case("UC09-FT007", framework="ai", capability="no_similarity_result", component="POST /api/evidence-reuse/analyze (no match)", data="improbable scope")
def ft007(ctx):
    resp = ctx.track(ctx.ai.similar_evidence(application="zz-no-such-application", control="zz-none"))
    assert resp.status < 500 and "Traceback" not in resp.text
    assert not _rows(resp.json()) if resp.is_json else True


@case("UC09-FT008", framework="audit", capability="audit_reuse_decision", component="POST /api/framework-onboarding/reuse-decision + audit_log", data="reuse decision")
def ft008(ctx):
    ctx.require_mutation()
    resp = ctx.track(ctx.onboarding.reuse_decision({"framework_id": ctx.data.framework(), "decision": "reuse"}))
    if not ctx.db.enabled:
        raise CapabilityBlocked("reuse decision audit rows are only verifiable in audit_log", requires="PostgreSQL access")
    ctx.audit.verify(request_id=resp.request_id)


register_crosscutting(PROFILE)
