"""Workflow audit wiring (Phase 4, Step 2).

A single helper that critical workflow handlers call to emit a durable audit
record AFTER a successful mutation. It is a pure side effect:

  * Gated by AUDIT_WORKFLOW_ENABLED (default FALSE) -> no-op, existing behavior
    is byte-for-byte unchanged.
  * Best-effort: never raises, so a DB/audit problem can never break a workflow.
  * Binds the Phase 1 authenticated identity from request.state.principal when
    present; falls back to the supplied actor label only when no principal exists
    (auth_source records which was used).

It does NOT alter approval/rejection/observation logic, RBAC, dashboards, or RAG.
"""

from __future__ import annotations

import os
from typing import Any


def workflow_audit_enabled() -> bool:
    """Feature flag. Default FALSE: no workflow audit records are written."""
    return str(os.environ.get("AUDIT_WORKFLOW_ENABLED", "")).strip().lower() in {
        "1", "true", "yes", "on",
    }


def _identity(request: Any, fallback_actor: str, fallback_role: str) -> dict[str, str]:
    """Resolve actor identity, preferring the Phase 1 validated principal.

    Returns actor (user_id or username), display label, role, and auth_source.
    Never raises."""
    principal = None
    try:
        principal = getattr(getattr(request, "state", None), "principal", None)
    except Exception:  # noqa: BLE001
        principal = None

    if principal is not None and getattr(principal, "is_authenticated", False):
        return {
            "actor": principal.user_id or principal.username or fallback_actor,
            "username": principal.username or "",
            "display_name": principal.display_name or "",
            "role": (principal.roles[0] if getattr(principal, "roles", None) else fallback_role),
            "auth_source": principal.auth_source or "session",
        }
    # No authenticated principal (e.g. auth disabled / dev demo) -> legacy label.
    return {
        "actor": fallback_actor or "unknown",
        "username": fallback_actor or "",
        "display_name": fallback_actor or "",
        "role": fallback_role or "",
        "auth_source": "legacy",
    }


def _request_id(request: Any) -> str:
    """Reuse a per-request correlation id if middleware set one, else generate."""
    from app.audit.service import new_request_id

    try:
        rid = getattr(getattr(request, "state", None), "request_id", "")
        if rid:
            return str(rid)
    except Exception:  # noqa: BLE001
        pass
    return new_request_id()


def audit_workflow_action(request: Any, action: str, *, resource: str = "",
                          fallback_actor: str = "", fallback_role: str = "",
                          before_state: dict[str, Any] | None = None,
                          after_state: dict[str, Any] | None = None,
                          detail: dict[str, Any] | None = None) -> bool:
    """Emit a durable audit record for a workflow mutation.

    No-op (returns False) when the feature flag is off. Returns True on a
    successful durable write. Never raises."""
    if not workflow_audit_enabled():
        return False
    try:
        from app.audit.service import AuditRecord, default_audit_service

        ident = _identity(request, fallback_actor, fallback_role)
        rec = AuditRecord(
            actor=ident["actor"],
            action=action,
            role=ident["role"],
            resource=resource,
            detail={**(detail or {}),
                    "username": ident["username"],
                    "display_name": ident["display_name"]},
            before_state=before_state,
            after_state=after_state,
            request_id=_request_id(request),
            auth_source=ident["auth_source"],
        )
        return default_audit_service.record(rec)
    except Exception:  # noqa: BLE001 - audit must never break a workflow
        return False
