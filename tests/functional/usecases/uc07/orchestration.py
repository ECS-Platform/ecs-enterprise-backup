"""UC07 - Evidence similarity and reuse (Cross Control).

NOTE (workbook): FT001-FT008 describe common-control creation/mapping; automated as written.
"""

from __future__ import annotations

from ...framework import scenarios as sc
from ...framework.assertions import (assert_denied, assert_equal, assert_exists, assert_record_count, assert_status, assert_success)
from ...framework.crosscutting import register_crosscutting
from ...framework.errors import CapabilityBlocked
from ...framework.spec import UseCaseProfile, case

PROFILE = UseCaseProfile(uc="UC07", subject="evidence similarity and cross-control reuse", page="/mvp/reuse", api="/api/evidence-reuse/records",
                         dashboard_api="/api/platform/evidence-reuse", rbac_capability="manage_frameworks", audit_action="reuse")


def _controls(ctx):
    body = ctx.search.common_controls()
    rows = body.get("controls", body) if isinstance(body, dict) else body
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def _slug(row) -> str:
    return str(row.get("slug") or row.get("id") or row.get("control_id") or "")


@case("UC07-FT001", framework="compliance", capability="create_common_control", component="GET /api/common-controls (ECS exposes read-only catalogue)",
      data="common-control catalogue")
def ft001(ctx):
    rows = _controls(ctx)
    assert_record_count(rows, minimum=1, msg="common-control catalogue is empty")
    raise CapabilityBlocked("ECS has no create/edit endpoint for common controls (GET-only /api/common-controls*; catalogue is config-driven). "
                            "Existence of the catalogue was asserted above.", requires="common control create API")


@case("UC07-FT002", framework="compliance", capability="map_control_to_frameworks", component="GET /api/common-controls/{slug} + /framework/{framework_id}",
      data="first common control")
def ft002(ctx):
    rows = _controls(ctx)
    assert_record_count(rows, minimum=1)
    detail = ctx.track(ctx.search.common_control(_slug(rows[0])))
    assert_success(detail)
    body = detail.json()
    frameworks = [k for k in ("frameworks", "mappings", "framework_mappings") if body.get(k)]
    assert frameworks, f"common control exposes no framework mapping: {list(body)[:10]}"


@case("UC07-FT003", framework="evidence", capability="reuse_via_common_control", component="POST /api/evidence-reuse/analyze + GET /api/evidence-reuse/records",
      data="repository evidence")
def ft003(ctx):
    resp = ctx.track(ctx.ai.similar_evidence())
    assert_success(resp)
    records = ctx.track(ctx.ai.reuse_records())
    assert_success(records)
    assert_exists(records.json())


@case("UC07-FT004", framework="compliance", capability="no_duplicate_common_control_identity", component="GET /api/common-controls identity uniqueness",
      data="catalogue ids")
def ft004(ctx):
    ids = [_slug(r) for r in _controls(ctx)]
    assert_equal(len(ids), len(set(ids)), "duplicate common-control identity in the catalogue")


@case("UC07-FT005", framework="compliance", capability="edit_common_control_mapping", component="(no edit API)", data="n/a")
def ft005(ctx):
    raise CapabilityBlocked("ECS exposes no write API for common-control mappings; mapping edits are done in config/framework_control_master.",
                            requires="common control mapping edit API")


@case("UC07-FT006", framework="search", capability="search_filter_common_controls", component="GET /api/common-controls, /api/framework-control-master/search",
      data="first common control name")
def ft006(ctx):
    rows = _controls(ctx)
    assert_record_count(rows, minimum=1)
    first = rows[0]
    term = str(first.get("name") or first.get("title") or _slug(first))[:12]
    resp = ctx.track(ctx.search.control_master_search(term))
    assert resp.status < 500
    fw = ctx.track(ctx.compliance.common_controls_for_framework(ctx.data.framework()))
    assert fw.status < 500


@case("UC07-FT007", framework="rbac", capability="maintenance_access_control", component="role guard on framework onboarding (manage_frameworks)",
      data="rbac_expectations.manage_frameworks")
def ft007(ctx):
    ctx.require_mutation()
    ctx.rbac.check_capability("manage_frameworks", lambda c: c.post("/api/onboarding/simulate", json={}))


@case("UC07-FT008", framework="compliance", capability="common_controls_persist_after_restart", component="GET /api/common-controls across restart", data="catalogue")
def ft008(ctx):
    ctx.require_restart_hook()
    before = sorted(_slug(r) for r in _controls(ctx))
    ctx.restart_ecs()
    assert_equal(sorted(_slug(r) for r in _controls(ctx)), before)


register_crosscutting(PROFILE)
