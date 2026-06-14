"""Phase 2 Step 2A — RBAC delegation parity tests.

Asserts that delegating a capability to the PolicyEngine yields the SAME boolean
as the legacy logic, for every role x every capability. This is the gating
control for delegation: if any cell differs, delegation is unsafe to enable.

The kill switch (ECS_RBAC_DELEGATION_ENABLED) is toggled in-process so both code
paths run against identical inputs. Default-off behavior is also asserted.
"""

from __future__ import annotations

import importlib
import os

import pytest

# Every role string the system may pass in (canonical + legacy aliases used by
# the legacy predicates), so parity is proven across the real input space.
ROLES = [
    "cio", "auditor", "owner", "application_owner", "compliance_officer",
    "compliance_head", "security_officer", "vertical_head", "functional_head",
    "control_owner", "system_admin", "admin", "enterprise_admin",
    "operations_owner", "ai_governance_owner", "ai_sdlc_owner", "framework_owner",
    "", "unknown_role",
]

# Engine B capabilities (function name on role_permissions).
B_CAPS = [
    "can_upload_evidence", "can_submit_to_auditor", "can_review_evidence",
    "can_export_reports", "can_manage_frameworks", "can_assign_owner",
    "can_escalate", "can_request_reupload", "can_raise_exception",
]

# Engine D capabilities (function name on framework_onboarding_engine).
D_CAPS = [
    "can_manage_framework_onboarding", "can_review_framework_onboarding",
    "can_reuse_evidence_decision",
]


def _fresh_modules():
    import modules.shared.services.role_permissions as rp
    import modules.frameworks.engines.framework_onboarding_engine as fo
    importlib.reload(rp)
    importlib.reload(fo)
    return rp, fo


def _eval(rp, fo, cap, role):
    if hasattr(rp, cap):
        return getattr(rp, cap)(role)
    return getattr(fo, cap)(role)


@pytest.fixture
def restore_env():
    prev = os.environ.get("ECS_RBAC_DELEGATION_ENABLED")
    yield
    if prev is None:
        os.environ.pop("ECS_RBAC_DELEGATION_ENABLED", None)
    else:
        os.environ["ECS_RBAC_DELEGATION_ENABLED"] = prev


def test_kill_switch_defaults_off(restore_env):
    os.environ.pop("ECS_RBAC_DELEGATION_ENABLED", None)
    rp, _ = _fresh_modules()
    assert rp._delegation_enabled() is False


def test_parity_all_roles_all_capabilities(restore_env):
    # 1) Capture legacy results (delegation OFF).
    os.environ["ECS_RBAC_DELEGATION_ENABLED"] = "false"
    rp, fo = _fresh_modules()
    legacy = {(cap, role): _eval(rp, fo, cap, role) for cap in (B_CAPS + D_CAPS) for role in ROLES}

    # 2) Capture delegated results (delegation ON).
    os.environ["ECS_RBAC_DELEGATION_ENABLED"] = "true"
    rp, fo = _fresh_modules()
    delegated = {(cap, role): _eval(rp, fo, cap, role) for cap in (B_CAPS + D_CAPS) for role in ROLES}

    # 3) Diff.
    mismatches = [(cap, role, legacy[(cap, role)], delegated[(cap, role)])
                  for cap in (B_CAPS + D_CAPS) for role in ROLES
                  if legacy[(cap, role)] != delegated[(cap, role)]]

    if mismatches:
        lines = [f"  {cap}({role!r}): legacy={lg} delegated={dg}" for cap, role, lg, dg in mismatches]
        pytest.fail(f"{len(mismatches)} parity mismatch(es):\n" + "\n".join(lines))


def test_signatures_and_return_types_preserved(restore_env):
    os.environ["ECS_RBAC_DELEGATION_ENABLED"] = "true"
    rp, fo = _fresh_modules()
    for cap in B_CAPS + D_CAPS:
        val = _eval(rp, fo, cap, "auditor")
        assert isinstance(val, bool), f"{cap} must return bool, got {type(val)}"
