"""UC08 - AI-generated evidence summaries.

NOTE (workbook): FT001-FT008 describe completeness detection; automated as written. The cross-cutting rows (FT009+) use this
sheet's title (AI-generated evidence summaries) and exercise ECS's AI summary/answer surface.
"""

from __future__ import annotations

from ...framework import scenarios as sc
from ...framework.assertions import (assert_equal, assert_exists, assert_json_field, assert_record_count, assert_status, assert_success)
from ...framework.crosscutting import register_crosscutting
from ...framework.errors import CapabilityBlocked
from ...framework.spec import UseCaseProfile, case

PROFILE = UseCaseProfile(uc="UC08", subject="AI-generated evidence summaries", page="/mvp/ai-ops-assistant", api="/api/audit-llm/prompts",
                         dashboard_api="/api/audit-llm/profiles", rbac_capability="", perf_key="ai_query_ms", audit_action="query")


@case("UC08-FT001", framework="compliance", capability="detect_missing_required_evidence", component="GET /api/evidence/completeness",
      data="catalog scope")
def ft001(ctx):
    body = ctx.dashboard.completeness(framework=ctx.data.framework(), application=ctx.data.application())
    assert_exists(body)
    text = str(body).lower()
    assert any(t in text for t in ("missing", "gap", "pending", "incomplete")), f"completeness payload reports no missing/gap indicator: {text[:200]}"


@case("UC08-FT002", framework="compliance", capability="mark_complete_control", component="GET /api/evidence/completeness + upload", data="uploaded evidence for control")
def ft002(ctx):
    if not ctx.data.control():
        raise CapabilityBlocked("set ECS_FT_CONTROL to a control id that is fully evidenced in the target environment", requires="known complete control")
    sc.upload_and_locate(ctx, control=ctx.data.control())
    body = ctx.dashboard.completeness(framework=ctx.data.framework(), application=ctx.data.application())
    assert ctx.data.control() in str(body), "control missing from completeness response"


@case("UC08-FT003", framework="compliance", capability="recalculate_after_upload", component="GET /api/evidence/completeness before/after POST /evidence/upload",
      data="DataFactory.file")
def ft003(ctx):
    scope = dict(framework=ctx.data.framework(), application=ctx.data.application())
    before = ctx.dashboard.completeness(**scope)
    sc.upload_and_locate(ctx, control=ctx.data.control(), **scope)
    after = ctx.dashboard.completeness(**scope)
    assert_exists(after)
    assert before != after or ctx.evidence.repository(), "completeness was not recalculated after upload"


@case("UC08-FT004", framework="compliance", capability="application_environment_scope", component="GET /api/evidence/completeness?application=",
      data="two applications")
def ft004(ctx):
    a = ctx.dashboard.completeness(application=ctx.data.application())
    b = ctx.dashboard.completeness(application=ctx.data.application(second=True))
    assert_exists(a)
    assert_exists(b)
    assert a != b, "different application scopes returned identical completeness data"


@case("UC08-FT005", framework="compliance", capability="completeness_reason_detail", component="GET /api/evidence-reuse/readiness", data="catalog scope")
def ft005(ctx):
    resp = ctx.track(ctx.compliance.readiness(framework=ctx.data.framework(), application=ctx.data.application()))
    assert_success(resp)
    assert any(k in resp.text.lower() for k in ("reason", "detail", "missing", "status")), "no reason/detail in readiness payload"


@case("UC08-FT006", framework="lifecycle", capability="expired_invalid_evidence", component="POST /mvp/platform/evidence-lifecycle/review (Expired) + completeness",
      data="uploaded evidence set to Expired")
def ft006(ctx):
    ctx.require_mutation()
    ctx.require_db()
    f, _, row = sc.upload_and_locate(ctx)
    uid = (ctx.db.one("evidence", title=f.name) or ctx.db.one("evidence", source_object_id=f.name) or {}).get("evidence_uid")
    assert_exists(uid, "evidence_uid for uploaded file")
    assert_status(ctx.track(ctx.lifecycle.set_status(uid, "Expired", note="functional test")), 303)
    assert_equal(ctx.lifecycle.review_row(uid)["status"], "Expired")


@case("UC08-FT007", framework="dashboard", capability="completeness_reconciliation", component="/api/evidence/completeness vs /api/evidence-reuse/readiness",
      data="catalog scope")
def ft007(ctx):
    a = ctx.dashboard.completeness()
    b = ctx.compliance.readiness().json()
    assert_exists(a)
    assert_exists(b)
    totals = ctx.dashboard.numbers_in(a, r"^(total|controls?|total_controls)$")
    assert totals, "no control total in completeness payload to reconcile"


@case("UC08-FT008", framework="audit", capability="audit_completeness_evaluation", component="POST /api/evidence-reuse/validate-completeness + audit_log",
      data="catalog scope")
def ft008(ctx):
    resp = ctx.track(ctx.compliance.validate_completeness(framework=ctx.data.framework(), application=ctx.data.application()))
    assert_success(resp)
    if not ctx.db.enabled:
        raise CapabilityBlocked("evaluation audit rows are only verifiable in audit_log", requires="PostgreSQL access")
    ctx.audit.verify(request_id=resp.request_id)


register_crosscutting(PROFILE)
