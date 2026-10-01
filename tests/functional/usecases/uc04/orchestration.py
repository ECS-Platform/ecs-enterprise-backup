"""UC04 - Evidence dashboard and hash integrity check.

NOTE (workbook): FT001-FT008 of this sheet describe SharePoint/ServiceNow connector behaviour although the sheet title is
"Evidence dashboard and hash integrity check". IDs/descriptions are preserved verbatim and automated as written; the cross-cutting
rows (FT009+) use the sheet title.
"""

from __future__ import annotations

from ...framework import scenarios as sc
from ...framework.assertions import assert_exists, assert_json_field, assert_record_count, assert_status, assert_traceability
from ...framework.crosscutting import register_crosscutting
from ...framework.errors import CapabilityBlocked
from ...framework.spec import UseCaseProfile, case

PROFILE = UseCaseProfile(uc="UC04", subject="evidence dashboard and hash integrity", page="/mvp/evidence-dashboard",
                         api="/api/evidence-dashboard/fcm-progress", dashboard_api="/api/evidence-dashboard/phase2-leadership",
                         rbac_capability="upload_evidence", audit_action="upload")


def _connect(ctx, kind: str):
    name = ctx.data.connector(kind)
    ctx.connectors.require_available(name)
    cfg = ctx.track(ctx.connectors.config_status(name))
    assert cfg.status < 500
    health = ctx.track(ctx.connectors.health_check(name))
    assert health.status < 500, health.text[:200]
    return name, health


def _collect(ctx, kind: str):
    name, _ = _connect(ctx, kind)
    ctx.require_live_connectors()
    resp = ctx.track(ctx.connectors.collect(name, live=True, max_items=3))
    assert resp.status < 500, resp.text[:200]
    rows = ctx.evidence.find_all(source=name)
    assert_record_count(rows, minimum=1, msg=f"no {kind} evidence persisted")
    return name, rows


@case("UC04-FT001", framework="connector", capability="connect_sharepoint", component="GET config-status + POST /api/connectors/sharepoint/health-check",
      data="connector sharepoint")
def ft001(ctx):
    _connect(ctx, "sharepoint")


@case("UC04-FT002", framework="connector", capability="collect_sharepoint_evidence", component="POST /api/connectors/sharepoint/collect",
      data="connector sharepoint (live)")
def ft002(ctx):
    _collect(ctx, "sharepoint")


@case("UC04-FT003", framework="connector", capability="connect_servicenow", component="GET config-status + POST /api/connectors/servicenow/health-check",
      data="connector servicenow")
def ft003(ctx):
    _connect(ctx, "servicenow")


@case("UC04-FT004", framework="connector", capability="collect_servicenow_evidence", component="POST /api/connectors/servicenow/collect",
      data="connector servicenow (live)")
def ft004(ctx):
    _collect(ctx, "servicenow")


@case("UC04-FT005", framework="evidence", capability="source_traceability", component="evidence.source_system/source_object_id/url",
      data="collected SharePoint + ServiceNow rows")
def ft005(ctx):
    for kind in ("sharepoint", "servicenow"):
        _, rows = _collect(ctx, kind)
        for r in rows[:5]:
            assert_traceability(r, ("source", "evidence_id"))
            assert ctx.connectors.source_traceability(r), "no source reference on collected evidence"


@case("UC04-FT006", framework="connector", capability="authorization_failure_handling", component="POST /api/connectors/{name}/health-check (bad credentials)",
      data="connector with invalid credentials")
def ft006(ctx):
    name = ctx.data.connector("servicenow")
    ctx.connectors.require_available(name)
    resp = ctx.track(ctx.connectors.health_check(name))
    assert resp.status < 500 and "Traceback" not in resp.text
    if not any(t in resp.text.lower() for t in ("unauthor", "forbidden", "401", "403", "credential", "not configured", "fail")):
        raise CapabilityBlocked("connector currently authorises successfully; point ECS at an invalid credential to exercise this case",
                                requires="connector with invalid credentials")


@case("UC04-FT007", framework="connector", capability="detect_source_changes", component="POST /api/connectors/{name}/collect (before/after) + content_hash",
      data="collected rows, changed source object")
def ft007(ctx):
    name, rows = _collect(ctx, "servicenow")
    snapshot = {r.get("evidence_id"): r.get("sha256") for r in rows}
    ctx.require_live_connectors()
    ctx.connectors.collect(name, live=True, max_items=3)
    after = {r.get("evidence_id"): r.get("sha256") for r in ctx.evidence.find_all(source=name)}
    assert set(snapshot) <= set(after), "previously collected evidence disappeared"


@case("UC04-FT008", framework="audit", capability="connector_audit_history", component="sync_runs + audit_log + /api/audit/integrations/health",
      data="connector health/collect calls")
def ft008(ctx):
    name, _ = _connect(ctx, "sharepoint")
    assert_status(ctx.connectors.integrations_health(), 200)
    if ctx.db.enabled:
        assert_exists(ctx.db.audit_records(action=name) or ctx.db.find("sync_runs", connector=name), "no audit/sync history for connector")


register_crosscutting(PROFILE)
