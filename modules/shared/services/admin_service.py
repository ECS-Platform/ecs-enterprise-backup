"""ECS Admin service — users, roles, and applications (Batch 1, UC6).

A minimal, dependency-light administration layer that REUSES existing sources:

  * **Roles** are read-only and sourced from the canonical role catalog
    (:data:`app.auth.roles.CANONICAL_ROLES`) + RBAC capability predicates
    (:mod:`modules.shared.services.role_permissions`). Roles are NOT invented or
    mutated here — ECS role policy lives in ``config/rbac.yaml``.
  * **Applications** are listed from the existing demo onboarding registry
    (``ecs_state.onboarded_applications``); this module does not re-implement
    onboarding (that stays in the onboarding engines / platform layer).
  * **Users** are held in a small in-memory admin registry. ECS authentication is
    IdP/OIDC- or demo-persona-based, so this store carries **no passwords / no
    secrets** — only administrative user records (email, display name, assigned
    role, active flag, scope). It is a management surface, not an auth store.

Everything is deterministic and offline. Callers enforce RBAC (only platform
admins may mutate) at the route layer via ``role_permissions.can_admin_platform``.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Roles (read-only; sourced from the canonical catalog)
# --------------------------------------------------------------------------- #
def list_roles() -> list[dict[str, Any]]:
    """Return the canonical ECS roles with metadata + key capabilities.

    Roles come from :data:`app.auth.roles.CANONICAL_ROLES`; capabilities are
    derived from the existing ``role_permissions`` predicates so the admin view
    matches real enforcement, without duplicating the policy.
    """
    from app.auth.roles import CANONICAL_ROLES
    from modules.shared.services import role_permissions as rp

    out: list[dict[str, Any]] = []
    for role in CANONICAL_ROLES:
        key = role.key
        out.append({
            "key": key,
            "title": role.title,
            "description": role.description,
            "scope": role.scope,
            "category": role.category,
            "aliases": list(role.aliases),
            "capabilities": {
                "can_admin_platform": rp.can_admin_platform(key),
                "can_manage_frameworks": rp.can_manage_frameworks(key),
                "can_upload_evidence": rp.can_upload_evidence(key),
            },
        })
    return out


def valid_role_keys() -> set[str]:
    """The set of role keys (incl. aliases) an admin may assign to a user."""
    from app.auth.roles import CANONICAL_ROLES

    keys: set[str] = set()
    for role in CANONICAL_ROLES:
        keys.add(role.key)
        keys.update(role.aliases)
    return keys


# --------------------------------------------------------------------------- #
# Applications (listed from the existing onboarding registry)
# --------------------------------------------------------------------------- #
def list_applications() -> list[dict[str, Any]]:
    """List onboarded applications from the existing demo registry (read-only).

    Does not re-implement onboarding — reflects ``ecs_state.onboarded_applications``
    so the admin view is consistent with the onboarding flow. Never raises.
    """
    try:
        from app import ecs_state

        apps = getattr(ecs_state, "onboarded_applications", []) or []
        out: list[dict[str, Any]] = []
        for a in apps:
            if isinstance(a, dict):
                out.append({
                    "name": a.get("name") or a.get("application") or a.get("app_name") or "",
                    "owner": a.get("owner") or a.get("app_owner") or "",
                    "environment": a.get("environment") or a.get("env") or "",
                    "criticality": a.get("criticality") or "",
                    "status": a.get("status") or "Onboarded",
                })
            elif isinstance(a, str):
                out.append({"name": a, "owner": "", "environment": "",
                            "criticality": "", "status": "Onboarded"})
        return out
    except Exception:  # noqa: BLE001 - admin listing must never crash
        return []


# --------------------------------------------------------------------------- #
# Users (in-memory admin registry — no secrets)
# --------------------------------------------------------------------------- #
#: user_id -> user record. Seeded with a couple of representative admin users so
#: the admin screen is non-empty on a fresh process (non-secret, demo identities).
_USERS: dict[str, dict[str, Any]] = {}
_user_seq = 0

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _seed_users() -> None:
    global _user_seq
    if _USERS:
        return
    seed = [
        ("admin@ecs.local", "ECS Administrator", "system_admin", "enterprise"),
        ("compliance.head@ecs.local", "Compliance Head", "compliance_officer", "enterprise"),
        ("netbanking.owner@ecs.local", "Net Banking Owner", "application_owner", "Net Banking"),
    ]
    for email, name, role, scope in seed:
        _user_seq += 1
        uid = f"USR-{_user_seq:04d}"
        _USERS[uid] = {
            "user_id": uid, "email": email, "display_name": name,
            "role": role, "scope": scope, "active": True,
            "created_at": _now(), "updated_at": _now(),
        }


def reset_users() -> None:
    """Test hook: clear the in-memory user registry."""
    global _user_seq
    _USERS.clear()
    _user_seq = 0


def list_users(*, role: str = "", active: Optional[bool] = None) -> list[dict[str, Any]]:
    _seed_users()
    users = list(_USERS.values())
    if role:
        users = [u for u in users if u["role"] == role]
    if active is not None:
        users = [u for u in users if u["active"] is active]
    return sorted(users, key=lambda u: u["user_id"])


def get_user(user_id: str) -> Optional[dict[str, Any]]:
    _seed_users()
    return _USERS.get(user_id)


class AdminError(ValueError):
    """Raised for invalid admin operations (bad email, unknown role, etc.)."""


def create_user(*, email: str, display_name: str, role: str,
                scope: str = "") -> dict[str, Any]:
    """Create an admin user record. Validates email + role. No password stored."""
    _seed_users()
    email = (email or "").strip().lower()
    if not _EMAIL_RE.match(email):
        raise AdminError("A valid email is required.")
    if any(u["email"] == email for u in _USERS.values()):
        raise AdminError(f"A user with email {email} already exists.")
    role = (role or "").strip()
    if role not in valid_role_keys():
        raise AdminError(f"Unknown role: {role}")
    global _user_seq
    _user_seq += 1
    uid = f"USR-{_user_seq:04d}"
    rec = {
        "user_id": uid, "email": email,
        "display_name": (display_name or email.split("@")[0]).strip(),
        "role": role, "scope": (scope or "").strip(), "active": True,
        "created_at": _now(), "updated_at": _now(),
    }
    _USERS[uid] = rec
    return rec


def update_user_role(user_id: str, role: str, *, scope: Optional[str] = None) -> dict[str, Any]:
    """Reassign a user's role (and optionally scope). Validates the role."""
    _seed_users()
    rec = _USERS.get(user_id)
    if rec is None:
        raise KeyError(user_id)
    role = (role or "").strip()
    if role not in valid_role_keys():
        raise AdminError(f"Unknown role: {role}")
    rec["role"] = role
    if scope is not None:
        rec["scope"] = scope.strip()
    rec["updated_at"] = _now()
    return rec


def set_user_active(user_id: str, active: bool) -> dict[str, Any]:
    """Activate / deactivate a user (soft; records are never hard-deleted here)."""
    _seed_users()
    rec = _USERS.get(user_id)
    if rec is None:
        raise KeyError(user_id)
    rec["active"] = bool(active)
    rec["updated_at"] = _now()
    return rec


def admin_summary() -> dict[str, Any]:
    """Roll-up for the admin dashboard header."""
    users = list_users()
    roles = list_roles()
    by_role: dict[str, int] = {}
    for u in users:
        by_role[u["role"]] = by_role.get(u["role"], 0) + 1
    return {
        "user_count": len(users),
        "active_user_count": sum(1 for u in users if u["active"]),
        "role_count": len(roles),
        "application_count": len(list_applications()),
        "users_by_role": by_role,
    }
