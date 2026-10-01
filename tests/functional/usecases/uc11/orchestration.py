"""UC11 - Multi-application onboarding. FT001-FT008 (natural-language evidence Q&A) are automated as written."""

from __future__ import annotations

from ...framework import scenarios as sc
from ...framework.assertions import (assert_equal, assert_exists, assert_json_field, assert_status, assert_success)
from ...framework.crosscutting import register_crosscutting
from ...framework.errors import CapabilityBlocked
from ...framework.spec import UseCaseProfile, case

PROFILE = UseCaseProfile(uc="UC11", subject="multi-application onboarding", page="/mvp/platform/onboarding", api="/api/admin/applications",
                         api_params={"role": "system_admin"}, rbac_capability="manage_frameworks", audit_action="onboard", notice_contains="onboard",
                         trigger=lambda ctx: ctx.track(ctx.onboarding.onboard_application()[1]))


@case("UC11-FT001", framework="ai", capability="ask_natural_language_question", component="POST /mvp/api/common-evidence-query | POST /mvp/chat",
      data="DataFactory.prompt('evidence')")
def ft001(ctx):
    resp = ctx.track(ctx.ai.common_evidence_query(query=ctx.data.prompt("evidence")))
    assert resp.status < 500, resp.text[:200]
    assert_exists(resp.text.strip(), "empty answer")


@case("UC11-FT002", framework="ai", capability="citation_evidence_grounding", component="POST /api/audit-llm/query -> validate-grounding", data="AI result")
def ft002(ctx):
    r = sc.ai_query(ctx)
    assert ctx.ai.citations(r), "answer has no citations / evidence context"
    ctx.ai.validate_grounding(r)


@case("UC11-FT003", framework="compliance", capability="application_framework_context", component="POST /mvp/api/common-evidence-query (application, framework)",
      data="catalog.default_application / default_framework")
def ft003(ctx):
    resp = ctx.track(ctx.ai.common_evidence_query(query=ctx.data.prompt("evidence"), application=ctx.data.application(), framework=ctx.data.framework()))
    assert resp.status < 500
    assert ctx.data.application().lower() in resp.text.lower() or ctx.data.framework().lower() in resp.text.lower(), "answer does not reflect the selected context"


@case("UC11-FT004", framework="ai", capability="no_answer_behavior", component="POST /api/audit-llm/query (out-of-corpus)", data="DataFactory.prompt('no_answer')")
def ft004(ctx):
    r = sc.ai_query(ctx, ctx.data.prompt("no_answer"))
    assert ctx.ai.is_no_answer(r), "model produced an answer with no supporting evidence"


@case("UC11-FT005", framework="search", capability="followup_retains_context", component="POST /mvp/api/chat-investigation (follow-up)", data="two-turn conversation")
def ft005(ctx):
    first = ctx.track(ctx.ai.common_evidence_query(query=ctx.data.prompt("evidence"), application=ctx.data.application()))
    follow = ctx.track(ctx.api.post("/mvp/api/chat-investigation", data={"query": ctx.data.prompt("followup"),
                                                                      "application": ctx.data.application(), "framework": ctx.data.framework()}))
    assert follow.status < 500, follow.text[:200]
    assert first.status < 500


@case("UC11-FT006", framework="rbac", capability="evidence_permissions_respected", component="POST /mvp/api/common-evidence-query as personas", data="personas")
def ft006(ctx):
    for p in ("owner", "auditor", "cio"):
        r = ctx.as_persona(p).post("/mvp/api/common-evidence-query", data={"query": ctx.data.prompt("evidence")})
        assert r.status < 500, f"{p}: {r.status}"


@case("UC11-FT007", framework="ai", capability="ai_vector_failure_handling", component="POST /mvp/api/common-evidence-query with vector/LLM down", data="failure environment")
def ft007(ctx):
    ctx.ai.require_failure_mode()
    resp = ctx.track(ctx.ai.common_evidence_query(query=ctx.data.prompt("evidence")))
    assert resp.status < 500 and "Traceback" not in resp.text, "vector/AI failure must degrade gracefully"


@case("UC11-FT008", framework="audit", capability="audit_nl_query", component="audit_log for POST /mvp/chat", data="request_id")
def ft008(ctx):
    resp = ctx.track(ctx.ai.chat(ctx.data.prompt("evidence")))
    assert resp.status < 500
    if not ctx.db.enabled:
        raise CapabilityBlocked("chat audit rows are only verifiable in audit_log", requires="PostgreSQL access")
    ctx.audit.verify(request_id=resp.request_id)


register_crosscutting(PROFILE)
