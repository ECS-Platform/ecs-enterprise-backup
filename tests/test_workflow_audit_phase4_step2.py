"""Phase 4 Step 2 — workflow audit wiring tests.

Validates the audit_workflow_action helper that the workflow handlers call:
  * flag OFF (default) -> no-op, nothing written (existing behavior unchanged)
  * flag ON -> durable record written with before/after, request_id, identity
  * Phase 1 authenticated principal is preferred over the URL/form fallback actor
  * fallback identity is used (auth_source=legacy) when no principal is present
  * the helper never raises, even if the audit backend fails

No live DB: app.audit.service.default_audit_service is swapped for a capture stub.
"""

from __future__ import annotations

import os
import types

import pytest

import app.audit.workflow as wf
import app.audit.service as svc


class _CaptureService:
    def __init__(self):
        self.records = []

    def record(self, rec):
        self.records.append(rec)
        return True


class _Principal:
    is_authenticated = True

    def __init__(self):
        self.user_id = "oid-123"
        self.username = "alice@bank.com"
        self.display_name = "Alice Banker"
        self.roles = ("auditor",)
        self.auth_source = "azure_ad"


def _request(principal=None, request_id=""):
    state = types.SimpleNamespace()
    if principal is not None:
        state.principal = principal
    if request_id:
        state.request_id = request_id
    return types.SimpleNamespace(state=state)


@pytest.fixture
def capture(monkeypatch):
    cap = _CaptureService()
    monkeypatch.setattr(svc, "default_audit_service", cap)
    # workflow.py imports default_audit_service lazily inside the function, so
    # patching the module attribute is sufficient.
    yield cap


@pytest.fixture(autouse=True)
def clean_flag():
    prev = os.environ.get("AUDIT_WORKFLOW_ENABLED")
    yield
    if prev is None:
        os.environ.pop("AUDIT_WORKFLOW_ENABLED", None)
    else:
        os.environ["AUDIT_WORKFLOW_ENABLED"] = prev


def test_flag_defaults_off():
    os.environ.pop("AUDIT_WORKFLOW_ENABLED", None)
    assert wf.workflow_audit_enabled() is False


def test_flag_off_is_noop(capture):
    os.environ["AUDIT_WORKFLOW_ENABLED"] = "false"
    out = wf.audit_workflow_action(_request(_Principal()), "evidence.approve",
                                   resource="K1", fallback_actor="Alice")
    assert out is False
    assert capture.records == []  # nothing written


def test_flag_on_persists_with_identity_and_state(capture):
    os.environ["AUDIT_WORKFLOW_ENABLED"] = "true"
    out = wf.audit_workflow_action(
        _request(_Principal(), request_id="req-77"), "evidence.approve",
        resource="PCI::MFA", fallback_actor="urlUser", fallback_role="owner",
        before_state={"status": "Pending Auditor Review"},
        after_state={"status": "Auditor Approved"},
        detail={"control": "MFA"})
    assert out is True
    assert len(capture.records) == 1
    rec = capture.records[0]
    # Phase 1 identity preferred over URL/form fallback.
    assert rec.actor == "oid-123"
    assert rec.auth_source == "azure_ad"
    assert rec.role == "auditor"
    # before/after captured.
    assert rec.before_state == {"status": "Pending Auditor Review"}
    assert rec.after_state == {"status": "Auditor Approved"}
    # request_id propagated from request.state.
    assert rec.request_id == "req-77"
    assert rec.resource == "PCI::MFA"
    assert rec.detail.get("display_name") == "Alice Banker"


def test_fallback_identity_when_no_principal(capture):
    os.environ["AUDIT_WORKFLOW_ENABLED"] = "true"
    out = wf.audit_workflow_action(_request(None), "evidence.reject",
                                   resource="K2", fallback_actor="LegacyUser",
                                   fallback_role="auditor",
                                   after_state={"status": "Rejected"})
    assert out is True
    rec = capture.records[0]
    assert rec.actor == "LegacyUser"
    assert rec.auth_source == "legacy"


def test_request_id_generated_when_absent(capture):
    os.environ["AUDIT_WORKFLOW_ENABLED"] = "true"
    wf.audit_workflow_action(_request(_Principal()), "observation.close", resource="OBS-1")
    rec = capture.records[0]
    assert rec.request_id and len(rec.request_id) >= 8


def test_never_raises_on_backend_failure(monkeypatch):
    os.environ["AUDIT_WORKFLOW_ENABLED"] = "true"

    class _Boom:
        def record(self, rec):
            raise RuntimeError("db down")

    monkeypatch.setattr(svc, "default_audit_service", _Boom())
    # Must swallow the error and return False, never propagate.
    assert wf.audit_workflow_action(_request(_Principal()), "evidence.approve",
                                    resource="K3") is False
