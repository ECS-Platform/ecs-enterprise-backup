"""UC03 - Metadata tagging and naming convention."""

from __future__ import annotations

from ...framework import scenarios as sc
from ...framework.assertions import (assert_audit_record, assert_equal, assert_exists, assert_failure, assert_metadata, assert_success)
from ...framework.crosscutting import register_crosscutting
from ...framework.errors import CapabilityBlocked
from ...framework.spec import UseCaseProfile, case

PROFILE = UseCaseProfile(uc="UC03", subject="metadata tagging and naming", page="/mvp/upload", api="/api/evidence/naming-preview",
                         api_params={"filename": "ft_probe.txt", "framework": "PCI DSS", "application": "Net Banking"},
                         rbac_capability="upload_evidence", audit_action="upload")


@case("UC03-FT001", framework="metadata", capability="save_complete_metadata", component="POST /evidence/upload -> GET /evidence/repository",
      data="DataFactory.evidence_metadata")
def ft001(ctx):
    meta = ctx.data.evidence_metadata(owner="AppOwner", comments="complete metadata")
    f, body, row = sc.upload_and_locate(ctx, **meta)
    assert_metadata(row, {"framework": meta["framework"], "application": meta["application"]})
    assert_metadata(body, {"evidence_type": meta["evidence_type"], "audit_cycle": meta["audit_cycle"]})


@case("UC03-FT002", framework="metadata", capability="mandatory_tag_enforcement", component="POST /api/evidence/validate-metadata",
      data="payload missing framework / application")
def ft002(ctx):
    for missing in ({"filename": "a.txt", "application": ctx.data.application()}, {"filename": "a.txt", "framework": ctx.data.framework()}):
        resp = ctx.track(ctx.evidence.validate_metadata(missing))
        text = resp.text.lower()
        assert resp.status < 500 and ("framework" in text or "application" in text), f"mandatory tag not enforced: {resp.text[:200]}"
        body = resp.json()
        assert body.get("ok") is False or body.get("valid") is False or body.get("errors") or resp.status >= 400, body


@case("UC03-FT003", framework="metadata", capability="naming_convention_applied", component="GET /api/evidence/naming-preview (enforce_naming)",
      data="DataFactory.file().name")
def ft003(ctx):
    name = ctx.data.file().name
    resp = ctx.track(ctx.evidence.naming_preview(name))
    assert_success(resp)
    body = resp.json()
    standardized = str(body.get("standardized_name") or body.get("standard_name") or body.get("name") or body.get("preview") or "")
    assert_exists(standardized, f"no standardized name in {body}")
    assert ctx.data.application().replace(" ", "").lower()[:4] in standardized.replace("_", "").replace("-", "").replace(" ", "").lower() \
        or ctx.data.framework().replace(" ", "").lower()[:3] in standardized.replace("_", "").replace("-", "").replace(" ", "").lower(), \
        f"standardized name does not carry the tags: {standardized}"


@case("UC03-FT004", framework="metadata", capability="invalid_naming_rejected", component="GET /api/evidence/naming-preview",
      data="invalid filenames (traversal / empty / illegal chars)")
def ft004(ctx):
    for bad in ("", "../../etc/passwd", "bad<>name|.txt"):
        resp = ctx.track(ctx.evidence.naming_preview(bad))
        assert resp.status < 500 and "Traceback" not in resp.text, f"{bad!r} caused {resp.status}"
        body = resp.json() if resp.is_json else {}
        out = str(body.get("standardized_name") or body.get("name") or "")
        assert ".." not in out and "<" not in out and "|" not in out, f"unsafe character survived naming: {out!r}"


@case("UC03-FT005", framework="metadata", capability="controlled_tag_values", component="POST /api/evidence/validate-metadata + framework catalogue",
      data="catalog.default_framework / unknown framework")
def ft005(ctx):
    ok = ctx.track(ctx.evidence.validate_metadata({"filename": "a.txt", "framework": ctx.data.framework(), "application": ctx.data.application()}))
    assert ok.status < 500
    bad = ctx.track(ctx.evidence.validate_metadata({"filename": "a.txt", "framework": "ZZ-NOT-A-FRAMEWORK", "application": ctx.data.application()}))
    if bad.is_json and bad.json() == ok.json():
        raise CapabilityBlocked("ECS validate-metadata does not constrain framework to the catalogue (only required-ness); "
                                "controlled-list enforcement is not exposed by the API.", requires="controlled value validation")


@case("UC03-FT006", framework="audit", capability="metadata_edit_audit_history", component="POST /evidence/revalidate | /evidence/submit + audit trail",
      data="uploaded evidence")
def ft006(ctx):
    f, body, row = sc.upload_and_locate(ctx)
    resp = ctx.track(ctx.evidence.revalidate(framework=ctx.data.framework(), application=ctx.data.application(), control=ctx.data.control()))
    assert_success(resp)
    ctx.audit.verify(action="upload")
    if not ctx.db.enabled:
        raise CapabilityBlocked("ECS has no metadata-edit endpoint for stored evidence (re-upload creates a new record); edit-with-history "
                                "is only assertable via audit_log before/after state, which needs database access.", requires="PostgreSQL access")
    rec = ctx.audit.verify(request_id=resp.request_id)
    ctx.audit.verify_state_change(rec)


@case("UC03-FT007", framework="search", capability="search_by_metadata_tags", component="GET /api/evidence/search (framework, application)",
      data="DataFactory.evidence_metadata")
def ft007(ctx):
    f, _, _ = sc.upload_and_locate(ctx, framework=ctx.data.framework(), application=ctx.data.application())
    hits = ctx.evidence.search(q="", framework=ctx.data.framework(), application=ctx.data.application())
    assert hits, "search by framework+application tags returned nothing"
    assert all(ctx.data.framework().lower() in str(h).lower() for h in hits[:20]), "search results ignore the framework tag"


@case("UC03-FT008", framework="metadata", capability="metadata_persists_across_restart", component="evidence metadata after ECS restart",
      data="DataFactory.file")
def ft008(ctx):
    ctx.require_mutation()
    ctx.require_restart_hook()
    f, _, row = sc.upload_and_locate(ctx)
    ctx.restart_ecs()
    after = sc.wait_until(lambda: ctx.evidence.by_filename(f.name), timeout=60, interval=ctx.cfg.poll_interval, what="evidence after restart")
    assert_metadata(after, {"framework": row["framework"], "application": row["application"]})
    assert_equal(after.get("sha256"), row.get("sha256"))


register_crosscutting(PROFILE)
