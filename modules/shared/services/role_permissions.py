"""Centralized ECS role permissions — audit governance workflow.

Phase 2 Step 2A: these capability predicates can DELEGATE to the consolidated
PolicyEngine (app/auth/authz.py) instead of their legacy set-membership logic.
Delegation is gated by the ECS_RBAC_DELEGATION_ENABLED kill switch (default FALSE),
so runtime behavior is unchanged until explicitly enabled. Every legacy body is
preserved verbatim as the default path; a differential parity test asserts that
legacy_result == delegated_result for every role and capability.

Phase 2 Step 2B: RBAC_ENFORCEMENT_ENABLED (default FALSE) ALSO activates the same
parity-equivalent engine-backed decision path here. The enforcement foundation
(app/auth/enforcement.py) additionally derives the effective role from the
authenticated principal at the route layer; these predicates keep their (role) ->
bool contract unchanged.
"""

from __future__ import annotations

import os
from urllib.parse import quote

from fastapi.responses import RedirectResponse


# ---------------------------------------------------------------------------
# Phase 2 Step 2A — delegation kill switch.
#   Default FALSE: every predicate uses its legacy body (no behavior change).
#   Set ECS_RBAC_DELEGATION_ENABLED=true to route through the PolicyEngine.
#
# Phase 2 Step 2B — enforcement foundation.
#   RBAC_ENFORCEMENT_ENABLED also routes these predicates through the SAME
#   parity-tested PolicyEngine legacy-compat path, so enabling enforcement implies
#   the engine-backed decision logic for a given role. The decision is identical to
#   legacy for any fixed role (parity-tested); enforcement changes WHERE the role
#   comes from at the route layer (app/auth/enforcement.resolve_effective_role),
#   not the per-role verdict here. Signatures and return values are unchanged.
# ---------------------------------------------------------------------------
def _delegation_enabled() -> bool:
    if str(os.environ.get("ECS_RBAC_DELEGATION_ENABLED", "")).strip().lower() in {
        "1", "true", "yes", "on",
    }:
        return True
    # Step 2B: enforcement implies engine-backed (parity-equivalent) decisions.
    return str(os.environ.get("RBAC_ENFORCEMENT_ENABLED", "")).strip().lower() in {
        "1", "true", "yes", "on",
    }


def _delegate(capability: str, role: str):
    """Return the PolicyEngine verdict for a capability, or None to use legacy.

    Delegates through the engine's LEGACY-COMPAT path (can_legacy), which is
    byte-for-byte identical to the historical predicate (parity-tested). None is
    returned whenever delegation/enforcement is disabled or the engine cannot
    answer, so the caller falls back to the verbatim legacy logic. Never raises.
    """
    if not _delegation_enabled():
        return None
    try:
        from app.auth.authz import get_policy_engine

        return bool(get_policy_engine().can_legacy(role, capability))
    except Exception:  # noqa: BLE001 - any engine error => legacy fallback
        return None


EXECUTIVE_ROLES = frozenset({
    "cio", "vertical_head", "compliance_head", "compliance_officer", "functional_head",
})

OPERATIONAL_UPLOAD_ROLES = frozenset({"owner"})

AUDITOR_GOVERNANCE_ROLES = frozenset({"auditor", "enterprise_admin"})

UPLOAD_ACTIONS = frozenset({
    "upload", "upload_evidence", "upload_missing", "upload_batch", "upload_draft",
    "replace", "replace_evidence", "bulk_upload", "submit", "submit_to_auditor",
    "submit_for_review", "add_attachment", "upload_package", "upload_workflow",
    "evidence_submission", "resubmit", "upload_revised", "validate", "reprocess",
    "approve_import", "reject_import", "generate_package",
})

AUDITOR_ALLOWED_ACTIONS = frozenset({
    "review", "approve", "reject", "add_comment", "request_reupload", "assign_owner",
    "reassign", "escalate", "transfer_review", "view_trail", "close_observation",
    "clarify", "close_gap", "mock_audit", "assign_gap", "request_owner",
    "approve_reuse", "reject_reuse", "approve_exception", "reject_exception",
    "view_trail", "export_summary", "drill_down", "escalate_stale", "escalate_risk",
})


def normalize_role(role: str) -> str:
    role = (role or "owner").strip().lower()
    aliases = {
        "compliance_officer": "compliance_head",
        "security_officer": "compliance_head",
        "operations_owner": "owner",
        "ai_governance_owner": "cio",
        "ai_sdlc_owner": "owner",
        "framework_owner": "compliance_head",
    }
    return aliases.get(role, role)


def can_raise_exception(role: str) -> bool:
    d = _delegate("can_raise_exception", role)
    if d is not None:
        return d
    r = normalize_role(role)
    return r in {"owner", "auditor", "compliance_head", "cio", "vertical_head", "enterprise_admin"}


def can_export_reports(role: str) -> bool:
    d = _delegate("can_export_reports", role)
    if d is not None:
        return d
    return normalize_role(role) in {
        "owner", "auditor", "cio", "vertical_head", "compliance_head", "enterprise_admin",
    }


def can_manage_frameworks(role: str) -> bool:
    d = _delegate("can_manage_frameworks", role)
    if d is not None:
        return d
    from modules.frameworks.engines.framework_onboarding_engine import can_manage_framework_onboarding
    return can_manage_framework_onboarding(role)


def can_upload_evidence(role: str) -> bool:
    d = _delegate("can_upload_evidence", role)
    if d is not None:
        return d
    return normalize_role(role) in OPERATIONAL_UPLOAD_ROLES


def can_submit_to_auditor(role: str) -> bool:
    d = _delegate("can_submit_to_auditor", role)
    if d is not None:
        return d
    return can_upload_evidence(role)


def is_auditor(role: str) -> bool:
    return normalize_role(role) == "auditor"


def is_executive_readonly(role: str) -> bool:
    return normalize_role(role) in EXECUTIVE_ROLES


def can_review_evidence(role: str) -> bool:
    d = _delegate("can_review_evidence", role)
    if d is not None:
        return d
    return normalize_role(role) in AUDITOR_GOVERNANCE_ROLES | {"auditor"}


def can_assign_owner(role: str) -> bool:
    d = _delegate("can_assign_owner", role)
    if d is not None:
        return d
    r = normalize_role(role)
    return r in {"owner", "auditor", "compliance_head", "enterprise_admin"}


def can_escalate(role: str) -> bool:
    d = _delegate("can_escalate", role)
    if d is not None:
        return d
    r = normalize_role(role)
    return r in {"owner", "auditor", "cio", "vertical_head", "compliance_head", "enterprise_admin"}


def can_request_reupload(role: str) -> bool:
    d = _delegate("can_request_reupload", role)
    if d is not None:
        return d
    return is_auditor(role)


def can_admin_platform(role: str) -> bool:
    """Phase 2 Step 2D-critical: platform administration (connector sync, RAG
    reindex/warm). New capability (no prior predicate) restricted to administrators.
    Mirrors the rbac_legacy_compat set so the delegated and fallback paths agree."""
    d = _delegate("can_admin_platform", role)
    if d is not None:
        return d
    return normalize_role(role) in {"system_admin", "enterprise_admin", "admin"}


def action_allowed(role: str, action: str) -> bool:
    action = (action or "").lower().replace("-", "_")
    r = normalize_role(role)
    if action in UPLOAD_ACTIONS:
        return can_upload_evidence(r)
    if is_auditor(r):
        return action in AUDITOR_ALLOWED_ACTIONS or action not in UPLOAD_ACTIONS
    if is_executive_readonly(r) and action in UPLOAD_ACTIONS:
        return False
    return True


def permission_denied_message(action: str = "perform this action") -> str:
    return f"Access denied: your role cannot {action}."


def deny_redirect(role: str, user: str, dest: str = "/dashboard", msg: str | None = None) -> RedirectResponse:
    notice = quote(msg or permission_denied_message())
    sep = "&" if "?" in dest else "?"
    return RedirectResponse(url=f"{dest}{sep}role={quote(role)}&user={quote(user)}&notice={notice}", status_code=303)


def guard_upload(role: str, user: str, dest: str = "/dashboard") -> RedirectResponse | None:
    if not can_upload_evidence(role):
        return deny_redirect(
            role, user, dest,
            "Access denied: Auditors and executives cannot upload or replace evidence. "
            "Use Request Re-upload to return items to the App Owner queue.",
        )
    return None


def guard_auditor_governance(role: str, user: str, dest: str = "/dashboard") -> RedirectResponse | None:
    if not can_review_evidence(role):
        return deny_redirect(role, user, dest, "Access denied: auditor governance action only.")
    return None


def guard_submit_to_auditor(role: str, user: str, dest: str = "/dashboard") -> RedirectResponse | None:
    if not can_submit_to_auditor(role):
        return deny_redirect(role, user, dest, "Access denied: only App Owners may submit evidence to auditor review.")
    return None


def permission_ctx(role: str) -> dict:
    r = normalize_role(role)
    return {
        "perm_can_upload": can_upload_evidence(r),
        "perm_can_submit_auditor": can_submit_to_auditor(r),
        "perm_is_auditor": is_auditor(r),
        "perm_is_executive_readonly": is_executive_readonly(r),
        "perm_can_review": can_review_evidence(r),
        "perm_can_assign_owner": can_assign_owner(r),
        "perm_can_escalate": can_escalate(r),
        "perm_can_request_reupload": can_request_reupload(r),
        "perm_can_raise_exception": can_raise_exception(r),
        "perm_can_export": can_export_reports(r),
        "perm_can_manage_frameworks": can_manage_frameworks(r),
    }


def filter_actions_for_role(role: str, actions: list[str]) -> list[str]:
    return [a for a in actions if action_allowed(role, a)]


def chatbot_actions_for_role(role: str) -> list[tuple[str, str]]:
    """Role-filtered chatbot quick actions."""
    from modules.shared.services.chatbot_context_engine import AUDITOR_CHAT_ACTIONS, CONTEXTUAL_ACTIONS, OWNER_CHAT_ACTIONS

    r = normalize_role(role)
    if is_auditor(r):
        return list(AUDITOR_CHAT_ACTIONS)
    if is_executive_readonly(r):
        return [(l, k) for l, k in CONTEXTUAL_ACTIONS if k not in ("trigger_remediation",)]
    if can_upload_evidence(r):
        return list(OWNER_CHAT_ACTIONS)
    return [(l, k) for l, k in CONTEXTUAL_ACTIONS if "upload" not in k.lower()]
