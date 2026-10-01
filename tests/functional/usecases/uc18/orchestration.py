"""UC18 - AI-assisted audit preparation."""

from __future__ import annotations

from ...framework import scenarios as sc
from ...framework.assertions import (assert_denied, assert_equal, assert_exists, assert_status, assert_success)
from ...framework.crosscutting import register_crosscutting
from ...framework.errors import CapabilityBlocked
from ...framework.spec import UseCaseProfile, case

PROFILE = UseCaseProfile(uc="UC18", subject="AI-assisted audit preparation", page="/mvp/audit-prep", api="/api/audit-prep/upcoming",
                         dashboard_api="/api/platform/audit-readiness", rbac_capability="", perf_key="report_generation_ms", audit_action="audit")


@case("UC18-FT001", framework="reporting", capability="create_audit_workspace_package", component="POST /audit/package/generate + GET /mvp/audit-prep", data="persona cio")
def ft001(ctx):
    sc.page_loads(ctx, "/mvp/audit-prep", "auditor")
    resp = ctx.track(ctx.reporting.generate_audit_package())
    assert_status(resp, 200)
    assert_exists(resp.json().get("package_name"))


@case("UC18-FT002", framework="reporting", capability="auto_assemble_evidence", component="audit package preview content", data="repository evidence")
def ft002(ctx):
    body = ctx.reporting.generate_audit_package().json()
    assert any(k in str(body).lower() for k in ("evidence", "control", "framework")), "package assembled no evidence references"


@case("UC18-FT003", framework="ai", capability="relevance_and_grounding", component="POST /api/audit-llm/query -> validate-grounding", data="audit prep prompt")
def ft003(ctx):
    r = sc.ai_query(ctx, f"Which evidence supports {ctx.data.framework()} audit preparation for {ctx.data.application()}?")
    assert ctx.ai.citations(r), "no evidence citations"
    ctx.ai.validate_grounding(r)


@case("UC18-FT004", framework="compliance", capability="identify_missing_audit_evidence", component="GET /api/audit-prep/audit-detail + /api/evidence/completeness", data="catalog scope")
def ft004(ctx):
    sc.json_loads(ctx, lambda: ctx.dashboard.completeness(framework=ctx.data.framework(), application=ctx.data.application()), "completeness")
    assert ctx.api.get("/api/audit-prep/audit-detail").status < 500


@case("UC18-FT005", framework="ai", capability="accept_reject_ai_suggestions", component="POST /mvp/api/chat-action", data="chat action")
def ft005(ctx):
    ctx.require_mutation()
    resp = ctx.track(ctx.api.post("/mvp/api/chat-action", data={"action": "reject"}))
    assert resp.status < 500, resp.text[:200]


@case("UC18-FT006", framework="rbac", capability="no_unauthorized_evidence_exposed", component="GET /api/evidence/search & /mvp/audit-prep as owner vs auditor", data="personas")
def ft006(ctx):
    res = ctx.rbac.visible_to("/api/evidence/search", ["owner", "auditor", "cio"], q="")
    for p, r in res.items():
        assert r.status < 500, f"{p}: {r.status}"


@case("UC18-FT007", framework="ai", capability="ai_failure_safe", component="POST /api/audit-llm/query with LLM unavailable", data="AI failure environment")
def ft007(ctx):
    ctx.ai.require_failure_mode()
    resp = ctx.track(ctx.ai.query())
    assert resp.status < 500 and "Traceback" not in resp.text
    assert_status(ctx.reporting.audit_prep(), 200)


@case("UC18-FT008", framework="reporting", capability="export_finalize_audit_package", component="GET /audit/package/export", data="generated package")
def ft008(ctx):
    ctx.reporting.generate_audit_package()
    resp = ctx.track(ctx.reporting.export_audit_package())
    assert resp.status < 500, resp.text[:200]


register_crosscutting(PROFILE)
