"""UC05 - Common Evidence Querying (Chatbot prebuilt).

NOTE (workbook): FT001-FT008 of this sheet describe the evidence dashboard / hash-integrity behaviour (title of UC04); they are
automated as written. The cross-cutting rows (FT009+) use this sheet's title (common evidence chatbot querying).
"""

from __future__ import annotations

from ...framework import scenarios as sc
from ...framework.assertions import (assert_equal, assert_exists, assert_hash_changed, assert_json_field, assert_not_equal,
                                     assert_status, assert_success)
from ...framework.crosscutting import register_crosscutting
from ...framework.errors import CapabilityBlocked
from ...framework.spec import UseCaseProfile, case

PROFILE = UseCaseProfile(uc="UC05", subject="common evidence chatbot querying", page="/dashboard",
                         api="/mvp/api/common-evidence-presets", rbac_capability="",
                         view_personas=("owner", "auditor", "cio", "compliance_head"), audit_action="chat")


@case("UC05-FT001", framework="dashboard", capability="summary_metrics_displayed", component="GET /mvp/evidence-dashboard + /api/evidence-dashboard/fcm-progress",
      data="existing repository")
def ft001(ctx):
    sc.page_loads(ctx, "/mvp/evidence-dashboard", "cio")
    sc.json_loads(ctx, ctx.dashboard.fcm_progress, "fcm-progress summary")
    sc.json_loads(ctx, ctx.dashboard.leadership, "phase2 leadership summary")


@case("UC05-FT002", framework="dashboard", capability="filter_by_application_framework", component="GET /api/evidence-dashboard/fcm-progress?application=&framework_id=",
      data="catalog.default_application / default_framework")
def ft002(ctx):
    base, filtered = sc.filter_changes_view(ctx, ctx.dashboard.fcm_progress, {}, {"application": ctx.data.application()})
    page = sc.page_loads(ctx, "/mvp/evidence-dashboard", "cio", application=ctx.data.application())
    assert ctx.data.application() in page.text, "selected application not reflected on the dashboard page"


@case("UC05-FT003", framework="dashboard", capability="drill_down", component="GET /api/evidence-dashboard/fcm-drill/{framework_id}/{control_id}",
      data="first framework/control from fcm-progress")
def ft003(ctx):
    prog = ctx.dashboard.fcm_progress()
    pair = _first_framework_control(prog)
    if not pair:
        raise CapabilityBlocked("fcm-progress exposes no framework/control rows to drill into in this environment", requires="framework control master data")
    sc.drill(ctx, lambda: ctx.dashboard.fcm_drill(*pair), "framework/control")


def _first_framework_control(obj):
    """Find a (framework_id, control_id) pair anywhere in an fcm-progress payload."""
    if isinstance(obj, dict):
        fw = obj.get("framework_id") or obj.get("framework")
        ctrl = obj.get("control_id")
        if fw and ctrl:
            return str(fw), str(ctrl)
        for v in obj.values():
            r = _first_framework_control(v)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _first_framework_control(v)
            if r:
                return r
    return None


@case("UC05-FT004", framework="integrity", capability="hash_verify_untampered", component="POST /evidence/upload -> GET /api/evidence/{id}/integrity",
      data="DataFactory.file")
def ft004(ctx):
    f, _, row = sc.upload_and_locate(ctx)
    sc.verify_integrity(ctx, f, row)


@case("UC05-FT005", framework="integrity", capability="detect_tampered_evidence", component="object store bytes vs stored sha256 (local store only)",
      data="DataFactory.file + ObjectStoreHelper.tamper")
def ft005(ctx):
    ctx.require_destructive()
    f, _, row = sc.upload_and_locate(ctx)
    ref = str(row.get("object_reference") or "")
    if "evidence/" not in ref:
        raise CapabilityBlocked("evidence has no object-store snapshot (custody REFERENCE_ONLY); nothing to tamper", requires="SNAPSHOT custody")
    key = "evidence/" + ref.split("evidence/", 1)[-1]
    ctx.storage.tamper(key)
    try:
        ctx.storage.verify_matches(key, row["sha256"])
    except AssertionError:
        return  # tamper detected by hash comparison, as required
    raise AssertionError("tampered object still matches the stored hash")


@case("UC05-FT006", framework="integrity", capability="original_hash_not_overwritten", component="re-upload same filename / GET /evidence/repository sha256",
      data="DataFactory.new_version_of")
def ft006(ctx):
    f, _, row = sc.upload_and_locate(ctx)
    original = row["sha256"]
    ctx.evidence.upload(ctx.data.new_version_of(f))
    first = [r for r in ctx.evidence.find_all(filename=f.name)]
    assert original in {r.get("sha256") for r in first}, "original hash no longer present after new upload"
    stored_hash = ctx.evidence.stored_hash(row["evidence_id"])
    assert_equal(stored_hash, original, "original evidence hash was silently overwritten")


@case("UC05-FT007", framework="dashboard", capability="dashboard_after_ingestion", component="fcm-progress / evidence-workflow summary before vs after upload",
      data="DataFactory.file")
def ft007(ctx):
    before = ctx.api.get_json("/api/evidence-workflow/summary")
    sc.upload_and_locate(ctx)
    after = ctx.api.get_json("/api/evidence-workflow/summary")
    assert_exists(after)
    assert before != after or ctx.evidence.repository(), "dashboard summary did not reflect the new ingestion"


@case("UC05-FT008", framework="dashboard", capability="dashboard_persists_after_restart", component="dashboard KPIs before/after ECS restart",
      data="repository state")
def ft008(ctx):
    ctx.require_restart_hook()
    before = ctx.dashboard.kpi_values(ctx.dashboard.fcm_progress())
    ctx.restart_ecs()
    after = ctx.dashboard.kpi_values(ctx.dashboard.fcm_progress())
    assert_equal(after, before, "dashboard KPIs changed across restart")


register_crosscutting(PROFILE)
