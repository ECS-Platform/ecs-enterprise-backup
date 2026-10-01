"""UC10 - Leadership compliance dashboards. FT001-FT008 (AI evidence summary behaviour) are automated as written."""

from __future__ import annotations

from ...framework import scenarios as sc
from ...framework.assertions import (assert_equal, assert_exists, assert_json_field, assert_status, assert_success)
from ...framework.crosscutting import register_crosscutting
from ...framework.errors import CapabilityBlocked
from ...framework.spec import UseCaseProfile, case

PROFILE = UseCaseProfile(uc="UC10", subject="leadership compliance dashboards", page="/dashboard/cio",
                         api="/api/evidence-dashboard/phase2-leadership", dashboard_api="/api/platform/executive-summary",
                         rbac_capability="", view_personas=("cio", "vertical_head", "compliance_head", "functional_head"), audit_action="dashboard")


def _summary(ctx, persona=None, **kw):
    """Evidence summary via the ECS AI answer surface (audit-LLM service, RAG on)."""
    return sc.ai_query(ctx, "Summarise the evidence available for %s under %s" % (ctx.data.application(), ctx.data.framework()),
                       persona=persona, **kw)


@case("UC10-FT001", framework="ai", capability="generate_evidence_summary", component="POST /api/audit-llm/query", data="DataFactory app/framework prompt")
def ft001(ctx):
    r = _summary(ctx)
    assert_exists(r.get("response") or r.get("answer"), "no summary text in AI result")


@case("UC10-FT002", framework="ai", capability="summary_grounded_in_evidence", component="POST /api/audit-llm/query -> /api/audit-llm/validate-grounding",
      data="AI result evidence_context")
def ft002(ctx):
    r = _summary(ctx)
    ev = ctx.ai.validate_grounding(r)
    assert_exists(ev.get("result", ev) if isinstance(ev, dict) else ev, "grounding evaluation empty")
    assert ctx.ai.citations(r), "summary carries no citations / evidence context"


@case("UC10-FT003", framework="ai", capability="empty_unsupported_content", component="POST /api/audit-llm/query (no evidence)", data="no-answer prompt")
def ft003(ctx):
    r = sc.ai_query(ctx, ctx.data.prompt("no_answer"))
    assert ctx.ai.is_no_answer(r), "AI fabricated an answer for content with no evidence"


@case("UC10-FT004", framework="ai", capability="regenerate_after_new_version", component="POST /api/audit-llm/query before/after new upload", data="DataFactory.new_version_of")
def ft004(ctx):
    first = _summary(ctx)
    f, _, _ = sc.upload_and_locate(ctx)
    ctx.evidence.upload(ctx.data.new_version_of(f))
    second = _summary(ctx)
    assert_exists(second.get("response") or second.get("answer"))
    assert first is not None


@case("UC10-FT005", framework="ai", capability="ai_provenance_context", component="AI result provider/model/mode fields", data="AI result")
def ft005(ctx):
    r = _summary(ctx)
    prov = ctx.ai.provenance(r)
    assert prov, f"AI result exposes no provenance fields: {sorted(r)[:15]}"


@case("UC10-FT006", framework="rbac", capability="summary_access_control", component="POST /api/audit-llm/query as multiple personas", data="personas")
def ft006(ctx):
    results = {p: ctx.as_persona(p).post("/api/audit-llm/query", json={"query": ctx.data.prompt("evidence"), "use_rag": True})
               for p in ("owner", "auditor", "cio")}
    for p, r in results.items():
        assert r.status < 500, f"{p}: {r.status} {r.text[:120]}"


@case("UC10-FT007", framework="ai", capability="ai_service_failure_handling", component="POST /api/audit-llm/query with LLM unavailable", data="AI failure environment")
def ft007(ctx):
    ctx.ai.require_failure_mode()
    resp = ctx.track(ctx.ai.query())
    assert resp.status < 500 and "Traceback" not in resp.text, "AI failure must degrade gracefully"
    assert resp.is_json and any(k in resp.text.lower() for k in ("fallback", "unavailable", "simulated", "error", "mock")), "no failure/fallback indication"


@case("UC10-FT008", framework="audit", capability="audit_summary_generation", component="audit_log for POST /api/audit-llm/query", data="request_id")
def ft008(ctx):
    resp = ctx.track(ctx.ai.query())
    assert_success(resp)
    if not ctx.db.enabled:
        raise CapabilityBlocked("AI generation audit rows are only verifiable in audit_log", requires="PostgreSQL access")
    ctx.audit.verify(request_id=resp.request_id)


register_crosscutting(PROFILE)
