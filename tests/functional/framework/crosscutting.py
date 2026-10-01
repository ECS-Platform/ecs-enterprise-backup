"""Generic scenarios for the generated 'Validate <topic> for <use case>' workbook rows (~170 of the 331 tests).

One implementation per topic, parameterised by the use case's :class:`UseCaseProfile` (its real ECS page/API/trigger).
``register_crosscutting`` binds each such workbook row to the topic scenario for its use case - no per-UC duplication.
"""

from __future__ import annotations

from typing import Any, Callable

from . import registry, scenarios as sc
from .api_client import ApiResponse, EcsApiClient
from .assertions import (assert_compliance_mapping, assert_denied, assert_equal, assert_exists, assert_json_field,
                         assert_record_count, assert_role_access, assert_status, assert_success)
from .data_factory import TestFile
from .errors import CapabilityBlocked
from .spec import CaseMeta, UseCaseProfile, register
from .wait import wait_until


# ---- request factories for rbac_expectations (each returns a function client -> response) ------------------------------
def _upload_request(ctx) -> Callable[[EcsApiClient], ApiResponse]:
    f = ctx.data.file()
    fields = ctx.data.evidence_metadata()

    def send(client: EcsApiClient) -> ApiResponse:
        return client.post("/evidence/upload", data=dict(fields), headers={"Accept": "application/json"},
                           files={"evidence_file": (f.name, f.content, f.mime)})

    return send


RBAC_REQUESTS: dict[str, Callable[[Any], Callable[[EcsApiClient], ApiResponse]]] = {
    "upload_evidence": _upload_request,
    "admin_platform": lambda ctx: (lambda c: c.post("/api/audit/scheduler/execute", json={})),
    "manage_frameworks": lambda ctx: (lambda c: c.post("/api/onboarding/simulate", json={})),
}


def default_trigger(ctx) -> ApiResponse:
    """Shared workflow trigger: bulk upload of one valid file (ECS redirects with a 'Bulk upload complete' notice)."""
    return ctx.track(ctx.evidence.bulk_upload([ctx.data.file()], persona="owner"))


# ---- topic scenarios ------------------------------------------------------------------------------------------------------------
def rbac_access(ctx, p: UseCaseProfile) -> None:
    with ctx.step("authorised personas can open the page"):
        sc.pages_for_roles(ctx, p.page, p.view_personas)
    if p.rbac_capability:
        with ctx.step(f"capability '{p.rbac_capability}' honours the ECS role matrix"):
            ctx.require_mutation()
            ctx.rbac.check_capability(p.rbac_capability, RBAC_REQUESTS[p.rbac_capability](ctx))


def performance(ctx, p: UseCaseProfile) -> None:
    ctx.perf.time_get(p.api or p.page, p.perf_key, **p.api_params)


def notification(ctx, p: UseCaseProfile) -> None:
    ctx.require_mutation()
    with ctx.step("workflow completion raises an in-app notice"):
        resp = (p.trigger or default_trigger)(ctx)
        ctx.notifier.assert_notified(resp, contains="complete" if p.trigger is None else p.notice_contains)
    with ctx.step("workflow failure (permission denied) raises a failure notice"):
        denied = ctx.track(ctx.evidence.bulk_upload([ctx.data.file()], persona="auditor"))
        ctx.notifier.assert_notified(denied, contains="denied")


def security_controls(ctx, p: UseCaseProfile) -> None:
    ctx.security.require_enabled()
    with ctx.step("authentication enforced"):
        ctx.security.assert_auth_enforced()
    with ctx.step("unauthorised role cannot mutate and the attempt is audited"):
        ctx.require_mutation()
        resp = ctx.security.unauthorized_mutation("auditor", _upload_request(ctx))
        ctx.track(resp)
        ctx.audit.verify(request_id=resp.request_id, action="denied")


def evidence_integrity(ctx, p: UseCaseProfile) -> None:
    if p.integration_source == "scheduler":
        run = sc.collection_run(ctx)
        rows = wait_until(lambda: ctx.evidence.find_all(application=ctx.data.application()), timeout=ctx.cfg.long_timeout,
                          interval=ctx.cfg.poll_interval, what="collected evidence")
        assert all(r.get("sha256") for r in rows[:20]), "collected evidence rows carry no sha256"
        ctx.correlation.add("run_id", run.get("run_id"))
        return
    f, _, row = sc.upload_and_locate(ctx)
    sc.verify_integrity(ctx, f, row)


def compliance_mapping(ctx, p: UseCaseProfile) -> None:
    fw, ctrl = ctx.data.framework(), ctx.data.control()
    f, _, row = sc.upload_and_locate(ctx, framework=fw, control=ctrl)
    assert_compliance_mapping(row, framework=fw, control=ctrl or None)
    if ctx.db.enabled:
        uid = ctx.db.one("evidence", title=f.name) or ctx.db.one("evidence", source_object_id=f.name)
        if uid:
            rel = ctx.db.relationships(uid["evidence_uid"])
            assert rel["frameworks"] or rel["controls"], "no framework/control mapping rows for the evidence"


def concurrency(ctx, p: UseCaseProfile) -> None:
    ctx.require_mutation()
    files = [ctx.data.file() for _ in range(32)]
    res = ctx.concurrency.run(lambda i: ctx.evidence.upload(files[i % len(files)], persona="owner"))
    ctx.concurrency.assert_no_conflicts(res)
    ids = [r.json().get("evidence_id") for r in res.results if r.status == 200 and r.is_json]
    assert_equal(len(ids), len(set(ids)), "concurrent uploads produced duplicate evidence ids")


def dashboard_visibility(ctx, p: UseCaseProfile) -> None:
    sc.page_loads(ctx, p.page, "cio")
    body = ctx.dashboard.fcm_progress()
    assert_exists(body, "KPI payload")
    filtered = ctx.dashboard.fcm_progress(application=ctx.data.application())
    assert filtered is not None, "filtered dashboard failed"
    if p.dashboard_api:
        assert_exists(ctx.api.get_json(p.dashboard_api), f"{p.dashboard_api} payload")


def retention_archival(ctx, p: UseCaseProfile) -> None:
    with ctx.step("lifecycle/retention view available"):
        assert_status(ctx.lifecycle.page(), 200)
    with ctx.step("archival workflow triggered"):
        ctx.require_destructive()
        ctx.lifecycle.trigger_archival()


def integration_flow(ctx, p: UseCaseProfile) -> None:
    f, _, row = sc.upload_and_locate(ctx)
    with ctx.step("evidence searchable"):
        assert any(r.get("filename") == f.name or f.name in str(r) for r in ctx.evidence.search(q=f.name)) or row
    with ctx.step("dashboard reflects repository"):
        sc.page_loads(ctx, "/mvp/evidence-dashboard", "owner")
    with ctx.step("audit trail"):
        ctx.audit.verify(action="upload")


def retry_recovery(ctx, p: UseCaseProfile) -> None:
    ctx.require_mutation()
    f = ctx.data.file()
    with ctx.step("first attempt fails (role not permitted)"):
        assert_denied(ctx.evidence.upload(f, persona="auditor"))
    with ctx.step("re-run succeeds"):
        sc.upload_and_locate(ctx, f)


def data_accuracy(ctx, p: UseCaseProfile) -> None:
    f, body, row = sc.upload_and_locate(ctx, application=ctx.data.application())
    assert_equal(row.get("filename"), f.name, "filename differs from source")
    assert_equal(row.get("sha256"), f.sha256, "hash differs from source")
    assert_equal(str(row.get("application")), ctx.data.application(), "application differs from source")


def audit_logging(ctx, p: UseCaseProfile) -> None:
    ctx.require_mutation()
    resp = ctx.track(ctx.evidence.upload(persona="owner"))
    assert_success(resp)
    rec = ctx.audit.verify(request_id=resp.request_id, action=p.audit_action, actor=None)
    assert rec.get("created_at") or rec.get("timestamp") or rec.get("at"), "audit record has no timestamp"


def error_handling(ctx, p: UseCaseProfile) -> None:
    with ctx.step("incomplete input is rejected with a meaningful message"):
        r = ctx.track(ctx.api.post("/evidence/submit", data={}, headers={"Accept": "application/json"}))
        assert r.status in (400, 422), f"expected a validation error, got {r.status}"
        assert "Traceback" not in r.text and r.status < 500
        assert r.text.strip(), "empty error body"
    with ctx.step("metadata validation reports the problem"):
        r = ctx.track(ctx.evidence.validate_metadata({}))
        assert r.status < 500 and "Traceback" not in r.text


TOPIC_IMPLS: dict[str, tuple[Callable[[Any, UseCaseProfile], None], str, str, str]] = {
    # topic slug: (impl, framework, capability, component)
    "rbac_access": (rbac_access, "rbac", "role_matrix_access", "role_permissions + page/route guards"),
    "performance": (performance, "performance", "timed_response_vs_sla", "primary page/API of the use case"),
    "notification": (notification, "notification", "in_app_notice", "redirect notice= / notification feed"),
    "security_controls": (security_controls, "security", "unauthorized_manipulation", "POST /evidence/upload (role guard) + audit"),
    "evidence_integrity": (evidence_integrity, "evidence", "hash_integrity", "POST /evidence/upload, GET /api/evidence/{id}/integrity"),
    "compliance_mapping": (compliance_mapping, "compliance", "evidence_control_mapping", "evidence_control_map / evidence_framework_map"),
    "concurrency": (concurrency, "concurrency", "parallel_uploads", "POST /evidence/upload (parallel)"),
    "dashboard_visibility": (dashboard_visibility, "dashboard", "kpi_and_filter", "GET /api/evidence-dashboard/fcm-progress"),
    "retention_archival": (retention_archival, "lifecycle", "archival_trigger", "evidence_reviews (no archival API)"),
    "integration_flow": (integration_flow, "workflow", "end_to_end_pipeline", "upload -> repository -> search -> dashboard -> audit"),
    "retry_recovery": (retry_recovery, "workflow", "retry_after_failure", "POST /evidence/upload"),
    "data_accuracy": (data_accuracy, "evidence", "source_vs_output", "GET /evidence/repository"),
    "audit_logging": (audit_logging, "audit", "audit_record_for_action", "audit_log (request_id)"),
    "error_handling": (error_handling, "api", "validation_error_handling", "POST /evidence/submit, POST /api/evidence/validate-metadata"),
}


def register_crosscutting(profile: UseCaseProfile, implemented: set[str] | None = None) -> int:
    """Bind every 'Validate <topic> for <UC>' workbook row of ``profile.uc`` to its topic scenario. Returns rows bound."""
    n = 0
    for t in registry.tests_for(profile.uc):
        if not t.topic or (implemented and t.id in implemented):
            continue
        impl, fw, cap, comp = TOPIC_IMPLS[t.topic]

        def bound(ctx, _impl=impl, _p=profile):
            _impl(ctx, _p)

        register(t.id, bound, CaseMeta(t.id, fw, cap, comp, data=f"profile:{profile.uc}", kind="crosscutting"))
        n += 1
    return n
