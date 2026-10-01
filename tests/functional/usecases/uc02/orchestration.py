"""UC02 - Bulk evidence upload."""

from __future__ import annotations

from ...framework import scenarios as sc
from ...framework.assertions import (assert_denied, assert_equal, assert_exists, assert_hash, assert_metadata, assert_record_count,
                                     assert_status, assert_success)
from ...framework.crosscutting import register_crosscutting
from ...framework.spec import UseCaseProfile, case

PROFILE = UseCaseProfile(uc="UC02", subject="bulk evidence upload", page="/mvp/upload", api="/evidence/repository",
                         api_params={"limit": 50}, rbac_capability="upload_evidence", audit_action="upload",
                         notice_contains="Bulk upload complete")


def _bulk(ctx, files, **kw):
    ctx.require_mutation()
    resp = ctx.track(ctx.evidence.bulk_upload(files, **kw))
    return resp


@case("UC02-FT001", framework="evidence", capability="bulk_upload_valid_files", component="POST /mvp/upload/bulk", data="DataFactory.files(3)")
def ft001(ctx):
    files = ctx.data.files(3)
    resp = _bulk(ctx, files, persona="owner")
    ctx.notifier.assert_notified(resp, contains="3 file(s)")
    for f in files:
        assert_exists(ctx.evidence.by_filename(f.name), f"{f.name} missing from repository")


@case("UC02-FT002", framework="metadata", capability="mandatory_metadata_validation", component="POST /api/evidence/validate-metadata",
      data="payload without framework/application")
def ft002(ctx):
    resp = ctx.track(ctx.evidence.validate_metadata({"filename": ctx.data.file().name}))
    assert resp.status < 500
    body = resp.json()
    text = str(body).lower()
    assert ("framework" in text or "application" in text) and ("required" in text or "missing" in text or body.get("ok") is False
                                                              or "errors" in body), f"no clear mandatory-field validation: {body}"


@case("UC02-FT003", framework="evidence", capability="mixed_valid_invalid_batch", component="POST /mvp/upload/bulk + custody allowed_mime_types",
      data="valid + invalid_ext + empty files")
def ft003(ctx):
    good, bad, empty = ctx.data.file(), ctx.data.file("invalid_ext"), ctx.data.file("empty")
    resp = _bulk(ctx, [good, bad, empty], persona="owner")
    assert resp.status < 500, resp.text[:200]
    assert_exists(ctx.evidence.by_filename(good.name), "valid file must be accepted despite invalid siblings")
    ctx.evidence.by_filename(bad.name)  # ECS decides (accept with flag vs reject); recorded in evidence capture for review


@case("UC02-FT004", framework="metadata", capability="per_file_metadata_persisted", component="GET /evidence/repository (framework/application/uploaded_by)",
      data="DataFactory.evidence_metadata")
def ft004(ctx):
    files = ctx.data.files(2)
    _bulk(ctx, files, persona="owner", framework=ctx.data.framework(), application=ctx.data.application())
    for f in files:
        row = sc.wait_until(lambda f=f: ctx.evidence.by_filename(f.name), timeout=60, interval=ctx.cfg.poll_interval, what=f.name)
        assert_metadata(row, {"framework": ctx.data.framework(), "application": ctx.data.application()})
        assert row.get("uploaded_by"), "uploader not recorded"
        assert row.get("uploaded_at"), "upload timestamp not recorded"


@case("UC02-FT005", framework="evidence", capability="duplicate_handling", component="POST /mvp/upload/bulk (same bytes twice)", data="DataFactory.duplicate_of")
def ft005(ctx):
    f = ctx.data.file()
    _bulk(ctx, [f], persona="owner")
    before = len(ctx.evidence.find_all(filename=f.name))
    _bulk(ctx, [ctx.data.duplicate_of(f)], persona="owner")
    after = len(ctx.evidence.find_all(filename=f.name))
    assert after in (before, before + 1), "duplicate upload produced an unexpected number of records"
    hashes = {r.get("sha256") for r in ctx.evidence.find_all(filename=f.name)}
    assert hashes == {f.sha256}, "duplicate upload altered the stored hash"


@case("UC02-FT006", framework="integrity", capability="hash_generation", component="GET /evidence/repository sha256 + GET /api/evidence/{id}/integrity",
      data="DataFactory.file")
def ft006(ctx):
    f, _, row = sc.upload_and_locate(ctx)
    sc.verify_integrity(ctx, f, row)


@case("UC02-FT007", framework="evidence", capability="batch_status_counts", component="POST /mvp/upload/bulk notice + repository delta",
      data="DataFactory.files(4)")
def ft007(ctx):
    before = len(ctx.evidence.repository())
    files = ctx.data.files(4)
    resp = _bulk(ctx, files, persona="owner")
    assert_equal(resp.notice, "Bulk upload complete: 4 file(s) with metadata tags applied.", "batch notice count")
    after = len(ctx.evidence.repository())
    assert after - before >= 4, f"repository grew by {after - before}, expected >= 4"


@case("UC02-FT008", framework="search", capability="uploaded_evidence_searchable", component="GET /api/evidence/search", data="unique filename token")
def ft008(ctx):
    f, _, _ = sc.upload_and_locate(ctx)
    hits = sc.wait_until(lambda: ctx.evidence.search(q=f.name.rsplit(".", 1)[0]), timeout=60, interval=ctx.cfg.poll_interval,
                         what=f"search hit for {f.name}")
    assert any(f.name in str(h) for h in hits), "uploaded file not returned by search"


register_crosscutting(PROFILE)
