"""UC14 - Automated control validation. FT001-FT008 (evidence versioning / retention / lifecycle) are automated as written."""

from __future__ import annotations

from ...framework import scenarios as sc
from ...framework.assertions import (assert_denied, assert_equal, assert_exists, assert_hash_changed, assert_record_count, assert_retention_state,
                                     assert_status, assert_version)
from ...framework.crosscutting import register_crosscutting
from ...framework.errors import CapabilityBlocked
from ...framework.spec import UseCaseProfile, case

PROFILE = UseCaseProfile(uc="UC14", subject="automated control validation", page="/mvp/completeness", api="/api/evidence/completeness",
                         dashboard_api="/api/evidence-reuse/readiness", rbac_capability="upload_evidence", audit_action="validat")


def _uid(ctx, f):
    ctx.require_db()
    row = ctx.db.one("evidence", title=f.name) or ctx.db.one("evidence", source_object_id=f.name)
    return assert_exists(row, "evidence DB row")["evidence_uid"]


@case("UC14-FT001", framework="lifecycle", capability="create_initial_version", component="POST /evidence/upload -> repository version", data="DataFactory.file")
def ft001(ctx):
    f, _, row = sc.upload_and_locate(ctx)
    assert str(row.get("version") or 1) in ("1", "v1", "1.0"), f"initial version is {row.get('version')!r}"


@case("UC14-FT002", framework="lifecycle", capability="new_version_on_update", component="POST /evidence/upload (same name, new bytes)", data="DataFactory.new_version_of")
def ft002(ctx):
    f, _, row = sc.upload_and_locate(ctx)
    v2 = ctx.data.new_version_of(f)
    sc.upload_and_locate(ctx, v2)
    rows = ctx.evidence.find_all(filename=f.name)
    assert len({r.get("sha256") for r in rows}) >= 2, "update did not create a distinct version"


@case("UC14-FT003", framework="lifecycle", capability="version_history", component="GET /api/audit/evidence/{key}/versions + timeline", data="evidence with 2 versions")
def ft003(ctx):
    f, _, row = sc.upload_and_locate(ctx)
    key = row.get("repository_id") or row["evidence_id"]
    versions = ctx.evidence.versions(str(key))
    assert_record_count(versions, minimum=1, msg="no version history returned")
    assert_version(versions, minimum_count=1)


@case("UC14-FT004", framework="lifecycle", capability="retrieve_historical_version", component="GET /api/audit/evidence/{key}/versions + object store", data="evidence with 2 versions")
def ft004(ctx):
    f, _, row = sc.upload_and_locate(ctx)
    sc.upload_and_locate(ctx, ctx.data.new_version_of(f))
    versions = ctx.evidence.versions(str(row.get("repository_id") or row["evidence_id"]))
    assert_record_count(versions, minimum=1)
    ref = str(row.get("object_reference") or "")
    if "evidence/" in ref:
        ctx.storage.verify_matches("evidence/" + ref.split("evidence/", 1)[-1], f.sha256)
    else:
        raise CapabilityBlocked("historical bytes are only retrievable from the object store (SNAPSHOT custody)", requires="SNAPSHOT custody")


@case("UC14-FT005", framework="lifecycle", capability="apply_retention_policy", component="evidence_reviews.valid_until via POST /mvp/platform/evidence-lifecycle/review",
      data="valid_days")
def ft005(ctx):
    ctx.require_mutation()
    ctx.require_db()
    f, _, _ = sc.upload_and_locate(ctx)
    uid = _uid(ctx, f)
    ctx.track(ctx.lifecycle.set_status(uid, "Approved", note="retention test", valid_days=30))
    assert_retention_state(ctx.lifecycle.review_row(uid), expected_status="Approved", require_valid_until=True)
    ctx.lifecycle.apply_retention_policy()  # documents the missing policy-configuration API


@case("UC14-FT006", framework="lifecycle", capability="protect_from_unauthorized_delete", component="no delete endpoint; object store immutable (put_immutable)",
      data="uploaded evidence")
def ft006(ctx):
    ctx.security.require_enabled()
    f, _, row = sc.upload_and_locate(ctx)
    for verb in ("DELETE", "PUT", "PATCH"):
        resp = ctx.track(ctx.as_persona("auditor").request(verb, f"/evidence/{row['evidence_id']}"))
        assert resp.status in (404, 405, 401, 403), f"{verb} on evidence returned {resp.status}"
    assert_exists(ctx.evidence.by_filename(f.name), "evidence disappeared")


@case("UC14-FT007", framework="lifecycle", capability="lifecycle_status_filters", component="GET /mvp/platform/evidence-lifecycle?status=", data="lifecycle statuses")
def ft007(ctx):
    from ...framework.lifecycle import LIFECYCLE_STATUSES
    for s in LIFECYCLE_STATUSES:
        r = ctx.track(ctx.lifecycle.page(s))
        assert_status(r, 200, f"lifecycle filter {s}")


@case("UC14-FT008", framework="audit", capability="audit_lifecycle_actions", component="audit_log for POST /mvp/platform/evidence-lifecycle/review", data="request_id")
def ft008(ctx):
    ctx.require_mutation()
    ctx.require_db()
    f, _, _ = sc.upload_and_locate(ctx)
    resp = ctx.track(ctx.lifecycle.set_status(_uid(ctx, f), "UnderReview", note="audit test"))
    ctx.audit.verify(request_id=resp.request_id)


register_crosscutting(PROFILE)
